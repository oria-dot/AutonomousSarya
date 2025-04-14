"""
Plugin Interface for SARYA.
Defines the interface that all plugins must implement.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class PluginInterface(ABC):
    """
    Interface for SARYA plugins.
    
    All plugins must implement this interface to be loaded by the plugin manager.
    """
    
    # Plugin metadata - must be defined by all plugins
    PLUGIN_ID = "base_plugin"  # Unique identifier for the plugin
    
    def __init__(self):
        """Initialize the plugin."""
        self.name = self.__class__.__name__
        self.description = self.__doc__ or "No description available"
        self.version = "1.0.0"
        self.initialized = False
        self.running = False
        self.config = {}
        self.logger = logging.getLogger(f"plugin.{self.PLUGIN_ID}")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        This method is called once when the plugin is loaded.
        
        Returns:
            bool: True if initialization was successful
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the plugin.
        
        This method is called after initialization to start the plugin.
        
        Returns:
            bool: True if startup was successful
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the plugin.
        
        This method is called when the plugin is requested to stop.
        
        Returns:
            bool: True if shutdown was successful
        """
        pass
    
    def cleanup(self) -> None:
        """
        Clean up resources used by the plugin.
        
        This method is called when the plugin is unloaded.
        """
        self.initialized = False
        self.running = False
    
    def is_initialized(self) -> bool:
        """
        Check if the plugin is initialized.
        
        Returns:
            bool: True if the plugin is initialized
        """
        return self.initialized
    
    def is_running(self) -> bool:
        """
        Check if the plugin is running.
        
        Returns:
            bool: True if the plugin is running
        """
        return self.running
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        Update the plugin configuration.
        
        Args:
            config: New configuration values
            
        Returns:
            bool: True if the configuration was updated successfully
        """
        try:
            self.config.update(config)
            self._on_config_update(config)
            return True
        except Exception as e:
            self.logger.exception(f"Error updating configuration: {str(e)}")
            return False
    
    def _on_config_update(self, updated_config: Dict[str, Any]) -> None:
        """
        Called when the configuration is updated.
        
        Args:
            updated_config: The updated configuration values
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dict containing plugin information
        """
        return {
            "id": self.PLUGIN_ID,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "initialized": self.initialized,
            "running": self.running,
            "config": self.config
        }
