"""Unit tests for the HumanFeedbackParser."""

import unittest
import json
from unittest.mock import MagicMock, patch
from memory_management.parsers.human_feedback_parser import (
    HumanFeedbackParser, 
    ParsedHumanFeedback,
    FeedbackItem
)
from memory_management.llm.client import LLMResponse


class TestHumanFeedbackParser(unittest.TestCase):
    """Test cases for HumanFeedbackParser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm_client = MagicMock()
        self.parser = HumanFeedbackParser(llm_client=self.mock_llm_client)
        
        # Sample feedback text
        self.sample_feedback = """
## HUMAN EXPERT FEEDBACK ##

**Reviewer:** Legal Expert
**Date:** 2024-10-27

**Overall Assessment:** The RA_Agent's report is largely correct and provides a solid baseline. The analysis of R1, R3, and R5 is accurate. However, there are two key areas that require correction and refinement based on deeper legal and technical best practices.

**Feedback on R2 (Data Retention):**
The agent correctly identified the issue with "indefinite" storage. However, the recommendation of a fixed "5 years" is too simplistic and arbitrary. A better, more defensible policy is event-driven.
*   **Refined Suggestion for R2:** "The data retention policy should be event-based. For example: 'User data will be retained for 3 years following the user's last login or transaction. The account will be considered inactive after this period and scheduled for deletion.'"

