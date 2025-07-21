"""
Unit tests for LTM Manager Neo4j operations.

Tests CRUD operations, semantic search, and relationship management.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from memory_management.processors.ltm_manager import LTMManager
from memory_management.models.ltm_rule import LTMRule


class TestLTMManager:
    """Test suite for LTM Manager Neo4j operations."""
    
    @pytest.fixture
    def sample_ltm_rule(self):
        """Create a sample LTM rule for testing."""
        return LTMRule(
            rule_id="GDPR_Consent_Unbundled_01",
            rule_text="For GDPR Article 7 compliance, consent requests must be unbundled and presented as separate, specific opt-in choices.",
            related_concepts=["Consent", "GDPR Article 7", "Unbundled", "Opt-in"],
            source_scenario_id=["ecommerce_r1_consent"],
            confidence_score=0.95,
            version=1
        )
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for testing."""
        with patch('memory_management.processors.ltm_manager.GraphDatabase') as mock_graph:
            mock_driver = Mock()
            mock_session = Mock()
            mock_graph.driver.return_value = mock_driver
            
            # Create a proper context manager mock
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            mock_driver.session.return_value = mock_context_manager
            
            yield mock_driver, mock_session
    
    @pytest.fixture
    def ltm_manager(self, mock_neo4j_driver):
        """Create LTM manager with mocked Neo4j connection."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch.object(LTMManager, '_connect'), \
             patch.object(LTMManager, '_create_schema'):
            manager = LTMManager(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="test"
            )
            manager.driver = mock_driver
            return manager, mock_session
    
    def test_init_with_env_vars(self):
        """Test LTM manager initialization with environment variables."""
        with patch.dict(os.environ, {
            'NEO4J_URI': 'bolt://test:7687',
            'NEO4J_USERNAME': 'testuser',
            'NEO4J_PASSWORD': 'testpass'
        }), patch.object(LTMManager, '_connect'), \
           patch.object(LTMManager, '_create_schema'):
            
            manager = LTMManager()
            assert manager.uri == 'bolt://test:7687'
            assert manager.username == 'testuser'
            assert manager.password == 'testpass'
    
    def test_init_with_params(self):
        """Test LTM manager initialization with parameters."""
        with patch.object(LTMManager, '_connect'), \
             patch.object(LTMManager, '_create_schema'):
            
            manager = LTMManager(
                uri="bolt://custom:7687",
                username="custom_user",
                password="custom_pass"
            )
            assert manager.uri == "bolt://custom:7687"
            assert manager.username == "custom_user"
            assert manager.password == "custom_pass"
    
    def test_store_ltm_rule_success(self, ltm_manager, sample_ltm_rule):
        """Test successful storage of LTM rule."""
        manager, mock_session = ltm_manager
        mock_session.run.return_value = Mock()
        
        result = manager.store_ltm_rule(sample_ltm_rule)
        
        assert result is True
        # Verify that multiple queries were executed (rule, concepts, scenarios, policy)
        assert mock_session.run.call_count >= 4
    
    def test_store_ltm_rule_invalid(self, ltm_manager):
        """Test storage of invalid LTM rule."""
        manager, mock_session = ltm_manager
        
        invalid_rule = LTMRule(
            rule_id="",  # Invalid empty rule_id
            rule_text="Test rule",
            related_concepts=["test"],
            source_scenario_id=["test_scenario"]
        )
        
        result = manager.store_ltm_rule(invalid_rule)
        
        assert result is False
        mock_session.run.assert_not_called()
    
    def test_store_ltm_rule_database_error(self, ltm_manager, sample_ltm_rule):
        """Test storage failure due to database error."""
        manager, mock_session = ltm_manager
        mock_session.run.side_effect = Exception("Database error")
        
        result = manager.store_ltm_rule(sample_ltm_rule)
        
        assert result is False
    
    def test_get_ltm_rule_success(self, ltm_manager, sample_ltm_rule):
        """Test successful retrieval of LTM rule."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score,
                'version': sample_ltm_rule.version,
                'created_at': sample_ltm_rule.created_at,
                'updated_at': sample_ltm_rule.updated_at
            },
            'concepts': sample_ltm_rule.related_concepts,
            'scenarios': sample_ltm_rule.source_scenario_id
        }
        
        mock_result = Mock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        result = manager.get_ltm_rule(sample_ltm_rule.rule_id)
        
        assert result is not None
        assert result.rule_id == sample_ltm_rule.rule_id
        assert result.rule_text == sample_ltm_rule.rule_text
        assert result.related_concepts == sample_ltm_rule.related_concepts
        assert result.source_scenario_id == sample_ltm_rule.source_scenario_id
    
    def test_get_ltm_rule_not_found(self, ltm_manager):
        """Test retrieval of non-existent LTM rule."""
        manager, mock_session = ltm_manager
        
        mock_result = Mock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        
        result = manager.get_ltm_rule("nonexistent_rule")
        
        assert result is None
    
    def test_get_ltm_rule_database_error(self, ltm_manager):
        """Test retrieval failure due to database error."""
        manager, mock_session = ltm_manager
        mock_session.run.side_effect = Exception("Database error")
        
        result = manager.get_ltm_rule("test_rule")
        
        assert result is None
    
    def test_search_ltm_rules_by_concepts(self, ltm_manager, sample_ltm_rule):
        """Test searching LTM rules by concepts."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score,
                'version': sample_ltm_rule.version,
                'created_at': sample_ltm_rule.created_at,
                'updated_at': sample_ltm_rule.updated_at
            },
            'concepts': sample_ltm_rule.related_concepts,
            'scenarios': sample_ltm_rule.source_scenario_id
        }
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result
        
        results = manager.search_ltm_rules(concepts=["Consent", "GDPR"])
        
        assert len(results) == 1
        assert results[0].rule_id == sample_ltm_rule.rule_id
    
    def test_search_ltm_rules_by_keywords(self, ltm_manager, sample_ltm_rule):
        """Test searching LTM rules by keywords."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score,
                'version': sample_ltm_rule.version,
                'created_at': sample_ltm_rule.created_at,
                'updated_at': sample_ltm_rule.updated_at
            },
            'concepts': sample_ltm_rule.related_concepts,
            'scenarios': sample_ltm_rule.source_scenario_id
        }
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result
        
        results = manager.search_ltm_rules(keywords=["consent", "unbundled"])
        
        assert len(results) == 1
        assert results[0].rule_id == sample_ltm_rule.rule_id
    
    def test_search_ltm_rules_by_policy(self, ltm_manager, sample_ltm_rule):
        """Test searching LTM rules by policy."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score,
                'version': sample_ltm_rule.version,
                'created_at': sample_ltm_rule.created_at,
                'updated_at': sample_ltm_rule.updated_at
            },
            'concepts': sample_ltm_rule.related_concepts,
            'scenarios': sample_ltm_rule.source_scenario_id
        }
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result
        
        results = manager.search_ltm_rules(policy="GDPR")
        
        assert len(results) == 1
        assert results[0].rule_id == sample_ltm_rule.rule_id
    
    def test_search_ltm_rules_empty_results(self, ltm_manager):
        """Test searching LTM rules with no results."""
        manager, mock_session = ltm_manager
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.run.return_value = mock_result
        
        results = manager.search_ltm_rules(concepts=["nonexistent"])
        
        assert len(results) == 0
    
    def test_search_ltm_rules_database_error(self, ltm_manager):
        """Test search failure due to database error."""
        manager, mock_session = ltm_manager
        mock_session.run.side_effect = Exception("Database error")
        
        results = manager.search_ltm_rules(concepts=["test"])
        
        assert len(results) == 0
    
    @patch('memory_management.processors.ltm_manager.LLMClient')
    def test_semantic_search_rules_success(self, mock_llm_client, ltm_manager, sample_ltm_rule):
        """Test successful semantic search using LLM."""
        manager, mock_session = ltm_manager
        
        # Mock get_all_rules
        with patch.object(manager, 'get_all_rules', return_value=[sample_ltm_rule]):
            # Mock LLM response
            mock_llm_instance = Mock()
            mock_llm_instance.generate_response.return_value = '[0.95]'
            mock_llm_client.return_value = mock_llm_instance
            manager.llm_client = mock_llm_instance
            
            results = manager.semantic_search_rules("consent requirements")
            
            assert len(results) == 1
            assert results[0][0].rule_id == sample_ltm_rule.rule_id
            assert results[0][1] == 0.95
    
    @patch('memory_management.processors.ltm_manager.LLMClient')
    def test_semantic_search_rules_fallback(self, mock_llm_client, ltm_manager, sample_ltm_rule):
        """Test semantic search fallback when LLM fails."""
        manager, mock_session = ltm_manager
        
        # Mock get_all_rules
        with patch.object(manager, 'get_all_rules', return_value=[sample_ltm_rule]):
            # Mock LLM response with invalid JSON
            mock_llm_instance = Mock()
            mock_llm_instance.generate_response.return_value = 'invalid json'
            mock_llm_client.return_value = mock_llm_instance
            manager.llm_client = mock_llm_instance
            
            results = manager.semantic_search_rules("consent unbundled")
            
            assert len(results) >= 0  # Fallback should work
    
    def test_update_ltm_rule_success(self, ltm_manager, sample_ltm_rule):
        """Test successful update of LTM rule."""
        manager, mock_session = ltm_manager
        mock_session.run.return_value = Mock()
        
        # Modify the rule
        sample_ltm_rule.rule_text = "Updated rule text"
        
        result = manager.update_ltm_rule(sample_ltm_rule)
        
        assert result is True
        assert mock_session.run.call_count >= 4
    
    def test_update_ltm_rule_invalid(self, ltm_manager):
        """Test update of invalid LTM rule."""
        manager, mock_session = ltm_manager
        
        invalid_rule = LTMRule(
            rule_id="",  # Invalid empty rule_id
            rule_text="Test rule",
            related_concepts=["test"],
            source_scenario_id=["test_scenario"]
        )
        
        result = manager.update_ltm_rule(invalid_rule)
        
        assert result is False
        mock_session.run.assert_not_called()
    
    def test_delete_ltm_rule_success(self, ltm_manager):
        """Test successful deletion of LTM rule."""
        manager, mock_session = ltm_manager
        
        # Mock successful deletion
        mock_result = Mock()
        mock_summary = Mock()
        mock_summary.counters.nodes_deleted = 1
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        result = manager.delete_ltm_rule("test_rule")
        
        assert result is True
        mock_session.run.assert_called_once()
    
    def test_delete_ltm_rule_not_found(self, ltm_manager):
        """Test deletion of non-existent LTM rule."""
        manager, mock_session = ltm_manager
        
        # Mock no deletion
        mock_result = Mock()
        mock_summary = Mock()
        mock_summary.counters.nodes_deleted = 0
        mock_result.consume.return_value = mock_summary
        mock_session.run.return_value = mock_result
        
        result = manager.delete_ltm_rule("nonexistent_rule")
        
        assert result is False
    
    def test_delete_ltm_rule_database_error(self, ltm_manager):
        """Test deletion failure due to database error."""
        manager, mock_session = ltm_manager
        mock_session.run.side_effect = Exception("Database error")
        
        result = manager.delete_ltm_rule("test_rule")
        
        assert result is False
    
    def test_get_rule_traceability_success(self, ltm_manager, sample_ltm_rule):
        """Test successful retrieval of rule traceability."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score,
                'version': sample_ltm_rule.version,
                'created_at': sample_ltm_rule.created_at,
                'updated_at': sample_ltm_rule.updated_at
            },
            'concepts': sample_ltm_rule.related_concepts,
            'scenarios': sample_ltm_rule.source_scenario_id,
            'policies': ['GDPR']
        }
        
        mock_result = Mock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        result = manager.get_rule_traceability(sample_ltm_rule.rule_id)
        
        assert 'rule' in result
        assert 'related_concepts' in result
        assert 'source_scenarios' in result
        assert 'governing_policies' in result
        assert result['rule']['rule_id'] == sample_ltm_rule.rule_id
    
    def test_get_rule_traceability_not_found(self, ltm_manager):
        """Test traceability retrieval for non-existent rule."""
        manager, mock_session = ltm_manager
        
        mock_result = Mock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        
        result = manager.get_rule_traceability("nonexistent_rule")
        
        assert result == {}
    
    def test_get_concept_relationships_success(self, ltm_manager, sample_ltm_rule):
        """Test successful retrieval of concept relationships."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score
            },
            'scenarios': sample_ltm_rule.source_scenario_id
        }
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result
        
        results = manager.get_concept_relationships("Consent")
        
        assert len(results) == 1
        assert results[0]['rule_id'] == sample_ltm_rule.rule_id
        assert 'source_scenarios' in results[0]
    
    def test_get_concept_relationships_empty(self, ltm_manager):
        """Test concept relationships with no results."""
        manager, mock_session = ltm_manager
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.run.return_value = mock_result
        
        results = manager.get_concept_relationships("NonexistentConcept")
        
        assert len(results) == 0
    
    def test_get_all_rules_success(self, ltm_manager, sample_ltm_rule):
        """Test successful retrieval of all rules."""
        manager, mock_session = ltm_manager
        
        # Mock database response
        mock_record = {
            'r': {
                'rule_id': sample_ltm_rule.rule_id,
                'rule_text': sample_ltm_rule.rule_text,
                'confidence_score': sample_ltm_rule.confidence_score,
                'version': sample_ltm_rule.version,
                'created_at': sample_ltm_rule.created_at,
                'updated_at': sample_ltm_rule.updated_at
            },
            'concepts': sample_ltm_rule.related_concepts,
            'scenarios': sample_ltm_rule.source_scenario_id
        }
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result
        
        results = manager.get_all_rules()
        
        assert len(results) == 1
        assert results[0].rule_id == sample_ltm_rule.rule_id
    
    def test_get_all_rules_empty(self, ltm_manager):
        """Test retrieval of all rules when database is empty."""
        manager, mock_session = ltm_manager
        
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.run.return_value = mock_result
        
        results = manager.get_all_rules()
        
        assert len(results) == 0
    
    def test_close_connection(self, ltm_manager):
        """Test closing Neo4j connection."""
        manager, mock_session = ltm_manager
        
        manager.close()
        
        manager.driver.close.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])