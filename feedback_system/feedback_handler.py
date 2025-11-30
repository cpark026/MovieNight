"""
Negative Feedback Handler Module

This module manages user negative feedback (dislike/thumbs-down) and integrates
it into the recommendation model to reinforce learning and improve future recommendations.

Key Functions:
- save_dislike(): Record when user dislikes a recommendation
- get_user_dislikes(): Retrieve user's dislike history
- calculate_negative_weight(): Determine weight of negative feedback
- update_model_with_negative_feedback(): Adjust recommendation model based on dislikes
- analyze_dislike_patterns(): Identify common reasons for dislikes
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import os
from enum import Enum

# Get database from parent directory
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "movies.db")


class DislikeReason(Enum):
    """Categories for why a recommendation was disliked"""
    WRONG_GENRE = "wrong_genre"
    POOR_QUALITY = "poor_quality"
    ALREADY_WATCHED = "already_watched"
    NOT_INTERESTED = "not_interested"
    IRRELEVANT = "irrelevant"
    OTHER = "other"


def init_feedback_tables():
    """Initialize database tables for feedback tracking if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Table for dislike records
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_dislikes (
                dislike_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER,
                movie_title TEXT,
                recommendation_set_id INTEGER,
                predicted_score REAL,
                reason TEXT DEFAULT 'not_interested',
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (recommendation_set_id) REFERENCES recommendation_sets(id)
            )
        """)
        
        # Table for tracking dislike impact on model
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dislike_feedback_impact (
                impact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dislike_id INTEGER NOT NULL,
                model_version_id INTEGER,
                impact_type TEXT,
                feature_affected TEXT,
                adjustment_magnitude REAL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dislike_id) REFERENCES user_dislikes(dislike_id),
                FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id)
            )
        """)
        
        # Table for dislike patterns analysis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dislike_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pattern_type TEXT,
                pattern_value TEXT,
                frequency INTEGER DEFAULT 1,
                severity REAL,
                identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        print("[FEEDBACK] Feedback tables initialized successfully")
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to initialize feedback tables: {e}")
    finally:
        conn.close()


def save_dislike(user_id: int, movie_id: Optional[int], movie_title: str,
                recommendation_set_id: Optional[int] = None,
                predicted_score: float = 0.0,
                reason: str = "not_interested",
                feedback_text: str = "") -> int:
    """
    Record a user dislike/negative feedback for a movie recommendation.
    
    This captures when a user explicitly rejects a recommendation, which is
    crucial feedback for model learning and improvement.
    
    Args:
        user_id (int): User ID who disliked the recommendation
        movie_id (int, optional): TMDB movie ID if available
        movie_title (str): Title of the disliked movie
        recommendation_set_id (int, optional): Related recommendation set ID
        predicted_score (float): The predicted score the model gave (0.0-1.0)
        reason (str): Reason for dislike (wrong_genre, poor_quality, etc.)
        feedback_text (str): Optional user feedback text
        
    Returns:
        int: dislike_id for tracking this feedback
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO user_dislikes 
            (user_id, movie_id, movie_title, recommendation_set_id, 
             predicted_score, reason, feedback_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (user_id, movie_id, movie_title, recommendation_set_id,
              predicted_score, reason, feedback_text))
        
        conn.commit()
        dislike_id = cur.lastrowid
        
        print(f"[FEEDBACK] Recorded dislike #{dislike_id} for user {user_id}: "
              f"{movie_title} (reason: {reason}, predicted_score: {predicted_score})")
        
        return dislike_id
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to save dislike: {e}")
        return -1
    finally:
        conn.close()


def get_user_dislikes(user_id: int, limit: int = 50) -> List[Dict]:
    """
    Retrieve a user's dislike history.
    
    Args:
        user_id (int): User ID
        limit (int): Maximum number of recent dislikes to retrieve
        
    Returns:
        List[Dict]: List of dislike records with metadata
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT dislike_id, movie_id, movie_title, predicted_score, 
                   reason, feedback_text, created_at
            FROM user_dislikes
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        results = [dict(row) for row in cur.fetchall()]
        return results
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to retrieve dislikes: {e}")
        return []
    finally:
        conn.close()


