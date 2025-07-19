"""LLM-based compliance report parser for extracting structured data."""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..llm.client import LLMClient, LLMResponse
from ..llm.prompts import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class ComplianceRequirement:
    """Structured representation of a compliance requirement."""
    requirement_number: str
    requirement_text: str
    status: str
    rationale: str
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'requirement_number': self.requirement_number,
            'requirement_text': self.requirement_text,
            'status': self.status,
            'rationale': self.rationale,
            'recommendation': self.recommendation
        }


@dataclass
class ParsedComplianceReport:
    """Container for parsed compliance report data."""
    requirements: List[ComplianceRequirement]
    raw_text: str
    parsing_success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'requirements': [req.to_dict() for req in self.requirements],
            'raw_text': self.raw_text,
            'parsing_success': self.parsing_success,
            'error_message': self.error_message
        }


class ComplianceReportParser:
    """LLM-based parser for compliance reports."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, model: str = 'qwq:32b'):
        """
        Initialize the compliance report parser.
        
        Args:
            llm_client: Optional LLM client instance
            model: Model to use for parsing
        """
        self.llm_client = llm_client or LLMClient()
        self.model = model
        self.prompt_templates = PromptTemplates()
    
    def parse_report_file(self, file_path: str) -> ParsedComplianceReport:
        """
        Parse a compliance report from a file.
        
        Args:
            file_path: Path to the compliance report file
            
        Returns:
            ParsedComplianceReport with extracted data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                report_text = file.read()
            
            return self.parse_report_text(report_text)
            
        except FileNotFoundError:
            logger.error(f"Compliance report file not found: {file_path}")
            return ParsedComplianceReport(
                requirements=[],
                raw_text="",
                parsing_success=False,
                error_message=f"File not found: {file_path}"
            )
        except Exception as e:
            logger.error(f"Error reading compliance report file: {str(e)}")
            return ParsedComplianceReport(
                requirements=[],
                raw_text="",
                parsing_success=False,
                error_message=f"File reading error: {str(e)}"
            )
    
    def parse_report_text(self, report_text: str) -> ParsedComplianceReport:
        """
        Parse compliance report from text content.
        
        Args:
            report_text: Raw compliance report text
            
        Returns:
            ParsedComplianceReport with extracted data
        """
        if not report_text.strip():
            return ParsedComplianceReport(
                requirements=[],
                raw_text=report_text,
                parsing_success=False,
                error_message="Empty report text provided"
            )
        
        try:
            # Get prompt template and schema
            template_data = self.prompt_templates.compliance_report_extraction()
            prompt = template_data["template"].format(report_text=report_text)
            schema = template_data["schema"]
            system_prompt = self.prompt_templates.get_system_prompts()["compliance_extraction"]
            
            # Extract structured data using LLM
            logger.info("Extracting compliance requirements using LLM")
            response = self.llm_client.extract_structured_data(
                prompt=prompt,
                expected_schema=schema,
                model=self.model,
                system_prompt=system_prompt
            )
            
            if not response.success:
                logger.error(f"LLM extraction failed: {response.error}")
                return ParsedComplianceReport(
                    requirements=[],
                    raw_text=report_text,
                    parsing_success=False,
                    error_message=f"LLM extraction failed: {response.error}"
                )
            
            # Parse the JSON response
            try:
                parsed_data = json.loads(response.content)
                requirements = self._convert_to_requirements(parsed_data.get('requirements', []))
                
                logger.info(f"Successfully parsed {len(requirements)} requirements")
                return ParsedComplianceReport(
                    requirements=requirements,
                    raw_text=report_text,
                    parsing_success=True
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {str(e)}")
                return ParsedComplianceReport(
                    requirements=[],
                    raw_text=report_text,
                    parsing_success=False,
                    error_message=f"JSON parsing error: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Unexpected error during compliance report parsing: {str(e)}")
            return ParsedComplianceReport(
                requirements=[],
                raw_text=report_text,
                parsing_success=False,
                error_message=f"Parsing error: {str(e)}"
            )
    
    def _convert_to_requirements(self, requirements_data: List[Dict[str, Any]]) -> List[ComplianceRequirement]:
        """
        Convert parsed JSON data to ComplianceRequirement objects.
        
        Args:
            requirements_data: List of requirement dictionaries from LLM
            
        Returns:
            List of ComplianceRequirement objects
        """
        requirements = []
        
        for req_data in requirements_data:
            try:
                requirement = ComplianceRequirement(
                    requirement_number=str(req_data.get('requirement_number', '')).strip(),
                    requirement_text=str(req_data.get('requirement_text', '')).strip(),
                    status=str(req_data.get('status', '')).strip(),
                    rationale=str(req_data.get('rationale', '')).strip(),
                    recommendation=str(req_data.get('recommendation', '')).strip()
                )
                
                # Validate that required fields are not empty
                if not requirement.requirement_number or not requirement.requirement_text:
                    logger.warning(f"Skipping requirement with missing required fields: {req_data}")
                    continue
                
                requirements.append(requirement)
                
            except Exception as e:
                logger.warning(f"Error converting requirement data: {str(e)}, data: {req_data}")
                continue
        
        return requirements
    
    def validate_parsed_data(self, parsed_report: ParsedComplianceReport) -> Dict[str, Any]:
        """
        Validate the parsed compliance report data.
        
        Args:
            parsed_report: Parsed compliance report to validate
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {
                'total_requirements': len(parsed_report.requirements),
                'compliant_count': 0,
                'non_compliant_count': 0,
                'partially_compliant_count': 0,
                'other_status_count': 0
            }
        }
        
        if not parsed_report.parsing_success:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Parsing failed: {parsed_report.error_message}")
            return validation_results
        
        if not parsed_report.requirements:
            validation_results['is_valid'] = False
            validation_results['errors'].append("No requirements found in the report")
            return validation_results
        
        # Validate individual requirements
        for i, req in enumerate(parsed_report.requirements):
            req_errors = []
            
            # Check required fields
            if not req.requirement_number:
                req_errors.append("Missing requirement number")
            if not req.requirement_text:
                req_errors.append("Missing requirement text")
            if not req.status:
                req_errors.append("Missing status")
            if not req.rationale:
                req_errors.append("Missing rationale")
            
            # Count status types
            status_lower = req.status.lower()
            if 'compliant' in status_lower and 'non' not in status_lower and 'partial' not in status_lower:
                validation_results['statistics']['compliant_count'] += 1
            elif 'non-compliant' in status_lower or 'non compliant' in status_lower:
                validation_results['statistics']['non_compliant_count'] += 1
            elif 'partial' in status_lower:
                validation_results['statistics']['partially_compliant_count'] += 1
            else:
                validation_results['statistics']['other_status_count'] += 1
            
            if req_errors:
                validation_results['errors'].extend([f"Requirement {req.requirement_number}: {error}" for error in req_errors])
                validation_results['is_valid'] = False
        
        # Check for duplicate requirement numbers
        req_numbers = [req.requirement_number for req in parsed_report.requirements]
        duplicates = set([num for num in req_numbers if req_numbers.count(num) > 1])
        if duplicates:
            validation_results['warnings'].append(f"Duplicate requirement numbers found: {list(duplicates)}")
        
        return validation_results
    
    def get_requirements_by_status(self, parsed_report: ParsedComplianceReport, status: str) -> List[ComplianceRequirement]:
        """
        Filter requirements by compliance status.
        
        Args:
            parsed_report: Parsed compliance report
            status: Status to filter by (case-insensitive)
            
        Returns:
            List of requirements matching the status
        """
        status_lower = status.lower()
        return [
            req for req in parsed_report.requirements 
            if status_lower in req.status.lower()
        ]
    
    def get_parsing_statistics(self, parsed_report: ParsedComplianceReport) -> Dict[str, Any]:
        """
        Get statistics about the parsed report.
        
        Args:
            parsed_report: Parsed compliance report
            
        Returns:
            Dictionary with parsing statistics
        """
        if not parsed_report.parsing_success:
            return {
                'parsing_success': False,
                'error': parsed_report.error_message,
                'total_requirements': 0
            }
        
        status_counts = {}
        for req in parsed_report.requirements:
            status = req.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'parsing_success': True,
            'total_requirements': len(parsed_report.requirements),
            'status_distribution': status_counts,
            'has_recommendations': sum(1 for req in parsed_report.requirements if req.recommendation.strip()),
            'average_text_length': sum(len(req.requirement_text) for req in parsed_report.requirements) / len(parsed_report.requirements) if parsed_report.requirements else 0
        }