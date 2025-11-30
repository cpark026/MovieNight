# Automatic Hyperparameter Tuner

Comprehensive hyperparameter optimization system that works with the model versioning and retraining infrastructure.

## Overview

The tuner provides three optimization strategies:

1. **Grid Search** - Systematic exploration around current parameters
2. **Random Search** - Broad exploration of hyperparameter space
3. **Bayesian Search** - Intelligent search focused on promising regions

## Components

### 1. `hyperparameter_tuner.py`

Core tuning engine with search space generation and experiment tracking.

**Key Classes:**
- `HyperparameterTuner` - Main orchestration class
- Database tables for storing experiment results

**Key Functions:**
- `generate_grid_search_space()` - Creates grid around current parameters
- `generate_random_search_space()` - Creates random configurations
- `generate_bayesian_search_space()` - Intelligent focused search
- `save_experiment()` - Stores results to database
- `get_best_experiment()` - Retrieves best configuration found
- `get_tuning_statistics()` - Aggregated progress metrics

### 2. `tune_orchestrator.py`

High-level orchestration script that:
- Generates configurations
- Tests each with the full retraining pipeline
- Tracks results across multiple runs
- Recommends best configuration

**Main Class:**
- `TuningOrchestrator` - Coordinates full tuning workflow

### 3. Integration with `retrain_model.py`

New command-line arguments:

```bash
--tune                    # Run tuning (generates configs)
--tune-method METHOD      # Choice: grid, random, bayesian
--tune-configs NUM        # Number of configurations to test
--tune-report             # Show tuning progress
--apply-hp JSON           # Apply hyperparameters from JSON
```

## Usage Examples

### Quick Start: Generate Configurations

```bash
# Generate 20 Bayesian-optimized configurations
python retrain_model.py --tune --tune-method bayesian --tune-configs 20

# Generate 50 random configurations for broad exploration
python retrain_model.py --tune --tune-method random --tune-configs 50

# Generate grid around current parameters
python retrain_model.py --tune --tune-method grid
```

### Full Tuning Workflow

```bash
# Step 1: Generate configurations (identifies candidates to test)
python retrain_model.py --tune --tune-method bayesian --tune-configs 20

# Step 2: Run full orchestrated tuning (tests each configuration)
python tune_orchestrator.py --method bayesian --configs 20

# Step 3: View tuning progress
python retrain_model.py --tune-report
python tune_orchestrator.py --summary

# Step 4: Apply best configuration found
python retrain_model.py --force --apply-hp '{"genre_weight": 0.42, "cast_weight": 0.16, ...}'

# Step 5: Validate with A/B test
python retrain_model.py --force --dry-run
```

### Phase-Specific Tuning

```bash
# Phase 1 tuning (current - optimizes cast, popularity, genre)
python tune_orchestrator.py --method bayesian --configs 30

# Phase 2 tuning (user preferences, franchise depth)
python tune_orchestrator.py --phase2 --method bayesian --configs 50
```

### Monitoring Progress

```bash
# View current best configuration
python retrain_model.py --tune-report

# Get statistics
python tune_orchestrator.py --summary

# Show detailed report with all experiments
python tune_orchestrator.py --report
```

## Hyperparameter Details

### Phase 1 Parameters (Currently Active)

**Hybrid Score Weights** (must sum to 1.0):
- `genre_weight` - Genre similarity (40%)
- `cast_weight` - Cast overlap (15%)
- `franchise_weight` - Same franchise (5%)
- `rating_weight` - User rating (30%)
- `popularity_weight` - Movie popularity (10%)

**Genre Confidence Boosts**:
- `genre_boost_high` - High similarity (>0.7) boost: +15%
- `genre_boost_medium` - Medium similarity (>0.5) boost: +10%
- `genre_boost_low` - Low similarity (<0.3) penalty: -20%
- `genre_threshold_high` - High threshold: 0.7
- `genre_threshold_medium` - Medium threshold: 0.5
- `genre_threshold_low` - Low threshold: 0.3

**Cast Weighting** (position-based):
- `cast_lead_weight` - Lead actors: 1.0
- `cast_supporting_weight` - Supporting: 0.7
- `cast_background_weight` - Background: 0.3
- `cast_lead_threshold` - Lead limit: 5
- `cast_supporting_threshold` - Supporting limit: 15

**Popularity Scoring**:
- `popularity_rating_weight` - Rating quality (70%)
- `popularity_count_weight` - Review count (30%)

**Model Validation**:
- `accuracy_threshold` - Retrain trigger (65%)

### Phase 2 Parameters (Planned)

- `user_preference_weight` - User history influence
- `franchise_depth_scale` - Franchise boost multiplier
- `rating_prediction_weight` - Predicted rating importance

## Database Schema

### `hp_experiments` Table

Stores all tested hyperparameter configurations and their results:

```
id                          INTEGER PRIMARY KEY
experiment_id               TEXT UNIQUE (e.g., "bayesian_20251130_155355_001")
status                      TEXT ("pending", "completed", "failed")
created_at                  TIMESTAMP
completed_at                TIMESTAMP

[All hyperparameters as individual REAL columns]

test_accuracy               REAL
improvement_from_baseline   REAL
recommendation_quality_score REAL (optional)

tuning_method               TEXT ("grid", "random", "bayesian")
parent_experiment_id        TEXT (for variant tracking)
```

