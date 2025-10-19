"""
Enhanced Configuration file for Podcast Generation Application

Centralizes all configuration management including Flask settings,
AI API keys, TTS engine settings, and audio file paths.

Features:
- Environment-based configuration management
- Enhanced security and validation
- Performance optimization settings
- Comprehensive logging configuration
- Production-ready deployment settings
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Fix for FFmpeg/torio extension loading issue
# Add system FFmpeg to DLL search path before importing torch/torio
def _setup_ffmpeg_path():
    """Setup FFmpeg DLL search path for torio extension loading"""
    try:
        # Path to system FFmpeg installation
        ffmpeg_system_path = r'C:\Users\ocean\ffmpegcd4b01707d-full_build\bin'

        # Check if system FFmpeg exists
        if os.path.exists(ffmpeg_system_path):
            # Add to PATH if not already present
            current_path = os.environ.get('PATH', '')
            if ffmpeg_system_path not in current_path:
                os.environ['PATH'] = ffmpeg_system_path + ';' + current_path
                logging.getLogger(__name__).info(f"Added FFmpeg to PATH: {ffmpeg_system_path}")

            # Also add to DLL search path (Windows specific)
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(ffmpeg_system_path)
                    logging.getLogger(__name__).info(f"Added FFmpeg to DLL directory: {ffmpeg_system_path}")
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to add DLL directory: {e}")

            return True
        else:
            logging.getLogger(__name__).debug(f"System FFmpeg not found at: {ffmpeg_system_path}")
            return False

    except Exception as e:
        logging.getLogger(__name__).error(f"Error setting up FFmpeg path: {e}")
        return False

# Execute the FFmpeg path setup immediately
_ffmpeg_setup_success = _setup_ffmpeg_path()
from datetime import timedelta, datetime

# Environment detection
def get_environment() -> str:
    """Detect the current environment (development, testing, production)."""
    env = os.environ.get('FLASK_ENV', os.environ.get('ENVIRONMENT', 'development')).lower()
    return env if env in ['development', 'testing', 'production'] else 'development'


# Configuration classes for better organization
@dataclass
class FlaskConfig:
    """Flask application configuration."""
    secret_key: str
    debug: bool
    host: str
    port: int
    testing: bool = False
    session_timeout: int = 3600  # 1 hour

    # Security settings
    csrf_enabled: bool = True
    secure_headers: bool = True

    # Performance settings
    max_content_length: int = 16 * 1024 * 1024  # 16MB
    send_file_max_age: int = 3600  # 1 hour


@dataclass
class APIConfig:
    """AI API configuration."""
    deepseek_api_key: str
    deepseek_api_base: str
    deepseek_model: str
    bigmodel_api_key: str
    bigmodel_api_base: str
    bigmodel_model: str
    timeout: int
    max_retries: int
    retry_delay: float


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""
    engine: str
    voice_rate: int
    voice_volume: float
    model_path: str
    device: str
    enable_cuda: bool
    refine_text: bool
    temperature: float
    top_p: float
    top_k: int


@dataclass
class LoggingConfig:
    """Enhanced logging configuration."""
    level: str
    file: str
    max_size_mb: int
    backup_count: int
    format: str
    date_format: str
    enable_console: bool
    enable_file: bool
    enable_structured: bool


@dataclass
class PerformanceConfig:
    """Performance and optimization configuration."""
    cache_enabled: bool
    cache_timeout: int
    thread_pool_workers: int
    rate_limit_enabled: bool
    rate_limit_requests: int
    rate_limit_window: int
    cleanup_interval: int
    max_concurrent_generations: int


@dataclass
class SecurityConfig:
    """Security configuration."""
    max_input_length: int
    allowed_audio_extensions: set
    sanitize_input: bool
    validate_file_paths: bool
    enable_cors: bool
    secure_cookies: bool
    require_https: bool


@dataclass
class APIKeyConfig:
    """Configuration for API key storage and validation."""
    provider: str
    encrypted_key: str
    key_mask: str  # Last 4 characters for UI display
    is_valid: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate API key configuration data after initialization."""
        if not self.provider.strip():
            raise ValueError("Provider name cannot be empty")
        if not self.encrypted_key.strip():
            raise ValueError("Encrypted API key cannot be empty")
        if not self.key_mask.strip():
            raise ValueError("Key mask cannot be empty")
        if len(self.key_mask) != 4:
            raise ValueError("Key mask must be exactly 4 characters")
        if not isinstance(self.is_valid, bool):
            raise ValueError("is_valid must be a boolean")