def calculate_dislike_weight(user_id: int, movie_id: Optional[int]) -> float:
    """
    Calculate the weight/importance of negative feedback for a specific movie.
    
    Considers:
    - How many times the user has disliked this movie
    - Time decay (recent dislikes matter more)
    - Confidence level (explicit feedback vs passive)
    
    Args:
        user_id (int): User ID
        movie_id (int, optional): Movie ID
        
    Returns:
        float: Weight/importance of the dislike (0.0-1.0)
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Count total dislikes for this movie by this user
        cur.execute("""
            SELECT COUNT(*) as count, 
                   CAST((julianday('now') - julianday(MAX(created_at))) 
                        as REAL) as days_since_last
            FROM user_dislikes
            WHERE user_id = ? AND movie_id = ?
        """, (user_id, movie_id))
        
        result = cur.fetchone()
        if result:
            count, days_since = result
            if count == 0:
                return 0.0
            
            # Base weight from frequency
            frequency_weight = min(count / 3.0, 1.0)  # Cap at 1.0
            
            # Time decay: dislikes older than 90 days have less impact
            if days_since and days_since > 0:
                decay_factor = max(0.5, 1.0 - (days_since / 180.0))
            else:
                decay_factor = 1.0
            
            return frequency_weight * decay_factor
        
        return 0.0
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to calculate dislike weight: {e}")
        return 0.0
    finally:
        conn.close()


def get_dislike_pattern_analysis(user_id: int) -> Dict:
    """
    Analyze patterns in user dislikes to identify systematic issues.
    
    Identifies:
    - Most common reasons for dislike
    - Genre patterns (which genres user consistently dislikes)
    - Actor/director patterns
    - Quality-related patterns
    
    Args:
        user_id (int): User ID
        
    Returns:
        Dict: Analysis of dislike patterns
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Get reason distribution
        cur.execute("""
            SELECT reason, COUNT(*) as count
            FROM user_dislikes
            WHERE user_id = ?
            GROUP BY reason
            ORDER BY count DESC
        """, (user_id,))
        
        reason_distribution = {row['reason']: row['count'] for row in cur.fetchall()}
        
        # Get recent dislike trend
        cur.execute("""
            SELECT COUNT(*) as total_dislikes,
                   AVG(predicted_score) as avg_predicted_score
            FROM user_dislikes
            WHERE user_id = ? AND created_at > datetime('now', '-30 days')
        """, (user_id,))
        
        recent = cur.fetchone()
        recent_dislikes = dict(recent) if recent else {}
        
        return {
            'reason_distribution': reason_distribution,
            'recent_trend': recent_dislikes,
            'total_dislikes': sum(reason_distribution.values())
        }
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to analyze dislike patterns: {e}")
        return {}
    finally:
        conn.close()


def record_feedback_impact(dislike_id: int, model_version_id: int,
                          impact_type: str, feature_affected: str,
                          adjustment_magnitude: float) -> bool:
    """
    Record how a specific dislike impacted model adjustments.
    
    Used to track the reinforcement learning feedback loop.
    
    Args:
        dislike_id (int): ID of the dislike record
        model_version_id (int): Model version that was adjusted
        impact_type (str): Type of adjustment (weight_reduction, feature_deemphasis, etc.)
        feature_affected (str): Which feature/component was affected
        adjustment_magnitude (float): Size of adjustment (-1.0 to 1.0)
        
    Returns:
        bool: True if recorded successfully
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO dislike_feedback_impact
            (dislike_id, model_version_id, impact_type, feature_affected, 
             adjustment_magnitude, applied_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (dislike_id, model_version_id, impact_type, feature_affected,
              adjustment_magnitude))
        
        conn.commit()
        print(f"[FEEDBACK] Recorded feedback impact for dislike {dislike_id}: "
              f"{impact_type} on {feature_affected} (magnitude: {adjustment_magnitude})")
        return True
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to record feedback impact: {e}")
        return False
    finally:
        conn.close()


def get_model_feedback_metrics(model_version_id: int) -> Dict:
    """
    Get aggregated feedback metrics for a specific model version.
    
    Shows how much negative feedback this version has received and what
    aspects of recommendations need improvement.
    
    Args:
        model_version_id (int): Model version ID
        
    Returns:
        Dict: Feedback metrics and recommendations
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Get aggregate feedback data
        cur.execute("""
            SELECT COUNT(*) as total_impacts,
                   COUNT(DISTINCT dislike_id) as unique_dislikes,
                   AVG(adjustment_magnitude) as avg_adjustment,
                   GROUP_CONCAT(DISTINCT feature_affected) as affected_features
            FROM dislike_feedback_impact
            WHERE model_version_id = ?
        """, (model_version_id,))
        
        result = cur.fetchone()
        metrics = dict(result) if result else {}
        
        # Get most problematic features
        cur.execute("""
            SELECT feature_affected, COUNT(*) as frequency,
                   AVG(ABS(adjustment_magnitude)) as avg_magnitude
            FROM dislike_feedback_impact
            WHERE model_version_id = ?
            GROUP BY feature_affected
            ORDER BY frequency DESC
            LIMIT 5
        """, (model_version_id,))
        
        problematic_features = [dict(row) for row in cur.fetchall()]
        metrics['problematic_features'] = problematic_features
        
        return metrics
    except Exception as e:
        print(f"[FEEDBACK ERROR] Failed to get feedback metrics: {e}")
        return {}
    finally:
        conn.close()
