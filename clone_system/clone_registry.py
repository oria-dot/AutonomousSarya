"""
Clone Registry for SARYA.
Manages clone type registration and instantiation.
"""
import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from core.base_module import BaseModule
from core.config import config_manager

from .clone_base import BaseClone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clone_registry")

class CloneRegistry(BaseModule):
    """
    Registry for clone types.
    
    Features:
    - Clone type registration and discovery
    - Clone instantiation
    - Clone type validation
    """
    
    def __init__(self):
        super().__init__("CloneRegistry")
        self.clone_types: Dict[str, Type[BaseClone]] = {}
        self.clone_dirs: List[str] = []
    
    def _initialize(self) -> bool:
        """Initialize the clone registry."""
        # Set default clone directories
        default_dirs = ["clone_system/types"]
        self.clone_dirs = config_manager.get("clone_system.clone_dirs", default_dirs)
        
        self.logger.info(f"Clone directories: {', '.join(self.clone_dirs)}")
        
        # Auto-discover clone types if enabled
        if config_manager.get("clone_system.auto_discover", True):
            self.discover_clone_types()
        
        return True
    
    def _start(self) -> bool:
        """Start the clone registry."""
        return True
    
    def _stop(self) -> bool:
        """Stop the clone registry."""
        self.clone_types.clear()
        return True
    
    def register_clone_type(self, clone_type: Type[BaseClone]) -> bool:
        """
        Register a clone type.
        
        Args:
            clone_type: The clone class to register
            
        Returns:
            bool: True if the clone type was registered successfully
        """
        if not issubclass(clone_type, BaseClone):
            self.logger.error(f"Cannot register {clone_type.__name__}: not a subclass of BaseClone")
            return False
        
        type_name = clone_type.__name__
        
        if type_name in self.clone_types:
            self.logger.warning(f"Clone type {type_name} already registered")
            return False
        
        self.clone_types[type_name] = clone_type
        self.logger.info(f"Registered clone type: {type_name}")
        return True
    
    def unregister_clone_type(self, type_name: str) -> bool:
        """
        Unregister a clone type.
        
        Args:
            type_name: Name of the clone type to unregister
            
        Returns:
            bool: True if the clone type was unregistered
        """
        if type_name in self.clone_types:
            del self.clone_types[type_name]
            self.logger.info(f"Unregistered clone type: {type_name}")
            return True
        
        self.logger.warning(f"Clone type {type_name} not registered")
        return False
    
    def get_clone_type(self, type_name: str) -> Optional[Type[BaseClone]]:
        """
        Get a clone type by name.
        
        Args:
            type_name: Name of the clone type
            
        Returns:
            The clone class or None if not found
        """
        return self.clone_types.get(type_name)
    
    def get_clone_types(self) -> Dict[str, Type[BaseClone]]:
        """
        Get all registered clone types.
        
        Returns:
            Dictionary of clone type name to clone class
        """
        return self.clone_types.copy()
    
    def create_clone(
        self, 
        type_name: str, 
        clone_id: Optional[str] = None, 
        name: Optional[str] = None,
        **kwargs
    ) -> Optional[BaseClone]:
        """
        Create a new clone instance.
        
        Args:
            type_name: Name of the clone type
            clone_id: Optional ID for the clone
            name: Optional name for the clone
            **kwargs: Additional arguments for the clone constructor
            
        Returns:
            New clone instance or None if creation failed
        """
        clone_type = self.get_clone_type(type_name)
        
        if not clone_type:
            self.logger.error(f"Clone type {type_name} not found")
            return None
        
        try:
            # Create clone instance
            clone = clone_type(clone_id=clone_id, name=name, **kwargs)
            self.logger.info(f"Created clone of type {type_name} with ID {clone.clone_id}")
            return clone
        except Exception as e:
            self.logger.exception(f"Error creating clone of type {type_name}: {str(e)}")
            return None
    
    def discover_clone_types(self) -> List[str]:
        """
        Discover clone types in the clone directories.
        
        Returns:
            List of discovered clone type names
        """
        discovered_types = []
        
        for clone_dir in self.clone_dirs:
            if not os.path.exists(clone_dir) or not os.path.isdir(clone_dir):
                self.logger.warning(f"Clone directory not found: {clone_dir}")
                continue
            
            self.logger.info(f"Discovering clone types in {clone_dir}")
            
            # Find all Python files in the clone directory
            clone_files = []
            for root, _, files in os.walk(clone_dir):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        clone_files.append(os.path.join(root, file))
            
            # Process each file
            for clone_file in clone_files:
                discovered = self._discover_clone_types_in_file(clone_file)
                discovered_types.extend(discovered)
        
        self.logger.info(f"Discovered {len(discovered_types)} clone types: {', '.join(discovered_types)}")
        return discovered_types
    
    def _discover_clone_types_in_file(self, file_path: str) -> List[str]:
        """
        Discover clone types in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of discovered clone type names
        """
        discovered = []
        
        try:
            # Convert file path to module path
            module_path = file_path.replace('/', '.').replace('\\', '.')
            if module_path.endswith('.py'):
                module_path = module_path[:-3]
            
            # Load the module
            module = importlib.import_module(module_path)
            
            # Find clone classes in the module
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseClone) and 
                    obj is not BaseClone and
                    obj.__module__ == module.__name__):
                    
                    type_name = obj.__name__
                    if self.register_clone_type(obj):
                        discovered.append(type_name)
            
            return discovered
        except Exception as e:
            self.logger.error(f"Error discovering clone types in {file_path}: {str(e)}")
            return []

# Create a singleton instance
clone_registry = CloneRegistry()
