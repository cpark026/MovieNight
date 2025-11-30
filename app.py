from flask import Flask, render_template, jsonify, request, session, redirect
import requests
import urllib.parse
import sqlite3
import sys
import os
import hashlib
import secrets
import csv
from dotenv import load_dotenv

# Add model_training folder to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'model_training'))

# Add feedback_system folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'feedback_system'))

from recommendation_tracker import (
    save_recommendation_set, 
    check_for_model_revalidation,
    get_model_performance_metrics,
    validate_recommendation_against_rating
)
from model_versioning import (
    init_model_versioning,
    get_active_model_version,
    create_weighted_training_data,
    create_model_version,
    evaluate_model_version,
    activate_model_version,
    should_retrain,
    get_model_stats
)

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Add the app directory to path for model imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "movies.db")
CSV_PATH = os.path.join(BASE_DIR, "output.csv")

# Initialize model once at startup
try:
    import model
    MODEL_READY = True
except Exception as e:
    print(f"Warning: Could not initialize model: {e}")
    MODEL_READY = False

# Initialize feedback system
try:
    from feedback_system import init_feedback_tables, register_feedback_routes
    init_feedback_tables()
    register_feedback_routes(app)
    FEEDBACK_READY = True
except Exception as e:
    print(f"Warning: Could not initialize feedback system: {e}")
    FEEDBACK_READY = False

# ========================
# TMDb Bearer token (from environment)
# ========================
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")

# ========================
# Helper Functions
# ========================
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, stored_hash):
    """Verify password against stored hash"""
    return hash_password(password) == stored_hash

def create_users_table():
    """Create users table if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# ========================
# Authentication Routes
# ========================
@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint that verifies password hash"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"message": "Username and password required"}), 400
        
        conn = sqlite3.connect("movies.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()
        
        if not user or not verify_password(password, user['password_hash']):
            return jsonify({"message": "Invalid username or password"}), 401
        
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = username
        return jsonify({"success": True, "username": username}), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"message": "An error occurred"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"message": "Username and password required"}), 400
        
        if len(password) < 6:
            return jsonify({"message": "Password must be at least 6 characters"}), 400
        
        password_hash = hash_password(password)
        
        conn = sqlite3.connect("movies.db")
        cur = conn.cursor()
        
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()
            user_id = cur.lastrowid
            conn.close()
            
            session.permanent = True
            session['user_id'] = user_id
            session['username'] = username
            return jsonify({"success": True, "username": username}), 201
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"message": "Username already exists"}), 409
            
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({"message": "An error occurred"}), 500

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated and return username"""
    if 'user_id' in session and 'username' in session:
        return jsonify({"authenticated": True, "username": session['username']}), 200
    return jsonify({"authenticated": False}), 200

@app.route('/api/logout', methods=['POST'])
def logout_user():
    """Logout user by clearing session"""
    session.clear()
    return jsonify({"success": True}), 200

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect('/')
    return render_template('login.html')

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('results.html')

@app.route("/getWatchlistIDs", methods=["GET"])
def get_watchlist_ids():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        conn = sqlite3.connect("movies.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM movies WHERE user_id = ?", (session['user_id'],))
        rows = cur.fetchall()
        conn.close()

        result = [{"mediaID": row["id"]} for row in rows]
        return jsonify(result)
    except Exception as e:
        print("Error fetching watchlist IDs:", e)
        return jsonify([])

@app.route("/addShow", methods=["POST"])
def add_show():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        if not data or "id" not in data:
            return jsonify({"error": "Invalid data"}), 400

        conn = sqlite3.connect("movies.db")
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO movies 
            (id, title, adult, genres, overview, production_companies, cast_and_crew, rating_count, userRating, poster, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("id"),
            data.get("title") or data.get("name"),
            data.get("adult"),
            data.get("genres"),
            data.get("overview") or data.get("summary"),
            data.get("production_companies"),
            data.get("cast_and_crew"),
            data.get("rating_count"),
            data.get("userRating"),
            data.get("poster") or data.get("image"),
            session['user_id']
        ))

        conn.commit()
        
        # RECOMMENDATION VALIDATION
        # When user adds a movie, check if it was in any recent recommendations
        movie_title = data.get("title") or data.get("name")
        user_rating = data.get("userRating")
        movie_id = data.get("id")
        
        validation_result = None
        if user_rating and movie_title:
            validation_result = validate_recommendation_against_rating(
                session['user_id'], 
                movie_id, 
                movie_title, 
                user_rating
            )
        
        conn.close()
        
        response = {"success": True}
        if validation_result:
            response["recommendation_validation"] = {
                "was_recommended": validation_result['was_in_recommendations'],
                "predicted_score": round(validation_result['predicted_score'], 3),
                "actual_rating": round(validation_result['actual_rating'], 2),
                "quality_score": round(validation_result['quality_score'], 3),
                "is_accurate": validation_result['is_accurate'],
                "message": (
                    f"✓ Good recommendation!" if validation_result['is_accurate'] 
                    else f"✗ Prediction was off by {abs(validation_result['predicted_score'] - validation_result['actual_rating']):.2f}"
                ) if validation_result['was_in_recommendations'] else None
            }
        
        return jsonify(response)
    except Exception as e:
        print("Error adding show:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/getResults")
