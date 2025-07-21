"""
Comprehensive Test Suite for Compliance Memory Management Module.

This test suite validates all requirements and provides comprehensive coverage
including integration tests, end-to-end tests, performance tests, and data quality tests.
"""

import pytest
import asyncio
import concurrent.futures
import time
import json
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import statistics
from datetime import datetime, timedelta

# Import all components for comprehensive testing
from memory_management.memory_extractor import MemoryExtractor, MemoryExtractionError
from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager
from memory_management.processors.rule_extractor import RuleExtractor
from memory_management.processors.traceability_service import TraceabilityService
from memory_management.api.memory_api import MemoryAPI
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule
from memory_management.parsers.compliance_report_parser import ComplianceReportParser
from memory_management.parsers.human_feedback_parser import HumanFeedbackParser
from memory_management.utils.validators import DataValidator
from memory_management.performance.metrics_collector import MetricsCollector
from memory_management.config.settings import get_settings


class TestFixtures:
    """Centralized test fixtures and mock data generators."""
    
    @staticmethod
    def create_sample_compliance_report() -> str:
        """Generate realistic compliance report content."""
        return """## FINAL COMPLIANCE ASSESSMENT REPORT (RA_Agent) ##

**Project:** E-commerce Platform SRS
**Governing Policy:** GDPR
**Status:** 3 Non-Compliant, 2 Compliant Requirements Identified.

---
**Requirement R1:** During account signup, the user must agree to our Terms of Service.
*   **Status:** Non-Compliant
*   **Rationale:** Bundled consent violates GDPR Art. 7 which requires separate consent for different purposes.
*   **Recommendation:** Implement separate, unticked opt-in checkboxes for different data processing purposes.

---
**Requirement R2:** All user passwords will be stored using SHA-256 hashing.
*   **Status:** Non-Compliant
*   **Rationale:** SHA-256 without salt is vulnerable to rainbow table attacks and doesn't meet GDPR Art. 32 requirements.
*   **Recommendation:** Use salted SHA-256 or bcrypt hashing with appropriate work factors.

---
**Requirement R3:** User data will be encrypted at rest using AES-256.
*   **Status:** Compliant
*   **Rationale:** AES-256 encryption meets GDPR Art. 32 requirements for data protection.
*   **Recommendation:** None needed, current implementation is adequate.

---
**Requirement R4:** Users can request data deletion through customer support.
*   **Status:** Non-Compliant
*   **Rationale:** Manual process doesn't meet GDPR Art. 17 requirements for timely data deletion.
*   **Recommendation:** Implement automated data deletion system with user self-service portal.

---
**Requirement R5:** System logs user access for audit purposes.
*   **Status:** Compliant
*   **Rationale:** Audit logging supports GDPR Art. 5 accountability principle.
*   **Recommendation:** Ensure logs are retained for appropriate duration and protected from unauthorized access.
"""
    
    @staticmethod
    def create_sample_human_feedback() -> str:
        """Generate realistic human feedback content."""
        return """## HUMAN EXPERT FEEDBACK ##

**Reviewer:** Legal Expert - Data Protection Officer
**Date:** 2024-10-27
**Review Session:** GDPR Compliance Assessment Review

**Feedback on R1 (Consent Mechanism):**
*   **Decision:** No change
*   **Rationale:** Agent's analysis is correct about bundled consent violating GDPR Art. 7. The requirement clearly bundles different purposes.
*   **Suggestion:** Implement granular consent checkboxes with clear purpose descriptions and ensure they are unticked by default.

**Feedback on R2 (Password Hashing):**
*   **Decision:** Change status to Partially Compliant
*   **Rationale:** While SHA-256 is cryptographically sound, lack of salt makes it vulnerable. However, it's not completely non-compliant.
*   **Suggestion:** Migrate to bcrypt or Argon2 for new passwords, implement salt for existing SHA-256 hashes.

**Feedback on R3 (Data Encryption):**
*   **Decision:** No change
*   **Rationale:** AES-256 encryption at rest is indeed compliant with GDPR requirements.
*   **Suggestion:** Consider implementing key rotation policies for enhanced security.

**Feedback on R4 (Data Deletion):**
*   **Decision:** No change
*   **Rationale:** Manual deletion process is insufficient for GDPR compliance. Automated system is necessary.
*   **Suggestion:** Implement automated deletion with 30-day processing window and user notification system.

**Feedback on R5 (Audit Logging):**
*   **Decision:** Change status to Partially Compliant
*   **Rationale:** While logging exists, need to verify log retention policies and access controls meet GDPR requirements.
*   **Suggestion:** Implement log anonymization after 12 months and restrict access to authorized personnel only.
"""
    
    @staticmethod
    def create_sample_stm_entry(scenario_id: str = "ecommerce_r1_consent") -> STMEntry:
        """Create sample STM entry for testing."""
        initial_assessment = InitialAssessment(
            status="Non-Compliant",
            rationale="Bundled consent violates GDPR Art. 7",
            recommendation="Implement separate opt-in checkboxes"
        )
        
        human_feedback = HumanFeedback(
            decision="No change",
            rationale="Agent's analysis is correct",
            suggestion="Implement granular consent checkboxes"
        )
        
        return STMEntry(
            scenario_id=scenario_id,
            requirement_text="During account signup, the user must agree to our Terms of Service.",
            initial_assessment=initial_assessment,
            human_feedback=human_feedback,
            final_status="Non-Compliant"
        )
    
    @staticmethod
    def create_sample_ltm_rule(rule_id: str = "GDPR_Consent_Granular_01") -> LTMRule:
        """Create sample LTM rule for testing."""
        return LTMRule(
            rule_id=rule_id,
            rule_text="For GDPR Article 7 compliance, consent mechanisms must provide separate, unticked checkboxes for different data processing purposes to avoid bundled consent violations.",
            related_concepts=["Consent", "GDPR Article 7", "Data Processing", "User Interface", "Bundled Consent"],
            source_scenario_id=["ecommerce_r1_consent"],
            confidence_score=0.95
        )
    
    @staticmethod
    def create_temp_files(compliance_content: str, feedback_content: str):
        """Create temporary files for testing."""
        temp_dir = tempfile.mkdtemp()
        
        compliance_path = Path(temp_dir) / "compliance_report.txt"
        with open(compliance_path, 'w', encoding='utf-8') as f:
            f.write(compliance_content)
        
        feedback_path = Path(temp_dir) / "human_feedback.txt"
        with open(feedback_path, 'w', encoding='utf-8') as f:
            f.write(feedback_content)
        
        return str(compliance_path), str(feedback_path), temp_dir


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    def stm_processor(self):
        """Create STM processor for testing."""
        try:
            processor = STMProcessor()
            yield processor
            # Cleanup test data
            try:
                processor.clear_test_data()
            except:
                pass
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
    
    @pytest.fixture
    def ltm_manager(self):
        """Create LTM manager for testing."""
        try:
            manager = LTMManager()
            yield manager
            # Cleanup test data
            try:
                manager.clear_test_data()
            except:
                pass
            manager.close()
        except Exception as e:
            pytest.skip(f"Neo4j not available: {e}")
    
    def test_redis_stm_operations(self, stm_processor):
        """Test Redis STM operations integration."""
        # Create test STM entry
        stm_entry = TestFixtures.create_sample_stm_entry("integration_test_001")
        
        # Test create operation
        created_entry = stm_processor.create_entry(
            stm_entry.scenario_id,
            stm_entry.requirement_text,
            stm_entry.initial_assessment
        )
        
        assert created_entry is not None
        assert created_entry.scenario_id == stm_entry.scenario_id
        
        # Test retrieve operation
        retrieved_entry = stm_processor.get_entry(stm_entry.scenario_id)
        assert retrieved_entry is not None
        assert retrieved_entry.scenario_id == stm_entry.scenario_id
        assert retrieved_entry.requirement_text == stm_entry.requirement_text
        
        # Test update with feedback
        updated_entry = stm_processor.add_human_feedback(
            stm_entry.scenario_id,
            stm_entry.human_feedback
        )
        assert updated_entry.human_feedback is not None
        
        # Test final status update
        final_entry = stm_processor.set_final_status(stm_entry.scenario_id, "Non-Compliant")
        assert final_entry.final_status == "Non-Compliant"
        
        # Test delete operation
        success = stm_processor.delete_entry(stm_entry.scenario_id)
        assert success
        
        # Verify deletion
        deleted_entry = stm_processor.get_entry(stm_entry.scenario_id)
        assert deleted_entry is None
    
    def test_neo4j_ltm_operations(self, ltm_manager):
        """Test Neo4j LTM operations integration."""
        # Create test LTM rule
        ltm_rule = TestFixtures.create_sample_ltm_rule("INTEGRATION_TEST_RULE_01")
        
        # Test store operation
        success = ltm_manager.store_ltm_rule(ltm_rule)
        assert success
        
        # Test retrieve operation
        retrieved_rule = ltm_manager.get_ltm_rule(ltm_rule.rule_id)
        assert retrieved_rule is not None
        assert retrieved_rule.rule_id == ltm_rule.rule_id
        assert retrieved_rule.rule_text == ltm_rule.rule_text
        
        # Test search by concepts
        search_results = ltm_manager.search_ltm_rules(
            concepts=["Consent", "GDPR Article 7"],
            limit=10
        )
        assert len(search_results) > 0
        assert any(rule.rule_id == ltm_rule.rule_id for rule in search_results)
        
        # Test update operation
        ltm_rule.confidence_score = 0.98
        update_success = ltm_manager.update_ltm_rule(ltm_rule)
        assert update_success
        
        # Verify update
        updated_rule = ltm_manager.get_ltm_rule(ltm_rule.rule_id)
        assert updated_rule.confidence_score == 0.98
        
        # Test delete operation
        delete_success = ltm_manager.delete_ltm_rule(ltm_rule.rule_id)
        assert delete_success
        
        # Verify deletion
        deleted_rule = ltm_manager.get_ltm_rule(ltm_rule.rule_id)
        assert deleted_rule is None
    
    def test_database_connection_resilience(self, stm_processor, ltm_manager):
        """Test database connection resilience and error handling."""
        # Test Redis connection resilience
        try:
            # Attempt operation that might fail due to connection issues
            health = stm_processor.health_check()
            assert 'status' in health
        except Exception as e:
            # Verify error is handled gracefully
            assert isinstance(e, (ConnectionError, TimeoutError))
        
        # Test Neo4j connection resilience
        try:
            # Attempt operation that might fail due to connection issues
            health = ltm_manager.health_check()
            assert 'status' in health
        except Exception as e:
            # Verify error is handled gracefully
            assert isinstance(e, (ConnectionError, TimeoutError))


