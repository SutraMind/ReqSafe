"""Test LLM response parsing with <think> blocks."""

import json
import logging
from memory_management.llm.client import LLMClient, LLMResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_clean_llm_response():
    """Test the _clean_llm_response method."""
    client = LLMClient()
    
    # Test with <think> blocks
    test_input = """
<think>
Let me analyze this compliance report carefully.
I need to extract all the requirements with their status.
</think>

{
  "requirements": [
    {
      "requirement_number": "R1",
      "requirement_text": "Test requirement",
      "status": "Non-Compliant",
      "rationale": "Test rationale",
      "recommendation": "Test recommendation"
    }
  ]
}
"""
    
    cleaned = client._clean_llm_response(test_input)
    print("\nCleaned output:")
    print(cleaned)
    
    # Try parsing the cleaned output
    try:
        parsed = json.loads(cleaned)
        print("\n✅ Successfully parsed JSON")
        print(f"Found {len(parsed.get('requirements', []))} requirements")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON parsing failed: {e}")
    
    # Test with other artifacts
    test_input_2 = """
Response: 
<reasoning>
This looks like a compliance report with several requirements.
I'll extract them into a structured format.
</reasoning>

{
  "requirements": [
    {
      "requirement_number": "R1",
      "requirement_text": "Test requirement",
      "status": "Non-Compliant",
      "rationale": "Test rationale",
      "recommendation": "Test recommendation"
    }
  ]
}
"""
    
    cleaned_2 = client._clean_llm_response(test_input_2)
    print("\nCleaned output (second test):")
    print(cleaned_2)
    
    # Try parsing the second cleaned output
    try:
        parsed_2 = json.loads(cleaned_2)
        print("\n✅ Successfully parsed JSON (second test)")
        print(f"Found {len(parsed_2.get('requirements', []))} requirements")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON parsing failed (second test): {e}")


def test_extract_structured_data():
    """Test the extract_structured_data method with mock response."""
    client = LLMClient()
    
    # Create a mock response with <think> blocks
    mock_response = """
<think>
Let me analyze this compliance report carefully.
I need to extract all the requirements with their status.
</think>

{
  "requirements": [
    {
      "requirement_number": "R1",
      "requirement_text": "Test requirement",
      "status": "Non-Compliant",
      "rationale": "Test rationale",
      "recommendation": "Test recommendation"
    }
  ]
}
"""
    
    # Monkey patch the generate method to return our mock response
    original_generate = client.generate
    client.generate = lambda **kwargs: LLMResponse(
        content=mock_response,
        model='test-model',
        success=True
    )
    
    try:
        # Test the extract_structured_data method
        result = client.extract_structured_data(
            prompt="Test prompt",
            expected_schema={"requirements": "array"},
            model="test-model"
        )
        
        print("\nExtract structured data result:")
        print(f"Success: {result.success}")
        
        if result.success:
            parsed = json.loads(result.content)
            print(f"Requirements found: {len(parsed.get('requirements', []))}")
            print("Content:")
            print(result.content)
        else:
            print(f"Error: {result.error}")
            
    finally:
        # Restore original method
        client.generate = original_generate


if __name__ == "__main__":
    print("Testing LLM response cleaning...")
    test_clean_llm_response()
    
    print("\n" + "-"*50)
    print("Testing structured data extraction...")
    test_extract_structured_data()