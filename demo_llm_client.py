"""Demonstration script for LLM client functionality."""

import json
from memory_management.llm.client import LLMClient
from memory_management.llm.prompts import PromptTemplates


def demo_llm_client():
    """Demonstrate LLM client capabilities."""
    print("=== LLM Client Demonstration ===\n")
    
    # Initialize client
    client = LLMClient()
    print("1. Initialized LLM Client")
    
    # Check server health
    print("\n2. Checking Ollama server health...")
    try:
        health = client.check_health()
        if health:
            print("✓ Ollama server is healthy and models are available")
        else:
            print("✗ Ollama server issues or missing models")
            print("Note: Make sure Ollama is running and qwq:32b, gemma3:27b models are installed")
            return
    except Exception as e:
        print(f"✗ Cannot connect to Ollama server: {e}")
        print("Note: Make sure Ollama is running on localhost:11434")
        return
    
    # List available models
    print("\n3. Available models:")
    models = client.list_models()
    for model in models:
        print(f"   - {model}")
    
    # Test simple text generation
    print("\n4. Testing simple text generation...")
    try:
        response = client.generate(
            "Explain GDPR compliance in one sentence.",
            model="qwq:32b",
            temperature=0.1
        )
        if response.success:
            print(f"✓ Generated: {response.content}")
            print(f"   Tokens used: {response.tokens_used}")
        else:
            print(f"✗ Generation failed: {response.error}")
    except Exception as e:
        print(f"✗ Error during generation: {e}")
    
    # Test structured data extraction
    print("\n5. Testing structured data extraction...")
    try:
        schema = {
            "requirement": "string",
            "status": "string",
            "recommendation": "string"
        }
        
        prompt = """
        Extract information from this compliance text:
        "R1: Data encryption is required. Status: Non-Compliant. 
        Recommendation: Implement AES-256 encryption for all sensitive data."
        """
        
        response = client.extract_structured_data(prompt, schema)
        if response.success:
            print("✓ Structured extraction successful:")
            data = json.loads(response.content)
            for key, value in data.items():
                print(f"   {key}: {value}")
        else:
            print(f"✗ Structured extraction failed: {response.error}")
    except Exception as e:
        print(f"✗ Error during structured extraction: {e}")
    
    # Test compliance report template
    print("\n6. Testing compliance report template...")
    try:
        template_data = PromptTemplates.compliance_report_extraction()
        sample_report = """
        R1: User consent must be obtained before processing personal data.
        Status: Non-Compliant
        Rationale: The application collects email addresses without explicit consent checkboxes.
        Recommendation: Add separate, unticked consent checkboxes for each data processing purpose.
        
        R2: Data must be encrypted in transit and at rest.
        Status: Partially Compliant
        Rationale: HTTPS is used but database encryption is not implemented.
        Recommendation: Enable database encryption using AES-256.
        """
        
        prompt = template_data["template"].format(report_text=sample_report)
        system_prompt = PromptTemplates.get_system_prompts()["compliance_extraction"]
        
        response = client.extract_structured_data(
            prompt,
            template_data["schema"],
            system_prompt=system_prompt
        )
        
        if response.success:
            print("✓ Compliance report extraction successful:")
            data = json.loads(response.content)
            for i, req in enumerate(data.get("requirements", []), 1):
                print(f"   Requirement {i}:")
                print(f"     Number: {req.get('requirement_number', 'N/A')}")
                print(f"     Status: {req.get('status', 'N/A')}")
                print(f"     Rationale: {req.get('rationale', 'N/A')[:50]}...")
        else:
            print(f"✗ Compliance extraction failed: {response.error}")
    except Exception as e:
        print(f"✗ Error during compliance extraction: {e}")
    
    print("\n=== Demonstration Complete ===")


if __name__ == "__main__":
    demo_llm_client()