"""Comprehensive test of the compliance memory management system."""

import json
import logging
from memory_management.parsers.compliance_report_parser import ComplianceReportParser
from memory_management.llm.client import LLMClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_llm_client():
    """Test the LLM client basic functionality."""
    print("=== Testing LLM Client ===")
    
    try:
        client = LLMClient()
        print("✓ LLM Client initialized")
        
        # Test health check
        health = client.check_health()
        print(f"Health check: {'✓ Healthy' if health else '✗ Unhealthy'}")
        
        # List available models
        models = client.list_models()
        print(f"Available models: {models}")
        
        return client, health
        
    except Exception as e:
        print(f"✗ LLM Client error: {e}")
        return None, False


def test_compliance_parser_basic():
    """Test the compliance parser with basic functionality."""
    print("\n=== Testing Compliance Parser (Basic) ===")
    
    try:
        # Test without LLM first
        parser = ComplianceReportParser()
        print("✓ Parser initialized")
        
        # Test with empty input
        result = parser.parse_report_text("")
        print(f"Empty input test: {'✓ Handled correctly' if not result.parsing_success else '✗ Should fail'}")
        
        # Test file not found
        result = parser.parse_report_file("nonexistent.txt")
        print(f"File not found test: {'✓ Handled correctly' if not result.parsing_success else '✗ Should fail'}")
        
        return parser
        
    except Exception as e:
        print(f"✗ Parser basic test error: {e}")
        return None


def test_compliance_parser_with_llm(parser, llm_healthy):
    """Test the compliance parser with LLM integration."""
    print("\n=== Testing Compliance Parser (LLM Integration) ===")
    
    if not llm_healthy:
        print("⚠ Skipping LLM integration tests - LLM not healthy")
        return
    
    # Simple test text
    test_text = """
**Requirement R1:** During account signup, the user must agree to our Terms of Service.
*   **Status:** Non-Compliant
*   **Rationale:** Bundled consent violates GDPR Art. 7.
*   **Recommendation:** Implement separate opt-in checkboxes.
"""
    
    try:
        print("Testing with sample text...")
        result = parser.parse_report_text(test_text)
        
        if result.parsing_success:
            print(f"✓ Successfully parsed {len(result.requirements)} requirements")
            for req in result.requirements:
                print(f"  - {req.requirement_number}: {req.status}")
        else:
            print(f"✗ Parsing failed: {result.error_message}")
            
    except Exception as e:
        print(f"✗ LLM integration test error: {e}")


def test_actual_compliance_file(parser, llm_healthy):
    """Test parsing the actual compliance report file."""
    print("\n=== Testing Actual Compliance File ===")
    
    if not llm_healthy:
        print("⚠ Skipping actual file test - LLM not healthy")
        return
    
    try:
        print("Parsing Compliance_report_ra_agent.txt...")
        result = parser.parse_report_file("Compliance_report_ra_agent.txt")
        
        if result.parsing_success:
            print(f"✓ Successfully parsed {len(result.requirements)} requirements")
            
            # Show summary
            stats = parser.get_parsing_statistics(result)
            print(f"Statistics: {stats}")
            
            # Show first few requirements
            for i, req in enumerate(result.requirements[:3]):
                print(f"  Requirement {i+1}:")
                print(f"    Number: {req.requirement_number}")
                print(f"    Status: {req.status}")
                print(f"    Text: {req.requirement_text[:100]}...")
                
        else:
            print(f"✗ Parsing failed: {result.error_message}")
            
    except Exception as e:
        print(f"✗ Actual file test error: {e}")


def main():
    """Run comprehensive tests."""
    print("Starting comprehensive tests...\n")
    
    # Test LLM client
    llm_client, llm_healthy = test_llm_client()
    
    # Test parser basic functionality
    parser = test_compliance_parser_basic()
    
    if parser:
        # Test parser with LLM
        test_compliance_parser_with_llm(parser, llm_healthy)
        
        # Test with actual file
        test_actual_compliance_file(parser, llm_healthy)
    
    print("\n=== Tests Complete ===")


if __name__ == "__main__":
    main()