"""
Demo script for Memory API functionality using mocked processors.

Shows how to use the unified Memory API for STM and LTM operations without requiring actual databases.
"""

import json
from unittest.mock import Mock
from memory_management.api.memory_api import MemoryAPI
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule


def create_mock_stm_processor():
    """Create a mock STM processor with sample data."""
    mock = Mock()
    
    # Sample STM entry
    sample_entry = STMEntry(
        scenario_id="ecommerce_r1_consent",
        requirement_text="During account signup, the user must agree to data processing terms",
        initial_assessment=InitialAssessment(
            status="Non-Compliant",
            rationale="Bundled consent violates GDPR Article 7 requirements for specific consent",
            recommendation="Implement separate, unticked opt-in checkboxes for each data processing purpose"
        )
    )
    
    # Mock methods
    mock.get_entry.return_value = sample_entry
    mock.create_entry.return_value = sample_entry
    mock.add_human_feedback.return_value = sample_entry
    mock.set_final_status.return_value = sample_entry
    mock.update_entry.return_value = sample_entry
    mock.list_entries.return_value = [sample_entry]
    mock.get_entries_by_status.return_value = [sample_entry]
    mock.get_entries_with_feedback.return_value = []
    mock.get_entries_without_feedback.return_value = [sample_entry]
    mock.get_stats.return_value = {
        "total_entries": 1,
        "entries_with_feedback": 0,
        "entries_without_feedback": 1,
        "status_breakdown": {"Non-Compliant": 1}
    }
    mock.get_traceability_info.return_value = {
        "stm_entry": sample_entry.to_dict(),
        "related_ltm_rules": ["GDPR_Consent_Separate_01"],
        "has_human_feedback": False,
        "final_status": None
    }
    
    # Mock Redis client for health check
    mock.redis_client = Mock()
    mock.redis_client.ping.return_value = True
    
    return mock


def create_mock_ltm_manager():
    """Create a mock LTM manager with sample data."""
    mock = Mock()
    
    # Sample LTM rule
    sample_rule = LTMRule(
        rule_id="GDPR_Consent_Separate_01",
        rule_text="Consent must be separate and specific for each data processing purpose",
        related_concepts=["Consent", "GDPR", "Data Processing", "Specific Purpose"],
        source_scenario_id=["ecommerce_r1_consent"],
        confidence_score=0.95
    )
    
    # Mock methods
    mock.get_ltm_rule.return_value = sample_rule
    mock.search_ltm_rules.return_value = [sample_rule]
    mock.semantic_search_rules.return_value = [(sample_rule, 0.85)]
    mock.get_concept_relationships.return_value = [
        {
            "rule_id": "GDPR_Consent_Separate_01",
            "rule_text": "Consent must be separate and specific for each data processing purpose",
            "confidence_score": 0.95,
            "source_scenarios": ["ecommerce_r1_consent"]
        }
    ]
    mock.get_rule_traceability.return_value = {
        "rule": sample_rule.to_dict(),
        "related_concepts": ["Consent", "GDPR", "Data Processing"],
        "source_scenarios": ["ecommerce_r1_consent"],
        "governing_policies": ["GDPR"]
    }
    mock.get_rules_by_source_scenario.return_value = [sample_rule]
    mock.get_complete_audit_trail.return_value = {
        "rule": sample_rule.to_dict(),
        "version_history": [sample_rule.to_dict()],
        "source_scenarios": ["ecommerce_r1_consent"],
        "concept_relationships": {"Consent": [sample_rule.to_dict()]},
        "audit_metadata": {
            "total_versions": 1,
            "source_count": 1,
            "concept_count": 4,
            "confidence_score": 0.95
        }
    }
    mock.get_all_rules.return_value = [sample_rule]
    
    # Mock Neo4j driver for health check
    mock.driver = Mock()
    session_mock = Mock()
    session_mock.run.return_value = None
    mock.driver.session.return_value.__enter__ = Mock(return_value=session_mock)
    mock.driver.session.return_value.__exit__ = Mock(return_value=None)
    mock.close = Mock()
    
    return mock


def print_response(title: str, response: dict):
    """Pretty print API response."""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(json.dumps(response, indent=2))


