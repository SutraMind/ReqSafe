"""
Integration tests for the Memory Extractor orchestrator.

Tests the complete end-to-end workflow from input files to memory storage,
including STM entry creation and LTM rule generation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from memory_management.memory_extractor import MemoryExtractor, MemoryExtractionError
from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager
from memory_management.processors.rule_extractor import RuleExtractor
from memory_management.models.stm_entry import STMEntry, InitialAssessment
from memory_management.models.ltm_rule import LTMRule


class TestMemoryExtractorIntegration:
    """Integration tests for Memory Extractor orchestrator."""
    
    @pytest.fixture
    def sample_compliance_report(self):
        """Sample compliance report content."""
        return """## FINAL COMPLIANCE ASSESSMENT REPORT (RA_Agent) ##

**Project:** E-commerce Platform SRS
**Governing Policy:** GDPR
**Status:** 2 Non-Compliant, 1 Compliant Requirements Identified.

---
**Requirement R1:** During account signup, the user must agree to our Terms of Service.
*   **Status:** Non-Compliant
*   **Rationale:** Bundled consent violates GDPR Art. 7.
*   **Recommendation:** Implement separate opt-in checkboxes.

---
**Requirement R2:** All user passwords will be stored using SHA-256 hashing.
*   **Status:** Compliant
*   **Rationale:** SHA-256 is industry standard for password security.
*   **Recommendation:** None needed.
"""
    
    @pytest.fixture
    def sample_human_feedback(self):
        """Sample human feedback content."""
        return """## HUMAN EXPERT FEEDBACK ##

**Reviewer:** Legal Expert
**Date:** 2024-10-27

**Feedback on R1 (Consent):**
*   **Decision:** No change
*   **Rationale:** Agent's analysis is correct about bundled consent.
*   **Suggestion:** Implement granular consent checkboxes.

