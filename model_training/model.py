# ===== HYPERPARAMETERS (Best Tuned Configuration) =====
# Experiment ID: bayesian_20251130_165747_013
# Accuracy: 60.14% (+5.14% improvement from baseline)
# Tuning Method: Bayesian Search
# Created: 2025-11-30 21:57:47
# ====================================================
HP_GENRE_WEIGHT = 0.14662101250859466
HP_CAST_WEIGHT = 0.3201074645922799
HP_FRANCHISE_WEIGHT = 0.21160768562420387
HP_RATING_WEIGHT = 0.09461928091764502
HP_POPULARITY_WEIGHT = 0.21341924397465173
HP_GENRE_BOOST_HIGH = 0.15
HP_GENRE_BOOST_MED = 0.1
HP_GENRE_BOOST_LOW = -0.2
HP_GENRE_THRESHOLD_HIGH = 0.7
HP_GENRE_THRESHOLD_MED = 0.5
HP_GENRE_THRESHOLD_LOW = 0.3
# ====================================================
import sqlite3
import re
import time
import math
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, lit, udf, split, array_intersect, size, when, log10
from pyspark.sql.types import FloatType, StringType, ArrayType

"""
Movie Recommendation Engine using PySpark

This module provides collaborative filtering-based movie recommendations using PySpark
for distributed computation. It calculates similarity scores based on genres, cast, and
franchises, then ranks movies by a hybrid scoring algorithm.

Key Features:
- Weighted user profile generation from rated movies
- Multi-dimensional similarity metrics (genre, cast, franchise)
- Hybrid scoring combining genre, cast, franchise, and rating components
- Per-user recommendations based on viewing history
- Last-added movie recommendations
- Genre-based recommendations
"""

# Global Spark session and cached dataframe
spark = None
df_all = None
_data_loaded = False

# Database and CSV paths
DB_PATH = "movies.db"
CSV_PATH = "output.csv"


def extract_cast_names(cc_str):
    """
    Extract cast members from pipe-separated cast string.
    
    Parses cast_and_crew format: "FirstName|LastName,FirstName|LastName,..."
    Returns a set of lowercase "firstname lastname" pairs for easy comparison.
    
    Args:
        cc_str (str): Cast string in format "First|Last,First|Last,..."
        
    Returns:
        set: Set of lowercased "firstname lastname" pairs
        
    Example:
        >>> extract_cast_names("Tom|Hanks,Tim|Allen")
        {'tom hanks', 'tim allen'}
    """
    if not cc_str:
        return set()
    names = set()
    # Iterate through comma-separated cast entries
    for entry in cc_str.split(","):
        # Split by pipe to get first and last names
        parts = entry.strip().split("|")
        if len(parts) >= 2:
            first, last = parts[0].strip().lower(), parts[1].strip().lower()
            if first and last:
                names.add(f"{first} {last}")
    return names


def extract_base_title(title):
    """
    Extract base franchise name from movie title.
    
    Removes franchise indicators like "Part 2", "Returns", "Sequel", etc.
    to identify movies from the same franchise.
    
    Args:
        title (str): Movie title string
        
    Returns:
        str: Lowercased base title without franchise indicators
        
    Example:
        >>> extract_base_title("Toy Story 2: The Sequel")
        'toy story'
    """
    if not title:
        return ""
    # Remove "Part X" or "Vol X" patterns
    title = re.sub(r'\s+(Part|Vol)\s+[IVX0-9]+', '', title, flags=re.IGNORECASE)
    # Remove trailing numbers
    title = re.sub(r'\s+\d+$', '', title)
    # Remove sequel/return indicators
    title = re.sub(r':\s+(The\s+)?Sequel|Returns|Reborn|Unleashed', '', title, flags=re.IGNORECASE)
    # Remove parenthetical suffixes
    title = re.sub(r'\s+\(.*?\)', '', title)
    return title.strip().lower()


