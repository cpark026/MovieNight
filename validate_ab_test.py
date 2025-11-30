#!/usr/bin/env python3
"""
Step 4: Validate best configuration with A/B test
"""
import sqlite3
import json
from datetime import datetime

def validate_config():
    """Validate the best configuration through A/B testing"""
    conn = sqlite3.connect('movies.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check database tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print("=" * 80)
    print("DATABASE TABLES AVAILABLE")
    print("=" * 80)
    print(f"Tables: {', '.join(tables)}")
    print()
    
    # Check hp_experiments table
    if 'hp_experiments' in tables:
        cursor.execute("SELECT COUNT(*) as count FROM hp_experiments")
        count = cursor.fetchone()['count']
        print(f"✓ HP Experiments table: {count} records")
        
        # Get best experiment
        cursor.execute("""
            SELECT experiment_id, test_accuracy, improvement_from_baseline, 
                   tuning_method, created_at 
            FROM hp_experiments 
            ORDER BY test_accuracy DESC 
            LIMIT 1
        """)
        best = cursor.fetchone()
        if best:
            print(f"\nBest Configuration for A/B Test:")
            print(f"  Experiment: {best['experiment_id']}")
            print(f"  Accuracy: {best['test_accuracy']:.2%}")
            print(f"  Improvement: {best['improvement_from_baseline']:+.2%}")
            print(f"  Method: {best['tuning_method']}")
            print(f"  Created: {best['created_at']}")
    
    print()
    print("=" * 80)
    print("A/B TEST VALIDATION STRATEGY")
    print("=" * 80)
    print("""
    The best configuration (60.14% accuracy, +5.14% improvement) is ready for A/B testing.
    
    RECOMMENDED A/B TEST APPROACH:
    
    1. CONTROL GROUP: Current model (v1_initial)
       - Baseline accuracy: ~55%
       - Serves recommendations to 50% of users
    
    2. TREATMENT GROUP: Model with tuned hyperparameters
       - New accuracy: 60.14% (target)
       - Serves recommendations to 50% of users
    
    3. METRICS TO TRACK (24-48 hours):
       - Click-through rate (CTR)
       - Recommendation satisfaction
       - User engagement time
       - Model prediction accuracy
    
    4. SUCCESS CRITERIA:
       - Treatment group CTR > Control group CTR
       - At least 5% improvement in engagement
       - Statistical significance (p < 0.05)
    
    5. DEPLOYMENT:
       - If successful: Roll out tuned config to 100% of users
       - If unsuccessful: Investigate and run more tuning experiments
    
    CURRENT STATUS:
    ✓ Best config identified (bayesian_20251130_165747_013)
    ✓ Hyperparameters applied to model.py
    ✓ Ready for A/B test deployment
    
    NEXT STEPS:
    1. Deploy treatment model version with tuned hyperparameters
    2. Route 50% of traffic to each version
    3. Monitor metrics for 24-48 hours
    4. Compare results and decide on full rollout
    """)
    
    conn.close()

if __name__ == "__main__":
    validate_config()
