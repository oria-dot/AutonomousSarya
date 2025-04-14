#!/usr/bin/env python3
"""
SARYA - AI Intelligence Framework
Main entry point for the SARYA system.
"""
import argparse
import asyncio
import logging
import os
import signal
import sys
import threading
import time
from typing import List, Optional

from api.main import start_api
from clone_system.clone_manager import clone_manager
from clone_system.clone_registry import clone_registry
from clone_system.clone_worker import worker_pool
from core.config import config_manager
from core.event_bus import Event, event_bus
from core.intelligence import IntelligenceModule
from core.memory import memory_system
from core.plugin_manager import plugin_manager
from metrics.prometheus_metrics import metrics_manager
from reflex_system.emotional_reflex import emotional_reflex_manager
from reflex_system.reflex_processor import reflex_processor
from reflex_system.spiritual_reflex import spiritual_reflex_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("sarya.log")
    ]
)
logger = logging.getLogger("sarya")

# Create intelligence module instance
intelligence_module = IntelligenceModule()

class SaryaSystem:
    """
    Main SARYA system class.
    Manages the lifecycle of all system components.
    """
    
    def __init__(self):
        """Initialize the SARYA system."""
        self.running = False
        self.event_loop = None
        self.components = []
        self.api_thread = None
    
    def initialize(self, config_path: Optional[str] = None) -> bool:
        """
        Initialize the SARYA system.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            bool: True if initialization was successful
        """
        logger.info("Initializing SARYA system")
        
        # Load configuration
        if not config_manager.load(config_path):
            logger.error("Failed to load configuration")
            return False
        
        # Set up event loop for async operations
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        
        # Set event loop for event bus
        event_bus.set_event_loop(self.event_loop)
        
        # Initialize components in order
        self.components = [
            memory_system,          # Memory system (first to allow others to use it)
            intelligence_module,     # Intelligence module (for reasoning and decision making)
            emotional_reflex_manager,  # Emotional reflex system
            spiritual_reflex_manager,  # Spiritual reflex system
            reflex_processor,        # Reflex processor
            plugin_manager,         # Plugin manager
            clone_registry,         # Clone registry
            clone_manager,          # Clone manager
            worker_pool,            # Clone worker pool
            metrics_manager         # Metrics manager (last to monitor others)
        ]
        
        # Initialize each component
        for component in self.components:
            if not component.initialize():
                logger.error(f"Failed to initialize {component.name}")
                return False
            logger.info(f"Initialized {component.name}")
        
        logger.info("SARYA system initialized successfully")
        return True
    
    def start(self) -> bool:
        """
        Start the SARYA system.
        
        Returns:
            bool: True if startup was successful
        """
        if self.running:
            logger.warning("SARYA system already running")
            return True
        
        logger.info("Starting SARYA system")
        
        # Start each component
        for component in self.components:
            if not component.start():
                logger.error(f"Failed to start {component.name}")
                return False
            logger.info(f"Started {component.name}")
        
        # Emit system startup event
        event_bus.publish(Event(
            event_type="system.startup",
            source="sarya",
            data={"timestamp": time.time()}
        ))
        
        # Start API server in a separate thread
        self.api_thread = threading.Thread(
            target=start_api,
            daemon=True
        )
        self.api_thread.start()
        
        self.running = True
        logger.info("SARYA system started successfully")
        return True
    
    def stop(self) -> bool:
        """
        Stop the SARYA system.
        
        Returns:
            bool: True if shutdown was successful
        """
        if not self.running:
            logger.warning("SARYA system not running")
            return True
        
        logger.info("Stopping SARYA system")
        
        # Emit system shutdown event
        event_bus.publish(Event(
            event_type="system.shutdown",
            source="sarya",
            data={"timestamp": time.time()}
        ))
        
        # Stop components in reverse order
        for component in reversed(self.components):
            if not component.stop():
                logger.error(f"Failed to stop {component.name}")
            else:
                logger.info(f"Stopped {component.name}")
        
        self.running = False
        logger.info("SARYA system stopped successfully")
        return True
    
    def run(self) -> None:
        """Run the SARYA system and wait for termination signal."""
        # Set up signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the system
        if not self.start():
            logger.error("Failed to start SARYA system")
            return
        
        logger.info("SARYA system running, press Ctrl+C to stop")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
            self.stop()

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SARYA - AI Intelligence Framework")
    parser.add_argument(
        "--config", 
        help="Path to configuration file",
        default=os.environ.get("SARYA_CONFIG")
    )
    parser.add_argument(
        "--debug", 
        help="Enable debug logging",
        action="store_true"
    )
    args = parser.parse_args()
    
    # Set up logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # Create and run the system
    sarya = SaryaSystem()
    
    if not sarya.initialize(args.config):
        logger.error("Initialization failed, exiting")
        sys.exit(1)
    
    sarya.run()

if __name__ == "__main__":
    main()
