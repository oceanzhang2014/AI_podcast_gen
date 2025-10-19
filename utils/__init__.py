"""
Utilities package for podcast generation.

This package contains utility functions for input validation,
file handling, error handling, and other common operations needed throughout
the podcast generation system.
"""

__version__ = "1.0.0"

# Import main components for easy access
from .error_handler import (
    PodcastGenerationError,
    AIAPIError,
    TTSError,
    FileOperationError,
    ValidationError,
    NetworkError,
    ConfigurationError,
    ErrorSeverity,
    get_logger,
    log_exception,
    create_error_response,
    create_user_friendly_error,
    retry_on_exception,
    ai_api_retry,
    tts_retry,
    handle_errors,
    ErrorHandlerContext,
    translate_exception,
    validate_system_requirements
)
from .ai_client import (
    AIMessage,
    AIResponse,
    BaseAIClient,
    DeepSeekClient,
    BigModelClient,
    AIClientFactory,
    UnifiedAIClient,
    create_ai_client,
    generate_podcast_dialogue
)
from .file_handler import (
    FileHandler,
    get_file_handler,
    save_audio_file,
    generate_filename,
    cleanup_old_files,
    get_file_for_download,
    list_audio_files,
    get_storage_info
)

__all__ = [
    'PodcastGenerationError',
    'AIAPIError',
    'TTSError',
    'FileOperationError',
    'ValidationError',
    'NetworkError',
    'ConfigurationError',
    'ErrorSeverity',
    'get_logger',
    'log_exception',
    'create_error_response',
    'create_user_friendly_error',
    'retry_on_exception',
    'ai_api_retry',
    'tts_retry',
    'handle_errors',
    'ErrorHandlerContext',
    'translate_exception',
    'validate_system_requirements',
    'AIMessage',
    'AIResponse',
    'BaseAIClient',
    'DeepSeekClient',
    'BigModelClient',
    'AIClientFactory',
    'UnifiedAIClient',
    'create_ai_client',
    'generate_podcast_dialogue',
    'FileHandler',
    'get_file_handler',
    'save_audio_file',
    'generate_filename',
    'cleanup_old_files',
    'get_file_for_download',
    'list_audio_files',
    'get_storage_info'
]