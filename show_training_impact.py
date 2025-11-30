#!/usr/bin/env python3
"""
Display summary of how unexpected movies affect training
"""

print("""
╔════════════════════════════════════════════════════════════════════════════════════════╗
║         HOW UNEXPECTED MOVIES AFFECT MODEL TRAINING - COMPLETE EXPLANATION            ║
╚════════════════════════════════════════════════════════════════════════════════════════╝

YOUR QUESTION:
--------------
"When an unexpected movie is added, does it affect the training?"


THE SHORT ANSWER:
-----------------
YES - But only under 4 specific conditions:
  1. System recommended it (within last 30 days)
  2. You rated it
  3. Your rating differs from prediction
  4. Enough errors accumulate to trigger retraining (< 50% accuracy)

NO - If any of these are true:
  1. System never recommended it
  2. Recommended >30 days ago (too old)
  3. You haven't rated it yet
  4. Single movie can't affect training (need 5+ samples)


THE MECHANISM:
--------------

You add movie
        ↓
System checks: Was this recently recommended?
        ↓
IF YES:
  ├─ Records validation data
  │  ├─ What system predicted (predicted_score)
  │  ├─ What you rated (actual_rating)
  │  └─ The error between them
  ├─ Checks accuracy of recent recommendations
  └─ If accuracy < 50%:
      ├─ TRIGGERS RETRAINING
      ├─ New model created
      ├─ Hyperparameters adjusted
      └─ Tested before activation

IF NO:
  └─ Zero impact (no data created)


REAL SCENARIOS:
---------------

SCENARIO 1: Affects Training (YES)
  Movie:         "Action Film - The Explosion"
  Recommended:   YES - 5 days ago (predicted: 0.75)
  You rated:     2/10 (normalized: 0.2)
  Error:         0.55 (HUGE!)
  
  Result:        GOES INTO TRAINING
                 ├─ Gets LOW weight (because wrong)
                 └─ If errors accumulate:
                    ├─ Accuracy drops below 50%
                    ├─ Triggers retraining
                    └─ New model learns to reduce action recommendations

SCENARIO 2: No Impact (NO)
  Movie:         "Indie Film - The Quiet Part"
  Recommended:   NO (you found it yourself)
  You rated:     9/10 (loved it!)
  
  Result:        IGNORED
                 ├─ No baseline prediction
                 ├─ No training data
                 └─ System learns nothing about it
                    (Can't learn from predictions it never made)

SCENARIO 3: No Impact (NO)
  Movie:         "Comedy - The Setup"
  Recommended:   YES, but 45 days ago
  You rated:     8/10
  
  Result:        FILTERED OUT
                 ├─ Outside 30-day training window
                 ├─ Considered "stale data"
                 └─ System ignores it

SCENARIO 4: No Impact Yet (NO)
  Movie:         "Mystery - The Truth"
  Recommended:   YES - 3 days ago
  You rated:     (Haven't rated yet)
  
  Result:        NO VALIDATION
                 ├─ No rating = no validation check
                 └─ Will affect training once you rate it


THE LEARNING PROCESS:
---------------------

Step 1: Movie Added
        └─ app.py calls validate_recommendation_against_rating()

Step 2: Validation Recorded
        └─ Creates entry in recommendation_quality table
           ├─ predicted_score: 0.75
           ├─ actual_rating: 0.2
           └─ error: 0.55

Step 3: Accuracy Checked
        └─ recommendation_tracker.py calculates last 30 days
           ├─ Total recommendations: 20
           ├─ Accurate: 8
           └─ Accuracy: 40% (BELOW 50% THRESHOLD!)

Step 4: Retraining Triggered
        └─ retrain_model.py begins process

Step 5: Training Data Prepared
        └─ model_versioning.py collects all errors (30 days)
           ├─ Your error: weight = 0.1 (low - because wrong)
           └─ Good predictions: weight > 0.5 (high - because right)

Step 6: New Model Created
        └─ Adjusts hyperparameters based on weighted errors
           ├─ Old: Genre Weight = 0.1466
           └─ New: Genre Weight = 0.1400 (reduced)
              (Because action movie recommendation was wrong)

Step 7: Evaluation
        └─ Test against test set
           ├─ Old model: 60.14% accuracy
           ├─ New model: 60.25% accuracy
           └─ Improvement: +0.11%

Step 8: Decision
        └─ If improvement > 5%: Auto-activate
           Or if 0-5%: Run A/B test
           Or if negative: Keep old model

Result:  System improved from your unexpected movie!


KEY SYSTEM PARAMETERS:
----------------------

Training Window: 30 days
  └─ Only recent recommendations affect training
  └─ Older data is filtered out
  └─ Can be adjusted: retrain_model.py line 317

Accuracy Threshold: 50%
  └─ Retraining triggers when accuracy drops below this
  └─ Prevents constant retraining from minor errors
  └─ Can be adjusted: recommendation_tracker.py line 264

Minimum Samples: 5
  └─ Need at least 5 ratings before a movie affects training
  └─ Prevents single outliers from derailing the model
  └─ Can be adjusted: retrain_model.py line 320

Auto-Activate Threshold: 5%
  └─ Only auto-activate if improvement > 5%
  └─ Smaller improvements go through A/B testing first
  └─ Can be adjusted: retrain_model.py line 106


THE THREE POSSIBLE OUTCOMES:
----------------------------

1. Your Error Gets WEIGHTED LOW
   ├─ System recorded: "This prediction was wrong"
   ├─ Next model: Less confident about this pattern
   └─ Result: System learns NOT to recommend similar movies

2. No Impact (Movie Ignored)
   ├─ Never recommended OR too old OR not rated
   ├─ No training data created
   └─ Result: System continues unchanged

3. Your Correct Prediction Gets WEIGHTED HIGH
   ├─ System recorded: "This prediction was right"
   ├─ Next model: More confident about this pattern
   └─ Result: System learns TO recommend similar movies


WHY THIS DESIGN?
----------------

Safety:
  └─ Single unexpected movie can't break the model
  └─ Weighted low to prevent overreaction
  └─ Requires accumulation (50% threshold) before retraining

Learning:
  └─ System improves from your surprising preferences
  └─ Each error is feedback
  └─ Hyperparameters adjust based on YOUR taste

Stability:
  └─ Recent data matters more (30-day window)
  └─ Old data is stale and filtered out
  └─ A/B testing before deploying new models

Efficiency:
  └─ Minimum samples prevent noise (5 per movie type)
  └─ Auto-activate only significant improvements (>5%)
  └─ System doesn't waste time on every tiny change


PRACTICAL EXAMPLES:
-------------------

Example 1: Your Unexpected Movie Triggers Retraining
├─ Monday: System recommends "Action Movie" (score: 0.75)
├─ Friday: You add it, rate 2/10 (error: 0.55)
├─ Saturday: Accuracy drops to 40%, triggers retraining
├─ Sunday: A/B test begins
├─ Wednesday: New model activates
└─ Result: System now less confident about action movies

Example 2: Your Unexpected Movie Is Ignored
├─ You find "Indie Drama" on Letterboxd (never recommended)
├─ You rate it 9/10
└─ Result: Zero training impact (system can't learn what it didn't predict)

Example 3: Unexpected Movie Too Old
├─ You finally watch "Comedy" from 45 days ago
├─ You rate it 8/10
└─ Result: Outside retention window, zero training impact


FILES INVOLVED:
---------------

app.py (line 246)
  └─ Triggers validation when movie added

recommendation_tracker.py
  └─ Records predicted vs actual ratings
  └─ Checks if accuracy triggers retraining

model_versioning.py (line 104)
  └─ Prepares weighted training data
  └─ Creates new model versions

retrain_model.py (line 68)
  └─ Orchestrates full retraining process

model.py
  └─ Contains hyperparameters
  └─ Gets updated by retraining


DOCUMENTATION:
---------------

Quick Reference:  UNEXPECTED_MOVIES_QUICK_REFERENCE.md
Full Analysis:    UNEXPECTED_MOVIES_ANALYSIS.md
Summary:          UNEXPECTED_MOVIES_SUMMARY.txt
Visual Examples:  Run: python show_unexpected_impact.py


BOTTOM LINE:
------------

When you add an unexpected movie:

✓ Affects training IF:
  • Recently recommended (< 30 days)
  • You rated it
  • Rating differs from prediction
  • Errors accumulate (< 50% accuracy)

✗ Doesn't affect training IF:
  • Never recommended
  • Recommended >30 days ago
  • Not yet rated
  • Single outlier

The unexpected movies are GOOD for the system!
They teach it about your surprising preferences
and help it adjust for next time.

════════════════════════════════════════════════════════════════════════════════════════
""")