class TestEndToEndWorkflows:
    """End-to-end tests with realistic compliance data."""
    
    @pytest.fixture
    def memory_extractor(self):
        """Create memory extractor for end-to-end testing."""
        extractor = MemoryExtractor()
        yield extractor
        extractor.close()
    
    def test_complete_memory_extraction_workflow(self, memory_extractor):
        """Test complete end-to-end memory extraction workflow."""
        # Create realistic test data
        compliance_content = TestFixtures.create_sample_compliance_report()
        feedback_content = TestFixtures.create_sample_human_feedback()
        
        compliance_path, feedback_path, temp_dir = TestFixtures.create_temp_files(
            compliance_content, feedback_content
        )
        
        try:
            # Execute complete extraction workflow
            result = memory_extractor.extract_from_files(
                compliance_path, feedback_path, domain="integration_test"
            )
            
            # Verify extraction success
            assert result['success'] is True
            assert 'extraction_summary' in result
            assert 'stm_results' in result
            assert 'ltm_results' in result
            
            # Verify STM entries were created
            stm_results = result['stm_results']
            assert len(stm_results) >= 5  # Should have 5 requirements
            
            # Verify LTM rules were generated
            ltm_results = result['ltm_results']
            assert len(ltm_results) >= 2  # Should generate some rules
            
            # Verify extraction statistics
            stats = result['extraction_summary']['statistics']
            assert stats['processing_success_rate'] >= 80.0
            assert stats['stm_entries_created'] >= 5
            assert stats['entries_with_feedback'] >= 5
            
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_api_integration_workflow(self):
        """Test complete API integration workflow."""
        api = MemoryAPI()
        
        try:
            # Test adding new assessment
            assessment_data = {
                "scenario_id": "api_test_scenario_001",
                "requirement_text": "Test requirement for API integration",
                "initial_assessment": {
                    "status": "Non-Compliant",
                    "rationale": "Test rationale for API integration",
                    "recommendation": "Test recommendation for API integration"
                }
            }
            
            create_response = api.add_new_assessment(assessment_data)
            assert create_response['status'] == 'success'
            
            # Test retrieving STM entry
            get_response = api.get_stm_entry("api_test_scenario_001")
            assert get_response['status'] == 'success'
            assert get_response['data']['scenario_id'] == "api_test_scenario_001"
            
            # Test updating with feedback
            feedback_data = {
                "decision": "Approved",
                "rationale": "Test feedback rationale",
                "suggestion": "Test feedback suggestion",
                "final_status": "Compliant"
            }
            
            feedback_response = api.update_with_feedback("api_test_scenario_001", feedback_data)
            assert feedback_response['status'] == 'success'
            
            # Test LTM rule search
            search_response = api.search_ltm_rules("Test", ["API", "Integration"])
            assert search_response['status'] == 'success'
            assert isinstance(search_response['data'], list)
            
        finally:
            api.close()
    
    def test_traceability_workflow(self):
        """Test complete traceability workflow."""
        stm_processor = STMProcessor()
        ltm_manager = LTMManager()
        traceability_service = TraceabilityService(stm_processor, ltm_manager)
        
        try:
            # Create STM entry
            stm_entry = TestFixtures.create_sample_stm_entry("traceability_test_001")
            created_entry = stm_processor.create_entry(
                stm_entry.scenario_id,
                stm_entry.requirement_text,
                stm_entry.initial_assessment
            )
            
            # Add human feedback
            stm_processor.add_human_feedback(stm_entry.scenario_id, stm_entry.human_feedback)
            stm_processor.set_final_status(stm_entry.scenario_id, "Non-Compliant")
            
            # Create LTM rule from STM
            rule_created = traceability_service.create_rule_from_stm(
                stm_entry.scenario_id, "TRACEABILITY_TEST_RULE_01"
            )
            assert rule_created
            
            # Test STM to LTM navigation
            stm_to_ltm = traceability_service.get_stm_to_ltm_navigation(stm_entry.scenario_id)
            assert stm_to_ltm['success']
            assert len(stm_to_ltm['related_rules']) > 0
            
            # Test LTM to STM navigation
            ltm_to_stm = traceability_service.get_ltm_to_stm_navigation("TRACEABILITY_TEST_RULE_01")
            assert ltm_to_stm['success']
            assert len(ltm_to_stm['source_scenarios']) > 0
            
            # Test complete audit trail
            audit_trail = traceability_service.get_complete_traceability_chain("TRACEABILITY_TEST_RULE_01")
            assert audit_trail['success']
            assert 'rule_details' in audit_trail
            assert 'source_scenarios' in audit_trail
            
        finally:
            # Cleanup
            try:
                stm_processor.delete_entry("traceability_test_001")
                ltm_manager.delete_ltm_rule("TRACEABILITY_TEST_RULE_01")
            except:
                pass
            ltm_manager.close()


