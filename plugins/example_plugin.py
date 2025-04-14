"""
Example Plugin for SARYA.
Demonstrates a basic plugin implementation.
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from core.event_bus import Event, event_bus

from .plugin_interface import PluginInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ExamplePlugin(PluginInterface):
    """
    Example plugin for SARYA that demonstrates basic functionality.
    
    Features:
    - Event listening and generation
    - Background task execution
    - Configuration management
    """
    
    # Plugin metadata
    PLUGIN_ID = "example_plugin"
    
    def __init__(self):
        """Initialize the example plugin."""
        super().__init__()
        self.name = "Example Plugin"
        self.description = "Example plugin for demonstration purposes"
        self.version = "1.0.0"
        
        # Plugin-specific attributes
        self.counter = 0
        self.background_thread = None
        self.running_thread = False
        self.interval = 60  # seconds
    
    def initialize(self) -> bool:
        """Initialize the plugin."""
        self.logger.info(f"Initializing {self.name} v{self.version}")
        
        try:
            # Set default configuration
            self.config.setdefault("enabled", True)
            self.config.setdefault("interval", 60)
            self.interval = self.config["interval"]
            
            # Subscribe to events
            event_bus.subscribe(
                event_type="clone.created",
                handler=self._on_clone_created,
                subscriber_id=f"{self.PLUGIN_ID}_clone_created"
            )
            
            event_bus.subscribe(
                event_type="clone.completed",
                handler=self._on_clone_completed,
                subscriber_id=f"{self.PLUGIN_ID}_clone_completed"
            )
            
            self.initialized = True
            self.logger.info(f"{self.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Error initializing {self.name}: {str(e)}")
            return False
    
    def start(self) -> bool:
        """Start the plugin."""
        if not self.initialized:
            self.logger.error(f"Cannot start {self.name}: not initialized")
            return False
        
        if self.running:
            self.logger.warning(f"{self.name} already running")
            return True
        
        self.logger.info(f"Starting {self.name}")
        
        try:
            # Check if enabled in config
            if not self.config.get("enabled", True):
                self.logger.info(f"{self.name} is disabled in configuration")
                return False
            
            # Start background thread
            self.running_thread = True
            self.background_thread = threading.Thread(
                target=self._background_task,
                daemon=True
            )
            self.background_thread.start()
            
            # Emit plugin started event
            event_bus.publish(Event(
                event_type="plugin.started",
                source=f"plugin:{self.PLUGIN_ID}",
                data={"plugin_id": self.PLUGIN_ID}
            ))
            
            self.running = True
            self.logger.info(f"{self.name} started successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Error starting {self.name}: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """Stop the plugin."""
        if not self.running:
            self.logger.warning(f"{self.name} not running")
            return True
        
        self.logger.info(f"Stopping {self.name}")
        
        try:
            # Stop background thread
            self.running_thread = False
            if self.background_thread and self.background_thread.is_alive():
                self.background_thread.join(timeout=5)
            
            # Unsubscribe from events
            event_bus.unsubscribe(subscriber_id=f"{self.PLUGIN_ID}_clone_created")
            event_bus.unsubscribe(subscriber_id=f"{self.PLUGIN_ID}_clone_completed")
            
            # Emit plugin stopped event
            event_bus.publish(Event(
                event_type="plugin.stopped",
                source=f"plugin:{self.PLUGIN_ID}",
                data={"plugin_id": self.PLUGIN_ID}
            ))
            
            self.running = False
            self.logger.info(f"{self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Error stopping {self.name}: {str(e)}")
            self.running = False  # Force to stopped state
            return False
    
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        if self.running:
            self.stop()
        
        self.logger.info(f"Cleaning up {self.name}")
        super().cleanup()
    
    def _on_config_update(self, updated_config: Dict[str, Any]) -> None:
        """
        Handle configuration updates.
        
        Args:
            updated_config: Updated configuration values
        """
        # Check for interval change
        if "interval" in updated_config:
            self.interval = updated_config["interval"]
            self.logger.info(f"Updated interval to {self.interval}")
        
        # Check for enabled/disabled change
        if "enabled" in updated_config:
            enabled = updated_config["enabled"]
            if enabled and not self.running:
                self.start()
            elif not enabled and self.running:
                self.stop()
    
    def _background_task(self) -> None:
        """Background task that runs periodically."""
        self.logger.info("Background task started")
        
        while self.running_thread:
            try:
                # Sleep for the configured interval
                for _ in range(self.interval):
                    if not self.running_thread:
                        break
                    time.sleep(1)
                
                if not self.running_thread:
                    break
                
                # Perform some periodic task
                self.counter += 1
                
                # Emit heartbeat event
                event_bus.publish(Event(
                    event_type="plugin.heartbeat",
                    source=f"plugin:{self.PLUGIN_ID}",
                    data={
                        "plugin_id": self.PLUGIN_ID,
                        "counter": self.counter,
                        "message": f"Heartbeat #{self.counter}"
                    }
                ))
                
                self.logger.debug(f"Background task executed ({self.counter})")
            except Exception as e:
                self.logger.exception(f"Error in background task: {str(e)}")
                time.sleep(10)  # Sleep on error to avoid tight loop
        
        self.logger.info("Background task stopped")
    
    def _on_clone_created(self, event: Event) -> None:
        """
        Handle clone created events.
        
        Args:
            event: The clone created event
        """
        clone_id = event.data.get("clone_id")
        if not clone_id:
            return
        
        self.logger.info(f"Clone created: {clone_id}")
        
        # Emit event
        event_bus.publish(Event(
            event_type="plugin.clone_detected",
            source=f"plugin:{self.PLUGIN_ID}",
            data={
                "plugin_id": self.PLUGIN_ID,
                "clone_id": clone_id,
                "action": "created"
            }
        ))
    
    def _on_clone_completed(self, event: Event) -> None:
        """
        Handle clone completed events.
        
        Args:
            event: The clone completed event
        """
        clone_id = event.data.get("clone_id")
        if not clone_id:
            return
        
        self.logger.info(f"Clone completed: {clone_id}")
        
        # Emit event
        event_bus.publish(Event(
            event_type="plugin.clone_detected",
            source=f"plugin:{self.PLUGIN_ID}",
            data={
                "plugin_id": self.PLUGIN_ID,
                "clone_id": clone_id,
                "action": "completed"
            }
        ))
