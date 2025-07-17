"""Prompt templates for structured data extraction."""

from typing import Dict, Any


class PromptTemplates:
    """Collection of prompt templates for different data extraction tasks."""
    
    @staticmethod
    def compliance_report_extraction() -> Dict[str, Any]:
        """
        Template for extracting data from compliance reports.
        
        Returns:
            Dictionary with prompt template and expected schema
        """
        prompt_template = """
Extract structured information from the following compliance report text.
Focus on identifying requirements, their assessment status, rationale, and recommendations.

Compliance Report Text:
{report_text}

Extract the following information for each requirement found:
- requirement_number: The requirement identifier (e.g., R1, R2, etc.)
- requirement_text: The full text describing what needs to be compliant
- status: The compliance status (Compliant, Non-Compliant, Partially Compliant, etc.)
- rationale: The reasoning behind the assessment
- recommendation: Suggested actions to achieve compliance

If multiple requirements are present, extract all of them.
"""
        
        expected_schema = {
            "requirements": [
                {
                    "requirement_number": "string",
                    "requirement_text": "string", 
                    "status": "string",
                    "rationale": "string",
                    "recommendation": "string"
                }
            ]
        }
        
        return {
            "template": prompt_template,
            "schema": expected_schema
        }
    
    @staticmethod
    def human_feedback_extraction() -> Dict[str, Any]:
        """
        Template for extracting data from human feedback text.
        
        Returns:
            Dictionary with prompt template and expected schema
        """
        prompt_template = """
Extract structured information from the following human expert feedback text.
Focus on identifying the expert's decisions, rationale, and refined suggestions.

Human Feedback Text:
{feedback_text}

Extract the following information for each feedback item:
- requirement_reference: Which requirement this feedback relates to (e.g., R1, R2, etc.)
- decision: The expert's decision (Accept, Reject, Modify, etc.)
- rationale: The expert's reasoning for their decision
- suggestion: Any refined or additional suggestions from the expert
- confidence: Expert's confidence level if mentioned

If multiple feedback items are present, extract all of them.
"""
        
        expected_schema = {
            "feedback_items": [
                {
                    "requirement_reference": "string",
                    "decision": "string",
                    "rationale": "string", 
                    "suggestion": "string",
                    "confidence": "string"
                }
            ]
        }
        
        return {
            "template": prompt_template,
            "schema": expected_schema
        }
    
    @staticmethod
    def scenario_id_generation() -> Dict[str, Any]:
        """
        Template for generating scenario IDs from requirement text.
        
        Returns:
            Dictionary with prompt template and expected schema
        """
        prompt_template = """
Generate a unique scenario ID for the following requirement text.
The ID should follow the format: {{domain}}_{{requirement_number}}_{{key_concept}}

Where:
- domain: The main domain/area (e.g., ecommerce, healthcare, finance)
- requirement_number: The requirement identifier (e.g., r1, r2)
- key_concept: A short, descriptive concept (e.g., consent, encryption, authentication)

Requirement Text:
{requirement_text}

Requirement Number: {requirement_number}

Generate a scenario ID that is:
- Human-readable and descriptive
- Uses lowercase with underscores
- Captures the essence of the requirement
- Unique and specific to this requirement
"""
        
        expected_schema = {
            "scenario_id": "string",
            "domain": "string",
            "requirement_number": "string", 
            "key_concept": "string",
            "explanation": "string"
        }
        
        return {
            "template": prompt_template,
            "schema": expected_schema
        }
    
    @staticmethod
    def ltm_rule_generation() -> Dict[str, Any]:
        """
        Template for generating LTM rules from human feedback.
        
        Returns:
            Dictionary with prompt template and expected schema
        """
        prompt_template = """
Analyze the following human expert feedback and generate a reusable compliance rule.
The rule should be generalizable and applicable to similar situations.

Original Requirement:
{requirement_text}

Initial Assessment:
{initial_assessment}

Human Expert Feedback:
{human_feedback}

Generate a Long-Term Memory rule that:
- Captures the expert's knowledge in a reusable format
- Is context-free and can apply to similar situations
- Includes the key concepts for indexing and retrieval
- Has a clear, actionable rule statement

Extract related concepts that would help in future retrieval of this rule.
"""
        
        expected_schema = {
            "rule_text": "string",
            "related_concepts": ["string"],
            "policy_area": "string",
            "confidence_score": "number",
            "applicability": "string"
        }
        
        return {
            "template": prompt_template,
            "schema": expected_schema
        }
    
    @staticmethod
    def concept_extraction() -> Dict[str, Any]:
        """
        Template for extracting concepts from text for indexing.
        
        Returns:
            Dictionary with prompt template and expected schema
        """
        prompt_template = """
Extract key concepts from the following text for indexing and retrieval purposes.
Focus on technical terms, compliance areas, and domain-specific concepts.

Text:
{text}

Extract concepts that are:
- Relevant for compliance and regulatory contexts
- Technical terms and standards
- Domain-specific terminology
- Actionable concepts that could be searched for

Provide both the concepts and their categories (e.g., Technical, Legal, Domain, Process).
"""
        
        expected_schema = {
            "concepts": [
                {
                    "term": "string",
                    "category": "string",
                    "relevance_score": "number"
                }
            ]
        }
        
        return {
            "template": prompt_template,
            "schema": expected_schema
        }
    
    @staticmethod
    def get_system_prompts() -> Dict[str, str]:
        """
        Get system prompts for different extraction tasks.
        
        Returns:
            Dictionary mapping task names to system prompts
        """
        return {
            "compliance_extraction": """You are a compliance analysis expert. Extract structured information from compliance reports with high accuracy. Focus on identifying requirements, their status, and actionable recommendations. Always respond with valid JSON.""",
            
            "feedback_analysis": """You are an expert in analyzing human feedback on compliance assessments. Extract the expert's decisions, reasoning, and suggestions in a structured format. Always respond with valid JSON.""",
            
            "id_generation": """You are a system architect responsible for generating meaningful, unique identifiers. Create scenario IDs that are human-readable, descriptive, and follow the specified format. Always respond with valid JSON.""",
            
            "rule_generation": """You are a knowledge management expert specializing in compliance rules. Generate reusable, generalizable rules from specific expert feedback. Focus on creating context-free rules that can apply broadly. Always respond with valid JSON.""",
            
            "concept_extraction": """You are a knowledge indexing specialist. Extract relevant concepts from text for effective categorization and retrieval. Focus on compliance, technical, and domain-specific terms. Always respond with valid JSON."""
        }