**Feedback on R2 (Password Hashing):**
*   **Decision:** Change status to Partially Compliant
*   **Rationale:** SHA-256 without salt is vulnerable to rainbow table attacks.
*   **Suggestion:** Use salted SHA-256 hashing for better security.
"""
    
    @pytest.fixture
    def temp_files(self, sample_compliance_report, sample_human_feedback):
        """Create temporary files for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create compliance report file
            compliance_path = Path(temp_dir) / "compliance_report.txt"
            with open(compliance_path, 'w', encoding='utf-8') as f:
                f.write(sample_compliance_report)
            
            # Create human feedback file
            feedback_path = Path(temp_dir) / "human_feedback.txt"
            with open(feedback_path, 'w', encoding='utf-8') as f:
                f.write(sample_human_feedback)
            
            yield str(compliance_path), str(feedback_path)
    
    @pytest.fixture
    def mock_stm_processor(self):
        """Mock STM processor for testing."""
        mock_processor = Mock(spec=STMProcessor)
        
        # Mock create_entry method
        def mock_create_entry(scenario_id, requirement_text, initial_assessment):
            entry = Mock(spec=STMEntry)
            entry.scenario_id = scenario_id
            entry.requirement_text = requirement_text
            entry.initial_assessment = initial_assessment
            entry.human_feedback = None
            entry.final_status = None
            entry.to_dict.return_value = {
                'scenario_id': scenario_id,
                'requirement_text': requirement_text,
                'initial_assessment': initial_assessment.to_dict(),
                'human_feedback': None,
                'final_status': None
            }
            return entry
        
        mock_processor.create_entry.side_effect = mock_create_entry
        mock_processor.add_human_feedback.return_value = Mock(spec=STMEntry)
        mock_processor.set_final_status.return_value = Mock(spec=STMEntry)
        mock_processor.get_entry.return_value = Mock(spec=STMEntry)
        mock_processor.add_ltm_rule_link.return_value = True
        mock_processor.get_stats.return_value = {
            'total_entries': 2,
            'entries_with_feedback': 2,
            'entries_without_feedback': 0
        }
        
        return mock_processor
    
    @pytest.fixture
    def mock_ltm_manager(self):
        """Mock LTM manager for testing."""
        mock_manager = Mock(spec=LTMManager)
        mock_manager.store_ltm_rule.return_value = True
        mock_manager.get_all_rules.return_value = []
        return mock_manager
    
    @pytest.fixture
    def mock_rule_extractor(self):
        """Mock rule extractor for testing."""
        mock_extractor = Mock(spec=RuleExtractor)
        
        # Mock rule generation
        def mock_extract_rule(stm_entry):
            from memory_management.processors.rule_extractor import RuleGenerationResult
            rule = Mock(spec=LTMRule)
            rule.rule_id = f"GDPR_Test_Rule_01"
            rule.rule_text = "Test rule generated from feedback"
            rule.related_concepts = ["consent", "gdpr"]
            rule.source_scenario_id = [stm_entry.scenario_id]
            rule.confidence_score = 0.85
            rule.to_dict.return_value = {
                'rule_id': rule.rule_id,
                'rule_text': rule.rule_text,
                'related_concepts': rule.related_concepts,
                'source_scenario_id': rule.source_scenario_id,
                'confidence_score': rule.confidence_score
            }
            return RuleGenerationResult(success=True, rule=rule, confidence_score=0.85)
        
        mock_extractor.extract_rule_from_stm.side_effect = mock_extract_rule
        return mock_extractor
    
    @pytest.fixture
    def memory_extractor(self, mock_stm_processor, mock_ltm_manager, mock_rule_extractor):
        """Create memory extractor with mocked components."""
        with patch('memory_management.memory_extractor.STMProcessor', return_value=mock_stm_processor), \
             patch('memory_management.memory_extractor.LTMManager', return_value=mock_ltm_manager), \
             patch('memory_management.memory_extractor.RuleExtractor', return_value=mock_rule_extractor):
            
            extractor = MemoryExtractor(
                stm_processor=mock_stm_processor,
                ltm_manager=mock_ltm_manager,
                rule_extractor=mock_rule_extractor
            )
            return extractor
    
    def test_memory_extractor_initialization(self):
        """Test memory extractor initialization."""
        with patch('memory_management.memory_extractor.STMProcessor') as mock_stm, \
             patch('memory_management.memory_extractor.LTMManager') as mock_ltm, \
             patch('memory_management.memory_extractor.RuleExtractor') as mock_rule:
            
            extractor = MemoryExtractor()
            
            # Verify components were initialized
            mock_stm.assert_called_once()
            mock_ltm.assert_called_once()
            mock_rule.assert_called_once()
            
            assert extractor.compliance_parser is not None
            assert extractor.feedback_parser is not None
            assert extractor.scenario_id_generator is not None
    
    def test_memory_extractor_initialization_failure(self):
        """Test memory extractor initialization failure handling."""
        with patch('memory_management.memory_extractor.STMProcessor', side_effect=Exception("Connection failed")):
            with pytest.raises(MemoryExtractionError, match="Initialization failed"):
                MemoryExtractor()
    
    def test_extract_from_files_success(self, memory_extractor, temp_files):
        """Test successful end-to-end extraction from files."""
        compliance_path, feedback_path = temp_files
        
        # Mock the parsing methods to return successful results
        with patch.object(memory_extractor.compliance_parser, 'parse_report_file') as mock_parse_report, \
             patch.object(memory_extractor.feedback_parser, 'parse_feedback_file') as mock_parse_feedback, \
             patch.object(memory_extractor.compliance_parser, 'validate_parsed_data') as mock_validate_report, \
             patch.object(memory_extractor.feedback_parser, 'validate_parsed_data') as mock_validate_feedback, \
             patch.object(memory_extractor.feedback_parser, 'map_feedback_to_requirements') as mock_map_feedback:
            
            # Setup mock returns
            mock_parsed_report = Mock()
            mock_parsed_report.parsing_success = True
            mock_parsed_report.requirements = [
                Mock(requirement_number='R1', requirement_text='Test requirement 1', 
                     status='Non-Compliant', rationale='Test rationale', recommendation='Test recommendation'),
                Mock(requirement_number='R2', requirement_text='Test requirement 2',
                     status='Compliant', rationale='Test rationale 2', recommendation='Test recommendation 2')
            ]
            mock_parse_report.return_value = mock_parsed_report
            
            mock_parsed_feedback = Mock()
            mock_parsed_feedback.parsing_success = True
            mock_parsed_feedback.feedback_items = [
                Mock(requirement_reference='R1', decision='No change', rationale='Correct', suggestion='Good'),
                Mock(requirement_reference='R2', decision='Change', rationale='Needs salt', suggestion='Use salted hash')
            ]
            mock_parse_feedback.return_value = mock_parsed_feedback
            
            mock_validate_report.return_value = {'is_valid': True, 'errors': []}
            mock_validate_feedback.return_value = {'is_valid': True, 'errors': []}
            mock_map_feedback.return_value = {
                'R1': {'requirement': {}, 'feedback': {'decision': 'No change', 'rationale': 'Correct', 'suggestion': 'Good'}},
                'R2': {'requirement': {}, 'feedback': {'decision': 'Change', 'rationale': 'Needs salt', 'suggestion': 'Use salted hash'}}
            }
            
            # Execute extraction
            result = memory_extractor.extract_from_files(compliance_path, feedback_path, domain="test")
            
            # Verify success
            assert result['success'] is True
            assert 'extraction_summary' in result
            assert 'stm_results' in result
            assert 'ltm_results' in result
            assert 'timestamp' in result
            
            # Verify STM processor was called
            assert memory_extractor.stm_processor.create_entry.call_count == 2
            assert memory_extractor.stm_processor.add_human_feedback.call_count == 2
            assert memory_extractor.stm_processor.set_final_status.call_count == 2
            
            # Verify LTM manager was called
            assert memory_extractor.ltm_manager.store_ltm_rule.call_count >= 1
    
    def test_extract_from_files_missing_compliance_report(self, memory_extractor):
        """Test extraction with missing compliance report file."""
        result = memory_extractor.extract_from_files(
            "nonexistent_compliance.txt", 
            "nonexistent_feedback.txt"
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()
    
    def test_extract_from_files_parsing_failure(self, memory_extractor, temp_files):
        """Test extraction with parsing failure."""
        compliance_path, feedback_path = temp_files
        
        # Mock parsing failure
        with patch.object(memory_extractor.compliance_parser, 'parse_report_file') as mock_parse:
            mock_parsed_report = Mock()
            mock_parsed_report.parsing_success = False
            mock_parsed_report.error_message = "Parsing failed"
            mock_parse.return_value = mock_parsed_report
            
            result = memory_extractor.extract_from_files(compliance_path, feedback_path)
            
            assert result['success'] is False
            assert 'Parsing failed' in result['error']
    
    def test_extract_from_files_validation_failure(self, memory_extractor, temp_files):
        """Test extraction with validation failure."""
        compliance_path, feedback_path = temp_files
        
        with patch.object(memory_extractor.compliance_parser, 'parse_report_file') as mock_parse_report, \
             patch.object(memory_extractor.feedback_parser, 'parse_feedback_file') as mock_parse_feedback, \
             patch.object(memory_extractor.compliance_parser, 'validate_parsed_data') as mock_validate:
            
            # Setup successful parsing
            mock_parsed_report = Mock()
            mock_parsed_report.parsing_success = True
            mock_parse_report.return_value = mock_parsed_report
            
            mock_parsed_feedback = Mock()
            mock_parsed_feedback.parsing_success = True
            mock_parse_feedback.return_value = mock_parsed_feedback
            
            # Setup validation failure
            mock_validate.return_value = {'is_valid': False, 'errors': ['Invalid data format']}
            
            result = memory_extractor.extract_from_files(compliance_path, feedback_path)
            
            assert result['success'] is False
            assert 'Invalid data format' in result['error']
    
    def test_process_sample_data(self, memory_extractor):
        """Test processing of sample data files."""
        with patch.object(memory_extractor, 'extract_from_files') as mock_extract:
            mock_extract.return_value = {'success': True, 'test': 'data'}
            
            result = memory_extractor.process_sample_data()
            
            mock_extract.assert_called_once_with(
                compliance_report_path="Compliance_report_ra_agent.txt",
                human_feedback_path="human_feedback.txt",
                domain="ecommerce"
            )
            assert result == {'success': True, 'test': 'data'}
    
    def test_get_extraction_statistics(self, memory_extractor):
        """Test getting extraction statistics."""
        # Mock LTM manager to return sample rules
        sample_rules = [
            Mock(rule_id='GDPR_Test_01', confidence_score=0.8, related_concepts=['consent']),
            Mock(rule_id='GDPR_Test_02', confidence_score=0.9, related_concepts=['security', 'hashing'])
        ]
        memory_extractor.ltm_manager.get_all_rules.return_value = sample_rules
        
        stats = memory_extractor.get_extraction_statistics()
        
        assert 'stm_statistics' in stats
        assert 'ltm_statistics' in stats
        assert 'timestamp' in stats
        assert stats['ltm_statistics']['total_rules'] == 2
        assert stats['ltm_statistics']['average_confidence'] == 0.85
    
    def test_get_extraction_statistics_error(self, memory_extractor):
        """Test getting extraction statistics with error."""
        memory_extractor.stm_processor.get_stats.side_effect = Exception("Database error")
        
        stats = memory_extractor.get_extraction_statistics()
        
        assert 'error' in stats
        assert 'Database error' in stats['error']
    
    def test_validate_extraction_results_success(self, memory_extractor):
        """Test validation of successful extraction results."""
        extraction_results = {
            'success': True,
            'extraction_summary': {
                'statistics': {
                    'processing_success_rate': 100.0,
                    'stm_entries_created': 2,
                    'ltm_rules_created': 2,
                    'entries_with_feedback': 2
                }
            }
        }
        
        validation = memory_extractor.validate_extraction_results(extraction_results)
        
        assert validation['is_valid'] is True
        assert len(validation['errors']) == 0
    
    def test_validate_extraction_results_failure(self, memory_extractor):
        """Test validation of failed extraction results."""
        extraction_results = {
            'success': False,
            'error': 'Extraction failed'
        }
        
        validation = memory_extractor.validate_extraction_results(extraction_results)
        
        assert validation['is_valid'] is False
        assert 'Extraction failed' in validation['errors'][0]
    
    def test_validate_extraction_results_low_success_rate(self, memory_extractor):
        """Test validation with low success rate."""
        extraction_results = {
            'success': True,
            'extraction_summary': {
                'statistics': {
                    'processing_success_rate': 50.0,
                    'stm_entries_created': 1,
                    'ltm_rules_created': 0,
                    'entries_with_feedback': 0
                }
            }
        }
        
        validation = memory_extractor.validate_extraction_results(extraction_results)
        
        assert validation['is_valid'] is True  # Still valid but with warnings
        assert len(validation['warnings']) >= 2  # Low success rate + no LTM rules
        assert len(validation['recommendations']) >= 1
    
    def test_validate_extraction_results_no_stm_entries(self, memory_extractor):
        """Test validation with no STM entries created."""
        extraction_results = {
            'success': True,
            'extraction_summary': {
                'statistics': {
                    'processing_success_rate': 0.0,
                    'stm_entries_created': 0,
                    'ltm_rules_created': 0,
                    'entries_with_feedback': 0
                }
            }
        }
        
        validation = memory_extractor.validate_extraction_results(extraction_results)
        
        assert validation['is_valid'] is False
        assert 'No STM entries were created' in validation['errors']
    
    def test_determine_final_status(self, memory_extractor):
        """Test final status determination logic."""
        # Test no change decision
        final_status = memory_extractor._determine_final_status('Non-Compliant', 'No change')
        assert final_status == 'Non-Compliant'
        
        # Test change from compliant
        final_status = memory_extractor._determine_final_status('Compliant', 'Change status')
        assert final_status == 'Partially Compliant'
        
        # Test change from non-compliant
        final_status = memory_extractor._determine_final_status('Non-Compliant', 'Change status')
        assert final_status == 'Partially Compliant'
        
        # Test unclear decision
        final_status = memory_extractor._determine_final_status('Compliant', 'Unclear decision')
        assert final_status == 'Compliant'
    
    def test_close(self, memory_extractor):
        """Test closing memory extractor."""
        memory_extractor.close()
        
        # Verify LTM manager close was called
        memory_extractor.ltm_manager.close.assert_called_once()


class TestMemoryExtractorRealFiles:
    """Integration tests using real sample files."""
    
    def test_extract_from_real_sample_files(self):
        """Test extraction using the actual sample files in the workspace."""
        # Check if sample files exist
        compliance_path = "Compliance_report_ra_agent.txt"
        feedback_path = "human_feedback.txt"
        
        if not (Path(compliance_path).exists() and Path(feedback_path).exists()):
            pytest.skip("Sample files not found in workspace")
        
        # Mock the database components to avoid actual database connections
        with patch('memory_management.memory_extractor.STMProcessor') as mock_stm, \
             patch('memory_management.memory_extractor.LTMManager') as mock_ltm, \
             patch('memory_management.memory_extractor.RuleExtractor') as mock_rule:
            
            # Setup mocks
            mock_stm_instance = Mock()
            mock_stm_instance.create_entry.return_value = Mock(spec=STMEntry)
            mock_stm_instance.add_human_feedback.return_value = Mock(spec=STMEntry)
            mock_stm_instance.set_final_status.return_value = Mock(spec=STMEntry)
            mock_stm_instance.get_entry.return_value = Mock(spec=STMEntry)
            mock_stm_instance.add_ltm_rule_link.return_value = True
            mock_stm_instance.get_stats.return_value = {'total_entries': 5}
            mock_stm.return_value = mock_stm_instance
            
            mock_ltm_instance = Mock()
            mock_ltm_instance.store_ltm_rule.return_value = True
            mock_ltm_instance.get_all_rules.return_value = []
            mock_ltm.return_value = mock_ltm_instance
            
            mock_rule_instance = Mock()
            from memory_management.processors.rule_extractor import RuleGenerationResult
            mock_rule_instance.extract_rule_from_stm.return_value = RuleGenerationResult(
                success=True, 
                rule=Mock(rule_id='GDPR_Test_01', to_dict=lambda: {'rule_id': 'GDPR_Test_01'}),
                confidence_score=0.8
            )
            mock_rule.return_value = mock_rule_instance
            
            # Create extractor and process files
            extractor = MemoryExtractor()
            result = extractor.extract_from_files(compliance_path, feedback_path)
            
            # Verify processing was attempted
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'timestamp' in result
            
            # If successful, verify structure
            if result['success']:
                assert 'extraction_summary' in result
                assert 'stm_results' in result
                assert 'ltm_results' in result
                
                # Verify statistics structure
                summary = result['extraction_summary']
                assert 'input_files' in summary
                assert 'stm_processing' in summary
                assert 'ltm_processing' in summary
                assert 'statistics' in summary
                assert 'traceability' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])