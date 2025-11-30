"""
HYPERPARAMETERS REFERENCE

Complete list of all hyperparameters currently set in the MovieNight recommendation system.
Last Updated: November 30, 2025
"""

# ==============================================================================
# RECOMMENDATION ENGINE HYPERPARAMETERS (model.py)
# ==============================================================================

RECOMMENDATION_ENGINE = {
    "Function": "get_top_recommendations()",
    "File": "model.py",
    
    "1. Recommendation Count": {
        "name": "top_n",
        "default_value": 10,
        "range": "1-100",
        "description": "Number of movies to recommend",
        "impact": "Higher = more recommendations, more computation",
        "location": "line 268"
    },
    
    "2. Cast Similarity Position Weights": {
        "name": "cast_position_weights",
        "values": {
            "lead_cast": {
                "positions": "0-5",
                "weight": 1.0,
                "description": "Main/lead actors"
            },
            "supporting_cast": {
                "positions": "5-15",
                "weight": 0.7,
                "description": "Supporting actors"
            },
            "background_cast": {
                "positions": "15+",
                "weight": 0.3,
                "description": "Background/minor actors"
            }
        },
        "impact": "Determines importance of each actor in cast similarity calculation",
        "location": "lines 367-396"
    },
    
    "3. Popularity Score Weighting": {
        "name": "popularity_component_weights",
        "rating_weight": 0.7,
        "count_weight": 0.3,
        "formula": "0.7 * rating_popularity + 0.3 * count_popularity",
        "description": "Balance between quality (avg_rating) and quantity (rating_count)",
        "impact": "Higher rating_weight = prioritize highly-rated movies",
        "location": "lines 427-428"
    },
    
    "4. Count Popularity Scaling": {
        "name": "count_popularity_scale",
        "formula": "log10(rating_count + 1) / 3.0",
        "description": "Logarithmic scaling for rating_count",
        "rationale": "Prevents blockbusters from dominating",
        "max_value": "When rating_count >> 1000000, approaches 2.0",
        "location": "line 427"
    },
    
    "5. Genre Confidence Boost/Penalty": {
        "name": "genre_boost_values",
        "high_confidence": {
            "threshold": "> 0.7",
            "boost": 0.15,
            "description": "70%+ genre overlap"
        },
        "medium_confidence": {
            "threshold": "> 0.5",
            "boost": 0.10,
            "description": "50-70% genre overlap"
        },
        "low_confidence": {
            "threshold": "< 0.3",
            "boost": -0.20,
            "description": "Less than 30% genre overlap"
        },
        "impact": "Dynamic adjustment to score based on confidence",
        "location": "lines 429-434"
    },
    
    "6. Hybrid Score Weights": {
        "name": "hybrid_score_formula",
        "formula": """
            0.40 * genre_sim +
            0.15 * cast_sim +
            0.05 * franchise_sim +
            0.30 * user_rating_norm +
            0.10 * popularity_score +
            genre_boost
        """,
        "weights": {
            "genre_similarity": 0.40,
            "cast_similarity": 0.15,
            "franchise_similarity": 0.05,
            "user_rating_norm": 0.30,
            "popularity_score": 0.10
        },
        "total": "1.00 + dynamic boost (-0.20 to +0.15)",
        "impact": "Most important parameter - controls recommendation balance",
        "history": {
            "original": {
                "genre": 0.45,
                "cast": 0.15,
                "franchise": 0.05,
                "user_rating": 0.35,
                "timestamp": "Pre-Phase-1"
            },
            "phase_1": {
                "genre": 0.40,
                "cast": 0.15,
                "franchise": 0.05,
                "user_rating": 0.30,
                "popularity": 0.10,
                "timestamp": "Post-Phase-1"
            }
        },
        "location": "lines 435-441"
    },
    
    "7. User Rating Normalization": {
        "name": "user_rating_weight",
        "formula": "userRating / 10.0",
        "range": "0.0 - 1.0 (assuming 10-point scale)",
        "description": "Normalizes user's average rating to [0, 1]",
        "impact": "Higher user ratings → higher recommendations for similar movies",
        "location": "line 324"
    }
}

# ==============================================================================
# MODEL VERSIONING HYPERPARAMETERS (model_versioning.py)
# ==============================================================================

MODEL_VERSIONING = {
    "Function": "should_retrain()",
    "File": "model_versioning.py",
    
    "1. Accuracy Threshold": {
        "name": "accuracy_threshold",
        "default_value": 0.65,
        "range": "0.0 - 1.0",
        "description": "Minimum accuracy required (65%)",
        "impact": "If accuracy < 65%, model is flagged for retraining",
        "location": "line 556 (default parameter)"
    }
}

