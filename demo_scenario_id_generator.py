"""Demo script for ScenarioIdGenerator functionality."""

import json
from unittest.mock import Mock
from memory_management.utils.scenario_id_generator import ScenarioIdGenerator, ScenarioIdComponents
from memory_management.llm.client import LLMClient, LLMResponse


def demo_scenario_id_generation():
    """Demonstrate scenario ID generation with mock LLM responses."""
    print("=== Scenario ID Generator Demo ===\n")
    
    # Create a mock LLM client for demonstration
    mock_llm_client = Mock(spec=LLMClient)
    generator = ScenarioIdGenerator(llm_client=mock_llm_client)
    
    # Test cases with different requirement texts
    test_cases = [
        {
            "text": "During account signup, the user must provide explicit consent for data processing.",
            "mock_response": {
                "domain": "ecommerce",
                "requirement_number": "r1",
                "key_concept": "consent",
                "confidence": 0.9
            }
        },
        {
            "text": "Patient data must be encrypted at rest using AES-256 encryption.",
            "mock_response": {
                "domain": "healthcare",
                "requirement_number": "r3",
                "key_concept": "encryption",
                "confidence": 0.85
            }
        },
        {
            "text": "Financial transactions must be authenticated using two-factor authentication.",
            "mock_response": {
                "domain": "finance",
                "requirement_number": "r5",
                "key_concept": "authentication",
                "confidence": 0.8
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print(f"Requirement: {test_case['text']}")
        
        # Mock the LLM response
        mock_response = LLMResponse(
            content=json.dumps(test_case['mock_response']),
            model="qwq:32b",
            success=True
        )
        mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Generate scenario ID
        scenario_id = generator.generate_scenario_id(test_case['text'])
        print(f"Generated ID: {scenario_id}")
        print()
    
    # Demonstrate uniqueness handling
    print("=== Uniqueness Demo ===")
    print("Generating duplicate IDs to show uniqueness handling...")
    
    # Use the same mock response multiple times
    mock_response = LLMResponse(
        content=json.dumps({
            "domain": "ecommerce",
            "requirement_number": "r1",
            "key_concept": "consent",
            "confidence": 0.9
        }),
        model="qwq:32b",
        success=True
    )
    mock_llm_client.extract_structured_data.return_value = mock_response
    
    for i in range(3):
        scenario_id = generator.generate_scenario_id("User consent requirement.")
        print(f"Attempt {i+1}: {scenario_id}")
    
    print()
    
    # Demonstrate domain and requirement number overrides
    print("=== Override Demo ===")
    print("Using domain and requirement number overrides...")
    
    scenario_id = generator.generate_scenario_id(
        "Data must be protected according to regulations.",
        domain="banking",
        requirement_number="r10"
    )
    print(f"With overrides: {scenario_id}")
    print()
    
    # Show all generated IDs
    print("=== All Generated IDs ===")
    all_ids = generator.get_generated_ids()
    for scenario_id in sorted(all_ids):
        print(f"- {scenario_id}")
    
    print(f"\nTotal unique IDs generated: {len(all_ids)}")


def demo_component_cleaning():
    """Demonstrate component cleaning functionality."""
    print("\n=== Component Cleaning Demo ===\n")
    
    generator = ScenarioIdGenerator()
    
    # Test component cleaning
    test_components = [
        "E-Commerce Platform",
        "User Authentication & Authorization",
        "GDPR Compliance!!!",
        "test@domain.com",
        "Multi-Factor Authentication",
        "___special___chars___",
        "this_is_a_very_long_component_name_that_exceeds_the_twenty_character_limit"
    ]
    
    print("Component cleaning examples:")
    for component in test_components:
        cleaned = generator._clean_component(component)
        print(f"'{component}' -> '{cleaned}'")
    
    print("\nRequirement number cleaning examples:")
    test_req_nums = ["r1", "R5", "req10", "requirement_3", "15", "", "no_numbers"]
    
    for req_num in test_req_nums:
        cleaned = generator._clean_requirement_number(req_num)
        print(f"'{req_num}' -> '{cleaned}'")


def demo_id_validation():
    """Demonstrate ID format validation."""
    print("\n=== ID Validation Demo ===\n")
    
    generator = ScenarioIdGenerator()
    
    # Test valid and invalid IDs
    test_ids = [
        "ecommerce_r1_consent",           # Valid
        "healthcare_r10_encryption",      # Valid
        "finance_r5_authentication_1",    # Valid with suffix
        "e_commerce_r1_user_auth",        # Valid with underscores
        "",                               # Invalid - empty
        "invalid",                        # Invalid - wrong format
        "ecommerce_consent",              # Invalid - missing requirement number
        "_r1_consent",                    # Invalid - starts with underscore
        "ecommerce_1_consent",            # Invalid - missing 'r' prefix
        "ECOMMERCE_R1_CONSENT"            # Invalid - uppercase
    ]
    
    print("ID format validation examples:")
    for test_id in test_ids:
        is_valid = generator._validate_id_format(test_id)
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"'{test_id}' -> {status}")


if __name__ == "__main__":
    demo_scenario_id_generation()
    demo_component_cleaning()
    demo_id_validation()