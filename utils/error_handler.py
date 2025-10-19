"""
Error handling utilities for podcast generation system.

This module provides comprehensive error handling functionality including:
- Custom exception classes for different error types
- Logging configuration for debugging and monitoring
- Error response formatting functions
- Retry mechanism decorators for API calls

Purpose: Centralize error handling and logging throughout the podcast generation system.
"""

import logging
import time
import functools
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Union, Type, Tuple
from enum import Enum

# Import configuration with fallback defaults
try:
    from config import (
        LOG_LEVEL, LOG_FILE, LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT,
        AI_SERVICE_TIMEOUT, AI_MAX_RETRIES, AI_RETRY_DELAY,
        AUDIO_OUTPUT_DIR
    )
except (ValueError, ImportError):
    # Fallback defaults for testing/development
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'podcast_generation.log'
    LOG_MAX_SIZE_MB = 10
    LOG_BACKUP_COUNT = 5
    AI_SERVICE_TIMEOUT = 60
    AI_MAX_RETRIES = 3
    AI_RETRY_DELAY = 1.0
    AUDIO_OUTPUT_DIR = Path('generated_audio')


class ErrorSeverity(Enum):
    """Error severity levels for categorizing issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PodcastGenerationError(Exception):
    """Base exception class for all podcast generation errors."""

    def __init__(self, message: str, error_code: str = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Dict[str, Any] = None, original_error: Exception = None):
        """
        Initialize podcast generation error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            severity: Error severity level
            details: Additional error details dictionary
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.now()

        # Add original error details if available
        if original_error:
            self.details['original_error'] = str(original_error)
            self.details['original_error_type'] = type(original_error).__name__


class AIAPIError(PodcastGenerationError):
    """Exception raised for AI API related errors."""

    def __init__(self, message: str, api_provider: str = None, status_code: int = None,
                 response_data: Dict[str, Any] = None, **kwargs):
        """
        Initialize AI API error.

        Args:
            message: Error message
            api_provider: Name of the AI API provider (e.g., 'deepseek', 'bigmodel')
            status_code: HTTP status code from API response
            response_data: Raw API response data
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.HIGH, **kwargs)
        self.api_provider = api_provider
        self.status_code = status_code
        self.response_data = response_data or {}

        # Update details with API-specific information
        if api_provider:
            self.details['api_provider'] = api_provider
        if status_code:
            self.details['status_code'] = status_code
        if response_data:
            self.details['response_data'] = response_data


class TTSError(PodcastGenerationError):
    """Exception raised for Text-to-Speech related errors."""

    def __init__(self, message: str, tts_engine: str = None, voice_profile: str = None,
                 text_snippet: str = None, **kwargs):
        """
        Initialize TTS error.

        Args:
            message: Error message
            tts_engine: Name of the TTS engine (e.g., 'chattts', 'azure')
            voice_profile: Voice profile being used
            text_snippet: Snippet of text that failed to process
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.MEDIUM, **kwargs)
        self.tts_engine = tts_engine
        self.voice_profile = voice_profile
        self.text_snippet = text_snippet

        # Update details with TTS-specific information
        if tts_engine:
            self.details['tts_engine'] = tts_engine
        if voice_profile:
            self.details['voice_profile'] = voice_profile
        if text_snippet:
            self.details['text_snippet'] = text_snippet[:100] + "..." if len(text_snippet) > 100 else text_snippet


