#!/usr/bin/env python3
"""
Startup script for the Memory Management Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from memory_management.config.startup import initialize_app, get_app


def main():
    """Main entry point."""
    print("Starting Memory Management Module...")
    
    # Initialize the application
    if not initialize_app():
        print("Failed to initialize application")
        sys.exit(1)
    
    app = get_app()
    
    # Check initial health
    health_status = app.get_health_status()
    print(f"Initial health status: {health_status['overall_status']}")
    
    if health_status['overall_status'] == 'unhealthy':
        print("Warning: Some services are unhealthy")
        for service_name, service_health in health_status['services'].items():
            if service_health['status'] == 'unhealthy':
                print(f"  - {service_name}: {service_health['message']}")
    
    print("Memory Management Module started successfully")
    print("Press Ctrl+C to stop")
    
    try:
        # Keep the application running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        app.shutdown()


if __name__ == "__main__":
    main()