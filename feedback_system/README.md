# Feedback System

A comprehensive system for managing user negative feedback (dislikes) and integrating it into the recommendation model for continuous learning and improvement.

## Structure

```
feedback_system/
├── __init__.py                          # Package initialization with exports
├── feedback_handler.py                  # Dislike recording and tracking
├── feedback_reinforcement.py            # Model training integration
├── feedback_api.py                      # Flask API endpoints
├── FRONTEND_FEEDBACK_INTEGRATION.md     # Frontend integration guide
└── README.md                            # This file
```

## Quick Start

### Installation

The feedback system is already integrated into the main application. To use it:

```python
from feedback_system import (
    save_dislike,
    get_dislike_pattern_analysis,
    should_retrain_from_feedback,
    register_feedback_routes
)
```

### Registration in Flask App

In your `app.py`:

```python
from feedback_system import register_feedback_routes, init_feedback_tables

# After creating Flask app
app = Flask(__name__)

# Initialize feedback system
init_feedback_tables()

# Register API routes
register_feedback_routes(app)
```

### Recording a Dislike

```python
from feedback_system import save_dislike, apply_dislike_to_training_data

# Record the dislike
dislike_id = save_dislike(
    user_id=123,
    movie_id=456,
    movie_title="Movie Title",
    predicted_score=0.75,
    reason="wrong_genre"
)

# Convert to training data for model improvement
training_data = apply_dislike_to_training_data(
    user_id=123,
    movie_id=456,
    movie_title="Movie Title",
    predicted_score=0.75
)
```

## Modules

### feedback_handler.py

Manages dislike records and feedback tracking.

**Key Functions:**
- `init_feedback_tables()` - Initialize database schema
- `save_dislike()` - Record a user dislike
- `get_user_dislikes()` - Retrieve user's dislike history
- `calculate_dislike_weight()` - Calculate feedback importance
- `get_dislike_pattern_analysis()` - Analyze dislike patterns
- `record_feedback_impact()` - Track feature adjustments
- `get_model_feedback_metrics()` - Aggregate feedback metrics

**Database Tables Created:**
- `user_dislikes` - Individual dislike records
- `dislike_feedback_impact` - Feature adjustment tracking
- `dislike_patterns` - Identified user patterns

### feedback_reinforcement.py

Integrates feedback into model training and improvement.

**Key Functions:**
- `apply_dislike_to_training_data()` - Create negative training examples
- `calculate_feature_adjustment_from_dislike()` - Determine feature changes
- `get_untrained_negative_feedback_count()` - Check accumulation
- `should_retrain_from_feedback()` - Decide if retraining needed
- `mark_negative_examples_as_used()` - Mark used examples
- `get_negative_training_batch()` - Retrieve training batch
- `apply_feature_adjustments()` - Update model configuration
- `get_feedback_improvement_metrics()` - Track improvement

**Configuration Constants:**
```python
DISLIKE_WEIGHT_MULTIPLIER = 0.8          # Weight in training
FEEDBACK_ACCUMULATION_THRESHOLD = 20     # Trigger retraining at N dislikes
GENRE_DEEMPHASIS_FACTOR = 0.15          # Genre weight adjustment
CAST_DEEMPHASIS_FACTOR = 0.10           # Cast weight adjustment
FRANCHISE_DEEMPHASIS_FACTOR = 0.12      # Franchise weight adjustment
```

### feedback_api.py

Flask API endpoints for frontend integration.

**Endpoints:**

#### POST /api/dislike
Record a user dislike.

**Request:**
```json
{
    "movie_id": 123,
    "movie_title": "Movie Title",
    "recommendation_set_id": 456,
    "predicted_score": 0.75,
    "reason": "wrong_genre",
    "feedback_text": "Not my type of movie",
    "genres": ["Action", "Sci-Fi"],
    "cast": ["Actor 1", "Actor 2"]
}
```

**Response:**
```json
{
    "success": true,
    "dislike_id": 789,
    "training_impact": {
        "error_recorded": 0.75,
        "weight": 0.8
    },
    "feature_adjustments": {
        "genre_adjustments": {"Action": -0.15, "Sci-Fi": -0.15},
        "cast_adjustments": {},
        "reason": "wrong_genre"
    },
    "user_patterns": {
        "reason_distribution": {"wrong_genre": 5, "poor_quality": 2},
        "total_dislikes": 7
    }
}
```

#### GET /api/dislike-history
Retrieve user's dislike history.

**Query Parameters:**
- `limit` (int, default 50) - Number of recent dislikes

**Response:**
```json
{
    "success": true,
    "count": 15,
    "dislikes": [
        {
            "dislike_id": 789,
            "movie_id": 123,
            "movie_title": "Movie Title",
            "predicted_score": 0.75,
            "reason": "wrong_genre",
            "created_at": "2025-11-30 18:00:00"
        }
    ]
}
```