def genre_similarity(user_genres, movie_genres):
    """
    Calculate Jaccard similarity between user's genres and movie's genres.
    
    Jaccard similarity = |intersection| / |union|
    Ranges from 0.0 (no overlap) to 1.0 (identical genres)
    
    Args:
        user_genres (str): Pipe-separated genre string from user profile
        movie_genres (str): Pipe-separated genre string from candidate movie
        
    Returns:
        float: Jaccard similarity score [0.0, 1.0]
    """
    if not user_genres or not movie_genres:
        return 0.0
    # Convert pipe-separated strings to sets for intersection/union calculation
    user_set = set(user_genres.split("|"))
    movie_set = set(movie_genres.split("|"))
    # Jaccard similarity = overlap / total unique
    return float(len(user_set & movie_set)) / float(len(user_set | movie_set))


def franchise_similarity(user_title, movie_title):
    """
    Check if two movies belong to the same franchise.
    
    Uses extract_base_title to compare base franchise names.
    
    Args:
        user_title (str): Title of user's rated movie
        movie_title (str): Title of candidate movie
        
    Returns:
        float: 1.0 if same franchise, 0.0 otherwise
    """
    # Extract base titles to compare franchises
    user_base = extract_base_title(user_title)
    movie_base = extract_base_title(movie_title)
    # Return 1.0 if same franchise and not empty
    if user_base == movie_base and user_base:
        return 1.0
    return 0.0


def cast_similarity(user_names_str, movie_names_str):
    """
    Calculate cast overlap as a ratio of common actors.
    
    Compares pre-extracted cast names. Returns ratio of overlapping actors
    to total actors in the candidate movie.
    
    Args:
        user_names_str (str): Pipe-separated cast names from user's movies
        movie_names_str (str): Pipe-separated cast names from candidate movie
        
    Returns:
        float: Ratio [0.0, 1.0] of movie actors present in user's cast
    """
    if not user_names_str or not movie_names_str:
        return 0.0
    # Convert pipe-separated strings to sets for overlap calculation
    user_set = set(user_names_str.split("|"))
    movie_set = set(movie_names_str.split("|"))
    if not user_set or not movie_set:
        return 0.0
    # Return overlap ratio relative to movie's total cast
    intersection = user_set & movie_set
    return float(len(intersection)) / float(len(movie_set))


def read_csv():
    """
    Load and preprocess CSV data into Spark DataFrame.
    
    Performs the following operations:
    1. Reads CSV with proper escape/quote handling for complex fields
    2. Extracts cast names from cast_and_crew field
    3. Pre-computes base titles for franchise matching
    4. Splits genres and cast into arrays for efficient Spark operations
    5. Cleans and casts numeric columns
    6. Caches result for reuse
    
    Returns:
        DataFrame: Cached Spark DataFrame with preprocessed movie data
        
    Global:
        df_all: Set to the loaded and cached DataFrame
    """
    global df_all, spark

    # Read CSV with special handling for multiline and quoted fields
    df = spark.read.option("header", True) \
        .option("multiLine", True) \
        .option("escape", "\"") \
        .option("quote", "\"") \
        .csv(CSV_PATH)

    # Extract cast names and convert to pipe-separated format
    @udf(StringType())
    def extract_names_udf(cc_str):
        """Extract and join cast names from cast_and_crew string."""
        names = extract_cast_names(cc_str)
        return "|".join(sorted(names)) if names else ""

    df = df.withColumn("cast_names", extract_names_udf(col("cast_and_crew")))

    # Extract base franchise titles
    @udf(StringType())
    def base_title_udf(title):
        """Extract base franchise title."""
        return extract_base_title(title)
    
    df = df.withColumn("base_title", base_title_udf(col("title")))

    # Pre-split genres and cast names into arrays for efficient operations
    df = df.withColumn("genres_array", split(col("genres"), "\\|")) \
           .withColumn("cast_names_array", split(col("cast_names"), "\\|"))

    # Clean and cast numeric columns
    numeric_columns = ["avg_rating", "rating_count"]
    for c in numeric_columns:
        if c in df.columns:
            df = df.withColumn(c, regexp_replace(col(c), r'[^0-9.\-]', "")) \
                   .withColumn(c, col(c).cast(FloatType()))
    # Fill missing numeric values with 0.0
    df = df.fillna({c: 0.0 for c in numeric_columns})

    # Cache for performance
    df_all = df.cache()
    return df_all


