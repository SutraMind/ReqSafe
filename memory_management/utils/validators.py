"""
Data validation utilities for the memory management system.
"""

from typing import Dict, Any, List, Tuple
from ..models import STMEntry, LTMRule


class DataValidator:
    """Validates data completeness and format for memory management objects."""
    
    @staticmethod
    def validate_stm_entry(entry: STMEntry) -> Tuple[bool, List[str]]:
        """
        Validate an STM entry for completeness and format.
        
        Args:
            entry: STM entry to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not entry.validate():
            # Check specific validation failures
            if not entry.scenario_id or not entry.scenario_id.strip():
                errors.append("scenario_id is required and cannot be empty")
            
            if not entry.requirement_text or not entry.requirement_text.strip():
                errors.append("requirement_text is required and cannot be empty")
            
            if not entry.final_status or not entry.final_status.strip():
                errors.append("final_status is required and cannot be empty")
            
            # Validate scenario_id format
            parts = entry.scenario_id.split('_') if entry.scenario_id else []
            if len(parts) < 3:
                errors.append("scenario_id must follow format: {domain}_{requirement_number}_{key_concept}")
            
            # Validate nested objects
            if not entry.initial_assessment.validate():
                errors.append("initial_assessment is incomplete - status, rationale, and recommendation are required")
            
            if not entry.human_feedback.validate():
                errors.append("human_feedback is incomplete - decision, rationale, and suggestion are required")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_ltm_rule(rule: LTMRule) -> Tuple[bool, List[str]]:
        """
        Validate an LTM rule for completeness and format.
        
        Args:
            rule: LTM rule to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not rule.validate():
            # Check specific validation failures
            if not rule.rule_id or not rule.rule_id.strip():
                errors.append("rule_id is required and cannot be empty")
            
            if not rule.rule_text or not rule.rule_text.strip():
                errors.append("rule_text is required and cannot be empty")
            
            # Validate rule_id format
            parts = rule.rule_id.split('_') if rule.rule_id else []
            if len(parts) < 3:
                errors.append("rule_id must follow format: {policy}_{concept}_{version}")
            
            if not rule.related_concepts or len(rule.related_concepts) == 0:
                errors.append("related_concepts cannot be empty")
            
            if not rule.source_scenario_id or len(rule.source_scenario_id) == 0:
                errors.append("source_scenario_id cannot be empty")
            
            if not (0.0 <= rule.confidence_score <= 1.0):
                errors.append("confidence_score must be between 0.0 and 1.0")
            
            if rule.version < 1:
                errors.append("version must be a positive integer")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_extracted_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate extracted data from compliance reports and feedback.
        
        Args:
            data: Dictionary containing extracted data
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_fields = [
            'requirement_text',
            'initial_assessment',
            'human_feedback'
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate initial_assessment structure
        if 'initial_assessment' in data and isinstance(data['initial_assessment'], dict):
            assessment = data['initial_assessment']
            required_assessment_fields = ['status', 'rationale', 'recommendation']
            for field in required_assessment_fields:
                if field not in assessment or not assessment[field]:
                    errors.append(f"initial_assessment.{field} is required")
        
        # Validate human_feedback structure
        if 'human_feedback' in data and isinstance(data['human_feedback'], dict):
            feedback = data['human_feedback']
            required_feedback_fields = ['decision', 'rationale', 'suggestion']
            for field in required_feedback_fields:
                if field not in feedback or not feedback[field]:
                    errors.append(f"human_feedback.{field} is required")
        
        return len(errors) == 0, errors