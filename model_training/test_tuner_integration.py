#!/usr/bin/env python3
"""
Integration test for hyperparameter tuner system.
Verifies all components work together correctly.
"""

import sys
import json
import sqlite3
from pathlib import Path

def test_hyperparameter_tuner_import():
    """Test that hyperparameter_tuner module imports correctly."""
    try:
        from hyperparameter_tuner import (
            HyperparameterTuner,
            get_current_hyperparameters,
            generate_grid_search_space,
            generate_random_search_space,
            generate_bayesian_search_space,
            init_tuning_database,
            save_experiment,
            get_best_experiment,
            get_tuning_statistics
        )
        print("✓ hyperparameter_tuner imports successful")
        return True
    except Exception as e:
        print(f"✗ hyperparameter_tuner import failed: {e}")
        return False


def test_tune_orchestrator_import():
    """Test that tune_orchestrator module imports correctly."""
    try:
        from tune_orchestrator import TuningOrchestrator
        print("✓ tune_orchestrator imports successful")
        return True
    except Exception as e:
        print(f"✗ tune_orchestrator import failed: {e}")
        return False


def test_retrain_model_integration():
    """Test that retrain_model has tuning integration."""
    try:
        with open("retrain_model.py", "r") as f:
            content = f.read()
        
        required_imports = [
            "from hyperparameter_tuner import",
            "apply_hyperparameters",
            "run_hyperparameter_tuning"
        ]
        
        for required in required_imports:
            if required not in content:
                print(f"✗ retrain_model missing: {required}")
                return False
        
        print("✓ retrain_model tuning integration verified")
        return True
    except Exception as e:
        print(f"✗ retrain_model integration check failed: {e}")
        return False


def test_current_hyperparameters():
    """Test that current hyperparameters are accessible."""
    try:
        from hyperparameter_tuner import get_current_hyperparameters
        
        hp = get_current_hyperparameters()
        
        required_params = [
            "genre_weight", "cast_weight", "franchise_weight",
            "rating_weight", "popularity_weight",
            "genre_boost_high", "genre_boost_medium", "genre_boost_low",
            "cast_lead_weight", "cast_supporting_weight", "cast_background_weight",
            "popularity_rating_weight", "popularity_count_weight",
            "accuracy_threshold"
        ]
        
        for param in required_params:
            if param not in hp:
                print(f"✗ Missing hyperparameter: {param}")
                return False
        
        # Verify weights sum to approximately 1.0
        total_weight = (
            hp["genre_weight"] + hp["cast_weight"] + hp["franchise_weight"] +
            hp["rating_weight"] + hp["popularity_weight"]
        )
        
        if not (0.95 < total_weight < 1.05):
            print(f"✗ Weights don't sum to 1.0 (got {total_weight})")
            return False
        
        print(f"✓ Current hyperparameters valid (total weight: {total_weight:.4f})")
        return True
    except Exception as e:
        print(f"✗ Hyperparameter check failed: {e}")
        return False


def test_search_space_generation():
    """Test that search space generation works."""
    try:
        from hyperparameter_tuner import (
            HyperparameterTuner,
            get_current_hyperparameters
        )
        
        tuner = HyperparameterTuner()
        current_hp = get_current_hyperparameters()
        
        # Test grid search
        grid_configs = tuner.run_grid_search(search_radius=0.05, steps=1)
        if not isinstance(grid_configs, list) or len(grid_configs) == 0:
            print("✗ Grid search generation failed")
            return False
        print(f"✓ Grid search generated {len(grid_configs)} configurations")
        
        # Test random search
        random_configs = tuner.run_random_search(num_configs=10)
        if not isinstance(random_configs, list) or len(random_configs) != 10:
            print("✗ Random search generation failed")
            return False
        print(f"✓ Random search generated {len(random_configs)} configurations")
        
        # Test Bayesian search
        bayesian_configs = tuner.run_bayesian_search(num_configs=10)
        if not isinstance(bayesian_configs, list):
            print("✗ Bayesian search generation failed")
            return False
        print(f"✓ Bayesian search generated {len(bayesian_configs)} configurations")
        
        return True
    except Exception as e:
        print(f"✗ Search space generation test failed: {e}")
        return False