class FileOperationError(PodcastGenerationError):
    """Exception raised for file system related errors."""

    def __init__(self, message: str, file_path: str = None, operation: str = None,
                 file_size: int = None, **kwargs):
        """
        Initialize file operation error.

        Args:
            message: Error message
            file_path: Path of the file involved in the error
            operation: File operation being performed (e.g., 'read', 'write', 'delete')
            file_size: Size of the file (in bytes)
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.MEDIUM, **kwargs)
        self.file_path = file_path
        self.operation = operation
        self.file_size = file_size

        # Update details with file-specific information
        if file_path:
            self.details['file_path'] = str(file_path)
        if operation:
            self.details['operation'] = operation
        if file_size:
            self.details['file_size'] = file_size


class ValidationError(PodcastGenerationError):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, field: str = None, value: Any = None,
                 validation_rule: str = None, **kwargs):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Name of the field that failed validation
            value: Value that failed validation
            validation_rule: Description of the validation rule that failed
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.LOW, **kwargs)
        self.field = field
        self.value = value
        self.validation_rule = validation_rule

        # Update details with validation-specific information
        if field:
            self.details['field'] = field
        if validation_rule:
            self.details['validation_rule'] = validation_rule
        # Don't include sensitive values in details
        if value is not None and not isinstance(value, (str, bytes)) or (isinstance(value, str) and len(value) <= 100):
            self.details['value'] = value


class NetworkError(PodcastGenerationError):
    """Exception raised for network-related errors."""

    def __init__(self, message: str, url: str = None, timeout: float = None,
                 retry_count: int = None, **kwargs):
        """
        Initialize network error.

        Args:
            message: Error message
            url: URL that was being accessed
            timeout: Timeout value in seconds
            retry_count: Number of retries attempted
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.HIGH, **kwargs)
        self.url = url
        self.timeout = timeout
        self.retry_count = retry_count

        # Update details with network-specific information
        if url:
            self.details['url'] = url
        if timeout:
            self.details['timeout'] = timeout
        if retry_count:
            self.details['retry_count'] = retry_count


class ConfigurationError(PodcastGenerationError):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, config_key: str = None, config_value: Any = None,
                 **kwargs):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Configuration value that caused the error
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.CRITICAL, **kwargs)
        self.config_key = config_key
        self.config_value = config_value

        # Update details with configuration-specific information
        if config_key:
            self.details['config_key'] = config_key
        # Don't include sensitive config values
        if config_value is not None and not any(key in config_key.lower() if config_key else "" for key in ['key', 'secret', 'password', 'token']):
            self.details['config_value'] = config_value


class DatabaseError(PodcastGenerationError):
    """Exception raised for database-related errors."""

    def __init__(self, message: str, table: str = None, operation: str = None,
                 query: str = None, **kwargs):
        """
        Initialize database error.

        Args:
            message: Error message
            table: Database table involved in the error
            operation: Database operation being performed (e.g., 'SELECT', 'INSERT', 'UPDATE', 'DELETE')
            query: SQL query that failed
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.HIGH, **kwargs)
        self.table = table
        self.operation = operation
        self.query = query

        # Update details with database-specific information
        if table:
            self.details['table'] = table
        if operation:
            self.details['operation'] = operation
        if query:
            # Truncate very long queries for logging
            self.details['query'] = query[:500] + "..." if len(query) > 500 else query


class EncryptionError(PodcastGenerationError):
    """Exception raised for encryption/decryption related errors."""

    def __init__(self, message: str, operation: str = None, data_type: str = None,
                 encryption_key_id: str = None, **kwargs):
        """
        Initialize encryption error.

        Args:
            message: Error message
            operation: Type of encryption operation (e.g., 'encrypt', 'decrypt', 'key_generation')
            data_type: Type of data being encrypted/decrypted (e.g., 'api_key', 'config_data')
            encryption_key_id: Identifier for the encryption key (if applicable)
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(message, severity=ErrorSeverity.CRITICAL, **kwargs)
        self.operation = operation
        self.data_type = data_type
        self.encryption_key_id = encryption_key_id

        # Update details with encryption-specific information
        if operation:
            self.details['operation'] = operation
        if data_type:
            self.details['data_type'] = data_type
        if encryption_key_id:
            self.details['encryption_key_id'] = encryption_key_id
        # Never include sensitive data in encryption error details


