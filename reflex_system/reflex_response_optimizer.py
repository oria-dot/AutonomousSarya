"""
Reflex Response Optimizer for SARYA.
Optimizes and tunes response thresholds based on historical performance.
"""
import logging
import time
from typing import Dict, Any, Optional
from core.base_module import BaseModule
from core.event_bus import event_bus

class ReflexResponseOptimizer(BaseModule):
    """Optimizes reflex responses based on historical data."""

    def __init__(self):
        super().__init__("ReflexResponseOptimizer")
        self.response_thresholds = {}
        self.performance_history = {}

    def _initialize(self) -> bool:
        """Initialize optimizer."""
        try:
            self.load_thresholds()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize optimizer: {e}")
            return False

    def optimize_response(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize response based on pattern analysis.

        Args:
            pattern: Pattern analysis results

        Returns:
            Optimized response parameters
        """
        response_type = pattern.get("type", "default")
        intensity = pattern.get("intensity", 0.5)

        # Get base thresholds
        thresholds = self.response_thresholds.get(
            response_type,
            {
                "min_intensity": 0.2,
                "max_intensity": 0.8,
                "scale_factor": 1.0
            }
        )

        # Apply optimization
        optimized = {
            "intensity": min(
                max(
                    intensity * thresholds["scale_factor"],
                    thresholds["min_intensity"]
                ),
                thresholds["max_intensity"]
            ),
            "type": response_type,
            "thresholds": thresholds
        }

        return optimized

    def update_thresholds(self, 
                         response_type: str,
                         performance: float) -> None:
        """
        Update thresholds based on performance feedback.

        Args:
            response_type: Type of response
            performance: Performance score (0-1)
        """
        if response_type not in self.response_thresholds:
            self.response_thresholds[response_type] = {
                "min_intensity": 0.2,
                "max_intensity": 0.8,
                "scale_factor": 1.0
            }

        # Update history
        if response_type not in self.performance_history:
            self.performance_history[response_type] = []
        self.performance_history[response_type].append(performance)

        # Adjust thresholds based on performance
        avg_performance = sum(self.performance_history[response_type][-5:]) / 5
        thresholds = self.response_thresholds[response_type]

        if avg_performance < 0.4:
            # Poor performance - increase sensitivity
            thresholds["scale_factor"] *= 1.1
            thresholds["min_intensity"] *= 0.9
        elif avg_performance > 0.8:
            # Good performance - decrease sensitivity
            thresholds["scale_factor"] *= 0.9
            thresholds["max_intensity"] *= 1.1

        # Save updated thresholds
        self.save_thresholds()

    def get_optimized_response(self,
                             clone_id: str,
                             response_type: str) -> Optional[Dict[str, Any]]:
        """
        Get optimized response for specific clone and type.

        Args:
            clone_id: Clone identifier
            response_type: Type of response

        Returns:
            Optimized response parameters
        """
        if response_type not in self.response_thresholds:
            return None

        return {
            "clone_id": clone_id,
            "type": response_type,
            "thresholds": self.response_thresholds[response_type]
        }

    def load_thresholds(self) -> None:
        """Load thresholds from storage."""
        stored = self.memory.get("response_thresholds")
        if stored:
            self.response_thresholds = stored

    def save_thresholds(self) -> None:
        """Save thresholds to storage."""
        self.memory.set("response_thresholds", self.response_thresholds)

# Initialize global instance
response_optimizer = ReflexResponseOptimizer()