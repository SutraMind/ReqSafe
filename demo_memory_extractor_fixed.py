#!/usr/bin/env python3
"""
Fixed Demo Script with Explicit Database Parameters.

This version bypasses environment variable issues by using explicit parameters.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager
from memory_management.processors.rule_extractor import RuleExtractor
from memory_management.memory_extractor import MemoryExtractor


def print_banner():
    """Print application banner."""
    print("🧠 Compliance Memory Management Module - Fixed Demo")
    print("=" * 60)
    print("Using explicit database parameters to bypass env issues")
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


def create_memory_extractor_with_explicit_params():
    """Create memory extractor with explicit database parameters."""
    print("🔧 Creating components with explicit parameters...")
    
    try:
        # Create STM processor (Redis - no auth)
        print("  Initializing STM Processor (Redis)...")
        stm_processor = STMProcessor(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password=None  # No password
        )
        print("  ✅ STM Processor initialized")
        
        # Create LTM manager (Neo4j - with explicit auth)
        print("  Initializing LTM Manager (Neo4j)...")
        ltm_manager = LTMManager(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password123"
        )
        print("  ✅ LTM Manager initialized")
        
        # Create rule extractor
        print("  Initializing Rule Extractor...")
        rule_extractor = RuleExtractor()
        print("  ✅ Rule Extractor initialized")
        
        # Create memory extractor with explicit components
        print("  Initializing Memory Extractor...")
        memory_extractor = MemoryExtractor(
            stm_processor=stm_processor,
            ltm_manager=ltm_manager,
            rule_extractor=rule_extractor
        )
        print("  ✅ Memory Extractor initialized")
        
        return memory_extractor
        
    except Exception as e:
        print(f"  ❌ Failed to initialize: {e}")
        raise


def display_results(results):
    """Display extraction results."""
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
    
    # Display first few STM entries
    stm_results = results.get('stm_results', {})
    if isinstance(stm_results, dict) and 'entries' in stm_results:
        entries = stm_results['entries']
        if entries:
            print(f"\n📝 Short-Term Memory Entries ({len(entries)}):")
            for i, entry in enumerate(entries[:3], 1):
                scenario_id = entry.get('scenario_id', 'Unknown')
                entry_data = entry.get('entry', {})
                final_status = entry_data.get('final_status', 'Unknown')
                requirement_text = entry_data.get('requirement_text', '')
                print(f"   {i}. {scenario_id}")
                print(f"      Status: {final_status}")
                print(f"      Requirement: {requirement_text[:80]}...")
    
    # Display first few LTM rules
    ltm_results = results.get('ltm_results', {})
    if isinstance(ltm_results, dict) and 'rules' in ltm_results:
        rules = ltm_results['rules']
        if rules:
            print(f"\n🧠 Long-Term Memory Rules ({len(rules)}):")
            for i, rule in enumerate(rules[:3], 1):
                rule_id = rule.get('rule_id', 'Unknown')
                rule_data = rule.get('rule', {})
                confidence = rule_data.get('confidence_score', 0)
                concepts = rule_data.get('related_concepts', [])
                rule_text = rule_data.get('rule_text', '')
                print(f"   {i}. {rule_id}")
                print(f"      Confidence: {confidence:.2f}")
                print(f"      Concepts: {', '.join(concepts[:3])}")
                print(f"      Rule: {rule_text[:80]}...")


def main():
    """Main execution function."""
    print_banner()
    
    # Step 1: Check input files
    print("\n🔍 CHECKING INPUT FILES")
    print("-" * 30)
    files_exist, compliance_file, feedback_file = check_input_files()
    
    if not files_exist:
        print("\n❌ Required input files are missing!")
        return 1
    
    # Step 2: Initialize memory extractor with explicit parameters
    print("\n🚀 INITIALIZING MEMORY EXTRACTOR")
    print("-" * 40)
    
    try:
        memory_extractor = create_memory_extractor_with_explicit_params()
        print("✅ Memory extractor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize memory extractor: {e}")
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
    display_results(results)
    
    # Step 5: Save results
    print("\n💾 SAVING RESULTS")
    print("-" * 20)
    try:
        with open("memory_extraction_results_fixed.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        print("💾 Results saved to: memory_extraction_results_fixed.json")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")
    
    # Step 6: Final summary
    print("\n🎉 PROCESSING COMPLETE")
    print("=" * 30)
    
    if results.get('success'):
        print("✅ Memory extraction successful!")
        print("📊 Check the results above and in memory_extraction_results_fixed.json")
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