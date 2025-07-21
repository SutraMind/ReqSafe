"""
Unit tests for TraceabilityService.

Tests bidirectional navigation, version history, and audit trail functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from memory_management.processors.traceability_service import TraceabilityService
from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule


class TestTraceabilityService(unittest.TestCase):
    """Test cases for TraceabilityService functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_stm_processor = Mock(spec=STMProcessor)
        self.mock_ltm_manager = Mock(spec=LTMManager)
        
        self.traceability_service = TraceabilityService(
            self.mock_stm_processor,
            self.mock_ltm_manager
        )
        
        # Sample test data
        self.sample_stm_entry = STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="During account signup, the user must agree to terms",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="Bundled consent violates GDPR",
                recommendation="Implement separate checkboxes"
            ),
            human_feedback=HumanFeedback(
                decision="Agree",
                rationale="Agent analysis is correct",
                suggestion="Use granular consent"
            ),
            final_status="Non-Compliant"
        )
        
        self.sample_ltm_rule = LTMRule(
            rule_id="gdpr_consent_001",
            rule_text="Consent must be granular and specific for each purpose",
            related_concepts=["consent", "gdpr", "granular"],
            source_scenario_id=["ecommerce_r1_consent"],
            confidence_score=0.9,
            version=1
        )
    
    def test_create_rule_from_stm_success(self):
        """Test successful creation of LTM rule from STM entry."""
        # Setup mocks
        self.mock_stm_processor.get_entry.return_value = self.sample_stm_entry
        self.mock_ltm_manager.store_ltm_rule.return_value = True
        self.mock_stm_processor.add_ltm_rule_link.return_value = True
        
        # Test
        result = self.traceability_service.create_rule_from_stm(
            "ecommerce_r1_consent", 
            self.sample_ltm_rule
        )
        
        # Assertions
        self.assertTrue(result)
        self.mock_stm_processor.get_entry.assert_called_once_with("ecommerce_r1_consent")
        self.mock_ltm_manager.store_ltm_rule.assert_called_once()
        self.mock_stm_processor.add_ltm_rule_link.assert_called_once_with(
            "ecommerce_r1_consent", 
            "gdpr_consent_001"
        )
    
    def test_create_rule_from_stm_missing_stm_entry(self):
        """Test failure when STM entry doesn't exist."""
        # Setup mocks
        self.mock_stm_processor.get_entry.return_value = None
        
        # Test
        result = self.traceability_service.create_rule_from_stm(
            "nonexistent_scenario", 
            self.sample_ltm_rule
        )
        
        # Assertions
        self.assertFalse(result)
        self.mock_ltm_manager.store_ltm_rule.assert_not_called()
    
    def test_link_existing_rule_to_scenario_success(self):
        """Test successful linking of existing rule to additional scenario."""
        # Setup mocks
        self.mock_stm_processor.get_entry.return_value = self.sample_stm_entry
        self.mock_ltm_manager.get_ltm_rule.return_value = self.sample_ltm_rule
        self.mock_ltm_manager.update_rule_with_new_scenario.return_value = True
        self.mock_stm_processor.add_ltm_rule_link.return_value = True
        
        # Test
        result = self.traceability_service.link_existing_rule_to_scenario(
            "gdpr_consent_001",
            "ecommerce_r2_data_processing"
        )
        
        # Assertions
        self.assertTrue(result)
        self.mock_ltm_manager.update_rule_with_new_scenario.assert_called_once_with(
            "gdpr_consent_001",
            "ecommerce_r2_data_processing"
        )
        self.mock_stm_processor.add_ltm_rule_link.assert_called_once_with(
            "ecommerce_r2_data_processing",
            "gdpr_consent_001"
        )
    
    def test_get_stm_to_ltm_navigation(self):
        """Test navigation from STM entry to related LTM rules."""
        # Setup mocks
        self.mock_stm_processor.get_entry.return_value = self.sample_stm_entry
        self.mock_ltm_manager.get_rules_by_source_scenario.return_value = [self.sample_ltm_rule]
        
        # Test
        result = self.traceability_service.get_stm_to_ltm_navigation("ecommerce_r1_consent")
        
        # Assertions
        self.assertIn('stm_entry', result)
        self.assertIn('related_ltm_rules', result)
        self.assertEqual(result['rule_count'], 1)
        self.assertEqual(result['stm_entry']['scenario_id'], "ecommerce_r1_consent")
        self.assertEqual(len(result['related_ltm_rules']), 1)
    
    def test_get_ltm_to_stm_navigation(self):
        """Test navigation from LTM rule to source STM entries."""
        # Setup mocks
        self.mock_ltm_manager.get_ltm_rule.return_value = self.sample_ltm_rule
        self.mock_stm_processor.get_entry.return_value = self.sample_stm_entry
        
        # Test
        result = self.traceability_service.get_ltm_to_stm_navigation("gdpr_consent_001")
        
        # Assertions
        self.assertIn('ltm_rule', result)
        self.assertIn('source_stm_entries', result)
        self.assertEqual(result['source_count'], 1)
        self.assertEqual(result['missing_sources'], 0)
        self.assertEqual(result['ltm_rule']['rule_id'], "gdpr_consent_001")
    
    def test_get_complete_traceability_chain(self):
        """Test complete audit trail generation."""
        # Setup mocks
        audit_trail = {
            'rule': self.sample_ltm_rule.to_dict(),
            'source_scenarios': ["ecommerce_r1_consent"],
            'audit_metadata': {
                'total_versions': 1,
                'source_count': 1,
                'concept_count': 3
            }
        }
        
        stm_traceability = {
            'stm_entry': self.sample_stm_entry.to_dict(),
            'has_human_feedback': True,
            'final_status': 'Non-Compliant'
        }
        
        self.mock_ltm_manager.get_complete_audit_trail.return_value = audit_trail
        self.mock_stm_processor.get_traceability_info.return_value = stm_traceability
        
        # Test
        result = self.traceability_service.get_complete_traceability_chain("gdpr_consent_001")
        
        # Assertions
        self.assertIn('rule_audit_trail', result)
        self.assertIn('detailed_source_scenarios', result)
        self.assertIn('traceability_metadata', result)
        self.assertEqual(result['traceability_metadata']['chain_length'], 1)
        self.assertTrue(result['traceability_metadata']['has_human_feedback'])
        self.assertGreater(result['traceability_metadata']['evidence_completeness'], 0.0)
    
    def test_calculate_evidence_completeness_full(self):
        """Test evidence completeness calculation with full data."""
        audit_trail = {
            'source_scenarios': ["scenario1", "scenario2"],
            'audit_metadata': {'total_versions': 2}
        }
        
        sources = [
            {'has_human_feedback': True},
            {'has_human_feedback': True}
        ]
        
        # Test
        completeness = self.traceability_service._calculate_evidence_completeness(
            audit_trail, sources
        )
        
        # Should be high completeness (all sources available with feedback)
        self.assertGreater(completeness, 0.8)
        self.assertLessEqual(completeness, 1.0)
    
    def test_calculate_evidence_completeness_partial(self):
        """Test evidence completeness calculation with partial data."""
        audit_trail = {
            'source_scenarios': ["scenario1", "scenario2", "scenario3"],
            'audit_metadata': {'total_versions': 1}
        }
        
        sources = [
            {'has_human_feedback': True},
            {'has_human_feedback': False}
        ]  # Missing one source
        
        # Test
        completeness = self.traceability_service._calculate_evidence_completeness(
            audit_trail, sources
        )
        
        # Should be moderate completeness
        self.assertGreater(completeness, 0.3)
        self.assertLess(completeness, 0.8)
    
    def test_update_rule_version_with_traceability(self):
        """Test rule version update with traceability maintenance."""
        # Setup mocks
        updated_rule = LTMRule(
            rule_id="gdpr_consent_002",
            rule_text="Updated consent rule with additional requirements",
            related_concepts=["consent", "gdpr", "granular", "explicit"],
            source_scenario_id=["ecommerce_r1_consent", "ecommerce_r2_data"],
            confidence_score=0.95,
            version=2
        )
        
        self.mock_ltm_manager.create_rule_version.return_value = True
        self.mock_stm_processor.add_ltm_rule_link.return_value = True
        
        # Test
        result = self.traceability_service.update_rule_version_with_traceability(
            "gdpr_consent_001",
            updated_rule,
            "ecommerce_r2_data"
        )
        
        # Assertions
        self.assertTrue(result)
        self.mock_ltm_manager.create_rule_version.assert_called_once_with(
            "gdpr_consent_001",
            updated_rule
        )
        self.mock_stm_processor.add_ltm_rule_link.assert_called_once_with(
            "ecommerce_r2_data",
            "gdpr_consent_002"
        )
    
    def test_validate_traceability_integrity_pass(self):
        """Test traceability integrity validation with no issues."""
        # Setup mocks
        self.mock_stm_processor.list_entries.return_value = [self.sample_stm_entry]
        self.mock_stm_processor.get_related_ltm_rules.return_value = ["gdpr_consent_001"]
        self.mock_ltm_manager.get_all_rules.return_value = [self.sample_ltm_rule]
        self.mock_stm_processor.get_entry.return_value = self.sample_stm_entry
        
        # Test
        result = self.traceability_service.validate_traceability_integrity()
        
        # Assertions
        self.assertEqual(result['integrity_status'], 'PASS')
        self.assertEqual(result['statistics']['total_stm_entries'], 1)
        self.assertEqual(result['statistics']['total_ltm_rules'], 1)
        self.assertEqual(result['statistics']['orphaned_stm_entries'], 0)
        self.assertEqual(result['statistics']['broken_links'], 0)
        self.assertEqual(len(result['issues']), 0)
    
    def test_validate_traceability_integrity_with_issues(self):
        """Test traceability integrity validation with issues found."""
        # Setup mocks - orphaned STM entry
        orphaned_stm = STMEntry(
            scenario_id="orphaned_scenario",
            requirement_text="Test requirement",
            initial_assessment=InitialAssessment("Compliant", "Test", "Test"),
            human_feedback=HumanFeedback("Agree", "Test", "Test")
        )
        
        # Orphaned LTM rule
        orphaned_ltm = LTMRule(
            rule_id="orphaned_rule",
            rule_text="Orphaned rule",
            related_concepts=["test"],
            source_scenario_id=[]  # No source scenarios
        )
        
        self.mock_stm_processor.list_entries.return_value = [orphaned_stm]
        self.mock_stm_processor.get_related_ltm_rules.return_value = []  # No related rules
        self.mock_ltm_manager.get_all_rules.return_value = [orphaned_ltm]
        
        # Test
        result = self.traceability_service.validate_traceability_integrity()
        
        # Assertions
        self.assertEqual(result['integrity_status'], 'ISSUES_FOUND')
        self.assertEqual(result['statistics']['orphaned_stm_entries'], 1)
        self.assertEqual(result['statistics']['orphaned_ltm_rules'], 1)
        self.assertGreater(len(result['issues']), 0)
    
    def test_cleanup_broken_links(self):
        """Test cleanup of broken traceability links."""
        # Setup mocks
        validation_result = {
            'integrity_status': 'ISSUES_FOUND',
            'issues': ['Broken link found']
        }
        
        self.traceability_service.validate_traceability_integrity = Mock(
            return_value=validation_result
        )
        
        self.mock_stm_processor.list_entries.return_value = [self.sample_stm_entry]
        self.mock_stm_processor.get_related_ltm_rules.return_value = ["nonexistent_rule"]
        self.mock_ltm_manager.get_ltm_rule.return_value = None  # Rule doesn't exist
        self.mock_stm_processor.remove_ltm_rule_link.return_value = True
        
        # Test
        result = self.traceability_service.cleanup_broken_links()
        
        # Assertions
        self.assertEqual(result['status'], 'CLEANUP_COMPLETED')
        self.assertEqual(result['cleaned_links'], 1)
        self.mock_stm_processor.remove_ltm_rule_link.assert_called_once_with(
            "ecommerce_r1_consent",
            "nonexistent_rule"
        )
    
    def test_cleanup_broken_links_no_cleanup_needed(self):
        """Test cleanup when no broken links exist."""
        # Setup mocks
        validation_result = {
            'integrity_status': 'PASS'
        }
        
        self.traceability_service.validate_traceability_integrity = Mock(
            return_value=validation_result
        )
        
        # Test
        result = self.traceability_service.cleanup_broken_links()
        
        # Assertions
        self.assertEqual(result['status'], 'NO_CLEANUP_NEEDED')
        self.assertEqual(result['cleaned_links'], 0)