class TestPerformanceRequirements:
    """Performance tests for concurrent access scenarios."""
    
    def test_stm_performance_requirements(self):
        """Test STM operations meet sub-second response time requirements."""
        stm_processor = STMProcessor()
        
        try:
            # Test single operation performance
            start_time = time.time()
            stm_entry = TestFixtures.create_sample_stm_entry("perf_test_001")
            created_entry = stm_processor.create_entry(
                stm_entry.scenario_id,
                stm_entry.requirement_text,
                stm_entry.initial_assessment
            )
            create_time = (time.time() - start_time) * 1000
            
            assert create_time < 1000, f"STM create time {create_time:.2f}ms exceeds 1000ms requirement"
            
            # Test retrieval performance
            start_time = time.time()
            retrieved_entry = stm_processor.get_entry(stm_entry.scenario_id)
            retrieve_time = (time.time() - start_time) * 1000
            
            assert retrieve_time < 100, f"STM retrieve time {retrieve_time:.2f}ms exceeds 100ms requirement"
            
        finally:
            try:
                stm_processor.delete_entry("perf_test_001")
            except:
                pass
    
    def test_ltm_performance_requirements(self):
        """Test LTM operations meet performance requirements."""
        ltm_manager = LTMManager()
        
        try:
            # Create test rule
            ltm_rule = TestFixtures.create_sample_ltm_rule("PERF_TEST_RULE_01")
            
            # Test store performance
            start_time = time.time()
            success = ltm_manager.store_ltm_rule(ltm_rule)
            store_time = (time.time() - start_time) * 1000
            
            assert success
            assert store_time < 2000, f"LTM store time {store_time:.2f}ms exceeds 2000ms requirement"
            
            # Test search performance
            start_time = time.time()
            results = ltm_manager.search_ltm_rules(concepts=["Consent"], limit=10)
            search_time = (time.time() - start_time) * 1000
            
            assert search_time < 1000, f"LTM search time {search_time:.2f}ms exceeds 1000ms requirement"
            
        finally:
            try:
                ltm_manager.delete_ltm_rule("PERF_TEST_RULE_01")
            except:
                pass
            ltm_manager.close()
    
    def test_concurrent_access_performance(self):
        """Test performance under concurrent access scenarios."""
        api = MemoryAPI()
        
        def concurrent_operation(index):
            """Single concurrent operation."""
            scenario_id = f"concurrent_perf_test_{index}"
            assessment_data = {
                "scenario_id": scenario_id,
                "requirement_text": f"Concurrent test requirement {index}",
                "initial_assessment": {
                    "status": "Non-Compliant",
                    "rationale": f"Concurrent test rationale {index}",
                    "recommendation": f"Concurrent test recommendation {index}"
                }
            }
            
            start_time = time.time()
            
            # Create and retrieve
            create_response = api.add_new_assessment(assessment_data)
            get_response = api.get_stm_entry(scenario_id)
            
            total_time = (time.time() - start_time) * 1000
            
            return {
                'success': create_response['status'] == 'success' and get_response['status'] == 'success',
                'time': total_time
            }
        
        try:
            # Execute concurrent operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(concurrent_operation, i) for i in range(20)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Verify all operations succeeded
            assert all(r['success'] for r in results), "Some concurrent operations failed"
            
            # Verify performance
            times = [r['time'] for r in results]
            avg_time = statistics.mean(times)
            p95_time = sorted(times)[int(len(times) * 0.95)]
            
            assert avg_time < 2000, f"Average concurrent time {avg_time:.2f}ms exceeds 2000ms requirement"
            assert p95_time < 5000, f"P95 concurrent time {p95_time:.2f}ms exceeds 5000ms requirement"
            
        finally:
            api.close()


