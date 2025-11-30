# Model Training Module

This folder contains all model training, tuning, and versioning logic for the MovieNight recommendation system.

## Core Files

### Training Infrastructure
- **`model.py`** - Main recommendation model with hyperparameters
- **`model_versioning.py`** - Version management, A/B testing framework
- **`retrain_model.py`** - Automated retraining orchestration
- **`recommendation_tracker.py`** - Tracks prediction accuracy and triggers retraining

### Hyperparameter Tuning
- **`hyperparameter_tuner.py`** - Grid, Random, and Bayesian search algorithms
- **`tune_orchestrator.py`** - Orchestrates complete tuning workflow
- **`best_hp.json`** - Best hyperparameters found (60.14% accuracy)

### Testing & Validation
- **`test_tuner_integration.py`** - Integration tests for tuning system (8/8 passing)
- **`test_model_versioning.py`** - Version management tests
- **`validate_ab_test.py`** - A/B test validation
- **`review_best_config.py`** - Review best configuration

### Utilities
- **`check_schema.py`** - Database schema inspection

## Documentation

### Getting Started
- **`QUICK_START_TUNING.md`** - Quick start guide for hyperparameter tuning
- **`README_TUNER.md`** - Tuner system overview

### Guides
- **`HYPERPARAMETER_TUNER_GUIDE.md`** - Comprehensive tuner documentation
- **`TUNER_SYSTEM_SUMMARY.md`** - System architecture summary
- **`DEPLOYMENT_SUMMARY.md`** - Deployment information (one level up)

### Analysis & Learning
- **`UNEXPECTED_MOVIES_IMPACT.md`** - How unexpected movies affect training
- **`UNEXPECTED_MOVIES_QUICK_REFERENCE.md`** - Quick reference for training impact
- **`UNEXPECTED_MOVIES_SUMMARY.txt`** - Summary of training impact
- **`UNEXPECTED_MOVIES_ANALYSIS.md`** - Complete analysis of training impact
- **`TRAINING_IMPACT_INDEX.md`** - Index for training impact docs (one level up)

### Implementation Details
- **`PHASE_1_IMPLEMENTATION.md`** - Phase 1 tuning implementation details
- **`TUNER_IMPLEMENTATION_COMPLETE.md`** - Implementation completion summary
- **`HYPERPARAMETERS.md`** - Hyperparameter details

## Scripts

### Visualization & Reporting
- **`show_training_impact.py`** - Visual guide: training impact of unexpected movies
- **`show_unexpected_impact.py`** - Flowcharts and scenarios
- **`show_deployment_status.py`** - Deployment status dashboard
- **`visualize_unexpected_impact.py`** - Additional visualizations

## Usage

### From Root Directory
```bash
# Train and tune model
python model_training/retrain_model.py --tune

# Review best configuration
python model_training/review_best_config.py

# Run A/B test validation
python model_training/validate_ab_test.py

# Run tests
python -m pytest model_training/test_tuner_integration.py
python -m pytest model_training/test_model_versioning.py
```

### View Training Impact
```bash
python model_training/show_training_impact.py
python model_training/show_unexpected_impact.py
```

## Key Concepts

### Training Data Flow
1. User rates movie → `app.py` validates recommendation
2. Error recorded → `recommendation_tracker.py` 
3. Accuracy checked → If < 50%, triggers retraining
4. New model created → `model_versioning.py` with adjusted hyperparameters
5. A/B tested → If better, activated

### Hyperparameter Tuning
- **Grid Search**: 81 configurations around current params
- **Random Search**: 50 random configurations  
- **Bayesian Search**: 20 intelligent configurations using prior results
- **Best Found**: 60.14% accuracy (+5.14% vs baseline)

### Current Model
- **Accuracy**: 60.14%
- **Method**: Bayesian optimization
- **Experiment ID**: bayesian_20251130_165747_013
- **Hyperparameters**: See `best_hp.json`

## Database

Uses `movies.db` with tables:
- `hp_experiments` - Tuning experiment results
- `hp_tuning_history` - Tuning run progress
- `model_versions` - Model version tracking
- `recommendation_quality` - Prediction accuracy tracking
- `ab_tests` - A/B test results

## Import Notes

When using from root directory:
```python
from model_training.model_versioning import get_active_model_version
from model_training.recommendation_tracker import check_for_model_revalidation
from model_training.model import get_top_recommendations
```

The `app.py` handles path setup automatically.

## Performance Metrics

- Training window: 30 days
- Accuracy threshold: 50%
- Min samples per movie: 5
- Auto-activate threshold: 5% improvement

See documentation for details on adjusting these parameters.

---

*Last Updated: 2025-11-30*
*Status: Production Ready*
