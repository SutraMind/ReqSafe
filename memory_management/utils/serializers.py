"""
JSON serialization utilities for the memory management system.
"""

import json
from typing import Dict, Any, Union
from ..models import STMEntry, LTMRule


class JSONSerializer:
    """Handles JSON serialization and deserialization for memory objects."""
    
    @staticmethod
    def serialize_stm_entry(entry: STMEntry) -> str:
        """
        Serialize STM entry to JSON string.
        
        Args:
            entry: STM entry to serialize
            
        Returns:
            str: JSON string representation
        """
        try:
            return json.dumps(entry.to_dict(), indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"Failed to serialize STM entry: {str(e)}")
    
    @staticmethod
    def deserialize_stm_entry(json_str: str) -> STMEntry:
        """
        Deserialize STM entry from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            STMEntry: Deserialized STM entry
        """
        try:
            data = json.loads(json_str)
            return STMEntry.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize STM entry: {str(e)}")
    
    @staticmethod
    def serialize_ltm_rule(rule: LTMRule) -> str:
        """
        Serialize LTM rule to JSON string.
        
        Args:
            rule: LTM rule to serialize
            
        Returns:
            str: JSON string representation
        """
        try:
            return json.dumps(rule.to_dict(), indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"Failed to serialize LTM rule: {str(e)}")
    
    @staticmethod
    def deserialize_ltm_rule(json_str: str) -> LTMRule:
        """
        Deserialize LTM rule from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            LTMRule: Deserialized LTM rule
        """
        try:
            data = json.loads(json_str)
            return LTMRule.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize LTM rule: {str(e)}")
    
    @staticmethod
    def serialize_dict(data: Dict[str, Any]) -> str:
        """
        Serialize dictionary to JSON string.
        
        Args:
            data: Dictionary to serialize
            
        Returns:
            str: JSON string representation
        """
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"Failed to serialize dictionary: {str(e)}")
    
    @staticmethod
    def deserialize_dict(json_str: str) -> Dict[str, Any]:
        """
        Deserialize dictionary from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            Dict: Deserialized dictionary
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize dictionary: {str(e)}")