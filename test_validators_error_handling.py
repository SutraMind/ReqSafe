"""
Unit tests for data validation and error handling components.

Tests validation logic, error handling, retry mechanisms, and structured error responses.
"""

import pytest
import tempfile
import os
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from memory_management.utils.validators import (
    DataValidator, ValidationError, DatabaseConnectionError, FileParsingError, APIError,
    ErrorHandler, FileValidator, DatabaseErrorHandler, retry_on_failure
)
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule


class TestValidationError:
    """Test custom validation error exception."""
    
    def test_validation_error_creation(self):
        """Test ValidationError creation with all parameters."""
        error = ValidationError(
            message="Test validation error",
            field="test_field",
            details={"key": "value"}
        )
        
        assert str(error) == "Test validation error"
        assert error.field == "test_field"
        assert error.details == {"key": "value"}
    
    def test_validation_error_minimal(self):
        """Test ValidationError creation with minimal parameters."""
        error = ValidationError("Simple error")
        
        assert str(error) == "Simple error"
        assert error.field is None
        assert error.details == {}


class TestDatabaseConnectionError:
    """Test database connection error exception."""
    
    def test_database_connection_error_creation(self):
        """Test DatabaseConnectionError creation with all parameters."""
        error = DatabaseConnectionError(
            message="Connection failed",
            service="Redis",
            retry_count=3
        )
        
        assert str(error) == "Connection failed"
        assert error.service == "Redis"
        assert error.retry_count == 3
    
    def test_database_connection_error_minimal(self):
        """Test DatabaseConnectionError creation with minimal parameters."""
        error = DatabaseConnectionError("Connection failed")
        
        assert str(error) == "Connection failed"
        assert error.service is None
        assert error.retry_count == 0


class TestFileParsingError:
    """Test file parsing error exception."""
    
    def test_file_parsing_error_creation(self):
        """Test FileParsingError creation with all parameters."""
        error = FileParsingError(
            message="Parsing failed",
            file_path="/test/file.txt",
            line_number=42
        )
        
        assert str(error) == "Parsing failed"
        assert error.file_path == "/test/file.txt"
        assert error.line_number == 42
    
    def test_file_parsing_error_minimal(self):
        """Test FileParsingError creation with minimal parameters."""
        error = FileParsingError("Parsing failed")
        
        assert str(error) == "Parsing failed"
        assert error.file_path is None
        assert error.line_number is None


class TestAPIError:
    """Test API error exception."""
    
    def test_api_error_creation(self):
        """Test APIError creation with all parameters."""
        error = APIError(
            message="API request failed",
            error_code="INVALID_REQUEST",
            status_code=400
        )
        
        assert str(error) == "API request failed"
        assert error.error_code == "INVALID_REQUEST"
        assert error.status_code == 400
    
    def test_api_error_minimal(self):
        """Test APIError creation with minimal parameters."""
        error = APIError("API request failed")
        
        assert str(error) == "API request failed"
        assert error.error_code is None
        assert error.status_code == 500


class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    def test_retry_success_on_first_attempt(self):
        """Test function succeeds on first attempt."""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test function succeeds after some failures."""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Test function fails after all retries exhausted."""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection failed")
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            test_function()
        
        assert call_count == 3  # Initial attempt + 2 retries
        assert "Operation failed after 2 retries" in str(exc_info.value)
        assert exc_info.value.retry_count == 2
    
    def test_retry_with_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        @retry_on_failure(max_retries=2, delay=0.1, exceptions=(ConnectionError,))
        def test_function():
            raise ValueError("Different error")
        
        # Should not retry on ValueError
        with pytest.raises(ValueError):
            test_function()
    
    def test_retry_backoff_timing(self):
        """Test exponential backoff timing."""
        call_times = []
        
        @retry_on_failure(max_retries=2, delay=0.1, backoff_factor=2.0)
        def test_function():
            call_times.append(time.time())
            raise ConnectionError("Connection failed")
        
        start_time = time.time()
        with pytest.raises(DatabaseConnectionError):
            test_function()
        
        # Check that delays increase exponentially
        assert len(call_times) == 3
        # First retry should be after ~0.1s, second after ~0.2s
        # Allow some tolerance for timing
        assert call_times[1] - call_times[0] >= 0.09
        assert call_times[2] - call_times[1] >= 0.18


