"""
Demo script for Memory API functionality.

Shows how to use the unified Memory API for STM and LTM operations.
"""

import json
from memory_management.api.memory_api import MemoryAPI
from memory_management.models.stm_entry import InitialAssessment
from memory_management.models.ltm_rule import LTMRule


def print_response(title: str, response: dict):
    """Pretty print API response."""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(json.dumps(response, indent=2))


def demo_memory_api():
    """Demonstrate Memory API functionality."""
    print("Memory API Demo")
    print("===============")
    
    # Note: This demo uses mock processors since we don't have Redis/Neo4j running
    # In a real environment, you would initialize with actual database connections
    
    try:
        # Initialize Memory API (will use default mock processors for demo)
        api = MemoryAPI()
        
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
        
        # 7. Get Traceability Chain
        print("\n7. Getting Traceability Chain")
        trace_response = api.get_traceability_chain("ecommerce_r1_consent")
        print_response("Traceability Chain", trace_response)
        
        # 8. List STM Entries
        print("\n8. Listing STM Entries")
        list_response = api.list_stm_entries(limit=10)
        print_response("List STM Entries", list_response)
        
        # 9. Get System Statistics
        print("\n9. System Statistics")
        stats_response = api.get_system_stats()
        print_response("System Stats", stats_response)
        
        # 10. Error Handling Demo
        print("\n10. Error Handling Demo")
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
    print("\nAPI Features Demo")
    print("=================")
    
    api = MemoryAPI()
    
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
    
    api.close()


if __name__ == "__main__":
    demo_memory_api()
    demo_api_features()