# ==============================================================================
# RETRAINING SCRIPT HYPERPARAMETERS (retrain_model.py)
# ==============================================================================

RETRAINING_SCRIPT = {
    "1. Training Data Window": {
        "name": "days",
        "default_value": 30,
        "range": "1-365",
        "description": "How many days of historical data to use",
        "cli_argument": "--days",
        "impact": "More days = more training data but potentially stale",
        "location": "line 245"
    },
    
    "2. Retraining Threshold": {
        "name": "threshold",
        "default_value": 0.65,
        "range": "0.0 - 1.0",
        "description": "Accuracy threshold for triggering retraining",
        "cli_argument": "--threshold",
        "impact": "If accuracy falls below this, retraining triggered",
        "location": "line 246"
    },
    
    "3. Minimum Samples": {
        "name": "min_samples",
        "default_value": 5,
        "range": "1-100",
        "description": "Minimum recommendations per movie to include in training",
        "cli_argument": "--min-samples",
        "impact": "Filters out movies with insufficient data",
        "location": "line 247"
    }
}

# ==============================================================================
# RECOMMENDATION QUALITY HYPERPARAMETERS (recommendation_tracker.py)
# ==============================================================================

RECOMMENDATION_TRACKER = {
    "1. Accuracy Definition": {
        "name": "accuracy_threshold_for_correctness",
        "formula": "error <= 0.2",
        "description": "A prediction is 'correct' if error is within 0.2 (±0.2 rating)",
        "example": "Predicted 7.5, Actual 7.3 → correct (error 0.2)",
        "location": "recommendation_tracker.py"
    },
    
    "2. Revalidation Window": {
        "name": "rolling_window_days",
        "default_value": 30,
        "description": "Consider last 30 days of recommendations for validation",
        "impact": "Focuses on recent model performance",
        "location": "recommendation_tracker.py"
    },
    
    "3. Revalidation Threshold": {
        "name": "revalidation_accuracy_threshold",
        "default_value": 0.50,
        "description": "If accuracy < 50%, recommend model revalidation",
        "impact": "Conservative threshold for flagging concerns",
        "location": "recommendation_tracker.py"
    }
}

# ==============================================================================
# SPARK CONFIGURATION HYPERPARAMETERS (model.py)
# ==============================================================================

SPARK_CONFIG = {
    "1. Master": {
        "name": "spark.master",
        "value": "local[*]",
        "description": "Use all available CPU cores",
        "impact": "Parallel processing on all cores",
        "location": "line 252"
    },
    
    "2. Shuffle Partitions": {
        "name": "spark.sql.shuffle.partitions",
        "value": 4,
        "description": "Number of partitions for shuffle operations",
        "impact": "Lower = faster for small datasets",
        "location": "line 254"
    },
    
    "3. Driver Host": {
        "name": "spark.driver.host",
        "value": "127.0.0.1",
        "description": "Bind to localhost",
        "impact": "Ensures stability",
        "location": "line 255"
    },
    
    "4. Driver Bind Address": {
        "name": "spark.driver.bindAddress",
        "value": "127.0.0.1",
        "description": "Where to listen for connections",
        "impact": "Local communication only",
        "location": "line 256"
    }
}

# ==============================================================================
# A/B TESTING HYPERPARAMETERS (model_versioning.py)
# ==============================================================================

AB_TESTING = {
    "1. A/B Test Duration": {
        "name": "duration_hours",
        "default_value": 24,
        "range": "1-168 (1 week)",
        "description": "How long to run A/B test",
        "cli_argument": "--duration-hours (not yet exposed)",
        "impact": "Longer = more statistical power",
        "location": "model_versioning.py:start_ab_test()"
    }
}

# ==============================================================================
# WEIGHTED TRAINING HYPERPARAMETERS (model_versioning.py)
# ==============================================================================

WEIGHTED_TRAINING = {
    "1. Recency Weight": {
        "name": "recency_weight",
        "value": 1.0,
        "description": "Currently uniform, no time decay",
        "future_improvement": "Could add exponential decay for older data",
        "location": "model_versioning.py:create_weighted_training_data()"
    },
    
    "2. Accuracy Weight": {
        "name": "accuracy_weight_exponent",
        "formula": "accuracy ** 2",
        "description": "Exponential boost for highly accurate movies",
        "example": "80% accuracy = 0.64, 50% accuracy = 0.25",
        "impact": "Emphasizes proven good recommendations",
        "location": "model_versioning.py line ~140"
    },
    
    "3. Minimum Baseline Weight": {
        "name": "minimum_baseline",
        "value": 0.1,
        "description": "Minimum weight even for 0% accuracy",
        "impact": "Ensures all data points considered",
        "location": "model_versioning.py line ~141"
    }
}

