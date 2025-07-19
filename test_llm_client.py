"""Unit tests for LLM client functionality."""

import json
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from memory_management.llm.client import LLMClient, LLMResponse
from memory_management.llm.prompts import PromptTemplates


class TestLLMClient:
    """Test cases for LLMClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = LLMClient(
            base_url="http://localhost:11434",
            timeout=30,
            max_retries=2,
            retry_delay=0.5
        )
    
    def test_init_default_values(self):
        """Test LLMClient initialization with default values."""
        client = LLMClient()
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == 120
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert 'qwq:32b' in client.MODELS
        assert 'gemma3:27b' in client.MODELS
    
    def test_init_custom_values(self):
        """Test LLMClient initialization with custom values."""
        client = LLMClient(
            base_url="http://custom:8080/",
            timeout=60,
            max_retries=5,
            retry_delay=2.0
        )
        assert client.base_url == "http://custom:8080"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
    
    @patch('requests.Session.post')
    def test_make_request_success(self, mock_post):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "test response"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.client._make_request('api/generate', {'test': 'data'})
        
        assert result == {"response": "test response"}
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_make_request_timeout(self, mock_post):
        """Test API request timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(requests.exceptions.Timeout):
            self.client._make_request('api/generate', {'test': 'data'})
    
    @patch('requests.Session.post')
    def test_make_request_connection_error(self, mock_post):
        """Test API request connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        with pytest.raises(requests.exceptions.ConnectionError):
            self.client._make_request('api/generate', {'test': 'data'})
    
    @patch('requests.Session.post')
    def test_make_request_http_error(self, mock_post):
        """Test API request HTTP error handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            self.client._make_request('api/generate', {'test': 'data'})
    
    @patch.object(LLMClient, '_make_request')
    def test_generate_success(self, mock_request):
        """Test successful text generation."""
        mock_request.return_value = {
            "response": "Generated text response",
            "eval_count": 150
        }
        
        result = self.client.generate("Test prompt", model="qwq:32b")
        
        assert isinstance(result, LLMResponse)
        assert result.success is True
        assert result.content == "Generated text response"
        assert result.model == "qwq:32b"
        assert result.tokens_used == 150
        assert result.error is None
    
    @patch.object(LLMClient, '_make_request')
    def test_generate_with_system_prompt(self, mock_request):
        """Test text generation with system prompt."""
        mock_request.return_value = {"response": "System guided response"}
        
        result = self.client.generate(
            "Test prompt", 
            model="gemma3:27b",
            system_prompt="You are a helpful assistant"
        )
        
        assert result.success is True
        assert result.content == "System guided response"
        mock_request.assert_called_once()
        
        # Check that system prompt was included in the request
        call_args = mock_request.call_args
        assert call_args[0][1]['system'] == "You are a helpful assistant"
    
    def test_generate_invalid_model(self):
        """Test text generation with invalid model."""
        with pytest.raises(ValueError, match="Unsupported model"):
            self.client.generate("Test prompt", model="invalid_model")
    
    @patch.object(LLMClient, '_make_request')
    def test_generate_api_error(self, mock_request):
        """Test text generation with API error."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = self.client.generate("Test prompt")
        
        assert isinstance(result, LLMResponse)
        assert result.success is False
        assert result.content == ""
        assert "Connection failed" in result.error
    
    @patch.object(LLMClient, 'generate')
    def test_extract_structured_data_success(self, mock_generate):
        """Test successful structured data extraction."""
        mock_generate.return_value = LLMResponse(
            content='{"name": "John", "age": 30}',
            model="qwq:32b",
            success=True
        )
        
        schema = {"name": "string", "age": "number"}
        result = self.client.extract_structured_data(
            "Extract person info", 
            schema
        )
        
        assert result.success is True
        parsed_content = json.loads(result.content)
        assert parsed_content["name"] == "John"
        assert parsed_content["age"] == 30
    
    @patch.object(LLMClient, 'generate')
    def test_extract_structured_data_invalid_json(self, mock_generate):
        """Test structured data extraction with invalid JSON."""
        mock_generate.return_value = LLMResponse(
            content='Invalid JSON response',
            model="qwq:32b",
            success=True
        )
        
        schema = {"name": "string"}
        result = self.client.extract_structured_data(
            "Extract data", 
            schema
        )
        
        assert result.success is False
        assert "Invalid JSON response" in result.error
    
    @patch.object(LLMClient, 'generate')
    def test_extract_structured_data_generation_failed(self, mock_generate):
        """Test structured data extraction when generation fails."""
        mock_generate.return_value = LLMResponse(
            content="",
            model="qwq:32b",
            success=False,
            error="Generation failed"
        )
        
        schema = {"name": "string"}
        result = self.client.extract_structured_data(
            "Extract data", 
            schema
        )
        
        assert result.success is False
        assert result.error == "Generation failed"
    
    @patch('requests.Session.get')
    def test_check_health_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwq:32b"},
                {"name": "gemma3:27b"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.check_health()
        
        assert result is True
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags", 
            timeout=10
        )
    
    @patch('requests.Session.get')
    def test_check_health_missing_model(self, mock_get):
        """Test health check with missing required model."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwq:32b"}
                # Missing gemma3:27b
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.check_health()
        
        assert result is False
    
    @patch('requests.Session.get')
    def test_check_health_connection_error(self, mock_get):
        """Test health check with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        result = self.client.check_health()
        
        assert result is False
    
    @patch('requests.Session.get')
    def test_list_models_success(self, mock_get):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwq:32b"},
                {"name": "gemma3:27b"},
                {"name": "llama2:7b"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.list_models()
        
        assert result == ["qwq:32b", "gemma3:27b", "llama2:7b"]
    
    @patch('requests.Session.get')
    def test_list_models_error(self, mock_get):
        """Test model listing with error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        result = self.client.list_models()
        
        assert result == []


