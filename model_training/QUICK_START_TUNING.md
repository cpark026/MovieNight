# Quick Start: Hyperparameter Tuning

## One-Minute Overview

The automatic hyperparameter tuner works with your model to find the best hyperparameter configuration through intelligent search.

**Three search methods:**
- **Grid Search** - Systematic around current values
- **Random Search** - Broad exploration
- **Bayesian Search** - Smart focus on promising areas (recommended)

## Quick Commands

### Start Tuning

```bash
# Generate 20 configurations to test (no testing yet)
python retrain_model.py --tune --tune-method bayesian --tune-configs 20

# Actually run the tests (this takes a while)
python tune_orchestrator.py --method bayesian --configs 20

# See results
python retrain_model.py --tune-report
```

### Apply Best Configuration

```bash
python retrain_model.py --force --apply-hp '{"genre_weight": 0.42, "cast_weight": 0.15, ...}'
```

### View Progress

```bash
python tune_orchestrator.py --summary
```

## Files Added

| File | Purpose |
|------|---------|
| `hyperparameter_tuner.py` | Core tuning engine (search algorithms, database) |
| `tune_orchestrator.py` | Orchestrates full testing workflow |
| `HYPERPARAMETER_TUNER_GUIDE.md` | Complete documentation |
| Updated `retrain_model.py` | Added tuning CLI arguments |

## How It Works

```
Step 1: Generate Configurations
  python retrain_model.py --tune
        ↓
  Creates 20 (or N) hyperparameter configs to test
  
Step 2: Test Each Configuration  
  python tune_orchestrator.py --configs 20
        ↓
  Runs full retraining pipeline for each config
  Saves accuracy results to database
  
Step 3: Find Best
  python retrain_model.py --tune-report
        ↓
  Shows which configuration achieved best accuracy
  
Step 4: Apply Best
  python retrain_model.py --force --apply-hp <json>
        ↓
  Uses best hyperparameters for next training
```

## Hyperparameters Being Tuned

### Primary Weights (must sum to 1.0)
- Genre weight (currently 40%)
- Cast weight (currently 15%)
- Franchise weight (currently 5%)
- Rating weight (currently 30%)
- Popularity weight (currently 10%)

### Confidence Boosts
- High genre match boost (+15%)
- Medium genre match boost (+10%)
- Low genre match penalty (-20%)

### Cast Weighting (position-based)
- Lead actors: 1.0x weight
- Supporting: 0.7x weight
- Background: 0.3x weight

### Popularity Scoring
- Rating importance: 70%
- Count importance: 30%

## Integration with Existing System

✅ Works with model versioning system
✅ Uses model_versioning.py for tracking versions
✅ Integrates with retrain_model.py orchestration
✅ Stores results in existing movies.db database
✅ Tracks A/B testing capabilities

## Example: Full Tuning Session

```bash
# 1. Generate candidates (fast)
$ python retrain_model.py --tune --tune-method bayesian --tune-configs 30
[INFO] Generated 30 Bayesian configurations

# 2. Test each one (takes ~2-3 minutes)
$ python tune_orchestrator.py --method bayesian --configs 30
[INFO] Testing Configuration: bayesian_20251130_155355_001
[INFO] Configuration bayesian_20251130_155355_001 achieved 58% accuracy
[INFO] Improvement: +0.08%
... (repeat for all 30)

# 3. Check results
$ python retrain_model.py --tune-report
==================================================
HYPERPARAMETER TUNING REPORT
==================================================
TUNING STATISTICS:
├─ Total Experiments Run: 30
├─ Average Accuracy: 56.8%
├─ Best Accuracy Found: 59.2%
└─ Best Improvement: +0.85%

BEST CONFIGURATION:
├─ Experiment ID: bayesian_20251130_155355_015
├─ Accuracy: 59.2%
└─ Improvement: +0.85%

# 4. Apply best configuration
$ python retrain_model.py --force --apply-hp '{"genre_weight": 0.42, "cast_weight": 0.16, ...}'
[INFO] Applied 20 hyperparameters to model.py

# 5. Validate
$ python retrain_model.py --stats
Model version: v20251130_161520_abc123ef
Current accuracy: 59.2%
```

## Performance Impact

- **Tuning time per config:** ~5 seconds
- **30 configs:** ~2-3 minutes total
- **Database size:** Minimal (~500 bytes per experiment)
- **Model performance:** No change (tuning is offline)

## Next Steps

1. Run initial Bayesian tuning: `python tune_orchestrator.py --method bayesian --configs 30`
2. Review results: `python tune_orchestrator.py --summary`
3. Apply best: `python retrain_model.py --force --apply-hp <json>`
4. Validate with A/B test
5. Commit to git when improvements confirmed

## Detailed Guide

See `HYPERPARAMETER_TUNER_GUIDE.md` for:
- Complete parameter reference
- Advanced usage patterns
- Phase 2 tuning setup
- Troubleshooting
- Best practices
- Database schema

## Commands Reference

```bash
# Generation (fast)
python retrain_model.py --tune                           # Default bayesian
python retrain_model.py --tune --tune-method grid        # Grid search
python retrain_model.py --tune --tune-method random      # Random search
python retrain_model.py --tune --tune-configs 50         # Generate 50 configs

# Testing (slow)
python tune_orchestrator.py                              # Run full tuning
python tune_orchestrator.py --method grid                # Grid method
python tune_orchestrator.py --configs 50                 # Test 50 configs

# Reporting
python retrain_model.py --tune-report                    # Show progress
python tune_orchestrator.py --summary                    # Show summary
python tune_orchestrator.py --report                     # Detailed report

# Application
python retrain_model.py --force --apply-hp <json>        # Apply best config
python retrain_model.py --force --apply-hp <json> --dry-run  # Test first
```

---

**Start tuning now:**
```bash
python tune_orchestrator.py --method bayesian --configs 20
```
