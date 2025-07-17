"""
Long-Term Memory (LTM) Rule data model.

Represents generalizable knowledge rules extracted from expert feedback.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class LTMRule:
    """
    Long-Term Memory rule representing generalizable compliance knowledge.
    
    Stores reusable patterns and principles extracted from human expert feedback
    that can be applied to future compliance assessments.
    """
    rule_id: str
    rule_text: str
    related_concepts: List[str]
    source_scenario_id: List[str]
    confidence_score: float = 0.0
    version: int = 1
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
        Validate the LTM rule data completeness and format.
        
        Returns:
            bool: True if all required fields are present and valid
        """
        # Check required string fields
        if not self.rule_id or not self.rule_id.strip():
            return False
        
        if not self.rule_text or not self.rule_text.strip():
            return False
        
        # Validate rule_id format: {policy}_{concept}_{version}
        parts = self.rule_id.split('_')
        if len(parts) < 3:
            return False
        
        # Check that related_concepts is not empty
        if not self.related_concepts or len(self.related_concepts) == 0:
            return False
        
        # Check that source_scenario_id is not empty
        if not self.source_scenario_id or len(self.source_scenario_id) == 0:
            return False
        
        # Validate confidence score range
        if not (0.0 <= self.confidence_score <= 1.0):
            return False
        
        # Validate version is positive
        if self.version < 1:
            return False
        
        return True
    
    def to_json(self) -> str:
        """
        Serialize LTM rule to JSON string.
        
        Returns:
            str: JSON representation of the LTM rule
        """
        return self.to_json()
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LTMRule':
        """
        Deserialize LTM rule from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            LTMRule: Deserialized LTM rule object
        """
        return cls.from_json(json_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert LTM rule to dictionary.
        
        Returns:
            Dict: Dictionary representation of the LTM rule
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LTMRule':
        """
        Create LTM rule from dictionary.
        
        Args:
            data: Dictionary containing LTM rule data
            
        Returns:
            LTMRule: LTM rule object
        """
        return cls(**data)
    
    def update_timestamp(self):
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow().isoformat() + 'Z'
    
    def add_source_scenario(self, scenario_id: str):
        """
        Add a source scenario ID to the rule.
        
        Args:
            scenario_id: ID of the scenario that contributed to this rule
        """
        if scenario_id not in self.source_scenario_id:
            self.source_scenario_id.append(scenario_id)
            self.update_timestamp()
    
    def add_related_concept(self, concept: str):
        """
        Add a related concept to the rule.
        
        Args:
            concept: Concept to add to the related concepts list
        """
        if concept not in self.related_concepts:
            self.related_concepts.append(concept)
            self.update_timestamp()
    
    def increment_version(self):
        """Increment the rule version and update timestamp."""
        self.version += 1
        self.update_timestamp()