def create_spark_and_load_data():
    """
    Initialize Spark session and load/preprocess CSV data.
    
    Creates local Spark session with optimized settings for movie recommendations:
    - Uses all available CPU cores
    - Minimizes shuffle partitions for faster processing
    - Configures driver for stable operation
    - Only loads data once (uses global flag to prevent re-reading)
    
    Global:
        spark: Initialized SparkSession instance
        df_all: Cached DataFrame with preprocessed movie data
        _data_loaded: Flag to prevent re-loading data
    """
    global spark, df_all, _data_loaded
    
    # Skip if data is already loaded and cached
    if _data_loaded and df_all is not None:
        return
    
    # Create Spark session with local cluster using all available cores
    if spark is None:
        spark = SparkSession.builder \
            .master("local[*]") \
            .appName("MovieRecommenderModel") \
            .config("spark.driver.host", "127.0.0.1") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.python.worker.faulthandler.enabled", "true") \
            .getOrCreate()
        # Suppress INFO/WARN logs
        spark.sparkContext.setLogLevel("ERROR")
    
    # Load and cache the movie data
    read_csv()
    _data_loaded = True


def get_top_recommendations(user_id, top_n=10):
    """
    Generate personalized recommendations for a user.
    
    Algorithm:
    1. Loads user's rated movies from SQLite
    2. Builds weighted user profile combining genres, cast, and ratings
    3. Filters out user's already-rated movies
    4. Calculates similarity scores for remaining movies:
       - Genre similarity (45% weight)
       - Cast similarity (15% weight)
       - Franchise similarity (5% weight)
       - User's average rating norm (35% weight)
    5. Returns top N movies by hybrid score
    
    Args:
        user_id (int): Database user ID
        top_n (int): Number of recommendations to return (default 10)
        
    Returns:
        list: List of dicts with keys:
            - title: Movie title
            - cast_names: Pipe-separated cast string
            - genre_sim, cast_sim, franchise_sim: Individual similarity scores
            - user_rating_norm: User's average rating
            - hybrid_score: Combined score [0.0, 1.0]
            - cast_overlap: List of cast members in both user profile and movie
    """
    _timer_start = time.time()
    global spark, df_all, _data_loaded
    # Initialize Spark and load data once if not already done (uses cache)
    if not _data_loaded or df_all is None:
        create_spark_and_load_data()

    # Fetch user's rated movies from database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM movies WHERE user_id = ? AND userRating IS NOT NULL AND userRating > 0", (user_id,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()

    # Convert rows to list of dicts
    user_movies_list = [dict(zip(columns, row)) for row in rows]
    if not user_movies_list:
        print(f"No rated movies found for user {user_id}")
        return []

    # Extract cast names for each user movie
    for movie_dict in user_movies_list:
        names = extract_cast_names(movie_dict["cast_and_crew"])
        movie_dict["cast_names"] = "|".join(sorted(names))

    # Create Spark DataFrame from user movies
    df_user = spark.createDataFrame(user_movies_list)
    # Normalize ratings to [0, 1] and split genres/cast into arrays
    df_user = df_user.withColumn("weight", col("userRating") / 10.0) \
                     .withColumn("cast_names_array", split(col("cast_names"), "\\|")) \
                     .withColumn("genres_array", split(col("genres"), "\\|"))

    # Aggregate user profile: collect all genres and cast members
    profile_agg = df_user.selectExpr(
        "collect_list(id) as user_ids",
        "collect_list(title) as user_titles",
        "avg(weight * weight) / avg(weight) as weighted_avg_rating",
        "concat_ws('|', collect_set(concat_ws('|', genres))) as all_genres",
        "concat_ws('|', collect_set(concat_ws('|', cast_names))) as all_cast"
    ).collect()[0]
    
    # Extract profile components
    user_ids_list = [str(uid) for uid in profile_agg.user_ids]
    user_titles_list = profile_agg.user_titles
    weighted_avg_rating = float(profile_agg.weighted_avg_rating) if profile_agg.weighted_avg_rating else 0.0
    
    # Broadcast user profile to all workers for UDF computation
    user_cast_str = profile_agg.all_cast if profile_agg.all_cast else ""
    user_cast_array = [c.strip() for c in user_cast_str.split("|") if c.strip()]

    bc_genres = spark.sparkContext.broadcast(profile_agg.all_genres)
    bc_cast = spark.sparkContext.broadcast(profile_agg.all_cast)
    bc_titles = spark.sparkContext.broadcast("|".join(user_titles_list))
    bc_avg_rating = spark.sparkContext.broadcast(weighted_avg_rating)
    bc_user_cast_array = spark.sparkContext.broadcast(user_cast_array)

    # Filter out user's already-rated movies
    df_filtered = df_all.filter(~col("id").isin(user_ids_list))

    # UDF: Calculate genre similarity with user profile
    @udf(FloatType())
    def genre_sim_udf(genres_array):
        """Calculate genre similarity with user profile."""
        if not genres_array or not bc_genres.value:
            return 0.0
        user_set = set(bc_genres.value.split("|"))
        movie_set = set([g.strip() for g in genres_array if g.strip()])
        if not user_set or not movie_set:
            return 0.0
        return float(len(user_set & movie_set)) / float(len(user_set | movie_set))

    # UDF: Calculate weighted cast overlap with position-based weighting
    @udf(FloatType())
    def cast_sim_udf(cast_array):
        """
        Calculate cast overlap ratio with position-based weighting.
        Lead cast (0-5): weight 1.0
        Supporting (5-15): weight 0.7
        Background (15+): weight 0.3
        """
        if not cast_array or not bc_cast.value:
            return 0.0
        
        # Parse user cast with position weights
        user_cast_list = [c.strip() for c in bc_cast.value.split("|") if c.strip()]
        user_cast_weighted = {}
        for i, c in enumerate(user_cast_list):
            weight = 1.0 if i < 5 else (0.7 if i < 15 else 0.3)
            user_cast_weighted[c] = weight
        
        # Parse movie cast with position weights
        movie_cast_list = [c.strip() for c in cast_array if isinstance(c, str) and c.strip()]
        movie_cast_weighted = {}
        for i, c in enumerate(movie_cast_list):
            weight = 1.0 if i < 5 else (0.7 if i < 15 else 0.3)
            movie_cast_weighted[c] = weight
        
        # Calculate weighted overlap
        if not user_cast_weighted or not movie_cast_weighted:
            return 0.0
        
        overlap_weight = sum(user_cast_weighted.get(c, 0) for c in movie_cast_weighted)
        max_weight = sum(movie_cast_weighted.values())
        
        return min(1.0, overlap_weight / max_weight) if max_weight > 0 else 0.0

    # UDF: Check if movie is in same franchise as any user movie
    @udf(FloatType())
    def franchise_sim_udf(movie_title):
        """Check if movie is in same franchise as any user movie."""
        if not movie_title or not bc_titles.value:
            return 0.0
        return 1.0 if any(franchise_similarity(t, movie_title) > 0.0 for t in bc_titles.value.split("|")) else 0.0

    # Calculate similarity scores for all candidate movies
    df_profile_sim = df_filtered \
        .withColumn("genre_sim", genre_sim_udf(col("genres_array"))) \
        .withColumn("cast_sim", cast_sim_udf(col("cast_names_array"))) \
        .withColumn("franchise_sim", franchise_sim_udf(col("title"))) \
        .withColumn("user_rating_norm", lit(bc_avg_rating.value)) \
        .withColumn("cast_overlap_array", array_intersect(col("cast_names_array"), when(size(col("cast_names_array")) > 0, col("cast_names_array")))) \
        .withColumn("rating_popularity", col("avg_rating") / 10.0) \
        .withColumn("count_popularity", when(col("rating_count") > 0, (log10(col("rating_count") + 1) / 3.0)).otherwise(0.0)) \
        .withColumn("popularity_score", 0.7 * col("rating_popularity") + 0.3 * col("count_popularity")) \
        .withColumn("genre_boost",
                   when(col("genre_sim") > 0.7, 0.15)
                   .when(col("genre_sim") > 0.5, 0.10)
                   .when(col("genre_sim") < 0.3, -0.20)
                   .otherwise(0.0)) \
        .withColumn("hybrid_score",
                    0.40 * col("genre_sim") +
                    0.15 * col("cast_sim") +
                    0.05 * col("franchise_sim") +
                    0.30 * col("user_rating_norm") +
                    0.10 * col("popularity_score") +
                    col("genre_boost")) \
        .orderBy(col("hybrid_score").desc())

    # Collect top N results from Spark cluster
    results = df_profile_sim.select(
        "title", "cast_names", "genre_sim", "cast_sim", "franchise_sim", "user_rating_norm", "hybrid_score", "cast_overlap_array"
    ).limit(top_n).collect()

    # Format results
    result_list = []
    for row in results:
        rec_dict = row.asDict()
        rec_dict["cast_overlap"] = sorted([c for c in rec_dict.get("cast_overlap_array", []) if c])
        result_list.append(rec_dict)

    _elapsed = time.time() - _timer_start
    print(f"[TIMER] get_top_recommendations: {_elapsed:.2f}s")
    return result_list


