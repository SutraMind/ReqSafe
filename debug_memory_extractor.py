#!/usr/bin/env python3
"""
Debug script to check memory extractor initialization issues.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check environment variables."""
    print("🔍 CHECKING ENVIRONMENT VARIABLES")
    print("=" * 40)
    
    # Load .env file
    load_dotenv()
    
    neo4j_vars = {
        'NEO4J_URI': os.getenv('NEO4J_URI'),
        'NEO4J_USERNAME': os.getenv('NEO4J_USERNAME'), 
        'NEO4J_PASSWORD': os.getenv('NEO4J_PASSWORD'),
        'NEO4J_DATABASE': os.getenv('NEO4J_DATABASE')
    }
    
    redis_vars = {
        'REDIS_HOST': os.getenv('REDIS_HOST'),
        'REDIS_PORT': os.getenv('REDIS_PORT'),
        'REDIS_DB': os.getenv('REDIS_DB'),
        'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD')
    }
    
    print("Neo4j Environment Variables:")
    for key, value in neo4j_vars.items():
        print(f"  {key}: {value}")
    
    print("\nRedis Environment Variables:")
    for key, value in redis_vars.items():
        print(f"  {key}: {value}")
    
    return neo4j_vars, redis_vars

def test_direct_connections(neo4j_vars, redis_vars):
    """Test direct database connections."""
    print("\n🔌 TESTING DIRECT CONNECTIONS")
    print("=" * 40)
    
    # Test Redis
    try:
        import redis
        r = redis.Redis(
            host=redis_vars['REDIS_HOST'] or 'localhost',
            port=int(redis_vars['REDIS_PORT'] or 6379),
            db=int(redis_vars['REDIS_DB'] or 0),
            decode_responses=True
        )
        r.ping()
        print("✅ Redis: Direct connection successful")
    except Exception as e:
        print(f"❌ Redis: Direct connection failed - {e}")
    
    # Test Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            neo4j_vars['NEO4J_URI'] or 'bolt://localhost:7687',
            auth=(
                neo4j_vars['NEO4J_USERNAME'] or 'neo4j',
                neo4j_vars['NEO4J_PASSWORD'] or 'password123'
            )
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        print("✅ Neo4j: Direct connection successful")
    except Exception as e:
        print(f"❌ Neo4j: Direct connection failed - {e}")

def test_component_initialization():
    """Test individual component initialization."""
    print("\n🧩 TESTING COMPONENT INITIALIZATION")
    print("=" * 40)
    
    # Test STM Processor
    try:
        from memory_management.processors.stm_processor import STMProcessor
        stm = STMProcessor()
        print("✅ STMProcessor: Initialized successfully")
    except Exception as e:
        print(f"❌ STMProcessor: Failed - {e}")
    
    # Test LTM Manager
    try:
        from memory_management.processors.ltm_manager import LTMManager
        ltm = LTMManager()
        print("✅ LTMManager: Initialized successfully")
        ltm.close()
    except Exception as e:
        print(f"❌ LTMManager: Failed - {e}")
    
    # Test Rule Extractor
    try:
        from memory_management.processors.rule_extractor import RuleExtractor
        rule_extractor = RuleExtractor()
        print("✅ RuleExtractor: Initialized successfully")
    except Exception as e:
        print(f"❌ RuleExtractor: Failed - {e}")

def test_memory_extractor_step_by_step():
    """Test memory extractor initialization step by step."""
    print("\n🧠 TESTING MEMORY EXTRACTOR STEP BY STEP")
    print("=" * 40)
    
    try:
        from memory_management.parsers.compliance_report_parser import ComplianceReportParser
        parser = ComplianceReportParser()
        print("✅ ComplianceReportParser: OK")
    except Exception as e:
        print(f"❌ ComplianceReportParser: {e}")
    
    try:
        from memory_management.parsers.human_feedback_parser import HumanFeedbackParser
        parser = HumanFeedbackParser()
        print("✅ HumanFeedbackParser: OK")
    except Exception as e:
        print(f"❌ HumanFeedbackParser: {e}")
    
    try:
        from memory_management.utils.scenario_id_generator import ScenarioIdGenerator
        generator = ScenarioIdGenerator()
        print("✅ ScenarioIdGenerator: OK")
    except Exception as e:
        print(f"❌ ScenarioIdGenerator: {e}")
    
    # Now try the full memory extractor
    try:
        from memory_management.memory_extractor import MemoryExtractor
        extractor = MemoryExtractor()
        print("✅ MemoryExtractor: Initialized successfully!")
        extractor.close()
    except Exception as e:
        print(f"❌ MemoryExtractor: Failed - {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run debug checks."""
    print("🐛 Memory Extractor Debug Tool")
    print("=" * 50)
    
    # Check environment
    neo4j_vars, redis_vars = check_environment()
    
    # Test direct connections
    test_direct_connections(neo4j_vars, redis_vars)
    
    # Test component initialization
    test_component_initialization()
    
    # Test memory extractor step by step
    test_memory_extractor_step_by_step()
    
    print("\n🎯 DEBUG COMPLETE")
    print("=" * 20)

if __name__ == "__main__":
    main()