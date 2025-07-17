"""Integration test for ComplianceReportParser with real LLM."""

import pytest
import json
from memory_management.parsers.compliance_report_parser import ComplianceReportParser
from memory_management.llm.client import LLMClient


class TestComplianceReportParserIntegration:
    """Integration tests for ComplianceReportParser with real LLM."""
    
    @pytest.fixture
    def parser(self):
        """Create a real ComplianceReportParser instance."""
        return ComplianceReportParser()
    
    def test_parse_actual_compliance_report(self, parser):
        """Test parsing the actual compliance report file."""
        # This test requires Ollama to be running
        try:
            # Check if LLM is available
            if not parser.llm_client.check_health():
                pytest.skip("LLM client not available")
            
            # Parse the actual file
            result = parser.parse_report_file("Compliance_report_ra_agent.txt")
            
            # Basic assertions
            assert result.parsing_success, f"Parsing failed: {result.error_message}"
            assert len(result.requirements) > 0, "No requirements found"
            assert result.raw_text, "No raw text captured"
            
            # Check that we found the expected requirements
            req_numbers = [req.requirement_number for req in result.requirements]
            expected_reqs = ["R1", "R2", "R3", "R4", "R5"]
            
            for expected_req in expected_reqs:
                assert any(expected_req in req_num for req_num in req_numbers), f"Missing requirement {expected_req}"
            
            # Validate the parsed data
            validation = parser.validate_parsed_data(result)
            assert validation['is_valid'], f"Validation failed: {validation['errors']}"
            
            # Check statistics
            stats = parser.get_parsing_statistics(result)
            assert stats['parsing_success']
            assert stats['total_requirements'] >= 5
            
            print(f"Successfully parsed {len(result.requirements)} requirements")
            for req in result.requirements:
                print(f"  {req.requirement_number}: {req.status}")
                
        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")
    
    def test_parse_sample_text(self, parser):
        """Test parsing with a simple sample text."""
        sample_text = """
**Requirement R1:** During account signup, the user must agree to our Terms of Service.
*   **Status:** Non-Compliant
*   **Rationale:** Bundled consent violates GDPR Art. 7.
*   **Recommendation:** Implement separate opt-in checkboxes.

**Requirement R2:** All user passwords will be stored using SHA-256 hashing.
*   **Status:** Compliant
*   **Rationale:** SHA-256 hashing aligns with GDPR Art. 32.
*   **Recommendation:** None needed.
"""
        
        try:
            # Check if LLM is available
            if not parser.llm_client.check_health():
                pytest.skip("LLM client not available")
            
            result = parser.parse_report_text(sample_text)
            
            assert result.parsing_success, f"Parsing failed: {result.error_message}"
            assert len(result.requirements) >= 2, "Should find at least 2 requirements"
            
            # Check specific requirements
            req_numbers = [req.requirement_number for req in result.requirements]
            assert "R1" in str(req_numbers), "Should find R1"
            assert "R2" in str(req_numbers), "Should find R2"
            
            # Check statuses
            statuses = [req.status for req in result.requirements]
            assert any("Non-Compliant" in status for status in statuses), "Should find Non-Compliant status"
            assert any("Compliant" in status for status in statuses), "Should find Compliant status"
            
            print(f"Sample text parsing successful: {len(result.requirements)} requirements found")
            
        except Exception as e:
            pytest.fail(f"Sample text parsing failed: {str(e)}")


if __name__ == "__main__":
    # Run a simple test
    parser = ComplianceReportParser()
    
    print("Testing ComplianceReportParser integration...")
    
    # Test with sample text first
    sample_text = """
**Requirement R1:** Test requirement text.
*   **Status:** Non-Compliant
*   **Rationale:** Test rationale.
*   **Recommendation:** Test recommendation.
"""
    
    try:
        result = parser.parse_report_text(sample_text)
        print(f"Sample parsing result: {result.parsing_success}")
        if result.parsing_success:
            print(f"Found {len(result.requirements)} requirements")
        else:
            print(f"Error: {result.error_message}")
    except Exception as e:
        print(f"Error during sample parsing: {e}")
    
    print("Integration test complete.")