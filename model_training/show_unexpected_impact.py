#!/usr/bin/env python3
"""
Visual demonstration of how unexpected movies affect model training
(Text-only version for Windows console compatibility)
"""

def print_flowchart():
    print("\n" + "=" * 100)
    print("UNEXPECTED MOVIE IMPACT ON TRAINING - FLOWCHART".center(100))
    print("=" * 100)
    
    print("""
                          USER ADDS AN UNEXPECTED MOVIE
                                    |
                    Was it recently recommended? (<30 days)
                           /                  \\
                         YES                  NO
                         /                      \\
                  FOUND in                    NOT in
              recommendation                recommendation
                  table                    quality table
                    |                          |
                    v                          v
            Create validation         NO TRAINING IMPACT
            record (predicted          |
            vs actual rating)          Movie goes in DB
                    |                  System learns
                    v                  nothing about it
            Calculate error
            accuracy metrics
                 /      \\
            GOOD        BAD
            PRED        PREDICTION
             /             \\
            |               |
            v               v
        Accuracy      Error recorded
        stays high    in training data
        No retrain    (low weight)
                        |
                        v
                If errors accumulate
                & accuracy < 50%
                        |
                        v
                TRIGGERS RETRAINING
                
                * Collects training data
                  (30-day window)
                * Creates new model
                * Tests new vs old
                * If better: Auto-activates
                  or runs A/B test
    """)

def print_scenarios():
    print("\n" + "=" * 100)
    print("FOUR KEY SCENARIOS".center(100))
    print("=" * 100)
    
    print("""

SCENARIO 1: Recommended 5 Days Ago, You Hate It
===============================================
  Movie:         Action Movie - The Explosion
  Recommended:   YES (5 days ago, score: 0.75)
  Your Rating:   2/10 (You hate action movies!)
  In Training:   YES
  
  Impact:
  -------
    + Error recorded: 0.75 - 0.2 = 0.55 (huge!)
    + Low weight assigned to this movie
    + Accumulates with other errors
    + If 50%+ of recent recs are this bad -> Retraining triggered
    + Next model: Reduces action movie weight in recommendations
    + Result: System learns you don't like action films


SCENARIO 2: You Find Random Indie Film on Letterboxd
====================================================
  Movie:         Indie Drama - The Quiet Part
  Recommended:   NO (never in recommendations)
  Your Rating:   9/10 (Amazing!)
  In Training:   NO
  
  Impact:
  -------
    - No baseline prediction (wasn't recommended)
    - No training data created
    - Model learns nothing about why you liked it
    - But: Added to your movies table for future reference
    - System just moves on (no impact on hyperparameters)
    - Result: Zero impact on model training


SCENARIO 3: Recommended 45 Days Ago (Outside Window)
===================================================
  Movie:         Comedy - The Setup
  Recommended:   YES (but 45 days ago!)
  Your Rating:   8/10
  In Training:   NO (too old)
  
  Impact:
  -------
    - Recommendation too old (outside 30-day window)
    - Filtered out during training data preparation
    - System: "This data is stale, can't use it"
    - No impact on retraining decision
    - Result: Zero impact on model training


SCENARIO 4: Recommended, But You Haven't Rated It Yet
====================================================
  Movie:         Mystery - The Truth
  Recommended:   YES (3 days ago)
  Your Rating:   (Not yet rated)
  In Training:   NO
  
  Impact:
  -------
    - No validation check triggered
    - No rating means no prediction validation
    - Movie in database but no training data
    - Once you rate it -> Training impact enabled
    - Result: Zero impact until you rate it
    """)

