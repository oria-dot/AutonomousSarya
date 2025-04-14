"""
Integration tests for SARYA reflex system modules.
"""
import unittest
import time
from typing import Dict, List
from datetime import datetime
from reflex_system.reflex_processor import reflex_processor
from reflex_system.reflex_learning_engine import reflex_learning_engine
from reflex_system.reflex_pattern_analyzer import reflex_pattern_analyzer
from reflex_system.reflex_response_optimizer import reflex_response_optimizer
from reflex_system.reflex_signal_router import ReflexSignalRouter
from reflex_system.clone_behavior_tracker import CloneBehaviorTracker
from reflex_system.clone_strategy_autotuner import CloneStrategyAutotuner

class TestReflexIntegration(unittest.TestCase):
    """Integration tests for reflex system modules."""
    
    def setUp(self):
        """Set up test environment."""
        # Initialize modules
        self.learning_engine = reflex_learning_engine
        self.pattern_analyzer = reflex_pattern_analyzer
        self.response_optimizer = reflex_response_optimizer
        
        # Initialize modules
        modules = [
            self.learning_engine,
            self.pattern_analyzer,
            self.response_optimizer
        ]
        for module in modules:
            self.assertTrue(
                module._initialize(),
                f"Failed to initialize {module.name}"
            )
            
    def test_learning_analysis(self):
        """Test learning engine analysis."""
        pattern_data = {
            "type": "test_pattern",
            "metrics": {
                "response_time": 500,
                "resource_usage": 50
            },
            "outcome": "success"
        }
        
        result = self.learning_engine.analyze_pattern(pattern_data)
        
        self.assertIn("pattern_type", result)
        self.assertIn("success_rate", result)
        self.assertIn("efficiency", result)
        self.assertIn("insights", result)
        
    def test_pattern_analysis(self):
        """Test pattern analyzer."""
        reflex_data = {
            "type": "test_reflex",
            "metrics": {
                "response_time": 800,
                "intensity": 0.9
            },
            "timestamp": time.time()
        }
        
        result = self.pattern_analyzer.analyze_pattern(reflex_data)
        
        self.assertIn("pattern_type", result)
        self.assertIn("frequency", result)
        self.assertIn("trend", result)
        self.assertIn("anomalies", result)
        
    def test_response_optimization(self):
        """Test response optimizer."""
        response_data = {
            "priority": "medium",
            "batch_size": 20,
            "resource_allocation": 60,
            "timeout": 2000,
            "retry_count": 3,
            "metrics": {
                "response_time": 1200,
                "resource_usage": 70
            }
        }
        
        optimized = self.response_optimizer.optimize_response(
            "test_reflex",
            response_data
        )
        
        self.assertIn("priority", optimized)
        self.assertIn("batch_size", optimized)
        self.assertIn("resource_allocation", optimized)
        self.assertTrue(
            optimized["resource_allocation"] <= 90,
            "Resource allocation exceeds maximum"
        )
        
    def test_end_to_end_flow(self):
        """Test complete reflex optimization flow."""
        # Initial reflex data
        reflex_data = {
            "type": "test_flow",
            "metrics": {
                "response_time": 1500,
                "resource_usage": 80,
                "intensity": 0.95
            },
            "timestamp": time.time()
        }
        
        # Analyze pattern
        pattern_result = self.pattern_analyzer.analyze_pattern(reflex_data)
        self.assertTrue(len(pattern_result["anomalies"]) > 0)
        
        # Get learning insights
        insights = self.learning_engine.get_insights("test_flow")
        
        # Optimize response
        response_data = {
            "priority": "low",
            "batch_size": 50,
            "resource_allocation": 70,
            "timeout": 3000,
            "retry_count": 4,
            "metrics": reflex_data["metrics"]
        }
        
        optimized = self.response_optimizer.optimize_response(
            "test_flow",
            response_data
        )
        
        # Verify optimizations
        self.assertLess(
            optimized["resource_allocation"],
            response_data["resource_allocation"]
        )
        self.assertLess(
            optimized["timeout"],
            response_data["timeout"]
        )

    #New tests from edited code start here

