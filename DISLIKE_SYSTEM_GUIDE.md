# How the Dislike System Works Now

## Complete System Overview

The dislike system is a comprehensive feedback mechanism that captures user negative feedback and automatically improves recommendations through model retraining.

---

## 1. User Interaction (Frontend)

### What the User Sees
- Each movie recommendation card displays a 👎 thumbs-down button
- Located next to the movie title
- Clicking opens a confirmation dialog

### The Click Flow
```
User clicks 👎 button
    ↓
Confirmation dialog: "Are you sure you want to dislike this movie?"
    ├─ [Cancel] → returns to card display
    └─ [Confirm] → triggers POST request
```

### What Gets Sent
When user confirms, a POST request is sent with:

```json
{
  "movie_id": 12345,                    // TMDB movie ID
  "movie_title": "Movie Name",          // Movie title
  "recommendation_set_id": 789,         // Which recommendation set this came from
  "predicted_score": 0.75,              // Score the model predicted (0.0-1.0)
  "reason": "not_interested",           // Why they disliked it
  "genres": ["Action", "Sci-Fi"],       // Movie genres
  "cast": ["Actor 1", "Actor 2"]        // Cast members
}
```

**Headers Include:**
- `Content-Type: application/json`
- `X-User-ID: {userId}` (from /api/check-auth)

---

## 2. Backend Processing (app.py)

### Initialization
When the Flask app starts:
```python
# 1. Add feedback_system to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'feedback_system'))

# 2. Initialize feedback tables in database
from feedback_system import init_feedback_tables, register_feedback_routes
init_feedback_tables()

# 3. Register all feedback API routes
register_feedback_routes(app)
```

This creates three database tables:
- `user_dislikes` - Records individual dislikes
- `negative_training_examples` - Training data
- `dislike_feedback_impact` - Feature adjustments

---

## 3. API Endpoint Handler (feedback_api.py)

### POST /api/dislike Endpoint

**Step 1: Authentication**
```python
# Get user ID from header or session
user_id = request.headers.get('X-User-ID', type=int)
if not user_id and 'user_id' in session:
    user_id = session.get('user_id')

if not user_id:
    return error 401 (Not authenticated)
```

**Step 2: Validation**
```python
if not data.get('movie_title'):
    return error 400 (movie_title required)
```

**Step 3: Record the Dislike**
```python
dislike_id = save_dislike(
    user_id=user_id,
    movie_id=data.get('movie_id'),
    movie_title=data['movie_title'],
    recommendation_set_id=data.get('recommendation_set_id'),
    predicted_score=data.get('predicted_score', 0.0),
    reason=data.get('reason', 'not_interested'),
    feedback_text=data.get('feedback_text', '')
)
```

**Step 4: Convert to Training Data**
```python
training_data = apply_dislike_to_training_data(
    user_id=user_id,
    movie_id=data.get('movie_id'),
    movie_title=data['movie_title'],
    predicted_score=data.get('predicted_score', 0.0)
)
```

**Step 5: Calculate Feature Adjustments**
```python
adjustments = calculate_feature_adjustment_from_dislike(
    movie_metadata={'genres': data.get('genres'), 'cast': data.get('cast')},
    reason=data.get('reason', 'not_interested')
)
```

**Step 6: Analyze Patterns**
```python
patterns = get_dislike_pattern_analysis(user_id)
```

**Step 7: Return Response**
```json
{
    "success": true,
    "dislike_id": 123,
    "training_impact": {
        "error_recorded": 0.75,
        "weight": 0.8
    },
    "feature_adjustments": {
        "genre_adjustments": {"Action": -0.15},
        "reason": "not_interested"
    },
    "user_patterns": {
        "reason_distribution": {"not_interested": 5},
        "total_dislikes": 5
    }
}
```

---

## 4. Feedback Handler (feedback_handler.py)

### save_dislike() Function

**What it does:**
1. Creates a record in `user_dislikes` table
2. Stores all metadata about the dislike
3. Returns dislike_id for tracking

**Database Record Created:**
```
dislike_id: 123 (auto-increment)
user_id: 1
movie_id: 12345
movie_title: "Movie Name"
predicted_score: 0.75        ← What the model predicted
reason: "not_interested"      ← Why user disliked it
feedback_text: ""             ← Optional user comment
created_at: 2025-11-30 18:30:00
```

