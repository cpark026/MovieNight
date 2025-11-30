#!/usr/bin/env python3
"""
Visual demonstration of how unexpected movies affect model training
"""

def print_flowchart():
    print("\n" + "=" * 100)
    print("UNEXPECTED MOVIE IMPACT ON TRAINING - VISUAL FLOWCHART".center(100))
    print("=" * 100)
    
    print("\n")
    print("┌─────────────────────────────────────────────────────────────────────────────┐")
    print("│ USER ADDS AN UNEXPECTED MOVIE TO THEIR LIST                                │")
    print("└────────────────────────────────┬────────────────────────────────────────────┘")
    print("                                 │")
    print("                                 ▼")
    print("                    ┌────────────────────────────┐")
    print("                    │  Was it recently          │")
    print("                    │  recommended? (< 30 days) │")
    print("                    └────┬──────────────────┬────┘")
    print("                 ┌──────┘                  └──────┐")
    print("                 │ YES                         NO │")
    print("                 ▼                               ▼")
    print("        ┌──────────────────┐      ┌─────────────────────────┐")
    print("        │ FOUND in          │      │ NOT in                  │")
    print("        │ recommendation    │      │ recommendation_quality  │")
    print("        │ table             │      │ table                   │")
    print("        └─────────┬────────┘      └──────────────┬──────────┘")
    print("                  │                               │")
    print("                  ▼                               ▼")
    print("         ┌────────────────┐           ┌─────────────────────┐")
    print("         │ Create         │           │ NO TRAINING IMPACT  │")
    print("         │ validation     │           │                     │")
    print("         │ record         │           │ Movie goes in DB    │")
    print("         │ (predicted vs  │           │ System learns       │")
    print("         │ actual rating) │           │ nothing about it    │")
    print("         └────────┬───────┘           └─────────────────────┘")
    print("                  │")
    print("                  ▼")
    print("         ┌────────────────────┐")
    print("         │ Calculate error    │")
    print("         │ accuracy metrics   │")
    print("         └────┬───────────┬───┘")
    print("              │           │")
    print("        GOOD  │           │ BAD")
    print("        PRED  │           │ PREDICTION")
    print("              ▼           ▼")
    print("         ┌────────┐  ┌──────────────┐")
    print("         │Accuracy│  │Error is      │")
    print("         │stays   │  │recorded in   │")
    print("         │high    │  │training data │")
    print("         │        │  │with LOWER    │")
    print("         │No      │  │weight        │")
    print("         │retrain │  │              │")
    print("         │        │  │Accumulates..│")
    print("         └────────┘  └──────┬───────┘")
    print("                            │")
    print("                            ▼")
    print("                   ┌─────────────────────┐")
    print("                   │ If errors           │")
    print("                   │ accumulate &        │")
    print("                   │ accuracy < 50%      │")
    print("                   └──────────┬──────────┘")
    print("                              │")
    print("                              ▼")
    print("                   ┌─────────────────────┐")
    print("                   │ TRIGGERS RETRAINING │")
    print("                   │                     │")
    print("                   │ • Collects training │")
    print("                   │   data (30-day      │")
    print("                   │   window)           │")
    print("                   │ • Creates new model │")
    print("                   │ • Tests new vs old  │")
    print("                   │ • If better:        │")
    print("                   │   - Runs A/B test   │")
    print("                   │   - or auto-        │")
    print("                   │     activates       │")
    print("                   └─────────────────────┘")
    print()

