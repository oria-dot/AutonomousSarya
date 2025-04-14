
"""Tests for the Spiritual Reflex system."""
import json
import time
import unittest
from unittest.mock import MagicMock, patch

from core.event_bus import Event
from reflex_system.spiritual_reflex import SpiritualReflex

class TestSpiritualReflex(unittest.TestCase):
    """Test cases for SpiritualReflex."""
    
    def setUp(self):
        """Set up test cases."""
        self.reflex = SpiritualReflex()
        self.reflex.symbol_map = {
            "alert": "awakening",
            "warning": "caution",
            "error": "challenge"
        }
        
    def test_signal_analysis(self):
        """Test signal analysis and insight generation."""
        event = Event(
            "reflex.signal",
            source="test",
            data={
                "type": "alert",
                "intensity": 0.9
            }
        )
        
        self.reflex._analyze_signal(event)
        
        self.assertEqual(len(self.reflex.insight_log), 1)
        insight = self.reflex.insight_log[0]
        self.assertEqual(insight["type"], "signal")
        self.assertEqual(insight["source"], "alert")
        self.assertTrue("Strong manifestation" in insight["insight"])
        
    def test_pattern_detection(self):
        """Test pattern detection in lifecycle events."""
        # Add repeated events
        for _ in range(3):
            event = Event(
                "clone.lifecycle",
                source="test",
                data={
                    "type": "start",
                    "clone_id": "test_clone"
                }
            )
            self.reflex._analyze_lifecycle(event)
            
        pattern = self.reflex._detect_pattern()
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern["type"], "repetition")
        self.assertEqual(pattern["event_type"], "start")

if __name__ == "__main__":
    unittest.main()
