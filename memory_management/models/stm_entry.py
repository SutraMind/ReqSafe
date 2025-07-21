"""
STM (Short-Term Memory) Entry data model for immediate memory operations.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class InitialAssessment:
    """Initial assessment data from RA_Agent."""
    status: str
    rationale: str
    recommendation: str
    
    def validate(self) -> bool:
        """Validate initial assessment data."""
        return (bool(self.status and self.status.strip()) and
                bool(self.rationale and self.rationale.strip()) and
                bool(self.recommendation and self.recommendation.strip()))


@dataclass
class HumanFeedback:
    """Human expert feedback data."""
    decision: str
    rationale: str
    suggestion: str
    
    def validate(self) -> bool:
        """Validate human feedback data."""
        return (bool(self.decision and self.decision.strip()) and
                bool(self.rationale and self.rationale.strip()) and
                bool(self.suggestion and self.suggestion.strip()))


@dataclass
class STMEntry:
    """
    Data model for Short-Term Memory entries storing detailed case files.
    
    Based on design specification schema:
    {
      "scenario_id": "ecommerce_r1_consent",
      "requirement_text": "During account signup, the user must agree...",
      "initial_assessment": {
        "status": "Non-Compliant",
        "rationale": "Bundled consent violates GDPR Art. 7...",
        "recommendation": "Implement separate, unticked opt-in checkboxes..."
      },
      "human_feedback": {
        "decision": "No change",
        "rationale": "Agent's analysis is correct...",
        "suggestion": "Implement separate, unticked opt-in checkboxes..."
      },
      "final_status": "Non-Compliant",
      "created_at": "2024-10-27T10:30:00Z",
      "updated_at": "2024-10-27T11:15:00Z"
    }
    """
    scenario_id: str
    requirement_text: str
    initial_assessment: InitialAssessment
    human_feedback: Optional[HumanFeedback] = None
    final_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert STM entry to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO string for JSON serialization
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert STM entry to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'STMEntry':
        """Create STM entry from dictionary."""
        # Convert ISO strings back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Convert nested objects
        if 'initial_assessment' in data and isinstance(data['initial_assessment'], dict):
            data['initial_assessment'] = InitialAssessment(**data['initial_assessment'])
        if 'human_feedback' in data and isinstance(data['human_feedback'], dict):
            data['human_feedback'] = HumanFeedback(**data['human_feedback'])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'STMEntry':
        """Create STM entry from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> bool:
        """Validate STM entry data."""
        # Check required fields
        if not self.scenario_id or not self.requirement_text:
            return False
        
        if not self.initial_assessment:
            return False
        
        # Validate initial assessment status
        valid_statuses = ['Compliant', 'Non-Compliant', 'Partial', 'Pending']
        if self.initial_assessment.status not in valid_statuses:
            return False
        
        # Validate final status if present
        if self.final_status and self.final_status not in valid_statuses:
            return False
        
        return True
    
    def update_with_feedback(self, decision: str, rationale: str, suggestion: str) -> None:
        """Update entry with human feedback."""
        self.human_feedback = HumanFeedback(
            decision=decision,
            rationale=rationale,
            suggestion=suggestion
        )
        self.updated_at = datetime.utcnow()
    
    def set_final_status(self, status: str) -> None:
        """Set the final compliance status."""
        valid_statuses = ['Compliant', 'Non-Compliant', 'Partial', 'Pending']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        self.final_status = status
        self.updated_at = datetime.utcnow()