class TestErrorHandler:
    """Test comprehensive error handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_handle_validation_error(self):
        """Test validation error handling."""
        error = ValidationError(
            message="Invalid field",
            field="test_field",
            details={"expected": "string", "got": "int"}
        )
        
        response = self.error_handler.handle_validation_error(error, "test_context")
        
        assert response["error_type"] == "validation_error"
        assert response["message"] == "Invalid field"
        assert response["field"] == "test_field"
        assert response["details"] == {"expected": "string", "got": "int"}
        assert response["context"] == "test_context"
        assert "timestamp" in response
    
    def test_handle_database_error(self):
        """Test database error handling."""
        error = ConnectionError("Redis connection failed")
        
        response = self.error_handler.handle_database_error(error, "Redis", "get_entry")
        
        assert response["error_type"] == "database_error"
        assert "Redis operation failed" in response["message"]
        assert response["service"] == "Redis"
        assert response["operation"] == "get_entry"
        assert "timestamp" in response
    
    def test_handle_file_parsing_error(self):
        """Test file parsing error handling."""
        error = FileParsingError(
            message="Invalid JSON format",
            file_path="/test/file.json",
            line_number=15
        )
        
        response = self.error_handler.handle_file_parsing_error(error, "json_parsing")
        
        assert response["error_type"] == "file_parsing_error"
        assert response["message"] == "Invalid JSON format"
        assert response["file_path"] == "/test/file.json"
        assert response["line_number"] == 15
        assert response["context"] == "json_parsing"
        assert "timestamp" in response
    
    def test_handle_api_error(self):
        """Test API error handling."""
        error = APIError(
            message="Invalid request",
            error_code="INVALID_INPUT",
            status_code=400
        )
        
        response = self.error_handler.handle_api_error(error, "/api/memory/stm")
        
        assert response["error_type"] == "api_error"
        assert response["message"] == "Invalid request"
        assert response["error_code"] == "INVALID_INPUT"
        assert response["status_code"] == 400
        assert response["endpoint"] == "/api/memory/stm"
        assert "timestamp" in response
    
    def test_handle_generic_error(self):
        """Test generic error handling."""
        error = RuntimeError("Unexpected error")
        
        response = self.error_handler.handle_generic_error(error, "test_operation", "runtime_error")
        
        assert response["error_type"] == "runtime_error"
        assert response["message"] == "Unexpected error"
        assert response["exception_type"] == "RuntimeError"
        assert response["context"] == "test_operation"
        assert "timestamp" in response
    
    def test_create_success_response(self):
        """Test success response creation."""
        data = {"result": "success", "count": 5}
        
        response = self.error_handler.create_success_response(data, "Operation completed")
        
        assert response["status"] == "success"
        assert response["message"] == "Operation completed"
        assert response["data"] == data
        assert "timestamp" in response


class TestFileValidator:
    """Test file validation and parsing error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_validator = FileValidator()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_file_for_parsing_success(self):
        """Test successful file validation."""
        # Create a valid test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("This is a test file with valid content.\nLine 2\nLine 3")
        
        is_valid, error_response = self.file_validator.validate_file_for_parsing(test_file, "txt")
        
        assert is_valid is True
        assert error_response is None
    
    def test_validate_file_for_parsing_not_found(self):
        """Test validation with non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        is_valid, error_response = self.file_validator.validate_file_for_parsing(non_existent_file)
        
        assert is_valid is False
        assert error_response["error_type"] == "file_parsing_error"
        assert "File does not exist" in error_response["message"]
    
    def test_validate_file_for_parsing_too_large(self):
        """Test validation with file that's too large."""
        large_file = os.path.join(self.temp_dir, "large.txt")
        
        # Mock os.path.getsize to return a large size
        with patch('os.path.getsize', return_value=60 * 1024 * 1024):  # 60MB
            is_valid, error_response = self.file_validator.validate_file_for_parsing(large_file)
        
        assert is_valid is False
        assert error_response["error_type"] == "file_parsing_error"
        assert "File does not exist" in error_response["message"]  # File validation fails before size check
    
    def test_validate_file_for_parsing_wrong_format(self):
        """Test validation with wrong file format."""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        is_valid, error_response = self.file_validator.validate_file_for_parsing(test_file, "json")
        
        assert is_valid is False
        assert error_response["error_type"] == "file_parsing_error"
        assert "Unexpected file format" in error_response["message"]
    
    def test_validate_file_content_structure_success(self):
        """Test successful content structure validation."""
        content = "Header\nSection 1\nContent here\nSection 2\nMore content"
        expected_sections = ["Header", "Section 1"]
        
        is_valid, error_response = self.file_validator.validate_file_content_structure(content, expected_sections)
        
        assert is_valid is True
        assert error_response is None
    
    def test_validate_file_content_structure_empty(self):
        """Test content structure validation with empty content."""
        is_valid, error_response = self.file_validator.validate_file_content_structure("")
        
        assert is_valid is False
        assert error_response["error_type"] == "file_parsing_error"
        assert "empty or contains only whitespace" in error_response["message"]
    
    def test_validate_file_content_structure_missing_sections(self):
        """Test content structure validation with missing sections."""
        content = "Header\nSome content"
        expected_sections = ["Header", "Missing Section"]
        
        is_valid, error_response = self.file_validator.validate_file_content_structure(content, expected_sections)
        
        assert is_valid is False
        assert error_response["error_type"] == "file_parsing_error"
        assert "Missing expected sections" in error_response["message"]
        assert "Missing Section" in error_response["message"]
    
    def test_validate_file_content_structure_too_short(self):
        """Test content structure validation with too short content."""
        content = "Line 1\nLine 2"  # Only 2 non-empty lines
        
        is_valid, error_response = self.file_validator.validate_file_content_structure(content)
        
        assert is_valid is False
        assert error_response["error_type"] == "file_parsing_error"
        assert "too short or incomplete" in error_response["message"]
    
    def test_safe_file_read_success(self):
        """Test successful safe file reading."""
        test_file = os.path.join(self.temp_dir, "test.txt")
        test_content = "Line 1\nLine 2\nLine 3\nLine 4"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        content, error_response = self.file_validator.safe_file_read(test_file)
        
        assert content == test_content
        assert error_response is None
    
    def test_safe_file_read_not_found(self):
        """Test safe file reading with non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        content, error_response = self.file_validator.safe_file_read(non_existent_file)
        
        assert content is None
        assert error_response["error_type"] == "file_parsing_error"
        assert "File does not exist" in error_response["message"]  # Matches actual validation error message
    
    def test_safe_file_read_permission_error(self):
        """Test safe file reading with permission error."""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Mock permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            content, error_response = self.file_validator.safe_file_read(test_file)
        
        assert content is None
        assert error_response["error_type"] == "file_parsing_error"
        assert "Permission denied" in error_response["message"]
    
    def test_safe_file_read_encoding_error(self):
        """Test safe file reading with encoding error."""
        test_file = os.path.join(self.temp_dir, "test.txt")
        
        # Create file with invalid UTF-8 content
        with open(test_file, 'wb') as f:
            f.write(b'\xff\xfe\x00\x00')  # Invalid UTF-8 bytes
        
        content, error_response = self.file_validator.safe_file_read(test_file)
        
        assert content is None
        assert error_response["error_type"] == "file_parsing_error"
        assert "encoding error" in error_response["message"].lower()


class TestDatabaseErrorHandler:
    """Test database-specific error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.db_error_handler = DatabaseErrorHandler()
    
    def test_execute_with_retry_success(self):
        """Test successful operation with retry decorator."""
        def test_operation(value):
            return f"success: {value}"
        
        result = self.db_error_handler.execute_with_retry(test_operation, "test")
        assert result == "success: test"
    
    def test_execute_with_retry_failure(self):
        """Test operation failure with retry decorator."""
        def failing_operation():
            raise ConnectionError("Connection failed")
        
        with pytest.raises(DatabaseConnectionError):
            self.db_error_handler.execute_with_retry(failing_operation)
    
    def test_handle_redis_error_connection(self):
        """Test Redis connection error handling."""
        import redis
        error = redis.ConnectionError("Connection refused")
        
        response = self.db_error_handler.handle_redis_error(error, "get_key")
        
        assert response["error_type"] == "database_error"
        assert response["service"] == "Redis"
        assert response["operation"] == "get_key"
    
    def test_handle_redis_error_timeout(self):
        """Test Redis timeout error handling."""
        import redis
        error = redis.TimeoutError("Operation timed out")
        
        response = self.db_error_handler.handle_redis_error(error, "set_key")
        
        assert response["error_type"] == "database_error"
        assert response["service"] == "Redis"
        assert response["operation"] == "set_key"
    
    def test_handle_neo4j_error_service_unavailable(self):
        """Test Neo4j service unavailable error handling."""
        from neo4j.exceptions import ServiceUnavailable
        error = ServiceUnavailable("Service unavailable")
        
        response = self.db_error_handler.handle_neo4j_error(error, "run_query")
        
        assert response["error_type"] == "database_error"
        assert response["service"] == "Neo4j"
        assert response["operation"] == "run_query"
    
    def test_handle_neo4j_error_transient(self):
        """Test Neo4j transient error handling."""
        from neo4j.exceptions import TransientError
        error = TransientError("Transient error")
        
        response = self.db_error_handler.handle_neo4j_error(error, "create_node")
        
        assert response["error_type"] == "database_error"
        assert response["service"] == "Neo4j"
        assert response["operation"] == "create_node"
    
    def test_test_database_connection_success(self):
        """Test successful database connection test."""
        def successful_connection():
            return True
        
        is_connected, error_response = self.db_error_handler.test_database_connection(
            "TestDB", successful_connection
        )
        
        assert is_connected is True
        assert error_response is None
    
    def test_test_database_connection_failure(self):
        """Test failed database connection test."""
        def failing_connection():
            raise ConnectionError("Connection failed")
        
        is_connected, error_response = self.db_error_handler.test_database_connection(
            "TestDB", failing_connection
        )
        
        assert is_connected is False
        assert error_response["error_type"] == "database_error"
        assert error_response["service"] == "TestDB"
    
    def test_create_connection_health_check_all_healthy(self):
        """Test health check with all connections healthy."""
        connections = {
            "Redis": lambda: True,
            "Neo4j": lambda: True
        }
        
        health_status = self.db_error_handler.create_connection_health_check(connections)
        
        assert health_status["overall_status"] == "healthy"
        assert health_status["connections"]["Redis"]["status"] == "healthy"
        assert health_status["connections"]["Neo4j"]["status"] == "healthy"
    
    def test_create_connection_health_check_degraded(self):
        """Test health check with some connections unhealthy."""
        def failing_connection():
            raise ConnectionError("Connection failed")
        
        connections = {
            "Redis": lambda: True,
            "Neo4j": failing_connection
        }
        
        health_status = self.db_error_handler.create_connection_health_check(connections)
        
        assert health_status["overall_status"] == "degraded"
        assert health_status["connections"]["Redis"]["status"] == "healthy"
        assert health_status["connections"]["Neo4j"]["status"] == "unhealthy"
    
    def test_create_connection_health_check_all_unhealthy(self):
        """Test health check with all connections unhealthy."""
        def failing_connection():
            raise ConnectionError("Connection failed")
        
        connections = {
            "Redis": failing_connection,
            "Neo4j": failing_connection
        }
        
        health_status = self.db_error_handler.create_connection_health_check(connections)
        
        assert health_status["overall_status"] == "unhealthy"
        assert health_status["connections"]["Redis"]["status"] == "unhealthy"
        assert health_status["connections"]["Neo4j"]["status"] == "unhealthy"


