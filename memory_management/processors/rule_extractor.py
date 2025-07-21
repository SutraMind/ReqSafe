"""
Rule Extractor for generating Long-Term Memory rules from human feedback.

This module uses LLM to analyze human expert feedback and extract reusable
compliance rules that can be applied to future assessments.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..models.stm_entry import STMEntry
from ..models.ltm_rule import LTMRule
from ..llm.client import LLMClient
from ..llm.prompts import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class RuleGenerationResult:
    """Result of rule generation process."""
    success: bool
    rule: Optional[LTMRule] = None
    error: Optional[str] = None
    confidence_score: float = 0.0


class RuleExtractor:
    """
    Extracts generalizable compliance rules from human expert feedback using LLM.
    
    This class analyzes STM entries containing human feedback and generates
    reusable LTM rules that can be applied to similar compliance scenarios.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the rule extractor.
        
        Args:
            llm_client: Optional LLM client instance. If None, creates a new one.
        """
        self.llm_client = llm_client or LLMClient()
        self.prompt_templates = PromptTemplates()
    
    def extract_rule_from_stm(self, stm_entry: STMEntry) -> RuleGenerationResult:
        """
        Extract a generalizable rule from an STM entry with human feedback.
        
        Args:
            stm_entry: STM entry containing human expert feedback
            
        Returns:
            RuleGenerationResult with the generated rule or error information
        """
        if not stm_entry.human_feedback:
            return RuleGenerationResult(
                success=False,
                error="STM entry must contain human feedback to generate rules"
            )
        
        try:
            # Generate the rule using LLM
            rule_data = self._generate_rule_with_llm(stm_entry)
            
            if not rule_data:
                return RuleGenerationResult(
                    success=False,
                    error="Failed to generate rule data from LLM"
                )
            
            # Create LTM rule object
            rule = self._create_ltm_rule(stm_entry, rule_data)
            
            if not rule.validate():
                return RuleGenerationResult(
                    success=False,
                    error="Generated rule failed validation"
                )
            
            return RuleGenerationResult(
                success=True,
                rule=rule,
                confidence_score=rule.confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error extracting rule from STM entry {stm_entry.scenario_id}: {str(e)}")
            return RuleGenerationResult(
                success=False,
                error=f"Rule extraction failed: {str(e)}"
            )
    
    def _generate_rule_with_llm(self, stm_entry: STMEntry) -> Optional[Dict[str, Any]]:
        """
        Use LLM to generate rule data from STM entry.
        
        Args:
            stm_entry: STM entry with human feedback
            
        Returns:
            Dictionary containing rule data or None if generation failed
        """
        # Get the prompt template for LTM rule generation
        template_data = self.prompt_templates.ltm_rule_generation()
        
        # Format the prompt with STM entry data
        prompt = template_data["template"].format(
            requirement_text=stm_entry.requirement_text,
            initial_assessment=self._format_initial_assessment(stm_entry.initial_assessment),
            human_feedback=self._format_human_feedback(stm_entry.human_feedback)
        )
        
        # Get system prompt for rule generation
        system_prompts = self.prompt_templates.get_system_prompts()
        system_prompt = system_prompts.get("rule_generation")
        
        # Call LLM to extract structured rule data
        response = self.llm_client.extract_structured_data(
            prompt=prompt,
            expected_schema=template_data["schema"],
            model='qwq:32b',  # Use reasoning model for rule generation
            system_prompt=system_prompt
        )
        
        if not response.success:
            logger.error(f"LLM rule generation failed: {response.error}")
            return None
        
        try:
            import json
            rule_data = json.loads(response.content)
            return rule_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            return None
    
    def _create_ltm_rule(self, stm_entry: STMEntry, rule_data: Dict[str, Any]) -> LTMRule:
        """
        Create LTM rule object from STM entry and LLM-generated rule data.
        
        Args:
            stm_entry: Source STM entry
            rule_data: Rule data from LLM
            
        Returns:
            LTMRule object
        """
        # Generate rule ID based on policy area and key concept
        policy_area = rule_data.get("policy_area", "GDPR")
        key_concept = self._extract_key_concept(rule_data.get("related_concepts", []))
        rule_id = f"{policy_area}_{key_concept}_01"
        
        # Create LTM rule
        rule = LTMRule(
            rule_id=rule_id,
            rule_text=rule_data.get("rule_text", ""),
            related_concepts=rule_data.get("related_concepts", []),
            source_scenario_id=[stm_entry.scenario_id],
            confidence_score=rule_data.get("confidence_score", 0.8),
            version=1
        )
        
        return rule
    
    def _extract_key_concept(self, concepts: List[str]) -> str:
        """
        Extract the primary concept for rule ID generation.
        
        Args:
            concepts: List of related concepts
            
        Returns:
            Primary concept string formatted for ID
        """
        if not concepts:
            return "general"
        
        # Take the first concept and format it for ID
        key_concept = concepts[0].lower().replace(" ", "_").replace("-", "_")
        # Remove special characters and limit length
        key_concept = "".join(c for c in key_concept if c.isalnum() or c == "_")
        return key_concept[:20]  # Limit length
    
    def _format_initial_assessment(self, assessment) -> str:
        """
        Format initial assessment for LLM prompt.
        
        Args:
            assessment: InitialAssessment object
            
        Returns:
            Formatted string
        """
        return f"""Status: {assessment.status}