@dataclass
class AgentModelConfig:
    """Configuration for agent-model mapping."""
    agent_id: str
    provider: str
    model: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate agent model configuration data after initialization."""
        if not self.agent_id.strip():
            raise ValueError("Agent ID cannot be empty")
        if not self.provider.strip():
            raise ValueError("Provider name cannot be empty")
        if not self.model.strip():
            raise ValueError("Model name cannot be empty")


@dataclass
class UserConfig:
    """Complete user configuration containing API keys and agent settings."""
    session_id: str
    api_keys: List[APIKeyConfig]
    agent_configs: List[AgentModelConfig]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate user configuration data after initialization."""
        if not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")
        if not isinstance(self.api_keys, list):
            raise ValueError("API keys must be a list")
        if not isinstance(self.agent_configs, list):
            raise ValueError("Agent configurations must be a list")

        # Validate API key configurations
        for api_key in self.api_keys:
            if not isinstance(api_key, APIKeyConfig):
                raise ValueError("All API key entries must be APIKeyConfig instances")

        # Validate agent configurations
        for agent_config in self.agent_configs:
            if not isinstance(agent_config, AgentModelConfig):
                raise ValueError("All agent configuration entries must be AgentModelConfig instances")

            # Verify that agent's provider exists in API keys
            provider_exists = any(ak.provider == agent_config.provider for ak in self.api_keys)
            if not provider_exists:
                raise ValueError(f"Agent '{agent_config.agent_id}' references provider '{agent_config.provider}' which is not configured")


# Supported AI providers for validation
SUPPORTED_AI_PROVIDERS = {
    'deepseek': {
        'name': 'DeepSeek',
        'key_prefix': 'sk-',
        'min_length': 20,
        'models': ['deepseek-chat', 'deepseek-coder']
    },
    'bigmodel': {
        'name': 'BigModel',
        'key_prefix': '',
        'min_length': 32,
        'models': ['glm-4', 'glm-3-turbo']
    }
}


def validate_provider_name(provider: str) -> bool:
    """Validate that the provider name is supported."""
    return provider.lower() in SUPPORTED_AI_PROVIDERS


def get_provider_info(provider: str) -> Dict[str, Any]:
    """Get provider information for validation."""
    provider_key = provider.lower()
    if provider_key not in SUPPORTED_AI_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    return SUPPORTED_AI_PROVIDERS[provider_key]


def create_api_key_config(provider: str, encrypted_key: str, key_mask: str,
                         is_valid: bool = True) -> APIKeyConfig:
    """Create an APIKeyConfig instance with validation."""
    now = datetime.now()
    return APIKeyConfig(
        provider=provider,
        encrypted_key=encrypted_key,
        key_mask=key_mask,
        is_valid=is_valid,
        created_at=now,
        updated_at=now
    )


def create_agent_model_config(agent_id: str, provider: str, model: str) -> AgentModelConfig:
    """Create an AgentModelConfig instance with validation."""
    now = datetime.now()
    return AgentModelConfig(
        agent_id=agent_id,
        provider=provider,
        model=model,
        created_at=now,
        updated_at=now
    )


def create_user_config(session_id: str, api_keys: List[APIKeyConfig] = None,
                      agent_configs: List[AgentModelConfig] = None) -> UserConfig:
    """Create a UserConfig instance with validation."""
    now = datetime.now()
    return UserConfig(
        session_id=session_id,
        api_keys=api_keys or [],
        agent_configs=agent_configs or [],
        created_at=now,
        updated_at=now
    )


# Load environment-specific configurations
ENVIRONMENT = get_environment()

# Flask Configuration with environment-specific defaults
SECRET_KEY = os.environ.get('SECRET_KEY') or (
    'dev-secret-key' if ENVIRONMENT == 'development' else
    'test-secret-key' if ENVIRONMENT == 'testing' else
    os.environ.get('FLASK_SECRET_KEY', 'change-in-production')
)

DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true' and ENVIRONMENT == 'development'
HOST = os.environ.get('FLASK_HOST', '0.0.0.0' if ENVIRONMENT == 'development' else '0.0.0.0')
PORT = int(os.environ.get('FLASK_PORT', 5000 if ENVIRONMENT == 'development' else 8080))

# AI API Configuration
# DeepSeek API Settings
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_BASE = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