#### GET /api/dislike-patterns
Analyze user's dislike patterns.

**Response:**
```json
{
    "success": true,
    "patterns": {
        "reason_distribution": {"wrong_genre": 5, "poor_quality": 3},
        "recent_trend": {"total_dislikes": 8, "avg_predicted_score": 0.72},
        "total_dislikes": 15
    }
}
```

#### GET /api/feedback-metrics
Get system-wide feedback metrics.

**Response:**
```json
{
    "success": true,
    "metrics": {
        "total_negative_examples": 45,
        "avg_prediction_error": 0.68,
        "max_error": 0.95,
        "min_error": 0.05
    },
    "active_model_version": {
        "version_id": 3,
        "created_at": "2025-11-30 10:00:00",
        "accuracy": 0.82
    }
}
```

## Workflow

### User Feedback Flow

```
1. User sees recommendation with score
   ↓
2. User clicks thumbs-down button
   ↓
3. Confirmation dialog appears
   ↓
4. User confirms dislike with optional reason
   ↓
5. Frontend sends POST /api/dislike
   ↓
6. Backend processes:
   - Records dislike in database
   - Creates negative training data
   - Calculates feature adjustments
   - Analyzes patterns
   ↓
7. Returns analysis to frontend
   ↓
8. Frontend shows confirmation
```

### Model Improvement Flow

```
User Dislike
   ↓
save_dislike() → Database record
   ↓
apply_dislike_to_training_data() → Negative training example
   ↓
calculate_feature_adjustment_from_dislike() → Feature weights
   ↓
Accumulation Check
   ↓
should_retrain_from_feedback() → Trigger?
   ↓
If YES:
   - Retrieve batch: get_negative_training_batch()
   - Apply adjustments: apply_feature_adjustments()
   - Create model version
   - Mark used: mark_negative_examples_as_used()
   ↓
If NO:
   - Wait for more feedback
```

## Dislike Reasons

Supported dislike categories:

- `wrong_genre` - Movie not in expected genre
- `poor_quality` - Movie quality issues
- `already_watched` - User already saw this
- `not_interested` - General lack of interest
- `irrelevant` - Recommendation not relevant
- `other` - Other reason

## Configuration

### Database Path

The system automatically finds the database in the parent directory:

```python
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "movies.db")
```

### Retraining Trigger

Modify in `feedback_reinforcement.py`:

```python
FEEDBACK_ACCUMULATION_THRESHOLD = 20  # Change this to trigger more/less frequently
```

### Feature Adjustments

Modify factors in `feedback_reinforcement.py`:

```python
GENRE_DEEMPHASIS_FACTOR = 0.15        # Increase for stronger genre corrections
CAST_DEEMPHASIS_FACTOR = 0.10         # Adjust cast importance
FRANCHISE_DEEMPHASIS_FACTOR = 0.12    # Adjust franchise importance
```

## Testing

### Manual API Testing

```bash
# Record a dislike
curl -X POST http://localhost:5000/api/dislike \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -d '{
    "movie_id": 123,
    "movie_title": "Test Movie",
    "predicted_score": 0.75,
    "reason": "wrong_genre"
  }'

# Get dislike history
curl http://localhost:5000/api/dislike-history \
  -H "X-User-ID: 1"

# Get patterns
curl http://localhost:5000/api/dislike-patterns \
  -H "X-User-ID: 1"

# Get metrics
curl http://localhost:5000/api/feedback-metrics
```

### Unit Tests

See `test_feedback_system.py` for comprehensive unit tests.

## Monitoring

### Key Metrics

1. **Dislike Rate** - Total dislikes / total recommendations
2. **Reason Distribution** - Most common dislike reasons
3. **Prediction Error** - Average error on disliked items
4. **Retraining Frequency** - How often model retrains
5. **Improvement Rate** - Decrease in dislike rate over time

### Logs

```bash
# Monitor feedback processing
grep "\[FEEDBACK\]" app.log

# Check retraining triggers
grep "Feedback threshold reached" app.log

# Track feature adjustments
grep "Feature adjustments" app.log
```

## Integration Points

- **model_versioning.py** - Creates new model versions from feedback
- **recommendation_tracker.py** - Correlates dislikes with recommendations
- **model.py** - Uses adjusted weights in predictions
- **app.py** - Registers API routes and initializes tables

## Documentation

- **FRONTEND_FEEDBACK_INTEGRATION.md** - Frontend integration guide
- **FEEDBACK_REINFORCEMENT_GUIDE.md** - Complete system documentation

## Next Steps

1. Integrate frontend UI with dislike button
2. Test feedback recording workflow
3. Monitor dislike patterns and trends
4. Trigger model retraining based on feedback
5. Compare model versions with/without feedback
6. Build user-facing analytics dashboard