### Database Schema
```sql
CREATE TABLE user_dislikes (
    dislike_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER,
    movie_title TEXT,
    recommendation_set_id INTEGER,
    predicted_score REAL,
    reason TEXT DEFAULT 'not_interested',
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## 5. Reinforcement System (feedback_reinforcement.py)

### apply_dislike_to_training_data()

Converts each dislike into a negative training example:

```
Original Prediction:  0.75 (model said: "user will like this")
Actual User Action:   0.0  (user disliked it)
Error:               0.75  (prediction was wrong)
Weight:              0.8   (importance: 80% of normal training)

Database Record:
example_id: 456
user_id: 1
movie_id: 12345
actual_rating: 0.0            ← User effectively rated as 0
predicted_rating: 0.75        ← Model's prediction
error: 0.75                   ← How wrong the model was
weight: 0.8                   ← Use 80% weight in retraining
used_in_training: 0           ← Not used in retraining yet
```

### calculate_feature_adjustment_from_dislike()

Based on the reason for dislike, adjusts model features:

**If reason = "wrong_genre":**
- Reduce importance of genres in movie
- Example: Movie is "Action", reduce Action weight by 15%
- Result: Model less likely to recommend Action movies to this user

**If reason = "poor_quality":**
- Reduce cast importance for that movie's cast
- Reduce director importance
- Result: Model downweights those actors/directors

**If reason = "not_interested":**
- Light adjustment to genres and cast
- Result: Subtle preference shift

**If reason = "already_watched":**
- Flag movie to not recommend again
- Result: Filter from future recommendations

---

## 6. Automatic Retraining Trigger

### should_retrain_from_feedback()

Monitors when enough feedback accumulates:

```python
# Check threshold
untrained_count = count of records where used_in_training = 0
threshold = 20 (configurable)

if untrained_count >= 20:
    return True → Trigger model retraining
else:
    return False → Wait for more feedback
```

### What Happens When Triggered

1. **Retrieve Training Batch**
   - Get 100 unused negative training examples
   - These are dislike records converted to training data

2. **Apply Feature Adjustments**
   - Get accumulated adjustments from all dislikes
   - Update model feature weights
   - Example: If users dislike Action movies, reduce Action weight

3. **Create New Model Version**
   - Train model with adjusted weights
   - Incorporate negative training examples
   - Evaluate performance

4. **Mark as Used**
   - Update `used_in_training = 1` for processed examples
   - Track which retraining used which examples

5. **Compare Versions**
   - Evaluate new model vs. old model
   - If better: activate as new default
   - If worse: keep old model, investigate

---

## 7. Response to Frontend

### On Success (HTTP 201)

```json
{
    "success": true,
    "dislike_id": 123,
    "training_impact": {
        "error_recorded": 0.75,
        "weight": 0.8
    },
    "feature_adjustments": {
        "genre_adjustments": {"Action": -0.15, "Sci-Fi": -0.15},
        "cast_adjustments": {},
        "franchise_adjustment": 0.0,
        "reason": "wrong_genre"
    },
    "user_patterns": {
        "reason_distribution": {"wrong_genre": 5, "poor_quality": 2},
        "recent_trend": {"total_dislikes": 8},
        "total_dislikes": 15
    }
}
```

**Frontend Action:**
- Display green confirmation: "✓ Dislike recorded. We'll improve recommendations!"
- Fade out card after 2 seconds
- User experience shows their feedback matters

### On Error (HTTP 400/401/500)

```json
{
    "success": false,
    "error": "Not authenticated" or "Failed to save dislike"
}
```

**Frontend Action:**
- Display red error message
- Allow user to retry or dismiss

---

## 8. Data Flow Diagram

```
┌─────────────────────┐
│   User Interface    │
│  Click 👎 button    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Confirmation Dialog                │
│  Are you sure?                      │
│  [Cancel] [Confirm]                 │
└──────────┬──────────────────────────┘
           │ (Confirm clicked)
           ▼
┌──────────────────────────────────────┐
│ GET /api/check-auth                 │
│ (Get user_id)                        │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ POST /api/dislike                   │
│ {movie_id, title, score, reason}    │
└──────────┬──────────────────────────┘
           │
     ┌─────┴────────────────┬──────────────────┐
     ▼                      ▼                  ▼
save_dislike()  apply_dislike()  calculate_feature_adjustments()
     │                      │                  │
     ▼                      ▼                  ▼
