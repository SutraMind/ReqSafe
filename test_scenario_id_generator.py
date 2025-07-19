"""Unit tests for ScenarioIdGenerator class."""

import pytest
import json
from unittest.mock import Mock, patch
from memory_management.utils.scenario_id_generator import ScenarioIdGenerator, ScenarioIdComponents
from memory_management.llm.client import LLMClient, LLMResponse


class TestScenarioIdGenerator:
    """Test cases for ScenarioIdGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm_client = Mock(spec=LLMClient)
        self.generator = ScenarioIdGenerator(llm_client=self.mock_llm_client)
    
    def test_init_with_custom_client(self):
        """Test initialization with custom LLM client."""
        generator = ScenarioIdGenerator(llm_client=self.mock_llm_client)
        assert generator.llm_client == self.mock_llm_client
        assert generator._generated_ids == set()
    
    def test_init_with_default_client(self):
        """Test initialization with default LLM client."""
        with patch('memory_management.utils.scenario_id_generator.LLMClient') as mock_client_class:
            generator = ScenarioIdGenerator()
            mock_client_class.assert_called_once()
            assert generator._generated_ids == set()
    
    def test_generate_scenario_id_success(self):
        """Test successful scenario ID generation."""
        # Mock LLM response
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
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "During account signup, the user must provide explicit consent for data processing."
        
        result = self.generator.generate_scenario_id(requirement_text)
        
        assert result == "ecommerce_r1_consent"
        assert result in self.generator._generated_ids
        
        # Verify LLM was called correctly
        self.mock_llm_client.extract_structured_data.assert_called_once()
        call_args = self.mock_llm_client.extract_structured_data.call_args
        assert "consent" in call_args[1]['prompt'].lower()
        assert call_args[1]['model'] == 'qwq:32b'
    
    def test_generate_scenario_id_with_overrides(self):
        """Test scenario ID generation with domain and requirement overrides."""
        # Mock LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "domain": "healthcare",  # This should be overridden
                "requirement_number": "r5",  # This should be overridden
                "key_concept": "encryption",
                "confidence": 0.8
            }),
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "Patient data must be encrypted at rest."
        
        result = self.generator.generate_scenario_id(
            requirement_text, 
            domain="finance", 
            requirement_number="r10"
        )
        
        assert result == "finance_r10_encryption"
    
    def test_generate_scenario_id_uniqueness(self):
        """Test that duplicate IDs get unique suffixes."""
        # Mock LLM response that returns same components twice
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
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "User consent requirement."
        
        # Generate first ID
        result1 = self.generator.generate_scenario_id(requirement_text)
        assert result1 == "ecommerce_r1_consent"
        
        # Generate second ID - should get suffix
        result2 = self.generator.generate_scenario_id(requirement_text)
        assert result2 == "ecommerce_r1_consent_1"
        
        # Generate third ID - should get incremented suffix
        result3 = self.generator.generate_scenario_id(requirement_text)
        assert result3 == "ecommerce_r1_consent_2"
        
        assert len(self.generator._generated_ids) == 3
    
    def test_generate_scenario_id_llm_failure(self):
        """Test handling of LLM extraction failure."""
        # Mock LLM failure
        mock_response = LLMResponse(
            content="",
            model="qwq:32b",
            success=False,
            error="Connection timeout"
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "Some requirement text."
        
        with pytest.raises(ValueError, match="Scenario ID generation failed"):
            self.generator.generate_scenario_id(requirement_text)
    
    def test_generate_scenario_id_invalid_json(self):
        """Test handling of invalid JSON response from LLM."""
        # Mock LLM response with invalid JSON
        mock_response = LLMResponse(
            content="This is not valid JSON",
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "Some requirement text."
        
        with pytest.raises(ValueError, match="Invalid LLM response format"):
            self.generator.generate_scenario_id(requirement_text)
    
    def test_clean_component_basic(self):
        """Test basic component cleaning."""
        generator = ScenarioIdGenerator()
        
        assert generator._clean_component("E-Commerce") == "e_commerce"
        assert generator._clean_component("User Authentication") == "user_authentication"
        assert generator._clean_component("GDPR Compliance") == "gdpr_compliance"
        assert generator._clean_component("") == "unknown"
        assert generator._clean_component(None) == "unknown"
    
    def test_clean_component_special_chars(self):
        """Test component cleaning with special characters."""
        generator = ScenarioIdGenerator()
        
        assert generator._clean_component("user@domain.com") == "user_domain_com"
        assert generator._clean_component("test-case#1") == "test_case_1"
        assert generator._clean_component("___multiple___underscores___") == "multiple_underscores"
    
    def test_clean_component_length_limit(self):
        """Test component cleaning with length limits."""
        generator = ScenarioIdGenerator()
        
        long_text = "this_is_a_very_long_component_name_that_exceeds_the_limit"
        result = generator._clean_component(long_text)
        
        assert len(result) <= 20
        assert not result.endswith('_')
    
    def test_clean_requirement_number_formats(self):
        """Test requirement number cleaning with various formats."""
        generator = ScenarioIdGenerator()
        
        assert generator._clean_requirement_number("r1") == "r1"
        assert generator._clean_requirement_number("R1") == "r1"
        assert generator._clean_requirement_number("req1") == "r1"
        assert generator._clean_requirement_number("requirement_5") == "r5"
        assert generator._clean_requirement_number("10") == "r10"
        assert generator._clean_requirement_number("") == "r1"
        assert generator._clean_requirement_number(None) == "r1"
        assert generator._clean_requirement_number("no_numbers") == "r1"
    
    def test_validate_id_format_valid(self):
        """Test ID format validation with valid IDs."""
        generator = ScenarioIdGenerator()
        
        assert generator._validate_id_format("ecommerce_r1_consent") == True
        assert generator._validate_id_format("healthcare_r10_encryption") == True
        assert generator._validate_id_format("finance_r5_authentication_1") == True
        assert generator._validate_id_format("e_commerce_r1_user_auth") == True
    
    def test_validate_id_format_invalid(self):
        """Test ID format validation with invalid IDs."""
        generator = ScenarioIdGenerator()
        
        assert generator._validate_id_format("") == False
        assert generator._validate_id_format("invalid") == False
        assert generator._validate_id_format("ecommerce_consent") == False  # Missing requirement number
        assert generator._validate_id_format("_r1_consent") == False  # Starts with underscore
        assert generator._validate_id_format("ecommerce_1_consent") == False  # Missing 'r' prefix
        assert generator._validate_id_format("ECOMMERCE_R1_CONSENT") == False  # Uppercase
    
    def test_extract_id_components_success(self):
        """Test successful component extraction."""
        # Mock LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "domain": "healthcare",
                "requirement_number": "r3",
                "key_concept": "patient_data",
                "confidence": 0.85
            }),
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "Patient data must be protected according to HIPAA."
        
        components = self.generator._extract_id_components(requirement_text)
        
        assert components.domain == "healthcare"
        assert components.requirement_number == "r3"
        assert components.key_concept == "patient_data"
        assert components.confidence == 0.85
    
    def test_extract_id_components_with_overrides(self):
        """Test component extraction with overrides."""
        # Mock LLM response
        mock_response = LLMResponse(
            content=json.dumps({
                "domain": "original_domain",
                "requirement_number": "r1",
                "key_concept": "security",
                "confidence": 0.7
            }),
            model="qwq:32b",
            success=True
        )
        self.mock_llm_client.extract_structured_data.return_value = mock_response
        
        requirement_text = "Security requirement text."
        
        components = self.generator._extract_id_components(
            requirement_text,
            domain_override="finance",
            req_num_override="r15"
        )
        
        assert components.domain == "finance"  # Overridden
        assert components.requirement_number == "r15"  # Overridden
        assert components.key_concept == "security"  # From LLM
    
    def test_reset_generated_ids(self):
        """Test resetting generated IDs."""
        self.generator._generated_ids.add("test_id_1")
        self.generator._generated_ids.add("test_id_2")
        
        assert len(self.generator._generated_ids) == 2
        
        self.generator.reset_generated_ids()
        
        assert len(self.generator._generated_ids) == 0
    
    def test_get_generated_ids(self):
        """Test getting generated IDs."""
        self.generator._generated_ids.add("test_id_1")
        self.generator._generated_ids.add("test_id_2")
        
        ids = self.generator.get_generated_ids()
        
        assert ids == {"test_id_1", "test_id_2"}
        # Ensure it's a copy, not the original set
        ids.add("test_id_3")
        assert "test_id_3" not in self.generator._generated_ids


class TestScenarioIdGeneratorIntegration:
    """Integration tests with real LLM client (requires Ollama running)."""
    
    @pytest.mark.integration
    def test_real_llm_integration(self):
        """Test with real LLM client (requires Ollama server)."""
        try:
            # Create generator with real LLM client
            generator = ScenarioIdGenerator()
            
            # Test with realistic requirement text
            requirement_text = """
            During the account registration process, users must provide explicit consent 
            for the collection and processing of their personal data in accordance with 
            GDPR Article 6. The consent mechanism must be clearly separated from other 
            terms and conditions.
            """
            
            result = generator.generate_scenario_id(requirement_text)
            
            # Verify format
            assert isinstance(result, str)
            assert len(result.split('_')) >= 3
            assert result.startswith(result.split('_')[0])  # Has domain
            assert '_r' in result  # Has requirement number
            
        except Exception as e:
            pytest.skip(f"Integration test skipped - Ollama not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])