"""
Model Versioning and Weighted Retraining System

Handles model versioning, weighted retraining based on recommendation quality,
and A/B testing between model versions.
"""

import json
import pickle
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model storage directory
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

DB_PATH = "movies.db"


def init_model_versioning():
    """Initialize model versioning tables in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Model versions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_versions (
            id INTEGER PRIMARY KEY,
            version_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            training_samples INTEGER,
            avg_accuracy REAL,
            test_accuracy REAL,
            active_until TIMESTAMP,
            parent_version_id TEXT,
            retrain_trigger TEXT
        )
    """)
    
    # A/B test results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ab_tests (
            id INTEGER PRIMARY KEY,
            test_id TEXT UNIQUE NOT NULL,
            version_a_id TEXT NOT NULL,
            version_b_id TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            status TEXT NOT NULL,
            winner_id TEXT,
            confidence_score REAL,
            FOREIGN KEY (version_a_id) REFERENCES model_versions(version_id),
            FOREIGN KEY (version_b_id) REFERENCES model_versions(version_id)
        )
    """)
    
    # Model performance log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_performance_log (
            id INTEGER PRIMARY KEY,
            version_id TEXT NOT NULL,
            user_id TEXT,
            prediction_score REAL,
            actual_rating REAL,
            error REAL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES model_versions(version_id)
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("[VERSIONING] Initialized model versioning tables")


def get_active_model_version():
    """Get the currently active model version."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT version_id FROM model_versions 
        WHERE status = 'active' 
        AND (active_until IS NULL OR active_until > CURRENT_TIMESTAMP)
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return "v1_initial"  # Fallback to initial model


def create_weighted_training_data(user_id=None, days_back=30, min_samples=5):
    """
    Extract weighted training data from recommendation_quality table.
    
    Args:
        user_id: Specific user (None for all users)
        days_back: Only use data from last N days
        min_samples: Minimum recommendations per movie to include
    
    Returns:
        Dict with weighted training data
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT 
            movie_id,
            title,
            predicted_score,
            actual_rating,
            was_correct,
            ABS(predicted_score - actual_rating) as error,
            checked_at
        FROM recommendation_quality
        WHERE checked_at > datetime('now', '-' || ? || ' days')
    """
    
    params = [days_back]
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    query += " ORDER BY checked_at DESC"
    
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        logger.warning(f"[RETRAINING] No training data found (user={user_id}, days={days_back})")
        return None
    
    # Group by movie and calculate weights
    movie_stats = {}
    for movie_id, title, pred_score, actual_rating, was_correct, error, checked_at in records:
        if movie_id not in movie_stats:
            movie_stats[movie_id] = {
                "title": title,
                "predictions": [],
                "accuracy": 0,
                "weight": 1.0
            }
        
        movie_stats[movie_id]["predictions"].append({
            "predicted": pred_score,
            "actual": actual_rating,
            "correct": was_correct,
            "error": error,
            "timestamp": checked_at
        })
    
    # Filter by minimum samples
    movie_stats = {
        mid: stats for mid, stats in movie_stats.items()
        if len(stats["predictions"]) >= min_samples
    }
    
    if not movie_stats:
        logger.warning(f"[RETRAINING] Insufficient samples after filtering (min={min_samples})")
        return None
    
    # Calculate per-movie accuracy and assign weights
    for movie_id, stats in movie_stats.items():
        correct = sum(1 for p in stats["predictions"] if p["correct"])
        stats["accuracy"] = correct / len(stats["predictions"])
        
        # Weight: higher for recent, higher accuracy, exponential boost for very accurate
        # Ensure minimum weight even for low accuracy
        recency_weight = 1.0  # Could be enhanced with time decay
        accuracy_weight = (stats["accuracy"] ** 2) + 0.1  # Exponential boost + minimum baseline
        
        stats["weight"] = recency_weight * accuracy_weight
        stats["sample_count"] = len(stats["predictions"])
    
    logger.info(f"[RETRAINING] Generated weighted data: {len(movie_stats)} movies, {len(records)} predictions")
    
    return {
        "movie_stats": movie_stats,
        "total_predictions": len(records),
        "sample_count": len(movie_stats),
        "generated_at": datetime.now().isoformat()
    }


def create_model_version(base_version, weights_data, reason="automatic_retraining"):
    """
    Create a new model version with weighted training.
    
    Args:
        base_version: Version ID to base this on
        weights_data: Output from create_weighted_training_data()
        reason: Why this retraining was triggered
    
    Returns:
        Version ID of new model
    """
    import uuid
    version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Record new version
    cursor.execute("""
        INSERT INTO model_versions 
        (version_id, status, training_samples, parent_version_id, retrain_trigger)
        VALUES (?, ?, ?, ?, ?)
    """, (
        version_id,
        "training",
        weights_data["total_predictions"],
        base_version,
        reason
    ))
    
    conn.commit()
    conn.close()
    
    logger.info(f"[VERSIONING] Created new model version: {version_id} (parent: {base_version})")
    
    return version_id


