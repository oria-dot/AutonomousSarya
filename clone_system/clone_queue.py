"""
Clone Queue for SARYA.
Manages the queue of clones to be executed.
"""
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

import redis
from redis.exceptions import RedisError

from core.base_module import BaseModule
from core.config import config_manager
from core.event_bus import Event, event_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CloneQueue(BaseModule):
    """
    Queue for clones to be executed.
    
    Features:
    - Priority-based queuing
    - Distributed queue (Redis-backed)
    - Queue monitoring and statistics
    """
    
    def __init__(self):
        super().__init__("CloneQueue")
        self.redis: Optional[redis.Redis] = None
        self.queue_key = "sarya:clone_queue"
        self.processing_key = "sarya:clone_processing"
        self.priority_prefix = "sarya:clone_priority:"
        self.lock = threading.RLock()
        self.fallback_queue: List[Tuple[int, str]] = []  # (priority, clone_id)
        self.fallback_processing: Set[str] = set()
        self.use_fallback = False
    
    def _initialize(self) -> bool:
        """Initialize the clone queue."""
        # Check if Redis is enabled
        redis_enabled = config_manager.get("redis.enabled", True)
        
        if not redis_enabled:
            self.logger.info("Redis is disabled in configuration, using in-memory queue")
            self.use_fallback = True
            return True
            
        # Get Redis configuration
        redis_host = config_manager.get("redis.host", "localhost")
        redis_port = config_manager.get("redis.port", 6379)
        redis_db = config_manager.get("redis.db", 0)
        redis_password = config_manager.get("redis.password", None)
        
        try:
            # Initialize Redis connection
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True
            )
            
            # Test connection
            self.redis.ping()
            self.use_fallback = False
            self.logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except RedisError as e:
            self.logger.error(f"Redis connection failed: {str(e)}")
            self.logger.info("Falling back to in-memory queue")
            self.use_fallback = True
        
        # Subscribe to relevant events
        event_bus.subscribe(
            event_type="clone.completed",
            handler=self._handle_clone_completion,
            subscriber_id="clone_queue"
        )
        
        event_bus.subscribe(
            event_type="clone.failed",
            handler=self._handle_clone_completion,
            subscriber_id="clone_queue"
        )
        
        event_bus.subscribe(
            event_type="clone.terminated",
            handler=self._handle_clone_completion,
            subscriber_id="clone_queue"
        )
        
        return True
    
    def _start(self) -> bool:
        """Start the clone queue."""
        return True
    
    def _stop(self) -> bool:
        """Stop the clone queue."""
        # Unsubscribe from events
        event_bus.unsubscribe(subscriber_id="clone_queue")
        
        # Close Redis connection
        if self.redis:
            try:
                self.redis.close()
            except:
                pass
            self.redis = None
        
        return True
    
    def enqueue(self, clone_id: str, priority: int = 0) -> bool:
        """
        Add a clone to the queue.
        
        Args:
            clone_id: ID of the clone to enqueue
            priority: Priority of the clone (higher is more important)
            
        Returns:
            bool: True if the clone was enqueued successfully
        """
        self.logger.info(f"Enqueuing clone {clone_id} with priority {priority}")
        
        if self.use_fallback:
            return self._enqueue_fallback(clone_id, priority)
        
        try:
            # Check if Redis is None (not connected)
            if self.redis is None:
                self.logger.warning("Redis not connected, using in-memory fallback")
                self.use_fallback = True
                return self._enqueue_fallback(clone_id, priority)
                
            # Store the priority
            self.redis.set(f"{self.priority_prefix}{clone_id}", priority)
            
            # Add to queue
            result = self.redis.lpush(self.queue_key, clone_id)
            
            # Sort the queue by priority
            self._sort_queue()
            
            # Emit event
            self._emit_queue_event("queue.enqueued", clone_id, priority)
            
            return result > 0
        except RedisError as e:
            self.logger.error(f"Redis error in enqueue: {str(e)}")
            self.use_fallback = True
            return self._enqueue_fallback(clone_id, priority)
    
    def dequeue(self) -> Optional[str]:
        """
        Get the next clone from the queue.
        
        Returns:
            ID of the next clone or None if queue is empty
        """
        if self.use_fallback:
            return self._dequeue_fallback()
        
        try:
            # Check if Redis is None (not connected)
            if self.redis is None:
                self.logger.warning("Redis not connected, using in-memory fallback")
                self.use_fallback = True
                return self._dequeue_fallback()
                
            # Move from queue to processing
            clone_id = self.redis.brpoplpush(
                self.queue_key,
                self.processing_key,
                timeout=1
            )
            
            if clone_id:
                priority = self._get_priority(clone_id)
                self._emit_queue_event("queue.dequeued", clone_id, priority)
            
            return clone_id
        except RedisError as e:
            self.logger.error(f"Redis error in dequeue: {str(e)}")
            self.use_fallback = True
            return self._dequeue_fallback()
    
    def requeue(self, clone_id: str, priority: Optional[int] = None) -> bool:
        """
        Put a clone back in the queue.
        
        Args:
            clone_id: ID of the clone to requeue
            priority: Optional new priority (if not provided, use existing)
            
        Returns:
            bool: True if the clone was requeued successfully
        """
        self.logger.info(f"Requeuing clone {clone_id}")
        
        if self.use_fallback:
            return self._requeue_fallback(clone_id, priority)
        
        try:
            # Check if Redis is None (not connected)
            if self.redis is None:
                self.logger.warning("Redis not connected, using in-memory fallback")
                self.use_fallback = True
                return self._requeue_fallback(clone_id, priority)
                
            # Update priority if provided
            if priority is not None:
                self.redis.set(f"{self.priority_prefix}{clone_id}", priority)
            else:
                priority = self._get_priority(clone_id)
            
            # Remove from processing
            self.redis.lrem(self.processing_key, 0, clone_id)
            
            # Add to queue
            result = self.redis.lpush(self.queue_key, clone_id)
            
            # Sort the queue by priority
            self._sort_queue()
            
            # Emit event
            self._emit_queue_event("queue.requeued", clone_id, priority)
            
            return result > 0
        except RedisError as e:
            self.logger.error(f"Redis error in requeue: {str(e)}")
            self.use_fallback = True
            return self._requeue_fallback(clone_id, priority)
    
    def remove(self, clone_id: str) -> bool:
        """
        Remove a clone from the queue.
        
        Args:
            clone_id: ID of the clone to remove
            
        Returns:
            bool: True if the clone was removed successfully
        """
        self.logger.info(f"Removing clone {clone_id}")
        
        if self.use_fallback:
            return self._remove_fallback(clone_id)
        
        try:
            # Check if Redis is None (not connected)
            if self.redis is None:
                self.logger.warning("Redis not connected, using in-memory fallback")
                self.use_fallback = True
                return self._remove_fallback(clone_id)
                
            # Remove from queue and processing
            removed_queue = self.redis.lrem(self.queue_key, 0, clone_id)
            removed_processing = self.redis.lrem(self.processing_key, 0, clone_id)
            
            # Remove priority
            self.redis.delete(f"{self.priority_prefix}{clone_id}")
            
            # Emit event
            self._emit_queue_event("queue.removed", clone_id)
            
            return removed_queue > 0 or removed_processing > 0
        except RedisError as e:
            self.logger.error(f"Redis error in remove: {str(e)}")
            self.use_fallback = True
            return self._remove_fallback(clone_id)
    
    def get_queue_size(self) -> int:
        """
        Get the current size of the queue.
        
        Returns:
            Size of the queue
        """
        if self.use_fallback:
            return self._get_queue_size_fallback()
        
        try:
            # Check if Redis is None (not connected)
            if self.redis is None:
                self.logger.warning("Redis not connected, using in-memory fallback")
                self.use_fallback = True
                return self._get_queue_size_fallback()
                
            return self.redis.llen(self.queue_key)
        except RedisError as e:
            self.logger.error(f"Redis error in get_queue_size: {str(e)}")
            self.use_fallback = True
            return self._get_queue_size_fallback()
    
    def get_processing_size(self) -> int:
        """
        Get the number of clones being processed.
        
        Returns:
            Number of clones being processed
        """
        if self.use_fallback:
            return self._get_processing_size_fallback()
        
        try:
            # Check if Redis is None (not connected)
            if self.redis is None:
                self.logger.warning("Redis not connected, using in-memory fallback")
                self.use_fallback = True
                return self._get_processing_size_fallback()
                
            return self.redis.llen(self.processing_key)
        except RedisError as e:
            self.logger.error(f"Redis error in get_processing_size: {str(e)}")
            self.use_fallback = True
            return self._get_processing_size_fallback()
    
    def get_queued_clones(self) -> List[str]:
        """
        Get IDs of all clones in the queue.
        
        Returns:
            List of clone IDs in the queue
        """
        if self.use_fallback:
            return self._get_queued_clones_fallback()
        
        try:
            return self.redis.lrange(self.queue_key, 0, -1)
        except RedisError as e:
            self.logger.error(f"Redis error in get_queued_clones: {str(e)}")
            self.use_fallback = True
            return self._get_queued_clones_fallback()
    
    def get_processing_clones(self) -> List[str]:
        """
        Get IDs of all clones being processed.
        
        Returns:
            List of clone IDs being processed
        """
        if self.use_fallback:
            return self._get_processing_clones_fallback()
        
        try:
            return self.redis.lrange(self.processing_key, 0, -1)
        except RedisError as e:
            self.logger.error(f"Redis error in get_processing_clones: {str(e)}")
            self.use_fallback = True
            return self._get_processing_clones_fallback()
    
    def clear_queue(self) -> bool:
        """
        Clear the entire queue.
        
        Returns:
            bool: True if the queue was cleared successfully
        """
        self.logger.info("Clearing clone queue")
        
        if self.use_fallback:
            return self._clear_queue_fallback()
        
        try:
            # Get all clone IDs from queue
            clone_ids = self.redis.lrange(self.queue_key, 0, -1)
            
            # Delete queue
            self.redis.delete(self.queue_key)
            
            # Delete priorities
            for clone_id in clone_ids:
                self.redis.delete(f"{self.priority_prefix}{clone_id}")
            
            # Emit event
            self._emit_queue_event("queue.cleared")
            
            return True
        except RedisError as e:
            self.logger.error(f"Redis error in clear_queue: {str(e)}")
            self.use_fallback = True
            return self._clear_queue_fallback()
    
    def _get_priority(self, clone_id: str) -> int:
        """
        Get the priority of a clone.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            Priority of the clone (0 if not found)
        """
        if self.use_fallback:
            with self.lock:
                for priority, cid in self.fallback_queue:
                    if cid == clone_id:
                        return priority
                return 0
        
        try:
            priority = self.redis.get(f"{self.priority_prefix}{clone_id}")
            return int(priority) if priority else 0
        except (RedisError, ValueError):
            return 0
    
    def _sort_queue(self) -> None:
        """Sort the Redis queue by priority."""
        try:
            # Get all clone IDs from queue
            clone_ids = self.redis.lrange(self.queue_key, 0, -1)
            
            if not clone_ids:
                return
            
            # Get priorities for all clones
            priorities = {}
            for clone_id in clone_ids:
                priorities[clone_id] = self._get_priority(clone_id)
            
            # Clear the queue
            self.redis.delete(self.queue_key)
            
            # Sort by priority (highest first)
            sorted_clone_ids = sorted(
                clone_ids,
                key=lambda cid: priorities.get(cid, 0),
                reverse=True
            )
            
            # Repopulate the queue
            if sorted_clone_ids:
                self.redis.rpush(self.queue_key, *sorted_clone_ids)
        except RedisError as e:
            self.logger.error(f"Redis error in sort_queue: {str(e)}")
    
    def _handle_clone_completion(self, event: Event) -> None:
        """
        Handle clone completion events.
        
        Args:
            event: The event to handle
        """
        clone_id = event.data.get("clone_id")
        if not clone_id:
            return
        
        # Remove from processing
        if self.use_fallback:
            with self.lock:
                if clone_id in self.fallback_processing:
                    self.fallback_processing.remove(clone_id)
        else:
            try:
                self.redis.lrem(self.processing_key, 0, clone_id)
            except RedisError as e:
                self.logger.error(f"Redis error in handle_clone_completion: {str(e)}")
    
    def _emit_queue_event(self, event_type: str, clone_id: str = None, priority: int = None) -> None:
        """
        Emit a queue event.
        
        Args:
            event_type: Type of event
            clone_id: Optional clone ID
            priority: Optional priority
        """
        data = {
            "queue_size": self.get_queue_size(),
            "processing_size": self.get_processing_size()
        }
        
        if clone_id:
            data["clone_id"] = clone_id
        
        if priority is not None:
            data["priority"] = priority
        
        event = Event(
            event_type=event_type,
            source="clone_queue",
            data=data
        )
        
        event_bus.publish(event)
    
    # Fallback in-memory queue methods
    def _enqueue_fallback(self, clone_id: str, priority: int = 0) -> bool:
        """Add a clone to the in-memory queue."""
        with self.lock:
            # Check if already in queue
            for i, (_, cid) in enumerate(self.fallback_queue):
                if cid == clone_id:
                    self.fallback_queue[i] = (priority, clone_id)
                    break
            else:
                # Not in queue, add it
                self.fallback_queue.append((priority, clone_id))
            
            # Sort queue by priority (highest first)
            self.fallback_queue.sort(key=lambda x: x[0], reverse=True)
        
        # Emit event
        self._emit_queue_event("queue.enqueued", clone_id, priority)
        
        return True
    
    def _dequeue_fallback(self) -> Optional[str]:
        """Get the next clone from the in-memory queue."""
        with self.lock:
            if not self.fallback_queue:
                return None
            
            priority, clone_id = self.fallback_queue.pop(0)
            self.fallback_processing.add(clone_id)
        
        # Emit event
        self._emit_queue_event("queue.dequeued", clone_id, priority)
        
        return clone_id
    
    def _requeue_fallback(self, clone_id: str, priority: Optional[int] = None) -> bool:
        """Put a clone back in the in-memory queue."""
        with self.lock:
            # Remove from processing
            if clone_id in self.fallback_processing:
                self.fallback_processing.remove(clone_id)
            
            # Find original priority if not provided
            if priority is None:
                for p, cid in self.fallback_queue:
                    if cid == clone_id:
                        priority = p
                        break
                else:
                    priority = 0
            
            # Check if already in queue
            for i, (_, cid) in enumerate(self.fallback_queue):
                if cid == clone_id:
                    self.fallback_queue[i] = (priority, clone_id)
                    break
            else:
                # Not in queue, add it
                self.fallback_queue.append((priority, clone_id))
            
            # Sort queue by priority (highest first)
            self.fallback_queue.sort(key=lambda x: x[0], reverse=True)
        
        # Emit event
        self._emit_queue_event("queue.requeued", clone_id, priority)
        
        return True
    
    def _remove_fallback(self, clone_id: str) -> bool:
        """Remove a clone from the in-memory queue."""
        removed = False
        
        with self.lock:
            # Remove from queue
            self.fallback_queue = [(p, cid) for p, cid in self.fallback_queue if cid != clone_id]
            
            # Remove from processing
            if clone_id in self.fallback_processing:
                self.fallback_processing.remove(clone_id)
                removed = True
        
        # Emit event
        self._emit_queue_event("queue.removed", clone_id)
        
        return removed
    
    def _get_queue_size_fallback(self) -> int:
        """Get the in-memory queue size."""
        with self.lock:
            return len(self.fallback_queue)
    
    def _get_processing_size_fallback(self) -> int:
        """Get the in-memory processing size."""
        with self.lock:
            return len(self.fallback_processing)
    
    def _get_queued_clones_fallback(self) -> List[str]:
        """Get IDs of all clones in the in-memory queue."""
        with self.lock:
            return [cid for _, cid in self.fallback_queue]
    
    def _get_processing_clones_fallback(self) -> List[str]:
        """Get IDs of all clones being processed in-memory."""
        with self.lock:
            return list(self.fallback_processing)
    
    def _clear_queue_fallback(self) -> bool:
        """Clear the in-memory queue."""
        with self.lock:
            self.fallback_queue = []
        
        # Emit event
        self._emit_queue_event("queue.cleared")
        
        return True

# Create a singleton instance
clone_queue = CloneQueue()
