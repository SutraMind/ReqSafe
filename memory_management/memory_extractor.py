"""
Main Memory Extractor Orchestrator.

Coordinates all memory management components to create an end-to-end workflow
from input files to memory storage, generating both STM entries and LTM rules.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

from .parsers.compliance_report_parser import ComplianceReportParser, ParsedComplianceReport
from .parsers.human_feedback_parser import HumanFeedbackParser, ParsedHumanFeedback
from .processors.stm_processor import STMProcessor
from .processors.ltm_manager import LTMManager
from .processors.rule_extractor import RuleExtractor
from .utils.scenario_id_generator import ScenarioIdGenerator
from .models.stm_entry import InitialAssessment
from .utils.validators import DataValidator


class MemoryExtractionError(Exception):
    """Base exception for memory extraction errors."""
    pass


class MemoryExtractor:
    """
    Main orchestrator for memory extraction and storage workflow.
    
    Coordinates parsing, processing, and storage of compliance assessments
    and human feedback to build both STM and LTM knowledge bases.
    """
    
    def __init__(self, 
                 stm_processor: Optional[STMProcessor] = None,
                 ltm_manager: Optional[LTMManager] = None,
                 rule_extractor: Optional[RuleExtractor] = None):
        """
        Initialize the memory extractor with all required components.
        
        Args:
            stm_processor: STM processor instance (creates default if None)
            ltm_manager: LTM manager instance (creates default if None)
            rule_extractor: Rule extractor instance (creates default if None)
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        try:
            self.compliance_parser = ComplianceReportParser()
            self.feedback_parser = HumanFeedbackParser()
            self.scenario_id_generator = ScenarioIdGenerator()
            self.stm_processor = stm_processor or STMProcessor()
            self.ltm_manager = ltm_manager or LTMManager()
            self.rule_extractor = rule_extractor or RuleExtractor()
            
            self.logger.info("Memory extractor initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory extractor: {e}")
            raise MemoryExtractionError(f"Initialization failed: {str(e)}")
    
    def extract_from_files(self, 
                          compliance_report_path: str, 
                          human_feedback_path: str,
                          domain: str = "ecommerce") -> Dict[str, Any]:
        """
        Complete end-to-end workflow from input files to memory storage.
        
        Implements Requirements 5.1, 5.2, 5.5: Process existing compliance 
        reports and feedback files to generate both STM and LTM entries.
        
        Args:
            compliance_report_path: Path to compliance report file
            human_feedback_path: Path to human feedback file
            domain: Domain context for scenario ID generation
            
        Returns:
            Dictionary with extraction results and statistics
        """
        self.logger.info(f"Starting memory extraction from files: {compliance_report_path}, {human_feedback_path}")
        
        try:
            # Step 1: Parse input files
            parsed_report = self._parse_compliance_report(compliance_report_path)
            parsed_feedback = self._parse_human_feedback(human_feedback_path)
            
            # Step 2: Validate parsed data
            self._validate_parsed_data(parsed_report, parsed_feedback)
            
            # Step 3: Map feedback to requirements
            feedback_mapping = self._map_feedback_to_requirements(parsed_report, parsed_feedback)
            
            # Step 4: Generate STM entries
            stm_results = self._generate_stm_entries(parsed_report, feedback_mapping, domain)
            
            # Step 5: Generate LTM rules from feedback
            ltm_results = self._generate_ltm_rules(stm_results['entries'], feedback_mapping)
            
            # Step 6: Create extraction summary
            extraction_summary = self._create_extraction_summary(
                parsed_report, parsed_feedback, stm_results, ltm_results
            )
            
            self.logger.info(f"Memory extraction completed successfully: {extraction_summary['statistics']}")
            
            return {
                'success': True,
                'extraction_summary': extraction_summary,
                'stm_results': stm_results,
                'ltm_results': ltm_results,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            self.logger.error(f"Memory extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
    
    def _parse_compliance_report(self, file_path: str) -> ParsedComplianceReport:
        """Parse compliance report file."""
        self.logger.info(f"Parsing compliance report: {file_path}")
        
        if not Path(file_path).exists():
            raise MemoryExtractionError(f"Compliance report file not found: {file_path}")
        
        parsed_report = self.compliance_parser.parse_report_file(file_path)
        
        if not parsed_report.parsing_success:
            raise MemoryExtractionError(f"Failed to parse compliance report: {parsed_report.error_message}")
        
        self.logger.info(f"Successfully parsed {len(parsed_report.requirements)} requirements")
        return parsed_report
    
    def _parse_human_feedback(self, file_path: str) -> ParsedHumanFeedback:
        """Parse human feedback file."""
        self.logger.info(f"Parsing human feedback: {file_path}")
        
        if not Path(file_path).exists():
            raise MemoryExtractionError(f"Human feedback file not found: {file_path}")
        
        parsed_feedback = self.feedback_parser.parse_feedback_file(file_path)
        
        if not parsed_feedback.parsing_success:
            raise MemoryExtractionError(f"Failed to parse human feedback: {parsed_feedback.error_message}")
        
        self.logger.info(f"Successfully parsed {len(parsed_feedback.feedback_items)} feedback items")
        return parsed_feedback
    
    def _validate_parsed_data(self, 
                             parsed_report: ParsedComplianceReport, 
                             parsed_feedback: ParsedHumanFeedback) -> None:
        """Validate parsed data completeness and format."""
        self.logger.info("Validating parsed data")
        
        # Validate compliance report
        report_validation = self.compliance_parser.validate_parsed_data(parsed_report)
        if not report_validation['is_valid']:
            raise MemoryExtractionError(f"Invalid compliance report data: {report_validation['errors']}")
        
        # Validate human feedback
        feedback_validation = self.feedback_parser.validate_parsed_data(parsed_feedback)
        if not feedback_validation['is_valid']:
            raise MemoryExtractionError(f"Invalid human feedback data: {feedback_validation['errors']}")
        
        self.logger.info("Data validation completed successfully")
    
    def _map_feedback_to_requirements(self, 
                                    parsed_report: ParsedComplianceReport,
                                    parsed_feedback: ParsedHumanFeedback) -> Dict[str, Any]:
        """Map human feedback items to corresponding compliance requirements."""
        self.logger.info("Mapping feedback to requirements")
        
        # Convert requirements to dict format for mapping
        requirements_dict = [req.to_dict() for req in parsed_report.requirements]
        
        # Use feedback parser's mapping functionality
        feedback_mapping = self.feedback_parser.map_feedback_to_requirements(
            parsed_feedback, requirements_dict
        )
        
        self.logger.info(f"Successfully mapped {len(feedback_mapping)} feedback items to requirements")
        return feedback_mapping
    
    def _generate_stm_entries(self, 
                            parsed_report: ParsedComplianceReport,
                            feedback_mapping: Dict[str, Any],
                            domain: str) -> Dict[str, Any]:
        """Generate STM entries from parsed data."""
        self.logger.info("Generating STM entries")
        
        created_entries = []
        failed_entries = []
        
        for requirement in parsed_report.requirements:
            try:
                # Generate scenario ID
                scenario_id = self.scenario_id_generator.generate_scenario_id(
                    requirement_text=requirement.requirement_text,
                    domain=domain,
                    requirement_number=requirement.requirement_number.lower()
                )
                
                # Create initial assessment
                initial_assessment = InitialAssessment(
                    status=requirement.status,
                    rationale=requirement.rationale,
                    recommendation=requirement.recommendation
                )
                
                # Create STM entry
                stm_entry = self.stm_processor.create_entry(
                    scenario_id=scenario_id,
                    requirement_text=requirement.requirement_text,
                    initial_assessment=initial_assessment
                )
                
                # Add human feedback if available
                req_num = requirement.requirement_number
                if req_num in feedback_mapping:
                    feedback_data = feedback_mapping[req_num]['feedback']
                    self.stm_processor.add_human_feedback(
                        scenario_id=scenario_id,
                        decision=feedback_data['decision'],
                        rationale=feedback_data['rationale'],
                        suggestion=feedback_data['suggestion']
                    )
                    
                    # Set final status based on feedback
                    final_status = self._determine_final_status(
                        initial_assessment.status,
                        feedback_data['decision']
                    )
                    self.stm_processor.set_final_status(scenario_id, final_status)
                
                created_entries.append({
                    'scenario_id': scenario_id,
                    'requirement_number': requirement.requirement_number,
                    'has_feedback': req_num in feedback_mapping,
                    'entry': stm_entry.to_dict()
                })
                
                self.logger.debug(f"Created STM entry: {scenario_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to create STM entry for {requirement.requirement_number}: {e}")
                failed_entries.append({
                    'requirement_number': requirement.requirement_number,
                    'error': str(e)
                })
        
        self.logger.info(f"STM generation completed: {len(created_entries)} created, {len(failed_entries)} failed")
        
        return {
            'entries': created_entries,
            'failed': failed_entries,
            'statistics': {
                'total_processed': len(parsed_report.requirements),
                'successful': len(created_entries),
                'failed': len(failed_entries),
                'with_feedback': sum(1 for entry in created_entries if entry['has_feedback'])
            }
        }
    
    def _generate_ltm_rules(self, 
                          stm_entries: List[Dict[str, Any]], 
                          feedback_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LTM rules from STM entries with human feedback."""
        self.logger.info("Generating LTM rules from human feedback")
        
        created_rules = []
        failed_rules = []
        
        # Only process entries that have human feedback
        entries_with_feedback = [entry for entry in stm_entries if entry['has_feedback']]
        
        for entry_data in entries_with_feedback:
            try:
                scenario_id = entry_data['scenario_id']
                req_num = entry_data['requirement_number']
                
                if req_num not in feedback_mapping:
                    continue
                
                # Get the STM entry
                stm_entry = self.stm_processor.get_entry(scenario_id)
                if not stm_entry:
                    self.logger.warning(f"STM entry not found for rule generation: {scenario_id}")
                    continue
                
                # Generate LTM rules using rule extractor
                rule_result = self.rule_extractor.extract_rule_from_stm(stm_entry)
                
                if rule_result.success and rule_result.rule:
                    rule = rule_result.rule
                    # Store rule in LTM
                    if self.ltm_manager.store_ltm_rule(rule):
                        # Create bidirectional link
                        self.stm_processor.add_ltm_rule_link(scenario_id, rule.rule_id)
                        
                        created_rules.append({
                            'rule_id': rule.rule_id,
                            'source_scenario_id': scenario_id,
                            'rule': rule.to_dict()
                        })
                        
                        self.logger.debug(f"Created LTM rule: {rule.rule_id}")
                    else:
                        failed_rules.append({
                            'rule_id': rule.rule_id,
                            'source_scenario_id': scenario_id,
                            'error': 'Failed to store rule in LTM'
                        })
                else:
                    failed_rules.append({
                        'source_scenario_id': scenario_id,
                        'error': f"Rule extraction failed: {rule_result.error if rule_result.error else 'Unknown error'}"
                    })
                
            except Exception as e:
                self.logger.error(f"Failed to generate LTM rules for {entry_data['scenario_id']}: {e}")
                failed_rules.append({
                    'source_scenario_id': entry_data['scenario_id'],
                    'error': str(e)
                })
        
        self.logger.info(f"LTM generation completed: {len(created_rules)} created, {len(failed_rules)} failed")
        
        return {
            'rules': created_rules,
            'failed': failed_rules,
            'statistics': {
                'entries_processed': len(entries_with_feedback),
                'rules_created': len(created_rules),
                'rules_failed': len(failed_rules)
            }
        }
    
    def _determine_final_status(self, initial_status: str, feedback_decision: str) -> str:
        """Determine final compliance status based on initial assessment and human feedback."""
        decision_lower = feedback_decision.lower()
        
        if 'no change' in decision_lower or 'accept' in decision_lower:
            return initial_status
        elif 'change' in decision_lower and 'compliant' in initial_status.lower():
            # If expert wants to change a compliant status, likely making it non-compliant
            return 'Partially Compliant'
        elif 'change' in decision_lower and 'non-compliant' in initial_status.lower():
            # If expert wants to change a non-compliant status, likely making it partially compliant
            return 'Partially Compliant'
        else:
            # Default to initial status if unclear
            return initial_status
    
    def _create_extraction_summary(self, 
                                 parsed_report: ParsedComplianceReport,
                                 parsed_feedback: ParsedHumanFeedback,
                                 stm_results: Dict[str, Any],
                                 ltm_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive extraction summary."""
        return {
            'input_files': {
                'compliance_report': {
                    'requirements_found': len(parsed_report.requirements),
                    'parsing_success': parsed_report.parsing_success
                },
                'human_feedback': {
                    'feedback_items_found': len(parsed_feedback.feedback_items),
                    'parsing_success': parsed_feedback.parsing_success
                }
            },
            'stm_processing': stm_results['statistics'],
            'ltm_processing': ltm_results['statistics'],
            'statistics': {
                'total_requirements_processed': len(parsed_report.requirements),
                'stm_entries_created': stm_results['statistics']['successful'],
                'ltm_rules_created': ltm_results['statistics']['rules_created'],
                'entries_with_feedback': stm_results['statistics']['with_feedback'],
                'processing_success_rate': (
                    stm_results['statistics']['successful'] / 
                    max(stm_results['statistics']['total_processed'], 1)
                ) * 100
            },
            'traceability': {
                'stm_to_ltm_links': ltm_results['statistics']['rules_created'],
                'bidirectional_links_created': ltm_results['statistics']['rules_created']
            }
        }
    
    def process_sample_data(self) -> Dict[str, Any]:
        """
        Process the existing sample compliance report and feedback files.
        
        Convenience method to process the default sample files in the workspace.
        
        Returns:
            Dictionary with processing results
        """
        self.logger.info("Processing sample data files")
        
        # Default file paths
        compliance_report_path = "Compliance_report_ra_agent.txt"
        human_feedback_path = "human_feedback.txt"
        
        return self.extract_from_files(
            compliance_report_path=compliance_report_path,
            human_feedback_path=human_feedback_path,
            domain="ecommerce"
        )
    
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics about extracted memory data.
        
        Returns:
            Dictionary with current memory statistics
        """
        try:
            stm_stats = self.stm_processor.get_stats()
            
            # Get LTM statistics
            all_rules = self.ltm_manager.get_all_rules()
            ltm_stats = {
                'total_rules': len(all_rules),
                'average_confidence': (
                    sum(rule.confidence_score for rule in all_rules) / len(all_rules) 
                    if all_rules else 0
                ),
                'rules_by_policy': {},
                'total_concepts': len(set(
                    concept for rule in all_rules for concept in rule.related_concepts
                ))
            }
            
            # Count rules by policy
            for rule in all_rules:
                policy = rule.rule_id.split('_')[0]
                ltm_stats['rules_by_policy'][policy] = ltm_stats['rules_by_policy'].get(policy, 0) + 1
            
            return {
                'stm_statistics': stm_stats,
                'ltm_statistics': ltm_stats,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get extraction statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
    
    def validate_extraction_results(self, extraction_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the results of memory extraction.
        
        Args:
            extraction_results: Results from extract_from_files method
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        if not extraction_results.get('success', False):
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Extraction failed: {extraction_results.get('error', 'Unknown error')}")
            return validation_results
        
        summary = extraction_results.get('extraction_summary', {})
        statistics = summary.get('statistics', {})
        
        # Check processing success rate
        success_rate = statistics.get('processing_success_rate', 0)
        if success_rate < 80:
            validation_results['warnings'].append(f"Low processing success rate: {success_rate:.1f}%")
        
        # Check STM/LTM generation
        stm_created = statistics.get('stm_entries_created', 0)
        ltm_created = statistics.get('ltm_rules_created', 0)
        
        if stm_created == 0:
            validation_results['errors'].append("No STM entries were created")
            validation_results['is_valid'] = False
        
        if ltm_created == 0:
            validation_results['warnings'].append("No LTM rules were generated")
            validation_results['recommendations'].append("Ensure human feedback contains actionable insights for rule generation")
        
        # Check traceability
        entries_with_feedback = statistics.get('entries_with_feedback', 0)
        if entries_with_feedback == 0:
            validation_results['warnings'].append("No entries have human feedback")
            validation_results['recommendations'].append("Human feedback is required for LTM rule generation")
        
        return validation_results
    
    def close(self) -> None:
        """Close all database connections and cleanup resources."""
        try:
            if hasattr(self.ltm_manager, 'close'):
                self.ltm_manager.close()
            self.logger.info("Memory extractor closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing memory extractor: {e}")