class TestReflexIntegration_New(unittest.TestCase):
    """Test integration between reflex system components."""

    def setUp(self):
        """Set up test environment."""
        self.learning_engine = ReflexLearningEngine()
        self.pattern_analyzer = ReflexPatternAnalyzer()
        self.response_optimizer = ReflexResponseOptimizer()
        self.signal_router = ReflexSignalRouter()
        self.behavior_tracker = CloneBehaviorTracker()
        self.strategy_autotuner = CloneStrategyAutotuner()

        # Initialize all components
        self.learning_engine._initialize()
        self.pattern_analyzer._initialize()
        self.response_optimizer._initialize()
        self.signal_router._initialize()
        self.behavior_tracker._initialize()
        self.strategy_autotuner._initialize()

    def test_reflex_signal_flow(self):
        """Test complete signal flow through reflex system."""
        # Create test signal
        test_signal = {
            "type": "risk_alert",
            "source": "clone_001",
            "intensity": 0.8,
            "data": {"risk_level": "high"}
        }

        # Route signal
        routed = self.signal_router.route_signal(test_signal)
        self.assertTrue(routed)

        # Track behavior
        tracked = self.behavior_tracker.log_action(
            "clone_001", 
            "risk_alert",
            {"risk_level": "high"}
        )
        self.assertTrue(tracked)

        # Analyze pattern
        pattern = self.pattern_analyzer.analyze_signal_pattern([test_signal])
        self.assertIsNotNone(pattern)

        # Generate response
        response = self.response_optimizer.optimize_response(pattern)
        self.assertIsNotNone(response)

        # Update strategy
        strategy = self.strategy_autotuner.adjust_strategy("clone_001", response)
        self.assertIsNotNone(strategy)

    def test_learning_cycle(self):
        """Test learning cycle with feedback."""
        # Initial signal
        test_signal = {
            "type": "trade_decision",
            "source": "clone_002",
            "intensity": 0.6,
            "data": {"decision": "buy"}
        }

        # Process signal
        self.signal_router.route_signal(test_signal)

        # Generate feedback
        feedback = {
            "success": True,
            "profit": 100,
            "risk_taken": 0.5
        }

        # Update learning
        learned = self.learning_engine.process_feedback(
            "clone_002",
            test_signal,
            feedback
        )
        self.assertTrue(learned)

        # Verify learning impact
        new_response = self.response_optimizer.get_optimized_response(
            "clone_002",
            "trade_decision"
        )
        self.assertIsNotNone(new_response)

    def tearDown(self):
        """Clean up test environment."""
        self.learning_engine._stop()
        self.pattern_analyzer._stop()
        self.response_optimizer._stop()
        self.signal_router._stop()
        self.behavior_tracker._stop()
        self.strategy_autotuner._stop()


class TestReflexIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.reflex_processor = reflex_processor
        self.learning_engine = reflex_learning_engine
        self.pattern_analyzer = reflex_pattern_analyzer
        self.response_optimizer = reflex_response_optimizer

    def test_reflex_processing(self):
        """Test complete reflex processing flow."""
        # Create test event
        event_data = {
            "event_type": "test_event",
            "source": "test_integration",
            "data": {
                "action": "test_action",
                "intensity": 0.7
            }
        }

        # Process event
        log_entry = self.reflex_processor.process_event(
            event_type=event_data["event_type"],
            source=event_data["source"],
            data=event_data["data"]
        )

        # Verify log entry
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry["event_type"], "test_event")
        self.assertEqual(log_entry["source"], "test_integration")

        # Test pattern analysis
        patterns = self.pattern_analyzer.analyze_patterns([log_entry])
        self.assertIsInstance(patterns, list)

        # Test learning
        self.learning_engine.learn_from_event(log_entry)
        learning_status = self.learning_engine.get_status()
        self.assertIn("total_events_processed", learning_status)

        # Test response optimization
        optimized_response = self.response_optimizer.optimize_response(
            event_type=event_data["event_type"],
            current_intensity=0.7
        )
        self.assertIsInstance(optimized_response["intensity"], float)

    def test_reflex_stats(self):
        """Test reflex statistics generation."""
        stats = self.reflex_processor.get_stats()
        
    def test_sync_validation(self):
        """Test reflex sync validation."""
        clone_id = "test_clone_001"
        reflex_data = {
            "sync_hash": "test_hash_123",
            "pattern": "test_pattern"
        }
        
        is_valid = reflex_sync_validator.validate_sync(clone_id, reflex_data)
        self.assertIsInstance(is_valid, bool)
        
    def test_memory_fusion(self):
        """Test memory link fusion."""
        clone_id = "test_clone_002"
        pattern = {"type": "test_pattern", "hash": "pattern_hash_123"}
        
        fused_state = memory_link_fusion.fuse_memory(clone_id, pattern)
        self.assertIn("fused_timestamp", fused_state)

        self.assertIsInstance(stats, dict)
        self.assertIn("total_events", stats)
        
    def test_integrity_sweep(self):
        """Test reflex integrity sweep."""
        sweep_result = reflex_integrity_sweep.perform_sweep()
        
        self.assertIsInstance(sweep_result, dict)
        self.assertIn("integrity_hash", sweep_result)
        self.assertTrue(sweep_result["state_archived"])
        
        # Verify archived state
        archived_state = memory_system.get(
            f"reflex_archive:{sweep_result['integrity_hash']}", 
            namespace="reflex_archives"
        )
        self.assertIsNotNone(archived_state)
        self.assertIn("top_emotions", stats)
        self.assertIn("top_symbols", stats)

if __name__ == '__main__':
    unittest.main()