def print_decision_tree():
    print("\n" + "=" * 100)
    print("QUICK DECISION TREE: DOES MY MOVIE AFFECT TRAINING?".center(100))
    print("=" * 100)
    
    print("""

START: You added a new movie to your list

1. Was this movie RECOMMENDED to you?
   |
   +-- NO  --> ANSWER: No impact on training
   |          (System can't learn from predictions it never made)
   |
   +-- YES --> Go to question 2


2. Was it recommended within the LAST 30 DAYS?
   |
   +-- NO  --> ANSWER: No impact on training
   |          (Too old, filtered out of training data)
   |
   +-- YES --> Go to question 3


3. Have you RATED it?
   |
   +-- NO  --> ANSWER: No impact yet
   |          (But will affect training once you rate it!)
   |
   +-- YES --> Go to question 4


4. Does your RATING match the PREDICTION?
   |
   +-- YES (or close)  --> Good prediction
   |                       System reinforces this behavior
   |
   +-- NO (big difference) --> Bad prediction
                               Error recorded
                               If errors accumulate:
                               - Accuracy drops
                               - Retraining triggered
                               - Model adjusts hyperparameters
    """)

def print_detailed_example():
    print("\n" + "=" * 100)
    print("DETAILED EXAMPLE: The Impact Chain".center(100))
    print("=" * 100)
    
    print("""

You add: "Indie Comedy - The Setup"
Rating: 2/10
You didn't find it, it was recommended to you 3 days ago

STEP 1: Movie Added (app.py line 246)
-------
  app.py validates_recommendation_against_rating()
  Checks: Was this in recent recommendations?
  Found: YES! In recommendation_sets table
  
  
STEP 2: Validation Recorded (recommendation_tracker.py)
-------
  Creates record in recommendation_quality table:
  
  | Field            | Value     |
  |------------------|-----------|
  | predicted_score  | 0.72      | (system predicted: 72% match)
  | actual_rating    | 0.2       | (you rated: 2/10 = 20%)
  | was_correct      | false     | (prediction was wrong)
  | error            | 0.52      | (huge miss!)
  | checked_at       | now       |


STEP 3: Accuracy Metrics Updated (recommendation_tracker.py line 264)
-------
  Over last 30 days:
  - 20 recommendations checked
  - 8 were accurate
  - Accuracy = 40% (BELOW 50% THRESHOLD!)
  
  Decision: needs_revalidation = TRUE


STEP 4: Retraining Triggered (retrain_model.py line 58)
-------
  should_retrain() returns: True
  
  Calls: prepare_training_data(days_back=30, min_samples=5)
  
  Loads from recommendation_quality:
  - Your 0.52 error is included
  - Weighted lower (because high error)
  - Other errors also included
  
  
STEP 5: New Model Version Created (model_versioning.py line 200)
-------
  Collects all errors from last 30 days
  Weights movies by accuracy
  
  Your movie gets: weight = 0.1 (high error -> low weight)
  Other accurate movies get: weight > 0.5 (low error -> high weight)
  
  Creates new model version with adjusted hyperparameters:
  
  OLD HYPERPARAMETERS    NEW HYPERPARAMETERS    REASON
  ==================     ===================    ======
  Genre Weight: 0.1466   Genre Weight: 0.1400   Your indie comedy wasn't
                                                well-matched by genre
  
  Cast Weight: 0.3201    Cast Weight: 0.3300    Cast matching was better
                                                predictor of your taste
  
  Rating Weight: 0.0946  Rating Weight: 0.0900  Movie ratings less
                                                predictive of your rating
  

STEP 6: Version Evaluation (model_versioning.py line 350)
-------
  Tests new model against test set
  
  Current model accuracy: 60.14%
  New model accuracy:     60.45%
  Improvement:            +0.31%
  
  Decision Tree:
  - Improvement > 5%? NO  -> Don't auto-activate
  - Improvement > 0%?  YES -> Run A/B test
  - Worse?              NO  -> Don't keep old one
  
  Result: Runs A/B test for next 24-48 hours


STEP 7: A/B Test (optional)
-------
  50% of recommendations use new model
  50% use old model (current: 60.14%)
  
  Track: Which group rates movies higher?
  
  If new model wins: Activate it (replace 60.14%)
  If old model wins: Keep using 60.14%
  

OUTCOME:
========
  Your single "unexpected" movie triggered:
  - Validation record
  - Accuracy check
  - Retraining decision
  - New model creation
  - A/B test
  
  System learns: "This user doesn't like indie comedies
                  with this particular cast"
  
  Next time: Less likely to recommend similar cast members
             in indie comedies to you
    """)