# BigModel API Settings
BIGMODEL_API_KEY = os.environ.get('BIGMODEL_API_KEY', '')
BIGMODEL_API_BASE = os.environ.get('BIGMODEL_API_BASE', 'https://open.bigmodel.cn/api/paas/v4')
BIGMODEL_MODEL = os.environ.get('BIGMODEL_MODEL', 'glm-4')

# AI Service Configuration
AI_SERVICE_TIMEOUT = int(os.environ.get('AI_SERVICE_TIMEOUT', 60))  # seconds
AI_MAX_RETRIES = int(os.environ.get('AI_MAX_RETRIES', 3))
AI_RETRY_DELAY = float(os.environ.get('AI_RETRY_DELAY', 1.0))  # seconds

# TTS Engine Configuration
TTS_ENGINE = os.environ.get('TTS_ENGINE', 'chattts')  # Default TTS engine - changed to ChatTTS
TTS_VOICE_RATE = int(os.environ.get('TTS_VOICE_RATE', 150))  # Words per minute
TTS_VOICE_VOLUME = float(os.environ.get('TTS_VOICE_VOLUME', 0.9))  # 0.0 to 1.0

# ChatTTS Configuration
CHATTTS_MODEL_PATH = os.environ.get('CHATTTS_MODEL_PATH', '2Noise/ChatTTS')