def get_recommendations_for_last_added(user_id, top_n=10):
    """
    Generate recommendations based on user's most recently added movie.
    
    Algorithm:
    1. Retrieves user's last added movie from SQLite
    2. Finds similar movies by comparing:
       - Genres (45% weight)
       - Cast members (15% weight)
       - Franchise (5% weight)
       - Average rating (35% weight)
    3. Returns top N similar movies
    
    Args:
        user_id (int): Database user ID
        top_n (int): Number of recommendations to return (default 10)
        
    Returns:
        list: List of dicts with keys:
            - title: Movie title
            - genres: Pipe-separated genre string
            - cast_names: Pipe-separated cast string
            - genre_sim, cast_sim, franchise_sim: Individual similarity scores
            - hybrid_score: Combined score
            - reference_movie: Title of the movie used as basis
            - cast_overlap: List of shared cast members
    """
    _timer_start = time.time()
    global spark, df_all, _data_loaded
    # Initialize Spark and load data once if not already done (uses cache)
    if not _data_loaded or df_all is None:
        create_spark_and_load_data()

    # Fetch user's last added movie
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM movies WHERE user_id = ? ORDER BY ROWID DESC LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        return []
    columns = [desc[0] for desc in cur.description]
    last_movie = dict(zip(columns, row))
    conn.close()

    # Extract cast names for reference movie
    last_cast_names = "|".join(sorted(extract_cast_names(last_movie["cast_and_crew"])))
    last_movie["cast_names"] = last_cast_names
    last_movie_id = str(last_movie["id"])

    # Broadcast reference movie attributes to all workers
    bc_genres = spark.sparkContext.broadcast(last_movie["genres"])
    bc_cast = spark.sparkContext.broadcast(last_movie["cast_names"])
    bc_title = spark.sparkContext.broadcast(last_movie["title"])
    bc_movie_id = spark.sparkContext.broadcast(last_movie_id)
    bc_last_cast_array = spark.sparkContext.broadcast([c.strip() for c in last_movie["cast_names"].split("|") if c.strip()])

    # UDF: Calculate genre similarity with reference movie
    @udf(FloatType())
    def genre_sim_udf(genres_array):
        """Calculate genre similarity with reference movie."""
        if not genres_array or not bc_genres.value:
            return 0.0
        user_set = set([g.strip() for g in bc_genres.value.split("|") if g.strip()])
        movie_set = set([g.strip() for g in genres_array if g.strip()])
        if not user_set or not movie_set:
            return 0.0
        return float(len(user_set & movie_set)) / float(len(user_set | movie_set))

    # UDF: Calculate cast overlap with reference movie
    @udf(FloatType())
    def cast_sim_udf(cast_array):
        """Calculate cast overlap with reference movie."""
        if not cast_array or not bc_cast.value:
            return 0.0
        user_set = set([c.strip() for c in bc_cast.value.split("|") if c.strip()])
        movie_set = set([c.strip() for c in cast_array if c.strip()])
        if not user_set or not movie_set:
            return 0.0
        intersection = user_set & movie_set
        return float(len(intersection)) / float(len(movie_set))

    # UDF: Check if movie is in same franchise as reference movie
    @udf(FloatType())
    def franchise_sim_udf(movie_title):
        """Check if movie is in same franchise as reference movie."""
        return franchise_similarity(bc_title.value, movie_title)

    # Calculate similarity scores for all candidate movies
    df_recommendations = df_all.filter(col("id") != bc_movie_id.value) \
        .withColumn("genre_sim", genre_sim_udf(col("genres_array"))) \
        .withColumn("cast_sim", cast_sim_udf(col("cast_names_array"))) \
        .withColumn("franchise_sim", franchise_sim_udf(col("title"))) \
        .withColumn("cast_overlap_array", array_intersect(col("cast_names_array"), when(size(col("cast_names_array")) > 0, col("cast_names_array")))) \
        .withColumn("hybrid_score",
                    0.45 * col("genre_sim") +
                    0.15 * col("cast_sim") +
                    0.05 * col("franchise_sim") +
                    0.35 * col("avg_rating") / 10.0) \
        .orderBy(col("hybrid_score").desc())

    # Collect top N results
    results = df_recommendations.select(
        "title", "cast_names", "genres", "genre_sim", "cast_sim", "franchise_sim", "hybrid_score", "cast_overlap_array"
    ).limit(top_n).collect()

    # Format results with reference movie info
    result_list = []
    for row in results:
        rec_dict = row.asDict()
        rec_dict["reference_movie"] = last_movie['title']
        rec_dict["cast_overlap"] = sorted([c for c in rec_dict.get("cast_overlap_array", []) if c])
        result_list.append(rec_dict)

    _elapsed = time.time() - _timer_start
    print(f"[TIMER] get_recommendations_for_last_added: {_elapsed:.2f}s")
    return result_list


