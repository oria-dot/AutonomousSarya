
"""
Reflex Pattern Analyzer for SARYA.
Analyzes reflex patterns and identifies significant patterns and anomalies.
"""
import logging
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from core.base_module import BaseModule
from core.memory import memory_system
from reflex_system.reflex_learning_engine import reflex_learning_engine

logger = logging.getLogger(__name__)

class ReflexPatternAnalyzer(BaseModule):
    """
    Analyzes reflex patterns to identify trends and anomalies.
    
    Features:
    - Pattern detection
    - Anomaly detection
    - Trend analysis
    - Pattern classification
    """
    
    def __init__(self):
        super().__init__("ReflexPatternAnalyzer")
        self.pattern_history = defaultdict(list)
        self.anomaly_thresholds = {
            "response_time": 1000,  # ms
            "frequency": 100,       # events/min
            "intensity": 0.8        # 0-1 scale
        }
        
    def _initialize(self) -> bool:
        """Initialize the pattern analyzer."""
        try:
            # Load stored patterns
            stored_patterns = memory_system.get(
                "reflex_patterns",
                namespace="analysis"
            )
            if stored_patterns:
                self.pattern_history = defaultdict(list, stored_patterns)
                
            logger.info("Pattern analyzer initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing pattern analyzer: {e}")
            return False
            
    def _start(self) -> bool:
        """Start the pattern analyzer."""
        return True
        
    def _stop(self) -> bool:
        """Stop the pattern analyzer."""
        # Save pattern history
        try:
            memory_system.set(
                "reflex_patterns",
                dict(self.pattern_history),
                namespace="analysis"
            )
            return True
        except Exception as e:
            logger.error(f"Error saving pattern history: {e}")
            return False
            
    def analyze_pattern(self, reflex_data: Dict) -> Dict:
        """
        Analyze a reflex pattern.
        
        Args:
            reflex_data: Reflex data to analyze
            
        Returns:
            Dict containing analysis results
        """
        pattern_type = reflex_data.get("type", "unknown")
        timestamp = reflex_data.get("timestamp", time.time())
        metrics = reflex_data.get("metrics", {})
        
        # Store pattern
        self.pattern_history[pattern_type].append({
            "data": reflex_data,
            "timestamp": timestamp
        })
        
        # Keep only last 1000 patterns
        if len(self.pattern_history[pattern_type]) > 1000:
            self.pattern_history[pattern_type] = \
                self.pattern_history[pattern_type][-1000:]
        
        # Analyze components
        frequency = self._analyze_frequency(pattern_type)
        trend = self._analyze_trend(pattern_type)
        anomalies = self._detect_anomalies(reflex_data)
        
        # Get learning insights
        insights = reflex_learning_engine.get_insights(pattern_type)
        
        return {
            "pattern_type": pattern_type,
            "frequency": frequency,
            "trend": trend,
            "anomalies": anomalies,
            "insights": insights,
            "timestamp": timestamp
        }
        
    def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, List[Dict]]:
        """
        Get stored patterns.
        
        Args:
            pattern_type: Optional type to filter by
            limit: Maximum patterns to return
            
        Returns:
            Dict of pattern lists by type
        """
        if pattern_type:
            patterns = self.pattern_history.get(pattern_type, [])
            return {pattern_type: patterns[-limit:]}
        
        return {
            ptype: patterns[-limit:]
            for ptype, patterns in self.pattern_history.items()
        }
        
    def _analyze_frequency(self, pattern_type: str) -> Dict:
        """Analyze pattern frequency."""
        patterns = self.pattern_history[pattern_type]
        if not patterns:
            return {"current": 0, "average": 0}
            
        # Calculate events per minute
        now = time.time()
        recent_patterns = [
            p for p in patterns
            if now - p["timestamp"] <= 60
        ]
        current_frequency = len(recent_patterns)
        
        # Calculate average frequency
        total_time = patterns[-1]["timestamp"] - patterns[0]["timestamp"]
        if total_time > 0:
            avg_frequency = len(patterns) / (total_time / 60)
        else:
            avg_frequency = 0
            
        return {
            "current": current_frequency,
            "average": avg_frequency
        }
        
    def _analyze_trend(self, pattern_type: str) -> Dict:
        """Analyze pattern trends."""
        patterns = self.pattern_history[pattern_type]
        if len(patterns) < 2:
            return {"direction": "stable", "strength": 0}
            
        # Simple trend analysis based on frequency change
        old_freq = len([
            p for p in patterns
            if time.time() - p["timestamp"] <= 120
            and time.time() - p["timestamp"] > 60
        ])
        new_freq = len([
            p for p in patterns
            if time.time() - p["timestamp"] <= 60
        ])
        
        if new_freq > old_freq * 1.2:
            direction = "increasing"
            strength = min((new_freq - old_freq) / old_freq, 1.0) \
                if old_freq > 0 else 0
        elif new_freq < old_freq * 0.8:
            direction = "decreasing"
            strength = min((old_freq - new_freq) / old_freq, 1.0) \
                if old_freq > 0 else 0
        else:
            direction = "stable"
            strength = 0
            
        return {
            "direction": direction,
            "strength": strength
        }
        
    def _detect_anomalies(self, reflex_data: Dict) -> List[Dict]:
        """Detect anomalies in reflex data."""
        anomalies = []
        metrics = reflex_data.get("metrics", {})
        
        # Check response time
        response_time = metrics.get("response_time")
        if response_time and response_time > self.anomaly_thresholds["response_time"]:
            anomalies.append({
                "type": "response_time",
                "value": response_time,
                "threshold": self.anomaly_thresholds["response_time"],
                "severity": min(
                    (response_time - self.anomaly_thresholds["response_time"]) 
                    / self.anomaly_thresholds["response_time"],
                    1.0
                )
            })
            
        # Check intensity
        intensity = metrics.get("intensity")
        if intensity and intensity > self.anomaly_thresholds["intensity"]:
            anomalies.append({
                "type": "intensity",
                "value": intensity,
                "threshold": self.anomaly_thresholds["intensity"],
                "severity": min(
                    (intensity - self.anomaly_thresholds["intensity"]) 
                    / self.anomaly_thresholds["intensity"],
                    1.0
                )
            })
            
        return anomalies

# Create singleton instance
reflex_pattern_analyzer = ReflexPatternAnalyzer()
