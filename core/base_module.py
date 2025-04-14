#!/usr/bin/env python3
"""
Base Module for SARYA.
Provides a common interface for all system modules.
"""
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseModule(ABC):
    """
    Abstract base class for all SARYA modules.
    Provides common functionality and required interface.
    """
    
    def __init__(self, name: Optional[str] = None, module_id: Optional[str] = None):
        """Initialize a module with a unique ID and name."""
        # Generate module ID if not provided
        if module_id is None:
            module_id = str(uuid.uuid4())[:8]
            
        # Use class name if name not provided
        if name is None:
            name = self.__class__.__name__
            
        self.module_id = module_id
        self.name = name
        self.full_name = f"{name}_{module_id}"
        self.initialized = False
        self.started = False
        self.status = "created"
        
        # Set up logger
        self.logger = logging.getLogger(self.full_name)
        
        self.logger.info(f"Module {self.full_name} created with ID {module_id}")
        
    def initialize(self) -> bool:
        """
        Initialize the module.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            self.logger.info(f"Initializing module {self.name}")
            
            # Call implementation-specific initialization
            result = self._initialize()
            
            if result:
                self.initialized = True
                self.status = "initialized"
                self.logger.info(f"Module {self.name} initialized successfully")
            else:
                self.status = "initialization_failed"
                self.logger.error(f"Module {self.name} initialization failed")
                
            return result
        except Exception as e:
            self.status = "initialization_error"
            self.logger.error(f"Error initializing module {self.name}: {e}", exc_info=True)
            return False
            
    def start(self) -> bool:
        """
        Start the module.
        
        Returns:
            bool: True if startup was successful
        """
        if not self.initialized:
            self.logger.error(f"Cannot start uninitialized module {self.name}")
            return False
            
        try:
            self.logger.info(f"Starting module {self.name}")
            
            # Call implementation-specific startup
            result = self._start()
            
            if result:
                self.started = True
                self.status = "running"
                self.logger.info(f"Module {self.name} started successfully")
            else:
                self.status = "start_failed"
                self.logger.error(f"Module {self.name} start failed")
                
            return result
        except Exception as e:
            self.status = "start_error"
            self.logger.error(f"Error starting module {self.name}: {e}", exc_info=True)
            return False
            
    def stop(self) -> bool:
        """
        Stop the module.
        
        Returns:
            bool: True if shutdown was successful
        """
        if not self.started:
            self.logger.warning(f"Module {self.name} not running, nothing to stop")
            return True
            
        try:
            self.logger.info(f"Stopping module {self.name}")
            
            # Call implementation-specific shutdown
            result = self._stop()
            
            if result:
                self.started = False
                self.status = "stopped"
                self.logger.info(f"Module {self.name} stopped successfully")
            else:
                self.status = "stop_failed"
                self.logger.error(f"Module {self.name} stop failed")
                
            return result
        except Exception as e:
            self.status = "stop_error"
            self.logger.error(f"Error stopping module {self.name}: {e}", exc_info=True)
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the module.
        
        Returns:
            Dict: Status information
        """
        return {
            "id": self.module_id,
            "name": self.name,
            "full_name": self.full_name,
            "status": self.status,
            "initialized": self.initialized,
            "running": self.started
        }
        
    @abstractmethod
    def _initialize(self) -> bool:
        """
        Implementation-specific initialization.
        
        Returns:
            bool: True if initialization was successful
        """
        pass
        
    @abstractmethod
    def _start(self) -> bool:
        """
        Implementation-specific startup.
        
        Returns:
            bool: True if startup was successful
        """
        pass
        
    @abstractmethod
    def _stop(self) -> bool:
        """
        Implementation-specific shutdown.
        
        Returns:
            bool: True if shutdown was successful
        """
        pass