#!/usr/bin/env python3
"""
Debug STM storage to see where entries are actually stored.
"""

import sys
from pathlib import Path
import redis
import json

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from memory_management.processors.stm_processor import STMProcessor
from memory_management.models.stm_entry import STMEntry, InitialAssessment

def test_stm_storage():
    """Test STM storage directly."""
    print("🔍 Testing STM Storage Directly")
    print("=" * 40)
    
    try:
        # Create STM processor
        stm_processor = STMProcessor(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password=None
        )
        print("✅ STM Processor created")
        
        # Create a test entry
        test_scenario_id = "test_debug_entry"
        initial_assessment = InitialAssessment(
            status="Non-Compliant",
            rationale="Test rationale for debugging",
            recommendation="Test recommendation for debugging"
        )
        
        print(f"📝 Creating test STM entry: {test_scenario_id}")
        
        # Create entry
        entry = stm_processor.create_entry(
            scenario_id=test_scenario_id,
            requirement_text="Test requirement for debugging STM storage",
            initial_assessment=initial_assessment
        )
        
        if entry:
            print(f"✅ Test entry created: {entry.scenario_id}")
            
            # Try to retrieve it
            retrieved = stm_processor.get_entry(test_scenario_id)
            if retrieved:
                print(f"✅ Test entry retrieved successfully")
                print(f"   Scenario ID: {retrieved.scenario_id}")
                print(f"   Status: {retrieved.initial_assessment.status}")
            else:
                print("❌ Failed to retrieve test entry")
        else:
            print("❌ Failed to create test entry")
        
        # Check what keys exist in Redis after our test
        print("\n🔍 Checking Redis keys after test:")
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        all_keys = r.keys("*")
        print(f"Total keys: {len(all_keys)}")
        
        for key in all_keys:
            print(f"  - {key}")
            if "test_debug" in key:
                value = r.get(key)
                print(f"    Value: {str(value)[:100]}...")
        
        # Clean up test entry
        if entry:
            stm_processor.delete_entry(test_scenario_id)
            print(f"🗑️  Cleaned up test entry")
        
    except Exception as e:
        print(f"❌ Error testing STM storage: {e}")
        import traceback
        traceback.print_exc()

def check_existing_stm_entries():
    """Check for existing STM entries using STM processor methods."""
    print("\n🔍 Checking Existing STM Entries via STM Processor")
    print("=" * 50)
    
    try:
        stm_processor = STMProcessor(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password=None
        )
        
        # Get statistics
        stats = stm_processor.get_stats()
        print(f"STM Statistics: {stats}")
        
        # Try to get entries that we know should exist
        known_scenario_ids = [
            "ecommerce_r1_consent",
            "ecommerce_r2_data_retention", 
            "ecommerce_r4_hashing"
        ]
        
        print(f"\nTrying to retrieve known scenario IDs:")
        for scenario_id in known_scenario_ids:
            entry = stm_processor.get_entry(scenario_id)
            if entry:
                print(f"✅ Found: {scenario_id}")
                print(f"   Status: {entry.initial_assessment.status if entry.initial_assessment else 'None'}")
                print(f"   Final Status: {entry.final_status}")
            else:
                print(f"❌ Not found: {scenario_id}")
        
    except Exception as e:
        print(f"❌ Error checking existing entries: {e}")

def main():
    """Run all debug tests."""
    test_stm_storage()
    check_existing_stm_entries()

if __name__ == "__main__":
    main()