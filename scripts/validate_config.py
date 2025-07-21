#!/usr/bin/env python3
"""
Configuration validation script for the Memory Management Module.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from memory_management.config.settings import get_settings, validate_environment


def main():
    """Validate configuration and environment."""
    print("Memory Management Module - Configuration Validation")
    print("=" * 50)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    if validate_environment():
        print("✓ All required environment variables are set")
    else:
        print("✗ Missing required environment variables")
        return False
    
    # Load and validate settings
    print("\n2. Loading configuration...")
    try:
        settings = get_settings()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False
    
    # Validate configuration
    print("\n3. Validating configuration...")
    if settings.validate():
        print("✓ Configuration is valid")
    else:
        print("✗ Configuration validation failed")
        return False
    
    # Display configuration summary
    print("\n4. Configuration Summary:")
    print(f"   Environment: {settings.environment}")
    print(f"   Debug mode: {settings.debug}")
    print(f"   Redis: {settings.redis.host}:{settings.redis.port}")
    print(f"   Neo4j: {settings.neo4j.uri}")
    print(f"   Ollama: {settings.ollama.base_url}")
    print(f"   API: {settings.api.host}:{settings.api.port}")
    print(f"   Log level: {settings.logging.level}")
    
    print("\n✓ Configuration validation completed successfully")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)