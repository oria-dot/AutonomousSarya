"""
Base Clone class for SARYA.
Defines the interface and base functionality for all clones.
"""
import logging
import time
import uuid
from abc import abstractmethod
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from core.base_module import BaseModule
from core.config import config_manager
from core.event_bus import Event, event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CloneStatus(Enum):
    """Status values for a clone."""
    CREATED = auto()       # Clone has been created but not initialized
    INITIALIZED = auto()   # Clone has been initialized but not started
    RUNNING = auto()       # Clone is actively running
    PAUSED = auto()        # Clone execution is paused
    COMPLETED = auto()     # Clone has completed its execution successfully
    FAILED = auto()        # Clone has failed during execution
    TERMINATED = auto()    # Clone was terminated before completion

class CloneExecutionEvent(Event):
    """Event emitted during clone execution lifecycle."""
    
    def __init__(
        self, 
        event_type: str, 
        clone_id: str, 
        data: Dict[str, Any] = None
    ):
        super().__init__(
            event_type=event_type,
            source=f"clone:{clone_id}",
            data=data or {}
        )
        self.data["clone_id"] = clone_id

class BaseClone(BaseModule):
    """
    Base class for all SARYA clones.
    
    Features:
    - Standardized lifecycle management
    - Execution metrics
    - Event emission
    - State management
    """
    
    def __init__(self, clone_id: Optional[str] = None, name: Optional[str] = None):
        """
        Initialize a new clone.
        
        Args:
            clone_id: Optional ID for the clone. If not provided, a UUID is generated.
            name: Optional name for the clone. If not provided, the class name is used.
        """
        self.clone_id = clone_id or str(uuid.uuid4())
        name = name or self.__class__.__name__
        super().__init__(f"{name}_{self.clone_id[:8]}")
        
        # Clone-specific attributes
        self.status = CloneStatus.CREATED
        self.creation_time = time.time()
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.last_active_time: Optional[float] = None
        self.failure_reason: Optional[str] = None
        self.progress: float = 0.0  # 0.0 to 1.0
        self.metadata: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        
        # Emit clone creation event
        self._emit_event("clone.created", {
            "creation_time": self.creation_time,
            "clone_type": self.__class__.__name__
        })
    
    def _initialize(self) -> bool:
        """Initialize the clone."""
        if self.status != CloneStatus.CREATED:
            self.logger.warning(f"Clone {self.clone_id} already initialized")
            return True
        
        self.logger.info(f"Initializing clone {self.clone_id}")
        
        try:
            # Call subclass initialization
            result = self._initialize_clone()
            
            if result:
                self.status = CloneStatus.INITIALIZED
                self._emit_event("clone.initialized", {
                    "initialized_time": time.time()
                })
                self.logger.info(f"Clone {self.clone_id} initialized successfully")
            else:
                self.logger.error(f"Clone {self.clone_id} initialization failed")
                self.status = CloneStatus.FAILED
                self.failure_reason = "Initialization failed"
                self._emit_event("clone.failed", {
                    "failure_time": time.time(),
                    "failure_reason": self.failure_reason
                })
            
            return result
        except Exception as e:
            self.logger.exception(f"Error initializing clone {self.clone_id}: {str(e)}")
            self.status = CloneStatus.FAILED
            self.failure_reason = f"Initialization error: {str(e)}"
            self._emit_event("clone.failed", {
                "failure_time": time.time(),
                "failure_reason": self.failure_reason,
                "exception": str(e)
            })
            return False
    
    def _start(self) -> bool:
        """Start the clone."""
        if self.status != CloneStatus.INITIALIZED and self.status != CloneStatus.PAUSED:
            self.logger.error(f"Cannot start clone {self.clone_id}: status is {self.status.name}")
            return False
        
        self.logger.info(f"Starting clone {self.clone_id}")
        
        try:
            # Set start time if not already running
            if self.status == CloneStatus.INITIALIZED:
                self.start_time = time.time()
            
            # Update status and last active time
            self.status = CloneStatus.RUNNING
            self.last_active_time = time.time()
            
            # Emit event
            self._emit_event("clone.started", {
                "start_time": self.start_time,
                "last_active_time": self.last_active_time
            })
            
            # Call subclass execution
            result = self._execute_clone()
            
            if result:
                self.logger.info(f"Clone {self.clone_id} execution successful")
                self.status = CloneStatus.COMPLETED
                self.end_time = time.time()
                self.progress = 1.0
                self._emit_event("clone.completed", {
                    "end_time": self.end_time,
                    "execution_time": self.end_time - self.start_time,
                    "results": self.results
                })
            else:
                self.logger.error(f"Clone {self.clone_id} execution failed")
                self.status = CloneStatus.FAILED
                self.end_time = time.time()
                self.failure_reason = "Execution failed"
                self._emit_event("clone.failed", {
                    "failure_time": self.end_time,
                    "execution_time": self.end_time - self.start_time,
                    "failure_reason": self.failure_reason
                })
            
            return result
        except Exception as e:
            self.logger.exception(f"Error executing clone {self.clone_id}: {str(e)}")
            self.status = CloneStatus.FAILED
            self.end_time = time.time()
            self.failure_reason = f"Execution error: {str(e)}"
            self._emit_event("clone.failed", {
                "failure_time": self.end_time,
                "execution_time": self.end_time - self.start_time,
                "failure_reason": self.failure_reason,
                "exception": str(e)
            })
            return False
    
    def _stop(self) -> bool:
        """Stop the clone."""
        if self.status != CloneStatus.RUNNING and self.status != CloneStatus.PAUSED:
            self.logger.warning(f"Cannot stop clone {self.clone_id}: status is {self.status.name}")
            return True
        
        self.logger.info(f"Stopping clone {self.clone_id}")
        
        try:
            # Call subclass cleanup
            result = self._cleanup_clone()
            
            # Update status and end time
            self.status = CloneStatus.TERMINATED
            self.end_time = time.time()
            
            # Emit event
            self._emit_event("clone.terminated", {
                "termination_time": self.end_time,
                "execution_time": self.end_time - self.start_time
            })
            
            self.logger.info(f"Clone {self.clone_id} stopped successfully")
            return result
        except Exception as e:
            self.logger.exception(f"Error stopping clone {self.clone_id}: {str(e)}")
            self.status = CloneStatus.TERMINATED
            self.end_time = time.time()
            self._emit_event("clone.terminated", {
                "termination_time": self.end_time,
                "execution_time": self.end_time - self.start_time,
                "error": str(e)
            })
            return False
    
    def pause(self) -> bool:
        """
        Pause the clone execution.
        
        Returns:
            bool: True if the clone was paused successfully
        """
        if self.status != CloneStatus.RUNNING:
            self.logger.warning(f"Cannot pause clone {self.clone_id}: status is {self.status.name}")
            return False
        
        self.logger.info(f"Pausing clone {self.clone_id}")
        
        try:
            # Call subclass pause method
            result = self._pause_clone()
            
            if result:
                # Update status and emit event
                self.status = CloneStatus.PAUSED
                self._emit_event("clone.paused", {
                    "pause_time": time.time(),
                    "execution_time_so_far": time.time() - self.start_time
                })
                self.logger.info(f"Clone {self.clone_id} paused successfully")
            else:
                self.logger.error(f"Failed to pause clone {self.clone_id}")
            
            return result
        except Exception as e:
            self.logger.exception(f"Error pausing clone {self.clone_id}: {str(e)}")
            return False
    
    def resume(self) -> bool:
        """
        Resume a paused clone.
        
        Returns:
            bool: True if the clone was resumed successfully
        """
        if self.status != CloneStatus.PAUSED:
            self.logger.warning(f"Cannot resume clone {self.clone_id}: status is {self.status.name}")
            return False
        
        return self.start()
    
    def update_progress(self, progress: float, message: Optional[str] = None) -> None:
        """
        Update the clone progress.
        
        Args:
            progress: Progress value from 0.0 to 1.0
            message: Optional progress message
        """
        # Clamp progress to valid range
        self.progress = max(0.0, min(1.0, progress))
        self.last_active_time = time.time()
        
        # Emit progress event
        self._emit_event("clone.progress", {
            "progress": self.progress,
            "message": message,
            "time": self.last_active_time
        })
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update the clone metadata.
        
        Args:
            metadata: Dictionary of metadata to update
        """
        self.metadata.update(metadata)
        
        # Emit metadata event
        self._emit_event("clone.metadata_updated", {
            "metadata": metadata,
            "time": time.time()
        })
    
    def set_result(self, key: str, value: Any) -> None:
        """
        Set a result value.
        
        Args:
            key: Result key
            value: Result value
        """
        self.results[key] = value
        
        # Emit result event
        self._emit_event("clone.result", {
            "key": key,
            "time": time.time()
        })
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the clone.
        
        Returns:
            Dict containing clone information
        """
        runtime = None
        if self.start_time:
            end = self.end_time or time.time()
            runtime = end - self.start_time
        
        return {
            "clone_id": self.clone_id,
            "name": self.name,
            "type": self.__class__.__name__,
            "status": self.status.name,
            "creation_time": self.creation_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "last_active_time": self.last_active_time,
            "runtime": runtime,
            "progress": self.progress,
            "failure_reason": self.failure_reason,
            "metadata": self.metadata
        }
    
    def is_active(self) -> bool:
        """
        Check if the clone is active.
        
        Returns:
            bool: True if the clone is running or paused
        """
        return self.status in (CloneStatus.RUNNING, CloneStatus.PAUSED)
    
    def is_complete(self) -> bool:
        """
        Check if the clone has completed execution.
        
        Returns:
            bool: True if the clone has completed execution
        """
        return self.status in (CloneStatus.COMPLETED, CloneStatus.FAILED, CloneStatus.TERMINATED)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """
        Emit a clone event.
        
        Args:
            event_type: Type of event
            data: Optional event data
        """
        event = CloneExecutionEvent(
            event_type=event_type,
            clone_id=self.clone_id,
            data=data or {}
        )
        event_bus.publish(event)
    
    @abstractmethod
    def _initialize_clone(self) -> bool:
        """
        Initialize clone resources. Must be implemented by subclasses.
        
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    def _execute_clone(self) -> bool:
        """
        Execute the clone. Must be implemented by subclasses.
        
        Returns:
            bool: True if execution successful
        """
        pass
    
    def _pause_clone(self) -> bool:
        """
        Pause the clone execution. Override in subclasses if needed.
        
        Returns:
            bool: True if pause successful
        """
        return True
    
    def _cleanup_clone(self) -> bool:
        """
        Clean up clone resources. Override in subclasses if needed.
        
        Returns:
            bool: True if cleanup successful
        """
        return True