Rationale: {assessment.rationale}
Recommendation: {assessment.recommendation}"""
    
    def _format_human_feedback(self, feedback) -> str:
        """
        Format human feedback for LLM prompt.
        
        Args:
            feedback: HumanFeedback object
            
        Returns:
            Formatted string
        """
        return f"""Decision: {feedback.decision}
Rationale: {feedback.rationale}
Suggestion: {feedback.suggestion}"""
    
    def extract_concepts_from_text(self, text: str) -> List[str]:
        """
        Extract related concepts from text for rule indexing.
        
        Args:
            text: Text to extract concepts from
            
        Returns:
            List of extracted concepts
        """
        try:
            # Get concept extraction template
            template_data = self.prompt_templates.concept_extraction()
            
            # Format prompt
            prompt = template_data["template"].format(text=text)
            
            # Get system prompt
            system_prompts = self.prompt_templates.get_system_prompts()
            system_prompt = system_prompts.get("concept_extraction")
            
            # Call LLM
            response = self.llm_client.extract_structured_data(
                prompt=prompt,
                expected_schema=template_data["schema"],
                model='gemma3:27b',  # Use efficient model for concept extraction
                system_prompt=system_prompt
            )
            
            if not response.success:
                logger.warning(f"Concept extraction failed: {response.error}")
                return []
            
            import json
            concept_data = json.loads(response.content)
            concepts = concept_data.get("concepts", [])
            
            # Extract just the terms, sorted by relevance
            extracted_concepts = []
            for concept in concepts:
                if isinstance(concept, dict) and "term" in concept:
                    extracted_concepts.append(concept["term"])
                elif isinstance(concept, str):
                    extracted_concepts.append(concept)
            
            return extracted_concepts[:10]  # Limit to top 10 concepts
            
        except Exception as e:
            logger.error(f"Error extracting concepts: {str(e)}")
            return []
    
    def generate_multiple_rules(self, stm_entries: List[STMEntry]) -> List[RuleGenerationResult]:
        """
        Generate rules from multiple STM entries.
        
        Args:
            stm_entries: List of STM entries with human feedback
            
        Returns:
            List of rule generation results
        """
        results = []
        
        for stm_entry in stm_entries:
            if stm_entry.human_feedback:
                result = self.extract_rule_from_stm(stm_entry)
                results.append(result)
            else:
                logger.warning(f"Skipping STM entry {stm_entry.scenario_id} - no human feedback")
        
        return results
    
    def validate_rule_quality(self, rule: LTMRule) -> Dict[str, Any]:
        """
        Validate the quality of a generated rule.
        
        Args:
            rule: LTM rule to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "quality_score": 0.0
        }
        
        # Check rule text quality
        if len(rule.rule_text) < 20:
            validation_result["issues"].append("Rule text is too short")
            validation_result["is_valid"] = False
        
        if len(rule.rule_text) > 500:
            validation_result["issues"].append("Rule text is too long")
        
        # Check concepts quality
        if len(rule.related_concepts) < 2:
            validation_result["issues"].append("Too few related concepts")
        
        if len(rule.related_concepts) > 15:
            validation_result["issues"].append("Too many related concepts")
        
        # Check confidence score
        if rule.confidence_score < 0.5:
            validation_result["issues"].append("Low confidence score")
        
        # Calculate quality score
        quality_factors = []
        quality_factors.append(min(len(rule.rule_text) / 100, 1.0))  # Text length factor
        quality_factors.append(min(len(rule.related_concepts) / 5, 1.0))  # Concepts factor
        quality_factors.append(rule.confidence_score)  # Confidence factor
        
        validation_result["quality_score"] = sum(quality_factors) / len(quality_factors)
        
        return validation_result