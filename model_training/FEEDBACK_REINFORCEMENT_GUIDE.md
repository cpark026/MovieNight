# Feedback Reinforcement System

## Overview

The Feedback Reinforcement System integrates user negative feedback (thumbs-down/dislikes) into the recommendation model to create a continuous learning loop that improves recommendation quality over time.

When users dislike a recommendation, the system:
1. Records the dislike with contextual information
2. Creates negative training data points
3. Adjusts model feature weights based on dislike patterns
4. Automatically triggers model retraining when feedback accumulates
5. Evaluates and tracks improvement metrics

## Architecture

### Core Modules

#### `feedback_handler.py`
Manages user dislike records and feedback storage.

**Key Functions:**
- `save_dislike()` - Record a user dislike
- `get_user_dislikes()` - Retrieve dislike history
- `calculate_dislike_weight()` - Weight importance of feedback
- `get_dislike_pattern_analysis()` - Identify systematic issues
- `record_feedback_impact()` - Track how dislikes affect model

#### `feedback_reinforcement.py`
Integrates feedback into model training and feature adjustment.

**Key Functions:**
- `apply_dislike_to_training_data()` - Convert dislike to negative training example
- `calculate_feature_adjustment_from_dislike()` - Determine feature changes
- `get_untrained_negative_feedback_count()` - Check feedback accumulation
- `should_retrain_from_feedback()` - Decide if retraining needed
- `apply_feature_adjustments()` - Update model configuration
- `get_feedback_improvement_metrics()` - Track improvement progress

#### `feedback_api.py`
Flask API endpoints for frontend integration.

**Endpoints:**
- `POST /api/dislike` - Record a dislike
- `GET /api/dislike-history` - Get user's dislike history
- `GET /api/dislike-patterns` - Analyze dislike patterns
- `GET /api/feedback-metrics` - System-wide metrics

### Database Schema

#### `user_dislikes` Table
Stores individual dislike records:
- `dislike_id` - Unique dislike identifier
- `user_id` - User who disliked
- `movie_id` - Movie TMDB ID (optional)
- `movie_title` - Movie title
- `recommendation_set_id` - Related recommendation set
- `predicted_score` - Score model predicted (0.0-1.0)
- `reason` - Category of dislike (wrong_genre, poor_quality, etc.)
- `feedback_text` - Optional user comment
- `created_at` - Timestamp

#### `dislike_feedback_impact` Table
Tracks how dislikes impact model adjustments:
- `impact_id` - Unique identifier
- `dislike_id` - Related dislike
- `model_version_id` - Model version affected
- `impact_type` - Type of adjustment
- `feature_affected` - Which model component changed
- `adjustment_magnitude` - Size of change (-1.0 to 1.0)
- `applied_at` - Timestamp

#### `negative_training_examples` Table
Stores negative training data for model retraining:
- `example_id` - Unique identifier
- `user_id` - User source
- `movie_id` - Movie ID
- `movie_title` - Movie title
- `actual_rating` - 0.0 (user disliked)
- `predicted_rating` - Model's prediction
- `error` - Prediction error
- `weight` - Importance weight (0.8 for dislikes)
- `used_in_training` - Flag if used in retraining

#### `dislike_patterns` Table
Stores identified dislike patterns:
- `pattern_id` - Unique identifier
- `user_id` - User
- `pattern_type` - Type of pattern
- `pattern_value` - Pattern details
- `frequency` - How often occurs
- `severity` - Impact level
- `identified_at` - Timestamp

## Usage

### Recording a Dislike (Frontend)

```javascript
// When user clicks thumbs-down on a recommendation
const response = await fetch('/api/dislike', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
    },
    body: JSON.stringify({
        movie_id: 12345,
        movie_title: "Movie Title",
        recommendation_set_id: 456,
        predicted_score: 0.75,
        reason: "wrong_genre",
        feedback_text: "Not my type of movie",
        genres: ["Action", "Sci-Fi"],
        cast: ["Actor 1", "Actor 2"]
    })
});
```

