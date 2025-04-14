
"""Tests for CloneStrategyAutotuner."""
import unittest
import time
from reflex_system.clone_strategy_autotuner import clone_strategy_autotuner

class TestCloneStrategyAutotuner(unittest.TestCase):
    """Test cases for CloneStrategyAutotuner."""
    
    def setUp(self):
        """Set up test environment."""
        self.tuner = clone_strategy_autotuner
        self.assertTrue(
            self.tuner._initialize(),
            "Failed to initialize autotuner"
        )
        
        self.test_strategy = {
            "risk_tolerance": 0.5,
            "resource_allocation": 0.5,
            "retry_attempts": 2
        }
        
    def test_strategy_tuning(self):
        """Test basic strategy tuning."""
        tuned = self.tuner.tune_strategy(
            "test_clone",
            self.test_strategy,
            {"risk_score": 0.3, "efficiency": 0.7}
        )
        
        self.assertIn("risk_tolerance", tuned)
        self.assertIn("resource_allocation", tuned)
        self.assertIn("retry_attempts", tuned)
        
    def test_mode_switching(self):
        """Test operation mode switching."""
        # Test defensive mode
        mode = self.tuner.get_recommended_mode(
            "test_clone",
            risk_score=0.9,
            performance_score=0.5
        )
        self.assertEqual(mode, "defensive")
        
        # Test aggressive mode
        mode = self.tuner.get_recommended_mode(
            "test_clone",
            risk_score=0.3,
            performance_score=0.3
        )
        self.assertEqual(mode, "aggressive")
        
        # Test balanced mode
        mode = self.tuner.get_recommended_mode(
            "test_clone",
            risk_score=0.5,
            performance_score=0.6
        )
        self.assertEqual(mode, "balanced")
        
    def test_high_risk_adaptation(self):
        """Test adaptation to high risk scenarios."""
        initial = self.tuner.tune_strategy(
            "risk_test_clone",
            self.test_strategy
        )
        
        # Simulate high risk
        tuned = self.tuner.tune_strategy(
            "risk_test_clone",
            self.test_strategy,
            {"risk_score": 0.9, "efficiency": 0.5}
        )
        
        self.assertLess(
            tuned["risk_tolerance"],
            initial["risk_tolerance"],
            "Risk tolerance should decrease for high risk"
        )

if __name__ == "__main__":
    unittest.main()
