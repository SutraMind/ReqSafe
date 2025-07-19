"""LLM-powered scenario ID generation system."""

import json
import logging
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..llm.client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class ScenarioIdComponents:
    """Components extracted for scenario ID generation."""
    domain: str
    requirement_number: str
    key_concept: str
    confidence: float


class ScenarioIdGenerator:
    """
    LLM-powered generator for unique, human-readable scenario IDs.
    
    Generates scenario IDs in the format: {domain}_{requirement_number}_{key_concept}
    Uses Ollama LLM to extract key concepts from requirement text.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the scenario ID generator.
        
        Args:
            llm_client: Optional LLM client instance. If None, creates a new one.
        """
        self.llm_client = llm_client or LLMClient()
        self._generated_ids = set()  # Track generated IDs for uniqueness
    
    def generate_scenario_id(self, 
                           requirement_text: str, 
                           domain: Optional[str] = None,
                           requirement_number: Optional[str] = None) -> str:
        """
        Generate a unique scenario ID from requirement text.
        
        Args:
            requirement_text: The requirement text to analyze
            domain: Optional domain override (if not provided, will be extracted)
            requirement_number: Optional requirement number override
            
        Returns:
            Generated scenario ID in format: {domain}_{requirement_number}_{key_concept}
            
        Raises:
            ValueError: If ID generation fails or produces invalid format
        """
        try:
            # Extract components using LLM
            components = self._extract_id_components(
                requirement_text, 
                domain, 
                requirement_number
            )
            
            # Generate base ID
            base_id = f"{components.domain}_{components.requirement_number}_{components.key_concept}"
            
            # Ensure uniqueness
            unique_id = self._ensure_uniqueness(base_id)
            
            # Validate format
            if not self._validate_id_format(unique_id):
                raise ValueError(f"Generated ID '{unique_id}' does not match expected format")
            
            # Track generated ID
            self._generated_ids.add(unique_id)
            
            logger.info(f"Generated scenario ID: {unique_id}")
            return unique_id
            
        except Exception as e:
            logger.error(f"Failed to generate scenario ID: {str(e)}")
            raise ValueError(f"Scenario ID generation failed: {str(e)}")
    
    def _extract_id_components(self, 
                              requirement_text: str,
                              domain_override: Optional[str] = None,
                              req_num_override: Optional[str] = None) -> ScenarioIdComponents:
        """
        Extract ID components using LLM analysis.
        
        Args:
            requirement_text: Text to analyze
            domain_override: Optional domain override
            req_num_override: Optional requirement number override
            
        Returns:
            ScenarioIdComponents with extracted values
        """
        system_prompt = """You are an expert at analyzing compliance requirements and extracting key information for ID generation. 
Your task is to analyze requirement text and extract:
1. Domain: The business/technical domain (e.g., ecommerce, healthcare, finance)
2. Requirement number: The requirement identifier (e.g., r1, r2, req1, requirement_1)
3. Key concept: The main concept being addressed (e.g., consent, authentication, encryption)

Guidelines:
- Domain should be lowercase, single word or hyphenated
- Requirement number should be in format 'r' + number (e.g., r1, r2, r10)
- Key concept should be lowercase, single word or underscored
- All components should be suitable for use in identifiers (no spaces, special chars except underscore/hyphen)"""

        prompt = f"""Analyze this compliance requirement text and extract components for scenario ID generation:

REQUIREMENT TEXT:
{requirement_text}

Extract the following components:
- domain: The business/technical domain this requirement applies to
- requirement_number: The requirement identifier (format: r + number)
- key_concept: The main concept or topic being addressed

Respond with valid JSON only."""

        expected_schema = {
            "domain": "string",
            "requirement_number": "string", 
            "key_concept": "string",
            "confidence": "float"
        }
        
        response = self.llm_client.extract_structured_data(
            prompt=prompt,
            expected_schema=expected_schema,
            system_prompt=system_prompt,
            model='qwq:32b'
        )
        
        if not response.success:
            raise ValueError(f"LLM extraction failed: {response.error}")
        
        try:
            data = json.loads(response.content)
            
            # Apply overrides if provided
            domain = domain_override or data.get('domain', 'unknown')
            req_num = req_num_override or data.get('requirement_number', 'r1')
            key_concept = data.get('key_concept', 'general')
            confidence = data.get('confidence', 0.5)
            
            # Clean and validate components
            domain = self._clean_component(domain)
            req_num = self._clean_requirement_number(req_num)
            key_concept = self._clean_component(key_concept)
            
            return ScenarioIdComponents(
                domain=domain,
                requirement_number=req_num,
                key_concept=key_concept,
                confidence=confidence
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {response.content}")
            raise ValueError(f"Invalid LLM response format: {str(e)}")
    
    def _clean_component(self, component: str) -> str:
        """
        Clean a component to be suitable for ID generation.
        
        Args:
            component: Raw component string
            
        Returns:
            Cleaned component suitable for IDs
        """
        if not component:
            return "unknown"
        
        # Convert to lowercase
        cleaned = component.lower().strip()
        
        # Replace spaces and hyphens with underscores first
        cleaned = re.sub(r'[\s-]', '_', cleaned)
        
        # Replace any other special chars with underscores
        cleaned = re.sub(r'[^a-z0-9_]', '_', cleaned)
        
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        # Ensure not empty
        if not cleaned:
            return "unknown"
        
        # Limit length
        if len(cleaned) > 20:
            cleaned = cleaned[:20].rstrip('_')
        
        return cleaned
    
    def _clean_requirement_number(self, req_num: str) -> str:
        """
        Clean and format requirement number.
        
        Args:
            req_num: Raw requirement number
            
        Returns:
            Cleaned requirement number in format 'r{number}'
        """
        if not req_num:
            return "r1"
        
        # Extract number from various formats
        match = re.search(r'(\d+)', str(req_num))
        if match:
            number = match.group(1)
            return f"r{number}"
        
        return "r1"
    
    def _ensure_uniqueness(self, base_id: str) -> str:
        """
        Ensure the generated ID is unique by adding suffix if needed.
        
        Args:
            base_id: Base scenario ID
            
        Returns:
            Unique scenario ID
        """
        if base_id not in self._generated_ids:
            return base_id
        
        # Add numeric suffix to ensure uniqueness
        counter = 1
        while f"{base_id}_{counter}" in self._generated_ids:
            counter += 1
        
        return f"{base_id}_{counter}"
    
    def _validate_id_format(self, scenario_id: str) -> bool:
        """
        Validate that the scenario ID matches expected format.
        
        Args:
            scenario_id: ID to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        # Expected format: {domain}_{requirement_number}_{key_concept}[_{suffix}]
        pattern = r'^[a-z][a-z0-9_]*_r\d+_[a-z][a-z0-9_]*(?:_\d+)?$'
        return bool(re.match(pattern, scenario_id))
    
    def reset_generated_ids(self):
        """Reset the set of generated IDs for testing purposes."""
        self._generated_ids.clear()
    
    def get_generated_ids(self) -> set:
        """Get the set of generated IDs for testing purposes."""
        return self._generated_ids.copy()