"""Reflex Learning Engine for SARYA."""
import logging
import time
from typing import Dict, List, Optional
from core.base_module import BaseModule
from core.event_bus import event_bus
from core.memory import memory_system
from database import get_db

logger = logging.getLogger(__name__)

class ReflexLearningEngine(BaseModule):
    """Learns from reflex patterns and optimizes responses."""

    def __init__(self):
        super().__init__("ReflexLearningEngine")
        self.learning_data = {}
        self.pattern_weights = {}

    def _initialize(self) -> bool:
        """Initialize the learning engine."""
        try:
            # Load stored learning data
            stored_data = memory_system.get('reflex_learning_data', 'learning')
            if stored_data:
                self.learning_data = stored_data

            # Subscribe to pattern analysis events
            event_bus.subscribe(
                'pattern.analyzed',
                self._on_pattern_analyzed,
                subscriber_id='learning_engine'
            )

            return True
        except Exception as e:
            logger.error(f"Failed to initialize learning engine: {e}")
            return False

    def _on_pattern_analyzed(self, event):
        """Handle pattern analysis events."""
        pattern_data = event.data
        analysis = self.analyze_pattern(pattern_data)

        # Store analysis results
        self.learning_data[pattern_data['id']] = {
            'analysis': analysis,
            'timestamp': time.time()
        }

        # Update pattern weights
        self._update_pattern_weights(pattern_data, analysis)

    def analyze_pattern(self, pattern_data: Dict) -> Dict:
        """Analyze a reflex pattern for learning."""
        # Analyze pattern frequency
        frequency = pattern_data.get('frequency', 0)

        # Calculate success rate
        outcomes = pattern_data.get('outcomes', [])
        success_rate = len([o for o in outcomes if o['success']]) / len(outcomes) if outcomes else 0

        # Determine pattern significance
        significance = self._calculate_significance(frequency, success_rate)

        return {
            'frequency': frequency,
            'success_rate': success_rate,
            'significance': significance,
            'timestamp': time.time()
        }

    def _calculate_significance(self, frequency: float, success_rate: float) -> float:
        """Calculate pattern significance score."""
        # Simple weighted average of frequency and success rate
        return (frequency * 0.4 + success_rate * 0.6)

    def _update_pattern_weights(self, pattern_data: Dict, analysis: Dict):
        """Update learning weights for a pattern."""
        pattern_type = pattern_data.get('type', 'unknown')

        if pattern_type not in self.pattern_weights:
            self.pattern_weights[pattern_type] = 1.0

        # Adjust weight based on significance
        current_weight = self.pattern_weights[pattern_type]
        significance = analysis['significance']

        # Update weight with dampening
        self.pattern_weights[pattern_type] = (current_weight * 0.7 + significance * 0.3)

    def get_pattern_weight(self, pattern_type: str) -> float:
        """Get the current weight for a pattern type."""
        return self.pattern_weights.get(pattern_type, 1.0)

# Create singleton instance
reflex_learning_engine = ReflexLearningEngine()