# ==============================================================================
# SUMMARY TABLE
# ==============================================================================

CRITICAL_HYPERPARAMETERS = """
┌─────────────────────────────────────────────────────────────────────────────┐
│ MOST IMPORTANT HYPERPARAMETERS (Highest Impact on Accuracy)                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Hybrid Score Weights (Genre 40%, Cast 15%, Franchise 5%, Rating 30%,    │
│    Popularity 10%) - CRITICAL for balance                                   │
│                                                                               │
│ 2. Genre Confidence Boost (+15%, +10%, -20%) - Dynamic adjustment signal   │
│                                                                               │
│ 3. Cast Position Weights (1.0/0.7/0.3) - Lead vs supporting importance    │
│                                                                               │
│ 4. Popularity Weighting (0.7/0.3 rating/count) - Movie quality source      │
│                                                                               │
│ 5. Accuracy Threshold (65%) - Retraining trigger                           │
└─────────────────────────────────────────────────────────────────────────────┘
"""

# ==============================================================================
# HOW TO ADJUST HYPERPARAMETERS
# ==============================================================================

TUNING_GUIDE = """
TO ADJUST HYBRID SCORE WEIGHTS:
1. Edit model.py line 435-441
2. Change values for each component
3. Ensure they sum to approximately 1.0 + dynamic boost
4. Run test_model_versioning.py to verify
5. Create new model version to test

TO ADJUST CAST POSITION WEIGHTS:
1. Edit model.py line 372-374 (comments) and line 383 (code)
2. Change threshold values (5, 15) or weight values (1.0, 0.7, 0.3)
3. Run tests
4. Deploy

TO ADJUST ACCURACY THRESHOLD:
1. Edit model_versioning.py line 556 (default parameter)
2. Edit retrain_model.py line 246 (CLI default)
3. Edit test_model_versioning.py line 407 (test assertion)
4. Run tests

TO ADJUST GENRE BOOST:
1. Edit model.py lines 429-434
2. Change thresholds (0.7, 0.5, 0.3) or boost values (0.15, 0.10, -0.20)
3. Run tests
4. Deploy

EXAMPLE - INCREASE GENRE WEIGHT:
- Change line 435 from: 0.40 * col("genre_sim")
- To: 0.45 * col("genre_sim")
- Reduce another weight to compensate (e.g., rating from 0.30 to 0.25)
"""

# ==============================================================================
# CURRENT CONFIGURATION SNAPSHOT
# ==============================================================================

CURRENT_CONFIG = """
NOVEMBER 30, 2025 - PHASE 1 OPTIMIZATION

RECOMMENDATION SCORING:
├─ Hybrid Score Formula:
│  ├─ Genre Similarity: 40%
│  ├─ Cast Similarity: 15% (with position weighting)
│  ├─ Franchise Similarity: 5%
│  ├─ User Rating Norm: 30%
│  ├─ Popularity Score: 10%
│  └─ Genre Boost: +15% / +10% / -20% (conditional)
│
├─ Cast Position Weights:
│  ├─ Lead (0-5): 1.0
│  ├─ Supporting (5-15): 0.7
│  └─ Background (15+): 0.3
│
├─ Popularity Weighting:
│  ├─ Rating Quality: 70%
│  └─ Count Quantity: 30%
│
└─ Genre Confidence Thresholds:
   ├─ High (>0.7): +15% boost
   ├─ Medium (>0.5): +10% boost
   └─ Low (<0.3): -20% penalty

MODEL MANAGEMENT:
├─ Accuracy Threshold: 65%
├─ Retraining Window: 30 days
├─ Minimum Samples: 5
└─ A/B Test Duration: 24 hours

SPARK:
├─ Master: local[*] (all cores)
├─ Shuffle Partitions: 4
├─ Driver: 127.0.0.1
└─ Binding: 127.0.0.1

RECOMMENDATION DEFAULTS:
├─ Top N: 10 movies
└─ Accuracy for 'correct': error <= 0.2
"""

if __name__ == "__main__":
    print(CURRENT_CONFIG)