user_dislikes         negative_training    feature weights
   table              examples table          updated
     │                      │                  │
     └─────────┬────────────┴──────────────────┘
               │
               ▼
    get_dislike_pattern_analysis()
               │
               ▼
    Check: should_retrain_from_feedback()?
               │
         ┌─────┴─────┐
         ▼           ▼
      YES            NO
      │              │
      ▼              ▼
  Retrain         Wait for more
  Model           feedback
  │
  ├─ Get batch of negative examples
  ├─ Apply feature adjustments
  ├─ Create new model version
  ├─ Evaluate performance
  └─ Mark examples as used
               │
               ▼
    Return JSON response to frontend
               │
     ┌─────────┴──────────┐
     ▼                    ▼
  Success             Error
   │                   │
   ▼                   ▼
Green confirmation   Red error
"✓ Dislike recorded  "Error: ..."
We'll improve!"
   │                   │
   ▼                   ▼
Fade out card      Show error
after 2 sec        message
```

---

## 9. Metrics Tracked

### Per Dislike
- Dislike ID (unique identifier)
- User ID (who disliked)
- Movie ID (what was disliked)
- Movie Title
- Predicted Score (0.0-1.0)
- Dislike Reason (wrong_genre, poor_quality, etc)
- Timestamp (when)
- Feedback Text (optional user comment)

### User-Level Patterns
- Total dislikes per user
- Distribution by reason (why they dislike)
- Common genres disliked
- Common actors/directors disliked
- Prediction error trends

### System-Level Metrics
- Total negative examples collected
- Dislike rate (dislikes/recommendations)
- Most common dislike reasons
- Feature adjustment magnitudes
- Model retraining frequency
- Improvement in prediction accuracy

---

## 10. Dislike Reasons

Supported categories:

| Reason | What It Means | Adjustment |
|--------|-------------|-----------|
| `wrong_genre` | Movie not in expected genre | -15% genre weight |
| `poor_quality` | Quality issues with movie | -10% cast weight |
| `already_watched` | User already saw this | Filter from recommendations |
| `not_interested` | General lack of interest | -7.5% genre/cast adjustment |
| `irrelevant` | Not relevant recommendation | Light adjustment |
| `other` | Other reason | None (just recorded) |

---

## 11. Configuration

### Retraining Threshold
```python
# In feedback_reinforcement.py
FEEDBACK_ACCUMULATION_THRESHOLD = 20  # Retrain after 20 dislikes
```
Change this to trigger retraining more or less frequently.

### Feature Adjustment Factors
```python
GENRE_DEEMPHASIS_FACTOR = 0.15        # 15% genre reduction
CAST_DEEMPHASIS_FACTOR = 0.10         # 10% cast reduction
FRANCHISE_DEEMPHASIS_FACTOR = 0.12    # 12% franchise reduction
DISLIKE_WEIGHT_MULTIPLIER = 0.8       # 80% weight in training
```

---

## 12. Example Scenario

**User Journey:**

1. **See Recommendation**: "Matrix Reloaded" with 75% score
2. **Click 👎**: User thinks "Wrong genre, I wanted drama"
3. **Confirm**: Dialog closes, POST sent
4. **Backend Processes**:
   - Records dislike in database
   - Creates training example: predicted 0.75, actual 0.0 (error: 0.75)
   - Reduces Sci-Fi weight by 15%
   - Records pattern: User dislikes Sci-Fi
5. **Response**: "✓ Dislike recorded. We'll improve recommendations!"
6. **Card Fades**: After 2 seconds, card disappears
7. **Feedback Accumulates**: After 20 dislikes, model retrains
8. **Model Improves**: Next recommendations have less Sci-Fi, more drama

---

## 13. Key Files

| File | Purpose |
|------|---------|
| `static/js/index.js` | Frontend dislike button and POST |
| `app.py` | Initialize feedback system |
| `feedback_system/__init__.py` | Package exports |
| `feedback_system/feedback_handler.py` | Save dislike records |
| `feedback_system/feedback_reinforcement.py` | Convert to training data |
| `feedback_system/feedback_api.py` | API endpoints |

---

## 14. Next Steps for Full Integration

1. ✅ Frontend dislike UI (already done)
2. ✅ Backend API endpoints (already done)
3. ✅ Dislike recording (already done)
4. ⏳ Automated model retraining (schedule/trigger needed)
5. ⏳ A/B testing (compare models with/without feedback)
6. ⏳ User analytics dashboard (show feedback impact)
7. ⏳ Feedback loop display (show users how they're improving recommendations)

---

## Summary

The dislike system creates a **continuous learning loop**:

```
User Dislikes → Record Feedback → Convert to Training Data →
Feature Adjustment → Feedback Accumulates → Model Retrains →
Better Recommendations → Fewer Dislikes → Positive Feedback Loop
```

This turns every dislike into valuable training signal that improves the model over time!
