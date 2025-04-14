"""
Clone Worker for SARYA.
Executes clones from the clone queue.
"""
import logging
import threading
import time
from typing import List, Optional

from core.base_module import BaseModule
from core.config import config_manager
from core.event_bus import Event, event_bus

from .clone_manager import clone_manager
from .clone_queue import clone_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CloneWorker(BaseModule):
    """
    Worker that executes clones from the queue.
    
    Features:
    - Multi-worker execution
    - Dynamic worker scaling
    - Worker health monitoring
    """
    
    def __init__(self, worker_id: int):
        super().__init__(f"CloneWorker_{worker_id}")
        self.worker_id = worker_id
        self.running = False
        self.executing_clone_id: Optional[str] = None
        self.worker_thread: Optional[threading.Thread] = None
    
    def _initialize(self) -> bool:
        """Initialize the clone worker."""
        # Subscribe to relevant events
        event_bus.subscribe(
            event_type="worker.stop",
            handler=self._handle_stop_event,
            subscriber_id=f"worker_{self.worker_id}"
        )
        
        return True
    
    def _start(self) -> bool:
        """Start the clone worker."""
        if self.running:
            self.logger.warning(f"Worker {self.worker_id} already running")
            return True
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )
        self.worker_thread.start()
        
        self.logger.info(f"Worker {self.worker_id} started")
        return True
    
    def _stop(self) -> bool:
        """Stop the clone worker."""
        # Signal worker to stop
        self.running = False
        
        # Wait for worker thread to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        
        # Unsubscribe from events
        event_bus.unsubscribe(subscriber_id=f"worker_{self.worker_id}")
        
        self.logger.info(f"Worker {self.worker_id} stopped")
        return True
    
    def _worker_loop(self) -> None:
        """Main worker loop that processes clones from the queue."""
        while self.running:
            try:
                # Dequeue a clone ID to process
                clone_id = clone_queue.dequeue()
                
                if not clone_id:
                    # No clone to process, sleep and try again
                    time.sleep(1)
                    continue
                
                # Process the clone
                self._process_clone(clone_id)
            except Exception as e:
                self.logger.exception(f"Error in worker {self.worker_id}: {str(e)}")
                time.sleep(1)  # Avoid tight loop on error
    
    def _process_clone(self, clone_id: str) -> None:
        """
        Process a clone.
        
        Args:
            clone_id: ID of the clone to process
        """
        self.logger.info(f"Worker {self.worker_id} processing clone {clone_id}")
        self.executing_clone_id = clone_id
        
        # Get the clone instance
        clone = clone_manager.get_clone(clone_id)
        
        if not clone:
            self.logger.error(f"Clone {clone_id} not found")
            self.executing_clone_id = None
            return
        
        try:
            # Initialize the clone if needed
            if not clone.initialized:
                if not clone_manager.initialize_clone(clone_id):
                    self.logger.error(f"Failed to initialize clone {clone_id}")
                    self.executing_clone_id = None
                    return
            
            # Start the clone
            if not clone_manager.start_clone(clone_id):
                self.logger.error(f"Failed to start clone {clone_id}")
        finally:
            self.executing_clone_id = None
    
    def _handle_stop_event(self, event: Event) -> None:
        """
        Handle worker stop events.
        
        Args:
            event: The event to handle
        """
        worker_id = event.data.get("worker_id")
        
        # If the event targets this worker, stop it
        if worker_id is None or worker_id == self.worker_id:
            self.logger.info(f"Worker {self.worker_id} received stop event")
            self.running = False

class CloneWorkerPool(BaseModule):
    """
    Pool of clone workers.
    
    Features:
    - Dynamic worker pool sizing
    - Worker health monitoring
    - Load balancing
    """
    
    def __init__(self):
        super().__init__("CloneWorkerPool")
        self.workers: List[CloneWorker] = []
        self.max_workers = 10
        self.min_workers = 1
    
    def _initialize(self) -> bool:
        """Initialize the worker pool."""
        # Get configuration
        self.max_workers = config_manager.get("clone_system.max_workers", 10)
        self.min_workers = config_manager.get("clone_system.min_workers", 1)
        
        return True
    
    def _start(self) -> bool:
        """Start the worker pool."""
        # Create and start initial workers
        num_workers = max(self.min_workers, min(self.max_workers, 2))  # Start with at least 2 workers
        
        for i in range(num_workers):
            worker = CloneWorker(i)
            worker.initialize()
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"Started worker pool with {num_workers} workers")
        return True
    
    def _stop(self) -> bool:
        """Stop the worker pool."""
        # Stop all workers
        for worker in self.workers:
            worker.stop()
        
        # Clear workers list
        self.workers = []
        
        self.logger.info("Stopped worker pool")
        return True
    
    def adjust_pool_size(self, target_size: int) -> bool:
        """
        Adjust the worker pool size.
        
        Args:
            target_size: Target number of workers
            
        Returns:
            bool: True if the pool size was adjusted successfully
        """
        # Clamp target size to valid range
        target_size = max(self.min_workers, min(self.max_workers, target_size))
        current_size = len(self.workers)
        
        if target_size == current_size:
            return True
        
        self.logger.info(f"Adjusting worker pool size from {current_size} to {target_size}")
        
        if target_size > current_size:
            # Add workers
            for i in range(current_size, target_size):
                worker = CloneWorker(i)
                worker.initialize()
                worker.start()
                self.workers.append(worker)
        else:
            # Remove workers
            for i in range(target_size, current_size):
                worker = self.workers.pop()
                worker.stop()
        
        return True
    
    def get_active_workers(self) -> int:
        """
        Get the number of active workers.
        
        Returns:
            int: Number of active workers
        """
        return len([w for w in self.workers if w.running])
    
    def get_busy_workers(self) -> int:
        """
        Get the number of busy workers (executing a clone).
        
        Returns:
            int: Number of busy workers
        """
        return len([w for w in self.workers if w.executing_clone_id])

# Create a singleton instance
worker_pool = CloneWorkerPool()
