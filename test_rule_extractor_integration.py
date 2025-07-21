"""
Integration test for RuleExtractor with sample data.

This test demonstrates the rule extraction functionality using
realistic compliance data similar to what would be processed
in the actual system.
"""

import pytest
from memory_management.processors.rule_extractor import RuleExtractor
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.llm.client import LLMClient


class TestRuleExtractorIntegration:
    """Integration tests for RuleExtractor with realistic data."""
    
    def setup_method(self):
        """Set up test fixtures with realistic compliance scenarios."""
        self.rule_extractor = RuleExtractor()
        
        # Sample STM entry based on GDPR consent requirements
        self.gdpr_consent_stm = STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="""During account signup, the user must agree to data processing. 
            The system currently uses a single checkbox that covers all data processing purposes 
            including marketing, analytics, and service provision.""",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="""Bundled consent violates GDPR Art. 7 which requires consent to be 
                specific and granular. A single checkbox covering multiple purposes does not 
                meet the requirement for informed consent.""",
                recommendation="""Implement separate, unticked opt-in checkboxes for each data 
                processing purpose. Ensure users can consent to service provision while 
                declining marketing and analytics."""
            ),
            human_feedback=HumanFeedback(
                decision="Accept",
                rationale="""Agent's analysis is correct. GDPR Article 7 explicitly states that 
                consent must be specific and granular. Bundled consent is a common violation 
                that regulators actively enforce against.""",
                suggestion="""Implement granular consent with separate checkboxes for: 
                1) Essential service provision (pre-checked as legitimate interest)
                2) Marketing communications (unchecked)
                3) Analytics and improvement (unchecked)
                Include clear explanations for each purpose."""
            ),
            final_status="Non-Compliant"
        )
        
        # Sample STM entry for password security
        self.password_security_stm = STMEntry(
            scenario_id="ecommerce_r4_password_hashing",
            requirement_text="""User passwords must be securely stored using appropriate 
            cryptographic measures as required by GDPR Article 32.""",
            initial_assessment=InitialAssessment(
                status="Non-Compliant", 
                rationale="""Passwords are hashed using SHA-256 without salt, which does not 
                meet state-of-the-art security requirements under GDPR Article 32.""",
                recommendation="""Implement bcrypt or Argon2 password hashing with individual 
                salts for each password to meet current security standards."""
            ),
            human_feedback=HumanFeedback(
                decision="Modify",
                rationale="""While the agent correctly identifies the security issue, the 
                recommendation should be more specific about current best practices.""",
                suggestion="""Use bcrypt with a work factor of at least 12, or Argon2id with 
                appropriate memory and iteration parameters. Each password must have a unique 
                salt generated using a cryptographically secure random number generator."""
            ),
            final_status="Non-Compliant"
        )
    
    @pytest.mark.skip(reason="Requires running Ollama server - enable for manual testing")
    def test_extract_rule_from_gdpr_consent_scenario(self):
        """Test rule extraction from GDPR consent scenario."""
        # This test requires a running Ollama server with qwq:32b model
        result = self.rule_extractor.extract_rule_from_stm(self.gdpr_consent_stm)
        
        if result.success:
            rule = result.rule
            print(f"\nGenerated Rule ID: {rule.rule_id}")
            print(f"Rule Text: {rule.rule_text}")
            print(f"Related Concepts: {rule.related_concepts}")
            print(f"Confidence Score: {rule.confidence_score}")
            
            # Verify rule quality
            assert rule.validate()
            assert "consent" in rule.rule_text.lower()
            assert "granular" in rule.rule_text.lower() or "specific" in rule.rule_text.lower()
            assert len(rule.related_concepts) >= 3
            assert rule.confidence_score > 0.5
        else:
            print(f"Rule extraction failed: {result.error}")
            # Don't fail the test if LLM is not available
            pytest.skip("LLM not available for rule generation")
    
    @pytest.mark.skip(reason="Requires running Ollama server - enable for manual testing")
    def test_extract_rule_from_password_security_scenario(self):
        """Test rule extraction from password security scenario."""
        result = self.rule_extractor.extract_rule_from_stm(self.password_security_stm)
        
        if result.success:
            rule = result.rule
            print(f"\nGenerated Rule ID: {rule.rule_id}")
            print(f"Rule Text: {rule.rule_text}")
            print(f"Related Concepts: {rule.related_concepts}")
            print(f"Confidence Score: {rule.confidence_score}")
            
            # Verify rule quality
            assert rule.validate()
            assert "password" in rule.rule_text.lower()
            assert "hash" in rule.rule_text.lower() or "crypt" in rule.rule_text.lower()
            assert "salt" in rule.rule_text.lower()
            assert len(rule.related_concepts) >= 3
            assert rule.confidence_score > 0.5
        else:
            print(f"Rule extraction failed: {result.error}")
            pytest.skip("LLM not available for rule generation")
    
    @pytest.mark.skip(reason="Requires running Ollama server - enable for manual testing")
    def test_concept_extraction_from_compliance_text(self):
        """Test concept extraction from compliance-related text."""
        compliance_text = """
        GDPR Article 32 requires that personal data processing systems implement 
        appropriate technical and organizational measures to ensure a level of 
        security appropriate to the risk. This includes pseudonymization, encryption, 
        confidentiality, integrity, availability, and resilience of processing systems.
        """
        
        concepts = self.rule_extractor.extract_concepts_from_text(compliance_text)
        
        if concepts:
            print(f"\nExtracted concepts: {concepts}")
            
            # Verify concept quality
            assert len(concepts) > 0
            expected_concepts = ["GDPR", "Article 32", "encryption", "security", "personal data"]
            found_concepts = [c.lower() for c in concepts]
            
            # Check that at least some expected concepts are found
            matches = sum(1 for expected in expected_concepts 
                         if any(expected.lower() in found.lower() for found in found_concepts))
            assert matches >= 2
        else:
            pytest.skip("LLM not available for concept extraction")
    
    def test_rule_quality_validation_comprehensive(self):
        """Test comprehensive rule quality validation."""
        # Test with a well-formed rule
        good_rule_data = {
            "rule_text": """For GDPR Article 7 compliance, consent must be granular and specific 
            for each data processing purpose. Bundled consent that covers multiple purposes 
            in a single checkbox is not acceptable and violates the requirement for informed consent.""",
            "related_concepts": ["GDPR Article 7", "Consent", "Data Processing", "Granular Consent", "User Rights"],
            "policy_area": "GDPR",
            "confidence_score": 0.9
        }
        
        rule = self.rule_extractor._create_ltm_rule(self.gdpr_consent_stm, good_rule_data)
        validation = self.rule_extractor.validate_rule_quality(rule)
        
        assert validation["is_valid"] is True
        assert validation["quality_score"] > 0.7
        assert len(validation["issues"]) == 0
        
        # Test with a poor quality rule
        poor_rule_data = {
            "rule_text": "Use good consent",  # Too short and vague
            "related_concepts": ["consent"],  # Too few concepts
            "policy_area": "GDPR",
            "confidence_score": 0.2  # Low confidence
        }
        
        poor_rule = self.rule_extractor._create_ltm_rule(self.gdpr_consent_stm, poor_rule_data)
        poor_validation = self.rule_extractor.validate_rule_quality(poor_rule)
        
        assert poor_validation["is_valid"] is False
        assert poor_validation["quality_score"] < 0.5
        assert len(poor_validation["issues"]) > 0
    
    def test_multiple_rule_generation_workflow(self):
        """Test the workflow for generating multiple rules from STM entries."""
        stm_entries = [self.gdpr_consent_stm, self.password_security_stm]
        
        # Mock the LLM calls to test the workflow without requiring Ollama
        from unittest.mock import Mock, patch
        import json
        
        mock_responses = [
            {
                "rule_text": "GDPR consent must be granular and specific for each processing purpose",
                "related_concepts": ["GDPR", "Consent", "Data Processing"],
                "policy_area": "GDPR",
                "confidence_score": 0.9
            },
            {
                "rule_text": "Password hashing must use salt and appropriate algorithms like bcrypt",
                "related_concepts": ["Password Security", "Hashing", "Cryptography"],
                "policy_area": "GDPR",
                "confidence_score": 0.85
            }
        ]
        
        with patch.object(self.rule_extractor, '_generate_rule_with_llm') as mock_llm:
            mock_llm.side_effect = mock_responses
            
            results = self.rule_extractor.generate_multiple_rules(stm_entries)
            
            assert len(results) == 2
            assert all(result.success for result in results)
            assert all(result.rule is not None for result in results)
            assert all(result.rule.validate() for result in results)
            
            # Verify rule IDs are different
            rule_ids = [result.rule.rule_id for result in results]
            assert len(set(rule_ids)) == 2  # All unique


if __name__ == "__main__":
    # Run with: python test_rule_extractor_integration.py
    # To enable LLM tests, remove the @pytest.mark.skip decorators
    pytest.main([__file__, "-v", "-s"])