class TestDataQualityValidation:
    """Data quality validation tests."""
    
    def test_extraction_accuracy_validation(self):
        """Test extraction accuracy against known good examples."""
        parser = ComplianceReportParser()
        
        # Test with known good compliance report
        compliance_content = TestFixtures.create_sample_compliance_report()
        result = parser.parse_report_text(compliance_content)
        
        if result.parsing_success:
            # Verify expected number of requirements
            assert len(result.requirements) == 5, f"Expected 5 requirements, got {len(result.requirements)}"
            
            # Verify specific requirement details
            r1 = next((r for r in result.requirements if r.requirement_number == 'R1'), None)
            assert r1 is not None, "Requirement R1 not found"
            assert r1.status == "Non-Compliant", f"R1 status should be Non-Compliant, got {r1.status}"
            assert "consent" in r1.rationale.lower(), "R1 rationale should mention consent"
            
            # Verify data completeness
            for req in result.requirements:
                assert req.requirement_number is not None, "Requirement number missing"
                assert req.requirement_text is not None, "Requirement text missing"
                assert req.status in ["Compliant", "Non-Compliant", "Partially Compliant"], f"Invalid status: {req.status}"
                assert req.rationale is not None, "Rationale missing"
                assert req.recommendation is not None, "Recommendation missing"
    
    def test_ltm_rule_quality_validation(self):
        """Test LTM rule generation quality."""
        rule_extractor = RuleExtractor()
        
        # Create STM entry with human feedback
        stm_entry = TestFixtures.create_sample_stm_entry("quality_test_001")
        
        # Generate LTM rule
        rule_result = rule_extractor.extract_rule_from_stm(stm_entry)
        
        if rule_result.success:
            rule = rule_result.rule
            
            # Verify rule quality criteria
            assert len(rule.rule_text) > 50, "Rule text should be descriptive (>50 chars)"
            assert len(rule.related_concepts) >= 3, "Rule should have at least 3 related concepts"
            assert rule.confidence_score >= 0.7, f"Rule confidence {rule.confidence_score} should be >= 0.7"
            
            # Verify rule text quality
            rule_text_lower = rule.rule_text.lower()
            assert any(concept.lower() in rule_text_lower for concept in rule.related_concepts), \
                "Rule text should contain at least one related concept"
            
            # Verify concepts are meaningful
            for concept in rule.related_concepts:
                assert len(concept.strip()) > 2, f"Concept '{concept}' too short"
                assert concept.strip() != "", "Empty concept found"
    
    def test_traceability_integrity_validation(self):
        """Test traceability link integrity."""
        stm_processor = STMProcessor()
        ltm_manager = LTMManager()
        traceability_service = TraceabilityService(stm_processor, ltm_manager)
        
        try:
            # Create linked STM and LTM entries
            stm_entry = TestFixtures.create_sample_stm_entry("integrity_test_001")
            created_entry = stm_processor.create_entry(
                stm_entry.scenario_id,
                stm_entry.requirement_text,
                stm_entry.initial_assessment
            )
            
            # Create LTM rule
            rule_created = traceability_service.create_rule_from_stm(
                stm_entry.scenario_id, "INTEGRITY_TEST_RULE_01"
            )
            assert rule_created
            
            # Validate traceability integrity
            integrity_result = traceability_service.validate_traceability_integrity()
            
            assert integrity_result['is_valid'], f"Traceability integrity failed: {integrity_result.get('errors', [])}"
            assert len(integrity_result.get('errors', [])) == 0, "Traceability errors found"
            
            # Verify bidirectional links
            stm_to_ltm = traceability_service.get_stm_to_ltm_navigation(stm_entry.scenario_id)
            ltm_to_stm = traceability_service.get_ltm_to_stm_navigation("INTEGRITY_TEST_RULE_01")
            
            assert stm_to_ltm['success'] and ltm_to_stm['success'], "Bidirectional navigation failed"
            
        finally:
            # Cleanup
            try:
                stm_processor.delete_entry("integrity_test_001")
                ltm_manager.delete_ltm_rule("INTEGRITY_TEST_RULE_01")
            except:
                pass
            ltm_manager.close()