**Feedback on R4 (Password Hashing):**
This is the most critical error in the report. The agent marked this as "Compliant," but it is not. While SHA-256 is an industry standard, using it without a salt is a known vulnerability. This requirement is ambiguous and does not represent a state-of-the-art technical measure as required by Article 32.
*   **Decision on R4:** Change status from "Compliant" to "Partially Compliant".
*   **Expert Rationale for R4:** A raw (unsalted) hash is vulnerable to pre-computed "rainbow table" attacks. GDPR's "state-of-the-art" security requirement implies protection against such common attack vectors.
*   **Refined Suggestion for R4:** "The requirement must be updated to specify the use of a salted hash. For example: 'All user passwords will be stored using a salted SHA-256 hashing algorithm to ensure strong cryptographic protection.'"
"""
        
        # Sample LLM response for successful parsing
        self.sample_llm_response = {
            "feedback_items": [
                {
                    "requirement_reference": "R2",
                    "decision": "Modify",
                    "rationale": "The recommendation of a fixed '5 years' is too simplistic and arbitrary. A better, more defensible policy is event-driven.",
                    "suggestion": "The data retention policy should be event-based. For example: 'User data will be retained for 3 years following the user's last login or transaction. The account will be considered inactive after this period and scheduled for deletion.'",
                    "confidence": "High"
                },
                {
                    "requirement_reference": "R4",
                    "decision": "Change status from 'Compliant' to 'Partially Compliant'",
                    "rationale": "A raw (unsalted) hash is vulnerable to pre-computed 'rainbow table' attacks. GDPR's 'state-of-the-art' security requirement implies protection against such common attack vectors.",
                    "suggestion": "The requirement must be updated to specify the use of a salted hash. For example: 'All user passwords will be stored using a salted SHA-256 hashing algorithm to ensure strong cryptographic protection.'",
                    "confidence": "High"
                }
            ]
        }
    
    def test_parse_feedback_text_success(self):
        """Test successful parsing of feedback text."""
        # Mock the LLM client response
        self.mock_llm_client.extract_structured_data.return_value = LLMResponse(
            content=json.dumps(self.sample_llm_response),
            model="qwq:32b",
            success=True
        )
        
        # Parse the feedback
        result = self.parser.parse_feedback_text(self.sample_feedback)
        
        # Verify the result
        self.assertTrue(result.parsing_success)
        self.assertEqual(len(result.feedback_items), 2)
        self.assertEqual(result.feedback_items[0].requirement_reference, "R2")
        self.assertEqual(result.feedback_items[1].requirement_reference, "R4")
        self.assertIn("Partially Compliant", result.feedback_items[1].decision)
    
    def test_parse_feedback_text_llm_failure(self):
        """Test handling of LLM failure during parsing."""
        # Mock LLM client to return an error
        self.mock_llm_client.extract_structured_data.return_value = LLMResponse(
            content="",
            model="qwq:32b",
            success=False,
            error="LLM API error"
        )
        
        # Parse the feedback
        result = self.parser.parse_feedback_text(self.sample_feedback)
        
        # Verify the result
        self.assertFalse(result.parsing_success)
        self.assertEqual(len(result.feedback_items), 0)
        self.assertIn("LLM extraction failed", result.error_message)
    
    def test_parse_feedback_text_empty_input(self):
        """Test handling of empty input text."""
        # Parse empty feedback
        result = self.parser.parse_feedback_text("")
        
        # Verify the result
        self.assertFalse(result.parsing_success)
        self.assertEqual(len(result.feedback_items), 0)
        self.assertIn("Empty feedback text", result.error_message)
    
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="Sample feedback text")
    def test_parse_feedback_file_success(self, mock_open):
        """Test successful parsing from a file."""
        # Mock the parse_feedback_text method
        self.parser.parse_feedback_text = MagicMock(return_value=ParsedHumanFeedback(
            feedback_items=[
                FeedbackItem(
                    requirement_reference="R1",
                    decision="Accept",
                    rationale="Good analysis",
                    suggestion=""
                )
            ],
            raw_text="Sample feedback text",
            parsing_success=True
        ))
        
        # Parse from file
        result = self.parser.parse_feedback_file("dummy_path.txt")
        
        # Verify the result
        self.assertTrue(result.parsing_success)
        self.assertEqual(len(result.feedback_items), 1)
        mock_open.assert_called_once_with("dummy_path.txt", "r", encoding="utf-8")
    
    def test_parse_feedback_file_not_found(self):
        """Test handling of file not found error."""
        # Mock open to raise FileNotFoundError
        with patch('builtins.open', side_effect=FileNotFoundError()):
            result = self.parser.parse_feedback_file("nonexistent_file.txt")
            
            # Verify the result
            self.assertFalse(result.parsing_success)
            self.assertEqual(len(result.feedback_items), 0)
            self.assertIn("File not found", result.error_message)
    
    def test_validate_parsed_data_valid(self):
        """Test validation of valid parsed data."""
        # Create a valid parsed feedback
        parsed_feedback = ParsedHumanFeedback(
            feedback_items=[
                FeedbackItem(
                    requirement_reference="R1",
                    decision="Accept",
                    rationale="Good analysis",
                    suggestion=""
                ),
                FeedbackItem(
                    requirement_reference="R2",
                    decision="Modify",
                    rationale="Needs improvement",
                    suggestion="Improve this"
                )
            ],
            raw_text="Sample feedback",
            parsing_success=True
        )
        
        # Validate the parsed data
        result = self.parser.validate_parsed_data(parsed_feedback)
        
        # Verify the result
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['statistics']['total_feedback_items'], 2)
        self.assertEqual(result['statistics']['accept_count'], 1)
        self.assertEqual(result['statistics']['modify_count'], 1)
    
    def test_validate_parsed_data_invalid(self):
        """Test validation of invalid parsed data."""
        # Create an invalid parsed feedback (missing required fields)
        parsed_feedback = ParsedHumanFeedback(
            feedback_items=[
                FeedbackItem(
                    requirement_reference="",  # Missing requirement reference
                    decision="Accept",
                    rationale="Good analysis",
                    suggestion=""
                )
            ],
            raw_text="Sample feedback",
            parsing_success=True
        )
        
        # Validate the parsed data
        result = self.parser.validate_parsed_data(parsed_feedback)
        
        # Verify the result
        self.assertFalse(result['is_valid'])
        self.assertTrue(any("Missing requirement reference" in error for error in result['errors']))
    
    def test_get_feedback_by_decision(self):
        """Test filtering feedback items by decision type."""
        # Create parsed feedback with different decision types
        parsed_feedback = ParsedHumanFeedback(
            feedback_items=[
                FeedbackItem(
                    requirement_reference="R1",
                    decision="Accept",
                    rationale="Good analysis",
                    suggestion=""
                ),
                FeedbackItem(
                    requirement_reference="R2",
                    decision="Modify",
                    rationale="Needs improvement",
                    suggestion="Improve this"
                ),
                FeedbackItem(
                    requirement_reference="R3",
                    decision="Accept with minor changes",
                    rationale="Mostly good",
                    suggestion="Small tweak"
                )
            ],
            raw_text="Sample feedback",
            parsing_success=True
        )
        
        # Filter by "Accept"
        accept_items = self.parser.get_feedback_by_decision(parsed_feedback, "Accept")
        
        # Verify the result
        self.assertEqual(len(accept_items), 2)  # Should match both "Accept" and "Accept with minor changes"
        self.assertEqual(accept_items[0].requirement_reference, "R1")
        self.assertEqual(accept_items[1].requirement_reference, "R3")
    
    def test_map_feedback_to_requirements(self):
        """Test mapping feedback items to requirements."""
        # Create parsed feedback
        parsed_feedback = ParsedHumanFeedback(
            feedback_items=[
                FeedbackItem(
                    requirement_reference="R1",
                    decision="Accept",
                    rationale="Good analysis",
                    suggestion=""
                ),
                FeedbackItem(
                    requirement_reference="R2",
                    decision="Modify",
                    rationale="Needs improvement",
                    suggestion="Improve this"
                )
            ],
            raw_text="Sample feedback",
            parsing_success=True
        )
        
        # Sample requirements
        requirements = [
            {
                "requirement_number": "R1",
                "requirement_text": "Sample requirement 1",
                "status": "Compliant"
            },
            {
                "requirement_number": "R2",
                "requirement_text": "Sample requirement 2",
                "status": "Non-Compliant"
            },
            {
                "requirement_number": "R3",
                "requirement_text": "Sample requirement 3",
                "status": "Partially Compliant"
            }
        ]
        
        # Map feedback to requirements
        mapping = self.parser.map_feedback_to_requirements(parsed_feedback, requirements)
        
        # Verify the mapping
        self.assertEqual(len(mapping), 2)
        self.assertIn("R1", mapping)
        self.assertIn("R2", mapping)
        self.assertEqual(mapping["R1"]["requirement"]["status"], "Compliant")
        self.assertEqual(mapping["R2"]["feedback"]["decision"], "Modify")
    
    def test_extract_requirement_reference(self):
        """Test extracting requirement reference using LLM."""
        # Mock the LLM client response
        self.mock_llm_client.generate.return_value = LLMResponse(
            content="Based on the feedback content, this refers to requirement R3.",
            model="qwq:32b",
            success=True
        )
        
        # Create a feedback item with unclear reference
        feedback_item = FeedbackItem(
            requirement_reference="",  # Empty reference
            decision="Modify",
            rationale="The password policy needs to be improved",
            suggestion="Add password complexity requirements"
        )
        
        # Sample requirements
        requirements = [
            {"requirement_number": "R1", "requirement_text": "User consent requirement"},
            {"requirement_number": "R2", "requirement_text": "Data retention policy"},
            {"requirement_number": "R3", "requirement_text": "Password security policy"}
        ]
        
        # Extract the reference
        reference = self.parser._extract_requirement_reference(feedback_item, requirements)
        
        # Verify the result
        self.assertEqual(reference, "R3")
        self.mock_llm_client.generate.assert_called_once()


if __name__ == '__main__':
    unittest.main()