def get_results():
    query = request.args.get("name", "").strip()
    if not query:
        return jsonify([])

    encoded_query = urllib.parse.quote_plus(query)
    search_url = f"https://api.themoviedb.org/3/search/movie?query={encoded_query}&page=1&include_adult=false"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}"
    }

    try:
        search_resp = requests.get(search_url, headers=headers)
        search_resp.raise_for_status()
        results = search_resp.json().get("results", [])
    except Exception as e:
        print("TMDb search API error:", e)
        return jsonify([])

    final_data = []

    for item in results:
        movie_id = item.get("id")
        if not movie_id:
            continue

        detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?append_to_response=credits"
        try:
            detail_resp = requests.get(detail_url, headers=headers)
            detail_resp.raise_for_status()
            details = detail_resp.json()
        except Exception as e:
            print(f"TMDb detail API error for movie {movie_id}:", e)
            continue

        genres = "|".join([g.get("name") for g in details.get("genres", []) if g.get("name")])
        prod_companies = "|".join([c.get("name") for c in details.get("production_companies", []) if c.get("name")])

        credits = details.get("credits", {})
        cast_list = []
        for cast_member in credits.get("cast", []):
            name_parts = cast_member.get("name", "").split(" ", 1)
            first = name_parts[0] if len(name_parts) > 0 else ""
            last = name_parts[1] if len(name_parts) > 1 else ""
            cast_list.append(f"{first}|{last}")
        cast_and_crew = ",".join(cast_list)

        poster_path = details.get('poster_path')
        final_data.append({
            "id": details.get("id"),
            "title": details.get("title"),
            "adult": details.get("adult", False),
            "genres": genres,
            "overview": details.get("overview", ""),
            "production_companies": prod_companies,
            "cast_and_crew": cast_and_crew,
            "rating_count": details.get("vote_count", 0),
            "userRating": None,
            "poster": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "",
            "poster_path": poster_path
        })

    return jsonify(final_data)

@app.route("/getLastAddedMovie")
def get_last_added_movie():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        conn = sqlite3.connect("movies.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM movies WHERE user_id = ? ORDER BY rowid DESC LIMIT 1", (session['user_id'],))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return jsonify({"id": row["id"], "title": row["title"]})
        else:
            return jsonify({"error": "No movies found"}), 404
    except Exception as e:
        print(f"Error fetching last movie: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/getRecommendations")
