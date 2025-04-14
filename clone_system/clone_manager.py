"""
Clone Manager for SARYA.
Manages clone instances and their lifecycle.
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set

from core.base_module import BaseModule
from core.config import config_manager
from core.event_bus import Event, EventPriority, event_bus
from core.memory import memory_system

from .clone_base import BaseClone, CloneStatus
from .clone_registry import clone_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CloneManager(BaseModule):
    """
    Manages clone instances and their lifecycle.
    
    Features:
    - Clone creation and management
    - Clone lifecycle management
    - Clone status tracking
    - Clone persistence
    """
    
    def __init__(self):
        super().__init__("CloneManager")
        self.clones: Dict[str, BaseClone] = {}
        self.clone_lock = threading.RLock()
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.heartbeat_interval = 5  # seconds
        self.running_heartbeat = False
    
    def _initialize(self) -> bool:
        """Initialize the clone manager."""
        # Get heartbeat interval from config
        self.heartbeat_interval = config_manager.get(
            "clone_system.heartbeat_interval", 
            5
        )
        
        # Subscribe to clone events
        event_bus.subscribe(
            event_type="clone.created",
            handler=self._handle_clone_event,
            subscriber_id="clone_manager",
            priority=EventPriority.HIGH
        )
        
        event_bus.subscribe(
            event_type="clone.completed",
            handler=self._handle_clone_event,
            subscriber_id="clone_manager",
            priority=EventPriority.HIGH
        )
        
        event_bus.subscribe(
            event_type="clone.failed",
            handler=self._handle_clone_event,
            subscriber_id="clone_manager",
            priority=EventPriority.HIGH
        )
        
        event_bus.subscribe(
            event_type="clone.terminated",
            handler=self._handle_clone_event,
            subscriber_id="clone_manager",
            priority=EventPriority.HIGH
        )
        
        # Initialize clone persistence
        self._restore_active_clones()
        
        return True
    
    def _start(self) -> bool:
        """Start the clone manager."""
        # Start heartbeat thread
        self.running_heartbeat = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
        
        self.logger.info("Clone manager started")
        return True
    
    def _stop(self) -> bool:
        """Stop the clone manager."""
        # Stop heartbeat thread
        self.running_heartbeat = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
        
        # Stop all active clones
        with self.clone_lock:
            active_clones = [c for c in self.clones.values() if c.is_active()]
        
        for clone in active_clones:
            self.stop_clone(clone.clone_id)
        
        # Unsubscribe from events
        event_bus.unsubscribe(subscriber_id="clone_manager")
        
        self.logger.info("Clone manager stopped")
        return True
    
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
            type_name: Type of clone to create
            clone_id: Optional ID for the clone
            name: Optional name for the clone
            **kwargs: Additional arguments for the clone constructor
            
        Returns:
            New clone instance or None if creation failed
        """
        # Create clone through registry
        clone = clone_registry.create_clone(
            type_name=type_name,
            clone_id=clone_id,
            name=name,
            **kwargs
        )
        
        if not clone:
            self.logger.error(f"Failed to create clone of type {type_name}")
            return None
        
        # Register clone
        with self.clone_lock:
            self.clones[clone.clone_id] = clone
        
        self.logger.info(f"Registered clone {clone.clone_id} of type {type_name}")
        return clone
    
    def get_clone(self, clone_id: str) -> Optional[BaseClone]:
        """
        Get a clone by ID.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            Clone instance or None if not found
        """
        with self.clone_lock:
            return self.clones.get(clone_id)
    
    def get_clones(self, status: Optional[CloneStatus] = None) -> List[BaseClone]:
        """
        Get all clones, optionally filtered by status.
        
        Args:
            status: Optional status to filter by
            
        Returns:
            List of clone instances
        """
        with self.clone_lock:
            if status is None:
                return list(self.clones.values())
            else:
                return [c for c in self.clones.values() if c.status == status]
    
    def get_clone_ids(self, status: Optional[CloneStatus] = None) -> List[str]:
        """
        Get IDs of all clones, optionally filtered by status.
        
        Args:
            status: Optional status to filter by
            
        Returns:
            List of clone IDs
        """
        with self.clone_lock:
            if status is None:
                return list(self.clones.keys())
            else:
                return [c.clone_id for c in self.clones.values() if c.status == status]
    
    def initialize_clone(self, clone_id: str, config: Dict[str, Any] = None) -> bool:
        """
        Initialize a clone.
        
        Args:
            clone_id: ID of the clone
            config: Optional configuration for the clone
            
        Returns:
            bool: True if the clone was initialized successfully
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            self.logger.error(f"Clone {clone_id} not found")
            return False
        
        if clone.status != CloneStatus.CREATED:
            self.logger.warning(f"Clone {clone_id} already initialized")
            return True
        
        return clone.initialize(config)
    
    def start_clone(self, clone_id: str) -> bool:
        """
        Start a clone.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            bool: True if the clone was started successfully
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            self.logger.error(f"Clone {clone_id} not found")
            return False
        
        if clone.status != CloneStatus.INITIALIZED and clone.status != CloneStatus.PAUSED:
            self.logger.error(f"Cannot start clone {clone_id}: status is {clone.status.name}")
            return False
        
        return clone.start()
    
    def stop_clone(self, clone_id: str) -> bool:
        """
        Stop a clone.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            bool: True if the clone was stopped successfully
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            self.logger.error(f"Clone {clone_id} not found")
            return False
        
        if not clone.is_active():
            self.logger.warning(f"Clone {clone_id} not active")
            return True
        
        return clone.stop()
    
    def pause_clone(self, clone_id: str) -> bool:
        """
        Pause a clone.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            bool: True if the clone was paused successfully
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            self.logger.error(f"Clone {clone_id} not found")
            return False
        
        if clone.status != CloneStatus.RUNNING:
            self.logger.error(f"Cannot pause clone {clone_id}: status is {clone.status.name}")
            return False
        
        return clone.pause()
    
    def resume_clone(self, clone_id: str) -> bool:
        """
        Resume a paused clone.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            bool: True if the clone was resumed successfully
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            self.logger.error(f"Clone {clone_id} not found")
            return False
        
        if clone.status != CloneStatus.PAUSED:
            self.logger.error(f"Cannot resume clone {clone_id}: status is {clone.status.name}")
            return False
        
        return clone.resume()
    
    def remove_clone(self, clone_id: str, force: bool = False) -> bool:
        """
        Remove a clone from the manager.
        
        Args:
            clone_id: ID of the clone
            force: Whether to force removal even if the clone is active
            
        Returns:
            bool: True if the clone was removed
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            self.logger.warning(f"Clone {clone_id} not found")
            return True
        
        if clone.is_active() and not force:
            self.logger.error(f"Cannot remove active clone {clone_id} without force flag")
            return False
        
        # Stop the clone if it's active
        if clone.is_active():
            self.stop_clone(clone_id)
        
        # Remove from clones dict
        with self.clone_lock:
            if clone_id in self.clones:
                del self.clones[clone_id]
        
        # Remove from persistence
        memory_system.delete(
            key=f"clone:{clone_id}",
            namespace="clone_manager"
        )
        
        self.logger.info(f"Removed clone {clone_id}")
        return True
    
    def get_clone_info(self, clone_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a clone.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            Dict containing clone information or None if not found
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            return None
        
        return clone.get_info()
    
    def get_all_clone_info(self, status: Optional[CloneStatus] = None) -> List[Dict[str, Any]]:
        """
        Get information about all clones, optionally filtered by status.
        
        Args:
            status: Optional status to filter by
            
        Returns:
            List of dicts containing clone information
        """
        clones = self.get_clones(status)
        return [clone.get_info() for clone in clones]
    
    def _handle_clone_event(self, event: Event) -> None:
        """
        Handle clone events.
        
        Args:
            event: The event to handle
        """
        # Extract clone ID from event data
        clone_id = event.data.get("clone_id")
        if not clone_id:
            return
        
        # Process based on event type
        if event.event_type == "clone.completed":
            self._persist_clone_data(clone_id)
        elif event.event_type == "clone.failed":
            self._persist_clone_data(clone_id)
        elif event.event_type == "clone.terminated":
            self._persist_clone_data(clone_id)
    
    def _persist_clone_data(self, clone_id: str) -> None:
        """
        Persist clone data to memory system.
        
        Args:
            clone_id: ID of the clone
        """
        clone = self.get_clone(clone_id)
        
        if not clone:
            return
        
        # Get clone info and persist to memory
        clone_info = clone.get_info()
        memory_system.set(
            key=f"clone:{clone_id}",
            value=clone_info,
            namespace="clone_manager"
        )
    
    def _restore_active_clones(self) -> None:
        """Restore active clones from persistence."""
        # Get all clone IDs from memory
        clone_keys = memory_system.keys(
            pattern="clone:*",
            namespace="clone_manager"
        )
        
        self.logger.info(f"Found {len(clone_keys)} persisted clones")
        
        # Create placeholders for active clones
        for key in clone_keys:
            if not key.startswith("clone:"):
                continue
            
            clone_id = key[6:]  # Remove "clone:" prefix
            
            # Get clone info
            clone_info = memory_system.get(
                key=key,
                namespace="clone_manager"
            )
            
            if not clone_info or not isinstance(clone_info, dict):
                continue
            
            # Skip if the clone is complete
            status_name = clone_info.get("status")
            if status_name in ("COMPLETED", "FAILED", "TERMINATED"):
                continue
            
            # Create a placeholder for the clone
            clone_type = clone_info.get("type")
            if not clone_type:
                continue
            
            self.logger.info(f"Restoring active clone {clone_id} of type {clone_type}")
            
            # Create clone through registry
            # Note: This will create a new clone instance, with new state
            # It will not restore the exact state of the previous clone
            self.create_clone(
                type_name=clone_type,
                clone_id=clone_id,
                name=clone_info.get("name")
            )
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat loop to monitor active clones."""
        while self.running_heartbeat:
            # Sleep for heartbeat interval
            time.sleep(self.heartbeat_interval)
            
            # Get active clones
            with self.clone_lock:
                active_clones = [c for c in self.clones.values() if c.is_active()]
            
            # Update heartbeat for each active clone
            for clone in active_clones:
                clone.heartbeat()
            
            # Check for stale clones
            self._check_stale_clones()
    
    def _check_stale_clones(self) -> None:
        """Check for stale clones that haven't reported activity."""
        # Get configuration
        stale_threshold = config_manager.get(
            "clone_system.stale_threshold", 
            300  # 5 minutes
        )
        
        current_time = time.time()
        
        # Check each active clone
        with self.clone_lock:
            active_clones = [c for c in self.clones.values() if c.is_active()]
        
        for clone in active_clones:
            if (clone.last_active_time and 
                current_time - clone.last_active_time > stale_threshold):
                
                self.logger.warning(f"Clone {clone.clone_id} appears to be stale, stopping")
                self.stop_clone(clone.clone_id)

# Create a singleton instance
clone_manager = CloneManager()
