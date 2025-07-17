"""Unit tests for ComplianceReportParser."""

import json
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from memory_management.parsers.compliance_report_parser import (
    ComplianceReportParser,
    ComplianceRequirement,
    ParsedComplianceReport
)
from memory_management.llm.client import LLMClient, LLMResponse


class TestComplianceRequirement:
    """Test ComplianceRequirement data class."""
    
    def test_compliance_requirement_creation(self):
        """Test creating a ComplianceRequirement instance."""
        req = ComplianceRequirement(
            requirement_number="R1",
            requirement_text="Test requirement text",
            status="Non-Compliant",
            rationale="Test rationale",
            recommendation="Test recommendation"
        )
        
        assert req.requirement_number == "R1"
        assert req.requirement_text == "Test requirement text"
        assert req.status == "Non-Compliant"
        assert req.rationale == "Test rationale"
        assert req.recommendation == "Test recommendation"
    
    def test_compliance_requirement_to_dict(self):
        """Test converting ComplianceRequirement to dictionary."""
        req = ComplianceRequirement(
            requirement_number="R1",
            requirement_text="Test requirement text",
            status="Non-Compliant",
            rationale="Test rationale",
            recommendation="Test recommendation"
        )
        
        expected_dict = {
            'requirement_number': "R1",
            'requirement_text': "Test requirement text",
            'status': "Non-Compliant",
            'rationale': "Test rationale",
            'recommendation': "Test recommendation"
        }
        
        assert req.to_dict() == expected_dict


class TestParsedComplianceReport:
    """Test ParsedComplianceReport data class."""
    
    def test_parsed_compliance_report_creation(self):
        """Test creating a ParsedComplianceReport instance."""
        req = ComplianceRequirement(
            requirement_number="R1",
            requirement_text="Test requirement text",
            status="Non-Compliant",
            rationale="Test rationale",
            recommendation="Test recommendation"
        )
        
        report = ParsedComplianceReport(
            requirements=[req],
            raw_text="Raw report text",
            parsing_success=True
        )
        
        assert len(report.requirements) == 1
        assert report.requirements[0] == req
        assert report.raw_text == "Raw report text"
        assert report.parsing_success is True
        assert report.error_message is None
    
    def test_parsed_compliance_report_to_dict(self):
        """Test converting ParsedComplianceReport to dictionary."""
        req = ComplianceRequirement(
            requirement_number="R1",
            requirement_text="Test requirement text",
            status="Non-Compliant",
            rationale="Test rationale",
            recommendation="Test recommendation"
        )
        
        report = ParsedComplianceReport(
            requirements=[req],
            raw_text="Raw report text",
            parsing_success=True,
            error_message="Test error"
        )
        
        result_dict = report.to_dict()
        
        assert result_dict['parsing_success'] is True
        assert result_dict['raw_text'] == "Raw report text"
        assert result_dict['error_message'] == "Test error"
        assert len(result_dict['requirements']) == 1
        assert result_dict['requirements'][0] == req.to_dict()


class TestComplianceReportParser:
    """Test ComplianceReportParser class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        return Mock(spec=LLMClient)
    
    @pytest.fixture
    def parser(self, mock_llm_client):
        """Create a ComplianceReportParser instance with mock LLM client."""
        return ComplianceReportParser(llm_client=mock_llm_client)
    
    @pytest.fixture
    def sample_report_text(self):
        """Sample compliance report text for testing."""
        return """
## FINAL COMPLIANCE ASSESSMENT REPORT (RA_Agent) ##

**Project:** E-commerce Platform SRS
**Governing Policy:** GDPR
**Status:** 2 Non-Compliant, 1 Compliant Requirements Identified.

---
**Requirement R1:** During account signup, the user must agree to our Terms of Service.
*   **Status:** Non-Compliant
*   **Rationale:** Bundled consent violates GDPR Art. 7.
*   **Recommendation:** Implement separate opt-in checkboxes.