def evaluate_model_version(version_id, test_data=None, test_ratio=0.2):
    """
    Evaluate a model version's accuracy.
    
    Args:
        version_id: Model version to evaluate
        test_data: Optional test data (if None, uses recent data)
        test_ratio: Ratio of data to use for testing
    
    Returns:
        Accuracy metrics dict
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if test_data is None:
        # Use recent validation data
        cursor.execute("""
            SELECT 
                predicted_score,
                actual_rating,
                ABS(predicted_score - actual_rating) as error
            FROM recommendation_quality
            WHERE checked_at > datetime('now', '-7 days')
            ORDER BY RANDOM()
            LIMIT ?
        """, (int(100 / test_ratio),))  # Get enough for test set
        
        test_records = cursor.fetchall()
    else:
        test_records = test_data
    
    if not test_records:
        logger.warning(f"[EVALUATION] No test data for version {version_id}")
        return None
    
    # Calculate metrics
    errors = [abs(pred - actual) for pred, actual, _ in test_records]
    correct = sum(1 for error in errors if error <= 0.2)  # Threshold for "correct"
    
    accuracy = correct / len(test_records)
    avg_error = sum(errors) / len(errors)
    
    metrics = {
        "accuracy": accuracy,
        "avg_error": avg_error,
        "correct_predictions": correct,
        "total_predictions": len(test_records)
    }
    
    # Update version with metrics
    cursor.execute("""
        UPDATE model_versions 
        SET test_accuracy = ?, status = 'ready'
        WHERE version_id = ?
    """, (accuracy, version_id))
    
    conn.commit()
    conn.close()
    
    logger.info(f"[EVALUATION] Version {version_id}: {accuracy:.2%} accuracy ({avg_error:.3f} avg error)")
    
    return metrics


def activate_model_version(version_id, deactivate_previous=True):
    """
    Activate a model version for production use.
    
    Args:
        version_id: Version to activate
        deactivate_previous: Whether to deactivate the previous version
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if deactivate_previous:
        # Deactivate all previous versions
        cursor.execute("""
            UPDATE model_versions 
            SET status = 'inactive'
            WHERE status = 'active'
        """)
    
    # Activate new version
    cursor.execute("""
        UPDATE model_versions 
        SET status = 'active', active_until = datetime('now', '+30 days')
        WHERE version_id = ?
    """, (version_id,))
    
    conn.commit()
    conn.close()
    
    logger.info(f"[ACTIVATION] Model version {version_id} is now active")


def start_ab_test(version_a, version_b, duration_hours=24):
    """
    Start an A/B test between two model versions.
    
    Args:
        version_a: First version to test
        version_b: Second version to test
        duration_hours: How long to run the test
    
    Returns:
        Test ID
    """
    test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO ab_tests 
        (test_id, version_a_id, version_b_id, status)
        VALUES (?, ?, ?, ?)
    """, (test_id, version_a, version_b, "running"))
    
    conn.commit()
    conn.close()
    
    logger.info(f"[A/B TEST] Started test {test_id}: {version_a} vs {version_b} ({duration_hours}h)")
    
    return test_id


def evaluate_ab_test(test_id):
    """
    Evaluate an A/B test and determine winner.
    
    Returns:
        Results dict with winner and confidence
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get test info
    cursor.execute("""
        SELECT version_a_id, version_b_id FROM ab_tests WHERE test_id = ?
    """, (test_id,))
    
    test_info = cursor.fetchone()
    if not test_info:
        logger.error(f"[A/B TEST] Test {test_id} not found")
        return None
    
    version_a, version_b = test_info
    
    # Get accuracy for each version from recent predictions
    for version_id in [version_a, version_b]:
        cursor.execute("""
            SELECT test_accuracy FROM model_versions WHERE version_id = ?
        """, (version_id,))
        
        result = cursor.fetchone()
        if version_id == version_a:
            acc_a = result[0] if result else 0
        else:
            acc_b = result[0] if result else 0
    
    winner_id = version_a if acc_a > acc_b else version_b
    confidence = max(acc_a, acc_b)
    
    # Record results
    cursor.execute("""
        UPDATE ab_tests 
        SET status = 'completed', winner_id = ?, confidence_score = ?, ended_at = CURRENT_TIMESTAMP
        WHERE test_id = ?
    """, (winner_id, confidence, test_id))
    
    conn.commit()
    conn.close()
    
    logger.info(f"[A/B TEST] Test {test_id} complete: {winner_id} wins with {confidence:.2%} confidence")
    
    return {
        "test_id": test_id,
        "version_a": version_a,
        "version_b": version_b,
        "winner": winner_id,
        "confidence": confidence,
        "accuracy_a": acc_a,
        "accuracy_b": acc_b
    }


def should_retrain(user_id=None, accuracy_threshold=0.65):
    """
    Determine if model should be retrained based on accuracy.
    
    Args:
        user_id: Check specific user (None for all)
        accuracy_threshold: If accuracy below this, retrain (default 0.65 = 65%)
    
    Returns:
        (should_retrain, current_accuracy)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct
        FROM recommendation_quality
        WHERE checked_at > datetime('now', '-7 days')
    """
    
    if user_id:
        query += " AND user_id = ?"
        cursor.execute(query, (user_id,))
    else:
        cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    
    if not result or result[0] == 0:
        return False, 0
    
    total, correct = result
    accuracy = correct / total if total > 0 else 0
    
    should_retrain = accuracy < accuracy_threshold
    
    if should_retrain:
        logger.warning(f"[RETRAINING TRIGGER] Accuracy {accuracy:.2%} below threshold {accuracy_threshold:.2%}")
    
    return should_retrain, accuracy


def get_model_stats():
    """Get statistics about all model versions."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            version_id,
            status,
            created_at,
            training_samples,
            test_accuracy,
            retrain_trigger
        FROM model_versions
        ORDER BY created_at DESC
    """)
    
    versions = cursor.fetchall()
    conn.close()
    
    stats = {
        "versions": [
            {
                "version_id": v[0],
                "status": v[1],
                "created_at": v[2],
                "training_samples": v[3],
                "test_accuracy": v[4],
                "retrain_trigger": v[5]
            }
            for v in versions
        ],
        "total_versions": len(versions),
        "active_version": next((v[0] for v in versions if v[1] == "active"), None)
    }
    
    return stats