def test_database_operations():
    """Test database initialization and operations."""
    try:
        from hyperparameter_tuner import (
            init_tuning_database,
            save_experiment,
            get_best_experiment,
            get_tuning_statistics
        )
        
        # Initialize database
        init_tuning_database()
        
        # Check tables exist
        conn = sqlite3.connect("movies.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hp_experiments'
        """)
        
        if cursor.fetchone() is None:
            print("✗ hp_experiments table not found")
            conn.close()
            return False
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hp_tuning_history'
        """)
        
        if cursor.fetchone() is None:
            print("✗ hp_tuning_history table not found")
            conn.close()
            return False
        
        conn.close()
        
        print("✓ Database tables verified")
        return True
    except Exception as e:
        print(f"✗ Database operations test failed: {e}")
        return False


def test_documentation_files():
    """Test that all documentation files exist."""
    required_docs = [
        "HYPERPARAMETER_TUNER_GUIDE.md",
        "QUICK_START_TUNING.md",
        "TUNER_SYSTEM_SUMMARY.md"
    ]
    
    for doc in required_docs:
        if not Path(doc).exists():
            print(f"✗ Documentation file missing: {doc}")
            return False
        
        try:
            with open(doc, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) < 100:
                    print(f"✗ Documentation file too short: {doc}")
                    return False
        except UnicodeDecodeError:
            # Try with default encoding
            with open(doc, "r") as f:
                content = f.read()
                if len(content) < 100:
                    print(f"✗ Documentation file too short: {doc}")
                    return False
    
    print(f"✓ All {len(required_docs)} documentation files present")
    return True


def test_orchestrator_class():
    """Test TuningOrchestrator class initialization."""
    try:
        from tune_orchestrator import TuningOrchestrator
        
        orchestrator = TuningOrchestrator()
        
        if not hasattr(orchestrator, 'tuner'):
            print("✗ TuningOrchestrator missing 'tuner' attribute")
            return False
        
        if not hasattr(orchestrator, 'current_hp'):
            print("✗ TuningOrchestrator missing 'current_hp' attribute")
            return False
        
        if not hasattr(orchestrator, 'run_full_tuning'):
            print("✗ TuningOrchestrator missing 'run_full_tuning' method")
            return False
        
        print("✓ TuningOrchestrator class verified")
        return True
    except Exception as e:
        print(f"✗ TuningOrchestrator test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("HYPERPARAMETER TUNER INTEGRATION TEST")
    print("="*80 + "\n")
    
    tests = [
        ("Module Imports", [
            test_hyperparameter_tuner_import,
            test_tune_orchestrator_import
        ]),
        ("Integration Points", [
            test_retrain_model_integration,
        ]),
        ("Functionality", [
            test_current_hyperparameters,
            test_search_space_generation,
            test_database_operations,
            test_orchestrator_class
        ]),
        ("Documentation", [
            test_documentation_files
        ])
    ]
    
    results = {}
    total_passed = 0
    total_tests = 0
    
    for category, test_list in tests:
        print(f"\n{category}:")
        print("-" * 40)
        
        passed = 0
        for test_func in test_list:
            total_tests += 1
            if test_func():
                passed += 1
                total_passed += 1
        
        results[category] = (passed, len(test_list))
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for category, (passed, total) in results.items():
        status = "✓" if passed == total else "✗"
        print(f"{status} {category}: {passed}/{total} passed")
    
    print("-" * 40)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    print("="*80 + "\n")
    
    if total_passed == total_tests:
        print("✓ All integration tests passed!")
        print("\nReady to use:")
        print("  python retrain_model.py --tune")
        print("  python tune_orchestrator.py --method bayesian --configs 20")
        print("  python retrain_model.py --tune-report\n")
        return 0
    else:
        print(f"✗ {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
