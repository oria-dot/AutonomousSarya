"""
Prometheus metrics for SARYA.
Provides metrics collection and export for monitoring.
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import prometheus_client
from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client.registry import CollectorRegistry

from clone_system.clone_manager import clone_manager
from clone_system.clone_queue import clone_queue
from core.base_module import BaseModule
from core.config import config_manager
from core.event_bus import Event, event_bus
from core.plugin_manager import plugin_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class MetricsManager(BaseModule):
    """
    Manages metrics collection and export.
    
    Features:
    - Prometheus metrics collection
    - System statistics tracking
    - Performance monitoring
    - Event metrics
    """
    
    def __init__(self):
        super().__init__("MetricsManager")
        # Create registry
        self.registry = CollectorRegistry()
        
        # System metrics
        self.uptime_gauge = Gauge(
            'sarya_system_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        self.clone_count_gauge = Gauge(
            'sarya_clone_count',
            'Number of clones',
            ['status'],
            registry=self.registry
        )
        
        self.queue_size_gauge = Gauge(
            'sarya_queue_size',
            'Size of the clone queue',
            ['type'],
            registry=self.registry
        )
        
        self.plugin_count_gauge = Gauge(
            'sarya_plugin_count',
            'Number of plugins',
            ['status'],
            registry=self.registry
        )
        
        # Event metrics
        self.event_counter = Counter(
            'sarya_events_total',
            'Total number of events',
            ['event_type'],
            registry=self.registry
        )
        
        self.reflex_count_gauge = Gauge(
            'sarya_reflex_count',
            'Number of reflex mappings',
            ['type'],
            registry=self.registry
        )
        
        # Performance metrics
        self.clone_execution_time = Histogram(
            'sarya_clone_execution_seconds',
            'Clone execution time in seconds',
            ['clone_type'],
            registry=self.registry
        )
        
        self.api_request_time = Histogram(
            'sarya_api_request_seconds',
            'API request processing time in seconds',
            ['endpoint', 'method'],
            registry=self.registry
        )
        
        # Memory metrics
        self.memory_usage_gauge = Gauge(
            'sarya_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        # Thread for periodic metrics collection
        self.metrics_thread = None
        self.running = False
        self.collection_interval = 15  # seconds
        
        # Startup time
        self.start_time = time.time()
    
    def _initialize(self) -> bool:
        """Initialize the metrics manager."""
        # Check if metrics are enabled
        enabled = config_manager.get("metrics.enabled", True)
        if not enabled:
            self.logger.info("Metrics collection is disabled")
            return False
        
        # Get collection interval from config
        self.collection_interval = config_manager.get(
            "metrics.collection_interval", 
            15
        )
        
        # Subscribe to events
        event_bus.subscribe(
            event_type="*",
            handler=self._on_event,
            subscriber_id="metrics_manager"
        )
        
        # Subscribe to specific events for detailed metrics
        event_bus.subscribe(
            event_type="clone.started",
            handler=self._on_clone_started,
            subscriber_id="metrics_manager_clone"
        )
        
        event_bus.subscribe(
            event_type="clone.completed",
            handler=self._on_clone_completed,
            subscriber_id="metrics_manager_clone"
        )
        
        event_bus.subscribe(
            event_type="clone.failed",
            handler=self._on_clone_completed,
            subscriber_id="metrics_manager_clone"
        )
        
        self.logger.info("Metrics manager initialized")
        return True
    
    def _start(self) -> bool:
        """Start the metrics manager."""
        # Start metrics collection thread
        self.running = True
        self.metrics_thread = threading.Thread(
            target=self._collect_metrics_loop,
            daemon=True
        )
        self.metrics_thread.start()
        
        self.logger.info("Metrics collection started")
        return True
    
    def _stop(self) -> bool:
        """Stop the metrics manager."""
        # Stop metrics collection thread
        self.running = False
        if self.metrics_thread:
            self.metrics_thread.join(timeout=2)
        
        # Unsubscribe from events
        event_bus.unsubscribe(subscriber_id="metrics_manager")
        event_bus.unsubscribe(subscriber_id="metrics_manager_clone")
        
        self.logger.info("Metrics collection stopped")
        return True
    
    def _collect_metrics_loop(self) -> None:
        """Background thread for periodic metrics collection."""
        while self.running:
            try:
                # Collect metrics
                self._collect_system_metrics()
                
                # Sleep until next collection
                time.sleep(self.collection_interval)
            except Exception as e:
                self.logger.exception(f"Error collecting metrics: {str(e)}")
                time.sleep(5)  # Sleep on error to avoid tight loop
    
    def _collect_system_metrics(self) -> None:
        """Collect system-wide metrics."""
        # Update uptime
        uptime = time.time() - self.start_time
        self.uptime_gauge.set(uptime)
        
        # Update clone counts
        clone_infos = clone_manager.get_all_clone_info()
        status_counts = {}
        for info in clone_infos:
            status = info.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            self.clone_count_gauge.labels(status=status).set(count)
        
        # Update queue sizes
        queue_size = clone_queue.get_queue_size()
        processing_size = clone_queue.get_processing_size()
        self.queue_size_gauge.labels(type="queued").set(queue_size)
        self.queue_size_gauge.labels(type="processing").set(processing_size)
        
        # Update plugin counts
        available_plugins = plugin_manager.get_available_plugins()
        loaded_plugins = plugin_manager.get_loaded_plugins()
        disabled_plugins = plugin_manager.get_disabled_plugins()
        
        self.plugin_count_gauge.labels(status="available").set(len(available_plugins))
        self.plugin_count_gauge.labels(status="loaded").set(len(loaded_plugins))
        self.plugin_count_gauge.labels(status="disabled").set(len(disabled_plugins))
        
        # Update memory usage
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            self.memory_usage_gauge.labels(type="rss").set(memory_info.rss)
            self.memory_usage_gauge.labels(type="vms").set(memory_info.vms)
        except (ImportError, Exception) as e:
            # psutil might not be available
            self.logger.debug(f"Could not collect memory metrics: {str(e)}")
    
    def _on_event(self, event: Event) -> None:
        """
        Handle events for metrics tracking.
        
        Args:
            event: The event to track
        """
        # Increment event counter
        self.event_counter.labels(event_type=event.event_type).inc()
    
    def _on_clone_started(self, event: Event) -> None:
        """
        Handle clone started events.
        
        Args:
            event: The clone started event
        """
        clone_id = event.data.get("clone_id")
        if not clone_id:
            return
        
        # Get clone info
        clone_info = clone_manager.get_clone_info(clone_id)
        if not clone_info:
            return
        
        # Store start time for later calculation of execution time
        event.data["metrics_start_time"] = time.time()
    
    def _on_clone_completed(self, event: Event) -> None:
        """
        Handle clone completed or failed events.
        
        Args:
            event: The clone completed/failed event
        """
        clone_id = event.data.get("clone_id")
        if not clone_id:
            return
        
        # Get clone info
        clone_info = clone_manager.get_clone_info(clone_id)
        if not clone_info:
            return
        
        # Get execution time
        start_time = event.data.get("start_time")
        end_time = event.data.get("end_time") or time.time()
        
        if start_time and end_time > start_time:
            execution_time = end_time - start_time
            
            # Record execution time
            self.clone_execution_time.labels(
                clone_type=clone_info.get("type", "unknown")
            ).observe(execution_time)
    
    def get_metric_info(self) -> List[Dict[str, Any]]:
        """
        Get information about available metrics.
        
        Returns:
            List of metric information
        """
        metrics = []
        
        # System metrics
        metrics.append({
            "name": "sarya_system_uptime_seconds",
            "description": "System uptime in seconds",
            "type": "gauge",
            "labels": []
        })
        
        metrics.append({
            "name": "sarya_clone_count",
            "description": "Number of clones",
            "type": "gauge",
            "labels": ["status"]
        })
        
        metrics.append({
            "name": "sarya_queue_size",
            "description": "Size of the clone queue",
            "type": "gauge",
            "labels": ["type"]
        })
        
        metrics.append({
            "name": "sarya_plugin_count",
            "description": "Number of plugins",
            "type": "gauge",
            "labels": ["status"]
        })
        
        # Event metrics
        metrics.append({
            "name": "sarya_events_total",
            "description": "Total number of events",
            "type": "counter",
            "labels": ["event_type"]
        })
        
        metrics.append({
            "name": "sarya_reflex_count",
            "description": "Number of reflex mappings",
            "type": "gauge",
            "labels": ["type"]
        })
        
        # Performance metrics
        metrics.append({
            "name": "sarya_clone_execution_seconds",
            "description": "Clone execution time in seconds",
            "type": "histogram",
            "labels": ["clone_type"]
        })
        
        metrics.append({
            "name": "sarya_api_request_seconds",
            "description": "API request processing time in seconds",
            "type": "histogram",
            "labels": ["endpoint", "method"]
        })
        
        # Memory metrics
        metrics.append({
            "name": "sarya_memory_usage_bytes",
            "description": "Memory usage in bytes",
            "type": "gauge",
            "labels": ["type"]
        })
        
        return metrics
    
    def get_metric_values(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get current values of metrics.
        
        Args:
            name: Optional name to filter by
            
        Returns:
            List of metric values
        """
        # Collect metrics to ensure up-to-date values
        self._collect_system_metrics()
        
        # Convert registry to text format
        metrics_text = prometheus_client.generate_latest(self.registry).decode('utf-8')
        
        # Parse metrics text
        metrics = []
        current_metric = None
        
        for line in metrics_text.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse metric line
            parts = line.split(' ')
            if len(parts) < 2:
                continue
            
            metric_name_with_labels = parts[0]
            metric_value = float(parts[1])
            
            # Extract metric name and labels
            if '{' in metric_name_with_labels:
                metric_name, labels_str = metric_name_with_labels.split('{', 1)
                labels_str = labels_str.rstrip('}')
                
                # Parse labels
                labels = {}
                for label_pair in labels_str.split(','):
                    if '=' in label_pair:
                        label_name, label_value = label_pair.split('=', 1)
                        labels[label_name] = label_value.strip('"')
            else:
                metric_name = metric_name_with_labels
                labels = {}
            
            # Skip if filtering by name and not matching
            if name and metric_name != name:
                continue
            
            # Add to result
            metrics.append({
                "name": metric_name,
                "value": metric_value,
                "labels": labels,
                "timestamp": time.time()
            })
        
        return metrics
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Returns:
            Dict containing system statistics
        """
        # Collect metrics to ensure up-to-date values
        self._collect_system_metrics()
        
        # Get memory usage
        memory_usage = {}
        for metric in self.get_metric_values("sarya_memory_usage_bytes"):
            memory_type = metric.get("labels", {}).get("type", "unknown")
            memory_usage[memory_type] = metric.get("value", 0)
        
        # Count clones
        clone_count = len(clone_manager.get_all_clone_info())
        active_clones = len([c for c in clone_manager.get_clones() if c.is_active()])
        
        return {
            "uptime": time.time() - self.start_time,
            "clone_count": clone_count,
            "active_clones": active_clones,
            "queue_size": clone_queue.get_queue_size(),
            "plugin_count": len(plugin_manager.get_loaded_plugins()),
            "event_count": sum(m.get("value", 0) for m in self.get_metric_values("sarya_events_total")),
            "memory_usage": memory_usage
        }
    
    def get_prometheus_metrics(self) -> str:
        """
        Get metrics in Prometheus exposition format.
        
        Returns:
            Metrics in Prometheus text format
        """
        # Collect metrics to ensure up-to-date values
        self._collect_system_metrics()
        
        # Generate metrics text
        return prometheus_client.generate_latest(self.registry).decode('utf-8')

# Create a singleton instance
metrics_manager = MetricsManager()