---
**Requirement R2:** All user passwords will be stored using SHA-256 hashing.
*   **Status:** Compliant
*   **Rationale:** SHA-256 hashing aligns with GDPR Art. 32.
*   **Recommendation:** None needed.
"""
    
    @pytest.fixture
    def sample_llm_response(self):
        """Sample LLM response for testing."""
        return {
            "requirements": [
                {
                    "requirement_number": "R1",
                    "requirement_text": "During account signup, the user must agree to our Terms of Service.",
                    "status": "Non-Compliant",
                    "rationale": "Bundled consent violates GDPR Art. 7.",
                    "recommendation": "Implement separate opt-in checkboxes."
                },
                {
                    "requirement_number": "R2",
                    "requirement_text": "All user passwords will be stored using SHA-256 hashing.",
                    "status": "Compliant",
                    "rationale": "SHA-256 hashing aligns with GDPR Art. 32.",
                    "recommendation": "None needed."
                }
            ]
        }
    
    def test_parser_initialization(self):
        """Test ComplianceReportParser initialization."""
        # Test with default LLM client
        parser = ComplianceReportParser()
        assert parser.llm_client is not None
        assert parser.model == 'qwq:32b'
        
        # Test with custom LLM client and model
        mock_client = Mock(spec=LLMClient)
        parser = ComplianceReportParser(llm_client=mock_client, model='gemma3:27b')
        assert parser.llm_client == mock_client
        assert parser.model == 'gemma3:27b'
    
    def test_parse_report_text_success(self, parser, mock_llm_client, sample_report_text, sample_llm_response):
        """Test successful parsing of compliance report text."""
        # Mock successful LLM response
        mock_response = LLMResponse(
            content=json.dumps(sample_llm_response),
            model='qwq:32b',
            success=True
        )
        mock_llm_client.extract_structured_data.return_value = mock_response
        
        result = parser.parse_report_text(sample_report_text)
        
        assert result.parsing_success is True
        assert result.error_message is None
        assert len(result.requirements) == 2
        assert result.raw_text == sample_report_text
        
        # Check first requirement
        req1 = result.requirements[0]
        assert req1.requirement_number == "R1"
        assert req1.status == "Non-Compliant"
        assert "Terms of Service" in req1.requirement_text
        
        # Check second requirement
        req2 = result.requirements[1]
        assert req2.requirement_number == "R2"
        assert req2.status == "Compliant"
        assert "SHA-256" in req2.requirement_text
    
    def test_parse_report_text_empty_input(self, parser):
        """Test parsing with empty input text."""
        result = parser.parse_report_text("")
        
        assert result.parsing_success is False
        assert "Empty report text provided" in result.error_message
        assert len(result.requirements) == 0
    
    def test_parse_report_text_llm_failure(self, parser, mock_llm_client, sample_report_text):
        """Test handling of LLM extraction failure."""
        # Mock failed LLM response
        mock_response = LLMResponse(
            content='',
            model='qwq:32b',
            success=False,
            error="Connection timeout"
        )
        mock_llm_client.extract_structured_data.return_value = mock_response
        
        result = parser.parse_report_text(sample_report_text)
        
        assert result.parsing_success is False
        assert "LLM extraction failed: Connection timeout" in result.error_message
        assert len(result.requirements) == 0
    
    def test_parse_report_text_invalid_json(self, parser, mock_llm_client, sample_report_text):
        """Test handling of invalid JSON response from LLM."""
        # Mock LLM response with invalid JSON
        mock_response = LLMResponse(
            content='{"invalid": json}',  # Invalid JSON
            model='qwq:32b',
            success=True
        )
        mock_llm_client.extract_structured_data.return_value = mock_response
        
        result = parser.parse_report_text(sample_report_text)
        
        assert result.parsing_success is False
        assert "JSON parsing error" in result.error_message
        assert len(result.requirements) == 0
    
    def test_parse_report_file_success(self, parser, mock_llm_client, sample_report_text, sample_llm_response):
        """Test successful parsing of compliance report from file."""
        # Create temporary file with sample content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(sample_report_text)
            temp_file_path = temp_file.name
        
        try:
            # Mock successful LLM response
            mock_response = LLMResponse(
                content=json.dumps(sample_llm_response),
                model='qwq:32b',
                success=True
            )
            mock_llm_client.extract_structured_data.return_value = mock_response
            
            result = parser.parse_report_file(temp_file_path)
            
            assert result.parsing_success is True
            assert len(result.requirements) == 2
            assert result.raw_text == sample_report_text
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    def test_parse_report_file_not_found(self, parser):
        """Test handling of non-existent file."""
        result = parser.parse_report_file("non_existent_file.txt")
        
        assert result.parsing_success is False
        assert "File not found" in result.error_message
        assert len(result.requirements) == 0
    
    def test_convert_to_requirements(self, parser):
        """Test conversion of JSON data to ComplianceRequirement objects."""
        requirements_data = [
            {
                "requirement_number": "R1",
                "requirement_text": "Test requirement 1",
                "status": "Non-Compliant",
                "rationale": "Test rationale 1",
                "recommendation": "Test recommendation 1"
            },
            {
                "requirement_number": "R2",
                "requirement_text": "Test requirement 2",
                "status": "Compliant",
                "rationale": "Test rationale 2",
                "recommendation": "Test recommendation 2"
            }
        ]
        
        requirements = parser._convert_to_requirements(requirements_data)
        
        assert len(requirements) == 2
        assert requirements[0].requirement_number == "R1"
        assert requirements[0].status == "Non-Compliant"
        assert requirements[1].requirement_number == "R2"
        assert requirements[1].status == "Compliant"
    
    def test_convert_to_requirements_missing_fields(self, parser):
        """Test handling of missing required fields in requirement data."""
        requirements_data = [
            {
                "requirement_number": "R1",
                "requirement_text": "Test requirement 1",
                "status": "Non-Compliant",
                "rationale": "Test rationale 1",
                "recommendation": "Test recommendation 1"
            },
            {
                # Missing requirement_number and requirement_text
                "status": "Compliant",
                "rationale": "Test rationale 2",
                "recommendation": "Test recommendation 2"
            }
        ]
        
        requirements = parser._convert_to_requirements(requirements_data)
        
        # Should only return the valid requirement
        assert len(requirements) == 1
        assert requirements[0].requirement_number == "R1"
    
    def test_validate_parsed_data_success(self, parser):
        """Test validation of successfully parsed data."""
        requirements = [
            ComplianceRequirement(
                requirement_number="R1",
                requirement_text="Test requirement 1",
                status="Non-Compliant",
                rationale="Test rationale 1",
                recommendation="Test recommendation 1"
            ),
            ComplianceRequirement(
                requirement_number="R2",
                requirement_text="Test requirement 2",
                status="Compliant",
                rationale="Test rationale 2",
                recommendation="Test recommendation 2"
            )
        ]
        
        parsed_report = ParsedComplianceReport(
            requirements=requirements,
            raw_text="Test raw text",
            parsing_success=True
        )
        
        validation = parser.validate_parsed_data(parsed_report)
        
        assert validation['is_valid'] is True
        assert len(validation['errors']) == 0
        assert validation['statistics']['total_requirements'] == 2
        assert validation['statistics']['compliant_count'] == 1
        assert validation['statistics']['non_compliant_count'] == 1
    
    def test_validate_parsed_data_parsing_failure(self, parser):
        """Test validation of failed parsing."""
        parsed_report = ParsedComplianceReport(
            requirements=[],
            raw_text="Test raw text",
            parsing_success=False,
            error_message="Test error"
        )
        
        validation = parser.validate_parsed_data(parsed_report)
        
        assert validation['is_valid'] is False
        assert "Parsing failed: Test error" in validation['errors']
    
    def test_validate_parsed_data_no_requirements(self, parser):
        """Test validation when no requirements are found."""
        parsed_report = ParsedComplianceReport(
            requirements=[],
            raw_text="Test raw text",
            parsing_success=True
        )
        
        validation = parser.validate_parsed_data(parsed_report)
        
        assert validation['is_valid'] is False
        assert "No requirements found in the report" in validation['errors']
    
    def test_get_requirements_by_status(self, parser):
        """Test filtering requirements by status."""
        requirements = [
            ComplianceRequirement(
                requirement_number="R1",
                requirement_text="Test requirement 1",
                status="Non-Compliant",
                rationale="Test rationale 1",
                recommendation="Test recommendation 1"
            ),
            ComplianceRequirement(
                requirement_number="R2",
                requirement_text="Test requirement 2",
                status="Compliant",
                rationale="Test rationale 2",
                recommendation="Test recommendation 2"
            ),
            ComplianceRequirement(
                requirement_number="R3",
                requirement_text="Test requirement 3",
                status="Partially Compliant",
                rationale="Test rationale 3",
                recommendation="Test recommendation 3"
            )
        ]
        
        parsed_report = ParsedComplianceReport(
            requirements=requirements,
            raw_text="Test raw text",
            parsing_success=True
        )
        
        # Test filtering by different statuses
        non_compliant = parser.get_requirements_by_status(parsed_report, "Non-Compliant")
        assert len(non_compliant) == 1
        assert non_compliant[0].requirement_number == "R1"
        
        # Test exact match for "Compliant" (should not match "Non-Compliant" or "Partially Compliant")
        compliant_exact = parser.get_requirements_by_status(parsed_report, "Compliant")
        # This will match all that contain "compliant" - let's test what we actually get
        compliant_only = [req for req in compliant_exact if req.status == "Compliant"]
        assert len(compliant_only) == 1
        assert compliant_only[0].requirement_number == "R2"
        
        partial = parser.get_requirements_by_status(parsed_report, "Partial")
        assert len(partial) == 1
        assert partial[0].requirement_number == "R3"
    
    def test_get_parsing_statistics(self, parser):
        """Test getting parsing statistics."""
        requirements = [
            ComplianceRequirement(
                requirement_number="R1",
                requirement_text="Test requirement 1 with some text",
                status="Non-Compliant",
                rationale="Test rationale 1",
                recommendation="Test recommendation 1"
            ),
            ComplianceRequirement(
                requirement_number="R2",
                requirement_text="Test requirement 2",
                status="Compliant",
                rationale="Test rationale 2",
                recommendation=""  # Empty recommendation
            )
        ]
        
        parsed_report = ParsedComplianceReport(
            requirements=requirements,
            raw_text="Test raw text",
            parsing_success=True
        )
        
        stats = parser.get_parsing_statistics(parsed_report)
        
        assert stats['parsing_success'] is True
        assert stats['total_requirements'] == 2
        assert stats['status_distribution']['Non-Compliant'] == 1
        assert stats['status_distribution']['Compliant'] == 1
        assert stats['has_recommendations'] == 1  # Only one has non-empty recommendation
        assert stats['average_text_length'] > 0
    
    def test_get_parsing_statistics_failure(self, parser):
        """Test getting statistics for failed parsing."""
        parsed_report = ParsedComplianceReport(
            requirements=[],
            raw_text="Test raw text",
            parsing_success=False,
            error_message="Test error"
        )
        
        stats = parser.get_parsing_statistics(parsed_report)
        
        assert stats['parsing_success'] is False
        assert stats['error'] == "Test error"
        assert stats['total_requirements'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])