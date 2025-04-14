"""
Event Bus implementation for SARYA.
Provides a central event dispatch system for inter-module communication.
"""
import asyncio
import inspect
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("event_bus")

class EventPriority(Enum):
    """Priority levels for event handlers."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class Event:
    """Base event class for the event system."""
    event_type: str
    source: str
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    
    def serialize(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Event':
        """Create an event from a dictionary."""
        return cls(
            event_type=data["event_type"],
            source=data["source"],
            timestamp=data["timestamp"],
            event_id=data["event_id"],
            data=data["data"]
        )

@dataclass
class EventSubscription:
    """Represents a subscription to an event type."""
    event_type: str
    handler: Callable[[Event], Any]
    subscriber_id: str
    priority: EventPriority = EventPriority.NORMAL
    filter_fn: Optional[Callable[[Event], bool]] = None
    is_async: bool = False

class EventBus:
    """
    Central event bus for the SARYA system.
    
    Features:
    - Topic-based publish/subscribe
    - Synchronous and asynchronous event handling
    - Priority-based event processing
    - Event filtering
    - Dead letter queue for unhandled events
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._subscription_lock = threading.RLock()
        self._dead_letter_queue: List[Event] = []
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._logger = logger
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to subscribers.
        
        Args:
            event: The event to publish
        """
        self._logger.debug(f"Publishing event: {event.event_type} from {event.source}")
        
        # Get subscriptions for this event type
        subscriptions = self._get_subscriptions(event.event_type)
        
        if not subscriptions:
            self._logger.debug(f"No subscribers for event type: {event.event_type}")
            self._dead_letter_queue.append(event)
            return
        
        # Process event with each subscriber
        for subscription in subscriptions:
            # Apply filter if present
            if subscription.filter_fn and not subscription.filter_fn(event):
                continue
            
            try:
                # Handle based on whether the handler is async or not
                if subscription.is_async:
                    self._dispatch_async(subscription.handler, event)
                else:
                    subscription.handler(event)
            except Exception as e:
                self._logger.error(
                    f"Error in event handler {subscription.subscriber_id} "
                    f"for event {event.event_type}: {str(e)}"
                )
    
    def subscribe(
        self, 
        event_type: str, 
        handler: Callable[[Event], Any], 
        subscriber_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        filter_fn: Optional[Callable[[Event], bool]] = None
    ) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: Function to call when event occurs
            subscriber_id: Optional subscriber identifier
            priority: Handler priority
            filter_fn: Optional filter function
            
        Returns:
            str: The subscriber ID
        """
        if subscriber_id is None:
            subscriber_id = str(uuid.uuid4())
        
        # Check if the handler is async
        is_async = asyncio.iscoroutinefunction(handler) or (
            inspect.isgeneratorfunction(handler) and 
            asyncio.iscoroutinefunction(handler.__call__)
        )
        
        subscription = EventSubscription(
            event_type=event_type,
            handler=handler,
            subscriber_id=subscriber_id,
            priority=priority,
            filter_fn=filter_fn,
            is_async=is_async
        )
        
        with self._subscription_lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            
            # Insert based on priority
            self._subscriptions[event_type].append(subscription)
            self._subscriptions[event_type].sort(
                key=lambda s: s.priority.value, 
                reverse=True
            )
        
        self._logger.debug(
            f"Subscribed {subscriber_id} to {event_type} "
            f"with priority {priority.name}"
        )
        return subscriber_id
    
    def unsubscribe(self, subscriber_id: str, event_type: Optional[str] = None) -> None:
        """
        Unsubscribe from events.
        
        Args:
            subscriber_id: The subscriber ID to unsubscribe
            event_type: Optional event type to unsubscribe from (if None, unsubscribe from all)
        """
        with self._subscription_lock:
            if event_type is not None:
                # Unsubscribe from specific event type
                if event_type in self._subscriptions:
                    self._subscriptions[event_type] = [
                        s for s in self._subscriptions[event_type] 
                        if s.subscriber_id != subscriber_id
                    ]
                    self._logger.debug(f"Unsubscribed {subscriber_id} from {event_type}")
            else:
                # Unsubscribe from all event types
                for evt_type in self._subscriptions:
                    self._subscriptions[evt_type] = [
                        s for s in self._subscriptions[evt_type] 
                        if s.subscriber_id != subscriber_id
                    ]
                self._logger.debug(f"Unsubscribed {subscriber_id} from all events")
    
    def get_dead_letter_events(self, clear: bool = False) -> List[Event]:
        """
        Get events from the dead letter queue.
        
        Args:
            clear: Whether to clear the dead letter queue
            
        Returns:
            List of unhandled events
        """
        events = self._dead_letter_queue.copy()
        if clear:
            self._dead_letter_queue.clear()
        return events
    
    def get_event_types(self) -> Set[str]:
        """
        Get all registered event types.
        
        Returns:
            Set of event type strings
        """
        return set(self._subscriptions.keys())
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Set the event loop for async event handlers.
        
        Args:
            loop: The asyncio event loop to use
        """
        self._event_loop = loop
    
    def _get_subscriptions(self, event_type: str) -> List[EventSubscription]:
        """
        Get all subscriptions for an event type, sorted by priority.
        
        Args:
            event_type: The event type to get subscriptions for
            
        Returns:
            List of EventSubscription objects
        """
        with self._subscription_lock:
            return self._subscriptions.get(event_type, []).copy()
    
    def _dispatch_async(self, handler: Callable, event: Event) -> None:
        """
        Dispatch an event to an async handler.
        
        Args:
            handler: The async handler function
            event: The event to dispatch
        """
        if self._event_loop is None:
            self._event_loop = asyncio.get_event_loop()
        
        asyncio.run_coroutine_threadsafe(handler(event), self._event_loop)

# Create a singleton instance
event_bus = EventBus()