# Logging configuration
class LoggerManager:
    """Manages logging configuration for the podcast generation system."""

    _instance = None
    _logger = None

    def __new__(cls):
        """Singleton pattern for logger manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize logger manager."""
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Setup logging configuration."""
        # Create logger
        self._logger = logging.getLogger('podcast_generation')
        self._logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

        # Clear existing handlers
        self._logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )

        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self._logger.addHandler(console_handler)

        # File handler with rotation
        try:
            from logging.handlers import RotatingFileHandler

            # Ensure log directory exists
            log_file_path = Path(LOG_FILE)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
                backupCount=LOG_BACKUP_COUNT
            )
            file_handler.setLevel(getattr(logging, LOG_LEVEL.upper()))
            file_handler.setFormatter(detailed_formatter)
            self._logger.addHandler(file_handler)

        except Exception as e:
            # Fallback to basic file handler if rotating handler fails
            try:
                file_handler = logging.FileHandler(LOG_FILE)
                file_handler.setLevel(getattr(logging, LOG_LEVEL.upper()))
                file_handler.setFormatter(detailed_formatter)
                self._logger.addHandler(file_handler)
            except Exception:
                # If file logging fails, continue with console logging only
                self._logger.warning("Failed to setup file logging, using console only")

    @property
    def logger(self):
        """Get the configured logger instance."""
        return self._logger

    def log_exception(self, exception: Exception, context: Dict[str, Any] = None):
        """
        Log an exception with full context.

        Args:
            exception: Exception to log
            context: Additional context information
        """
        if isinstance(exception, PodcastGenerationError):
            # Use structured logging for custom exceptions
            log_data = {
                'error_code': exception.error_code,
                'severity': exception.severity.value,
                'details': exception.details,
                'timestamp': exception.timestamp.isoformat(),
                'traceback': traceback.format_exc()
            }

            if context:
                log_data['context'] = context

            if exception.severity == ErrorSeverity.CRITICAL:
                self._logger.critical(f"{exception.error_code}: {exception.message}", extra=log_data)
            elif exception.severity == ErrorSeverity.HIGH:
                self._logger.error(f"{exception.error_code}: {exception.message}", extra=log_data)
            elif exception.severity == ErrorSeverity.MEDIUM:
                self._logger.warning(f"{exception.error_code}: {exception.message}", extra=log_data)
            else:
                self._logger.info(f"{exception.error_code}: {exception.message}", extra=log_data)
        else:
            # Standard exception logging
            self._logger.error(f"Unexpected error: {str(exception)}", exc_info=True, extra={'context': context} or {})


# Global logger manager instance
logger_manager = LoggerManager()


def get_logger() -> logging.Logger:
    """
    Get the configured logger instance.

    Returns:
        Logger instance configured for the podcast generation system
    """
    return logger_manager.logger


def log_exception(exception: Exception, context: Dict[str, Any] = None):
    """
    Log an exception with full context.

    Args:
        exception: Exception to log
        context: Additional context information
    """
    logger_manager.log_exception(exception, context)


# Error response formatting functions
def create_error_response(error: Union[Exception, str], include_traceback: bool = False) -> Dict[str, Any]:
    """
    Create a standardized error response suitable for JSON API responses.

    Args:
        error: Exception or error message to create response for
        include_traceback: Whether to include traceback in response (for debugging)

    Returns:
        Dictionary with error information suitable for JSON response
    """
    if isinstance(error, str):
        return {
            'success': False,
            'error': error,
            'error_type': 'generic_error',
            'timestamp': datetime.now().isoformat()
        }

    if isinstance(error, PodcastGenerationError):
        response = {
            'success': False,
            'error': error.message,
            'error_code': error.error_code,
            'error_type': error.__class__.__name__.lower(),
            'severity': error.severity.value,
            'timestamp': error.timestamp.isoformat()
        }

        # Include details if available
        if error.details:
            response['details'] = error.details

        # Include traceback for debugging if requested
        if include_traceback:
            response['traceback'] = traceback.format_exc()

        return response

    # Standard exception handling
    return {
        'success': False,
        'error': str(error),
        'error_type': type(error).__name__.lower(),
        'timestamp': datetime.now().isoformat(),
        'traceback': traceback.format_exc() if include_traceback else None
    }


def create_user_friendly_error(error: Exception) -> str:
    """
    Create a user-friendly error message from an exception.

    Args:
        error: Exception to convert to user-friendly message

    Returns:
        User-friendly error message
    """
    if isinstance(error, AIAPIError):
        if error.status_code == 429:
            return "AI service is temporarily busy. Please try again in a moment."
        elif error.status_code and error.status_code >= 500:
            return "AI service is experiencing issues. Please try again later."
        elif error.status_code and error.status_code >= 400:
            return "Invalid request to AI service. Please check your input and try again."
        else:
            return "AI service temporarily unavailable. Please try again."

    elif isinstance(error, TTSError):
        if error.tts_engine:
            return f"Voice synthesis issue with {error.tts_engine} engine. Trying alternative voice..."
        return "Voice synthesis encountered issues. Please try again."

    elif isinstance(error, FileOperationError):
        if "space" in error.message.lower() or "disk" in error.message.lower():
            return "Storage issue detected. Please free up disk space and try again."
        elif "permission" in error.message.lower():
            return "File permission issue. Please check file access rights."
        else:
            return "File operation failed. Please try again."

    elif isinstance(error, NetworkError):
        return "Connection issue detected. Please check your internet connection and try again."

    elif isinstance(error, ValidationError):
        return f"Invalid input: {error.message}"

    elif isinstance(error, ConfigurationError):
        return "System configuration issue. Please contact support."

    else:
        return "An unexpected error occurred. Please try again."


# Retry mechanism decorators
def retry_on_exception(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_retries: int = None,
    base_delay: float = None,
    exponential_base: float = 2.0,
    jitter: bool = True,
    on_retry: Callable = None
):
    """
    Decorator for retrying functions on specific exceptions with exponential backoff.

    Args:
        exceptions: Exception class(es) to catch and retry on
        max_retries: Maximum number of retry attempts (defaults to AI_MAX_RETRIES)
        base_delay: Base delay between retries in seconds (defaults to AI_RETRY_DELAY)
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add jitter to retry delays
        on_retry: Optional callback function called on each retry attempt

    Returns:
        Decorated function with retry capability
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _max_retries = max_retries if max_retries is not None else AI_MAX_RETRIES
            _base_delay = base_delay if base_delay is not None else AI_RETRY_DELAY

            last_exception = None

            for attempt in range(_max_retries + 1):  # Include initial attempt
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Log retry attempt
                    logger = get_logger()
                    if attempt < _max_retries:
                        delay = _base_delay * (exponential_base ** attempt)

                        # Add jitter to prevent thundering herd
                        if jitter:
                            import random
                            delay *= (0.5 + random.random() * 0.5)

                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{_max_retries + 1}), "
                            f"retrying in {delay:.2f}s: {str(e)}"
                        )

                        # Call retry callback if provided
                        if on_retry:
                            try:
                                on_retry(e, attempt + 1, delay)
                            except Exception as callback_error:
                                logger.error(f"Retry callback failed: {callback_error}")

                        time.sleep(delay)
                    else:
                        logger.error(f"Function {func.__name__} failed after {_max_retries + 1} attempts: {str(e)}")

            # Raise the last exception if all retries failed
            raise last_exception

        return wrapper
    return decorator