def print_examples():
    print("\n" + "=" * 100)
    print("CONCRETE EXAMPLES".center(100))
    print("=" * 100)
    
    examples = [
        {
            "title": "SCENARIO 1: Recommended 5 Days Ago, You Hate It",
            "movie": "Action Movie - The Explosion",
            "recommended": "YES (5 days ago, score: 0.75)",
            "your_rating": "2/10 (You hate action movies!)",
            "in_training": "✅ YES",
            "impact": """
                ✓ Error recorded: 0.75 - 0.2 = 0.55 (huge!)
                ✓ Low weight assigned to this movie
                ✓ Accumulates with other errors
                ✓ If 50%+ of recent recs are this bad → Retraining triggered
                ✓ Next model: Reduces action movie weight
            """
        },
        {
            "title": "SCENARIO 2: You Find Random Indie Film on Letterboxd",
            "movie": "Indie Drama - The Quiet Part",
            "recommended": "NO (never in recommendations)",
            "your_rating": "9/10 (Amazing!)",
            "in_training": "❌ NO",
            "impact": """
                ✗ No baseline prediction (wasn't recommended)
                ✗ No training data created
                ✗ Model learns nothing about why you liked it
                ✗ But: Added to your movies table for future reference
                ✗ System just moves on (no impact on hyperparameters)
            """
        },
        {
            "title": "SCENARIO 3: Recommended 45 Days Ago (Outside Window)",
            "movie": "Comedy - The Setup",
            "recommended": "YES (but 45 days ago!)",
            "your_rating": "8/10",
            "in_training": "❌ NO (too old)",
            "impact": """
                ✗ Recommendation too old (outside 30-day window)
                ✗ Filtered out during training data preparation
                ✗ System: "This data is stale, can't use it"
                ✗ No impact on retraining decision
            """
        },
        {
            "title": "SCENARIO 4: Recommended, You Add It But Don't Rate",
            "movie": "Mystery - The Truth",
            "recommended": "YES (3 days ago)",
            "your_rating": "(Not yet rated)",
            "in_training": "❌ NO",
            "impact": """
                ✗ No validation check triggered
                ✗ No rating means no validation_recommendation_against_rating() call
                ✗ Movie in database but no training data
                ✗ Once you rate it → Training impact enabled
            """
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{example['title']}")
        print("─" * 100)
        print(f"Movie:           {example['movie']}")
        print(f"Recommended:     {example['recommended']}")
        print(f"Your Rating:     {example['your_rating']}")
        print(f"In Training Data: {example['in_training']}")
        print(f"Impact:")
        for line in example['impact'].strip().split('\n'):
            print(f"  {line}")

def print_decision_tree():
    print("\n" + "=" * 100)
    print("QUICK DECISION TREE - DOES MY MOVIE AFFECT TRAINING?".center(100))
    print("=" * 100)
    
    questions = [
        ("1. Was this movie RECOMMENDED to you?", ["YES (go to 2)", "NO → ANSWER: No impact"]),
        ("2. Was it recommended within the LAST 30 DAYS?", ["YES (go to 3)", "NO → ANSWER: No impact (too old)"]),
        ("3. Have you RATED it?", ["YES (go to 4)", "NO → ANSWER: No impact (yet)"]),
        ("4. Does your rating MATCH the prediction?", 
         ["YES → Good recommendation, reinforces model",
          "NO → Error recorded, may trigger retraining if errors accumulate"])
    ]
    
    for question, answers in questions:
        print(f"\n{question}")
        for answer in answers:
            print(f"  └─ {answer}")

def print_hyperparameter_impact():
    print("\n" + "=" * 100)
    print("HOW UNEXPECTED MOVIES CHANGE HYPERPARAMETERS".center(100))
    print("=" * 100)
    
    print("""
EXAMPLE: Unexpected action movie you rated 2/10 (predicted: 7/10)

Current Hyperparameters (from tuned model):
  • Genre Weight:     0.1466
  • Cast Weight:      0.3201
  • Franchise Weight: 0.2116
  • Rating Weight:    0.0946

If Many Similar Errors Accumulate:
  
  Retraining triggered because accuracy < 50%
  ↓
  Weighted training data includes your errors
  ↓
  Creates new model version with ADJUSTED weights
  
Potential new hyperparameters (example):
  • Genre Weight:     0.1400  ← Reduced (genre recommendations were wrong)
  • Cast Weight:      0.3300  ← Increased (cast matching works better)
  • Franchise Weight: 0.2116  ← Unchanged
  • Rating Weight:    0.0900  ← Slightly reduced (rating-based matching missed)
  
Result: Next recommendations less likely to be heavy action movies,
        more likely to consider lesser-known cast members you might like
    """)

def print_summary():
    print("\n" + "=" * 100)
    print("KEY TAKEAWAYS".center(100))
    print("=" * 100)
    print("""
✅ UNEXPECTED MOVIES AFFECT TRAINING WHEN:
  1. They were recommended in the last 30 days
  2. You rate them
  3. Your rating significantly differs from the prediction
  4. Enough similar errors accumulate to trigger retraining

❌ UNEXPECTED MOVIES DO NOT AFFECT TRAINING WHEN:
  1. They were never recommended
  2. They were recommended >30 days ago
  3. You don't rate them
  4. Your single movie's error isn't enough to trigger retraining

🎯 THE SYSTEM DESIGN:
  • Learns from prediction errors when you add unexpected movies
  • Ignores movies it never recommended (can't learn what it didn't predict)
  • Has a 30-day retention window (old data is stale)
  • Requires accumulation of errors (one bad prediction isn't enough)

🚀 YOUR BENEFIT:
  • The system IMPROVES when you add unexpected movies and rate them
  • Each error teaches the model something new about your preferences
  • Over time, recommendations get better at handling surprises
    """)

if __name__ == "__main__":
    print_flowchart()
    print_examples()
    print_decision_tree()
    print_hyperparameter_impact()
    print_summary()
    
    print("\n" + "=" * 100)
    print("For full details, see: UNEXPECTED_MOVIES_IMPACT.md".center(100))
    print("=" * 100 + "\n")