# Automatic CUDA detection function
def _detect_cuda_available():
    """Detect if CUDA is available for PyTorch"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

# Use automatic CUDA detection to set sensible defaults
_cuda_available = _detect_cuda_available()
CHATTTS_DEVICE = os.environ.get('CHATTTS_DEVICE', 'cuda' if _cuda_available else 'cpu')
CHATTTS_ENABLE_CUDA = os.environ.get('CHATTTS_ENABLE_CUDA', str(_cuda_available).lower()).lower() == 'true'
CHATTTS_REFINE_TEXT = os.environ.get('CHATTTS_REFINE_TEXT', 'True').lower() == 'true'
CHATTTS_TEMPERATURE = float(os.environ.get('CHATTTS_TEMPERATURE', 0.3))
CHATTTS_TOP_P = float(os.environ.get('CHATTTS_TOP_P', 0.7))
CHATTTS_TOP_K = int(os.environ.get('CHATTTS_TOP_K', 20))
CHATTTS_EOS = [",", ".", "!", "?", "~", "。", "！", "？", "…", "~"]

# Audio File Configuration
AUDIO_OUTPUT_DIR = Path(os.environ.get('AUDIO_OUTPUT_DIR', 'generated_audio'))
AUDIO_FORMAT = os.environ.get('AUDIO_FORMAT', 'mp3')
AUDIO_QUALITY = os.environ.get('AUDIO_QUALITY', 'high')  # high, medium, low
AUDIO_SAMPLE_RATE = int(os.environ.get('AUDIO_SAMPLE_RATE', 22050))  # Hz

# Voice Configuration by Gender and Personality
VOICE_PROFILES = {
    'male': {
        'professional': {'rate': 140, 'volume': 0.85, 'chattts_seed': 42},
        'casual': {'rate': 160, 'volume': 0.90, 'chattts_seed': 123},
        'energetic': {'rate': 180, 'volume': 0.95, 'chattts_seed': 456},
        'calm': {'rate': 130, 'volume': 0.80, 'chattts_seed': 789}
    },
    'female': {
        'professional': {'rate': 145, 'volume': 0.85, 'chattts_seed': 111},
        'casual': {'rate': 165, 'volume': 0.90, 'chattts_seed': 222},
        'energetic': {'rate': 185, 'volume': 0.95, 'chattts_seed': 333},
        'calm': {'rate': 135, 'volume': 0.80, 'chattts_seed': 444}
    },
    'other': {
        'neutral': {'rate': 150, 'volume': 0.85, 'chattts_seed': 555}
    }
}

# ChatTTS Voice Presets for different character types
# Note: Prompt parameters have been removed due to API compatibility issues
# Voice characteristics are now controlled through temperature, top_P, and top_K parameters
CHATTTS_VOICE_PRESETS = {
    'male_professional': {
        'temperature': 0.3,
        'top_P': 0.7,
        'top_K': 20
    },
    'male_casual': {
        'temperature': 0.5,
        'top_P': 0.8,
        'top_K': 25
    },
    'male_energetic': {
        'temperature': 0.7,
        'top_P': 0.9,
        'top_K': 30
    },
    'male_calm': {
        'temperature': 0.2,
        'top_P': 0.6,
        'top_K': 15
    },
    'female_professional': {
        'temperature': 0.3,
        'top_P': 0.7,
        'top_K': 20
    },
    'female_casual': {
        'temperature': 0.5,
        'top_P': 0.8,
        'top_K': 25
    },
    'female_energetic': {
        'temperature': 0.7,
        'top_P': 0.9,
        'top_K': 30
    },
    'female_calm': {
        'temperature': 0.2,
        'top_P': 0.6,
        'top_K': 15
    }
}

# Conversation Configuration
DEFAULT_CONVERSATION_ROUNDS = int(os.environ.get('DEFAULT_CONVERSATION_ROUNDS', 8))
MAX_CONVERSATION_ROUNDS = int(os.environ.get('MAX_CONVERSATION_ROUNDS', 20))
MIN_CONVERSATION_ROUNDS = int(os.environ.get('MIN_CONVERSATION_ROUNDS', 3))
MAX_PARTICIPANTS = int(os.environ.get('MAX_PARTICIPANTS', 6))
MIN_PARTICIPANTS = int(os.environ.get('MIN_PARTICIPANTS', 2))

# File Management Configuration
MAX_FILE_AGE_DAYS = int(os.environ.get('MAX_FILE_AGE_DAYS', 7))  # Auto-cleanup after 7 days
MAX_STORAGE_MB = int(os.environ.get('MAX_STORAGE_MB', 1000))  # 1GB max storage

# Enhanced Logging Configuration with environment-specific settings
DEFAULT_LOG_LEVEL = 'DEBUG' if ENVIRONMENT == 'development' else 'INFO'
LOG_LEVEL = os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()

# Validate log level
VALID_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
if LOG_LEVEL not in VALID_LOG_LEVELS:
    LOG_LEVEL = DEFAULT_LOG_LEVEL

LOG_FILE = os.environ.get('LOG_FILE', f'podcast_generation_{ENVIRONMENT}.log')
LOG_MAX_SIZE_MB = int(os.environ.get('LOG_MAX_SIZE_MB', 50 if ENVIRONMENT == 'production' else 10))
LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 10 if ENVIRONMENT == 'production' else 5))

# Enhanced logging formats
DETAILED_LOG_FORMAT = (
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - '
    '[%(threadName)s] - %(message)s'
)

SIMPLE_LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
STRUCTURED_LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'

LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Logging configuration object
LOGGING_CONFIG = LoggingConfig(
    level=LOG_LEVEL,
    file=LOG_FILE,
    max_size_mb=LOG_MAX_SIZE_MB,
    backup_count=LOG_BACKUP_COUNT,
    format=DETAILED_LOG_FORMAT if ENVIRONMENT == 'development' else SIMPLE_LOG_FORMAT,
    date_format=LOG_DATE_FORMAT,
    enable_console=True,
    enable_file=True,
    enable_structured=ENVIRONMENT == 'production'
)

# Performance Configuration
PERFORMANCE_CONFIG = PerformanceConfig(
    cache_enabled=ENVIRONMENT != 'testing',
    cache_timeout=300 if ENVIRONMENT == 'production' else 60,  # 5 min / 1 min
    thread_pool_workers=4 if ENVIRONMENT == 'production' else 2,
    rate_limit_enabled=ENVIRONMENT == 'production',
    rate_limit_requests=10 if ENVIRONMENT == 'production' else 100,
    rate_limit_window=300,  # 5 minutes
    cleanup_interval=3600,  # 1 hour
    max_concurrent_generations=5 if ENVIRONMENT == 'production' else 10
)

# Security Configuration
SECURITY_CONFIG = SecurityConfig(
    max_input_length=int(os.environ.get('MAX_INPUT_LENGTH', 1000 if ENVIRONMENT == 'production' else 2000)),
    allowed_audio_extensions={'mp3', 'wav', 'ogg', 'm4a'},
    sanitize_input=True,
    validate_file_paths=True,
    enable_cors=os.environ.get('ENABLE_CORS', 'False').lower() == 'true',
    secure_cookies=ENVIRONMENT == 'production',
    require_https=ENVIRONMENT == 'production'
)

# Update existing variables for backward compatibility
MAX_INPUT_LENGTH = SECURITY_CONFIG.max_input_length
ALLOWED_AUDIO_EXTENSIONS = SECURITY_CONFIG.allowed_audio_extensions
UPLOAD_FOLDER = AUDIO_OUTPUT_DIR

# Development Settings with environment awareness
ENABLE_CORS = SECURITY_CONFIG.enable_cors
API_DOCS_ENABLED = os.environ.get('API_DOCS_ENABLED', 'True' if ENVIRONMENT == 'development' else 'False').lower() == 'true'

# Enhanced configuration validation and helper functions
def validate_api_keys() -> Dict[str, Any]:
    """Validate API keys and return configuration status."""
    api_status = {
        'deepseek_configured': bool(DEEPSEEK_API_KEY),
        'bigmodel_configured': bool(BIGMODEL_API_KEY),
        'any_api_configured': bool(DEEPSEEK_API_KEY or BIGMODEL_API_KEY),
        'recommended_configured': bool(DEEPSEEK_API_KEY)
    }

    if not api_status['any_api_configured']:
        print("WARNING: No AI API keys configured. Please set DEEPSEEK_API_KEY or BIGMODEL_API_KEY environment variables.")

    if not api_status['recommended_configured']:
        print("INFO: DEEPSEEK_API_KEY not configured. BigModel API will be used as fallback.")

    return api_status


def validate_paths() -> Dict[str, Any]:
    """Validate file paths and permissions."""
    path_status = {
        'audio_output_dir': str(AUDIO_OUTPUT_DIR),
        'audio_dir_exists': AUDIO_OUTPUT_DIR.exists(),
        'audio_dir_writable': False,
        'log_dir_exists': False,
        'log_dir_writable': False
    }

    # Test audio directory
    try:
        if not path_status['audio_dir_exists']:
            AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            path_status['audio_dir_exists'] = True

        # Test write permissions
        test_file = AUDIO_OUTPUT_DIR / '.write_test'
        test_file.write_text('test')
        test_file.unlink()
        path_status['audio_dir_writable'] = True

    except Exception as e:
        print(f"WARNING: Audio directory validation failed: {e}")

    # Test log directory
    try:
        log_dir = Path(LOG_FILE).parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
        path_status['log_dir_exists'] = True

        # Test write permissions
        test_file = log_dir / '.log_test'
        test_file.write_text('test')
        test_file.unlink()
        path_status['log_dir_writable'] = True

    except Exception as e:
        print(f"WARNING: Log directory validation failed: {e}")

    return path_status


def validate_system_requirements() -> Dict[str, Any]:
    """Validate system requirements and return status."""
    requirements = {
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'python_version_ok': sys.version_info >= (3, 8),
        'environment': ENVIRONMENT,
        'debug_mode': DEBUG,
        'log_level': LOG_LEVEL,
        'api_keys': validate_api_keys(),
        'paths': validate_paths()
    }

    # Check Python version
    if not requirements['python_version_ok']:
        print(f"ERROR: Python 3.8+ required, found {requirements['python_version']}")

    return requirements


def get_config_summary() -> Dict[str, Any]:
    """Get a comprehensive summary of the current configuration."""
    return {
        'environment': ENVIRONMENT,
        'flask': {
            'host': HOST,
            'port': PORT,
            'debug': DEBUG,
            'testing': ENVIRONMENT == 'testing'
        },
        'api': {
            'deepseek_configured': bool(DEEPSEEK_API_KEY),
            'bigmodel_configured': bool(BIGMODEL_API_KEY),
            'timeout': AI_SERVICE_TIMEOUT,
            'max_retries': AI_MAX_RETRIES
        },
        'tts': {
            'engine': TTS_ENGINE,
            'device': CHATTTS_DEVICE,
            'cuda_enabled': CHATTTS_ENABLE_CUDA
        },
        'logging': {
            'level': LOG_LEVEL,
            'file': LOG_FILE,
            'max_size_mb': LOG_MAX_SIZE_MB,
            'backup_count': LOG_BACKUP_COUNT
        },
        'security': {
            'max_input_length': MAX_INPUT_LENGTH,
            'allowed_extensions': list(ALLOWED_AUDIO_EXTENSIONS),
            'secure_cookies': SECURITY_CONFIG.secure_cookies,
            'require_https': SECURITY_CONFIG.require_https
        },
        'performance': {
            'cache_enabled': PERFORMANCE_CONFIG.cache_enabled,
            'rate_limit_enabled': PERFORMANCE_CONFIG.rate_limit_enabled,
            'thread_workers': PERFORMANCE_CONFIG.thread_pool_workers
        }
    }


def setup_logging():
    """Set up enhanced logging configuration."""
    try:
        # Create logging configuration
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': LOGGING_CONFIG.format,
                    'datefmt': LOGGING_CONFIG.date_format
                },
                'simple': {
                    'format': SIMPLE_LOG_FORMAT,
                    'datefmt': LOG_DATE_FORMAT
                },
                'structured': {
                    'format': STRUCTURED_LOG_FORMAT,
                    'datefmt': LOG_DATE_FORMAT
                }
            },
            'handlers': {},
            'loggers': {
                '': {  # Root logger
                    'level': LOG_LEVEL,
                    'handlers': []
                },
                'podcast_generation': {
                    'level': LOG_LEVEL,
                    'handlers': [],
                    'propagate': False
                }
            }
        }

        # Console handler
        if LOGGING_CONFIG.enable_console:
            logging_config['handlers']['console'] = {
                'class': 'logging.StreamHandler',
                'level': LOG_LEVEL,
                'formatter': 'simple' if ENVIRONMENT == 'production' else 'detailed',
                'stream': 'ext://sys.stdout'
            }
            logging_config['loggers']['']['handlers'].append('console')
            logging_config['loggers']['podcast_generation']['handlers'].append('console')

        # File handler with rotation
        if LOGGING_CONFIG.enable_file:
            log_file_path = Path(LOG_FILE)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            logging_config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': LOG_LEVEL,
                'formatter': 'structured' if LOGGING_CONFIG.enable_structured else 'detailed',
                'filename': str(log_file_path),
                'maxBytes': LOG_MAX_SIZE_MB * 1024 * 1024,
                'backupCount': LOG_BACKUP_COUNT,
                'encoding': 'utf-8'
            }
            logging_config['loggers']['']['handlers'].append('file')
            logging_config['loggers']['podcast_generation']['handlers'].append('file')

        # Apply configuration
        logging.config.dictConfig(logging_config)

        # Log configuration status
        logger = logging.getLogger('podcast_generation')
        logger.info(f"Logging configured - Level: {LOG_LEVEL}, Environment: {ENVIRONMENT}")
        logger.info(f"Log file: {LOG_FILE}")

        return logger

    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL),
            format=SIMPLE_LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )
        print(f"WARNING: Enhanced logging configuration failed: {e}")
        return logging.getLogger(__name__)


# Initialize enhanced logging on import
enhanced_logger = None
try:
    import logging.config
    enhanced_logger = setup_logging()
except ImportError:
    # Fallback if logging.config is not available
    import logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=SIMPLE_LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    enhanced_logger = logging.getLogger(__name__)
    print("WARNING: logging.config not available, using basic logging")

# Initialize audio output directory with enhanced validation
def ensure_output_directory():
    """Create audio output directory if it doesn't exist with comprehensive validation."""
    try:
        AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Test write permissions
        test_file = AUDIO_OUTPUT_DIR / '.write_test'
        test_file.write_text('test')
        test_file.unlink()

        # Set appropriate permissions (in production environments)
        if ENVIRONMENT == 'production':
            try:
                import stat
                current_permissions = AUDIO_OUTPUT_DIR.stat().st_mode
                # Set permissions to 755 (rwxr-xr-x)
                AUDIO_OUTPUT_DIR.chmod(0o755)
            except Exception:
                pass  # Ignore permission errors

        return AUDIO_OUTPUT_DIR

    except Exception as e:
        raise OSError(f"Failed to create or access audio output directory {AUDIO_OUTPUT_DIR}: {e}")


