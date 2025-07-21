#!/usr/bin/env python3
"""
Simple Demo Script for Compliance Memory Management Module.

Quick demonstration of memory extraction from compliance reports.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from memory_management.memory_extractor import MemoryExtractor


def main():
    """Simple memory extraction demo."""
    print("🧠 Simple Memory Extraction Demo")
    print("=" * 40)
    
    try:
        # Initialize memory extractor
        print("Initializing memory extractor...")
        memory_extractor = MemoryExtractor()
        
        # Process sample data
        print("Processing sample compliance data...")
        results = memory_extractor.process_sample_data()
        
        if results.get('success'):
            print("✅ Success!")
            
            # Show basic statistics
            stats = results.get('extraction_summary', {}).get('statistics', {})
            print(f"📊 Created {stats.get('stm_entries_created', 0)} STM entries")
            print(f"🧠 Generated {stats.get('ltm_rules_created', 0)} LTM rules")
            print(f"📈 Success rate: {stats.get('processing_success_rate', 0):.1f}%")
            
        else:
            print(f"❌ Failed: {results.get('error', 'Unknown error')}")
        
        # Cleanup
        memory_extractor.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())