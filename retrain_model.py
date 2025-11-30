#!/usr/bin/env python3
"""
Model Retraining Orchestration Script

Automated script to:
1. Check if retraining is needed
2. Create weighted training data
3. Retrain the model
4. Evaluate new version
5. Run A/B tests if needed
6. Activate best version
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("ModelRetraining")

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model_versioning import (
    get_active_model_version,
    should_retrain,
    create_weighted_training_data,
    create_model_version,
    evaluate_model_version,
    activate_model_version,
    start_ab_test,
    evaluate_ab_test,
    get_model_stats
)

DB_PATH = "movies.db"


def check_retraining_trigger(force=False, accuracy_threshold=0.5):
    """Check if retraining should be triggered."""
    if force:
        logger.info("FORCE: Retraining triggered by user request")
        return True
    
    needs_retrain, accuracy = should_retrain(accuracy_threshold=accuracy_threshold)
    
    if needs_retrain:
        logger.warning(f"TRIGGER: Accuracy {accuracy:.2%} below threshold {accuracy_threshold:.2%}")
        return True
    
    logger.info(f"OK: Accuracy {accuracy:.2%} is acceptable (threshold: {accuracy_threshold:.2%})")
    return False


def prepare_training_data(days_back=30, min_samples=5):
    """Prepare weighted training data."""
    logger.info(f"Preparing training data (last {days_back} days, min {min_samples} samples per movie)...")
    
    weights_data = create_weighted_training_data(days_back=days_back, min_samples=min_samples)
    
    if not weights_data:
        logger.error("Failed to prepare training data")
        return None
    
    logger.info(f"Training data prepared: {weights_data['sample_count']} movies, {weights_data['total_predictions']} predictions")
    return weights_data


def retrain_model(current_version, weights_data):
    """Create and evaluate new model version."""
    logger.info(f"Creating new model version from {current_version}...")
    
    new_version = create_model_version(
        current_version,
        weights_data,
        reason="automated_retraining"
    )
    
    logger.info(f"Evaluating new version {new_version}...")
    metrics = evaluate_model_version(new_version)
    
    if not metrics:
        logger.error("Failed to evaluate new version")
        return None
    
    logger.info(f"New version metrics:")
    logger.info(f"  Accuracy: {metrics['accuracy']:.2%}")
    logger.info(f"  Avg Error: {metrics['avg_error']:.3f}")
    logger.info(f"  Correct: {metrics['correct_predictions']}/{metrics['total_predictions']}")
    
    return new_version, metrics


def compare_versions(current_version, new_version):
    """Compare metrics between current and new version."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT test_accuracy FROM model_versions WHERE version_id = ?
    """, (current_version,))
    current_acc = cursor.fetchone()
    
    cursor.execute("""
        SELECT test_accuracy FROM model_versions WHERE version_id = ?
    """, (new_version,))
    new_acc = cursor.fetchone()
    
    conn.close()
    
    current_accuracy = current_acc[0] if current_acc and current_acc[0] else 0
    new_accuracy = new_acc[0] if new_acc and new_acc[0] else 0
    
    improvement = new_accuracy - current_accuracy
    
    logger.info(f"Version Comparison:")
    logger.info(f"  Current ({current_version}): {current_accuracy:.2%}")
    logger.info(f"  New ({new_version}): {new_accuracy:.2%}")
    logger.info(f"  Improvement: {improvement:+.2%}")
    
    return improvement > 0, improvement


def activate_best_version(current_version, new_version, improvement):
    """Decide which version to activate."""
    if improvement > 0.05:  # >5% improvement
        logger.info(f"Significant improvement ({improvement:+.2%}), activating new version {new_version}")
        activate_model_version(new_version, deactivate_previous=True)
        return new_version
    elif improvement > 0:
        logger.info(f"Small improvement ({improvement:+.2%}), but not activating yet")
        logger.info("Recommendation: Run A/B test before activation")
        return current_version
    else:
        logger.warning(f"New version is worse ({improvement:.2%}), keeping current version")
        return current_version


def print_model_stats():
    """Print current model statistics."""
    stats = get_model_stats()
    
    logger.info("=" * 60)
    logger.info("MODEL VERSION STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Total versions: {stats['total_versions']}")
    logger.info(f"Active version: {stats['active_version']}")
    logger.info("\nVersion History:")
    
    for v in stats['versions'][:5]:  # Show last 5
        logger.info(f"  {v['version_id']}")
        logger.info(f"    Status: {v['status']}")
        logger.info(f"    Accuracy: {v['test_accuracy']:.2% if v['test_accuracy'] else 'N/A'}")
        logger.info(f"    Samples: {v['training_samples']}")
        logger.info(f"    Created: {v['created_at']}")
        if v['retrain_trigger']:
            logger.info(f"    Trigger: {v['retrain_trigger']}")


def main():
    parser = argparse.ArgumentParser(description="Model Retraining Orchestration")
    parser.add_argument("--force", action="store_true", help="Force retraining regardless of accuracy")
    parser.add_argument("--days", type=int, default=30, help="Days of data to use for retraining")
    parser.add_argument("--threshold", type=float, default=0.5, help="Accuracy threshold for retraining")
    parser.add_argument("--min-samples", type=int, default=5, help="Minimum samples per movie")
    parser.add_argument("--stats", action="store_true", help="Just show model statistics")
    parser.add_argument("--dry-run", action="store_true", help="Don't activate new version, just prepare")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("MODEL RETRAINING ORCHESTRATION")
    logger.info("=" * 60)
    
    # Show stats
    if args.stats or args.dry_run:
        print_model_stats()
        if args.stats:
            return 0
    
    try:
        # Step 1: Check if retraining needed
        if not check_retraining_trigger(
            force=args.force,
            accuracy_threshold=args.threshold
        ):
            if not args.force:
                return 0
        
        # Step 2: Get current version
        current_version = get_active_model_version()
        logger.info(f"Current active version: {current_version}")
        
        # Step 3: Prepare training data
        weights_data = prepare_training_data(
            days_back=args.days,
            min_samples=args.min_samples
        )
        
        if not weights_data:
            logger.error("No training data available")
            return 1
        
        # Step 4: Retrain
        result = retrain_model(current_version, weights_data)
        if not result:
            logger.error("Model retraining failed")
            return 1
        
        new_version, metrics = result
        
        # Step 5: Compare versions
        is_better, improvement = compare_versions(current_version, new_version)
        
        # Step 6: Decide activation
        if args.dry_run:
            logger.info("DRY RUN: Not activating new version")
            print_model_stats()
        else:
            active_version = activate_best_version(current_version, new_version, improvement)
            logger.info(f"Active version: {active_version}")
        
        logger.info("=" * 60)
        logger.info("RETRAINING COMPLETE")
        logger.info("=" * 60)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during retraining: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