# Enhanced configuration validation on startup
def validate_config():
    """Comprehensive validation of critical configuration settings."""
    validation_errors = []
    validation_warnings = []

    # Validate API keys
    api_status = validate_api_keys()
    if not api_status['any_api_configured']:
        validation_errors.append("At least one AI API key (DEEPSEEK_API_KEY or BIGMODEL_API_KEY) must be configured")
    elif not api_status['recommended_configured']:
        validation_warnings.append("DEEPSEEK_API_KEY not configured - BigModel API will be used as fallback")

    # Validate conversation limits
    if MIN_PARTICIPANTS > MAX_PARTICIPANTS:
        validation_errors.append("MIN_PARTICIPANTS cannot be greater than MAX_PARTICIPANTS")

    if MIN_CONVERSATION_ROUNDS > MAX_CONVERSATION_ROUNDS:
        validation_errors.append("MIN_CONVERSATION_ROUNDS cannot be greater than MAX_CONVERSATION_ROUNDS")

    # Validate numeric configurations
    if AI_SERVICE_TIMEOUT <= 0:
        validation_errors.append("AI_SERVICE_TIMEOUT must be positive")

    if AI_MAX_RETRIES < 0:
        validation_errors.append("AI_MAX_RETRIES cannot be negative")

    if AI_RETRY_DELAY < 0:
        validation_errors.append("AI_RETRY_DELAY cannot be negative")

    if MAX_FILE_AGE_DAYS < 1:
        validation_errors.append("MAX_FILE_AGE_DAYS must be at least 1")

    if MAX_STORAGE_MB < 100:
        validation_warnings.append("MAX_STORAGE_MB is less than 100MB - this may be insufficient for audio files")

    # Validate logging configuration
    if LOG_LEVEL not in VALID_LOG_LEVELS:
        validation_errors.append(f"Invalid LOG_LEVEL: {LOG_LEVEL}. Must be one of {VALID_LOG_LEVELS}")

    if LOG_MAX_SIZE_MB < 1:
        validation_errors.append("LOG_MAX_SIZE_MB must be at least 1")

    if LOG_BACKUP_COUNT < 1:
        validation_errors.append("LOG_BACKUP_COUNT must be at least 1")

    # Validate Flask configuration
    if PORT < 1 or PORT > 65535:
        validation_errors.append("PORT must be between 1 and 65535")

    if not SECRET_KEY or SECRET_KEY in ['dev-secret-key', 'test-secret-key', 'change-in-production']:
        if ENVIRONMENT == 'production':
            validation_errors.append("SECRET_KEY must be set to a secure value in production")
        else:
            validation_warnings.append("Using insecure SECRET_KEY - acceptable for development only")

    # Report results
    if validation_errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
        raise ValueError(error_msg)

    if validation_warnings:
        print("Configuration warnings:")
        for warning in validation_warnings:
            print(f"  - {warning}")

    return True