def ai_api_retry(max_retries: int = None, on_retry: Callable = None):
    """
    Specific retry decorator for AI API calls.

    Args:
        max_retries: Maximum number of retry attempts
        on_retry: Optional callback function called on each retry attempt

    Returns:
        Decorated function with AI API retry capability
    """
    def retry_callback(exception: Exception, attempt: int, delay: float):
        """Default retry callback for AI API calls."""
        if isinstance(exception, AIAPIError):
            get_logger().warning(
                f"AI API call failed (attempt {attempt}), retrying in {delay:.2f}s. "
                f"Provider: {exception.api_provider}, Status: {exception.status_code}"
            )
        else:
            get_logger().warning(
                f"AI API call failed (attempt {attempt}), retrying in {delay:.2f}s: {str(exception)}"
            )

    return retry_on_exception(
        exceptions=(AIAPIError, NetworkError, TimeoutError),
        max_retries=max_retries or AI_MAX_RETRIES,
        base_delay=AI_RETRY_DELAY,
        on_retry=on_retry or retry_callback
    )


def tts_retry(max_retries: int = None, on_retry: Callable = None):
    """
    Specific retry decorator for TTS calls.

    Args:
        max_retries: Maximum number of retry attempts
        on_retry: Optional callback function called on each retry attempt

    Returns:
        Decorated function with TTS retry capability
    """
    def retry_callback(exception: Exception, attempt: int, delay: float):
        """Default retry callback for TTS calls."""
        if isinstance(exception, TTSError):
            get_logger().warning(
                f"TTS call failed (attempt {attempt}), retrying in {delay:.2f}s. "
                f"Engine: {exception.tts_engine}, Voice: {exception.voice_profile}"
            )
        else:
            get_logger().warning(
                f"TTS call failed (attempt {attempt}), retrying in {delay:.2f}s: {str(exception)}"
            )

    return retry_on_exception(
        exceptions=(TTSError, NetworkError, TimeoutError),
        max_retries=max_retries or AI_MAX_RETRIES,
        base_delay=AI_RETRY_DELAY,
        on_retry=on_retry or retry_callback
    )