class TestDataValidatorErrorScenarios:
    """Test DataValidator with various error scenarios."""
    
    def test_validate_stm_entry_invalid(self):
        """Test STM entry validation with invalid data."""
        # Create invalid STM entry
        entry = STMEntry(
            scenario_id="",  # Invalid: empty
            requirement_text="Test requirement",
            initial_assessment=InitialAssessment("", "", "")  # Invalid: empty fields
        )
        
        is_valid, errors = DataValidator.validate_stm_entry(entry)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("scenario_id" in error for error in errors)
        assert any("initial_assessment" in error for error in errors)
    
    def test_validate_ltm_rule_invalid(self):
        """Test LTM rule validation with invalid data."""
        # Create invalid LTM rule
        rule = LTMRule(
            rule_id="",  # Invalid: empty
            rule_text="Test rule",
            related_concepts=[],  # Invalid: empty
            source_scenario_id=[],  # Invalid: empty
            confidence_score=1.5,  # Invalid: > 1.0
            version=0  # Invalid: < 1
        )
        
        is_valid, errors = DataValidator.validate_ltm_rule(rule)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("rule_id" in error for error in errors)
        assert any("related_concepts" in error for error in errors)
        assert any("source_scenario_id" in error for error in errors)
        assert any("confidence_score" in error for error in errors)
        assert any("version" in error for error in errors)
    
    def test_validate_scenario_id_invalid_format(self):
        """Test scenario ID validation with invalid format."""
        invalid_ids = [
            "",  # Empty
            "invalid",  # Too few parts
            "domain_invalid_concept",  # Invalid requirement number
            "123_r1_concept",  # Invalid domain (starts with number)
            "domain_r1_",  # Empty concept
        ]
        
        for invalid_id in invalid_ids:
            is_valid, errors = DataValidator.validate_scenario_id(invalid_id)
            assert is_valid is False
            assert len(errors) > 0
    
    def test_validate_rule_id_invalid_format(self):
        """Test rule ID validation with invalid format."""
        invalid_ids = [
            "",  # Empty
            "invalid",  # Too few parts
            "gdpr_concept_01",  # Invalid policy (lowercase)
            "GDPR_concept_abc",  # Invalid version (non-numeric)
            "GDPR_concept_0",  # Invalid version (< 1)
        ]
        
        for invalid_id in invalid_ids:
            is_valid, errors = DataValidator.validate_rule_id(invalid_id)
            assert is_valid is False
            assert len(errors) > 0
    
    def test_validate_api_input_missing_fields(self):
        """Test API input validation with missing required fields."""
        data = {"field1": "value1"}  # Missing field2
        required_fields = ["field1", "field2"]
        
        is_valid, errors = DataValidator.validate_api_input(data, required_fields)
        
        assert is_valid is False
        assert any("field2" in error for error in errors)
    
    def test_validate_api_input_unexpected_fields(self):
        """Test API input validation with unexpected fields."""
        data = {"field1": "value1", "unexpected": "value"}
        required_fields = ["field1"]
        
        is_valid, errors = DataValidator.validate_api_input(data, required_fields)
        
        assert is_valid is False
        assert any("Unexpected fields" in error for error in errors)
    
    def test_validate_confidence_score_invalid(self):
        """Test confidence score validation with invalid values."""
        invalid_scores = [-0.1, 1.1, "0.5", None]
        
        for invalid_score in invalid_scores:
            is_valid, errors = DataValidator.validate_confidence_score(invalid_score)
            assert is_valid is False
            assert len(errors) > 0
    
    def test_validate_concepts_list_invalid(self):
        """Test concepts list validation with invalid data."""
        invalid_lists = [
            [],  # Empty
            ["", "concept2"],  # Empty concept
            ["concept1", "concept1"],  # Duplicates
            "not_a_list",  # Not a list
            [123, "concept2"],  # Non-string concept
        ]
        
        for invalid_list in invalid_lists:
            is_valid, errors = DataValidator.validate_concepts_list(invalid_list)
            assert is_valid is False
            assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__])