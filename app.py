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

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Add the app directory to path for model imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize model once at startup
try:
    import model
    MODEL_READY = True
except Exception as e:
    print(f"Warning: Could not initialize model: {e}")
    MODEL_READY = False

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

def create_users_table(db_path="movies.db"):
    """Create users table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
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
        conn.close()
        return jsonify({"success": True})
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
        
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.csv")
        print(f"[DEBUG] Loading CSV from: {csv_path}")
        movie_data = {}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
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
        
        print("[DEBUG] Fetching top 10 recommendations from model...")
        recommendations = model.get_recommendations_for_last_added(session['user_id'], top_n=10)
        print(f"[DEBUG] Received {len(recommendations)} recommendations")
        
        if not recommendations:
            print("[DEBUG] No recommendations returned from model")
            return jsonify({"error": "No recommendations found"}), 404
        
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.csv")
        print(f"[DEBUG] Loading CSV from: {csv_path}")
        movie_data = {}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
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

        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.csv")
        print(f"[DEBUG] Loading CSV from: {csv_path}")

        movie_data = {}
        with open(csv_path, "r", encoding="utf-8") as f:
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

def create_movies_table(db_path="movies.db"):
    conn = sqlite3.connect(db_path)
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

# ========================
# Run server
# ========================
if __name__ == '__main__':
    create_movies_table()
    create_users_table()

    app.run(debug=True, host='0.0.0.0')