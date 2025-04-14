
"""
Clone Strategy Autotuner for SARYA.
Automatically adjusts clone strategies based on performance and reflex feedback.
"""
import logging
import time
from typing import Dict, List, Optional

from core.base_module import BaseModule
from core.event_bus import Event, event_bus
from core.memory import memory_system
from reflex_system.reflex_signal_router import reflex_signal_router

logger = logging.getLogger(__name__)

class CloneStrategyAutotuner(BaseModule):
    """
    Autotunes clone strategies based on reflex feedback and performance metrics.
    
    Features:
    - Strategy adjustment based on reflex feedback
    - Performance-based tuning
    - Risk-aware optimization
    - Mode switching (Balanced/Aggressive/Defensive)
    """
    
    def __init__(self):
        super().__init__("CloneStrategyAutotuner")
        self.tuning_history = {}
        self.current_modes = {}  # clone_id -> mode mapping
        self.strategy_cache = {}
        
        # Performance thresholds
        self.thresholds = {
            "high_risk": 0.8,
            "low_performance": 0.4,
            "stability_threshold": 0.6
        }
        
        # Strategy modes
        self.modes = {
            "balanced": {
                "risk_tolerance": 0.5,
                "resource_allocation": 0.5,
                "retry_attempts": 2
            },
            "aggressive": {
                "risk_tolerance": 0.8,
                "resource_allocation": 0.8,
                "retry_attempts": 1
            },
            "defensive": {
                "risk_tolerance": 0.2,
                "resource_allocation": 0.3,
                "retry_attempts": 3
            }
        }
        
    def _initialize(self) -> bool:
        """Initialize the autotuner."""
        try:
            # Load stored tuning data
            stored_data = memory_system.get(
                "clone_strategy_tuning",
                namespace="tuning"
            )
            if stored_data:
                self.tuning_history = stored_data
                
            # Subscribe to relevant events
            event_bus.subscribe(
                "clone.performance",
                self._on_performance_update,
                subscriber_id="strategy_tuner"
            )
            
            event_bus.subscribe(
                "reflex.signal",
                self._on_reflex_signal,
                subscriber_id="strategy_tuner"
            )
            
            logger.info("Strategy autotuner initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing strategy autotuner: {e}")
            return False
            
    def _stop(self) -> bool:
        """Stop the autotuner."""
        try:
            # Save tuning history
            memory_system.set(
                "clone_strategy_tuning",
                self.tuning_history,
                namespace="tuning"
            )
            
            # Unsubscribe from events
            event_bus.unsubscribe(subscriber_id="strategy_tuner")
            
            return True
        except Exception as e:
            logger.error(f"Error stopping strategy autotuner: {e}")
            return False
            
    def tune_strategy(
        self,
        clone_id: str,
        current_strategy: Dict,
        performance_metrics: Optional[Dict] = None
    ) -> Dict:
        """
        Tune a clone's strategy based on performance and feedback.
        
        Args:
            clone_id: ID of the clone
            current_strategy: Current strategy parameters
            performance_metrics: Optional performance metrics
            
        Returns:
            Dict containing tuned strategy parameters
        """
        # Get current mode
        current_mode = self.current_modes.get(clone_id, "balanced")
        base_config = self.modes[current_mode].copy()
        
        # Apply performance-based adjustments
        if performance_metrics:
            if performance_metrics.get("risk_score", 0) > self.thresholds["high_risk"]:
                # Switch to defensive mode
                current_mode = "defensive"
                base_config = self.modes["defensive"].copy()
                
            elif performance_metrics.get("efficiency", 0) < self.thresholds["low_performance"]:
                # Switch to aggressive mode
                current_mode = "aggressive"
                base_config = self.modes["aggressive"].copy()
        
        # Update mode
        self.current_modes[clone_id] = current_mode
        
        # Merge with current strategy
        tuned_strategy = current_strategy.copy()
        tuned_strategy.update(base_config)
        
        # Apply fine-tuning based on history
        if clone_id in self.tuning_history:
            history = self.tuning_history[clone_id]
            if history["success_rate"] > 0.7:
                # Slightly increase risk tolerance
                tuned_strategy["risk_tolerance"] = min(
                    tuned_strategy["risk_tolerance"] * 1.1,
                    0.9
                )
            elif history["success_rate"] < 0.3:
                # Decrease risk tolerance
                tuned_strategy["risk_tolerance"] *= 0.8
        
        # Cache the tuned strategy
        self.strategy_cache[clone_id] = {
            "strategy": tuned_strategy,
            "timestamp": time.time()
        }
        
        return tuned_strategy
        
    def get_recommended_mode(
        self,
        clone_id: str,
        risk_score: float,
        performance_score: float
    ) -> str:
        """
        Get recommended operation mode based on risk and performance.
        
        Args:
            clone_id: ID of the clone
            risk_score: Current risk assessment (0-1)
            performance_score: Current performance score (0-1)
            
        Returns:
            str: Recommended mode (balanced/aggressive/defensive)
        """
        if risk_score > self.thresholds["high_risk"]:
            return "defensive"
            
        if performance_score < self.thresholds["low_performance"]:
            if risk_score < self.thresholds["stability_threshold"]:
                return "aggressive"
                
        return "balanced"
        
    def _on_performance_update(self, event: Event) -> None:
        """Handle performance update events."""
        clone_id = event.data.get("clone_id")
        metrics = event.data.get("metrics", {})
        
        if not clone_id or not metrics:
            return
            
        # Update tuning history
        if clone_id not in self.tuning_history:
            self.tuning_history[clone_id] = {
                "success_rate": 0.0,
                "performance_history": []
            }
            
        history = self.tuning_history[clone_id]
        history["performance_history"].append({
            "metrics": metrics,
            "timestamp": time.time()
        })
        
        # Keep only last 100 entries
        if len(history["performance_history"]) > 100:
            history["performance_history"] = history["performance_history"][-100:]
            
        # Update success rate
        recent_successes = sum(
            1 for entry in history["performance_history"][-10:]
            if entry["metrics"].get("success", False)
        )
        history["success_rate"] = recent_successes / 10
        
    def _on_reflex_signal(self, event: Event) -> None:
        """Handle reflex signal events."""
        clone_id = event.data.get("clone_id")
        signal_type = event.data.get("type")
        intensity = event.data.get("intensity", 0.0)
        
        if not clone_id or not signal_type:
            return
            
        # Handle high-intensity signals
        if intensity > self.thresholds["high_risk"]:
            # Switch to defensive mode
            self.current_modes[clone_id] = "defensive"
            
            # Trigger a strategy update
            reflex_signal_router.route_signal(
                "strategy_update",
                {
                    "clone_id": clone_id,
                    "mode": "defensive",
                    "reason": "high_intensity_signal",
                    "intensity": intensity
                }
            )

# Create singleton instance
clone_strategy_autotuner = CloneStrategyAutotuner()