### `hp_tuning_history` Table

Tracks progress across tuning runs:

```
id                  INTEGER PRIMARY KEY
tuning_run_id       TEXT
iteration           INTEGER
timestamp           TIMESTAMP
best_accuracy       REAL
best_experiment_id  TEXT
exploration_phase   TEXT
```

## Search Space Details

### Grid Search

**Default Configuration:**
- Search radius: ±10% around current parameters
- Steps: 3 in each direction
- Result: ~50-80 configurations

**Parameters tuned:**
- Primary: 4 weight parameters (genre, cast, franchise, rating)
- Secondary: All threshold and boost parameters normalized

### Random Search

**Default Configuration:**
- Number of configurations: 50 (customizable)
- Coverage: Full hyperparameter space

**Parameters tuned:**
- All phase 1 parameters with random values
- Weights randomly distributed
- Thresholds randomly selected within valid ranges

### Bayesian Search

**How it works:**
1. Analyzes top 25% of previous experiments
2. Identifies successful regions of hyperparameter space
3. Adds small perturbations to best performers
4. Focuses on promising areas while avoiding convergence

**Default Configuration:**
- Number of configurations: 20 (customizable)
- Perturbation strength: ±5%
- Base sample size: 50 previous experiments

## Workflow Examples

### Finding First Improvement

```bash
# 1. Generate initial candidates
python retrain_model.py --tune --tune-method random --tune-configs 20

# 2. Test each one
python tune_orchestrator.py --method random --configs 20

# 3. See results
python retrain_model.py --tune-report

# 4. If improvement found, enable it
python retrain_model.py --force --apply-hp '{"genre_weight": 0.41, ...}'
```

### Iterative Refinement

```bash
# Round 1: Broad search
python tune_orchestrator.py --method random --configs 30

# Round 2: Focus on promising region
python tune_orchestrator.py --method bayesian --configs 20

# Round 3: Fine-tune with grid
python retrain_model.py --tune --tune-method grid
python tune_orchestrator.py --method grid --configs 15

# Apply best result
python retrain_model.py --force --apply-hp <best_json>
```

### Production Rollout

```bash
# 1. Run comprehensive tuning
python tune_orchestrator.py --method bayesian --configs 50

# 2. Review best configuration
python tune_orchestrator.py --summary

# 3. Stage with A/B test
python retrain_model.py --force --apply-hp <best_json> --dry-run

# 4. Monitor with:
# - /api/model-performance
# - /api/revalidation-status
# - /api/model-versions (view metrics)

# 5. Commit if successful
git add -A && git commit -m "Apply tuned hyperparameters - X% improvement"
```

## Performance Considerations

### Tuning Time

**Grid Search:** ~5-15 minutes (50-80 configs × ~5 seconds each)
**Random Search:** ~10-20 minutes (50 configs × ~5 seconds each)
**Bayesian Search:** ~8-18 minutes (20 configs × ~5 seconds each)

### Database Size

- Each experiment: ~500 bytes
- 50 experiments: ~25 KB
- 1000 experiments: ~500 KB

### Optimization Impact

- **Per-request overhead:** <50ms per additional tuning overhead
- **Memory:** ~5-10 MB for tuning tables
- **Disk:** Minimal (tuning data only ~1 MB even with 1000+ experiments)

## Best Practices

1. **Start with Random Search**
   - Gets broad sense of parameter landscape
   - Identifies promising regions
   - ~30 configs recommended

2. **Follow with Bayesian Search**
   - Focuses on successful regions
   - Reduces configs to test
   - ~20 configs recommended

3. **Fine-tune with Grid Search**
   - Final optimization around best result
   - Smaller search radius
   - ~10-15 configs recommended

4. **Validate Before Deployment**
   - Run A/B test with new configuration
   - Monitor for at least 24 hours
   - Track business metrics (not just accuracy)

5. **Document Results**
   - Save best configuration to HYPERPARAMETERS.md
   - Record accuracy improvement
   - Note any trade-offs observed

## Troubleshooting

### "No experiments found" error

```bash
# Initialize database
python hyperparameter_tuner.py report
```

### Tuning not finding improvements

1. Check current accuracy is below target:
   ```bash
   python retrain_model.py --stats
   ```

2. Try broader search space:
   ```bash
   python tune_orchestrator.py --method random --configs 50
   ```

3. Verify model.py changes are correct

### A configuration's accuracy is very low

- Possible bad hyperparameter combination
- Check model.py applies parameters correctly
- Review database entry for accuracy field

## Next Steps

1. **Phase 2 Implementation**
   - Add user preference tracking
   - Implement franchise depth scaling
   - Create rating prediction models

2. **Phase 3 Implementation**
   - Collaborative filtering integration
   - Deep learning components
   - Real-time adaptation

3. **Automated Tuning**
   - Schedule periodic tuning runs
   - Automatic A/B testing
   - Self-improving model

## References

- Main Model: `model.py`
- Versioning: `model_versioning.py`
- Retraining: `retrain_model.py`
- All Parameters: `HYPERPARAMETERS.md`
- Optimization Strategy: `MODEL_OPTIMIZATION_STRATEGY.py`