def get_recommendations():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if not MODEL_READY:
        return jsonify({"error": "Model not initialized"}), 500
    
    try:
        print(f"[DEBUG] Fetching top 10 recommendations for user {session['user_id']}...")
        recommendations = model.get_top_recommendations(session['user_id'], top_n=10)
        print(f"[DEBUG] Received {len(recommendations)} recommendations")
        
        if not recommendations:
            print("[DEBUG] No recommendations returned from model")
            return jsonify({"error": "No recommendations found"}), 404
        
        # Save recommendations for later validation
        rec_set_id = save_recommendation_set(session['user_id'], recommendations, "general")
        
        # Check if model needs revalidation
        revalidation_status = check_for_model_revalidation(session['user_id'])
        
        print(f"[DEBUG] Loading CSV from: {CSV_PATH}")
        movie_data = {}
        
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) > 1:
                    movie_id = row[1].strip()  # ID is at index 1
                    title = row[4].strip()  # Title is at index 4
                    movie_data[movie_id] = row
                    movie_data[title] = row
                    if len(movie_data) <= 10:
                        print(f"[DEBUG] Added: id='{movie_id}', title='{title}'")
        
        print(f"[DEBUG] Loaded {len(movie_data)} movies")
        print(f"[DEBUG] Sample keys: {list(movie_data.keys())[:4]}")
        
        result = []
        for idx, rec in enumerate(recommendations):
            rec_title = rec.get('title') or rec['title'] if isinstance(rec, dict) else rec['title']
            rec_id = rec.get('id')
            print(f"[DEBUG] Rec {idx+1}: '{rec_title}' (id={rec_id})")
            
            row = None
            if rec_id and str(rec_id) in movie_data:
                row = movie_data[str(rec_id)]
                print(f"[DEBUG]   By ID")
            elif rec_id and str(float(rec_id)) in movie_data:
                row = movie_data[str(float(rec_id))]
                print(f"[DEBUG]   By float ID")
            elif rec_title in movie_data:
                row = movie_data[rec_title]
                print(f"[DEBUG]   By title")
            else:
                print(f"[DEBUG]   NOT found")
                result.append({
                    "title": rec_title,
                    "scores": {
                        "genre_sim": float(rec.get('genre_sim', 0)),
                        "cast_sim": float(rec.get('cast_sim', 0)),
                        "franchise_sim": float(rec.get('franchise_sim', 0)),
                        "user_rating_norm": float(rec.get('user_rating_norm', 0)),
                        "hybrid_score": float(rec.get('hybrid_score', 0))
                    }
                })
                continue
            
            parsed = {
                "title": rec_title,
                "genres": row[0].split('|') if len(row) > 0 and row[0] else [],
                "id": float(row[1]) if len(row) > 1 and row[1] else 0,
                "overview": row[2] if len(row) > 2 else "",
                "production_companies": row[3].split('|') if len(row) > 3 and row[3] else [],
                "cast_and_crew": row[5].split(',') if len(row) > 5 and row[5] else [],
                "avg_rating": float(row[6]) if len(row) > 6 and row[6] else 0,
                "rating_count": float(row[7]) if len(row) > 7 and row[7] else 0,
                "scores": {
                    "genre_sim": float(rec.get('genre_sim', 0)),
                    "cast_sim": float(rec.get('cast_sim', 0)),
                    "franchise_sim": float(rec.get('franchise_sim', 0)),
                    "user_rating_norm": float(rec.get('user_rating_norm', 0)),
                    "hybrid_score": float(rec.get('hybrid_score', 0))
                }
            }
            result.append(parsed)
        
        print(f"[DEBUG] Returning {len(result)} recommendations")
        return jsonify({
            "total_recommendations": len(result),
            "recommendation_set_id": rec_set_id,
            "model_status": {
                "needs_revalidation": revalidation_status['needs_revalidation'],
                "current_accuracy": round(revalidation_status['accuracy'], 3),
                "status_message": revalidation_status['recommendation']
            },
            "recommendations": result
        })
        
    except Exception as e:
        print(f"[DEBUG] Error in getRecommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/getLastWatchedRecommendations")
