"""
Feedback Reinforcement Model Module

This module integrates negative feedback (dislikes) into the recommendation model
to continuously improve recommendation quality through reinforcement learning.

Implements:
- Negative reward propagation through recommendation features
- Feature importance adjustment based on dislike patterns
- Training data weighting using dislike history
- Model retraining triggering based on feedback accumulation
"""

import sqlite3
from typing import List, Dict, Tuple, Optional
import os
from datetime import datetime, timedelta
import json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "movies.db")

# Constants for feedback reinforcement
DISLIKE_WEIGHT_MULTIPLIER = 0.8  # How strongly dislikes affect model
FEEDBACK_ACCUMULATION_THRESHOLD = 20  # Retrain when this many new dislikes recorded
GENRE_DEEMPHASIS_FACTOR = 0.15  # Reduce genre importance by this % per dislike
CAST_DEEMPHASIS_FACTOR = 0.10
FRANCHISE_DEEMPHASIS_FACTOR = 0.12


def apply_dislike_to_training_data(user_id: int, movie_id: Optional[int],
                                   movie_title: str,
                                   predicted_score: float) -> Dict:
    """
    Convert a dislike into negative training data for model reinforcement.
    
    Creates an inverse training example where the model made a poor prediction.
    This is used to adjust feature weights and improve future recommendations.
    
    Args:
        user_id (int): User who disliked
        movie_id (int, optional): Movie ID
        movie_title (str): Movie title
        predicted_score (float): Score the model predicted (0.0-1.0)
        
    Returns:
        Dict: Negative training example with feature adjustments
    """
    try:
        # Create negative training record
        negative_training = {
            'user_id': user_id,
            'movie_id': movie_id,
            'movie_title': movie_title,
            'actual_rating': 0.0,  # User effectively "rated" as 0 by disliking
            'predicted_rating': predicted_score,
            'error': abs(predicted_score - 0.0),  # Prediction error
            'is_negative_feedback': True,
            'weight': DISLIKE_WEIGHT_MULTIPLIER,
            'created_at': datetime.now().isoformat()
        }
        
        # Store in database for future model training
        _save_negative_training_example(negative_training)
        
        return negative_training
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to create negative training data: {e}")
        return {}


