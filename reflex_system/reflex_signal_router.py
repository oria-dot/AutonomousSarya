
"""
Reflex Signal Router for SARYA.
Routes and manages reflex signals between clones and handlers.
"""
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from core.base_module import BaseModule
from core.event_bus import Event, event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ReflexSignalRouter(BaseModule):
    """
    Routes reflex signals to appropriate handlers and maintains logs.
    
    Features:
    - Dynamic handler registration
    - Signal routing with intensity control
    - Clone-aware logging
    - Filtered log retrieval
    """
    
    def __init__(self):
        super().__init__("ReflexSignalRouter")
        self.handlers: Dict[str, Callable] = {}
        self.log: List[Dict[str, Any]] = []
        
    def _initialize(self) -> bool:
        """Initialize router and register default handlers."""
        self.register_handler("alert", self.handle_alert)
        self.register_handler("shutdown", self.handle_shutdown)
        self.register_handler("cooldown", self.handle_cooldown)
        
        # Subscribe to reflex events
        event_bus.subscribe(
            event_type="reflex.signal",
            handler=self._on_reflex_signal,
            subscriber_id="reflex_router"
        )
        
        self.logger.info("Reflex signal router initialized")
        return True
    
    def _stop(self) -> bool:
        """Stop the router."""
        event_bus.unsubscribe(subscriber_id="reflex_router")
        return True
        
    def register_handler(self, reflex_type: str, handler_func: Callable) -> None:
        """
        Register a handler function for a reflex type.
        
        Args:
            reflex_type: Type of reflex to handle
            handler_func: Function to handle the reflex
        """
        self.handlers[reflex_type] = handler_func
        self.logger.info(f"Registered handler for reflex type: {reflex_type}")
    
    def route_signal(
        self, 
        reflex_type: str, 
        signal_data: Dict[str, Any],
        clone_id: Optional[str] = None
    ) -> bool:
        """
        Route a reflex signal to its handler.
        
        Args:
            reflex_type: Type of reflex to route
            signal_data: Signal data including intensity
            clone_id: Optional ID of originating clone
            
        Returns:
            bool: True if signal was handled successfully
        """
        # Log the signal
        log_entry = {
            "timestamp": time.time(),
            "type": reflex_type,
            "clone_id": clone_id,
            "intensity": signal_data.get("intensity", 0.0),
            "data": signal_data
        }
        self.log.append(log_entry)
        
        # Route to handler
        handler = self.handlers.get(reflex_type, self.default_handler)
        try:
            handler(signal_data)
            return True
        except Exception as e:
            self.logger.error(f"Error handling reflex signal: {str(e)}")
            return False
    
    def get_log(
        self, 
        filter_by_type: Optional[str] = None,
        clone_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get filtered log entries.
        
        Args:
            filter_by_type: Optional reflex type filter
            clone_id: Optional clone ID filter
            limit: Maximum entries to return
            
        Returns:
            List of filtered log entries
        """
        filtered = self.log
        
        if filter_by_type:
            filtered = [log for log in filtered if log["type"] == filter_by_type]
            
        if clone_id:
            filtered = [log for log in filtered if log["clone_id"] == clone_id]
            
        return filtered[-limit:]
    
    def default_handler(self, signal_data: Dict[str, Any]) -> None:
        """
        Default handler for unregistered reflex types.
        
        Args:
            signal_data: Signal data including intensity
        """
        intensity = signal_data.get("intensity", 0.0)
        
        if intensity > 0.8:
            self.logger.warning(f"High intensity reflex signal: {signal_data}")
        else:
            self.logger.info(f"Unhandled reflex signal: {signal_data}")
    
    def handle_alert(self, signal_data: Dict[str, Any]) -> None:
        """Handle alert reflexes."""
        self.logger.warning(
            f"Alert reflex triggered with intensity {signal_data.get('intensity', 0.0)}: "
            f"{signal_data.get('message', 'No message')}"
        )
    
    def handle_shutdown(self, signal_data: Dict[str, Any]) -> None:
        """Handle shutdown reflexes."""
        self.logger.info(
            f"Shutdown reflex triggered with intensity {signal_data.get('intensity', 0.0)}"
        )
        # In real implementation, trigger gradual shutdown
    
    def handle_cooldown(self, signal_data: Dict[str, Any]) -> None:
        """Handle cooldown reflexes."""
        self.logger.info(
            f"Cooldown reflex triggered with intensity {signal_data.get('intensity', 0.0)}"
        )
        # In real implementation, reduce system load
    
    def _on_reflex_signal(self, event: Event) -> None:
        """Handle reflex signal events."""
        self.route_signal(
            reflex_type=event.data.get("type"),
            signal_data=event.data,
            clone_id=event.data.get("clone_id")
        )

# Create singleton instance
reflex_signal_router = ReflexSignalRouter()

# Example usage
if __name__ == "__main__":
    # Register custom handler
    def custom_handler(signal_data):
        print(f"Custom handling of signal: {signal_data}")
    
    router = ReflexSignalRouter()
    router._initialize()
    
    # Register custom handler
    router.register_handler("custom", custom_handler)
    
    # Route some sample signals
    router.route_signal(
        "alert",
        {"intensity": 0.9, "message": "Critical system alert"},
        clone_id="clone_001"
    )
    
    router.route_signal(
        "cooldown",
        {"intensity": 0.6, "temperature": 85.5},
        clone_id="clone_002"
    )
    
    router.route_signal(
        "custom",
        {"intensity": 0.4, "data": "Custom signal data"},
        clone_id="clone_001"
    )
    
    # Get filtered logs
    clone_logs = router.get_log(clone_id="clone_001")
    alert_logs = router.get_log(filter_by_type="alert")
    
    print("\nClone 001 Logs:", clone_logs)
    print("\nAlert Logs:", alert_logs)