def get_last_watched_recommendations():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if not MODEL_READY:
        return jsonify({"error": "Model not initialized"}), 500
    
    try:
        import csv
        
        print(f"[DEBUG] Fetching top 10 recommendations from model...")
        recommendations = model.get_recommendations_for_last_added(session['user_id'], top_n=10)
        print(f"[DEBUG] Received {len(recommendations)} recommendations")
        
        if not recommendations:
            print("[DEBUG] No recommendations returned from model")
            return jsonify({"error": "No recommendations found"}), 404
        
        # Save recommendations for later validation
        rec_set_id = save_recommendation_set(session['user_id'], recommendations, "last_added")
        
        # Check if model needs revalidation
        revalidation_status = check_for_model_revalidation(session['user_id'])
        
        print(f"[DEBUG] Loading CSV from: {CSV_PATH}")
        movie_data = {}
        
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) > 1:
                    movie_id = row[1].strip()  # ID is at index 1
                    title = row[4].strip()  # Title is at index 4
                    movie_data[movie_id] = row
                    movie_data[title] = row
                    if len(movie_data) <= 10:
                        print(f"[DEBUG] Added: id='{movie_id}', title='{title}'")
        
        print(f"[DEBUG] Loaded {len(movie_data)} movies")
        print(f"[DEBUG] Sample keys: {list(movie_data.keys())[:4]}")
        
        result = []
        for idx, rec in enumerate(recommendations):
            rec_title = rec.get('title') or rec['title'] if isinstance(rec, dict) else rec['title']
            rec_id = rec.get('id')
            print(f"[DEBUG] Rec {idx+1}: '{rec_title}' (id={rec_id})")
            
            row = None
            if rec_id and str(rec_id) in movie_data:
                row = movie_data[str(rec_id)]
                print(f"[DEBUG]   By ID")
            elif rec_id and str(float(rec_id)) in movie_data:
                row = movie_data[str(float(rec_id))]
                print(f"[DEBUG]   By float ID")
            elif rec_title in movie_data:
                row = movie_data[rec_title]
                print(f"[DEBUG]   By title")
            else:
                print(f"[DEBUG]   NOT found")
                result.append({
                    "title": rec_title,
                    "scores": {
                        "genre_sim": float(rec.get('genre_sim', 0)),
                        "cast_sim": float(rec.get('cast_sim', 0)),
                        "franchise_sim": float(rec.get('franchise_sim', 0)),
                        "user_rating_norm": float(rec.get('user_rating_norm', 0)),
                        "hybrid_score": float(rec.get('hybrid_score', 0))
                    }
                })
                continue
            
            parsed = {
                "title": rec_title,
                "genres": row[0].split('|') if len(row) > 0 and row[0] else [],
                "id": float(row[1]) if len(row) > 1 and row[1] else 0,
                "overview": row[2] if len(row) > 2 else "",
                "production_companies": row[3].split('|') if len(row) > 3 and row[3] else [],
                "cast_and_crew": row[5].split(',') if len(row) > 5 and row[5] else [],
                "avg_rating": float(row[6]) if len(row) > 6 and row[6] else 0,
                "rating_count": float(row[7]) if len(row) > 7 and row[7] else 0,
                "scores": {
                    "genre_sim": float(rec.get('genre_sim', 0)),
                    "cast_sim": float(rec.get('cast_sim', 0)),
                    "franchise_sim": float(rec.get('franchise_sim', 0)),
                    "user_rating_norm": float(rec.get('user_rating_norm', 0)),
                    "hybrid_score": float(rec.get('hybrid_score', 0))
                }
            }
            result.append(parsed)
        
        print(f"[DEBUG] Returning {len(result)} recommendations")
        return jsonify({
            "total_recommendations": len(result),
            "recommendation_set_id": rec_set_id,
            "model_status": {
                "needs_revalidation": revalidation_status['needs_revalidation'],
                "current_accuracy": round(revalidation_status['accuracy'], 3),
                "status_message": revalidation_status['recommendation']
            },
            "recommendations": result
        })
        
    except Exception as e:
        print(f"[DEBUG] Error in getRecommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/getMostCommonGenreRecommendations")