def get_recommendations_by_most_common_genre(user_id, top_n=10):
    """
    Generate recommendations based on user's most frequently watched genre.
    
    Algorithm:
    1. Identifies the most common genre in user's rated movies
    2. Filters movies containing that genre
    3. Scores movies using:
       - Genre match (70% weight) - 1.0 if contains main genre, 0.0 otherwise
       - Average rating (30% weight)
    4. Returns top N movies by combined score
    
    Args:
        user_id (int): Database user ID
        top_n (int): Number of recommendations to return (default 10)
        
    Returns:
        list: List of dicts with keys:
            - title: Movie title
            - genres: Pipe-separated genre string
            - avg_rating: Movie's average rating
            - genre_match: 1.0 if contains main genre, 0.0 otherwise
            - score: Combined score [0.0, 1.0]
    """
    _timer_start = time.time()
    global spark, df_all, _data_loaded
    # Initialize Spark and load data once if not already done (uses cache)
    if not _data_loaded or df_all is None:
        create_spark_and_load_data()

    # Fetch user's genres from database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT genres FROM movies WHERE user_id = ? AND genres IS NOT NULL AND genres != ''", (user_id,))
    genre_rows = cur.fetchall()
    conn.close()
    if not genre_rows:
        return []

    # Find most common genre across all user movies
    genre_count = {}
    for (genre_str,) in genre_rows:
        for g in genre_str.split("|"):
            genre_count[g] = genre_count.get(g, 0) + 1

    most_common_genre = max(genre_count, key=genre_count.get)
    # Broadcast genre to all workers
    bc_main_genre = spark.sparkContext.broadcast(most_common_genre)

    # UDF: Check if movie contains the main genre
    @udf(FloatType())
    def single_genre_match(movie_genres):
        """Check if movie contains the main genre."""
        if not movie_genres:
            return 0.0
        return 1.0 if bc_main_genre.value in movie_genres.split("|") else 0.0

    # Score all movies by genre match and rating
    df_recs = df_all.withColumn("genre_match", single_genre_match(col("genres"))) \
                    .withColumn("score", 0.70 * col("genre_match") + 0.30 * (col("avg_rating") / 10.0)) \
                    .orderBy(col("score").desc())

    # Collect top N results
    results = df_recs.select("title", "genres", "avg_rating", "genre_match", "score").limit(top_n).collect()
    
    _elapsed = time.time() - _timer_start
    print(f"[TIMER] get_recommendations_by_most_common_genre: {_elapsed:.2f}s")
    return [r.asDict() for r in results]
