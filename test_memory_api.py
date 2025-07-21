"""
Unit tests for Memory API.

Tests all API endpoints with proper error handling and JSON response formatting.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from memory_management.api.memory_api import MemoryAPI, ValidationError, NotFoundError
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule


class TestMemoryAPI:
    """Test suite for Memory API functionality."""
    
    @pytest.fixture
    def mock_stm_processor(self):
        """Mock STM processor for testing."""
        mock = Mock()
        mock.get_entry.return_value = None
        mock.create_entry.return_value = None
        mock.update_entry.return_value = None
        mock.add_human_feedback.return_value = None
        mock.set_final_status.return_value = None
        mock.list_entries.return_value = []
        mock.get_entries_by_status.return_value = []
        mock.get_entries_with_feedback.return_value = []
        mock.get_entries_without_feedback.return_value = []
        mock.get_stats.return_value = {"total_entries": 0}
        mock.get_traceability_info.return_value = {}
        mock.redis_client = Mock()
        mock.redis_client.ping.return_value = True
        return mock
    
    @pytest.fixture
    def mock_ltm_manager(self):
        """Mock LTM manager for testing."""
        mock = Mock()
        mock.get_ltm_rule.return_value = None
        mock.search_ltm_rules.return_value = []
        mock.semantic_search_rules.return_value = []
        mock.get_concept_relationships.return_value = []
        mock.get_rule_traceability.return_value = {}
        mock.get_rules_by_source_scenario.return_value = []
        mock.get_complete_audit_trail.return_value = {}
        mock.get_all_rules.return_value = []
        
        # Mock Neo4j driver and session
        mock.driver = Mock()
        session_mock = Mock()
        session_mock.run.return_value = None
        mock.driver.session.return_value.__enter__ = Mock(return_value=session_mock)
        mock.driver.session.return_value.__exit__ = Mock(return_value=None)
        
        return mock
    
    @pytest.fixture
    def memory_api(self, mock_stm_processor, mock_ltm_manager):
        """Memory API instance with mocked dependencies."""
        return MemoryAPI(stm_processor=mock_stm_processor, ltm_manager=mock_ltm_manager)
    
    @pytest.fixture
    def sample_stm_entry(self):
        """Sample STM entry for testing."""
        return STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="User must provide consent for data processing",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="Bundled consent violates GDPR",
                recommendation="Implement separate opt-in checkboxes"
            )
        )
    
    @pytest.fixture
    def sample_ltm_rule(self):
        """Sample LTM rule for testing."""
        return LTMRule(
            rule_id="GDPR_Consent_Separate_01",
            rule_text="Consent must be separate and specific for each purpose",
            related_concepts=["Consent", "GDPR", "Data Processing"],
            source_scenario_id=["ecommerce_r1_consent"],
            confidence_score=0.95
        )
    
    def test_format_success_response(self, memory_api):
        """Test successful response formatting."""
        data = {"test": "data"}
        response = memory_api._format_success_response(data, "Test message")
        
        assert response["status"] == "success"
        assert response["message"] == "Test message"
        assert response["data"] == data
        assert "timestamp" in response
    
    def test_format_error_response(self, memory_api):
        """Test error response formatting."""
        response = memory_api._format_error_response("Test error", "test_error", {"detail": "info"})
        
        assert response["status"] == "error"
        assert response["error_type"] == "test_error"
        assert response["message"] == "Test error"
        assert response["details"] == {"detail": "info"}
        assert "timestamp" in response
    
    def test_validate_scenario_id_valid(self, memory_api):
        """Test valid scenario ID validation."""
        # Should not raise exception
        memory_api._validate_scenario_id("ecommerce_r1_consent")
    
    def test_validate_scenario_id_invalid(self, memory_api):
        """Test invalid scenario ID validation."""
        with pytest.raises(ValidationError):
            memory_api._validate_scenario_id("")
        
        with pytest.raises(ValidationError):
            memory_api._validate_scenario_id("invalid_format")
        
        with pytest.raises(ValidationError):
            memory_api._validate_scenario_id(None)
    
    def test_validate_assessment_data_valid(self, memory_api):
        """Test valid assessment data validation."""
        data = {
            "scenario_id": "ecommerce_r1_consent",
            "requirement_text": "Test requirement",
            "initial_assessment": {
                "status": "Compliant",
                "rationale": "Test rationale",
                "recommendation": "Test recommendation"
            }
        }
        # Should not raise exception
        memory_api._validate_assessment_data(data)
    
    def test_validate_assessment_data_invalid(self, memory_api):
        """Test invalid assessment data validation."""
        # Missing required field
        with pytest.raises(ValidationError):
            memory_api._validate_assessment_data({"scenario_id": "test"})
        
        # Invalid initial_assessment structure
        with pytest.raises(ValidationError):
            memory_api._validate_assessment_data({
                "scenario_id": "ecommerce_r1_consent",
                "requirement_text": "Test",
                "initial_assessment": "invalid"
            })
    
    def test_validate_feedback_data_valid(self, memory_api):
        """Test valid feedback data validation."""
        data = {
            "decision": "Approve",
            "rationale": "Test rationale",
            "suggestion": "Test suggestion"
        }
        # Should not raise exception
        memory_api._validate_feedback_data(data)
    
    def test_validate_feedback_data_invalid(self, memory_api):
        """Test invalid feedback data validation."""
        with pytest.raises(ValidationError):
            memory_api._validate_feedback_data({"decision": "Approve"})
    
    # STM API Tests
    
    def test_get_stm_entry_success(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test successful STM entry retrieval."""
        mock_stm_processor.get_entry.return_value = sample_stm_entry
        mock_stm_processor.get_traceability_info.return_value = {"test": "traceability"}
        
        response = memory_api.get_stm_entry("ecommerce_r1_consent")
        
        assert response["status"] == "success"
        assert "stm_entry" in response["data"]
        assert "traceability" in response["data"]
        mock_stm_processor.get_entry.assert_called_once_with("ecommerce_r1_consent")
    
    def test_get_stm_entry_not_found(self, memory_api, mock_stm_processor):
        """Test STM entry not found."""
        mock_stm_processor.get_entry.return_value = None
        
        response = memory_api.get_stm_entry("ecommerce_r1_nonexistent")
        
        assert response["status"] == "error"
        assert response["error_type"] == "notfounderror"
    
    def test_get_stm_entry_invalid_id(self, memory_api):
        """Test STM entry retrieval with invalid ID."""
        response = memory_api.get_stm_entry("invalid")
        
        assert response["status"] == "error"
        assert response["error_type"] == "validationerror"
    
    def test_list_stm_entries_all(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test listing all STM entries."""
        mock_stm_processor.list_entries.return_value = [sample_stm_entry]
        
        response = memory_api.list_stm_entries()
        
        assert response["status"] == "success"
        assert response["data"]["count"] == 1
        assert len(response["data"]["entries"]) == 1
    
    def test_list_stm_entries_by_status(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test listing STM entries by status."""
        mock_stm_processor.get_entries_by_status.return_value = [sample_stm_entry]
        
        response = memory_api.list_stm_entries(status="Non-Compliant")
        
        assert response["status"] == "success"
        assert response["data"]["filters"]["status"] == "Non-Compliant"
        mock_stm_processor.get_entries_by_status.assert_called_once_with("Non-Compliant")
    
    def test_list_stm_entries_with_feedback(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test listing STM entries with feedback."""
        mock_stm_processor.get_entries_with_feedback.return_value = [sample_stm_entry]
        
        response = memory_api.list_stm_entries(has_feedback=True)
        
        assert response["status"] == "success"
        assert response["data"]["filters"]["has_feedback"] is True
        mock_stm_processor.get_entries_with_feedback.assert_called_once()
    
    def test_get_stm_stats(self, memory_api, mock_stm_processor):
        """Test STM statistics retrieval."""
        mock_stm_processor.get_stats.return_value = {"total_entries": 5, "entries_with_feedback": 2}
        
        response = memory_api.get_stm_stats()
        
        assert response["status"] == "success"
        assert response["data"]["total_entries"] == 5
        assert response["data"]["entries_with_feedback"] == 2
    
    # LTM API Tests
    
    def test_search_ltm_rules_structured(self, memory_api, mock_ltm_manager, sample_ltm_rule):
        """Test structured LTM rule search."""
        mock_ltm_manager.search_ltm_rules.return_value = [sample_ltm_rule]
        
        response = memory_api.search_ltm_rules(concepts=["Consent"], keywords=["GDPR"])
        
        assert response["status"] == "success"
        assert response["data"]["search_type"] == "structured"
        assert response["data"]["count"] == 1
        mock_ltm_manager.search_ltm_rules.assert_called_once_with(
            concepts=["Consent"], keywords=["GDPR"], policy=None, limit=10
        )
    
    def test_search_ltm_rules_semantic(self, memory_api, mock_ltm_manager, sample_ltm_rule):
        """Test semantic LTM rule search."""
        mock_ltm_manager.semantic_search_rules.return_value = [(sample_ltm_rule, 0.85)]
        
        response = memory_api.search_ltm_rules(query="consent requirements")
        
        assert response["status"] == "success"
        assert response["data"]["search_type"] == "semantic"
        assert response["data"]["count"] == 1
        assert response["data"]["rules"][0]["relevance_score"] == 0.85
        mock_ltm_manager.semantic_search_rules.assert_called_once_with("consent requirements", 10)
    
    def test_get_ltm_rule_success(self, memory_api, mock_ltm_manager, sample_ltm_rule):
        """Test successful LTM rule retrieval."""
        mock_ltm_manager.get_ltm_rule.return_value = sample_ltm_rule
        mock_ltm_manager.get_rule_traceability.return_value = {"test": "traceability"}
        
        response = memory_api.get_ltm_rule("GDPR_Consent_Separate_01")
        
        assert response["status"] == "success"
        assert "ltm_rule" in response["data"]
        assert "traceability" in response["data"]
    
    def test_get_ltm_rule_not_found(self, memory_api, mock_ltm_manager):
        """Test LTM rule not found."""
        mock_ltm_manager.get_ltm_rule.return_value = None
        
        response = memory_api.get_ltm_rule("nonexistent_rule")
        
        assert response["status"] == "error"
        assert response["error_type"] == "notfounderror"
    
    def test_get_rules_by_concept(self, memory_api, mock_ltm_manager):
        """Test getting rules by concept."""
        mock_ltm_manager.get_concept_relationships.return_value = [{"rule_id": "test_rule"}]
        
        response = memory_api.get_rules_by_concept("Consent")
        
        assert response["status"] == "success"
        assert response["data"]["concept"] == "Consent"
        assert response["data"]["count"] == 1
    
    # Assessment Management API Tests
    
    def test_add_new_assessment_success(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test successful assessment creation."""
        mock_stm_processor.create_entry.return_value = sample_stm_entry
        
        assessment_data = {
            "scenario_id": "ecommerce_r1_consent",
            "requirement_text": "Test requirement",
            "initial_assessment": {
                "status": "Non-Compliant",
                "rationale": "Test rationale",
                "recommendation": "Test recommendation"
            }
        }
        
        response = memory_api.add_new_assessment(assessment_data)
        
        assert response["status"] == "success"
        assert "stm_entry" in response["data"]
        assert response["data"]["scenario_id"] == "ecommerce_r1_consent"
    
    def test_add_new_assessment_validation_error(self, memory_api):
        """Test assessment creation with validation error."""
        invalid_data = {"scenario_id": "test"}
        
        response = memory_api.add_new_assessment(invalid_data)
        
        assert response["status"] == "error"
        assert response["error_type"] == "validation_error"
    
    def test_add_new_assessment_conflict(self, memory_api, mock_stm_processor):
        """Test assessment creation with conflict (duplicate scenario_id)."""
        mock_stm_processor.create_entry.side_effect = ValueError("Entry already exists")
        
        assessment_data = {
            "scenario_id": "ecommerce_r1_consent",
            "requirement_text": "Test requirement",
            "initial_assessment": {
                "status": "Compliant",
                "rationale": "Test rationale",
                "recommendation": "Test recommendation"
            }
        }
        
        response = memory_api.add_new_assessment(assessment_data)
        
        assert response["status"] == "error"
        assert response["error_type"] == "conflict_error"
    
    def test_update_with_feedback_success(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test successful feedback update."""
        # Add feedback to sample entry
        sample_stm_entry.human_feedback = HumanFeedback(
            decision="Approve",
            rationale="Analysis is correct",
            suggestion="Implement recommendation"
        )
        mock_stm_processor.add_human_feedback.return_value = sample_stm_entry
        mock_stm_processor.set_final_status.return_value = sample_stm_entry
        
        feedback_data = {
            "decision": "Approve",
            "rationale": "Analysis is correct",
            "suggestion": "Implement recommendation",
            "final_status": "Non-Compliant"
        }
        
        response = memory_api.update_with_feedback("ecommerce_r1_consent", feedback_data)
        
        assert response["status"] == "success"
        assert "updated_stm_entry" in response["data"]
        assert "generated_ltm_rules" in response["data"]
    
    def test_update_with_feedback_not_found(self, memory_api, mock_stm_processor):
        """Test feedback update for non-existent entry."""
        mock_stm_processor.add_human_feedback.return_value = None
        
        feedback_data = {
            "decision": "Approve",
            "rationale": "Test rationale",
            "suggestion": "Test suggestion"
        }
        
        response = memory_api.update_with_feedback("ecommerce_r1_nonexistent", feedback_data)
        
        assert response["status"] == "error"
        assert response["error_type"] == "notfounderror"
    
    def test_update_stm_entry_success(self, memory_api, mock_stm_processor, sample_stm_entry):
        """Test successful STM entry update."""
        mock_stm_processor.update_entry.return_value = sample_stm_entry
        
        updates = {"requirement_text": "Updated requirement"}
        
        response = memory_api.update_stm_entry("ecommerce_r1_consent", updates)
        
        assert response["status"] == "success"
        assert "updated_stm_entry" in response["data"]
        assert response["data"]["updated_fields"] == ["requirement_text"]
    
    # Traceability API Tests
    
    def test_get_traceability_chain_success(self, memory_api, mock_stm_processor, mock_ltm_manager, sample_ltm_rule):
        """Test successful traceability chain retrieval."""
        mock_stm_processor.get_traceability_info.return_value = {
            "stm_entry": {"scenario_id": "ecommerce_r1_consent"},
            "has_human_feedback": True,
            "final_status": "Non-Compliant"
        }
        mock_ltm_manager.get_rules_by_source_scenario.return_value = [sample_ltm_rule]
        mock_ltm_manager.get_complete_audit_trail.return_value = {"audit": "trail"}
        
        response = memory_api.get_traceability_chain("ecommerce_r1_consent")
        
        assert response["status"] == "success"
        assert "stm_traceability" in response["data"]
        assert "derived_ltm_rules" in response["data"]
        assert "rule_audit_trails" in response["data"]
        assert "traceability_summary" in response["data"]
    
    def test_get_rule_audit_trail_success(self, memory_api, mock_ltm_manager):
        """Test successful rule audit trail retrieval."""
        mock_ltm_manager.get_complete_audit_trail.return_value = {"audit": "trail"}
        
        response = memory_api.get_rule_audit_trail("GDPR_Consent_Separate_01")
        
        assert response["status"] == "success"
        assert response["data"] == {"audit": "trail"}
    
    def test_get_rule_audit_trail_not_found(self, memory_api, mock_ltm_manager):
        """Test rule audit trail for non-existent rule."""
        mock_ltm_manager.get_complete_audit_trail.return_value = {}
        
        response = memory_api.get_rule_audit_trail("nonexistent_rule")
        
        assert response["status"] == "error"
        assert response["error_type"] == "notfounderror"
    
    # Health and Status API Tests
    
    def test_health_check_healthy(self, memory_api, mock_stm_processor, mock_ltm_manager):
        """Test health check with all systems healthy."""
        response = memory_api.health_check()
        
        assert response["status"] == "success"
        assert response["data"]["overall_status"] == "healthy"
        assert response["data"]["components"]["redis_connection"] == "healthy"
        assert response["data"]["components"]["neo4j_connection"] == "healthy"
    
    def test_health_check_redis_unhealthy(self, memory_api, mock_stm_processor):
        """Test health check with Redis unhealthy."""
        mock_stm_processor.redis_client.ping.side_effect = Exception("Connection failed")
        
        response = memory_api.health_check()
        
        assert response["status"] == "success"
        assert response["data"]["overall_status"] == "degraded"
        assert "unhealthy" in response["data"]["components"]["redis_connection"]
    
    def test_get_system_stats(self, memory_api, mock_stm_processor, mock_ltm_manager, sample_ltm_rule):
        """Test system statistics retrieval."""
        mock_stm_processor.get_stats.return_value = {"total_entries": 10}
        mock_ltm_manager.get_all_rules.return_value = [sample_ltm_rule]
        
        response = memory_api.get_system_stats()
        
        assert response["status"] == "success"
        assert "stm_stats" in response["data"]
        assert "ltm_stats" in response["data"]
        assert "system_info" in response["data"]
        assert response["data"]["ltm_stats"]["total_rules"] == 1
    
    # Error Handling Tests
    
    def test_internal_error_handling(self, memory_api, mock_stm_processor):
        """Test internal error handling."""
        mock_stm_processor.get_entry.side_effect = Exception("Database error")
        
        response = memory_api.get_stm_entry("ecommerce_r1_consent")
        
        assert response["status"] == "error"
        assert response["error_type"] == "internal_error"
        assert response["message"] == "Internal server error"
    
    def test_close_connections(self, memory_api, mock_ltm_manager):
        """Test closing database connections."""
        # Should not raise exception
        memory_api.close()
        mock_ltm_manager.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])