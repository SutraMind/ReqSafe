"""LLM-based human feedback parser for extracting structured data."""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..llm.client import LLMClient, LLMResponse
from ..llm.prompts import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class FeedbackItem:
    """Structured representation of a human feedback item."""
    requirement_reference: str
    decision: str
    rationale: str
    suggestion: str
    confidence: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'requirement_reference': self.requirement_reference,
            'decision': self.decision,
            'rationale': self.rationale,
            'suggestion': self.suggestion,
            'confidence': self.confidence
        }


@dataclass
class ParsedHumanFeedback:
    """Container for parsed human feedback data."""
    feedback_items: List[FeedbackItem]
    raw_text: str
    parsing_success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'feedback_items': [item.to_dict() for item in self.feedback_items],
            'raw_text': self.raw_text,
            'parsing_success': self.parsing_success,
            'error_message': self.error_message
        }


class HumanFeedbackParser:
    """LLM-based parser for human expert feedback."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, model: str = 'qwq:32b'):
        """
        Initialize the human feedback parser.
        
        Args:
            llm_client: Optional LLM client instance
            model: Model to use for parsing
        """
        self.llm_client = llm_client or LLMClient()
        self.model = model
        self.prompt_templates = PromptTemplates()
    
    def parse_feedback_file(self, file_path: str) -> ParsedHumanFeedback:
        """
        Parse human feedback from a file.
        
        Args:
            file_path: Path to the human feedback file
            
        Returns:
            ParsedHumanFeedback with extracted data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                feedback_text = file.read()
            
            return self.parse_feedback_text(feedback_text)
            
        except FileNotFoundError:
            logger.error(f"Human feedback file not found: {file_path}")
            return ParsedHumanFeedback(
                feedback_items=[],
                raw_text="",
                parsing_success=False,
                error_message=f"File not found: {file_path}"
            )
        except Exception as e:
            logger.error(f"Error reading human feedback file: {str(e)}")
            return ParsedHumanFeedback(
                feedback_items=[],
                raw_text="",
                parsing_success=False,
                error_message=f"File reading error: {str(e)}"
            )
    
    def parse_feedback_text(self, feedback_text: str) -> ParsedHumanFeedback:
        """
        Parse human feedback from text content.
        
        Args:
            feedback_text: Raw human feedback text
            
        Returns:
            ParsedHumanFeedback with extracted data
        """
        if not feedback_text.strip():
            return ParsedHumanFeedback(
                feedback_items=[],
                raw_text=feedback_text,
                parsing_success=False,
                error_message="Empty feedback text provided"
            )
        
        try:
            # Get prompt template and schema
            template_data = self.prompt_templates.human_feedback_extraction()
            prompt = template_data["template"].format(feedback_text=feedback_text)
            schema = template_data["schema"]
            system_prompt = self.prompt_templates.get_system_prompts()["feedback_analysis"]
            
            # Extract structured data using LLM
            logger.info("Extracting human feedback items using LLM")
            response = self.llm_client.extract_structured_data(
                prompt=prompt,
                expected_schema=schema,
                model=self.model,
                system_prompt=system_prompt
            )
            
            if not response.success:
                logger.error(f"LLM extraction failed: {response.error}")
                return ParsedHumanFeedback(
                    feedback_items=[],
                    raw_text=feedback_text,
                    parsing_success=False,
                    error_message=f"LLM extraction failed: {response.error}"
                )
            
            # Parse the JSON response
            try:
                parsed_data = json.loads(response.content)
                feedback_items = self._convert_to_feedback_items(parsed_data.get('feedback_items', []))
                
                logger.info(f"Successfully parsed {len(feedback_items)} feedback items")
                return ParsedHumanFeedback(
                    feedback_items=feedback_items,
                    raw_text=feedback_text,
                    parsing_success=True
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {str(e)}")
                return ParsedHumanFeedback(
                    feedback_items=[],
                    raw_text=feedback_text,
                    parsing_success=False,
                    error_message=f"JSON parsing error: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Unexpected error during human feedback parsing: {str(e)}")
            return ParsedHumanFeedback(
                feedback_items=[],
                raw_text=feedback_text,
                parsing_success=False,
                error_message=f"Parsing error: {str(e)}"
            )
    
    def _convert_to_feedback_items(self, feedback_data: List[Dict[str, Any]]) -> List[FeedbackItem]:
        """
        Convert parsed JSON data to FeedbackItem objects.
        
        Args:
            feedback_data: List of feedback item dictionaries from LLM
            
        Returns:
            List of FeedbackItem objects
        """
        feedback_items = []
        
        for item_data in feedback_data:
            try:
                feedback_item = FeedbackItem(
                    requirement_reference=str(item_data.get('requirement_reference', '')).strip(),
                    decision=str(item_data.get('decision', '')).strip(),
                    rationale=str(item_data.get('rationale', '')).strip(),
                    suggestion=str(item_data.get('suggestion', '')).strip(),
                    confidence=str(item_data.get('confidence', '')).strip()
                )
                
                # Validate that required fields are not empty
                if not feedback_item.requirement_reference or not feedback_item.decision:
                    logger.warning(f"Skipping feedback item with missing required fields: {item_data}")
                    continue
                
                feedback_items.append(feedback_item)
                
            except Exception as e:
                logger.warning(f"Error converting feedback item data: {str(e)}, data: {item_data}")
                continue
        
        return feedback_items
    
    def map_feedback_to_requirements(self, 
                                    feedback: ParsedHumanFeedback, 
                                    compliance_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Map human feedback items to corresponding compliance requirements.
        
        Args:
            feedback: Parsed human feedback
            compliance_requirements: List of compliance requirement dictionaries
            
        Returns:
            Dictionary mapping requirement numbers to feedback items
        """
        if not feedback.parsing_success:
            logger.error("Cannot map feedback: parsing was unsuccessful")
            return {}
        
        mapping = {}
        req_dict = {req['requirement_number']: req for req in compliance_requirements}
        
        for item in feedback.feedback_items:
            req_ref = item.requirement_reference
            
            # Clean up requirement reference (e.g., "R2" -> "R2")
            req_ref = req_ref.strip().upper()
            if req_ref.startswith('R') and req_ref[1:].isdigit():
                req_num = req_ref
            else:
                # Try to extract requirement number using LLM if reference is unclear
                req_num = self._extract_requirement_reference(item, compliance_requirements)
            
            if req_num in req_dict:
                mapping[req_num] = {
                    'requirement': req_dict[req_num],
                    'feedback': item.to_dict()
                }
            else:
                logger.warning(f"No matching requirement found for feedback reference: {req_ref}")
        
        return mapping
    
    def _extract_requirement_reference(self, 
                                      feedback_item: FeedbackItem, 
                                      compliance_requirements: List[Dict[str, Any]]) -> str:
        """
        Use LLM to extract the requirement reference when it's not clearly specified.
        
        Args:
            feedback_item: Feedback item to analyze
            compliance_requirements: List of compliance requirement dictionaries
            
        Returns:
            Extracted requirement number or empty string if not found
        """
        # Create a prompt to match feedback to requirements
        requirements_text = "\n\n".join([
            f"Requirement {req['requirement_number']}: {req['requirement_text']}"
            for req in compliance_requirements
        ])
        
        prompt = f"""
Determine which requirement number this feedback item refers to.
The feedback might mention the requirement explicitly or implicitly.

Available requirements:
{requirements_text}

Feedback item:
Decision: {feedback_item.decision}
Rationale: {feedback_item.rationale}
Suggestion: {feedback_item.suggestion}

Return only the requirement number (e.g., R1, R2) that this feedback most likely refers to.
"""
        
        system_prompt = "You are an expert at matching feedback to requirements. Identify which requirement a feedback item refers to based on context clues."
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model=self.model,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            if response.success:
                # Extract requirement number from response
                content = response.content.strip()
                # Look for patterns like "R1", "R2", etc.
                import re
                matches = re.search(r'R\d+', content, re.IGNORECASE)
                if matches:
                    return matches.group(0).upper()
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting requirement reference: {str(e)}")
            return ""
    
    def validate_parsed_data(self, parsed_feedback: ParsedHumanFeedback) -> Dict[str, Any]:
        """
        Validate the parsed human feedback data.
        
        Args:
            parsed_feedback: Parsed human feedback to validate
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {
                'total_feedback_items': len(parsed_feedback.feedback_items),
                'accept_count': 0,
                'reject_count': 0,
                'modify_count': 0,
                'other_decision_count': 0
            }
        }
        
        if not parsed_feedback.parsing_success:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Parsing failed: {parsed_feedback.error_message}")
            return validation_results
        
        if not parsed_feedback.feedback_items:
            validation_results['is_valid'] = False
            validation_results['errors'].append("No feedback items found in the text")
            return validation_results
        
        # Validate individual feedback items
        for i, item in enumerate(parsed_feedback.feedback_items):
            item_errors = []
            
            # Check required fields
            if not item.requirement_reference:
                item_errors.append("Missing requirement reference")
            if not item.decision:
                item_errors.append("Missing decision")
            if not item.rationale:
                item_errors.append("Missing rationale")
            
            # Count decision types
            decision_lower = item.decision.lower()
            if 'accept' in decision_lower or 'no change' in decision_lower:
                validation_results['statistics']['accept_count'] += 1
            elif 'reject' in decision_lower:
                validation_results['statistics']['reject_count'] += 1
            elif 'modify' in decision_lower or 'change' in decision_lower:
                validation_results['statistics']['modify_count'] += 1
            else:
                validation_results['statistics']['other_decision_count'] += 1
            
            if item_errors:
                validation_results['errors'].extend([f"Feedback item {i+1}: {error}" for error in item_errors])
                validation_results['is_valid'] = False
        
        # Check for duplicate requirement references
        req_refs = [item.requirement_reference for item in parsed_feedback.feedback_items]
        duplicates = set([ref for ref in req_refs if req_refs.count(ref) > 1])
        if duplicates:
            validation_results['warnings'].append(f"Duplicate requirement references found: {list(duplicates)}")
        
        return validation_results
    
    def get_feedback_by_decision(self, parsed_feedback: ParsedHumanFeedback, decision_type: str) -> List[FeedbackItem]:
        """
        Filter feedback items by decision type.
        
        Args:
            parsed_feedback: Parsed human feedback
            decision_type: Decision type to filter by (case-insensitive)
            
        Returns:
            List of feedback items matching the decision type
        """
        decision_lower = decision_type.lower()
        return [
            item for item in parsed_feedback.feedback_items 
            if decision_lower in item.decision.lower()
        ]
    
    def get_parsing_statistics(self, parsed_feedback: ParsedHumanFeedback) -> Dict[str, Any]:
        """
        Get statistics about the parsed feedback.
        
        Args:
            parsed_feedback: Parsed human feedback
            
        Returns:
            Dictionary with parsing statistics
        """
        if not parsed_feedback.parsing_success:
            return {
                'parsing_success': False,
                'error': parsed_feedback.error_message,
                'total_feedback_items': 0
            }
        
        decision_counts = {}
        for item in parsed_feedback.feedback_items:
            decision = item.decision
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        return {
            'parsing_success': True,
            'total_feedback_items': len(parsed_feedback.feedback_items),
            'decision_distribution': decision_counts,
            'has_suggestions': sum(1 for item in parsed_feedback.feedback_items if item.suggestion.strip()),
            'average_rationale_length': sum(len(item.rationale) for item in parsed_feedback.feedback_items) / len(parsed_feedback.feedback_items) if parsed_feedback.feedback_items else 0
        }