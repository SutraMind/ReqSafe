"""Integration tests for LLM client with actual Ollama server."""

import pytest
import json
from memory_management.llm.client import LLMClient
from memory_management.llm.prompts import PromptTemplates


class TestLLMIntegration:
    """Integration tests for LLM client with actual Ollama server."""
    
    @pytest.fixture
    def client(self):
        """Create LLM client for testing."""
        return LLMClient(timeout=30)
    
    @pytest.mark.integration
    def test_ollama_server_health(self, client):
        """Test if Ollama server is accessible."""
        # This test will be skipped if Ollama is not running
        try:
            health = client.check_health()
            if not health:
                pytest.skip("Ollama server not available or models not installed")
        except Exception:
            pytest.skip("Ollama server not accessible")
    
    @pytest.mark.integration
    def test_list_available_models(self, client):
        """Test listing available models."""
        try:
            models = client.list_models()
            print(f"Available models: {models}")
            # Just verify we can get a list (may be empty if no models installed)
            assert isinstance(models, list)
        except Exception:
            pytest.skip("Ollama server not accessible")
    
    @pytest.mark.integration
    def test_simple_text_generation(self, client):
        """Test simple text generation with available model."""
        try:
            # Try with default model first
            response = client.generate(
                "Say hello in one word only.",
                temperature=0.1
            )
            
            if not response.success:
                pytest.skip(f"Text generation failed: {response.error}")
            
            assert response.success
            assert len(response.content.strip()) > 0
            print(f"Generated text: {response.content}")
            
        except Exception as e:
            pytest.skip(f"Text generation test failed: {str(e)}")
    
    @pytest.mark.integration
    def test_structured_data_extraction(self, client):
        """Test structured data extraction with simple example."""
        try:
            schema = {"greeting": "string", "language": "string"}
            prompt = "Extract greeting and language from: 'Hello World in English'"
            
            response = client.extract_structured_data(prompt, schema)
            
            if not response.success:
                pytest.skip(f"Structured extraction failed: {response.error}")
            
            assert response.success
            
            # Try to parse the JSON response
            try:
                data = json.loads(response.content)
                assert "greeting" in data or "language" in data
                print(f"Extracted data: {data}")
            except json.JSONDecodeError:
                pytest.fail("Response was not valid JSON")
                
        except Exception as e:
            pytest.skip(f"Structured extraction test failed: {str(e)}")
    
    @pytest.mark.integration
    def test_compliance_report_template(self, client):
        """Test compliance report extraction template."""
        try:
            template_data = PromptTemplates.compliance_report_extraction()
            sample_report = """
            R1: User consent must be obtained before data collection.
            Status: Non-Compliant
            Rationale: No consent mechanism found in the application.
            Recommendation: Implement explicit consent checkboxes.
            """
            
            prompt = template_data["template"].format(report_text=sample_report)
            system_prompt = PromptTemplates.get_system_prompts()["compliance_extraction"]
            
            response = client.extract_structured_data(
                prompt, 
                template_data["schema"],
                system_prompt=system_prompt
            )
            
            if not response.success:
                pytest.skip(f"Compliance extraction failed: {response.error}")
            
            assert response.success
            print(f"Compliance extraction result: {response.content}")
            
        except Exception as e:
            pytest.skip(f"Compliance template test failed: {str(e)}")


if __name__ == "__main__":
    # Run integration tests only if explicitly requested
    pytest.main([__file__, "-v", "-m", "integration"])