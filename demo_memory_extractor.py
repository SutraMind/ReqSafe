#!/usr/bin/env python3
"""
Demo Script for Compliance Memory Management Module.

This script demonstrates the complete workflow:
1. Extract data from compliance reports and human feedback
2. Create Short-Term Memory (STM) entries
3. Generate Long-Term Memory (LTM) rules
4. Show traceability and statistics
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from memory_management.memory_extractor import MemoryExtractor, MemoryExtractionError
from memory_management.api.memory_api import MemoryAPI
from memory_management.processors.traceability_service import TraceabilityService
from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager


def print_banner():
    """Print application banner."""
    print("🧠 Compliance Memory Management Module - Demo")
    print("=" * 60)
    print("Processing compliance reports and human feedback to create")
    print("Short-Term Memory (STM) and Long-Term Memory (LTM)")
    print("=" * 60)


def check_input_files():
    """Check if required input files exist."""
    compliance_file = "Compliance_report_ra_agent.txt"
    feedback_file = "human_feedback.txt"
    
    files_exist = True
    
    if not Path(compliance_file).exists():
        print(f"❌ Missing: {compliance_file}")
        files_exist = False
    else:
        print(f"✅ Found: {compliance_file}")
    
    if not Path(feedback_file).exists():
        print(f"❌ Missing: {feedback_file}")
        files_exist = False
    else:
        print(f"✅ Found: {feedback_file}")
    
    return files_exist, compliance_file, feedback_file


def display_extraction_results(results):
    """Display extraction results in a formatted way."""
    print("\n📊 EXTRACTION RESULTS")
    print("=" * 40)
    
    if not results.get('success'):
        print(f"❌ Extraction failed: {results.get('error', 'Unknown error')}")
        return
    
    print("✅ Extraction successful!")
    
    # Display summary statistics
    summary = results.get('extraction_summary', {})
    stats = summary.get('statistics', {})
    
    print(f"\n📈 Statistics:")
    print(f"   Success Rate: {stats.get('processing_success_rate', 0):.1f}%")
    print(f"   STM Entries Created: {stats.get('stm_entries_created', 0)}")
    print(f"   LTM Rules Created: {stats.get('ltm_rules_created', 0)}")
    print(f"   Entries with Feedback: {stats.get('entries_with_feedback', 0)}")
    
    # Display STM entries
    stm_results = results.get('stm_results', [])
    if stm_results:
        print(f"\n📝 Short-Term Memory Entries ({len(stm_results)}):")
        for i, stm_entry in enumerate(stm_results[:3], 1):  # Show first 3
            print(f"   {i}. {stm_entry.get('scenario_id', 'Unknown')}")
            print(f"      Status: {stm_entry.get('final_status', 'Unknown')}")
            print(f"      Requirement: {stm_entry.get('requirement_text', '')[:80]}...")
    
    # Display LTM rules
    ltm_results = results.get('ltm_results', [])
    if ltm_results:
        print(f"\n🧠 Long-Term Memory Rules ({len(ltm_results)}):")
        for i, ltm_rule in enumerate(ltm_results[:3], 1):  # Show first 3
            print(f"   {i}. {ltm_rule.get('rule_id', 'Unknown')}")
            print(f"      Confidence: {ltm_rule.get('confidence_score', 0):.2f}")
            print(f"      Concepts: {', '.join(ltm_rule.get('related_concepts', [])[:3])}")
            print(f"      Rule: {ltm_rule.get('rule_text', '')[:80]}...")


def demonstrate_api_usage(results):
    """Demonstrate API usage with the extracted data."""
    print("\n🔌 API DEMONSTRATION")
    print("=" * 40)
    
    try:
        api = MemoryAPI()
        
        # Test health check
        health = api.health_check()
        print(f"System Health: {'✅ Healthy' if health.get('status') == 'success' else '❌ Unhealthy'}")
        
        # Test STM retrieval
        stm_results = results.get('stm_results', [])
        if stm_results:
            first_scenario = stm_results[0].get('scenario_id')
            if first_scenario:
                stm_response = api.get_stm_entry(first_scenario)
                if stm_response.get('status') == 'success':
                    print(f"✅ STM Retrieval: Successfully retrieved {first_scenario}")
                else:
                    print(f"❌ STM Retrieval: Failed to retrieve {first_scenario}")
        
        # Test LTM search
        search_response = api.search_ltm_rules("GDPR", ["Compliance", "Privacy"])
        if search_response.get('status') == 'success':
            rules_found = len(search_response.get('data', []))
            print(f"✅ LTM Search: Found {rules_found} rules for GDPR compliance")
        else:
            print(f"❌ LTM Search: Search failed")
        
        # Get system statistics
        stats_response = api.get_system_stats()
        if stats_response.get('status') == 'success':
            stats_data = stats_response.get('data', {})
            print(f"📊 System Stats: {stats_data.get('total_stm', 0)} STM entries, {stats_data.get('total_ltm', 0)} LTM rules")
        
        api.close()
        
    except Exception as e:
        print(f"❌ API Demo failed: {e}")


def demonstrate_traceability():
    """Demonstrate traceability features."""
    print("\n🔗 TRACEABILITY DEMONSTRATION")
    print("=" * 40)
    
    try:
        stm_processor = STMProcessor()
        ltm_manager = LTMManager()
        traceability_service = TraceabilityService(stm_processor, ltm_manager)
        
        # Get some entries to demonstrate traceability
        stm_stats = stm_processor.get_stats()
        ltm_rules = ltm_manager.get_all_rules()
        
        print(f"📝 STM Entries: {stm_stats.get('total_entries', 0)}")
        print(f"🧠 LTM Rules: {len(ltm_rules)}")
        
        # Demonstrate traceability validation
        integrity_result = traceability_service.validate_traceability_integrity()
        if integrity_result.get('is_valid'):
            print("✅ Traceability Integrity: All links are valid")
        else:
            errors = integrity_result.get('errors', [])
            print(f"⚠️  Traceability Issues: {len(errors)} problems found")
        
        ltm_manager.close()
        
    except Exception as e:
        print(f"❌ Traceability demo failed: {e}")


def save_results_to_file(results, filename="memory_extraction_results.json"):
    """Save extraction results to a JSON file."""
    try:
        # Convert datetime objects to strings for JSON serialization
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=json_serializer, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        
    except Exception as e:
        print(f"❌ Failed to save results: {e}")


def main():
    """Main execution function."""
    print_banner()
    
    # Step 1: Check input files
    print("\n🔍 CHECKING INPUT FILES")
    print("-" * 30)
    files_exist, compliance_file, feedback_file = check_input_files()
    
    if not files_exist:
        print("\n❌ Required input files are missing!")
        print("Please ensure the following files exist:")
        print("  - Compliance_report_ra_agent.txt")
        print("  - human_feedback.txt")
        return 1
    
    # Step 2: Initialize memory extractor
    print("\n🚀 INITIALIZING MEMORY EXTRACTOR")
    print("-" * 40)
    
    try:
        memory_extractor = MemoryExtractor()
        print("✅ Memory extractor initialized successfully")
    except MemoryExtractionError as e:
        print(f"❌ Failed to initialize memory extractor: {e}")
        print("\nPlease ensure Redis and Neo4j are running:")
        print("  Redis: docker run -d --name redis-memory -p 6379:6379 redis:latest")
        print("  Neo4j: docker run -d --name neo4j-memory -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:latest")
        return 1
    
    # Step 3: Extract memory from files
    print("\n⚙️  EXTRACTING MEMORY FROM FILES")
    print("-" * 40)
    
    start_time = time.time()
    
    try:
        results = memory_extractor.extract_from_files(
            compliance_report_path=compliance_file,
            human_feedback_path=feedback_file,
            domain="ecommerce"
        )
        
        extraction_time = time.time() - start_time
        print(f"⏱️  Extraction completed in {extraction_time:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return 1
    
    # Step 4: Display results
    display_extraction_results(results)
    
    # Step 5: Save results
    print("\n💾 SAVING RESULTS")
    print("-" * 20)
    save_results_to_file(results)
    
    # Step 6: Demonstrate API usage
    if results.get('success'):
        demonstrate_api_usage(results)
        demonstrate_traceability()
    
    # Step 7: Final summary
    print("\n🎉 PROCESSING COMPLETE")
    print("=" * 30)
    
    if results.get('success'):
        print("✅ Memory extraction successful!")
        print("📊 Check the results above and in memory_extraction_results.json")
        print("🔌 Memory data is now available via the API")
        print("🧠 Short-term and long-term memories have been created")
    else:
        print("❌ Memory extraction failed!")
        print("Please check the error messages above")
    
    # Cleanup
    try:
        memory_extractor.close()
    except:
        pass
    
    return 0 if results.get('success') else 1


if __name__ == "__main__":
    sys.exit(main())