### Recording a Dislike (Backend)

```python
from feedback_handler import save_dislike
from feedback_reinforcement import apply_dislike_to_training_data

# Save the dislike record
dislike_id = save_dislike(
    user_id=user_id,
    movie_id=movie_id,
    movie_title="Movie Title",
    predicted_score=0.75,
    reason="wrong_genre",
    feedback_text="Not my type"
)

# Convert to training data
training_data = apply_dislike_to_training_data(
    user_id=user_id,
    movie_id=movie_id,
    movie_title="Movie Title",
    predicted_score=0.75
)
```

### Analyzing Dislike Patterns

```python
from feedback_handler import get_dislike_pattern_analysis

patterns = get_dislike_pattern_analysis(user_id=123)
# Returns:
# {
#     'reason_distribution': {'wrong_genre': 5, 'poor_quality': 3, ...},
#     'recent_trend': {'total_dislikes': 8, 'avg_predicted_score': 0.72},
#     'total_dislikes': 15
# }
```

### Checking Retraining Trigger

```python
from feedback_reinforcement import should_retrain_from_feedback

if should_retrain_from_feedback():
    # Trigger model retraining
    retrain_model_with_feedback()
```

## Feedback Integration Points

### Feature Adjustment
When a dislike is recorded, features are adjusted based on reason:

- **wrong_genre**: Reduce importance of that genre (-15%)
- **poor_quality**: Reduce cast importance (-10%)
- **not_interested**: Light genre adjustment (-7.5%)
- **already_watched**: Flag for filtering

### Model Retraining
Negative feedback triggers retraining when:
- 20+ unused negative examples accumulate
- Average prediction error exceeds threshold
- Specific features show consistent issues

### Training Data Weighting
Dislike-derived training examples have:
- **Weight**: 0.8 (vs. 1.0 for regular positive ratings)
- **Actual Rating**: 0.0 (strong negative signal)
- **Time Decay**: Older dislikes weighted less

## Metrics & Monitoring

### Available Metrics

```python
from feedback_reinforcement import get_feedback_improvement_metrics

metrics = get_feedback_improvement_metrics()
# Returns:
# {
#     'total_negative_examples': 45,
#     'avg_prediction_error': 0.68,
#     'max_error': 0.95,
#     'min_error': 0.05,
#     'average_dislike_predicted_score': 0.72
# }
```

### Improvement Indicators

1. **Prediction Error Trend**: Should decrease over time
2. **Dislike Rate**: Should decrease for same content types
3. **Feature Adjustment Magnitude**: Converges as patterns stabilize
4. **Feedback Loop Efficiency**: Model retraining frequency

## Configuration

Key constants in `feedback_reinforcement.py`:

```python
DISLIKE_WEIGHT_MULTIPLIER = 0.8          # Weight of dislike in training
FEEDBACK_ACCUMULATION_THRESHOLD = 20     # Retrain after N dislikes
GENRE_DEEMPHASIS_FACTOR = 0.15          # Genre importance reduction
CAST_DEEMPHASIS_FACTOR = 0.10           # Cast importance reduction
FRANCHISE_DEEMPHASIS_FACTOR = 0.12      # Franchise importance reduction
```

## Integration with Existing System

### Model Versioning
Each feedback-driven retraining creates a new model version tracked by `model_versioning.py`.

### Recommendation Tracker
Dislikes are correlated with recommendation sets via `recommendation_set_id` for accuracy analysis.

### Model Performance
Feedback metrics inform model selection and validation decisions in `model_versioning.py`.

## Next Steps

1. **Frontend Integration**: Implement dislike button interactions in UI
2. **Retrain Pipeline**: Create automated retraining workflow with feedback
3. **A/B Testing**: Compare model versions with/without feedback
4. **User Analytics**: Dashboard showing dislike patterns by user/content
5. **Feature Learning**: Identify most impactful features from feedback
