#!/usr/bin/env python3
"""
Test script to verify the memory management data models work correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_management.models import STMEntry, LTMRule
from memory_management.models.stm_entry import InitialAssessment, HumanFeedback
from memory_management.utils import DataValidator, JSONSerializer


def test_stm_entry():
    """Test STM entry creation and validation."""
    print("Testing STM Entry...")
    
    # Create test data
    initial_assessment = InitialAssessment(
        status="Non-Compliant",
        rationale="Bundled consent violates GDPR Art. 7",
        recommendation="Implement separate, unticked opt-in checkboxes"
    )
    
    human_feedback = HumanFeedback(
        decision="No change",
        rationale="Agent's analysis is correct",
        suggestion="Implement separate, unticked opt-in checkboxes"
    )
    
    stm_entry = STMEntry(
        scenario_id="ecommerce_r1_consent",
        requirement_text="During account signup, the user must agree...",
        initial_assessment=initial_assessment,
        human_feedback=human_feedback,
        final_status="Non-Compliant"
    )
    
    # Test validation
    is_valid, errors = DataValidator.validate_stm_entry(stm_entry)
    print(f"STM Entry validation: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        print(f"Errors: {errors}")
    
    # Test serialization
    try:
        json_str = JSONSerializer.serialize_stm_entry(stm_entry)
        deserialized = JSONSerializer.deserialize_stm_entry(json_str)
        print("STM Entry serialization: PASS")
    except Exception as e:
        print(f"STM Entry serialization: FAIL - {e}")
    
    return is_valid


def test_ltm_rule():
    """Test LTM rule creation and validation."""
    print("\nTesting LTM Rule...")
    
    ltm_rule = LTMRule(
        rule_id="GDPR_Hashing_Salted_01",
        rule_text="For GDPR Article 32 compliance, password hashing must include a salt to be considered a state-of-the-art security measure.",
        related_concepts=[
            "Password Security",
            "Hashing",
            "GDPR Article 32",
            "Cryptography",
            "State-of-the-art"
        ],
        source_scenario_id=["ecommerce_r4_password_hashing"],
        confidence_score=0.95
    )
    
    # Test validation
    is_valid, errors = DataValidator.validate_ltm_rule(ltm_rule)
    print(f"LTM Rule validation: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        print(f"Errors: {errors}")
    
    # Test serialization
    try:
        json_str = JSONSerializer.serialize_ltm_rule(ltm_rule)
        deserialized = JSONSerializer.deserialize_ltm_rule(json_str)
        print("LTM Rule serialization: PASS")
    except Exception as e:
        print(f"LTM Rule serialization: FAIL - {e}")
    
    return is_valid


def main():
    """Run all tests."""
    print("Testing Memory Management Data Models")
    print("=" * 40)
    
    stm_valid = test_stm_entry()
    ltm_valid = test_ltm_rule()
    
    print("\n" + "=" * 40)
    print(f"Overall Result: {'PASS' if stm_valid and ltm_valid else 'FAIL'}")
    
    return stm_valid and ltm_valid


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)