def demo_memory_api():
    """Demonstrate Memory API functionality."""
    print("Memory API Demo (Mocked)")
    print("========================")
    
    # Create mocked processors
    mock_stm = create_mock_stm_processor()
    mock_ltm = create_mock_ltm_manager()
    
    # Initialize Memory API with mocked processors
    api = MemoryAPI(stm_processor=mock_stm, ltm_manager=mock_ltm)
    
    try:
        # 1. Health Check
        print("\n1. Health Check")
        health_response = api.health_check()
        print_response("Health Check", health_response)
        
        # 2. Add New Assessment
        print("\n2. Adding New Assessment")
        assessment_data = {
            "scenario_id": "ecommerce_r1_consent",
            "requirement_text": "During account signup, the user must agree to data processing terms",
            "initial_assessment": {
                "status": "Non-Compliant",
                "rationale": "Bundled consent violates GDPR Article 7 requirements for specific consent",
                "recommendation": "Implement separate, unticked opt-in checkboxes for each data processing purpose"
            }
        }
        
        add_response = api.add_new_assessment(assessment_data)
        print_response("Add Assessment", add_response)
        
        # 3. Get STM Entry
        print("\n3. Retrieving STM Entry")
        get_response = api.get_stm_entry("ecommerce_r1_consent")
        print_response("Get STM Entry", get_response)
        
        # 4. Update with Human Feedback
        print("\n4. Adding Human Feedback")
        feedback_data = {
            "decision": "Approve",
            "rationale": "Agent's analysis is correct. GDPR requires separate consent for each purpose.",
            "suggestion": "Implement separate checkboxes and ensure they are not pre-ticked",
            "final_status": "Non-Compliant"
        }
        
        # Update mock to return entry with feedback
        entry_with_feedback = STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="During account signup, the user must agree to data processing terms",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="Bundled consent violates GDPR Article 7 requirements for specific consent",
                recommendation="Implement separate, unticked opt-in checkboxes for each data processing purpose"
            ),
            human_feedback=HumanFeedback(
                decision="Approve",
                rationale="Agent's analysis is correct. GDPR requires separate consent for each purpose.",
                suggestion="Implement separate checkboxes and ensure they are not pre-ticked"
            ),
            final_status="Non-Compliant"
        )
        mock_stm.add_human_feedback.return_value = entry_with_feedback
        mock_stm.set_final_status.return_value = entry_with_feedback
        
        feedback_response = api.update_with_feedback("ecommerce_r1_consent", feedback_data)
        print_response("Update with Feedback", feedback_response)
        
        # 5. Search LTM Rules (Structured)
        print("\n5. Searching LTM Rules (Structured)")
        search_response = api.search_ltm_rules(
            concepts=["Consent", "GDPR"],
            keywords=["separate", "specific"],
            limit=5
        )
        print_response("Search LTM Rules", search_response)
        
        # 6. Search LTM Rules (Semantic)
        print("\n6. Searching LTM Rules (Semantic)")
        semantic_response = api.search_ltm_rules(
            query="consent requirements for data processing",
            limit=5
        )
        print_response("Semantic Search", semantic_response)
        
        # 7. Get LTM Rule
        print("\n7. Getting Specific LTM Rule")
        rule_response = api.get_ltm_rule("GDPR_Consent_Separate_01")
        print_response("Get LTM Rule", rule_response)
        
        # 8. Get Rules by Concept
        print("\n8. Getting Rules by Concept")
        concept_response = api.get_rules_by_concept("Consent")
        print_response("Rules by Concept", concept_response)
        
        # 9. Get Traceability Chain
        print("\n9. Getting Traceability Chain")
        trace_response = api.get_traceability_chain("ecommerce_r1_consent")
        print_response("Traceability Chain", trace_response)
        
        # 10. Get Rule Audit Trail
        print("\n10. Getting Rule Audit Trail")
        audit_response = api.get_rule_audit_trail("GDPR_Consent_Separate_01")
        print_response("Rule Audit Trail", audit_response)
        
        # 11. List STM Entries
        print("\n11. Listing STM Entries")
        list_response = api.list_stm_entries(limit=10)
        print_response("List STM Entries", list_response)
        
        # 12. Get STM Statistics
        print("\n12. STM Statistics")
        stm_stats_response = api.get_stm_stats()
        print_response("STM Stats", stm_stats_response)
        
        # 13. Get System Statistics
        print("\n13. System Statistics")
        stats_response = api.get_system_stats()
        print_response("System Stats", stats_response)
        
        # 14. Error Handling Demo
        print("\n14. Error Handling Demo")
        error_response = api.get_stm_entry("invalid_format")
        print_response("Error Handling", error_response)
        
        print("\n" + "="*50)
        print("Demo completed successfully!")
        print("="*50)
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up connections
        try:
            api.close()
        except:
            pass


def demo_api_features():
    """Demonstrate specific API features."""
    print("\n\nAPI Features Demo")
    print("=================")
    
    # Create mocked processors
    mock_stm = create_mock_stm_processor()
    mock_ltm = create_mock_ltm_manager()
    api = MemoryAPI(stm_processor=mock_stm, ltm_manager=mock_ltm)
    
    # Demonstrate validation
    print("\n1. Input Validation")
    
    # Valid scenario ID
    try:
        api._validate_scenario_id("ecommerce_r1_consent")
        print("✓ Valid scenario ID accepted")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    # Invalid scenario ID
    try:
        api._validate_scenario_id("invalid")
        print("✗ Invalid scenario ID should have been rejected")
    except Exception as e:
        print(f"✓ Invalid scenario ID correctly rejected: {e}")
    
    # Demonstrate response formatting
    print("\n2. Response Formatting")
    
    success_response = api._format_success_response(
        {"test": "data"}, 
        "Test successful"
    )
    print("Success Response Format:")
    print(json.dumps(success_response, indent=2))
    
    error_response = api._format_error_response(
        "Test error", 
        "test_error", 
        {"detail": "Additional info"}
    )
    print("\nError Response Format:")
    print(json.dumps(error_response, indent=2))
    
    # Demonstrate assessment data validation
    print("\n3. Assessment Data Validation")
    
    valid_assessment = {
        "scenario_id": "ecommerce_r1_consent",
        "requirement_text": "Test requirement",
        "initial_assessment": {
            "status": "Compliant",
            "rationale": "Test rationale",
            "recommendation": "Test recommendation"
        }
    }
    
    try:
        api._validate_assessment_data(valid_assessment)
        print("✓ Valid assessment data accepted")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    invalid_assessment = {"scenario_id": "test"}
    
    try:
        api._validate_assessment_data(invalid_assessment)
        print("✗ Invalid assessment data should have been rejected")
    except Exception as e:
        print(f"✓ Invalid assessment data correctly rejected: {e}")
    
    api.close()


if __name__ == "__main__":
    demo_memory_api()
    demo_api_features()