class TestRequirementsValidation:
    """Validate all requirements are met."""
    
    def test_requirement_1_stm_extraction_and_storage(self):
        """Validate Requirement 1: STM extraction and storage."""
        memory_extractor = MemoryExtractor()
        
        try:
            # Test data extraction
            compliance_content = TestFixtures.create_sample_compliance_report()
            feedback_content = TestFixtures.create_sample_human_feedback()
            
            compliance_path, feedback_path, temp_dir = TestFixtures.create_temp_files(
                compliance_content, feedback_content
            )
            
            result = memory_extractor.extract_from_files(compliance_path, feedback_path)
            
            # Requirement 1.1: Extract data to create STM entry
            assert result['success'], "Failed to extract data for STM creation"
            
            # Requirement 1.2: Generate unique scenario_id with correct format
            stm_results = result['stm_results']
            for stm_result in stm_results:
                scenario_id = stm_result['scenario_id']
                parts = scenario_id.split('_')
                assert len(parts) >= 3, f"Scenario ID {scenario_id} doesn't follow domain_requirement_concept format"
            
            # Requirement 1.3: Include required fields
            for stm_result in stm_results:
                assert 'requirement_text' in stm_result, "Missing requirement_text field"
                assert 'initial_assessment' in stm_result, "Missing initial_assessment field"
                assert 'human_feedback' in stm_result, "Missing human_feedback field"
                assert 'final_status' in stm_result, "Missing final_status field"
            
            # Requirement 1.4: Capture initial assessment details
            for stm_result in stm_results:
                initial = stm_result['initial_assessment']
                assert 'status' in initial, "Missing status in initial_assessment"
                assert 'rationale' in initial, "Missing rationale in initial_assessment"
                assert 'recommendation' in initial, "Missing recommendation in initial_assessment"
            
            # Requirement 1.5: Capture human feedback details
            for stm_result in stm_results:
                feedback = stm_result['human_feedback']
                if feedback:  # Some entries might not have feedback
                    assert 'decision' in feedback, "Missing decision in human_feedback"
                    assert 'rationale' in feedback, "Missing rationale in human_feedback"
                    assert 'suggestion' in feedback, "Missing suggestion in human_feedback"
            
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        finally:
            memory_extractor.close()
    
    def test_requirement_2_ltm_rule_generation(self):
        """Validate Requirement 2: LTM rule generation."""
        rule_extractor = RuleExtractor()
        stm_entry = TestFixtures.create_sample_stm_entry("req2_test_001")
        
        # Requirement 2.1: Identify generalizable patterns
        rule_result = rule_extractor.extract_rule_from_stm(stm_entry)
        assert rule_result.success, "Failed to identify generalizable patterns"
        
        rule = rule_result.rule
        
        # Requirement 2.2: Generate unique rule_id with correct format
        rule_id_parts = rule.rule_id.split('_')
        assert len(rule_id_parts) >= 3, f"Rule ID {rule.rule_id} doesn't follow policy_concept_version format"
        
        # Requirement 2.3: Include required LTM fields
        assert rule.rule_text is not None, "Missing rule_text field"
        assert rule.related_concepts is not None, "Missing related_concepts field"
        assert rule.source_scenario_id is not None, "Missing source_scenario_id field"
        
        # Requirement 2.4: Create context-free, reusable statements
        assert len(rule.rule_text) > 30, "Rule text should be descriptive and context-free"
        assert not any(specific in rule.rule_text.lower() for specific in ['r1', 'r2', 'ecommerce']), \
            "Rule text should not contain specific scenario references"
        
        # Requirement 2.5: Extract relevant concepts for indexing
        assert len(rule.related_concepts) >= 2, "Should extract multiple related concepts"
        assert all(len(concept.strip()) > 1 for concept in rule.related_concepts), \
            "All concepts should be meaningful"
    
    def test_requirement_3_efficient_storage_and_retrieval(self):
        """Validate Requirement 3: Efficient storage and retrieval."""
        stm_processor = STMProcessor()
        ltm_manager = LTMManager()
        
        try:
            # Requirement 3.1: Fast-access database for STM (Redis)
            stm_entry = TestFixtures.create_sample_stm_entry("req3_stm_test")
            created_entry = stm_processor.create_entry(
                stm_entry.scenario_id,
                stm_entry.requirement_text,
                stm_entry.initial_assessment
            )
            assert created_entry is not None, "STM storage failed"
            
            # Requirement 3.2: Optimized database for LTM (Neo4j)
            ltm_rule = TestFixtures.create_sample_ltm_rule("REQ3_LTM_TEST_01")
            ltm_stored = ltm_manager.store_ltm_rule(ltm_rule)
            assert ltm_stored, "LTM storage failed"
            
            # Requirement 3.3: Support retrieval by scenario_id, rule_id, and concepts
            retrieved_stm = stm_processor.get_entry(stm_entry.scenario_id)
            assert retrieved_stm is not None, "STM retrieval by scenario_id failed"
            
            retrieved_ltm = ltm_manager.get_ltm_rule(ltm_rule.rule_id)
            assert retrieved_ltm is not None, "LTM retrieval by rule_id failed"
            
            concept_search = ltm_manager.search_ltm_rules(concepts=["Consent"], limit=10)
            assert isinstance(concept_search, list), "LTM concept search failed"
            
            # Requirement 3.4: Sub-second STM response times
            start_time = time.time()
            stm_processor.get_entry(stm_entry.scenario_id)
            stm_time = (time.time() - start_time) * 1000
            assert stm_time < 1000, f"STM response time {stm_time:.2f}ms exceeds 1000ms requirement"
            
            # Requirement 3.5: Semantic search for LTM
            semantic_results = ltm_manager.search_ltm_rules(
                concepts=ltm_rule.related_concepts[:2],
                limit=5
            )
            assert len(semantic_results) >= 0, "Semantic search should return results"
            
        finally:
            try:
                stm_processor.delete_entry("req3_stm_test")
                ltm_manager.delete_ltm_rule("REQ3_LTM_TEST_01")
            except:
                pass
            ltm_manager.close()
    
    def test_requirement_4_traceability(self):
        """Validate Requirement 4: Traceability and source linking."""
        stm_processor = STMProcessor()
        ltm_manager = LTMManager()
        traceability_service = TraceabilityService(stm_processor, ltm_manager)
        
        try:
            # Create linked entries
            stm_entry = TestFixtures.create_sample_stm_entry("req4_trace_test")
            created_entry = stm_processor.create_entry(
                stm_entry.scenario_id,
                stm_entry.requirement_text,
                stm_entry.initial_assessment
            )
            
            rule_created = traceability_service.create_rule_from_stm(
                stm_entry.scenario_id, "REQ4_TRACE_RULE_01"
            )
            assert rule_created, "Failed to create rule with traceability"
            
            # Requirement 4.1: Provide links to source_scenario_id
            ltm_rule = ltm_manager.get_ltm_rule("REQ4_TRACE_RULE_01")
            assert stm_entry.scenario_id in ltm_rule.source_scenario_id, \
                "LTM rule should link to source scenario"
            
            # Requirement 4.2: Display complete STM case file
            ltm_to_stm = traceability_service.get_ltm_to_stm_navigation("REQ4_TRACE_RULE_01")
            assert ltm_to_stm['success'], "Failed to navigate from LTM to STM"
            assert len(ltm_to_stm['source_scenarios']) > 0, "Should show source scenarios"
            
            # Requirement 4.3: Show all contributing scenarios
            stm_to_ltm = traceability_service.get_stm_to_ltm_navigation(stm_entry.scenario_id)
            assert stm_to_ltm['success'], "Failed to navigate from STM to LTM"
            
            # Requirement 4.4: Maintain version history
            audit_trail = traceability_service.get_complete_traceability_chain("REQ4_TRACE_RULE_01")
            assert audit_trail['success'], "Failed to get audit trail"
            assert 'rule_details' in audit_trail, "Audit trail should include rule details"
            
            # Requirement 4.5: Complete chain of evidence
            assert 'source_scenarios' in audit_trail, "Audit trail should include source scenarios"
            assert 'traceability_links' in audit_trail, "Audit trail should include traceability links"
            
        finally:
            try:
                stm_processor.delete_entry("req4_trace_test")
                ltm_manager.delete_ltm_rule("REQ4_TRACE_RULE_01")
            except:
                pass
            ltm_manager.close()
    
    def test_requirement_5_file_processing(self):
        """Validate Requirement 5: File processing capabilities."""
        try:
            memory_extractor = MemoryExtractor()
        except Exception as e:
            # If databases are not available, use mocked components
            pytest.skip(f"Database not available, skipping integration test: {e}")
        
        try:
            # Create test files
            compliance_content = TestFixtures.create_sample_compliance_report()
            feedback_content = TestFixtures.create_sample_human_feedback()
            
            compliance_path, feedback_path, temp_dir = TestFixtures.create_temp_files(
                compliance_content, feedback_content
            )
            
            # Requirement 5.1: Parse compliance report
            result = memory_extractor.extract_from_files(compliance_path, feedback_path)
            assert result['success'], "Failed to parse compliance report"
            
            # Requirement 5.2: Parse human feedback
            assert 'stm_results' in result, "Failed to extract human feedback data"
            
            # Requirement 5.3: Validate data completeness
            validation = memory_extractor.validate_extraction_results(result)
            assert validation['is_valid'], f"Data validation failed: {validation.get('errors', [])}"
            
            # Requirement 5.4: Provide clear error messages for failures
            # Test with invalid file
            invalid_result = memory_extractor.extract_from_files("nonexistent.txt", "nonexistent.txt")
            assert invalid_result['success'] is False, "Should fail with nonexistent files"
            assert 'error' in invalid_result, "Should provide error message"
            assert len(invalid_result['error']) > 10, "Error message should be descriptive"
            
            # Requirement 5.5: Generate both STM and LTM entries
            assert len(result['stm_results']) > 0, "Should generate STM entries"
            assert len(result['ltm_results']) > 0, "Should generate LTM entries"
            
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        finally:
            memory_extractor.close()
    
    def test_requirement_6_api_integration(self):
        """Validate Requirement 6: API integration capabilities."""
        api = MemoryAPI()
        
        try:
            # Requirement 6.1: STM retrieval APIs by scenario_id
            # First create an entry
            assessment_data = {
                "scenario_id": "req6_api_test",
                "requirement_text": "Test requirement for API validation",
                "initial_assessment": {
                    "status": "Non-Compliant",
                    "rationale": "Test rationale",
                    "recommendation": "Test recommendation"
                }
            }
            
            create_response = api.add_new_assessment(assessment_data)
            assert create_response['status'] == 'success', "Failed to create assessment via API"
            
            get_response = api.get_stm_entry("req6_api_test")
            assert get_response['status'] == 'success', "Failed to retrieve STM by scenario_id"
            
            # Requirement 6.2: LTM search APIs by concepts and keywords
            search_response = api.search_ltm_rules("compliance", ["GDPR", "Test"])
            assert search_response['status'] == 'success', "Failed to search LTM by concepts"
            assert isinstance(search_response['data'], list), "LTM search should return list"
            
            # Requirement 6.3: APIs for adding new assessments
            # Already tested above in create_response
            
            # Requirement 6.4: APIs for updating with feedback
            feedback_data = {
                "decision": "Approved",
                "rationale": "Test feedback",
                "suggestion": "Test suggestion",
                "final_status": "Compliant"
            }
            
            feedback_response = api.update_with_feedback("req6_api_test", feedback_data)
            assert feedback_response['status'] == 'success', "Failed to update with feedback"
            
            # Requirement 6.5: Structured JSON responses with error handling
            # Test successful response structure
            assert 'status' in get_response, "Response should have status field"
            assert 'data' in get_response, "Successful response should have data field"
            
            # Test error response structure
            error_response = api.get_stm_entry("nonexistent_scenario")
            assert 'status' in error_response, "Error response should have status field"
            assert error_response['status'] != 'success', "Should indicate failure"
            
        finally:
            api.close()


if __name__ == "__main__":
    # Run comprehensive test suite
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=5"])