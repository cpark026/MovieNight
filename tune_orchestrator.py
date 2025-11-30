#!/usr/bin/env python3
"""
Hyperparameter Tuning Orchestrator

Coordinates the entire hyperparameter tuning workflow:
1. Generates candidate configurations
2. Tests each configuration
3. Tracks results in database
4. Recommends best configuration
5. Applies best configuration to model
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import argparse

from hyperparameter_tuner import (
    HyperparameterTuner,
    get_current_hyperparameters,
    save_experiment,
    get_best_experiment,
    get_tuning_statistics,
    generate_tuning_report
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TuningOrchestrator")


class TuningOrchestrator:
    """Orchestrates the complete tuning workflow."""
    
    def __init__(self):
        self.tuner = HyperparameterTuner()
        self.current_hp = get_current_hyperparameters()
    
    def test_configuration(self, config, config_id):
        """
        Test a specific hyperparameter configuration.
        
        Args:
            config: Dict of hyperparameters
            config_id: String ID for this configuration
        
        Returns:
            Accuracy achieved with this configuration
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing Configuration: {config_id}")
        logger.info(f"{'='*80}")
        
        # Convert config to JSON for retrain_model.py
        config_json = json.dumps(config)
        
        try:
            # Run retraining with this configuration
            cmd = [
                sys.executable, "retrain_model.py",
                "--force",
                "--apply-hp", config_json
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Configuration {config_id} failed:")
                logger.error(result.stderr)
                return None
            
            logger.info(result.stdout)
            
            # Extract accuracy from output
            accuracy = self._extract_accuracy(result.stdout)
            
            if accuracy:
                improvement = accuracy - self.current_hp.get("accuracy_threshold", 0.65)
                logger.info(f"Configuration {config_id} achieved {accuracy:.2%} accuracy")
                logger.info(f"Improvement: {improvement:+.2%}")
                
                # Save to database
                save_experiment(
                    experiment_id=config_id,
                    hyperparameters=config,
                    accuracy=accuracy,
                    improvement=improvement,
                    method="test",
                    parent_id=None
                )
                
                return accuracy
            else:
                logger.warning(f"Could not extract accuracy from output")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"Configuration {config_id} timed out")
            return None
        except Exception as e:
            logger.error(f"Error testing configuration {config_id}: {e}")
            return None
    
    def _extract_accuracy(self, output):
        """Extract accuracy metric from output."""
        import re
        
        # Look for "Accuracy: XX%" pattern
        patterns = [
            r"Accuracy[:\s]+(\d+\.?\d*)\s*%",
            r"accuracy[:\s]+(\d+\.?\d*)\s*%",
            r"(\d+\.?\d*)\s*%\s*accuracy"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return float(match.group(1)) / 100
        
        return None
    
    def run_full_tuning(self, method="bayesian", num_configs=20):
        """
        Run complete tuning workflow.
        
        Args:
            method: 'grid', 'random', or 'bayesian'
            num_configs: Number of configurations to test
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"STARTING FULL HYPERPARAMETER TUNING")
        logger.info(f"Method: {method}, Configurations: {num_configs}")
        logger.info(f"{'='*80}\n")
        
        # Generate configurations
        if method == "grid":
            configs = self.tuner.run_grid_search(search_radius=0.1, steps=2)
        elif method == "random":
            configs = self.tuner.run_random_search(num_configs)
        else:  # bayesian
            configs = self.tuner.run_bayesian_search(num_configs)
        
        logger.info(f"Generated {len(configs)} configurations\n")
        
        results = []
        for i, config in enumerate(configs, 1):
            config_id = f"{method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}"
            
            accuracy = self.test_configuration(config, config_id)
            
            if accuracy:
                results.append({
                    "config_id": config_id,
                    "accuracy": accuracy,
                    "config": config
                })
            
            # Progress update every 5 configurations
            if i % 5 == 0:
                logger.info(f"\nTuning Progress: {i}/{len(configs)} configurations tested")
                best = get_best_experiment()
                if best:
                    logger.info(f"Best so far: {best['experiment_id']} with {best['test_accuracy']:.2%} accuracy\n")
        
        return results
    
    def run_phase_2_tuning(self):
        """
        Run Phase 2 specific tuning to optimize new components.
        Focus on user preference weights and franchise scaling.
        """
        logger.info(f"\n{'='*80}")
        logger.info("PHASE 2 HYPERPARAMETER TUNING")
        logger.info(f"{'='*80}\n")
        
        phase2_configs = []
        
        # Generate variations for Phase 2 parameters
        for user_pref_weight in [0.05, 0.10, 0.15, 0.20]:
            for franchise_scale in [1.0, 1.2, 1.5, 2.0]:
                for rating_model_weight in [0.05, 0.10, 0.15]:
                    config = get_current_hyperparameters()
                    
                    # Phase 2 additions
                    config["user_preference_weight"] = user_pref_weight
                    config["franchise_depth_scale"] = franchise_scale
                    config["rating_prediction_weight"] = rating_model_weight
                    
                    phase2_configs.append(config)
        
        logger.info(f"Generated {len(phase2_configs)} Phase 2 configurations")
        
        return phase2_configs
    
    def generate_tuning_summary(self):
        """Generate summary of all tuning runs."""
        stats = get_tuning_statistics()
        best = get_best_experiment()
        
        summary = f"""
{'='*80}
HYPERPARAMETER TUNING SUMMARY
{'='*80}

Total Experiments: {stats['total_experiments']}
Average Accuracy: {stats['avg_accuracy']:.2%}
Best Accuracy: {stats['best_accuracy']:.2%}
Best Improvement: {stats['best_improvement']:+.2%}

Best Configuration:
  Experiment ID: {best['experiment_id'] if best else 'N/A'}
  Accuracy: {best['test_accuracy']:.2%}
  Improvement: {best['improvement']:+.2%}

Next Steps:
1. Review best configuration in database
2. Run: python retrain_model.py --tune-report
3. Apply best config: python retrain_model.py --apply-hp <json>
4. Validate with A/B test
5. Merge to main branch

{'='*80}
"""
        
        return summary


def main():
    parser = argparse.ArgumentParser(description="Hyperparameter Tuning Orchestrator")
    parser.add_argument("--method", default="bayesian", choices=["grid", "random", "bayesian"],
                        help="Tuning method to use")
    parser.add_argument("--configs", type=int, default=20,
                        help="Number of configurations to test")
    parser.add_argument("--phase2", action="store_true",
                        help="Run Phase 2 specific tuning")
    parser.add_argument("--summary", action="store_true",
                        help="Show tuning summary and exit")
    parser.add_argument("--report", action="store_true",
                        help="Show detailed tuning report")
    
    args = parser.parse_args()
    
    orchestrator = TuningOrchestrator()
    
    if args.summary:
        print(orchestrator.generate_tuning_summary())
        return 0
    
    if args.report:
        print(generate_tuning_report())
        return 0
    
    if args.phase2:
        configs = orchestrator.run_phase_2_tuning()
        print(f"\nGenerated {len(configs)} Phase 2 configurations")
        print("Run with: python tune_orchestrator.py --method bayesian --configs 50")
        return 0
    
    # Run full tuning
    results = orchestrator.run_full_tuning(args.method, args.configs)
    
    print(orchestrator.generate_tuning_summary())
    
    if results:
        logger.info(f"\nTesting complete. Tested {len(results)} configurations successfully.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
