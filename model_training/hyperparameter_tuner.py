"""
Automatic Hyperparameter Tuner

Systematically explores hyperparameter space to find optimal configurations.
Uses Bayesian optimization and grid search to improve model accuracy.
Works with model_versioning.py to test and validate new configurations.
"""

import sqlite3
import json
import logging
from datetime import datetime
from itertools import product
import random
import math
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HyperparameterTuner")

DB_PATH = "movies.db"


def init_tuning_database():
    """Initialize hyperparameter tuning results database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Hyperparameter experiments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hp_experiments (
            id INTEGER PRIMARY KEY,
            experiment_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            
            -- Hyperparameters
            genre_weight REAL,
            cast_weight REAL,
            franchise_weight REAL,
            rating_weight REAL,
            popularity_weight REAL,
            
            genre_boost_high REAL,
            genre_boost_medium REAL,
            genre_boost_low REAL,
            genre_threshold_high REAL,
            genre_threshold_medium REAL,
            genre_threshold_low REAL,
            
            cast_lead_weight REAL,
            cast_supporting_weight REAL,
            cast_background_weight REAL,
            cast_lead_threshold INTEGER,
            cast_supporting_threshold INTEGER,
            
            popularity_rating_weight REAL,
            popularity_count_weight REAL,
            
            accuracy_threshold REAL,
            
            -- Results
            test_accuracy REAL,
            improvement_from_baseline REAL,
            recommendation_quality_score REAL,
            
            tuning_method TEXT,
            parent_experiment_id TEXT
        )
    """)
    
    # Tuning history for tracking progress
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hp_tuning_history (
            id INTEGER PRIMARY KEY,
            tuning_run_id TEXT NOT NULL,
            iteration INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            best_accuracy REAL,
            best_experiment_id TEXT,
            exploration_phase TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("[TUNING] Initialized hyperparameter tuning database")


def get_current_hyperparameters():
    """Get current hyperparameters from model.py (Phase 1)."""
    return {
        "genre_weight": 0.40,
        "cast_weight": 0.15,
        "franchise_weight": 0.05,
        "rating_weight": 0.30,
        "popularity_weight": 0.10,
        
        "genre_boost_high": 0.15,
        "genre_boost_medium": 0.10,
        "genre_boost_low": -0.20,
        "genre_threshold_high": 0.7,
        "genre_threshold_medium": 0.5,
        "genre_threshold_low": 0.3,
        
        "cast_lead_weight": 1.0,
        "cast_supporting_weight": 0.7,
        "cast_background_weight": 0.3,
        "cast_lead_threshold": 5,
        "cast_supporting_threshold": 15,
        
        "popularity_rating_weight": 0.7,
        "popularity_count_weight": 0.3,
        
        "accuracy_threshold": 0.65
    }


def generate_grid_search_space(initial_hp, search_radius=0.1, steps=3):
    """
    Generate grid search space around current hyperparameters.
    
    Args:
        initial_hp: Current hyperparameters
        search_radius: How far to search (±10% by default)
        steps: Number of steps in each direction
    
    Returns:
        List of hyperparameter configurations
    """
    configs = []
    
    # Create search ranges for each weight parameter
    weight_params = [
        "genre_weight", "cast_weight", "franchise_weight", 
        "rating_weight", "popularity_weight"
    ]
    
    boost_params = ["genre_boost_high", "genre_boost_medium", "genre_boost_low"]
    cast_weight_params = ["cast_lead_weight", "cast_supporting_weight", "cast_background_weight"]
    popularity_params = ["popularity_rating_weight", "popularity_count_weight"]
    
    # Generate weight variations (keeping sum approximately 1.0)
    for genre in [initial_hp["genre_weight"] + delta * search_radius 
                   for delta in range(-steps, steps+1)]:
        for cast in [initial_hp["cast_weight"] + delta * search_radius 
                     for delta in range(-steps, steps+1)]:
            for franchise in [initial_hp["franchise_weight"] + delta * search_radius 
                             for delta in range(-steps, steps+1)]:
                for rating in [initial_hp["rating_weight"] + delta * search_radius 
                              for delta in range(-steps, steps+1)]:
                    
                    # Normalize to sum to 1.0
                    total = genre + cast + franchise + rating + initial_hp["popularity_weight"]
                    if total > 0:
                        config = initial_hp.copy()
                        config["genre_weight"] = max(0.01, genre / total * 0.90)
                        config["cast_weight"] = max(0.01, cast / total * 0.90)
                        config["franchise_weight"] = max(0.01, franchise / total * 0.90)
                        config["rating_weight"] = max(0.01, rating / total * 0.90)
                        config["popularity_weight"] = 1.0 - (
                            config["genre_weight"] + config["cast_weight"] + 
                            config["franchise_weight"] + config["rating_weight"]
                        )
                        
                        if all(v > 0 for v in [
                            config["genre_weight"], config["cast_weight"],
                            config["franchise_weight"], config["rating_weight"],
                            config["popularity_weight"]
                        ]):
                            configs.append(config)
    
    # Remove duplicates
    unique_configs = []
    seen = set()
    for config in configs:
        key = tuple((k, round(v, 3)) for k, v in sorted(config.items()))
        if key not in seen:
            seen.add(key)
            unique_configs.append(config)
    
    logger.info(f"[TUNING] Generated {len(unique_configs)} grid search configurations")
    return unique_configs


def generate_random_search_space(initial_hp, num_configs=50):
    """
    Generate random hyperparameter configurations for exploration.
    
    Args:
        initial_hp: Current hyperparameters as reference
        num_configs: Number of random configurations to generate
    
    Returns:
        List of hyperparameter configurations
    """
    configs = []
    
    for _ in range(num_configs):
        config = {}
        
        # Random weight distribution (must sum to 1.0)
        weights = [random.random() for _ in range(5)]
        total = sum(weights)
        normalized = [w / total for w in weights]
        
        config["genre_weight"] = normalized[0]
        config["cast_weight"] = normalized[1]
        config["franchise_weight"] = normalized[2]
        config["rating_weight"] = normalized[3]
        config["popularity_weight"] = normalized[4]
        
        # Random boost values
        config["genre_boost_high"] = random.uniform(0.05, 0.25)
        config["genre_boost_medium"] = random.uniform(0.05, 0.20)
        config["genre_boost_low"] = random.uniform(-0.30, -0.05)
        
        # Random thresholds
        config["genre_threshold_high"] = random.uniform(0.6, 0.8)
        config["genre_threshold_medium"] = random.uniform(0.4, 0.6)
        config["genre_threshold_low"] = random.uniform(0.2, 0.4)
        
        # Random cast weights
        config["cast_lead_weight"] = 1.0  # Keep fixed for stability
        config["cast_supporting_weight"] = random.uniform(0.5, 0.9)
        config["cast_background_weight"] = random.uniform(0.1, 0.5)
        
        # Random popularity weights
        config["popularity_rating_weight"] = random.uniform(0.6, 0.8)
        config["popularity_count_weight"] = 1.0 - config["popularity_rating_weight"]
        
        # Accuracy threshold
        config["accuracy_threshold"] = random.uniform(0.60, 0.70)
        
        configs.append(config)
    
    logger.info(f"[TUNING] Generated {num_configs} random configurations")
    return configs


def generate_bayesian_search_space(initial_hp, previous_experiments, num_configs=20):
    """
    Generate hyperparameter configurations using Bayesian optimization principles.
    
    Focuses search on regions of hyperparameter space that showed improvement.
    
    Args:
        initial_hp: Current hyperparameters
        previous_experiments: List of previous experiment results
        num_configs: Number of configurations to generate
    
    Returns:
        List of hyperparameter configurations
    """
    configs = []
    
    if not previous_experiments:
        logger.info("[TUNING] No previous experiments, using random search")
        return generate_random_search_space(initial_hp, num_configs)
    
    # Find best performing configurations
    sorted_experiments = sorted(
        previous_experiments,
        key=lambda x: x.get("improvement_from_baseline", 0),
        reverse=True
    )
    top_configs = sorted_experiments[:max(3, len(sorted_experiments) // 4)]
    
    logger.info(f"[TUNING] Bayesian search focusing on {len(top_configs)} best configs")
    
    # Generate variations around top performers
    for _ in range(num_configs):
        base_config = random.choice(top_configs)
        config = base_config.copy()
        
        # Add small perturbations
        perturbation_strength = 0.05
        
        # Perturb weights slightly
        perturbation = random.uniform(-perturbation_strength, perturbation_strength)
        config["genre_weight"] = max(0.01, config.get("genre_weight", 0.4) + perturbation)
        config["cast_weight"] = max(0.01, config.get("cast_weight", 0.15) + perturbation)
        
        # Normalize
        total = sum([
            config["genre_weight"], config["cast_weight"],
            config.get("franchise_weight", 0.05), config.get("rating_weight", 0.30),
            config.get("popularity_weight", 0.10)
        ])
        
        if total > 0:
            config["genre_weight"] = config["genre_weight"] / total * 0.90
            config["cast_weight"] = config["cast_weight"] / total * 0.90
        
        configs.append(config)
    
    return configs


def save_experiment(experiment_id, hyperparameters, accuracy, improvement, method, parent_id=None):
    """Save hyperparameter experiment results."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO hp_experiments
        (experiment_id, status, genre_weight, cast_weight, franchise_weight, rating_weight,
         popularity_weight, genre_boost_high, genre_boost_medium, genre_boost_low,
         genre_threshold_high, genre_threshold_medium, genre_threshold_low,
         cast_lead_weight, cast_supporting_weight, cast_background_weight,
         cast_lead_threshold, cast_supporting_threshold, popularity_rating_weight,
         popularity_count_weight, accuracy_threshold, test_accuracy, improvement_from_baseline,
         tuning_method, parent_experiment_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        experiment_id,
        "completed",
        hyperparameters.get("genre_weight"),
        hyperparameters.get("cast_weight"),
        hyperparameters.get("franchise_weight"),
        hyperparameters.get("rating_weight"),
        hyperparameters.get("popularity_weight"),
        hyperparameters.get("genre_boost_high"),
        hyperparameters.get("genre_boost_medium"),
        hyperparameters.get("genre_boost_low"),
        hyperparameters.get("genre_threshold_high"),
        hyperparameters.get("genre_threshold_medium"),
        hyperparameters.get("genre_threshold_low"),
        hyperparameters.get("cast_lead_weight"),
        hyperparameters.get("cast_supporting_weight"),
        hyperparameters.get("cast_background_weight"),
        hyperparameters.get("cast_lead_threshold"),
        hyperparameters.get("cast_supporting_threshold"),
        hyperparameters.get("popularity_rating_weight"),
        hyperparameters.get("popularity_count_weight"),
        hyperparameters.get("accuracy_threshold"),
        accuracy,
        improvement,
        method,
        parent_id
    ))
    
    conn.commit()
    conn.close()


def get_best_experiment():
    """Get the best performing hyperparameter configuration found so far."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM hp_experiments
        WHERE status = 'completed'
        ORDER BY improvement_from_baseline DESC, test_accuracy DESC
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "experiment_id": result["experiment_id"],
            "test_accuracy": result["test_accuracy"],
            "improvement": result["improvement_from_baseline"]
        }
    
    return None


def get_tuning_statistics():
    """Get statistics about tuning progress."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_experiments,
            AVG(test_accuracy) as avg_accuracy,
            MAX(test_accuracy) as best_accuracy,
            MAX(improvement_from_baseline) as best_improvement
        FROM hp_experiments
        WHERE status = 'completed'
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    return {
        "total_experiments": result[0] or 0,
        "avg_accuracy": result[1] or 0,
        "best_accuracy": result[2] or 0,
        "best_improvement": result[3] or 0
    }


def generate_tuning_report():
    """Generate comprehensive tuning report."""
    stats = get_tuning_statistics()
    best = get_best_experiment()
    
    report = f"""
{'='*80}
HYPERPARAMETER TUNING REPORT
{'='*80}

TUNING STATISTICS:
├─ Total Experiments Run: {stats['total_experiments']}
├─ Average Accuracy: {stats['avg_accuracy']:.2%}
├─ Best Accuracy Found: {stats['best_accuracy']:.2%}
└─ Best Improvement: {stats['best_improvement']:+.2%}

BEST CONFIGURATION:
├─ Experiment ID: {best['experiment_id'] if best else 'N/A'}
├─ Accuracy: {best['test_accuracy']:.2%}
└─ Improvement: {best['improvement']:+.2%}

{'='*80}
"""
    
    return report


class HyperparameterTuner:
    """Orchestrates hyperparameter tuning process."""
    
    def __init__(self, tuning_id=None):
        self.tuning_id = tuning_id or f"tune_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.initial_hp = get_current_hyperparameters()
        init_tuning_database()
    
    def run_grid_search(self, search_radius=0.1, steps=3):
        """Run grid search over hyperparameter space."""
        logger.info(f"[TUNING] Starting grid search (radius={search_radius}, steps={steps})")
        
        configs = generate_grid_search_space(self.initial_hp, search_radius, steps)
        
        logger.info(f"[TUNING] Grid search will evaluate {len(configs)} configurations")
        logger.info(f"[TUNING] Recommend running: python retrain_model.py --force for each config")
        
        return configs
    
    def run_random_search(self, num_configs=50):
        """Run random search over hyperparameter space."""
        logger.info(f"[TUNING] Starting random search ({num_configs} configs)")
        
        configs = generate_random_search_space(self.initial_hp, num_configs)
        
        return configs
    
    def run_bayesian_search(self, num_configs=20):
        """Run Bayesian optimization search."""
        logger.info(f"[TUNING] Starting Bayesian search ({num_configs} configs)")
        
        # Get previous experiments using named columns
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM hp_experiments 
            WHERE status = 'completed'
            ORDER BY improvement_from_baseline DESC
            LIMIT 50
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to dict format with proper type conversion
        previous = []
        for row in rows:
            previous.append({
                "genre_weight": float(row["genre_weight"]) if row["genre_weight"] is not None else 0.4,
                "cast_weight": float(row["cast_weight"]) if row["cast_weight"] is not None else 0.15,
                "franchise_weight": float(row["franchise_weight"]) if row["franchise_weight"] is not None else 0.05,
                "rating_weight": float(row["rating_weight"]) if row["rating_weight"] is not None else 0.30,
                "popularity_weight": float(row["popularity_weight"]) if row["popularity_weight"] is not None else 0.10,
                "improvement_from_baseline": float(row["improvement_from_baseline"]) if row["improvement_from_baseline"] is not None else 0
            })
        
        configs = generate_bayesian_search_space(self.initial_hp, previous, num_configs)
        
        return configs


def compare_configurations(config1, config2):
    """Compare two hyperparameter configurations."""
    comparison = {
        "differences": {},
        "similarities": []
    }
    
    for key in config1:
        if key in config2:
            if abs(config1[key] - config2[key]) > 0.001:
                comparison["differences"][key] = {
                    "config1": config1[key],
                    "config2": config2[key],
                    "delta": config2[key] - config1[key]
                }
            else:
                comparison["similarities"].append(key)
    
    return comparison


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python hyperparameter_tuner.py [grid|random|bayesian|report]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    tuner = HyperparameterTuner()
    
    if mode == "grid":
        configs = tuner.run_grid_search(search_radius=0.1, steps=2)
        print(f"\nGenerated {len(configs)} grid search configurations")
        print("Save to file and use with retrain_model.py")
    
    elif mode == "random":
        configs = tuner.run_random_search(num_configs=50)
        print(f"\nGenerated {len(configs)} random configurations")
    
    elif mode == "bayesian":
        configs = tuner.run_bayesian_search(num_configs=20)
        print(f"\nGenerated {len(configs)} Bayesian configurations")
    
    elif mode == "report":
        print(generate_tuning_report())
    
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
