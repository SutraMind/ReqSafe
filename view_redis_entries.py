#!/usr/bin/env python3
"""
View Redis STM entries in a formatted way.
"""

import redis
import json
import sys

def view_redis_entries():
    """View all STM entries in Redis."""
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        print("🔍 Redis STM Entries")
        print("=" * 40)
        
        # First, let's see ALL keys in Redis
        all_keys = r.keys("*")
        print(f"Total keys in Redis: {len(all_keys)}")
        
        if all_keys:
            print("\nAll keys found:")
            for key in all_keys[:20]:  # Show first 20 keys
                print(f"  - {key}")
            if len(all_keys) > 20:
                print(f"  ... and {len(all_keys) - 20} more")
        
        # Get all keys that look like scenario IDs
        ecommerce_keys = r.keys("ecommerce_*")
        stm_keys = r.keys("stm:*")  # Alternative pattern
        scenario_keys = r.keys("*scenario*")  # Another pattern
        
        print(f"\nKey patterns found:")
        print(f"  ecommerce_*: {len(ecommerce_keys)}")
        print(f"  stm:*: {len(stm_keys)}")
        print(f"  *scenario*: {len(scenario_keys)}")
        
        # Try to find STM entries with any pattern
        stm_entries = ecommerce_keys + stm_keys + scenario_keys
        stm_entries = list(set(stm_entries))  # Remove duplicates
        
        if not stm_entries:
            print("\n❌ No STM entries found with any pattern")
            
            # Let's check a few random keys to see the data structure
            if all_keys:
                print("\nSample key contents:")
                for key in all_keys[:3]:
                    value = r.get(key)
                    print(f"  {key}: {str(value)[:100]}...")
            return
        
        print(f"\nFound {len(stm_entries)} STM entries:\n")
        
        for i, key in enumerate(stm_entries, 1):
            print(f"{i}. Key: {key}")
            
            # Get the value
            value = r.get(key)
            if value:
                try:
                    # Parse JSON
                    data = json.loads(value)
                    
                    print(f"   Scenario ID: {data.get('scenario_id', 'Unknown')}")
                    print(f"   Requirement: {data.get('requirement_text', 'Unknown')[:80]}...")
                    print(f"   Initial Status: {data.get('initial_assessment', {}).get('status', 'Unknown')}")
                    print(f"   Final Status: {data.get('final_status', 'None')}")
                    print(f"   Has Feedback: {'Yes' if data.get('human_feedback') else 'No'}")
                    print(f"   Created: {data.get('created_at', 'Unknown')}")
                    
                except json.JSONDecodeError:
                    print(f"   Raw value: {value}")
            
            print()
        
        # Show Redis info
        info = r.info()
        print(f"Redis Info:")
        print(f"  Total Keys: {info.get('db0', {}).get('keys', 0)}")
        print(f"  Memory Used: {info.get('used_memory_human', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Error connecting to Redis: {e}")

if __name__ == "__main__":
    view_redis_entries()