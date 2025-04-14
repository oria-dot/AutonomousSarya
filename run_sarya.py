#!/usr/bin/env python3
"""
SARYA Runner
Starts the SARYA system with custom configuration.
"""
import os
import sys

from sarya import SaryaSystem

def main():
    """Start SARYA with custom configuration."""
    print("Starting SARYA system with custom configuration...")
    
    # Create SARYA instance
    sarya = SaryaSystem()
    
    # Initialize with config
    config_path = os.path.join(os.path.dirname(__file__), "sarya_config.json")
    if not sarya.initialize(config_path):
        print("Initialization failed, exiting")
        sys.exit(1)
    
    # Run the system
    sarya.run()

if __name__ == "__main__":
    main()