class TestPromptTemplates:
    """Test cases for PromptTemplates class."""
    
    def test_compliance_report_extraction(self):
        """Test compliance report extraction template."""
        template_data = PromptTemplates.compliance_report_extraction()
        
        assert "template" in template_data
        assert "schema" in template_data
        assert "requirements" in template_data["schema"]
        assert isinstance(template_data["schema"]["requirements"], list)
        
        # Check required fields in schema
        req_schema = template_data["schema"]["requirements"][0]
        required_fields = [
            "requirement_number", "requirement_text", 
            "status", "rationale", "recommendation"
        ]
        for field in required_fields:
            assert field in req_schema
    
    def test_human_feedback_extraction(self):
        """Test human feedback extraction template."""
        template_data = PromptTemplates.human_feedback_extraction()
        
        assert "template" in template_data
        assert "schema" in template_data
        assert "feedback_items" in template_data["schema"]
        
        # Check required fields in schema
        feedback_schema = template_data["schema"]["feedback_items"][0]
        required_fields = [
            "requirement_reference", "decision", 
            "rationale", "suggestion", "confidence"
        ]
        for field in required_fields:
            assert field in feedback_schema
    
    def test_scenario_id_generation(self):
        """Test scenario ID generation template."""
        template_data = PromptTemplates.scenario_id_generation()
        
        assert "template" in template_data
        assert "schema" in template_data
        
        # Check required fields in schema
        schema = template_data["schema"]
        required_fields = [
            "scenario_id", "domain", "requirement_number", 
            "key_concept", "explanation"
        ]
        for field in required_fields:
            assert field in schema
    
    def test_ltm_rule_generation(self):
        """Test LTM rule generation template."""
        template_data = PromptTemplates.ltm_rule_generation()
        
        assert "template" in template_data
        assert "schema" in template_data
        
        # Check required fields in schema
        schema = template_data["schema"]
        required_fields = [
            "rule_text", "related_concepts", "policy_area", 
            "confidence_score", "applicability"
        ]
        for field in required_fields:
            assert field in schema
    
    def test_concept_extraction(self):
        """Test concept extraction template."""
        template_data = PromptTemplates.concept_extraction()
        
        assert "template" in template_data
        assert "schema" in template_data
        assert "concepts" in template_data["schema"]
        
        # Check required fields in schema
        concept_schema = template_data["schema"]["concepts"][0]
        required_fields = ["term", "category", "relevance_score"]
        for field in required_fields:
            assert field in concept_schema
    
    def test_get_system_prompts(self):
        """Test system prompts retrieval."""
        system_prompts = PromptTemplates.get_system_prompts()
        
        expected_tasks = [
            "compliance_extraction", "feedback_analysis", 
            "id_generation", "rule_generation", "concept_extraction"
        ]
        
        for task in expected_tasks:
            assert task in system_prompts
            assert isinstance(system_prompts[task], str)
            assert len(system_prompts[task]) > 0


class TestLLMResponse:
    """Test cases for LLMResponse dataclass."""
    
    def test_llm_response_creation(self):
        """Test LLMResponse creation."""
        response = LLMResponse(
            content="Test content",
            model="qwq:32b",
            success=True,
            error=None,
            tokens_used=100
        )
        
        assert response.content == "Test content"
        assert response.model == "qwq:32b"
        assert response.success is True
        assert response.error is None
        assert response.tokens_used == 100
    
    def test_llm_response_with_error(self):
        """Test LLMResponse creation with error."""
        response = LLMResponse(
            content="",
            model="qwq:32b",
            success=False,
            error="Connection failed"
        )
        
        assert response.content == ""
        assert response.success is False
        assert response.error == "Connection failed"
        assert response.tokens_used is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])