def get_most_common_genre_recommendations():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if not MODEL_READY:
        return jsonify({"error": "Model not initialized"}), 500

    try:
        import csv

        print("[DEBUG] Fetching most-common-genre recommendations...")
        recommendations = model.get_recommendations_by_most_common_genre(session['user_id'], top_n=10)
        print(f"[DEBUG] Received {len(recommendations)} recommendations")

        if not recommendations:
            print("[DEBUG] No recommendations returned from model")
            return jsonify({"error": "No recommendations found"}), 404

        # Save recommendations for later validation
        rec_set_id = save_recommendation_set(session['user_id'], recommendations, "genre_based")
        
        # Check if model needs revalidation
        revalidation_status = check_for_model_revalidation(session['user_id'])

        print(f"[DEBUG] Loading CSV from: {CSV_PATH}")

        movie_data = {}
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) > 1:
                    movie_id = row[1].strip()  # ID is at index 1
                    title = row[4].strip()  # Title is at index 4
                    movie_data[movie_id] = row
                    movie_data[title] = row
                    if len(movie_data) <= 10:
                        print(f"[DEBUG] Added: id='{movie_id}', title='{title}'")

        print(f"[DEBUG] Loaded {len(movie_data)} movies")

        result = []
        for idx, rec in enumerate(recommendations):
            title = rec.get("title")
            rec_id = rec.get("id")
            print(f"[DEBUG] Rec {idx+1}: '{title}' (id={rec_id})")

            row = None
            if rec_id and str(rec_id) in movie_data:
                row = movie_data[str(rec_id)]
                print("[DEBUG]   By ID")
            elif rec_id and str(float(rec_id)) in movie_data:
                row = movie_data[str(float(rec_id))]
                print("[DEBUG]   By float ID")
            elif title in movie_data:
                row = movie_data[title]
                print("[DEBUG]   By title")
            else:
                print("[DEBUG]   NOT found")
                result.append({
                    "title": title,
                    "scores": {
                        "genre_match": float(rec.get("genre_match", 0)),
                        "score": float(rec.get("score", 0))
                    }
                })
                continue

            parsed = {
                "title": title,
                "adult": False,
                "genres": row[0].split("|") if len(row) > 0 and row[0] else [],
                "id": float(row[1]) if len(row) > 1 and row[1] else 0,
                "overview": row[2] if len(row) > 2 else "",
                "production_companies": row[3].split("|") if len(row) > 3 and row[3] else [],
                "cast_and_crew": row[5].split(",") if len(row) > 5 and row[5] else [],
                "avg_rating": float(row[6]) if len(row) > 6 and row[6] else 0,
                "rating_count": float(row[7]) if len(row) > 7 and row[7] else 0,
                "scores": {
                    "genre_match": float(rec.get("genre_match", 0)),
                    "score": float(rec.get("score", 0))
                }
            }

            result.append(parsed)

        print(f"[DEBUG] Returning {len(result)} recommendations")

        return jsonify({
            "total_recommendations": len(result),
            "recommendation_set_id": rec_set_id,
            "model_status": {
                "needs_revalidation": revalidation_status['needs_revalidation'],
                "current_accuracy": round(revalidation_status['accuracy'], 3),
                "status_message": revalidation_status['recommendation']
            },
            "recommendations": result
        })

    except Exception as e:
        print(f"[DEBUG] Error in getMostCommonGenreRecommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/getMostCommonGenre", methods=["GET"])
def get_most_common_genre():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        conn = sqlite3.connect("movies.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT genres FROM movies WHERE user_id = ? AND genres IS NOT NULL AND genres != ''", (session['user_id'],))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return jsonify({"error": "No genres found"}), 404

        genre_counts = {}
        for row in rows:
            genre_str = row["genres"]
            for g in genre_str.split("|"):
                g = g.strip()
                if g:
                    genre_counts[g] = genre_counts.get(g, 0) + 1

        if not genre_counts:
            return jsonify({"error": "No valid genres found"}), 404

        most_common = max(genre_counts, key=genre_counts.get)

        return jsonify({
            "most_common_genre": most_common,
            "count": genre_counts[most_common]
        })

    except Exception as e:
        print("Error in getMostCommonGenre:", e)
        return jsonify({"error": str(e)}), 500

