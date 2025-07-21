"""
Unit tests for RuleExtractor class.

Tests the LLM-based rule generation functionality for creating
Long-Term Memory rules from human expert feedback.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from memory_management.processors.rule_extractor import RuleExtractor, RuleGenerationResult
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule
from memory_management.llm.client import LLMClient, LLMResponse


class TestRuleExtractor:
    """Test cases for RuleExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock LLM client
        self.mock_llm_client = Mock(spec=LLMClient)
        self.rule_extractor = RuleExtractor(llm_client=self.mock_llm_client)
        
        # Sample STM entry with human feedback
        self.sample_stm_entry = STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="During account signup, the user must agree to data processing",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="Bundled consent violates GDPR Art. 7",
                recommendation="Implement separate opt-in checkboxes"
            ),
            human_feedback=HumanFeedback(
                decision="Accept",
                rationale="Agent's analysis is correct. Bundled consent is indeed problematic.",
                suggestion="Implement granular consent with separate checkboxes for each purpose"
            ),
            final_status="Non-Compliant"
        )
        
        # Sample LLM response for rule generation
        self.sample_rule_response = {
            "rule_text": "For GDPR Article 7 compliance, consent must be granular and specific for each data processing purpose. Bundled consent that covers multiple purposes in a single checkbox is not acceptable.",
            "related_concepts": [
                "GDPR Article 7",
                "Consent",
                "Data Processing",
                "Granular Consent",
                "User Rights"
            ],
            "policy_area": "GDPR",
            "confidence_score": 0.9,
            "applicability": "Applies to all data collection scenarios requiring user consent"
        }
    
    def test_extract_rule_from_stm_success(self):
        """Test successful rule extraction from STM entry."""
        # Mock successful LLM response
        mock_response = LLMResponse(
            content=json.dumps(self.sample_rule_response),
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Extract rule
        result = self.rule_extractor.extract_rule_from_stm(self.sample_stm_entry)
        
        # Verify result
        assert result.success is True
        assert result.rule is not None
        assert result.error is None
        assert result.confidence_score == 0.9
        
        # Verify rule properties
        rule = result.rule
        assert rule.rule_text == self.sample_rule_response["rule_text"]
        assert rule.related_concepts == self.sample_rule_response["related_concepts"]
        assert rule.source_scenario_id == ["ecommerce_r1_consent"]
        assert rule.confidence_score == 0.9
        assert rule.rule_id.startswith("GDPR_gdpr_article_7")
    
    def test_extract_rule_no_human_feedback(self):
        """Test rule extraction fails when STM entry has no human feedback."""
        # Create STM entry without human feedback
        stm_entry = STMEntry(
            scenario_id="test_scenario",
            requirement_text="Test requirement",
            initial_assessment=InitialAssessment(
                status="Compliant",
                rationale="Test rationale",
                recommendation="Test recommendation"
            )
        )
        
        # Extract rule
        result = self.rule_extractor.extract_rule_from_stm(stm_entry)
        
        # Verify failure
        assert result.success is False
        assert result.rule is None
        assert "human feedback" in result.error.lower()
    
    def test_extract_rule_llm_failure(self):
        """Test rule extraction handles LLM failure gracefully."""
        # Mock failed LLM response
        mock_response = LLMResponse(
            content="",
            model="qwq:32b",
            success=False,
            error="Connection timeout"
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Extract rule
        result = self.rule_extractor.extract_rule_from_stm(self.sample_stm_entry)
        
        # Verify failure handling
        assert result.success is False
        assert result.rule is None
        assert "Failed to generate rule data" in result.error
    
    def test_extract_rule_invalid_json(self):
        """Test rule extraction handles invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = LLMResponse(
            content="Invalid JSON content",
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Extract rule
        result = self.rule_extractor.extract_rule_from_stm(self.sample_stm_entry)
        
        # Verify failure handling
        assert result.success is False
        assert result.rule is None
        assert "Failed to generate rule data" in result.error
    
    def test_extract_concepts_from_text_success(self):
        """Test successful concept extraction from text."""
        # Sample concept extraction response
        concept_response = {
            "concepts": [
                {"term": "GDPR", "category": "Legal", "relevance_score": 0.9},
                {"term": "Consent", "category": "Legal", "relevance_score": 0.8},
                {"term": "Data Processing", "category": "Technical", "relevance_score": 0.7}
            ]
        }
        
        # Mock successful LLM response
        mock_response = LLMResponse(
            content=json.dumps(concept_response),
            model="gemma3:27b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Extract concepts
        concepts = self.rule_extractor.extract_concepts_from_text(
            "GDPR requires explicit consent for data processing"
        )
        
        # Verify results
        assert len(concepts) == 3
        assert "GDPR" in concepts
        assert "Consent" in concepts
        assert "Data Processing" in concepts
    
    def test_extract_concepts_llm_failure(self):
        """Test concept extraction handles LLM failure gracefully."""
        # Mock failed LLM response
        mock_response = LLMResponse(
            content="",
            model="gemma3:27b",
            success=False,
            error="Model not available"
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Extract concepts
        concepts = self.rule_extractor.extract_concepts_from_text("Test text")
        
        # Verify empty result
        assert concepts == []
    
    def test_generate_multiple_rules(self):
        """Test generating rules from multiple STM entries."""
        # Create multiple STM entries
        stm_entries = [
            self.sample_stm_entry,
            STMEntry(
                scenario_id="ecommerce_r2_encryption",
                requirement_text="User passwords must be encrypted",
                initial_assessment=InitialAssessment(
                    status="Non-Compliant",
                    rationale="Passwords are stored in plain text",
                    recommendation="Implement bcrypt hashing"
                ),
                human_feedback=HumanFeedback(
                    decision="Accept",
                    rationale="Plain text passwords are a security risk",
                    suggestion="Use bcrypt with salt for password hashing"
                )
            )
        ]
        
        # Mock successful LLM responses
        mock_response = LLMResponse(
            content=json.dumps(self.sample_rule_response),
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        # Generate rules
        results = self.rule_extractor.generate_multiple_rules(stm_entries)
        
        # Verify results
        assert len(results) == 2
        assert all(result.success for result in results)
        assert all(result.rule is not None for result in results)
    
    def test_validate_rule_quality_good_rule(self):
        """Test rule quality validation for a good rule."""
        rule = LTMRule(
            rule_id="GDPR_consent_01",
            rule_text="For GDPR compliance, consent must be freely given, specific, informed, and unambiguous. Users must be able to withdraw consent easily.",
            related_concepts=["GDPR", "Consent", "User Rights", "Data Protection"],
            source_scenario_id=["test_scenario"],
            confidence_score=0.9
        )
        
        validation = self.rule_extractor.validate_rule_quality(rule)
        
        assert validation["is_valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["quality_score"] > 0.7
    
    def test_validate_rule_quality_poor_rule(self):
        """Test rule quality validation for a poor rule."""
        rule = LTMRule(
            rule_id="test_rule_01",
            rule_text="Short rule",  # Too short
            related_concepts=["concept1"],  # Too few concepts
            source_scenario_id=["test_scenario"],
            confidence_score=0.3  # Low confidence
        )
        
        validation = self.rule_extractor.validate_rule_quality(rule)
        
        assert validation["is_valid"] is False
        assert len(validation["issues"]) >= 2
        assert "too short" in validation["issues"][0].lower()
        assert validation["quality_score"] < 0.5
    
    def test_extract_key_concept(self):
        """Test key concept extraction for rule ID generation."""
        concepts = ["GDPR Article 7", "Data Processing", "User Consent"]
        key_concept = self.rule_extractor._extract_key_concept(concepts)
        
        assert key_concept == "gdpr_article_7"
        assert len(key_concept) <= 20
        assert "_" in key_concept or key_concept.isalnum()
    
    def test_extract_key_concept_empty_list(self):
        """Test key concept extraction with empty concept list."""
        key_concept = self.rule_extractor._extract_key_concept([])
        assert key_concept == "general"
    
    def test_format_initial_assessment(self):
        """Test formatting of initial assessment for LLM prompt."""
        assessment = InitialAssessment(
            status="Non-Compliant",
            rationale="Test rationale",
            recommendation="Test recommendation"
        )
        
        formatted = self.rule_extractor._format_initial_assessment(assessment)
        
        assert "Status: Non-Compliant" in formatted
        assert "Rationale: Test rationale" in formatted
        assert "Recommendation: Test recommendation" in formatted
    
    def test_format_human_feedback(self):
        """Test formatting of human feedback for LLM prompt."""
        feedback = HumanFeedback(
            decision="Accept",
            rationale="Test rationale",
            suggestion="Test suggestion"
        )
        
        formatted = self.rule_extractor._format_human_feedback(feedback)
        
        assert "Decision: Accept" in formatted
        assert "Rationale: Test rationale" in formatted
        assert "Suggestion: Test suggestion" in formatted
    
    def test_create_ltm_rule(self):
        """Test LTM rule creation from STM entry and rule data."""
        rule = self.rule_extractor._create_ltm_rule(
            self.sample_stm_entry,
            self.sample_rule_response
        )
        
        assert rule.rule_text == self.sample_rule_response["rule_text"]
        assert rule.related_concepts == self.sample_rule_response["related_concepts"]
        assert rule.source_scenario_id == ["ecommerce_r1_consent"]
        assert rule.confidence_score == 0.9
        assert rule.rule_id.startswith("GDPR_")
        assert rule.version == 1


class TestRuleGenerationResult:
    """Test cases for RuleGenerationResult dataclass."""
    
    def test_successful_result(self):
        """Test creating a successful rule generation result."""
        rule = LTMRule(
            rule_id="test_rule_01",
            rule_text="Test rule text",
            related_concepts=["concept1", "concept2"],
            source_scenario_id=["scenario1"]
        )
        
        result = RuleGenerationResult(
            success=True,
            rule=rule,
            confidence_score=0.8
        )
        
        assert result.success is True
        assert result.rule == rule
        assert result.error is None
        assert result.confidence_score == 0.8
    
    def test_failed_result(self):
        """Test creating a failed rule generation result."""
        result = RuleGenerationResult(
            success=False,
            error="Test error message"
        )
        
        assert result.success is False
        assert result.rule is None
        assert result.error == "Test error message"
        assert result.confidence_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__])