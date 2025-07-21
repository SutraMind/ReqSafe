#!/usr/bin/env python3
"""
Demo script for Memory Extractor orchestrator.

Shows the complete end-to-end workflow from input files to memory storage.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def demo_memory_extractor():
    """Demonstrate the memory extractor with sample data."""
    print("=" * 60)
    print("MEMORY EXTRACTOR DEMO")
    print("=" * 60)
    
    # Check if sample files exist
    compliance_file = "Compliance_report_ra_agent.txt"
    feedback_file = "human_feedback.txt"
    
    if not (Path(compliance_file).exists() and Path(feedback_file).exists()):
        print(f"❌ Sample files not found:")
        print(f"   - {compliance_file}: {'✓' if Path(compliance_file).exists() else '✗'}")
        print(f"   - {feedback_file}: {'✓' if Path(feedback_file).exists() else '✗'}")
        return False
    
    print(f"✓ Sample files found:")
    print(f"   - {compliance_file}")
    print(f"   - {feedback_file}")
    print()
    
    try:
        # Import with mocked database components to avoid connection issues
        from memory_management.memory_extractor import MemoryExtractor
        from memory_management.processors.stm_processor import STMProcessor
        from memory_management.processors.ltm_manager import LTMManager
        from memory_management.processors.rule_extractor import RuleExtractor, RuleGenerationResult
        from memory_management.models.stm_entry import STMEntry
        from memory_management.models.ltm_rule import LTMRule
        
        print("📦 Creating memory extractor with mocked components...")
        
        # Mock the database components to avoid actual database connections
        with patch('memory_management.memory_extractor.STMProcessor') as mock_stm, \
             patch('memory_management.memory_extractor.LTMManager') as mock_ltm, \
             patch('memory_management.memory_extractor.RuleExtractor') as mock_rule:
            
            # Setup STM processor mock
            mock_stm_instance = Mock(spec=STMProcessor)
            mock_stm_instance.create_entry.return_value = Mock(
                spec=STMEntry,
                scenario_id="ecommerce_r1_consent",
                to_dict=lambda: {"scenario_id": "ecommerce_r1_consent", "status": "created"}
            )
            mock_stm_instance.add_human_feedback.return_value = Mock(spec=STMEntry)
            mock_stm_instance.set_final_status.return_value = Mock(spec=STMEntry)
            mock_stm_instance.get_entry.return_value = Mock(spec=STMEntry)
            mock_stm_instance.add_ltm_rule_link.return_value = True
            mock_stm_instance.get_stats.return_value = {
                'total_entries': 5,
                'entries_with_feedback': 2,
                'entries_without_feedback': 3
            }
            mock_stm.return_value = mock_stm_instance
            
            # Setup LTM manager mock
            mock_ltm_instance = Mock(spec=LTMManager)
            mock_ltm_instance.store_ltm_rule.return_value = True
            mock_ltm_instance.get_all_rules.return_value = [
                Mock(rule_id='GDPR_consent_01', confidence_score=0.85, related_concepts=['consent', 'gdpr']),
                Mock(rule_id='GDPR_security_01', confidence_score=0.90, related_concepts=['security', 'hashing'])
            ]
            mock_ltm.return_value = mock_ltm_instance
            
            # Setup rule extractor mock
            mock_rule_instance = Mock(spec=RuleExtractor)
            def mock_extract_rule(stm_entry):
                rule = Mock(spec=LTMRule)
                rule.rule_id = f"GDPR_extracted_rule_01"
                rule.rule_text = "Extracted compliance rule from human feedback"
                rule.related_concepts = ["consent", "gdpr", "compliance"]
                rule.source_scenario_id = [stm_entry.scenario_id]
                rule.confidence_score = 0.85
                rule.to_dict.return_value = {
                    'rule_id': rule.rule_id,
                    'rule_text': rule.rule_text,
                    'related_concepts': rule.related_concepts,
                    'source_scenario_id': rule.source_scenario_id,
                    'confidence_score': rule.confidence_score
                }
                return RuleGenerationResult(success=True, rule=rule, confidence_score=0.85)
            
            mock_rule_instance.extract_rule_from_stm.side_effect = mock_extract_rule
            mock_rule.return_value = mock_rule_instance
            
            # Create the memory extractor
            extractor = MemoryExtractor()
            print("✓ Memory extractor initialized successfully")
            print()
            
            # Process the sample files
            print("🔄 Processing sample files...")
            result = extractor.extract_from_files(
                compliance_report_path=compliance_file,
                human_feedback_path=feedback_file,
                domain="ecommerce"
            )
            
            # Display results
            print()
            print("📊 EXTRACTION RESULTS")
            print("-" * 40)
            
            if result['success']:
                print("✅ Extraction completed successfully!")
                
                summary = result['extraction_summary']
                stats = summary['statistics']
                
                print(f"\n📈 Statistics:")
                print(f"   • Requirements processed: {stats['total_requirements_processed']}")
                print(f"   • STM entries created: {stats['stm_entries_created']}")
                print(f"   • LTM rules created: {stats['ltm_rules_created']}")
                print(f"   • Entries with feedback: {stats['entries_with_feedback']}")
                print(f"   • Success rate: {stats['processing_success_rate']:.1f}%")
                
                print(f"\n🔗 Traceability:")
                traceability = summary['traceability']
                print(f"   • STM to LTM links: {traceability['stm_to_ltm_links']}")
                print(f"   • Bidirectional links: {traceability['bidirectional_links_created']}")
                
                # Show some sample data
                stm_results = result['stm_results']
                if stm_results['entries']:
                    print(f"\n📝 Sample STM Entries:")
                    for i, entry in enumerate(stm_results['entries'][:3]):
                        print(f"   {i+1}. {entry['scenario_id']} (Req: {entry['requirement_number']})")
                
                ltm_results = result['ltm_results']
                if ltm_results['rules']:
                    print(f"\n🧠 Sample LTM Rules:")
                    for i, rule in enumerate(ltm_results['rules'][:3]):
                        print(f"   {i+1}. {rule['rule_id']} (Source: {rule['source_scenario_id']})")
                
            else:
                print("❌ Extraction failed!")
                print(f"Error: {result['error']}")
            
            print()
            
            # Get current statistics
            print("📊 Getting current memory statistics...")
            stats = extractor.get_extraction_statistics()
            
            if 'error' not in stats:
                print("✓ Memory statistics retrieved successfully")
                print(f"   • STM entries: {stats['stm_statistics']['total_entries']}")
                print(f"   • LTM rules: {stats['ltm_statistics']['total_rules']}")
                print(f"   • Average confidence: {stats['ltm_statistics']['average_confidence']:.2f}")
            else:
                print(f"❌ Failed to get statistics: {stats['error']}")
            
            print()
            
            # Validate results
            if result['success']:
                print("🔍 Validating extraction results...")
                validation = extractor.validate_extraction_results(result)
                
                if validation['is_valid']:
                    print("✅ Validation passed!")
                else:
                    print("⚠️  Validation issues found:")
                    for error in validation['errors']:
                        print(f"   • Error: {error}")
                
                if validation['warnings']:
                    print("⚠️  Warnings:")
                    for warning in validation['warnings']:
                        print(f"   • {warning}")
                
                if validation['recommendations']:
                    print("💡 Recommendations:")
                    for rec in validation['recommendations']:
                        print(f"   • {rec}")
            
            print()
            print("🔧 Closing memory extractor...")
            extractor.close()
            print("✓ Demo completed successfully!")
            
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required modules are available.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def demo_parsing_only():
    """Demonstrate just the parsing components without database dependencies."""
    print("\n" + "=" * 60)
    print("PARSING DEMO (No Database Required)")
    print("=" * 60)
    
    try:
        from memory_management.parsers.compliance_report_parser import ComplianceReportParser
        from memory_management.parsers.human_feedback_parser import HumanFeedbackParser
        
        # Check if sample files exist
        compliance_file = "Compliance_report_ra_agent.txt"
        feedback_file = "human_feedback.txt"
        
        if not (Path(compliance_file).exists() and Path(feedback_file).exists()):
            print("❌ Sample files not found for parsing demo")
            return False
        
        print("🔍 Testing compliance report parsing...")
        
        # Mock the LLM components to avoid external dependencies
        with patch('memory_management.parsers.compliance_report_parser.LLMClient') as mock_llm_client, \
             patch('memory_management.parsers.human_feedback_parser.LLMClient') as mock_llm_client2:
            
            # Setup mock LLM responses
            mock_client_instance = Mock()
            mock_client_instance.extract_structured_data.return_value = Mock(
                success=True,
                content='{"requirements": [{"requirement_number": "R1", "requirement_text": "Test requirement", "status": "Non-Compliant", "rationale": "Test rationale", "recommendation": "Test recommendation"}]}'
            )
            mock_llm_client.return_value = mock_client_instance
            mock_llm_client2.return_value = mock_client_instance
            
            # Test compliance report parsing
            compliance_parser = ComplianceReportParser()
            parsed_report = compliance_parser.parse_report_file(compliance_file)
            
            if parsed_report.parsing_success:
                print(f"✅ Compliance report parsed successfully!")
                print(f"   • Found {len(parsed_report.requirements)} requirements")
                
                # Show first requirement
                if parsed_report.requirements:
                    req = parsed_report.requirements[0]
                    print(f"   • Sample: {req.requirement_number} - {req.status}")
            else:
                print(f"❌ Compliance report parsing failed: {parsed_report.error_message}")
            
            print("\n🔍 Testing human feedback parsing...")
            
            # Setup mock for feedback parsing
            mock_client_instance.extract_structured_data.return_value = Mock(
                success=True,
                content='{"feedback_items": [{"requirement_reference": "R1", "decision": "No change", "rationale": "Test rationale", "suggestion": "Test suggestion"}]}'
            )
            
            # Test human feedback parsing
            feedback_parser = HumanFeedbackParser()
            parsed_feedback = feedback_parser.parse_feedback_file(feedback_file)
            
            if parsed_feedback.parsing_success:
                print(f"✅ Human feedback parsed successfully!")
                print(f"   • Found {len(parsed_feedback.feedback_items)} feedback items")
                
                # Show first feedback item
                if parsed_feedback.feedback_items:
                    item = parsed_feedback.feedback_items[0]
                    print(f"   • Sample: {item.requirement_reference} - {item.decision}")
            else:
                print(f"❌ Human feedback parsing failed: {parsed_feedback.error_message}")
            
            print("\n✓ Parsing demo completed!")
            return True
            
    except Exception as e:
        print(f"❌ Parsing demo error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Memory Extractor Demo")
    print()
    
    # Run the main demo
    success1 = demo_memory_extractor()
    
    # Run the parsing-only demo
    success2 = demo_parsing_only()
    
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    print(f"Memory Extractor Demo: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"Parsing Demo: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All demos completed successfully!")
        print("\nNext steps:")
        print("• Run integration tests: python -m pytest test_memory_extractor_integration.py")
        print("• Check the memory_management/memory_extractor.py for the main orchestrator")
        print("• Use MemoryExtractor.process_sample_data() to process existing files")
        sys.exit(0)
    else:
        print("\n⚠️  Some demos failed. Check the error messages above.")
        sys.exit(1)