# Context manager for error handling
class ErrorHandlerContext:
    """Context manager for handling errors within a specific context."""

    def __init__(self, context_name: str, reraise: bool = True,
                 default_error: Exception = None, on_error: Callable = None):
        """
        Initialize error handler context.

        Args:
            context_name: Name of the context for logging
            reraise: Whether to reraise exceptions after handling
            default_error: Default error to raise if no specific handling
            on_error: Optional callback function called when an error occurs
        """
        self.context_name = context_name
        self.reraise = reraise
        self.default_error = default_error or PodcastGenerationError(f"Error in {context_name}")
        self.on_error = on_error
        self.logger = get_logger()

    def __enter__(self):
        """Enter the context."""
        self.logger.debug(f"Entering context: {self.context_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and handle any exceptions."""
        if exc_type is not None:
            self.logger.error(f"Error in context '{self.context_name}': {str(exc_val)}")

            # Call error callback if provided
            if self.on_error:
                try:
                    self.on_error(exc_val)
                except Exception as callback_error:
                    self.logger.error(f"Error callback failed: {callback_error}")

            # Log the exception
            if isinstance(exc_val, PodcastGenerationError):
                log_exception(exc_val, {'context': self.context_name})
            else:
                log_exception(exc_val, {'context': self.context_name})

            if self.reraise:
                return False  # Reraise the exception
            else:
                return True  # Suppress the exception

        self.logger.debug(f"Exiting context successfully: {self.context_name}")
        return True


def handle_errors(context_name: str, reraise: bool = True,
                 default_error: Exception = None, on_error: Callable = None):
    """
    Decorator for handling errors in functions with a specific context.

    Args:
        context_name: Name of the context for logging
        reraise: Whether to reraise exceptions after handling
        default_error: Default error to raise if no specific handling
        on_error: Optional callback function called when an error occurs

    Returns:
        Decorated function with error handling
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorHandlerContext(context_name, reraise, default_error, on_error):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Utility functions for error monitoring and reporting
def check_disk_space(min_space_mb: int = 100) -> bool:
    """
    Check if there's enough disk space available.

    Args:
        min_space_mb: Minimum required disk space in MB

    Returns:
        True if enough space is available, False otherwise
    """
    try:
        import shutil
        _, _, free_bytes = shutil.disk_usage(AUDIO_OUTPUT_DIR)
        free_mb = free_bytes // (1024 * 1024)
        return free_mb >= min_space_mb
    except Exception:
        # If we can't check disk space, assume it's available
        return True


def validate_system_requirements() -> Dict[str, Any]:
    """
    Validate system requirements for podcast generation.

    Returns:
        Dictionary with validation results
    """
    results = {
        'valid': True,
        'issues': [],
        'warnings': []
    }

    # Check disk space
    if not check_disk_space(100):
        results['valid'] = False
        results['issues'].append("Insufficient disk space (minimum 100MB required)")

    # Check audio output directory
    try:
        AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        # Test write permissions
        test_file = AUDIO_OUTPUT_DIR / '.write_test'
        test_file.write_text('test')
        test_file.unlink()
    except Exception as e:
        results['valid'] = False
        results['issues'].append(f"Cannot write to audio output directory: {str(e)}")

    return results


# Exception translation utilities
def translate_exception(exception: Exception, context: str = None) -> PodcastGenerationError:
    """
    Translate standard exceptions to podcast generation specific exceptions.

    Args:
        exception: Original exception to translate
        context: Context information for the translation

    Returns:
        Translated PodcastGenerationError instance
    """
    if isinstance(exception, PodcastGenerationError):
        return exception

    message = str(exception)

    # Network related errors
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return NetworkError(message, original_error=exception, details={'context': context})

    # File system errors
    elif isinstance(exception, (FileNotFoundError, PermissionError, OSError)):
        return FileOperationError(message, original_error=exception, details={'context': context})

    # Value errors (often input validation)
    elif isinstance(exception, ValueError):
        return ValidationError(message, original_error=exception, details={'context': context})

    # Generic exception
    else:
        return PodcastGenerationError(
            f"Unexpected error: {message}",
            original_error=exception,
            details={'context': context, 'original_type': type(exception).__name__}
        )