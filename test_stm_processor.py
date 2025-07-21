"""
Unit tests for STM Processor.
"""
import pytest
import redis
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from memory_management.processors.stm_processor import STMProcessor
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback


class TestSTMProcessor:
    """Test cases for STMProcessor class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_client = Mock(spec=redis.Redis)
        mock_client.ping.return_value = True
        mock_client.decode_responses = True
        return mock_client
    
    @pytest.fixture
    def processor(self, mock_redis):
        """STM processor with mocked Redis."""
        with patch('memory_management.processors.stm_processor.redis.Redis', return_value=mock_redis):
            return STMProcessor()
    
    @pytest.fixture
    def sample_assessment(self):
        """Sample initial assessment."""
        return InitialAssessment(
            status="Non-Compliant",
            rationale="Bundled consent violates GDPR Art. 7",
            recommendation="Implement separate opt-in checkboxes"
        )
    
    @pytest.fixture
    def sample_entry(self, sample_assessment):
        """Sample STM entry."""
        return STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="During account signup, the user must agree to terms",
            initial_assessment=sample_assessment
        )
    
    def test_init_successful_connection(self, mock_redis):
        """Test successful Redis connection during initialization."""
        with patch('memory_management.processors.stm_processor.redis.Redis', return_value=mock_redis):
            processor = STMProcessor()
            mock_redis.ping.assert_called_once()
            assert processor.redis_client == mock_redis
    
    def test_init_connection_failure(self):
        """Test Redis connection failure during initialization."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")
        
        with patch('memory_management.processors.stm_processor.redis.Redis', return_value=mock_redis):
            with pytest.raises(redis.ConnectionError):
                STMProcessor()
    
    def test_create_entry_success(self, processor, sample_assessment):
        """Test successful entry creation."""
        processor.redis_client.get.return_value = None  # Entry doesn't exist
        processor.redis_client.setex.return_value = True
        
        entry = processor.create_entry(
            "test_scenario",
            "Test requirement text",
            sample_assessment
        )
        
        assert entry.scenario_id == "test_scenario"
        assert entry.requirement_text == "Test requirement text"
        assert entry.initial_assessment == sample_assessment
        processor.redis_client.setex.assert_called_once()
    
    def test_create_entry_already_exists(self, processor, sample_assessment, sample_entry):
        """Test creating entry that already exists."""
        processor.redis_client.get.return_value = sample_entry.to_json()
        
        with pytest.raises(ValueError, match="already exists"):
            processor.create_entry(
                "ecommerce_r1_consent",
                "Test requirement text",
                sample_assessment
            )
    
    def test_get_entry_success(self, processor, sample_entry):
        """Test successful entry retrieval."""
        processor.redis_client.get.return_value = sample_entry.to_json()
        
        retrieved = processor.get_entry("ecommerce_r1_consent")
        
        assert retrieved is not None
        assert retrieved.scenario_id == sample_entry.scenario_id
        assert retrieved.requirement_text == sample_entry.requirement_text
    
    def test_get_entry_not_found(self, processor):
        """Test retrieving non-existent entry."""
        processor.redis_client.get.return_value = None
        
        result = processor.get_entry("nonexistent")
        
        assert result is None
    
    def test_get_entry_invalid_json(self, processor):
        """Test retrieving entry with invalid JSON."""
        processor.redis_client.get.return_value = "invalid json"
        
        result = processor.get_entry("test_scenario")
        
        assert result is None
    
    def test_update_entry_success(self, processor, sample_entry):
        """Test successful entry update."""
        processor.redis_client.get.return_value = sample_entry.to_json()
        processor.redis_client.setex.return_value = True
        
        updated = processor.update_entry(
            "ecommerce_r1_consent",
            final_status="Compliant"
        )
        
        assert updated is not None
        assert updated.final_status == "Compliant"
        assert updated.updated_at is not None
        processor.redis_client.setex.assert_called_once()
    
    def test_update_entry_not_found(self, processor):
        """Test updating non-existent entry."""
        processor.redis_client.get.return_value = None
        
        result = processor.update_entry("nonexistent", final_status="Compliant")
        
        assert result is None
    
    def test_add_human_feedback_success(self, processor, sample_entry):
        """Test adding human feedback to entry."""
        processor.redis_client.get.return_value = sample_entry.to_json()
        processor.redis_client.setex.return_value = True
        
        updated = processor.add_human_feedback(
            "ecommerce_r1_consent",
            "No change",
            "Agent's analysis is correct",
            "Implement separate checkboxes"
        )
        
        assert updated is not None
        assert updated.human_feedback is not None
        assert updated.human_feedback.decision == "No change"
        processor.redis_client.setex.assert_called_once()
    
    def test_set_final_status_success(self, processor, sample_entry):
        """Test setting final status."""
        processor.redis_client.get.return_value = sample_entry.to_json()
        processor.redis_client.setex.return_value = True
        
        updated = processor.set_final_status("ecommerce_r1_consent", "Compliant")
        
        assert updated is not None
        assert updated.final_status == "Compliant"
        processor.redis_client.setex.assert_called_once()
    
    def test_set_final_status_invalid(self, processor, sample_entry):
        """Test setting invalid final status."""
        processor.redis_client.get.return_value = sample_entry.to_json()
        
        with pytest.raises(ValueError, match="Invalid status"):
            processor.set_final_status("ecommerce_r1_consent", "InvalidStatus")
    
    def test_delete_entry_success(self, processor):
        """Test successful entry deletion."""
        processor.redis_client.delete.return_value = 1
        
        result = processor.delete_entry("test_scenario")
        
        assert result is True
        processor.redis_client.delete.assert_called_once_with("stm:test_scenario")
    
    def test_delete_entry_not_found(self, processor):
        """Test deleting non-existent entry."""
        processor.redis_client.delete.return_value = 0
        
        result = processor.delete_entry("nonexistent")
        
        assert result is False
    
    def test_list_entries(self, processor, sample_entry):
        """Test listing all entries."""
        processor.redis_client.keys.return_value = ["stm:test1", "stm:test2"]
        processor.redis_client.get.side_effect = [
            sample_entry.to_json(),
            sample_entry.to_json()
        ]
        
        entries = processor.list_entries()
        
        assert len(entries) == 2
        assert all(isinstance(entry, STMEntry) for entry in entries)
    
    def test_get_entries_by_status(self, processor, sample_entry):
        """Test filtering entries by status."""
        # Mock list_entries to return sample entries
        with patch.object(processor, 'list_entries') as mock_list:
            mock_list.return_value = [sample_entry]
            
            entries = processor.get_entries_by_status("Non-Compliant")
            
            assert len(entries) == 1
            assert entries[0].initial_assessment.status == "Non-Compliant"
    
    def test_get_entries_with_feedback(self, processor, sample_entry):
        """Test getting entries with human feedback."""
        # Add feedback to sample entry
        sample_entry.human_feedback = HumanFeedback(
            decision="No change",
            rationale="Correct analysis",
            suggestion="Implement checkboxes"
        )
        
        with patch.object(processor, 'list_entries') as mock_list:
            mock_list.return_value = [sample_entry]
            
            entries = processor.get_entries_with_feedback()
            
            assert len(entries) == 1
            assert entries[0].human_feedback is not None
    
    def test_get_entries_without_feedback(self, processor, sample_entry):
        """Test getting entries without human feedback."""
        with patch.object(processor, 'list_entries') as mock_list:
            mock_list.return_value = [sample_entry]
            
            entries = processor.get_entries_without_feedback()
            
            assert len(entries) == 1
            assert entries[0].human_feedback is None
    
    def test_extend_ttl_success(self, processor):
        """Test extending TTL for existing entry."""
        processor.redis_client.exists.return_value = True
        processor.redis_client.expire.return_value = True
        
        result = processor.extend_ttl("test_scenario", 48)
        
        assert result is True
        processor.redis_client.expire.assert_called_once()
    
    def test_extend_ttl_not_found(self, processor):
        """Test extending TTL for non-existent entry."""
        processor.redis_client.exists.return_value = False
        
        result = processor.extend_ttl("nonexistent")
        
        assert result is False
    
    def test_get_stats(self, processor, sample_entry):
        """Test getting statistics."""
        # Create entry with feedback
        entry_with_feedback = STMEntry(
            scenario_id="test2",
            requirement_text="Test",
            initial_assessment=InitialAssessment("Compliant", "Good", "None"),
            human_feedback=HumanFeedback("Agree", "Correct", "None")
        )
        
        with patch.object(processor, 'list_entries') as mock_list:
            mock_list.return_value = [sample_entry, entry_with_feedback]
            
            stats = processor.get_stats()
            
            assert stats['total_entries'] == 2
            assert stats['entries_with_feedback'] == 1
            assert stats['entries_without_feedback'] == 1
            assert 'status_breakdown' in stats
    
    def test_cleanup_expired(self, processor):
        """Test cleanup of expired entries."""
        processor.redis_client.keys.return_value = ["stm:test1", "stm:test2"]
        processor.redis_client.exists.side_effect = [True, False]  # One expired
        
        cleaned = processor.cleanup_expired()
        
        assert cleaned == 1


if __name__ == "__main__":
    pytest.main([__file__])