def _save_negative_training_example(example: Dict) -> bool:
    """
    Persist negative training example to database for model retraining.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS negative_training_examples (
                example_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER,
                movie_title TEXT,
                actual_rating REAL,
                predicted_rating REAL,
                error REAL,
                weight REAL DEFAULT 0.8,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_in_training INTEGER DEFAULT 0
            )
        """)
        
        cur.execute("""
            INSERT INTO negative_training_examples
            (user_id, movie_id, movie_title, actual_rating, predicted_rating,
             error, weight, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (example['user_id'], example['movie_id'], example['movie_title'],
              example['actual_rating'], example['predicted_rating'],
              example['error'], example['weight'], example['created_at']))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to save negative training example: {e}")
        return False
    finally:
        conn.close()


def calculate_feature_adjustment_from_dislike(movie_metadata: Dict,
                                             reason: str = "not_interested") -> Dict:
    """
    Determine which recommendation features should be de-emphasized based on dislike reason.
    
    Args:
        movie_metadata (Dict): Movie info (genres, cast, franchise, etc.)
        reason (str): Why the movie was disliked
        
    Returns:
        Dict: Feature adjustments to apply
    """
    adjustments = {
        'genre_adjustments': {},
        'cast_adjustments': {},
        'franchise_adjustment': 0.0,
        'reason': reason
    }
    
    try:
        # Parse reason and apply appropriate adjustments
        if reason == "wrong_genre":
            # De-emphasize this movie's genres
            if 'genres' in movie_metadata:
                for genre in movie_metadata['genres']:
                    adjustments['genre_adjustments'][genre] = -GENRE_DEEMPHASIS_FACTOR
        
        elif reason == "poor_quality":
            # Reduce cast and director importance for this movie's cast
            if 'cast' in movie_metadata:
                for actor in movie_metadata['cast'][:5]:  # Top 5 cast
                    adjustments['cast_adjustments'][actor] = -CAST_DEEMPHASIS_FACTOR
        
        elif reason == "already_watched":
            # Flag this movie to not be recommended again
            adjustments['should_filter'] = True
        
        elif reason == "not_interested":
            # Light adjustment to genre and cast
            if 'genres' in movie_metadata:
                for genre in movie_metadata['genres']:
                    adjustments['genre_adjustments'][genre] = -GENRE_DEEMPHASIS_FACTOR * 0.5
        
        return adjustments
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to calculate feature adjustments: {e}")
        return adjustments


def get_untrained_negative_feedback_count() -> int:
    """
    Get count of negative feedback examples not yet used in model training.
    
    Returns:
        int: Count of unused negative training examples
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT COUNT(*) as count
            FROM negative_training_examples
            WHERE used_in_training = 0
        """)
        
        result = cur.fetchone()
        return result[0] if result else 0
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to count untrained feedback: {e}")
        return 0
    finally:
        conn.close()


def should_retrain_from_feedback() -> bool:
    """
    Determine if model should be retrained based on feedback accumulation.
    
    Returns:
        bool: True if enough negative feedback has accumulated to warrant retraining
    """
    untrained_count = get_untrained_negative_feedback_count()
    should_retrain = untrained_count >= FEEDBACK_ACCUMULATION_THRESHOLD
    
    if should_retrain:
        print(f"[REINFORCEMENT] Feedback threshold reached: "
              f"{untrained_count} untrained examples (threshold: {FEEDBACK_ACCUMULATION_THRESHOLD})")
    
    return should_retrain


def mark_negative_examples_as_used(example_ids: List[int]) -> bool:
    """
    Mark negative training examples as used after model retraining.
    
    Args:
        example_ids (List[int]): List of example IDs that were used
        
    Returns:
        bool: True if successful
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        for example_id in example_ids:
            cur.execute("""
                UPDATE negative_training_examples
                SET used_in_training = 1
                WHERE example_id = ?
            """, (example_id,))
        
        conn.commit()
        print(f"[REINFORCEMENT] Marked {len(example_ids)} examples as used in training")
        return True
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to mark examples as used: {e}")
        return False
    finally:
        conn.close()


def get_negative_training_batch(limit: int = 100) -> List[Dict]:
    """
    Retrieve a batch of unused negative training examples for model retraining.
    
    Args:
        limit (int): Maximum number of examples to retrieve
        
    Returns:
        List[Dict]: List of negative training examples
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT example_id, user_id, movie_id, movie_title,
                   actual_rating, predicted_rating, error, weight
            FROM negative_training_examples
            WHERE used_in_training = 0
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        examples = [dict(row) for row in cur.fetchall()]
        return examples
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to get negative training batch: {e}")
        return []
    finally:
        conn.close()


def apply_feature_adjustments(feature_config: Dict, adjustments: Dict) -> Dict:
    """
    Apply dislike-based feature adjustments to recommendation model configuration.
    
    Modifies feature importance weights based on accumulated dislike feedback.
    
    Args:
        feature_config (Dict): Current model feature configuration
        adjustments (Dict): Adjustments from dislike analysis
        
    Returns:
        Dict: Updated feature configuration
    """
    try:
        updated_config = feature_config.copy()
        
        # Apply genre adjustments
        if 'genre_adjustments' in adjustments:
            if 'genre_weights' not in updated_config:
                updated_config['genre_weights'] = {}
            
            for genre, adjustment in adjustments['genre_adjustments'].items():
                current_weight = updated_config['genre_weights'].get(genre, 1.0)
                updated_config['genre_weights'][genre] = max(0.1, current_weight + adjustment)
        
        # Apply cast adjustments
        if 'cast_adjustments' in adjustments:
            if 'cast_weights' not in updated_config:
                updated_config['cast_weights'] = {}
            
            for actor, adjustment in adjustments['cast_adjustments'].items():
                current_weight = updated_config['cast_weights'].get(actor, 1.0)
                updated_config['cast_weights'][actor] = max(0.1, current_weight + adjustment)
        
        # Apply franchise adjustment
        if 'franchise_adjustment' in adjustments:
            current_franchise = updated_config.get('franchise_weight', 1.0)
            updated_config['franchise_weight'] = max(0.1, 
                                                     current_franchise + adjustments['franchise_adjustment'])
        
        return updated_config
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to apply feature adjustments: {e}")
        return feature_config


def get_feedback_improvement_metrics() -> Dict:
    """
    Calculate metrics showing how well feedback is improving recommendations.
    
    Compares prediction accuracy before and after applying feedback.
    
    Returns:
        Dict: Improvement metrics
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Get average error in negative feedback examples
        cur.execute("""
            SELECT COUNT(*) as total_examples,
                   AVG(error) as avg_error,
                   MAX(error) as max_error,
                   MIN(error) as min_error
            FROM negative_training_examples
        """)
        
        result = cur.fetchone()
        if result:
            metrics = {
                'total_negative_examples': result[0],
                'avg_prediction_error': result[1],
                'max_error': result[2],
                'min_error': result[3],
                'average_dislike_predicted_score': None
            }
            
            # Calculate average predicted score for disliked movies
            cur.execute("""
                SELECT AVG(predicted_rating) as avg_predicted
                FROM negative_training_examples
            """)
            
            avg_result = cur.fetchone()
            if avg_result:
                metrics['average_dislike_predicted_score'] = avg_result[0]
            
            return metrics
        
        return {}
    except Exception as e:
        print(f"[REINFORCEMENT ERROR] Failed to get improvement metrics: {e}")
        return {}
    finally:
        conn.close()
