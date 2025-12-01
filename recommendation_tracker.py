"""
Recommendation Quality Tracking Module

This module manages the tracking and validation of movie recommendations.
It stores recommendation sets, monitors their accuracy, and triggers model
revalidation when performance degrades.

Key Functions:
- save_recommendation_set(): Store generated recommendations for a user
- validate_recommendations(): Check if recommendations were accurate
- calculate_quality_score(): Assess recommendation accuracy
- check_for_revalidation(): Determine if model needs retraining
- get_model_performance(): Retrieve model accuracy metrics
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "movies.db")


def save_recommendation_set(user_id: int, recommendations: List[Dict], 
                           recommendation_type: str = "general") -> int:
    """
    Save a set of recommendations for a user for later validation.
    
    Stores the recommendations in the database with predicted scores so we can
    later compare against actual user ratings when they watch/rate movies.
    
    Args:
        user_id (int): User ID
        recommendations (list): List of recommendation dicts from model with:
            - title: Movie title
            - hybrid_score: Predicted recommendation score [0.0, 1.0]
            - scores: Dict with genre_sim, cast_sim, franchise_sim, user_rating_norm
            - genres, overview, production_companies, cast_and_crew, etc.
        recommendation_type (str): Type of recommendation (general, last_added, genre_based)
        
    Returns:
        int: recommendation_set_id for later tracking
    """
    import json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        print(f"[TRACKER] Saving {len(recommendations)} recommendations for user {user_id} (type: {recommendation_type})")
        
        # Insert recommendation set record
        cur.execute("""
            INSERT INTO recommendation_sets (user_id, recommendation_type, generated_at, is_valid)
            VALUES (?, ?, CURRENT_TIMESTAMP, 1)
        """, (user_id, recommendation_type))
        
        recommendation_set_id = cur.lastrowid
        print(f"[TRACKER] Created recommendation_set_id: {recommendation_set_id}")
        
        # Store individual recommendation items
        for rank, rec in enumerate(recommendations, 1):
            predicted_score = rec.get('hybrid_score', rec.get('score', 0.0))
            movie_title = rec.get('title', 'Unknown')
            movie_id = rec.get('id', None)
            
            # Try to convert movie_id to int if it's a float
            if movie_id is not None:
                try:
                    movie_id = int(float(movie_id))
                except (ValueError, TypeError):
                    pass
            
            print(f"[TRACKER]   Rank {rank}: '{movie_title}' (id: {movie_id}, score: {predicted_score})")
            
            # Serialize full recommendation data as JSON for later retrieval
            full_data_json = json.dumps(rec)
            
            cur.execute("""
                INSERT INTO recommendation_set_items 
                (recommendation_set_id, movie_id, movie_title, predicted_score, rank_position, full_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (recommendation_set_id, movie_id, movie_title, predicted_score, rank, full_data_json))
        
        conn.commit()
        print(f"[TRACKER] ✓ Successfully saved recommendation set {recommendation_set_id}")
        return recommendation_set_id
        
    except Exception as e:
        print(f"[TRACKER] ✗ Error saving recommendation set: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return -1
    finally:
        conn.close()


def validate_recommendation_against_rating(user_id: int, movie_id: float, 
                                           movie_title: str, user_rating: int) -> Dict:
    """
    Validate a recommendation when user rates a movie.
    
    Called when user rates a new movie. Checks if this movie was in any recent
    recommendation sets and calculates how accurate the prediction was.
    
    Args:
        user_id (int): User ID
        movie_id (float): Movie ID from database
        movie_title (str): Movie title
        user_rating (int): User's rating (0-10)
        
    Returns:
        dict: Validation result with:
            - was_in_recommendations: Whether movie was recommended
            - recommendation_set_id: Which recommendation set (if any)
            - predicted_score: What model predicted
            - actual_rating: User's actual rating (normalized to 0-1)
            - quality_score: Accuracy metric
            - is_accurate: Boolean if prediction was good
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    result = {
        'was_in_recommendations': False,
        'recommendation_set_id': None,
        'predicted_score': 0.0,
        'actual_rating': user_rating / 10.0,
        'quality_score': 0.0,
        'is_accurate': False
    }
    
    try:
        # Normalize movie title for better matching
        normalized_title = movie_title.strip().lower()
        
        print(f"[VALIDATION] Looking for movie: '{movie_title}' (normalized: '{normalized_title}')")
        
        # First, let's see what's in the database
        cur.execute("""
            SELECT COUNT(*) as count FROM recommendation_set_items
        """)
        total_items = cur.fetchone()[0]
        print(f"[VALIDATION] Total items in database: {total_items}")
        
        # Show recent recommendations for this user
        cur.execute("""
            SELECT rs.id, rs.recommendation_type, rsi.movie_title, rsi.predicted_score
            FROM recommendation_set_items rsi
            JOIN recommendation_sets rs ON rsi.recommendation_set_id = rs.id
            WHERE rs.user_id = ?
            AND rs.generated_at > datetime('now', '-30 days')
            LIMIT 20
        """, (user_id,))
        
        recent_recs = cur.fetchall()
        if recent_recs:
            print(f"[VALIDATION] Recent recommendations for user {user_id}:")
            for row in recent_recs:
                print(f"[VALIDATION]   - '{row[2]}' ({row[1]}, score: {row[3]})")
        else:
            print(f"[VALIDATION] No recent recommendations found for user {user_id}")
        
        # Look for this movie in recent recommendation sets - try exact match first
        cur.execute("""
            SELECT rsi.*, rs.id as set_id, rs.recommendation_type
            FROM recommendation_set_items rsi
            JOIN recommendation_sets rs ON rsi.recommendation_set_id = rs.id
            WHERE rs.user_id = ? AND LOWER(rsi.movie_title) = ?
            AND rs.is_valid = 1
            AND rs.generated_at > datetime('now', '-30 days')
            ORDER BY rsi.rank_position ASC
            LIMIT 1
        """, (user_id, normalized_title))
        
        recommendation = cur.fetchone()
        
        if not recommendation:
            print(f"[VALIDATION] No exact match found. Trying partial match...")
            # Try partial match if exact doesn't work
            cur.execute("""
                SELECT rsi.*, rs.id as set_id, rs.recommendation_type
                FROM recommendation_set_items rsi
                JOIN recommendation_sets rs ON rsi.recommendation_set_id = rs.id
                WHERE rs.user_id = ? AND (
                    LOWER(rsi.movie_title) LIKE ? OR
                    LOWER(?) LIKE ('%' || LOWER(rsi.movie_title) || '%')
                )
                AND rs.is_valid = 1
                AND rs.generated_at > datetime('now', '-30 days')
                ORDER BY rsi.rank_position ASC
                LIMIT 1
            """, (user_id, f'%{normalized_title}%', normalized_title))
            
            recommendation = cur.fetchone()
        
        if recommendation:
            print(f"[VALIDATION] ✓ Found in recommendations!")
            result['was_in_recommendations'] = True
            result['recommendation_set_id'] = recommendation['set_id']
            predicted_score = recommendation['predicted_score']
            result['predicted_score'] = predicted_score
            
            # Calculate quality score: how close prediction was to actual rating
            actual_rating_norm = user_rating / 10.0
            error = abs(predicted_score - actual_rating_norm)
            quality_score = max(0.0, 1.0 - error)  # 0-1 scale, higher is better
            result['quality_score'] = quality_score
            
            # Consider recommendation "accurate" if within 0.2 (2 points on 10-scale)
            result['is_accurate'] = error <= 0.2
            
            print(f"[VALIDATION] Predicted: {predicted_score:.2f}, Actual: {actual_rating_norm:.2f}, Quality: {quality_score:.3f}")
            
            # Record the validation
            cur.execute("""
                INSERT INTO recommendation_quality
                (recommendation_set_id, user_id, movie_id, movie_title, predicted_score,
                 actual_rating, quality_score, was_correct, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (recommendation['set_id'], user_id, movie_id, movie_title, 
                  predicted_score, user_rating, quality_score, result['is_accurate']))
            
            conn.commit()
        else:
            print(f"[VALIDATION] ✗ Movie NOT in recent recommendations - recording as external")
            # Still record it - use set_id of 0 to indicate it wasn't recommended
            cur.execute("""
                INSERT INTO recommendation_quality
                (recommendation_set_id, user_id, movie_id, movie_title, predicted_score,
                 actual_rating, quality_score, was_correct, checked_at)
                VALUES (0, ?, ?, ?, 0.0, ?, 0.0, 0, CURRENT_TIMESTAMP)
            """, (user_id, movie_id, movie_title, user_rating))
            
            conn.commit()
        
        return result
        
    except Exception as e:
        print(f"Error validating recommendation: {e}")
        import traceback
        traceback.print_exc()
        return result
    finally:
        conn.close()


def check_for_model_revalidation(user_id: int, threshold: float = 0.5) -> Dict:
    """
    Check if the model needs revalidation for a user based on recent accuracy.
    
    Analyzes recent recommendations and their outcomes. If accuracy falls below
    threshold, suggests model retraining.
    
    Args:
        user_id (int): User ID
        threshold (float): Quality score threshold (0-1) to trigger revalidation
        
    Returns:
        dict: Revalidation assessment with:
            - needs_revalidation: Boolean
            - accuracy: Average quality score of recent recommendations
            - correct_count: Number of accurate recommendations
            - total_validated: Total recommendations that were validated
            - avg_error: Average prediction error
            - recommendation: What action to take
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    result = {
        'needs_revalidation': False,
        'accuracy': 0.0,
        'correct_count': 0,
        'total_validated': 0,
        'avg_error': 0.0,
        'recommendation': 'Model performing well'
    }
    
    try:
        # Get recent validated recommendations
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct,
                AVG(quality_score) as avg_quality,
                AVG(ABS(predicted_score - (actual_rating))) as avg_error
            FROM recommendation_quality
            WHERE user_id = ?
            AND checked_at > datetime('now', '-30 days')
        """, (user_id,))
        
        stats = cur.fetchone()
        
        if stats and stats['total'] and stats['total'] > 5:
            result['total_validated'] = stats['total']
            result['correct_count'] = stats['correct']
            result['accuracy'] = stats['avg_quality']
            result['avg_error'] = stats['avg_error']
            
            if result['accuracy'] < threshold:
                result['needs_revalidation'] = True
                result['recommendation'] = (
                    f"Model accuracy ({result['accuracy']:.1%}) below threshold ({threshold:.1%}). "
                    f"Recommend retraining with weighted emphasis on recent high-error predictions."
                )
        
        return result
        
    except Exception as e:
        print(f"Error checking revalidation: {e}")
        return result
    finally:
        conn.close()


