"""
Data validation utilities for the memory management system.
"""

import re
import logging
import time
import functools
from typing import Dict, Any, List, Tuple, Optional, Union, Callable
from datetime import datetime
from ..models import STMEntry, LTMRule

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.field = field
        self.details = details or {}


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    def __init__(self, message: str, service: str = None, retry_count: int = 0):
        super().__init__(message)
        self.service = service
        self.retry_count = retry_count


class FileParsingError(Exception):
    """Custom exception for file parsing errors."""
    def __init__(self, message: str, file_path: str = None, line_number: int = None):
        super().__init__(message)
        self.file_path = file_path
        self.line_number = line_number


class APIError(Exception):
    """Base exception for API-related errors."""
    def __init__(self, message: str, error_code: str = None, status_code: int = 500):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0, 
                    exceptions: Tuple = (Exception,)):
    """
    Decorator for retrying functions on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise DatabaseConnectionError(
                            f"Operation failed after {max_retries} retries: {str(e)}",
                            retry_count=attempt
                        )
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class DataValidator:
    """
    Comprehensive data validator for memory management objects.
    
    Provides validation for STM entries, LTM rules, extracted data,
    and API inputs with detailed error reporting.
    """
    
    @staticmethod
    def validate_stm_entry(entry: STMEntry) -> Tuple[bool, List[str]]:
        """
        Validate an STM entry for completeness and format.
        
        Args:
            entry: STM entry to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not entry.validate():
            # Check specific validation failures
            if not entry.scenario_id or not entry.scenario_id.strip():
                errors.append("scenario_id is required and cannot be empty")
            
            if not entry.requirement_text or not entry.requirement_text.strip():
                errors.append("requirement_text is required and cannot be empty")
            
            if not entry.final_status or not entry.final_status.strip():
                errors.append("final_status is required and cannot be empty")
            
            # Validate scenario_id format
            parts = entry.scenario_id.split('_') if entry.scenario_id else []
            if len(parts) < 3:
                errors.append("scenario_id must follow format: {domain}_{requirement_number}_{key_concept}")
            
            # Validate nested objects
            if not entry.initial_assessment.validate():
                errors.append("initial_assessment is incomplete - status, rationale, and recommendation are required")
            
            if entry.human_feedback is not None and not entry.human_feedback.validate():
                errors.append("human_feedback is incomplete - decision, rationale, and suggestion are required")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_ltm_rule(rule: LTMRule) -> Tuple[bool, List[str]]:
        """
        Validate an LTM rule for completeness and format.
        
        Args:
            rule: LTM rule to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not rule.validate():
            # Check specific validation failures
            if not rule.rule_id or not rule.rule_id.strip():
                errors.append("rule_id is required and cannot be empty")
            
            if not rule.rule_text or not rule.rule_text.strip():
                errors.append("rule_text is required and cannot be empty")
            
            # Validate rule_id format
            parts = rule.rule_id.split('_') if rule.rule_id else []
            if len(parts) < 3:
                errors.append("rule_id must follow format: {policy}_{concept}_{version}")
            
            if not rule.related_concepts or len(rule.related_concepts) == 0:
                errors.append("related_concepts cannot be empty")
            
            if not rule.source_scenario_id or len(rule.source_scenario_id) == 0:
                errors.append("source_scenario_id cannot be empty")
            
            if not (0.0 <= rule.confidence_score <= 1.0):
                errors.append("confidence_score must be between 0.0 and 1.0")
            
            if rule.version < 1:
                errors.append("version must be a positive integer")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_scenario_id(scenario_id: str) -> Tuple[bool, List[str]]:
        """
        Validate scenario ID format and content.
        
        Args:
            scenario_id: Scenario ID to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not scenario_id or not isinstance(scenario_id, str):
            errors.append("scenario_id must be a non-empty string")
            return False, errors
        
        scenario_id = scenario_id.strip()
        if not scenario_id:
            errors.append("scenario_id cannot be empty or whitespace only")
            return False, errors
        
        # Check format: {domain}_{requirement_number}_{key_concept}
        parts = scenario_id.split('_')
        if len(parts) < 3:
            errors.append("scenario_id must follow format: {domain}_{requirement_number}_{key_concept}")
        else:
            # Validate domain part (should be alphanumeric)
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', parts[0]):
                errors.append("domain part of scenario_id should start with a letter and contain only alphanumeric characters")
            
            # Validate requirement number part (should start with 'r' or 'R' followed by number)
            if not re.match(r'^[rR]\d+$', parts[1]):
                errors.append("requirement_number part should follow format 'r1', 'R1', etc.")
            
            # Validate key concept part (should be alphanumeric with possible underscores)
            if not re.match(r'^[a-zA-Z0-9_]+$', parts[2]):
                errors.append("key_concept part should contain only alphanumeric characters and underscores")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_rule_id(rule_id: str) -> Tuple[bool, List[str]]:
        """
        Validate LTM rule ID format and content.
        
        Args:
            rule_id: Rule ID to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not rule_id or not isinstance(rule_id, str):
            errors.append("rule_id must be a non-empty string")
            return False, errors
        
        rule_id = rule_id.strip()
        if not rule_id:
            errors.append("rule_id cannot be empty or whitespace only")
            return False, errors
        
        # Check format: {policy}_{concept}_{version}
        parts = rule_id.split('_')
        if len(parts) < 3:
            errors.append("rule_id must follow format: {policy}_{concept}_{version}")
        else:
            # Validate policy part (should be uppercase alphanumeric)
            if not re.match(r'^[A-Z0-9]+$', parts[0]):
                errors.append("policy part of rule_id should be uppercase alphanumeric (e.g., GDPR, CCPA)")
            
            # Validate concept part (should be alphanumeric with possible underscores)
            if not re.match(r'^[a-zA-Z0-9_]+$', parts[1]):
                errors.append("concept part should contain only alphanumeric characters and underscores")
            
            # Validate version part (should be numeric)
            try:
                version = int(parts[2])
                if version < 1:
                    errors.append("version part should be a positive integer")
            except ValueError:
                errors.append("version part should be a valid integer")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_api_input(data: Dict[str, Any], required_fields: List[str], 
                          optional_fields: List[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate API input data structure.
        
        Args:
            data: Input data dictionary
            required_fields: List of required field names
            optional_fields: List of optional field names
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Input data must be a dictionary")
            return False, errors
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Required field '{field}' is missing")
            elif data[field] is None:
                errors.append(f"Required field '{field}' cannot be null")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"Required field '{field}' cannot be empty")
        
        # Check for unexpected fields
        all_allowed_fields = set(required_fields + (optional_fields or []))
        unexpected_fields = set(data.keys()) - all_allowed_fields
        if unexpected_fields:
            errors.append(f"Unexpected fields found: {list(unexpected_fields)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_file_path(file_path: str, must_exist: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate file path format and existence.
        
        Args:
            file_path: File path to validate
            must_exist: Whether the file must exist
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        import os
        errors = []
        
        if not file_path or not isinstance(file_path, str):
            errors.append("file_path must be a non-empty string")
            return False, errors
        
        file_path = file_path.strip()
        if not file_path:
            errors.append("file_path cannot be empty or whitespace only")
            return False, errors
        
        # Check for invalid characters (basic check) - exclude colon for Windows drive letters
        invalid_chars = ['<', '>', '"', '|', '?', '*']
        # Allow colon only if it's the second character (Windows drive letter)
        if any(char in file_path for char in invalid_chars):
            errors.append(f"file_path contains invalid characters: {invalid_chars}")
        elif ':' in file_path and not (len(file_path) > 1 and file_path[1] == ':'):
            errors.append("file_path contains invalid colon placement")
        
        if must_exist and not os.path.exists(file_path):
            errors.append(f"File does not exist: {file_path}")
        
        if must_exist and not os.path.isfile(file_path):
            errors.append(f"Path is not a file: {file_path}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_confidence_score(score: float) -> Tuple[bool, List[str]]:
        """
        Validate confidence score value.
        
        Args:
            score: Confidence score to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(score, (int, float)):
            errors.append("confidence_score must be a number")
            return False, errors
        
        if not (0.0 <= score <= 1.0):
            errors.append("confidence_score must be between 0.0 and 1.0")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_concepts_list(concepts: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate list of concepts.
        
        Args:
            concepts: List of concept strings
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(concepts, list):
            errors.append("concepts must be a list")
            return False, errors
        
        if len(concepts) == 0:
            errors.append("concepts list cannot be empty")
            return False, errors
        
        for i, concept in enumerate(concepts):
            if not isinstance(concept, str):
                errors.append(f"concept at index {i} must be a string")
            elif not concept.strip():
                errors.append(f"concept at index {i} cannot be empty")
        
        # Check for duplicates
        unique_concepts = set(concept.strip().lower() for concept in concepts if isinstance(concept, str))
        if len(unique_concepts) < len([c for c in concepts if isinstance(c, str)]):
            errors.append("concepts list contains duplicates")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_assessment_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate assessment data for creating new STM entries.
        
        Args:
            data: Assessment data dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required top-level fields
        required_fields = ['scenario_id', 'requirement_text', 'initial_assessment']
        is_valid, field_errors = DataValidator.validate_api_input(data, required_fields)
        errors.extend(field_errors)
        
        if not is_valid:
            return False, errors
        
        # Validate scenario_id format
        scenario_valid, scenario_errors = DataValidator.validate_scenario_id(data['scenario_id'])
        errors.extend(scenario_errors)
        
        # Validate initial_assessment structure
        if isinstance(data['initial_assessment'], dict):
            assessment = data['initial_assessment']
            required_assessment_fields = ['status', 'rationale', 'recommendation']
            assessment_valid, assessment_errors = DataValidator.validate_api_input(
                assessment, required_assessment_fields
            )
            errors.extend([f"initial_assessment.{error}" for error in assessment_errors])
            
            # Validate status value
            if 'status' in assessment:
                valid_statuses = ['Compliant', 'Non-Compliant', 'Partial', 'Pending']
                if assessment['status'] not in valid_statuses:
                    errors.append(f"initial_assessment.status must be one of: {valid_statuses}")
        else:
            errors.append("initial_assessment must be a dictionary")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_feedback_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate human feedback data.
        
        Args:
            data: Feedback data dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        required_fields = ['decision', 'rationale', 'suggestion']
        optional_fields = ['confidence', 'final_status']
        is_valid, field_errors = DataValidator.validate_api_input(
            data, required_fields, optional_fields
        )
        errors.extend(field_errors)
        
        # Validate final_status if provided
        if 'final_status' in data and data['final_status']:
            valid_statuses = ['Compliant', 'Non-Compliant', 'Partial', 'Pending']
            if data['final_status'] not in valid_statuses:
                errors.append(f"final_status must be one of: {valid_statuses}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_extracted_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate extracted data from compliance reports and feedback.
        
        Args:
            data: Dictionary containing extracted data
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_fields = [
            'requirement_text',
            'initial_assessment',
            'human_feedback'
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate initial_assessment structure
        if 'initial_assessment' in data and isinstance(data['initial_assessment'], dict):
            assessment = data['initial_assessment']
            required_assessment_fields = ['status', 'rationale', 'recommendation']
            for field in required_assessment_fields:
                if field not in assessment or not assessment[field]:
                    errors.append(f"initial_assessment.{field} is required")
        
        # Validate human_feedback structure
        if 'human_feedback' in data and isinstance(data['human_feedback'], dict):
            feedback = data['human_feedback']
            required_feedback_fields = ['decision', 'rationale', 'suggestion']
            for field in required_feedback_fields:
                if field not in feedback or not feedback[field]:
                    errors.append(f"human_feedback.{field} is required")
        
        return len(errors) == 0, errors
class ErrorHandler:
    """
    Comprehensive error handler for memory management operations.
    
    Provides structured error handling, logging, and response formatting
    for various types of errors in the system.
    """
    
    def __init__(self, logger_name: str = __name__):
        """
        Initialize error handler with logger.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
    
    def handle_validation_error(self, error: ValidationError, context: str = None) -> Dict[str, Any]:
        """
        Handle validation errors with structured response.
        
        Args:
            error: ValidationError instance
            context: Additional context about where the error occurred
            
        Returns:
            Structured error response dictionary
        """
        error_response = {
            "error_type": "validation_error",
            "message": str(error),
            "field": error.field,
            "details": error.details,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        if context:
            error_response["context"] = context
        
        self.logger.warning(f"Validation error in {context or 'unknown context'}: {error}")
        return error_response
    
    def handle_database_error(self, error: Exception, service: str, operation: str = None) -> Dict[str, Any]:
        """
        Handle database connection and operation errors.
        
        Args:
            error: Database error exception
            service: Database service name (Redis, Neo4j, etc.)
            operation: Operation that failed
            
        Returns:
            Structured error response dictionary
        """
        error_response = {
            "error_type": "database_error",
            "message": f"{service} operation failed: {str(error)}",
            "service": service,
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add specific error details based on error type
        if hasattr(error, 'retry_count'):
            error_response["retry_count"] = error.retry_count
        
        self.logger.error(f"Database error in {service} during {operation or 'unknown operation'}: {error}")
        return error_response
    
    def handle_file_parsing_error(self, error: FileParsingError, context: str = None) -> Dict[str, Any]:
        """
        Handle file parsing errors with detailed information.
        
        Args:
            error: FileParsingError instance
            context: Additional context about the parsing operation
            
        Returns:
            Structured error response dictionary
        """
        error_response = {
            "error_type": "file_parsing_error",
            "message": str(error),
            "file_path": error.file_path,
            "line_number": error.line_number,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        if context:
            error_response["context"] = context
        
        self.logger.error(f"File parsing error in {context or 'unknown context'}: {error}")
        return error_response
    
    def handle_api_error(self, error: APIError, endpoint: str = None) -> Dict[str, Any]:
        """
        Handle API-related errors.
        
        Args:
            error: APIError instance
            endpoint: API endpoint where error occurred
            
        Returns:
            Structured error response dictionary
        """
        error_response = {
            "error_type": "api_error",
            "message": str(error),
            "error_code": error.error_code,
            "status_code": error.status_code,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        if endpoint:
            error_response["endpoint"] = endpoint
        
        self.logger.error(f"API error at {endpoint or 'unknown endpoint'}: {error}")
        return error_response
    
    def handle_generic_error(self, error: Exception, context: str = None, 
                           error_type: str = "internal_error") -> Dict[str, Any]:
        """
        Handle generic errors with basic structured response.
        
        Args:
            error: Exception instance
            context: Context where error occurred
            error_type: Type of error for categorization
            
        Returns:
            Structured error response dictionary
        """
        error_response = {
            "error_type": error_type,
            "message": str(error),
            "exception_type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        if context:
            error_response["context"] = context
        
        self.logger.error(f"Generic error in {context or 'unknown context'}: {error}")
        return error_response
    
    def create_success_response(self, data: Any, message: str = "Operation successful") -> Dict[str, Any]:
        """
        Create structured success response.
        
        Args:
            data: Response data
            message: Success message
            
        Returns:
            Structured success response dictionary
        """
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }


class FileValidator:
    """
    Specialized validator for file operations and parsing.
    
    Provides comprehensive validation for file paths, content,
    and parsing operations with detailed error reporting.
    """
    
    def __init__(self):
        """Initialize file validator."""
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
    
    def validate_file_for_parsing(self, file_path: str, expected_format: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate file before parsing operations.
        
        Args:
            file_path: Path to file to validate
            expected_format: Expected file format (txt, json, etc.)
            
        Returns:
            Tuple of (is_valid, error_response_or_none)
        """
        import os
        
        try:
            # Check if file path is valid
            is_valid, errors = DataValidator.validate_file_path(file_path, must_exist=True)
            if not is_valid:
                raise FileParsingError(
                    f"Invalid file path: {'; '.join(errors)}",
                    file_path=file_path
                )
            
            # Check file size (prevent parsing extremely large files)
            file_size = os.path.getsize(file_path)
            max_size = 50 * 1024 * 1024  # 50MB limit
            if file_size > max_size:
                raise FileParsingError(
                    f"File too large: {file_size} bytes (max: {max_size} bytes)",
                    file_path=file_path
                )
            
            # Check file format if specified
            if expected_format:
                file_extension = os.path.splitext(file_path)[1].lower()
                if not file_extension.endswith(expected_format.lower()):
                    raise FileParsingError(
                        f"Unexpected file format: expected {expected_format}, got {file_extension}",
                        file_path=file_path
                    )
            
            # Check file readability
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Try to read first few bytes to ensure file is readable
                    f.read(1024)
            except UnicodeDecodeError as e:
                raise FileParsingError(
                    f"File encoding error: {str(e)}",
                    file_path=file_path
                )
            except PermissionError as e:
                raise FileParsingError(
                    f"Permission denied: {str(e)}",
                    file_path=file_path
                )
            
            return True, None
            
        except FileParsingError as e:
            return False, self.error_handler.handle_file_parsing_error(e, "file_validation")
        except Exception as e:
            return False, self.error_handler.handle_generic_error(e, "file_validation")
    
    def validate_file_content_structure(self, content: str, expected_sections: List[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate file content structure.
        
        Args:
            content: File content to validate
            expected_sections: List of expected sections/headers in content
            
        Returns:
            Tuple of (is_valid, error_response_or_none)
        """
        try:
            if not content or not content.strip():
                raise FileParsingError("File content is empty or contains only whitespace")
            
            # Check for expected sections if provided
            if expected_sections:
                missing_sections = []
                for section in expected_sections:
                    if section.lower() not in content.lower():
                        missing_sections.append(section)
                
                if missing_sections:
                    raise FileParsingError(
                        f"Missing expected sections: {', '.join(missing_sections)}"
                    )
            
            # Check for basic content quality
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            if len(non_empty_lines) < 3:
                raise FileParsingError("File content appears to be too short or incomplete")
            
            return True, None
            
        except FileParsingError as e:
            return False, self.error_handler.handle_file_parsing_error(e, "content_validation")
        except Exception as e:
            return False, self.error_handler.handle_generic_error(e, "content_validation")
    
    def safe_file_read(self, file_path: str, encoding: str = 'utf-8') -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Safely read file content with comprehensive error handling.
        
        Args:
            file_path: Path to file to read
            encoding: File encoding (default: utf-8)
            
        Returns:
            Tuple of (file_content_or_none, error_response_or_none)
        """
        try:
            # Validate file first
            is_valid, error_response = self.validate_file_for_parsing(file_path)
            if not is_valid:
                return None, error_response
            
            # Read file content
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Validate content structure
            is_valid, error_response = self.validate_file_content_structure(content)
            if not is_valid:
                return None, error_response
            
            self.logger.info(f"Successfully read file: {file_path}")
            return content, None
            
        except FileNotFoundError:
            error = FileParsingError(f"File not found: {file_path}", file_path=file_path)
            return None, self.error_handler.handle_file_parsing_error(error, "file_read")
        except PermissionError:
            error = FileParsingError(f"Permission denied: {file_path}", file_path=file_path)
            return None, self.error_handler.handle_file_parsing_error(error, "file_read")
        except UnicodeDecodeError as e:
            error = FileParsingError(f"Encoding error in {file_path}: {str(e)}", file_path=file_path)
            return None, self.error_handler.handle_file_parsing_error(error, "file_read")
        except Exception as e:
            return None, self.error_handler.handle_generic_error(e, f"file_read:{file_path}")


class DatabaseErrorHandler:
    """
    Specialized error handler for database operations.
    
    Provides retry logic, connection management, and structured
    error responses for database-related operations.
    """
    
    def __init__(self):
        """Initialize database error handler."""
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff_factor=2.0, 
                     exceptions=(ConnectionError, TimeoutError))
    def execute_with_retry(self, operation: Callable, *args, **kwargs):
        """
        Execute database operation with retry logic.
        
        Args:
            operation: Database operation function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            DatabaseConnectionError: If operation fails after all retries
        """
        return operation(*args, **kwargs)
    
    def handle_redis_error(self, error: Exception, operation: str = None) -> Dict[str, Any]:
        """
        Handle Redis-specific errors.
        
        Args:
            error: Redis error exception
            operation: Operation that failed
            
        Returns:
            Structured error response
        """
        import redis
        
        error_details = {
            "service": "Redis",
            "operation": operation,
            "error_class": type(error).__name__
        }
        
        if isinstance(error, redis.ConnectionError):
            error_details["error_category"] = "connection_error"
            error_details["suggestion"] = "Check Redis server status and connection parameters"
        elif isinstance(error, redis.TimeoutError):
            error_details["error_category"] = "timeout_error"
            error_details["suggestion"] = "Check network connectivity and Redis server performance"
        elif isinstance(error, redis.AuthenticationError):
            error_details["error_category"] = "authentication_error"
            error_details["suggestion"] = "Verify Redis password and authentication settings"
        else:
            error_details["error_category"] = "unknown_redis_error"
            error_details["suggestion"] = "Check Redis server logs for more details"
        
        return self.error_handler.handle_database_error(error, "Redis", operation)
    
    def handle_neo4j_error(self, error: Exception, operation: str = None) -> Dict[str, Any]:
        """
        Handle Neo4j-specific errors.
        
        Args:
            error: Neo4j error exception
            operation: Operation that failed
            
        Returns:
            Structured error response
        """
        from neo4j.exceptions import ServiceUnavailable, TransientError, ClientError
        
        error_details = {
            "service": "Neo4j",
            "operation": operation,
            "error_class": type(error).__name__
        }
        
        if isinstance(error, ServiceUnavailable):
            error_details["error_category"] = "service_unavailable"
            error_details["suggestion"] = "Check Neo4j server status and network connectivity"
        elif isinstance(error, TransientError):
            error_details["error_category"] = "transient_error"
            error_details["suggestion"] = "Retry the operation after a short delay"
        elif isinstance(error, ClientError):
            error_details["error_category"] = "client_error"
            error_details["suggestion"] = "Check query syntax and database schema"
        else:
            error_details["error_category"] = "unknown_neo4j_error"
            error_details["suggestion"] = "Check Neo4j server logs for more details"
        
        return self.error_handler.handle_database_error(error, "Neo4j", operation)
    
    def test_database_connection(self, db_type: str, connection_func: Callable) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Test database connection with error handling.
        
        Args:
            db_type: Type of database (Redis, Neo4j, etc.)
            connection_func: Function to test connection
            
        Returns:
            Tuple of (is_connected, error_response_or_none)
        """
        try:
            connection_func()
            self.logger.info(f"{db_type} connection test successful")
            return True, None
            
        except Exception as e:
            self.logger.error(f"{db_type} connection test failed: {e}")
            
            if db_type.lower() == "redis":
                error_response = self.handle_redis_error(e, "connection_test")
            elif db_type.lower() == "neo4j":
                error_response = self.handle_neo4j_error(e, "connection_test")
            else:
                error_response = self.error_handler.handle_database_error(e, db_type, "connection_test")
            
            return False, error_response
    
    def create_connection_health_check(self, connections: Dict[str, Callable]) -> Dict[str, Any]:
        """
        Create comprehensive health check for all database connections.
        
        Args:
            connections: Dictionary of connection name to test function
            
        Returns:
            Health check results dictionary
        """
        health_status = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "connections": {}
        }
        
        unhealthy_count = 0
        
        for conn_name, test_func in connections.items():
            is_healthy, error_response = self.test_database_connection(conn_name, test_func)
            
            if is_healthy:
                health_status["connections"][conn_name] = {
                    "status": "healthy",
                    "message": "Connection successful"
                }
            else:
                health_status["connections"][conn_name] = {
                    "status": "unhealthy",
                    "error": error_response
                }
                unhealthy_count += 1
        
        # Set overall status
        if unhealthy_count == 0:
            health_status["overall_status"] = "healthy"
        elif unhealthy_count < len(connections):
            health_status["overall_status"] = "degraded"
        else:
            health_status["overall_status"] = "unhealthy"
        
        return health_status