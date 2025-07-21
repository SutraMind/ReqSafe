"""
Traceability Service for managing bidirectional links between STM and LTM.

Provides comprehensive traceability features including source linking,
version history tracking, and audit trail generation.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .stm_processor import STMProcessor
from .ltm_manager import LTMManager
from ..models.stm_entry import STMEntry
from ..models.ltm_rule import LTMRule


class TraceabilityService:
    """
    Service for managing traceability and source linking between STM and LTM.
    
    Implements requirements 4.1-4.5 for complete traceability and audit trails.
    """
    
    def __init__(self, stm_processor: STMProcessor, ltm_manager: LTMManager):
        """
        Initialize traceability service with STM and LTM processors.
        
        Args:
            stm_processor: STM processor instance
            ltm_manager: LTM manager instance
        """
        self.stm_processor = stm_processor
        self.ltm_manager = ltm_manager
        self.logger = logging.getLogger(__name__)
        
        # Link processors for bidirectional communication
        self.ltm_manager.link_rule_to_stm_processor(stm_processor)
    
    def create_rule_from_stm(self, scenario_id: str, rule: LTMRule) -> bool:
        """
        Create an LTM rule from an STM entry with proper traceability links.
        
        Args:
            scenario_id: Source STM scenario ID
            rule: LTM rule to create
            
        Returns:
            True if rule was created with proper links
        """
        try:
            # Verify STM entry exists
            stm_entry = self.stm_processor.get_entry(scenario_id)
            if not stm_entry:
                self.logger.error(f"STM entry {scenario_id} not found")
                return False
            
            # Ensure scenario_id is in rule's source scenarios
            if scenario_id not in rule.source_scenario_id:
                rule.add_source_scenario(scenario_id)
            
            # Store the LTM rule
            if not self.ltm_manager.store_ltm_rule(rule):
                return False
            
            # Create bidirectional link
            self.stm_processor.add_ltm_rule_link(scenario_id, rule.rule_id)
            
            self.logger.info(f"Created LTM rule {rule.rule_id} from STM {scenario_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create rule from STM {scenario_id}: {e}")
            return False
    
    def link_existing_rule_to_scenario(self, rule_id: str, scenario_id: str) -> bool:
        """
        Link an existing LTM rule to an additional STM scenario.
        
        Supports multiple source scenarios for single rules (Requirement 4.3).
        
        Args:
            rule_id: Existing LTM rule ID
            scenario_id: STM scenario to link
            
        Returns:
            True if link was created successfully
        """
        try:
            # Verify both entries exist
            stm_entry = self.stm_processor.get_entry(scenario_id)
            ltm_rule = self.ltm_manager.get_ltm_rule(rule_id)
            
            if not stm_entry:
                self.logger.error(f"STM entry {scenario_id} not found")
                return False
            
            if not ltm_rule:
                self.logger.error(f"LTM rule {rule_id} not found")
                return False
            
            # Update LTM rule with new scenario
            success = self.ltm_manager.update_rule_with_new_scenario(rule_id, scenario_id)
            
            if success:
                # Create bidirectional link in STM
                self.stm_processor.add_ltm_rule_link(scenario_id, rule_id)
                self.logger.info(f"Linked LTM rule {rule_id} to STM {scenario_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to link rule {rule_id} to scenario {scenario_id}: {e}")
            return False
    
    def get_stm_to_ltm_navigation(self, scenario_id: str) -> Dict[str, Any]:
        """
        Get navigation information from STM entry to related LTM rules.
        
        Implements Requirement 4.1: Links to source_scenario_id entries.
        
        Args:
            scenario_id: STM scenario identifier
            
        Returns:
            Dictionary with STM entry and related LTM rules
        """
        try:
            # Get STM entry
            stm_entry = self.stm_processor.get_entry(scenario_id)
            if not stm_entry:
                return {}
            
            # Get related LTM rules
            related_rules = self.ltm_manager.get_rules_by_source_scenario(scenario_id)
            
            return {
                'stm_entry': stm_entry.to_dict(),
                'related_ltm_rules': [rule.to_dict() for rule in related_rules],
                'rule_count': len(related_rules),
                'navigation_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get STM to LTM navigation for {scenario_id}: {e}")
            return {}
    
    def get_ltm_to_stm_navigation(self, rule_id: str) -> Dict[str, Any]:
        """
        Get navigation information from LTM rule to source STM entries.
        
        Implements Requirement 4.2: Display complete STM case files.
        
        Args:
            rule_id: LTM rule identifier
            
        Returns:
            Dictionary with LTM rule and source STM entries
        """
        try:
            # Get LTM rule
            ltm_rule = self.ltm_manager.get_ltm_rule(rule_id)
            if not ltm_rule:
                return {}
            
            # Get all source STM entries
            source_stm_entries = []
            for scenario_id in ltm_rule.source_scenario_id:
                stm_entry = self.stm_processor.get_entry(scenario_id)
                if stm_entry:
                    source_stm_entries.append(stm_entry.to_dict())
            
            return {
                'ltm_rule': ltm_rule.to_dict(),
                'source_stm_entries': source_stm_entries,
                'source_count': len(source_stm_entries),
                'missing_sources': len(ltm_rule.source_scenario_id) - len(source_stm_entries),
                'navigation_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get LTM to STM navigation for {rule_id}: {e}")
            return {}
    
    def get_complete_traceability_chain(self, rule_id: str) -> Dict[str, Any]:
        """
        Get complete chain of evidence from human feedback to generalized rule.
        
        Implements Requirement 4.5: Complete audit trail.
        
        Args:
            rule_id: LTM rule identifier
            
        Returns:
            Dictionary with complete traceability chain
        """
        try:
            # Get LTM rule audit trail
            audit_trail = self.ltm_manager.get_complete_audit_trail(rule_id)
            if not audit_trail:
                return {}
            
            # Enhance with detailed STM information
            detailed_sources = []
            for scenario_id in audit_trail.get('source_scenarios', []):
                stm_info = self.stm_processor.get_traceability_info(scenario_id)
                if stm_info:
                    detailed_sources.append(stm_info)
            
            # Add traceability metadata
            traceability_chain = {
                'rule_audit_trail': audit_trail,
                'detailed_source_scenarios': detailed_sources,
                'traceability_metadata': {
                    'chain_length': len(detailed_sources),
                    'has_human_feedback': any(
                        source.get('has_human_feedback', False) 
                        for source in detailed_sources
                    ),
                    'evidence_completeness': self._calculate_evidence_completeness(
                        audit_trail, detailed_sources
                    ),
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            return traceability_chain
            
        except Exception as e:
            self.logger.error(f"Failed to get traceability chain for {rule_id}: {e}")
            return {}
    
    def _calculate_evidence_completeness(self, audit_trail: Dict, sources: List[Dict]) -> float:
        """
        Calculate completeness score for evidence chain.
        
        Args:
            audit_trail: LTM audit trail
            sources: Detailed source information
            
        Returns:
            Completeness score between 0.0 and 1.0
        """
        try:
            total_sources = len(audit_trail.get('source_scenarios', []))
            available_sources = len(sources)
            sources_with_feedback = sum(
                1 for source in sources 
                if source.get('has_human_feedback', False)
            )
            
            if total_sources == 0:
                return 0.0
            
            # Weight factors
            source_availability = available_sources / total_sources
            feedback_coverage = sources_with_feedback / total_sources if total_sources > 0 else 0
            version_tracking = 1.0 if audit_trail.get('audit_metadata', {}).get('total_versions', 0) > 0 else 0.5
            
            # Calculate weighted completeness
            completeness = (
                source_availability * 0.4 +
                feedback_coverage * 0.4 +
                version_tracking * 0.2
            )
            
            return min(completeness, 1.0)
            
        except Exception:
            return 0.0
    
    def update_rule_version_with_traceability(self, base_rule_id: str, 
                                            updated_rule: LTMRule,
                                            new_scenario_id: str = None) -> bool:
        """
        Update rule version while maintaining traceability.
        
        Implements Requirement 4.4: Version history and source traceability.
        
        Args:
            base_rule_id: Base rule ID to version
            updated_rule: Updated rule content
            new_scenario_id: Optional new scenario to add as source
            
        Returns:
            True if version was created with proper traceability
        """
        try:
            # Add new scenario if provided
            if new_scenario_id:
                if new_scenario_id not in updated_rule.source_scenario_id:
                    updated_rule.add_source_scenario(new_scenario_id)
            
            # Create new version
            success = self.ltm_manager.create_rule_version(base_rule_id, updated_rule)
            
            if success and new_scenario_id:
                # Update bidirectional links
                self.stm_processor.add_ltm_rule_link(new_scenario_id, updated_rule.rule_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update rule version for {base_rule_id}: {e}")
            return False
    
    def validate_traceability_integrity(self) -> Dict[str, Any]:
        """
        Validate integrity of traceability links across the system.
        
        Returns:
            Dictionary with validation results and any issues found
        """
        try:
            issues = []
            stats = {
                'total_stm_entries': 0,
                'total_ltm_rules': 0,
                'orphaned_stm_entries': 0,
                'orphaned_ltm_rules': 0,
                'broken_links': 0
            }
            
            # Check STM entries
            stm_entries = self.stm_processor.list_entries()
            stats['total_stm_entries'] = len(stm_entries)
            
            for entry in stm_entries:
                related_rules = self.stm_processor.get_related_ltm_rules(entry.scenario_id)
                if not related_rules and entry.human_feedback:
                    stats['orphaned_stm_entries'] += 1
                    issues.append(f"STM entry {entry.scenario_id} has feedback but no LTM rules")
            
            # Check LTM rules
            ltm_rules = self.ltm_manager.get_all_rules()
            stats['total_ltm_rules'] = len(ltm_rules)
            
            for rule in ltm_rules:
                if not rule.source_scenario_id:
                    stats['orphaned_ltm_rules'] += 1
                    issues.append(f"LTM rule {rule.rule_id} has no source scenarios")
                else:
                    # Check if source scenarios exist
                    for scenario_id in rule.source_scenario_id:
                        stm_entry = self.stm_processor.get_entry(scenario_id)
                        if not stm_entry:
                            stats['broken_links'] += 1
                            issues.append(f"LTM rule {rule.rule_id} references missing STM {scenario_id}")
            
            return {
                'validation_timestamp': datetime.utcnow().isoformat(),
                'integrity_status': 'PASS' if not issues else 'ISSUES_FOUND',
                'statistics': stats,
                'issues': issues
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate traceability integrity: {e}")
            return {
                'validation_timestamp': datetime.utcnow().isoformat(),
                'integrity_status': 'ERROR',
                'error': str(e)
            }
    
    def cleanup_broken_links(self) -> Dict[str, Any]:
        """
        Clean up broken traceability links.
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            validation = self.validate_traceability_integrity()
            if validation['integrity_status'] == 'PASS':
                return {'status': 'NO_CLEANUP_NEEDED', 'cleaned_links': 0}
            
            cleaned_count = 0
            
            # Clean up broken STM -> LTM links
            stm_entries = self.stm_processor.list_entries()
            for entry in stm_entries:
                related_rules = self.stm_processor.get_related_ltm_rules(entry.scenario_id)
                for rule_id in related_rules:
                    if not self.ltm_manager.get_ltm_rule(rule_id):
                        self.stm_processor.remove_ltm_rule_link(entry.scenario_id, rule_id)
                        cleaned_count += 1
            
            return {
                'status': 'CLEANUP_COMPLETED',
                'cleaned_links': cleaned_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup broken links: {e}")
            return {'status': 'CLEANUP_ERROR', 'error': str(e)}