class TestTraceabilityServiceIntegration(unittest.TestCase):
    """Integration tests for TraceabilityService with real processors."""
    
    @patch('memory_management.processors.stm_processor.redis.Redis')
    @patch('memory_management.processors.ltm_manager.GraphDatabase.driver')
    def setUp(self, mock_neo4j_driver, mock_redis):
        """Set up integration test fixtures."""
        # Mock Redis connection
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        
        # Mock Neo4j connection with proper context manager
        mock_driver_instance = Mock()
        mock_neo4j_driver.return_value = mock_driver_instance
        mock_session = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_driver_instance.session.return_value = mock_context_manager
        mock_session.run.return_value = Mock()
        
        # Create real processors with mocked connections
        self.stm_processor = STMProcessor()
        self.ltm_manager = LTMManager()
        self.traceability_service = TraceabilityService(
            self.stm_processor,
            self.ltm_manager
        )
    
    def test_service_initialization(self):
        """Test that traceability service initializes correctly."""
        self.assertIsNotNone(self.traceability_service.stm_processor)
        self.assertIsNotNone(self.traceability_service.ltm_manager)
        self.assertTrue(hasattr(self.ltm_manager, 'stm_processor'))
    
    def test_bidirectional_linking_setup(self):
        """Test that bidirectional linking is properly set up."""
        # The LTM manager should have a reference to the STM processor
        self.assertEqual(
            self.ltm_manager.stm_processor,
            self.stm_processor
        )


if __name__ == '__main__':
    unittest.main()