def print_key_parameters():
    print("\n" + "=" * 100)
    print("KEY SYSTEM PARAMETERS THAT CONTROL THIS".center(100))
    print("=" * 100)
    
    print("""

MODEL_VERSIONING.PY - Line 131:
  Default training window: 30 days
  
    WHERE checked_at > datetime('now', '-' || ? || ' days')
    
  Impact:
  - Recommendations older than 30 days are ignored
  - Recent errors have more influence on retraining
  - Can be adjusted: retrain_model.py line 317
  
    weights_data = prepare_training_data(days_back=30, ...)
                                                       ^^


RECOMMENDATION_TRACKER.PY - Line 264:
  Accuracy threshold for retraining: 50%
  
    if result['accuracy'] < threshold:  # threshold = 0.5
        result['needs_revalidation'] = True
  
  Impact:
  - If 50%+ of recent recs are wrong, triggers retrain
  - Prevents constant retraining from minor errors
  - Can be adjusted: app.py or retrain_model.py


MODEL_VERSIONING.PY - Line 163:
  Minimum recommendations per movie to use for training: 5
  
    if len(stats["predictions"]) >= min_samples
    
  Impact:
  - At least 5 ratings needed per movie type
  - Prevents single movies from affecting training
  - Can be adjusted: retrain_model.py line 320
  
    weights_data = prepare_training_data(
        days_back=30,
        min_samples=5  # <-- Adjust here
    )


RETRAIN_MODEL.PY - Lines 106-110:
  Version activation thresholds:
  
    if improvement > 0.05:      # > 5% -> Auto-activate
    elif improvement > 0:        # > 0%  -> Run A/B test
    else:                        # <= 0% -> Keep old
  
  Impact:
  - Only significant improvements auto-activate
  - Small improvements run A/B test first
  - Bad models automatically rejected
    """)

def print_summary():
    print("\n" + "=" * 100)
    print("SUMMARY: WHEN DO UNEXPECTED MOVIES AFFECT TRAINING?".center(100))
    print("=" * 100)
    
    print("""

YES - AFFECTS TRAINING:
=======================
  1. Recommended in last 30 days
  2. You rated it
  3. Your rating is significantly different from prediction
  4. Enough similar errors accumulate to trigger retraining
  
  Example: Recommended action movie you rated 2/10 (predicted 8/10)
  -> Creates error -> Goes into training data -> May trigger retraining
  -> New model learns to reduce action movie recommendations


NO - DOES NOT AFFECT TRAINING:
==============================
  1. Never recommended by system
     - Can't learn from predictions it never made
     
  2. Recommended >30 days ago
     - Outside retention window (filtered out)
     
  3. Added but not rated
     - No prediction validation check triggered
     
  4. Single movie
     - Need at least 5 samples per movie type
     - One unexpected movie isn't enough alone
     
  Example: Found indie film on Netflix (never recommended)
  -> No baseline prediction -> No training data -> Zero impact


THE SYSTEM LEARNS FROM MISTAKES:
================================
  Your unexpected movies HELP the system improve because:
  
  1. They identify prediction errors
  2. Errors get weighted lower in next training
  3. If errors accumulate -> Model retrains
  4. New model learns NOT to make same mistakes
  5. Hyperparameters adjust based on YOUR unexpected preferences
  
  This is a FEATURE: The system improves by learning from
  how you surprise it with your tastes!
    """)

if __name__ == "__main__":
    print_flowchart()
    print_scenarios()
    print_decision_tree()
    print_detailed_example()
    print_key_parameters()
    print_summary()
    
    print("\n" + "=" * 100)
    print("DOCUMENTATION: See UNEXPECTED_MOVIES_IMPACT.md for full details".center(100))
    print("=" * 100 + "\n")
