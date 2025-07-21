#!/usr/bin/env python3
"""
Test memory extractor environment loading.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_env_loading():
    """Test environment variable loading."""
    print("🔍 Testing Environment Loading")
    print("=" * 40)
    
    # Load .env file explicitly
    load_dotenv()
    
    print("Environment variables:")
    print(f"  NEO4J_URI: {os.getenv('NEO4J_URI')}")
    print(f"  NEO4J_USERNAME: {os.getenv('NEO4J_USERNAME')}")
    print(f"  NEO4J_PASSWORD: {os.getenv('NEO4J_PASSWORD')}")
    print(f"  REDIS_HOST: {os.getenv('REDIS_HOST')}")
    print(f"  REDIS_PASSWORD: '{os.getenv('REDIS_PASSWORD')}'")

def test_ltm_manager_direct():
    """Test LTM Manager initialization directly."""
    print("\n🧠 Testing LTM Manager Direct")
    print("=" * 40)
    
    try:
        from memory_management.processors.ltm_manager import LTMManager
        
        # Try with explicit parameters
        ltm = LTMManager(
            uri="bolt://localhost:7687",
            username="neo4j", 
            password="password123"
        )
        print("✅ LTM Manager with explicit params: SUCCESS")
        ltm.close()
        
        # Try with environment variables
        ltm2 = LTMManager()
        print("✅ LTM Manager with env vars: SUCCESS")
        ltm2.close()
        
    except Exception as e:
        print(f"❌ LTM Manager failed: {e}")

def test_memory_extractor_with_explicit_params():
    """Test memory extractor with explicit component initialization."""
    print("\n🚀 Testing Memory Extractor with Explicit Params")
    print("=" * 40)
    
    try:
        from memory_management.processors.stm_processor import STMProcessor
        from memory_management.processors.ltm_manager import LTMManager
        from memory_management.processors.rule_extractor import RuleExtractor
        from memory_management.memory_extractor import MemoryExtractor
        
        # Initialize components explicitly
        stm_processor = STMProcessor()
        ltm_manager = LTMManager(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password123"
        )
        rule_extractor = RuleExtractor()
        
        # Create memory extractor with explicit components
        extractor = MemoryExtractor(
            stm_processor=stm_processor,
            ltm_manager=ltm_manager,
            rule_extractor=rule_extractor
        )
        
        print("✅ Memory Extractor with explicit components: SUCCESS")
        extractor.close()
        
    except Exception as e:
        print(f"❌ Memory Extractor failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests."""
    test_env_loading()
    test_ltm_manager_direct()
    test_memory_extractor_with_explicit_params()

if __name__ == "__main__":
    main()