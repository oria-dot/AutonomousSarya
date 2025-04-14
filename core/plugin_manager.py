"""
Plugin Manager for SARYA.
Provides a system for discovering, loading, and managing plugins.
"""
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

from core.base_module import BaseModule
from core.config import config_manager
from plugins.plugin_interface import PluginInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("plugin_manager")

class PluginManager(BaseModule):
    """
    Manages the discovery, loading, and lifecycle of plugins.
    
    Features:
    - Dynamic plugin discovery
    - Versioned plugin support
    - Plugin dependency resolution
    - Plugin lifecycle management
    """
    
    def __init__(self):
        super().__init__("PluginManager")
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_classes: Dict[str, Type[PluginInterface]] = {}
        self.plugin_dirs: List[str] = []
        self.disabled_plugins: Set[str] = set()
    
    def _initialize(self) -> bool:
        """Initialize the plugin manager."""
        # Set default plugin directory
        default_plugin_dir = config_manager.get("plugins.plugin_dir", "plugins")
        self.plugin_dirs = [default_plugin_dir]
        
        # Add additional plugin directories from configuration
        additional_dirs = config_manager.get("plugins.additional_dirs", [])
        if additional_dirs:
            self.plugin_dirs.extend(additional_dirs)
        
        self.logger.info(f"Plugin directories: {', '.join(self.plugin_dirs)}")
        
        # Auto-discover plugins if enabled
        if config_manager.get("plugins.auto_discover", True):
            self.discover_plugins()
        
        return True
    
    def _start(self) -> bool:
        """Start the plugin manager and initialize plugins."""
        # Load enabled plugins
        for plugin_id, plugin_class in self.plugin_classes.items():
            if plugin_id not in self.disabled_plugins:
                self._load_plugin(plugin_id, plugin_class)
        
        return True
    
    def _stop(self) -> bool:
        """Stop all plugins and clean up."""
        for plugin_id, plugin in list(self.plugins.items()):
            self.unload_plugin(plugin_id)
        
        return True
    
    def discover_plugins(self) -> List[str]:
        """
        Discover plugins in the plugin directories.
        
        Returns:
            List of discovered plugin IDs
        """
        discovered_plugins = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir) or not os.path.isdir(plugin_dir):
                self.logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            self.logger.info(f"Discovering plugins in {plugin_dir}")
            
            # Find all Python files in the plugin directory
            plugin_files = []
            for root, _, files in os.walk(plugin_dir):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        plugin_files.append(os.path.join(root, file))
            
            # Process each file
            for plugin_file in plugin_files:
                plugin_id = self._discover_plugin_in_file(plugin_file)
                if plugin_id:
                    discovered_plugins.append(plugin_id)
        
        self.logger.info(f"Discovered {len(discovered_plugins)} plugins: {', '.join(discovered_plugins)}")
        return discovered_plugins
    
    def _discover_plugin_in_file(self, file_path: str) -> Optional[str]:
        """
        Discover plugins in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Plugin ID if a plugin was found, None otherwise
        """
        try:
            # Load the module
            module_name = os.path.basename(file_path)[:-3]  # Remove .py
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find plugin classes in the module
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    hasattr(obj, 'PLUGIN_ID')):
                    
                    plugin_id = obj.PLUGIN_ID
                    self.plugin_classes[plugin_id] = obj
                    self.logger.info(f"Discovered plugin: {plugin_id} ({obj.__name__})")
                    return plugin_id
            
            return None
        except Exception as e:
            self.logger.error(f"Error discovering plugin in {file_path}: {str(e)}")
            return None
    
    def load_plugin(self, plugin_id: str) -> bool:
        """
        Load and initialize a plugin.
        
        Args:
            plugin_id: ID of the plugin to load
            
        Returns:
            bool: True if the plugin was loaded successfully
        """
        if plugin_id in self.plugins:
            self.logger.warning(f"Plugin {plugin_id} already loaded")
            return True
        
        if plugin_id not in self.plugin_classes:
            self.logger.error(f"Plugin {plugin_id} not found")
            return False
        
        return self._load_plugin(plugin_id, self.plugin_classes[plugin_id])
    
    def _load_plugin(self, plugin_id: str, plugin_class: Type[PluginInterface]) -> bool:
        """
        Internal method to load and initialize a plugin.
        
        Args:
            plugin_id: ID of the plugin
            plugin_class: Class of the plugin
            
        Returns:
            bool: True if the plugin was loaded successfully
        """
        try:
            # Create plugin instance
            plugin = plugin_class()
            
            # Initialize the plugin
            if not plugin.initialize():
                self.logger.error(f"Failed to initialize plugin {plugin_id}")
                return False
            
            # Register the plugin
            self.plugins[plugin_id] = plugin
            self.logger.info(f"Loaded plugin: {plugin_id}")
            
            # Start the plugin if the manager is running
            if self.running:
                if not plugin.start():
                    self.logger.error(f"Failed to start plugin {plugin_id}")
                    self.plugins.pop(plugin_id)
                    return False
            
            return True
        except Exception as e:
            self.logger.exception(f"Error loading plugin {plugin_id}: {str(e)}")
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_id: ID of the plugin to unload
            
        Returns:
            bool: True if the plugin was unloaded successfully
        """
        if plugin_id not in self.plugins:
            self.logger.warning(f"Plugin {plugin_id} not loaded")
            return True
        
        plugin = self.plugins[plugin_id]
        
        try:
            # Stop the plugin if it's running
            if plugin.is_running():
                if not plugin.stop():
                    self.logger.error(f"Failed to stop plugin {plugin_id}")
                    return False
            
            # Clean up the plugin
            plugin.cleanup()
            
            # Remove from plugins dict
            self.plugins.pop(plugin_id)
            self.logger.info(f"Unloaded plugin: {plugin_id}")
            
            return True
        except Exception as e:
            self.logger.exception(f"Error unloading plugin {plugin_id}: {str(e)}")
            return False
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable a disabled plugin.
        
        Args:
            plugin_id: ID of the plugin to enable
            
        Returns:
            bool: True if the plugin was enabled successfully
        """
        if plugin_id in self.disabled_plugins:
            self.disabled_plugins.remove(plugin_id)
            self.logger.info(f"Enabled plugin: {plugin_id}")
            
            # Load the plugin if it's not already loaded
            if plugin_id not in self.plugins and plugin_id in self.plugin_classes:
                return self.load_plugin(plugin_id)
            
            return True
        
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_id: ID of the plugin to disable
            
        Returns:
            bool: True if the plugin was disabled successfully
        """
        # Add to disabled plugins set
        self.disabled_plugins.add(plugin_id)
        self.logger.info(f"Disabled plugin: {plugin_id}")
        
        # Unload if it's loaded
        if plugin_id in self.plugins:
            return self.unload_plugin(plugin_id)
        
        return True
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """
        Get a loaded plugin by ID.
        
        Args:
            plugin_id: ID of the plugin
            
        Returns:
            The plugin instance or None if not found
        """
        return self.plugins.get(plugin_id)
    
    def get_loaded_plugins(self) -> Dict[str, PluginInterface]:
        """
        Get all loaded plugins.
        
        Returns:
            Dictionary of plugin ID to plugin instance
        """
        return self.plugins.copy()
    
    def get_available_plugins(self) -> List[str]:
        """
        Get IDs of all available plugins.
        
        Returns:
            List of plugin IDs
        """
        return list(self.plugin_classes.keys())
    
    def get_disabled_plugins(self) -> Set[str]:
        """
        Get IDs of all disabled plugins.
        
        Returns:
            Set of disabled plugin IDs
        """
        return self.disabled_plugins.copy()

# Create a singleton instance
plugin_manager = PluginManager()
