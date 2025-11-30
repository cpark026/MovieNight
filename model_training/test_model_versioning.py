"""
Unit Tests for Model Versioning and Weighted Retraining System

Tests:
1. Database initialization
2. Weighted training data extraction
3. Model version creation and management
4. Performance evaluation
5. Model performance tracking
6. A/B testing framework
"""

import unittest
import sqlite3
import os
import sys
import uuid
from datetime import datetime, timedelta
import tempfile
import shutil

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model_versioning import (
    init_model_versioning,
    get_active_model_version,
    create_weighted_training_data,
    create_model_version,
    evaluate_model_version,
    activate_model_version,
    should_retrain,
    get_model_stats,
    start_ab_test,
    evaluate_ab_test
)


class TestModelVersioning(unittest.TestCase):
    """Test model versioning system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.test_db = "test_models.db"
        cls.original_db = "movies.db"
        
        # Use test database
        import model_versioning
        model_versioning.DB_PATH = cls.test_db
    
    def setUp(self):
        """Initialize clean test database before each test"""
        # Remove test DB if exists
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        # Create test database with required tables
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Create movies table (needed for data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY,
                title TEXT UNIQUE,
                rating REAL
            )
        """)
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        
        # Create recommendation_quality table for testing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_quality (
                id INTEGER PRIMARY KEY,
                set_id INTEGER,
                user_id TEXT,
                movie_id REAL,
                title TEXT,
                predicted_score REAL,
                actual_rating REAL,
                quality_score REAL,
                was_correct INTEGER,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize versioning
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        init_model_versioning()
    
    def tearDown(self):
        """Clean up test database"""
        try:
            if os.path.exists(self.test_db):
                os.remove(self.test_db)
        except:
            pass  # Ignore cleanup errors on Windows
    
    def _insert_sample_recommendations(self, count=20, accuracy=0.7):
        """Helper to insert sample recommendation quality data"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        movies = [
            ("The Matrix", 8.5),
            ("Inception", 8.8),
            ("Interstellar", 8.6),
            ("Pulp Fiction", 8.9),
            ("Fight Club", 8.8)
        ]
        
        for i in range(count):
            movie_title, base_rating = movies[i % len(movies)]
            predicted = base_rating + (0.5 if i % 3 == 0 else -0.2)
            actual = base_rating + (0.1 if i % 2 == 0 else -0.3)
            is_correct = abs(predicted - actual) <= 0.2
            
            cursor.execute("""
                INSERT INTO recommendation_quality
                (user_id, movie_id, title, predicted_score, actual_rating, was_correct, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-' || ? || ' days'))
            """, (f"user_{i%3}", i, movie_title, predicted, actual, int(is_correct), i % 7))
        
        conn.commit()
        conn.close()
    
    # ========================
    # Test 1: Database Initialization
    # ========================
    def test_01_init_model_versioning(self):
        """Test that model versioning tables are created"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check model_versions table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='model_versions'
        """)
        self.assertIsNotNone(cursor.fetchone(), "model_versions table not created")
        
        # Check ab_tests table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ab_tests'
        """)
        self.assertIsNotNone(cursor.fetchone(), "ab_tests table not created")
        
        # Check model_performance_log table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='model_performance_log'
        """)
        self.assertIsNotNone(cursor.fetchone(), "model_performance_log table not created")
        
        conn.close()
    
    # ========================
    # Test 2: Weighted Training Data
    # ========================
    def test_02_create_weighted_training_data(self):
        """Test extraction of weighted training data"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        data = create_weighted_training_data(days_back=30, min_samples=1)
        
        self.assertIsNotNone(data, "Failed to create weighted training data")
        self.assertIn("movie_stats", data)
        self.assertIn("total_predictions", data)
        self.assertGreater(len(data["movie_stats"]), 0, "No movies in weighted data")
        
        # Check movie stats structure
        for movie_id, stats in data["movie_stats"].items():
            self.assertIn("title", stats)
            self.assertIn("predictions", stats)
            self.assertIn("accuracy", stats)
            self.assertIn("weight", stats)
            self.assertGreater(stats["weight"], 0)
    
    def test_02b_weighted_data_empty(self):
        """Test handling of empty training data"""
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        data = create_weighted_training_data(days_back=30, min_samples=1)
        
        self.assertIsNone(data, "Should return None for empty data")
    
    # ========================
    # Test 3: Model Version Creation
    # ========================
    def test_03_create_model_version(self):
        """Test creating a new model version"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        self.assertIsNotNone(weights_data)
        
        new_version = create_model_version(
            "v1_initial",
            weights_data,
            reason="test_creation"
        )
        
        self.assertIsNotNone(new_version)
        self.assertTrue(new_version.startswith("v"))
        
        # Verify in database
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM model_versions WHERE version_id = ?", (new_version,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "training")
    
    # ========================
    # Test 4: Model Evaluation
    # ========================
    def test_04_evaluate_model_version(self):
        """Test evaluating model version accuracy"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        new_version = create_model_version("v1_initial", weights_data)
        
        metrics = evaluate_model_version(new_version)
        
        self.assertIsNotNone(metrics)
        self.assertIn("accuracy", metrics)
        self.assertIn("avg_error", metrics)
        self.assertIn("correct_predictions", metrics)
        
        # Verify metrics are reasonable
        self.assertGreaterEqual(metrics["accuracy"], 0)
        self.assertLessEqual(metrics["accuracy"], 1)
        self.assertGreater(metrics["total_predictions"], 0)
    
    # ========================
    # Test 5: Get Active Version
    # ========================
    def test_05_get_active_model_version(self):
        """Test retrieving active model version"""
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        active = get_active_model_version()
        
        # Should return default if no active version
        self.assertIsNotNone(active)
        self.assertTrue(len(active) > 0)
    
    # ========================
    # Test 6: Model Stats
    # ========================
    def test_06_get_model_stats(self):
        """Test getting model statistics"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        v1 = create_model_version("v1_initial", weights_data)
        evaluate_model_version(v1)
        
        stats = get_model_stats()
        
        self.assertIn("versions", stats)
        self.assertIn("total_versions", stats)
        self.assertIn("active_version", stats)
        self.assertGreater(stats["total_versions"], 0)
    
    # ========================
    # Test 7: Retraining Decision
    # ========================
    def test_07_should_retrain(self):
        """Test retraining decision logic"""
        self._insert_sample_recommendations(count=20, accuracy=0.4)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        needs_retrain, accuracy = should_retrain(accuracy_threshold=0.65)
        
        self.assertIsInstance(needs_retrain, bool)
        self.assertIsInstance(accuracy, float)
        self.assertGreaterEqual(accuracy, 0)
        self.assertLessEqual(accuracy, 1)
    
    # ========================
    # Test 8: Version Activation
    # ========================
    def test_08_activate_model_version(self):
        """Test activating a model version"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        new_version = create_model_version("v1_initial", weights_data)
        evaluate_model_version(new_version)
        
        activate_model_version(new_version)
        
        # Verify activation
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM model_versions WHERE version_id = ?", (new_version,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "active")
    
    # ========================
    # Test 9: A/B Testing
    # ========================
    def test_09_start_ab_test(self):
        """Test starting an A/B test"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        # Create two versions
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        v1 = create_model_version("v1_initial", weights_data, reason="test_v1")
        v2 = create_model_version("v1_initial", weights_data, reason="test_v2")
        
        evaluate_model_version(v1)
        evaluate_model_version(v2)
        
        # Start A/B test
        test_id = start_ab_test(v1, v2, duration_hours=24)
        
        self.assertIsNotNone(test_id)
        self.assertTrue(test_id.startswith("test_"))
        
        # Verify test in database
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM ab_tests WHERE test_id = ?", (test_id,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "running")
    
    def test_09b_evaluate_ab_test(self):
        """Test evaluating A/B test results"""
        self._insert_sample_recommendations(count=20)
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        v1 = create_model_version("v1_initial", weights_data, reason="test_v1")
        v2 = create_model_version("v1_initial", weights_data, reason="test_v2")
        
        evaluate_model_version(v1)
        evaluate_model_version(v2)
        
        test_id = start_ab_test(v1, v2)
        results = evaluate_ab_test(test_id)
        
        self.assertIsNotNone(results)
        self.assertIn("winner", results)
        self.assertIn("confidence", results)
        self.assertIn("accuracy_a", results)
        self.assertIn("accuracy_b", results)
    
    # ========================
    # Test 10: Performance Tracking
    # ========================
    def test_10_model_accuracy_trends(self):
        """Test tracking model accuracy over time"""
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        # Insert recommendations over time
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Day 1: 70% accuracy
        for i in range(10):
            is_correct = i < 3  # 30% accuracy
            cursor.execute("""
                INSERT INTO recommendation_quality
                (user_id, movie_id, title, predicted_score, actual_rating, was_correct, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-1 day'))
            """, (f"user_1", i, f"Movie {i}", 8.0, 8.2 if is_correct else 5.0, int(is_correct)))
        
        # Day 2: 20% accuracy
        for i in range(10):
            is_correct = i < 2
            cursor.execute("""
                INSERT INTO recommendation_quality
                (user_id, movie_id, title, predicted_score, actual_rating, was_correct, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-2 days'))
            """, (f"user_1", i+10, f"Movie {i+10}", 8.0, 8.2 if is_correct else 5.0, int(is_correct)))
        
        conn.commit()
        conn.close()
        
        # Check recent accuracy (25% average)
        needs_retrain, accuracy = should_retrain(accuracy_threshold=0.65)
        
        # Should trigger retraining due to low accuracy
        self.assertTrue(needs_retrain)


class TestModelPerformanceComparison(unittest.TestCase):
    """Test comparing model performance between versions"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.test_db = "test_performance.db"
    
    def setUp(self):
        """Initialize clean test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_quality (
                id INTEGER PRIMARY KEY,
                set_id INTEGER,
                user_id TEXT,
                movie_id REAL,
                title TEXT,
                predicted_score REAL,
                actual_rating REAL,
                quality_score REAL,
                was_correct INTEGER,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        init_model_versioning()
    
    def tearDown(self):
        """Clean up test database"""
        try:
            if os.path.exists(self.test_db):
                os.remove(self.test_db)
        except:
            pass  # Ignore cleanup errors on Windows
    
    def test_version_improvement_calculation(self):
        """Test calculating improvement between versions"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Insert v1 performance (80% accuracy)
        for i in range(10):
            cursor.execute("""
                INSERT INTO recommendation_quality
                (user_id, movie_id, title, predicted_score, actual_rating, was_correct)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"user_1", i, f"Movie {i}", 8.0, 8.2 if i < 8 else 5.0, i < 8))
        
        conn.commit()
        conn.close()
        
        import model_versioning
        model_versioning.DB_PATH = self.test_db
        
        weights_data = create_weighted_training_data(days_back=30, min_samples=1)
        self.assertIsNotNone(weights_data)
        
        v1 = create_model_version("v0", weights_data, reason="baseline")
        metrics_v1 = evaluate_model_version(v1)
        
        self.assertIsNotNone(metrics_v1)
        self.assertGreater(metrics_v1["accuracy"], 0)


def run_tests(verbose=True):
    """Run all tests and generate report"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestModelVersioning))
    suite.addTests(loader.loadTestsFromTestCase(TestModelPerformanceComparison))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