def create_movies_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id REAL,
        title TEXT,
        adult BOOLEAN,
        genres TEXT,
        overview TEXT,
        production_companies TEXT,
        cast_and_crew TEXT,
        rating_count INTEGER,
        userRating INTEGER,
        poster TEXT,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (id, user_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
    print("Movies table created or already exists.")


def create_recommendations_tracking_tables():
    """
    Create tables for tracking recommendation quality and model performance.
    
    Tables:
    - recommendation_sets: Stores batches of recommendations generated for users
    - recommendation_quality: Tracks accuracy of recommendations based on user ratings
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Table to store recommendation batches
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recommendation_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        recommendation_type TEXT NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_valid BOOLEAN DEFAULT 1,
        validation_timestamp TIMESTAMP,
        revalidation_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Drop and recreate recommendation_set_items if it exists (to fix NOT NULL constraint)
    cur.execute("DROP TABLE IF EXISTS recommendation_set_items")
    
    # Table to store individual recommendations and their outcomes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recommendation_quality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recommendation_set_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        movie_id REAL NOT NULL,
        movie_title TEXT,
        predicted_score REAL,
        actual_rating INTEGER,
        quality_score REAL,
        was_correct BOOLEAN,
        checked_at TIMESTAMP,
        FOREIGN KEY (recommendation_set_id) REFERENCES recommendation_sets(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (movie_id, user_id) REFERENCES movies(id, user_id) ON DELETE CASCADE
    )
    """)

    # Table to store recommendation set contents for reference
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recommendation_set_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recommendation_set_id INTEGER NOT NULL,
        movie_id REAL,
        movie_title TEXT,
        predicted_score REAL,
        rank_position INTEGER,
        FOREIGN KEY (recommendation_set_id) REFERENCES recommendation_sets(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
    print("Recommendation tracking tables created or already exist.")

@app.route("/api/model-performance", methods=["GET"])
def get_model_performance():
    """Get model performance metrics for current user"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        metrics = get_model_performance_metrics(session['user_id'])
        return jsonify({
            "success": True,
            "metrics": {
                "total_recommendations": metrics['total_recommendations'],
                "total_validated": metrics['total_validated'],
                "accuracy_rate": round(metrics['accuracy_rate'], 3),
                "avg_quality_score": round(metrics['avg_quality_score'], 3),
                "recommendations_by_type": metrics['recommendations_by_type'],
                "top_performing_type": metrics['top_performing_type']
            }
        })
    except Exception as e:
        print(f"Error getting model performance: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/revalidation-status", methods=["GET"])
def get_revalidation_status():
    """Check if model needs revalidation for current user"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        status = check_for_model_revalidation(session['user_id'])
        return jsonify({
            "success": True,
            "status": {
                "needs_revalidation": status['needs_revalidation'],
                "accuracy": round(status['accuracy'], 3),
                "correct_predictions": status['correct_count'],
                "total_validated": status['total_validated'],
                "avg_error": round(status['avg_error'], 3),
                "recommendation": status['recommendation']
            }
        })
    except Exception as e:
        print(f"Error getting revalidation status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/model-versions", methods=["GET"])
def get_model_versions():
    """Get all model versions and their status"""
    try:
        stats = get_model_stats()
        return jsonify({
            "success": True,
            "versions": stats['versions'],
            "total_versions": stats['total_versions'],
            "active_version": stats['active_version']
        })
    except Exception as e:
        print(f"Error getting model versions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/retrain", methods=["POST"])
def trigger_retraining():
    """Trigger model retraining with weighted data"""
    try:
        # Check if retraining is needed
        needs_retrain, accuracy = should_retrain(accuracy_threshold=0.5)
        
        if not needs_retrain:
            return jsonify({
                "success": False,
                "message": f"Model accuracy {accuracy:.2%} is acceptable, no retraining needed"
            }), 400
        
        # Get weighted training data
        current_version = get_active_model_version()
        weights_data = create_weighted_training_data(days_back=30, min_samples=5)
        
        if not weights_data:
            return jsonify({
                "success": False,
                "message": "Insufficient data for retraining"
            }), 400
        
        # Create new version
        new_version = create_model_version(
            current_version,
            weights_data,
            reason="manual_retraining_trigger"
        )
        
        # Evaluate it
        metrics = evaluate_model_version(new_version)
        
        return jsonify({
            "success": True,
            "new_version": new_version,
            "parent_version": current_version,
            "current_accuracy": round(accuracy, 3),
            "new_accuracy": round(metrics['accuracy'], 3) if metrics else None,
            "improvement": round(metrics['accuracy'] - accuracy, 3) if metrics else None,
            "training_samples": weights_data['total_predictions']
        })
    
    except Exception as e:
        print(f"Error triggering retraining: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/activate-version/<version_id>", methods=["POST"])
def activate_version(version_id):
    """Activate a specific model version"""
    try:
        activate_model_version(version_id)
        return jsonify({
            "success": True,
            "message": f"Version {version_id} is now active"
        })
    except Exception as e:
        print(f"Error activating version: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/retrain-status", methods=["GET"])
def get_retrain_status():
    """Get retraining status and recommendations"""
    try:
        needs_retrain, accuracy = should_retrain(accuracy_threshold=0.5)
        
        return jsonify({
            "success": True,
            "needs_retraining": needs_retrain,
            "current_accuracy": round(accuracy, 3),
            "accuracy_threshold": 0.5,
            "recommendation": "Retrain model with weighted data" if needs_retrain else "Model performing well"
        })
    except Exception as e:
        print(f"Error getting retrain status: {e}")
        return jsonify({"error": str(e)}), 500
        return jsonify({"error": str(e)}), 500

# ========================
# Run server
# ========================
if __name__ == '__main__':
    create_movies_table()
    create_users_table()
    create_recommendations_tracking_tables()
    init_model_versioning()

    app.run(debug=True, host='0.0.0.0')