def log_configuration_status():
    """Log detailed configuration status for debugging and monitoring."""
    if enhanced_logger:
        try:
            config_summary = get_config_summary()
            system_reqs = validate_system_requirements()

            enhanced_logger.info("=== Configuration Status ===")
            enhanced_logger.info(f"Environment: {config_summary['environment']}")
            enhanced_logger.info(f"Python Version: {system_reqs['python_version']} (OK: {system_reqs['python_version_ok']})")
            enhanced_logger.info(f"Flask: {config_summary['flask']['host']}:{config_summary['flask']['port']} (Debug: {config_summary['flask']['debug']})")

            # API Configuration
            api_config = config_summary['api']
            enhanced_logger.info(f"API Configuration: DeepSeek={api_config['deepseek_configured']}, BigModel={api_config['bigmodel_configured']}")
            enhanced_logger.info(f"API Settings: Timeout={api_config['timeout']}s, Max Retries={api_config['max_retries']}")

            # TTS Configuration
            tts_config = config_summary['tts']
            enhanced_logger.info(f"TTS Engine: {tts_config['engine']}, Device: {tts_config['device']}, CUDA: {tts_config['cuda_enabled']}")

            # Paths
            paths = system_reqs['paths']
            enhanced_logger.info(f"Audio Directory: {paths['audio_output_dir']} (Exists: {paths['audio_dir_exists']}, Writable: {paths['audio_dir_writable']})")

            # Security
            security = config_summary['security']
            enhanced_logger.info(f"Security: Max Input={security['max_input_length']}, Secure Cookies={security['secure_cookies']}, HTTPS Required={security['require_https']}")

            # Performance
            performance = config_summary['performance']
            enhanced_logger.info(f"Performance: Cache={performance['cache_enabled']}, Rate Limit={performance['rate_limit_enabled']}, Threads={performance['thread_workers']}")

            enhanced_logger.info("=== End Configuration Status ===")

        except Exception as e:
            print(f"Warning: Failed to log configuration status: {e}")


# Auto-validate configuration when module is imported
try:
    validate_config()
    ensure_output_directory()
    log_configuration_status()
except Exception as e:
    print(f"CRITICAL: Configuration validation failed: {e}")
    raise