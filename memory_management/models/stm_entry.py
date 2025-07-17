"""
Short-Term Memory (STM) Entry data model.

Represents detailed case files from compliance assessment interactions.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class InitialAssessment:
    """Initial assessment data from RA_Agent."""
    status: str
    rationale: str
    recommendation: str
    
    def validate(self) -> bool:
        """Validate the initial assessment data."""
        required_fields = ['status', 'rationale', 'recommendation']
        for field in required_fields:
            if not getattr(self, field) or not getattr(self, field).strip():
                return False
        return True


@dataclass_json
@dataclass
class HumanFeedback:
    """Human expert feedback data."""
    decision: str
    rationale: str
    suggestion: str
    
    def validate(self) -> bool:
        """Validate the human feedback data."""
        required_fields = ['decision', 'rationale', 'suggestion']
        for field in required_fields:
            if not getattr(self, field) or not getattr(self, field).strip():
                return False
        return True


@dataclass_json
@dataclass
class STMEntry:
    """
    Short-Term Memory entry representing a detailed case file.
    
    Stores complete information about a compliance assessment interaction
    including initial assessment, human feedback, and final status.
    """
    scenario_id: str
    requirement_text: str
    initial_assessment: InitialAssessment
    human_feedback: HumanFeedback
    final_status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        """Set timestamps if not provided."""
        current_time = datetime.utcnow().isoformat() + 'Z'
        if self.created_at is None:
            self.created_at = current_time
        if self.updated_at is None:
            self.updated_at = current_time
    
    def validate(self) -> bool:
        """
        Validate the STM entry data completeness and format.
        
        Returns:
            bool: True if all required fields are present and valid
        """
        # Check required string fields
        required_fields = ['scenario_id', 'requirement_text', 'final_status']
        for field in required_fields:
            if not getattr(self, field) or not getattr(self, field).strip():
                return False
        
        # Validate nested objects
        if not self.initial_assessment.validate():
            return False
        
        if not self.human_feedback.validate():
            return False
        
        # Validate scenario_id format: {domain}_{requirement_number}_{key_concept}
        parts = self.scenario_id.split('_')
        if len(parts) < 3:
            return False
        
        return True
    
    def to_json(self) -> str:
        """
        Serialize STM entry to JSON string.
        
        Returns:
            str: JSON representation of the STM entry
        """
        return self.to_json()
    
    @classmethod
    def from_json(cls, json_str: str) -> 'STMEntry':
        """
        Deserialize STM entry from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            STMEntry: Deserialized STM entry object
        """
        return cls.from_json(json_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert STM entry to dictionary.
        
        Returns:
            Dict: Dictionary representation of the STM entry
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'STMEntry':
        """
        Create STM entry from dictionary.
        
        Args:
            data: Dictionary containing STM entry data
            
        Returns:
            STMEntry: STM entry object
        """
        # Convert nested dictionaries to dataclass objects
        if 'initial_assessment' in data and isinstance(data['initial_assessment'], dict):
            data['initial_assessment'] = InitialAssessment(**data['initial_assessment'])
        
        if 'human_feedback' in data and isinstance(data['human_feedback'], dict):
            data['human_feedback'] = HumanFeedback(**data['human_feedback'])
        
        return cls(**data)
    
    def update_timestamp(self):
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow().isoformat() + 'Z'