def get_model_performance_metrics(user_id: int = None) -> Dict:
    """
    Get overall model performance metrics for a user or all users.
    
    Args:
        user_id (int, optional): If provided, get metrics for specific user.
                                 If None, get global metrics.
        
    Returns:
        dict: Performance metrics including:
            - total_recommendations: Total recommendations generated
            - total_validated: How many were checked against actual ratings
            - accuracy_rate: Percentage of accurate predictions
            - avg_quality_score: Average quality score [0-1]
            - recommendations_by_type: Breakdown by recommendation type
            - top_performing_genre: Most accurate recommendation category
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    result = {
        'total_recommendations': 0,
        'total_validated': 0,
        'accuracy_rate': 0.0,
        'avg_quality_score': 0.0,
        'recommendations_by_type': {},
        'top_performing_type': None
    }
    
    try:
        # Total recommendations
        user_filter = "WHERE user_id = ?" if user_id else ""
        params = [user_id] if user_id else []
        
        cur.execute(f"""
            SELECT COUNT(*) as count FROM recommendation_sets
            {user_filter}
        """, params)
        result['total_recommendations'] = cur.fetchone()['count']
        
        # Validated recommendations
        cur.execute(f"""
            SELECT COUNT(*) as count FROM recommendation_quality
            {user_filter}
        """, params)
        result['total_validated'] = cur.fetchone()['count']
        
        # Accuracy metrics
        cur.execute(f"""
            SELECT 
                AVG(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as accuracy,
                AVG(quality_score) as avg_quality
            FROM recommendation_quality
            {user_filter}
        """, params)
        
        metrics = cur.fetchone()
        if metrics['accuracy']:
            result['accuracy_rate'] = metrics['accuracy']
            result['avg_quality_score'] = metrics['avg_quality']
        
        # Performance by recommendation type
        cur.execute(f"""
            SELECT 
                rs.recommendation_type,
                COUNT(rq.id) as validated_count,
                AVG(CASE WHEN rq.was_correct = 1 THEN 1 ELSE 0 END) as type_accuracy,
                AVG(rq.quality_score) as type_quality
            FROM recommendation_sets rs
            LEFT JOIN recommendation_quality rq ON rs.id = rq.recommendation_set_id
            {user_filter}
            GROUP BY rs.recommendation_type
        """, params)
        
        for row in cur.fetchall():
            result['recommendations_by_type'][row['recommendation_type']] = {
                'count': row['validated_count'],
                'accuracy': row['type_accuracy'],
                'avg_quality': row['type_quality']
            }
            
            if result['top_performing_type'] is None and row['type_accuracy']:
                result['top_performing_type'] = row['recommendation_type']
        
        return result
        
    except Exception as e:
        print(f"Error getting performance metrics: {e}")
        return result
    finally:
        conn.close()


def invalidate_old_recommendations(user_id: int, days: int = 30) -> int:
    """
    Mark old recommendation sets as invalid to focus on recent model performance.
    
    Args:
        user_id (int): User ID
        days (int): Age threshold in days
        
    Returns:
        int: Number of recommendation sets invalidated
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE recommendation_sets
            SET is_valid = 0
            WHERE user_id = ?
            AND generated_at < datetime('now', ? || ' days')
        """, (user_id, f'-{days}'))
        
        conn.commit()
        return cur.rowcount
        
    except Exception as e:
        print(f"Error invalidating old recommendations: {e}")
        return 0
    finally:
        conn.close()


def get_cached_recommendations(user_id: int, limit: int = 10) -> Dict[str, List]:
    """
    Retrieve the most recent cached recommendations for a user with full movie details.
    
    Returns recommendations exactly as the model generated them, including all scores
    and metadata. These were previously saved in the recommendation_set_items.full_data column.
    
    Args:
        user_id (int): User ID
        limit (int): Max recommendations to return per category
        
    Returns:
        Dict with keys:
            - general: Most recent general recommendations
            - last_added: Most recent last_added recommendations
            - genre_based: Most recent genre_based recommendations
            Each contains full recommendation objects matching the model output format
    """
    import json
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    result = {
        "general": [],
        "last_added": [],
        "genre_based": []
    }
    
    try:
        # For each recommendation type, get the most recent set
        for rec_type in ["general", "last_added", "genre_based"]:
            print(f"[CACHE] Fetching {rec_type} recommendations for user {user_id}")
            
            # Get the most recent recommendation set for this type
            cur.execute("""
                SELECT rs.id as set_id
                FROM recommendation_sets rs
                WHERE rs.user_id = ? 
                AND rs.recommendation_type = ?
                AND rs.is_valid = 1
                ORDER BY rs.generated_at DESC
                LIMIT 1
            """, (user_id, rec_type))
            
            recent_set = cur.fetchone()
            if not recent_set:
                print(f"[CACHE] No {rec_type} recommendation set found for user {user_id}")
                continue
            
            set_id = recent_set['set_id']
            
            # Get all items from this set
            cur.execute("""
                SELECT rsi.movie_title, rsi.full_data, rsi.rank_position
                FROM recommendation_set_items rsi
                WHERE rsi.recommendation_set_id = ?
                ORDER BY rsi.rank_position ASC
                LIMIT ?
            """, (set_id, limit))
            
            items = cur.fetchall()
            print(f"[CACHE] Found {len(items)} items for {rec_type}")
            
            for item in items:
                # Use full_data if available (contains complete recommendation with scores)
                if item['full_data']:
                    try:
                        rec_obj = json.loads(item['full_data'])
                        print(f"[CACHE]   ✓ Loaded full data for: {item['movie_title']}")
                        result[rec_type].append(rec_obj)
                    except json.JSONDecodeError as e:
                        print(f"[CACHE]   ✗ Failed to parse full_data JSON for {item['movie_title']}: {e}")
                        # Fallback: return basic info
                        result[rec_type].append({
                            "title": item['movie_title']
                        })
                else:
                    print(f"[CACHE]   ⚠ No full_data available for: {item['movie_title']}")
                    # Fallback: return basic info
                    result[rec_type].append({
                        "title": item['movie_title']
                    })
        
        print(f"[CACHE] Retrieved {sum(len(v) for v in result.values())} cached recommendations for user {user_id}")
        return result
        
    except Exception as e:
        print(f"[CACHE] Error retrieving cached recommendations: {e}")
        import traceback
        traceback.print_exc()
        return result
    finally:
        conn.close()
