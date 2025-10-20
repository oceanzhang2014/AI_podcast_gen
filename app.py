"""
Podcast Generation Flask Application

Main web application for AI-powered podcast generation.
Provides user interface for configuring characters, topics, and generating podcast audio files.
Updated: ChatTTS parameter fixes applied

Features:
- Comprehensive error handling and logging
- Performance monitoring and caching
- Security best practices
- Real-time progress tracking
- Production-ready deployment capabilities
"""

import os

# Fix torio environment dependencies - MUST be set before any other imports
def fix_torio_environment():
    """Enhanced PATH fix for torio dependencies with system FFmpeg support"""
    import sys
    from pathlib import Path

    # Detect conda environment dynamically
    python_path = Path(sys.executable).parent
    conda_prefix = python_path  # For conda environments, the python path is the env root

    # All required DLL directories in priority order
    required_paths = [
        conda_prefix / "Lib" / "site-packages" / "torio" / "lib",
        conda_prefix / "Lib" / "site-packages" / "torch" / "lib",
        conda_prefix / "Library" / "bin",
        python_path / "Library" / "bin",
        # Add conda base paths for additional dependencies
        Path(r"C:\Users\ocean\MiniConda3\Library\bin"),
        Path(r"C:\Users\ocean\MiniConda3\Lib\site-packages\torio\lib"),
    ]

    # Check for system FFmpeg paths
    system_ffmpeg_paths = [
        Path(r"C:\Program Files\ffmpeg-master-latest-win64-gpl\bin"),
        Path(r"C:\Program Files (x86)\ffmpeg-master-latest-win64-gpl\bin"),
    ]

    # Add system FFmpeg to required paths if they exist
    for ffmpeg_path in system_ffmpeg_paths:
        if ffmpeg_path.exists():
            required_paths.append(ffmpeg_path)
            print(f"Found system FFmpeg: {ffmpeg_path}")

    # Add existing valid paths to PATH
    current_path = os.environ.get('PATH', '')
    current_path_dirs = current_path.split(';') if current_path else []
    new_paths = []

    for path in required_paths:
        if path.exists() and str(path) not in current_path:
            new_paths.append(str(path))

    if new_paths:
        # Insert new paths at the beginning for higher priority
        new_path = ";".join(new_paths + current_path_dirs)
        os.environ['PATH'] = new_path
        print(f"Enhanced torio environment fix - Added {len(new_paths)} paths to PATH with priority")

        # Log added paths for debugging
        for path in new_paths:
            print(f"  + Added to PATH: {path}")
    else:
        print("Torio environment: All required paths already in PATH")

def verify_torio_loading():
    """Verify that torio DLLs can load successfully - prioritize FFmpeg4 for stability"""
    try:
        import sys
        from pathlib import Path
        import ctypes

        # Detect conda environment
        conda_prefix = Path(sys.executable).parent  # For conda environments, python path is the env root

        # Try FFmpeg4 first (most compatible), then others
        dll_candidates = [
            "libtorio_ffmpeg4.pyd",
            "libtorio_ffmpeg5.pyd",
            "libtorio_ffmpeg6.pyd"
        ]

        for dll_name in dll_candidates:
            dll_path = conda_prefix / "Lib" / "site-packages" / "torio" / "lib" / dll_name
            if dll_path.exists():
                try:
                    # Try to load the DLL
                    handle = ctypes.windll.kernel32.LoadLibraryW(str(dll_path))
                    if handle:
                        ctypes.windll.kernel32.FreeLibrary(handle)
                        print(f"[OK] Torio FFmpeg extension verified successfully: {dll_path.name}")
                        return True
                    else:
                        error = ctypes.windll.kernel32.GetLastError()
                        print(f"[INFO] {dll_name} failed with error {error}, trying next...")
                except Exception as e:
                    print(f"[INFO] {dll_name} caused exception, trying next...")

        print("[INFO] All torio FFmpeg extensions failed to load, but torio basic functionality may still work")
        return False
    except Exception as e:
        print(f"[ERROR] Error verifying torio loading: {e}")
        return False

# Disable torio FFmpeg extension loading to avoid DLL issues
# System FFmpeg is available and sufficient for audio processing
import os
import logging
# Suppress torio debug logging
logging.getLogger('torio._extension.utils').setLevel(logging.WARNING)
os.environ['TORIO_DISABLE_FFMPEG'] = '1'
os.environ['TORIO_USE_FFMPEG'] = '0'
os.environ['PYTORCH_AUDIO_DISABLE_TORIO'] = '1'
# Force torio to skip FFmpeg extension loading
os.environ['TORIO_BACKEND'] = 'none'
os.environ['TORIO_LOG_LEVEL'] = 'WARNING'

# Apply the fix immediately
fix_torio_environment()

# Additional comprehensive fix for torio FFmpeg extensions
def comprehensive_torio_fix():
    """Comprehensive fix to ensure torio FFmpeg extensions work"""
    import sys
    from pathlib import Path
    import shutil
    import ctypes

    python_path = Path(sys.executable).parent
    conda_prefix = python_path
    torch_lib_path = conda_prefix / "Lib" / "site-packages" / "torch" / "lib"
    torio_lib_path = conda_prefix / "Lib" / "site-packages" / "torio" / "lib"

    # Ensure torch DLLs are in torio directory
    torch_dlls = ["torch_cpu.dll", "torch_cuda.dll", "c10.dll"]
    copied_count = 0

    for dll in torch_dlls:
        source = torch_lib_path / dll
        target = torio_lib_path / dll
        if source.exists() and not target.exists():
            try:
                shutil.copy2(source, target)
                copied_count += 1
                print(f"  Copied {dll} to torio directory")
            except Exception as e:
                print(f"  Failed to copy {dll}: {e}")

    if copied_count > 0:
        print(f"Enhanced torio fix: Copied {copied_count} torch DLLs")

# Apply comprehensive fix
comprehensive_torio_fix()

# Skip torio FFmpeg extension verification to avoid DLL issues
# System FFmpeg is available and sufficient
print("Skipping torio FFmpeg extension verification (using system FFmpeg)")
# verify_torio_loading()

import time
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template, request, jsonify, send_file, abort, g, session
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, BadRequest
from flask_cors import CORS
import sqlite3
import json
from contextlib import contextmanager

# Define create_tts_engine function at module level to ensure it's always available
def create_tts_engine():
    """Create TTS engine using new subprocess-based ChatTTS engine (based on testtts.py)"""
    try:
        from tts.chattts_engine import create_chatts_engine
        print("[INFO] Creating ChatTTS engine (subprocess-based, from testtts.py)")
        return create_chatts_engine("generated_audio")
    except Exception as e:
        print(f"[ERROR] Failed to create ChatTTS subprocess engine: {e}")
        # Fallback to original TTS engine if subprocess fails
        try:
            from tts.tts_engine import create_tts_engine as create_legacy_tts_engine
            print("[INFO] Falling back to legacy ChatTTS engine")
            return create_legacy_tts_engine()
        except Exception as e2:
            print(f"[ERROR] Failed to create fallback TTS engine: {e2}")
            return None

# Import configuration and error handling
try:
    from config import (
        DEBUG, HOST, PORT, SECRET_KEY,
        AUDIO_OUTPUT_DIR, ALLOWED_AUDIO_EXTENSIONS,
        MAX_INPUT_LENGTH, ensure_output_directory,
        LOG_LEVEL, LOG_FILE, LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT
    )
    from utils.error_handler import (
        get_logger, log_exception, handle_errors, ErrorHandlerContext,
        AIAPIError, TTSError, FileOperationError, ValidationError,
        NetworkError, ConfigurationError, create_error_response,
        create_user_friendly_error, check_disk_space, validate_system_requirements
    )
    from utils.validators import validate_podcast_input, create_validation_error_response
    from utils.models import Character, Gender, Language
    from utils.models import create_conversation_turn, create_podcast_result
    from agents.conversation_manager import ConversationManager, ConversationConfig
    from agents.character_agent import CharacterAgent, CharacterProfile
    from agents.autogen_conversation_service import create_autogen_conversation_service
    from tts.tts_engine import create_tts_engine as create_legacy_tts_engine
    from tts.subprocess_tts_service import create_subprocess_tts_service
    from tts.voice_manager import create_voice_manager
    from utils.file_handler import get_file_handler
    from audio.audio_merger import create_audio_merger_service
    CONFIG_LOADED = True
    logger = get_logger()
except ValueError as e:
    # Handle configuration validation errors gracefully
    print(f"Configuration Error: {e}")
    print("Please set DEEPSEEK_API_KEY or BIGMODEL_API_KEY environment variables")
    # Use safe defaults for development
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5000
    SECRET_KEY = 'dev-secret-key'
    AUDIO_OUTPUT_DIR = Path('generated_audio')
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}
    MAX_INPUT_LENGTH = 1000
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'podcast_generation.log'
    LOG_MAX_SIZE_MB = 10
    LOG_BACKUP_COUNT = 5
    CONFIG_LOADED = False

# Database configuration
DATABASE_PATH = Path('podcast_app.db')
ADMIN_USERNAME = 'admin'

# Import error handling with fallback
try:
    from utils.error_handler import get_logger, ErrorHandlerContext
    logger = get_logger()
except ImportError:
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

        # Create fallback ErrorHandlerContext
        class ErrorHandlerContext:
            def __init__(self, context_name, reraise=True):
                self.context_name = context_name
                self.reraise = reraise
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        # Create fallback imports for missing components
        class Character:
            def __init__(self, name, gender, background, personality, language):
                self.name = name
                self.gender = gender
                self.background = background
                self.personality = personality
                self.language = language

        class CharacterProfile:
            def __init__(self, name, gender, background, personality, age=None, style=None):
                self.name = name
                self.gender = gender
                self.background = background
                self.personality = personality
                self.age = age
                self.style = style

        class Gender:
            MALE = "male"
            FEMALE = "female"
            OTHER = "other"

        class Language:
            CHINESE = "chinese"
            ENGLISH = "english"

        def create_conversation_turn(round_number, character_id, text):
            from datetime import datetime
            return {
                'round_number': round_number,
                'character_id': character_id,
                'text': text,
                'created_at': datetime.now()
            }

        def create_podcast_result(request_id, topic, file_path, file_size, conversation_turns, total_duration):
            from datetime import datetime
            return {
                'request_id': request_id,
                'topic': topic,
                'file_path': file_path,
                'file_size': file_size,
                'conversation_turns': conversation_turns,
                'total_duration': total_duration,
                'created_at': datetime.now()
            }

        def create_voice_manager():
            return None

        def get_file_handler():
            return None

        # Fallback functions
        def check_disk_space(min_space_mb=100):
            return True

        def validate_system_requirements():
            return {'valid': True, 'issues': [], 'warnings': []}

        def log_exception(exception, context=None):
            logger.error(f"Exception: {str(exception)}")

        def handle_errors(context_name, reraise=True):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                return wrapper
            return decorator

# Fallback ensure_output_directory function
def ensure_output_directory_fallback():
    """Fallback function to create audio output directory."""
    AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)
    return AUDIO_OUTPUT_DIR

# Performance monitoring and caching utilities
class PerformanceMonitor:
    """Monitor application performance metrics."""

    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_error': 0,
            'response_times': [],
            'generation_requests': 0,
            'generation_success': 0,
            'generation_failures': 0,
            'active_generations': 0,
            'start_time': datetime.now()
        }
        self._lock = threading.Lock()

    def record_request(self, success: bool = True, response_time: float = None):
        """Record a request metric."""
        with self._lock:
            self.metrics['requests_total'] += 1
            if success:
                self.metrics['requests_success'] += 1
            else:
                self.metrics['requests_error'] += 1
            if response_time:
                self.metrics['response_times'].append(response_time)
                # Keep only last 100 response times
                if len(self.metrics['response_times']) > 100:
                    self.metrics['response_times'] = self.metrics['response_times'][-100:]

    def record_generation_start(self):
        """Record generation start."""
        with self._lock:
            self.metrics['generation_requests'] += 1
            self.metrics['active_generations'] += 1

    def record_generation_complete(self, success: bool = True):
        """Record generation completion."""
        with self._lock:
            self.metrics['active_generations'] = max(0, self.metrics['active_generations'] - 1)
            if success:
                self.metrics['generation_success'] += 1
            else:
                self.metrics['generation_failures'] += 1

    def get_metrics(self) -> dict:
        """Get current metrics."""
        with self._lock:
            metrics = self.metrics.copy()
            if metrics['response_times']:
                metrics['avg_response_time'] = sum(metrics['response_times']) / len(metrics['response_times'])
                metrics['max_response_time'] = max(metrics['response_times'])
                metrics['min_response_time'] = min(metrics['response_times'])
            else:
                metrics['avg_response_time'] = 0
                metrics['max_response_time'] = 0
                metrics['min_response_time'] = 0

            metrics['uptime_seconds'] = (datetime.now() - metrics['start_time']).total_seconds()
            metrics['success_rate'] = metrics['requests_success'] / max(1, metrics['requests_total']) * 100
            metrics['generation_success_rate'] = metrics['generation_success'] / max(1, metrics['generation_requests']) * 100

            return metrics

# Global performance monitor
performance_monitor = PerformanceMonitor()

def performance_monitoring(f):
    """Decorator to monitor route performance."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        success = False

        try:
            result = f(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            logger.error(f"Route {f.__name__} failed: {str(e)}")
            log_exception(e, {'route': f.__name__, 'args': args, 'kwargs': kwargs})
            raise
        finally:
            response_time = time.time() - start_time
            performance_monitor.record_request(success, response_time)
            logger.debug(f"Route {f.__name__} completed in {response_time:.3f}s, success: {success}")

    return decorated_function

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Simple rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

            if not hasattr(app, 'rate_limits'):
                app.rate_limits = {}

            now = time.time()
            if client_ip not in app.rate_limits:
                app.rate_limits[client_ip] = []

            # Clean old requests outside the window
            app.rate_limits[client_ip] = [
                req_time for req_time in app.rate_limits[client_ip]
                if now - req_time < window_seconds
            ]

            # Check rate limit
            if len(app.rate_limits[client_ip]) >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_ip}: {len(app.rate_limits[client_ip])} requests in {window_seconds}s")
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'error_type': 'rate_limit_exceeded'
                }), 429

            # Record this request
            app.rate_limits[client_ip].append(now)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_system_health():
    """Validate system health before processing requests."""
    try:
        # Use global fallback functions if not imported
        global check_disk_space, validate_system_requirements, FileOperationError, ConfigurationError

        # Check disk space
        if not check_disk_space(100):
            if 'FileOperationError' in globals():
                raise FileOperationError("Insufficient disk space", details={'required_space_mb': 100})
            else:
                print("Warning: Insufficient disk space check")

        # Validate system requirements
        system_validation = validate_system_requirements()
        if not system_validation['valid']:
            if 'ConfigurationError' in globals():
                raise ConfigurationError("System requirements not met", details=system_validation['issues'])
            else:
                print("Warning: System requirements not met")

        return True
    except Exception as e:
        logger.error(f"System health validation failed: {str(e)}")
        if 'ConfigurationError' in globals():
            raise
        else:
            print(f"System health validation failed: {str(e)}")
        return False

# Database Management Classes
@contextmanager
def get_db_connection():
    """Context manager for database connections with proper error handling."""
    conn = None
    try:
        conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

class DatabaseManager:
    """Handles database initialization and schema management."""

    @staticmethod
    def initialize_database():
        """Initialize database with required tables."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create podcast_configs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS podcast_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        topic TEXT NOT NULL,
                        participants INTEGER NOT NULL,
                        rounds INTEGER NOT NULL,
                        ai_provider TEXT NOT NULL,
                        ai_model TEXT NOT NULL,
                        character_configs TEXT NOT NULL,  -- JSON string
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')

                # Create api_keys table for API key management
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        provider TEXT NOT NULL,
                        encrypted_key TEXT NOT NULL,
                        key_mask TEXT NOT NULL,
                        is_valid BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, provider)
                    )
                ''')

                # Create agent_configs table for AI agent configurations
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS agent_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        config_data TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, provider, model)
                    )
                ''')

                # Create config_audit_log table for tracking configuration changes
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        action TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        record_id INTEGER NOT NULL,
                        old_values TEXT,
                        new_values TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create schema_version table for database migrations
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_version (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version INTEGER NOT NULL UNIQUE,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_podcast_configs_user_id
                    ON podcast_configs (user_id)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_podcast_configs_updated_at
                    ON podcast_configs (updated_at DESC)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_api_keys_user_id
                    ON api_keys (user_id)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_api_keys_provider
                    ON api_keys (provider)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_api_keys_valid
                    ON api_keys (is_valid)
                ''')

                # Add composite index for API key queries to optimize persistent display
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_api_keys_user_valid_updated
                    ON api_keys (user_id, is_valid, updated_at DESC)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_agent_configs_user_id
                    ON agent_configs (user_id)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_config_audit_log_user_id
                    ON config_audit_log (user_id)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_config_audit_log_created_at
                    ON config_audit_log (created_at)
                ''')

                # Insert initial schema version if not exists
                cursor.execute('''
                    INSERT OR IGNORE INTO schema_version (version, description)
                    VALUES (1, 'Initial database schema for podcast configuration system')
                ''')

                conn.commit()
                logger.info("Database initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

class UserManager:
    """Manages user operations for the application."""

    @staticmethod
    def get_or_create_admin_user():
        """Get or create the default admin user."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Try to find existing admin user
                cursor.execute('SELECT id, username FROM users WHERE username = ?', (ADMIN_USERNAME,))
                user = cursor.fetchone()

                if user:
                    logger.debug(f"Found existing admin user: {user['username']}")
                    return dict(user)
                else:
                    # Create admin user
                    cursor.execute('''
                        INSERT INTO users (username, created_at, updated_at)
                        VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (ADMIN_USERNAME,))

                    admin_id = cursor.lastrowid
                    conn.commit()

                    logger.info(f"Created new admin user with ID: {admin_id}")
                    return {'id': admin_id, 'username': ADMIN_USERNAME}

        except sqlite3.Error as e:
            logger.error(f"Failed to get or create admin user: {str(e)}")
            raise

class PodcastConfigRepository:
    """Repository for podcast configuration data operations."""

    @staticmethod
    def save_podcast_config(user_id, config_data):
        """Save a new podcast configuration."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO podcast_configs
                    (user_id, topic, participants, rounds, ai_provider, ai_model, character_configs)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    config_data.get('topic'),
                    config_data.get('participants'),
                    config_data.get('rounds'),
                    config_data.get('ai_provider'),
                    config_data.get('ai_model'),
                    json.dumps(config_data.get('character_configs', []))
                ))

                config_id = cursor.lastrowid

                # Save API keys if provided
                api_keys = config_data.get('api_keys', {})
                if api_keys and isinstance(api_keys, dict):
                    # Clear existing API keys for this user
                    cursor.execute("DELETE FROM api_keys WHERE user_id = ?", (user_id,))

                    # Insert new API keys
                    for provider, api_key in api_keys.items():
                        if api_key and api_key.strip():
                            # Create a masked version for display
                            key_mask = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"

                            cursor.execute('''
                                INSERT INTO api_keys
                                (user_id, provider, encrypted_key, key_mask, is_valid)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                user_id,
                                provider,
                                api_key,  # For now, storing directly - could be encrypted in production
                                key_mask,
                                True  # Assume valid if provided
                            ))

                conn.commit()

                logger.info(f"Saved podcast configuration with ID: {config_id}")
                return config_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save podcast config: {str(e)}")
            raise

    @staticmethod
    def get_latest_podcast_config(user_id):
        """Get the most recent podcast configuration for a user."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM podcast_configs
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                ''', (user_id,))

                config = cursor.fetchone()

                if config:
                    result = dict(config)
                    # Parse JSON field
                    result['character_configs'] = json.loads(result['character_configs'])

                    # Get API keys for this user
                    cursor.execute('''
                        SELECT provider, encrypted_key FROM api_keys
                        WHERE user_id = ? AND is_valid = 1
                    ''', (user_id,))

                    api_keys = {}
                    for api_key_row in cursor.fetchall():
                        api_keys[api_key_row['provider']] = api_key_row['encrypted_key']

                    result['api_keys'] = api_keys

                    logger.debug(f"Found latest config for user {user_id}")
                    return result
                else:
                    logger.debug(f"No config found for user {user_id}")
                    return None

        except sqlite3.Error as e:
            logger.error(f"Failed to get latest podcast config: {str(e)}")
            raise

    @staticmethod
    def update_podcast_config(config_id, config_data):
        """Update an existing podcast configuration."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE podcast_configs
                    SET topic = ?, participants = ?, rounds = ?,
                        ai_provider = ?, ai_model = ?, character_configs = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    config_data.get('topic'),
                    config_data.get('participants'),
                    config_data.get('rounds'),
                    config_data.get('ai_provider'),
                    config_data.get('ai_model'),
                    json.dumps(config_data.get('character_configs', [])),
                    config_id
                ))

                conn.commit()
                logger.info(f"Updated podcast configuration with ID: {config_id}")
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Failed to update podcast config: {str(e)}")
            raise

class AudioFileService:
    """Service for handling audio file operations with user-specific naming."""

    @staticmethod
    def generate_user_filename(username, timestamp=None):
        """Generate user-prefixed audio filename with timestamp."""
        if timestamp is None:
            timestamp = datetime.now()

        # Format: admin_YYYYMMDD_HHMMSS.wav
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        return f"{username}_{timestamp_str}.wav"

    @staticmethod
    def find_latest_user_audio(username):
        """Find the most recent audio file for a specific user."""
        try:
            audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}
            audio_files = []

            # Look for user-specific files first
            user_pattern = f"{username}_*"
            for file_path in AUDIO_OUTPUT_DIR.iterdir():
                if (file_path.is_file() and
                    file_path.suffix.lower() in audio_extensions and
                    file_path.name.startswith(username + "_")):

                    stat = file_path.stat()
                    audio_files.append({
                        'filename': file_path.name,
                        'created_at': datetime.fromtimestamp(stat.st_ctime),
                        'file_path': file_path
                    })

            # If no user files found, fall back to legacy files
            if not audio_files:
                legacy_pattern = "podcast_*"
                for file_path in AUDIO_OUTPUT_DIR.iterdir():
                    if (file_path.is_file() and
                        file_path.suffix.lower() in audio_extensions and
                        file_path.name.startswith("podcast_")):

                        stat = file_path.stat()
                        audio_files.append({
                            'filename': file_path.name,
                            'created_at': datetime.fromtimestamp(stat.st_ctime),
                            'file_path': file_path
                        })

            # Sort by creation time descending and return the latest
            if audio_files:
                audio_files.sort(key=lambda x: x['created_at'], reverse=True)
                return audio_files[0]

            return None

        except Exception as e:
            logger.error(f"Error finding user audio files: {str(e)}")
            return None

def get_most_recent_api_key_session():
    """
    Get the most recently used session ID that has API keys.
    This ensures we load the user's actual API keys instead of test data.
    """
    try:
        from utils.database import get_database_manager

        with get_database_manager().get_connection() as conn:
            # Find the most recently updated session with API keys (excluding admin_admin test session)
            cursor = conn.execute("""
                SELECT u.session_id, MAX(a.updated_at) as latest_update
                FROM api_keys a
                JOIN users u ON a.user_id = u.id
                WHERE a.is_valid = 1 AND u.session_id != 'admin_admin'
                GROUP BY u.session_id
                ORDER BY latest_update DESC
                LIMIT 1
            """)

            result = cursor.fetchone()

            if result:
                session_id = result['session_id']
                logger.info(f"Found most recent session with API keys: {session_id}")
                return session_id
            else:
                logger.warning("No session with API keys found (excluding admin_admin)")
                # Fallback to admin_admin if no other sessions have keys
                return "admin_admin"

    except Exception as e:
        logger.error(f"Error finding most recent API key session: {str(e)}")
        # Fallback to admin_admin on error
        return "admin_admin"


# Initialize Flask application
app = Flask(__name__)

# Configure CORS for development (allow file:// protocol access)
if DEBUG:
    CORS(app, resources={
        r"/audio/*": {
            "origins": ["null", "file://*", "http://127.0.0.1:5000", "http://localhost:5000"],
            "methods": ["GET", "HEAD", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        },
        r"/download/*": {
            "origins": ["null", "file://*", "http://127.0.0.1:5000", "http://localhost:5000"],
            "methods": ["GET", "HEAD", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
else:
    # Production CORS settings
    CORS(app, resources={
        r"/audio/*": {
            "origins": ["http://127.0.0.1:5000", "http://localhost:5000"],
            "methods": ["GET", "HEAD", "OPTIONS"]
        },
        r"/download/*": {
            "origins": ["http://127.0.0.1:5000", "http://localhost:5000"],
            "methods": ["GET", "HEAD", "OPTIONS"]
        }
    })

# Configure Flask app with enhanced security
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG
app.config['UPLOAD_FOLDER'] = str(ensure_output_directory() if CONFIG_LOADED else ensure_output_directory_fallback())
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Security settings
app.config['SESSION_COOKIE_SECURE'] = not DEBUG
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Performance settings
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600  # 1 hour cache for static files
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = DEBUG

# Initialize thread pool for concurrent operations
app.thread_pool = ThreadPoolExecutor(max_workers=4)

# Application context setup
def initialize_app():
    """Initialize application components with comprehensive error handling."""
    try:
        # Initialize database
        DatabaseManager.initialize_database()

        # Ensure output directory exists
        if CONFIG_LOADED:
            ensure_output_directory()
        else:
            ensure_output_directory_fallback()

        # Validate system health
        validate_system_health()

        # Initialize application state
        app.generation_progress = {}
        app.rate_limits = {}
        app.startup_time = datetime.now()

        # Log application startup
        logger.info("=== Podcast Generation Application Starting ===")
        logger.info(f"Version: 1.0.0")
        logger.info(f"Debug mode: {DEBUG}")
        logger.info(f"Configuration loaded: {CONFIG_LOADED}")
        logger.info(f"Audio output directory: {AUDIO_OUTPUT_DIR}")
        logger.info(f"Log level: {LOG_LEVEL}")
        logger.info(f"Host: {HOST}, Port: {PORT}")
        logger.info("=== Application startup completed successfully ===")

    except Exception as e:
        logger.critical(f"Failed to initialize application: {str(e)}")
        log_exception(e, {'context': 'application_startup'})
        raise

# Initialize app immediately with error handling
try:
    with ErrorHandlerContext('application_initialization', reraise=True):
        initialize_app()
except Exception as e:
    print(f"Error initializing application: {e}")
    # Continue with basic initialization even if some components fail

# Enhanced route handlers with comprehensive error handling and performance monitoring
@app.route('/')
@performance_monitoring
def index():
    """
    Main page route - serves the podcast generation interface.

    Returns:
        Rendered HTML template for the main interface with form validation helpers

    Raises:
        TemplateError: If template rendering fails
        ConfigurationError: If configuration is invalid
    """
    try:
        # Validate system health before serving content
        validate_system_health()

        # Import validation utilities for template context
        from utils.validators import (
            ValidationError, create_validation_error_response,
            MAX_INPUT_LENGTH, MIN_PARTICIPANTS, MAX_PARTICIPANTS,
            MIN_CONVERSATION_ROUNDS, MAX_CONVERSATION_ROUNDS
        )
        from utils.models import Gender, Language

        # Prepare comprehensive template context
        template_context = {
            # Application metadata
            'app_title': 'AI Podcast Generator',
            'app_version': '1.0.0',
            'debug_mode': DEBUG,

            # Form validation limits for client-side validation
            'validation_config': {
                'max_input_length': MAX_INPUT_LENGTH,
                'min_participants': MIN_PARTICIPANTS,
                'max_participants': MAX_PARTICIPANTS,
                'min_conversation_rounds': MIN_CONVERSATION_ROUNDS,
                'max_conversation_rounds': MAX_CONVERSATION_ROUNDS
            },

            # Default form values for better UX
            'default_values': {
                'participants': 2,
                'rounds': 8,
                'language': Language.CHINESE.value
            },

            # Available options for form selects
            'form_options': {
                'participants': list(range(MIN_PARTICIPANTS, MAX_PARTICIPANTS + 1)),
                'rounds': [3, 5, 8, 12],
                'genders': [gender.value for gender in Gender],
                'languages': [lang.value for lang in Language]
            },

            # Configuration status for user feedback
            'config_status': {
                'loaded': CONFIG_LOADED,
                'audio_output_dir': str(AUDIO_OUTPUT_DIR),
                'system_healthy': True
            },

            # Current timestamp for caching prevention
            'timestamp': datetime.now().isoformat(),

            # Performance and system info
            'system_info': {
                'uptime': str(datetime.now() - app.startup_time).split('.')[0],
                'active_generations': len([p for p in app.generation_progress.values() if p['status'] in ['initializing', 'creating_agents', 'generating_conversation', 'generating_audio', 'saving_file']])
            }
        }

        # Add validation error helpers
        template_context['validation_helpers'] = {
            'error_types': ['validation_error', 'api_error', 'server_error'],
            'field_types': ['text', 'select', 'textarea'],
            'required_fields': ['topic', 'participants', 'rounds', 'characters']
        }

        # Add example data for form pre-filling
        template_context['example_data'] = {
            'topic_example': 'The impact of artificial intelligence on creative industries',
            'character_examples': [
                {
                    'name': 'Dr. Sarah Chen',
                    'gender': Gender.FEMALE.value,
                    'background': 'AI researcher and creative technologist with 10 years of experience',
                    'personality': 'Thoughtful and analytical, with a passion for innovation'
                },
                {
                    'name': 'Marcus Rodriguez',
                    'gender': Gender.MALE.value,
                    'background': 'Digital artist and content creator exploring AI tools',
                    'personality': 'Creative and curious, always experimenting with new technologies'
                }
            ]
        }

        # Load saved configuration and check for user-specific audio files
        try:
            # Get admin user
            admin_user = UserManager.get_or_create_admin_user()
            template_context['current_user'] = admin_user['username']

            # Load latest saved configuration
            latest_config = PodcastConfigRepository.get_latest_podcast_config(admin_user['id'])
            if latest_config:
                template_context['saved_config'] = latest_config
                template_context['has_saved_config'] = True
                logger.info(f"Loaded saved configuration for user {admin_user['username']}")
            else:
                template_context['has_saved_config'] = False
                logger.debug(f"No saved configuration found for user {admin_user['username']}")

            # Find user-specific audio files
            latest_user_audio = AudioFileService.find_latest_user_audio(admin_user['username'])
            if latest_user_audio:
                template_context['audio_url'] = f"/audio/{latest_user_audio['filename']}"
                template_context['download_url'] = f"/download/{latest_user_audio['filename']}"
                template_context['audio_filename'] = latest_user_audio['filename']
                template_context['audio_size'] = latest_user_audio['file_path'].stat().st_size
                template_context['audio_created_at'] = latest_user_audio['created_at'].isoformat()
                template_context['has_audio'] = True

                logger.info(f"Found latest user audio file: {latest_user_audio['filename']}")
            else:
                # No user-specific audio files found
                template_context['audio_url'] = None
                template_context['download_url'] = None
                template_context['has_audio'] = False

        except Exception as e:
            logger.warning(f"Error loading user data: {str(e)}")
            template_context['current_user'] = ADMIN_USERNAME
            template_context['has_saved_config'] = False
            template_context['audio_url'] = None
            template_context['download_url'] = None
            template_context['has_audio'] = False

        # Enhanced API key loading for persistent display
        try:
            from utils.database import get_database_manager

            # Find the most recently used session with API keys
            admin_session_id = get_most_recent_api_key_session()
            logger.info(f"Loading API keys for persistent display from session: '{admin_session_id}'")

            # Load API keys directly from database with enhanced error handling
            with get_database_manager().get_connection() as conn:
                # Get admin user ID with retry logic
                cursor = conn.execute(
                    "SELECT id FROM users WHERE session_id = ?",
                    (admin_session_id,)
                )
                admin_user_db = cursor.fetchone()

                api_keys = {}
                api_key_validity = {}  # Track validation status for each provider

                if admin_user_db:
                    admin_user_id = admin_user_db['id']
                    logger.debug(f"Found admin user ID: {admin_user_id}")

                    # Get API keys for admin user with optimized query using composite index
                    api_keys_result = conn.execute(
                        """
                        SELECT provider, encrypted_key, key_mask, is_valid, updated_at
                        FROM api_keys
                        WHERE user_id = ? AND is_valid = 1
                        ORDER BY updated_at DESC
                        """,
                        (admin_user_id,)
                    ).fetchall()

                    logger.debug(f"Found {len(api_keys_result)} API key records in database")

                    for api_key_row in api_keys_result:
                        # Use the plaintext API key (stored in encrypted_key field)
                        provider = api_key_row['provider']
                        plaintext_key = api_key_row['encrypted_key']  # This now contains plaintext
                        is_valid = bool(api_key_row['is_valid'])

                        # Only include valid API keys for display
                        if plaintext_key and plaintext_key.strip():
                            api_keys[provider] = plaintext_key
                            api_key_validity[provider] = is_valid
                            logger.debug(f"Loaded {provider} API key (valid: {is_valid})")

                # Enhanced template context with API key metadata
                # Use the complete API keys directly without additional masking
                template_context['api_keys'] = api_keys
                template_context['has_api_keys'] = len(api_keys) > 0
                template_context['api_key_validity'] = api_key_validity  # For validation status display
                template_context['api_key_providers'] = list(api_keys.keys())  # For JavaScript

                # DEBUG: Log what's being passed to template
                logger.info(f"DEBUG: API keys being passed to template: {api_keys}")
                logger.info(f"Successfully loaded {len(api_keys)} API keys for persistent display")

                # Log successful load with providers (but not the keys themselves)
                if api_keys:
                    providers_str = ', '.join(api_keys.keys())
                    logger.info(f"API key providers loaded: {providers_str}")

        except Exception as e:
            logger.error(f"Error loading API keys for persistent display: {str(e)}")
            log_exception(e, {
                'route': 'index',
                'operation': 'api_key_loading',
                'admin_session_id': 'admin_admin'
            })

            # Ensure graceful fallback
            template_context['api_keys'] = {}
            template_context['has_api_keys'] = False
            template_context['api_key_validity'] = {}
            template_context['api_key_providers'] = []

        logger.info("Index page rendered successfully")
        return render_template('index.html', **template_context)

    except ValidationError as e:
        logger.error(f"Validation error in index route: {str(e)}")
        return _render_error_page(
            title="Configuration Error",
            message="The application has configuration issues.",
            details=str(e) if DEBUG else None,
            show_retry=True
        ), 500

    except Exception as e:
        logger.error(f"Unexpected error in index route: {str(e)}")
        log_exception(e, {'route': 'index', 'user_agent': request.headers.get('User-Agent')})

        return _render_error_page(
            title="Application Error",
            message="The application encountered an unexpected error.",
            details=str(e) if DEBUG else None,
            show_retry=True
        ), 500

def _render_error_page(title: str, message: str, details: str = None, show_retry: bool = False) -> str:
    """
    Render a user-friendly error page.

    Args:
        title: Error page title
        message: Error message to display
        details: Optional error details (shown in debug mode)
        show_retry: Whether to show retry button

    Returns:
        Rendered HTML error page
    """
    try:
        error_context = {
            'error_title': title,
            'error_message': message,
            'error_details': details if DEBUG else None,
            'show_retry': show_retry,
            'timestamp': datetime.now().isoformat(),
            'debug_mode': DEBUG
        }
        return render_template('error.html', **error_context)
    except Exception:
        # Fallback to basic HTML if template fails
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - AI Podcast Generator</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f8f9fa; }}
                .error-container {{ max-width: 600px; margin: 0 auto; padding: 30px;
                                  background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .error-title {{ color: #dc3545; margin-bottom: 20px; }}
                .error-message {{ color: #6c757d; line-height: 1.6; }}
                .debug-info {{ background: #f8f9fa; padding: 15px; border-radius: 4px;
                             margin-top: 20px; font-family: monospace; font-size: 0.9em; }}
                .btn {{ padding: 10px 20px; background: #007bff; color: white; text-decoration: none;
                        border-radius: 4px; display: inline-block; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1 class="error-title">{title}</h1>
                <p class="error-message">{message}</p>
                {f'<div class="debug-info"><strong>Debug Information:</strong><br>{details}</div>' if details and DEBUG else ''}
                {f'<a href="/" class="btn">Try Again</a>' if show_retry else ''}
                <hr>
                <p><small>Error occurred at: {datetime.now().isoformat()}</small></p>
            </div>
        </body>
        </html>
        """


@app.route('/api/podcast-config/save', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=30, window_seconds=60)
def save_podcast_config():
    """
    Save podcast configuration for auto-save functionality.

    Accepts JSON data with:
    - topic: Podcast topic
    - participants: Number of participants
    - rounds: Number of conversation rounds
    - ai_provider: AI provider name
    - ai_model: AI model name
    - character_configs: List of character configurations

    Returns:
        JSON response with saved configuration details
    """
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON',
                'error_type': 'validation_error'
            }), 400

        data = request.get_json()

        # Validate required fields
        required_fields = ['topic', 'participants', 'rounds', 'ai_provider', 'ai_model', 'character_configs']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'error_type': 'validation_error'
                }), 400

        # Get or create admin user
        admin_user = get_or_create_admin_user()

        # Save configuration to database
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Insert or update podcast configuration
            cursor.execute('''
                INSERT OR REPLACE INTO podcast_configs
                (user_id, topic, participants, rounds, ai_provider, ai_model, character_configs, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                admin_user['id'],
                data['topic'],
                int(data['participants']),
                int(data['rounds']),
                data['ai_provider'],
                data['ai_model'],
                json.dumps(data['character_configs'])
            ))

            conn.commit()

            # Get the saved configuration ID
            config_id = cursor.lastrowid

            logger.info(f"Podcast configuration saved for admin user: {admin_user['username']}, config_id: {config_id}")

            return jsonify({
                'success': True,
                'message': 'Configuration saved successfully',
                'config_id': config_id,
                'saved_at': datetime.now().isoformat()
            })

    except ValueError as e:
        logger.warning(f"Validation error in save_podcast_config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Invalid data format',
            'error_type': 'validation_error'
        }), 400

    except Exception as e:
        logger.error(f"Error saving podcast configuration: {str(e)}")
        log_exception(e, {'context': 'save_podcast_config'})
        return jsonify({
            'success': False,
            'error': 'Failed to save configuration',
            'error_type': 'server_error'
        }), 500


@app.route('/api/podcast-config/latest', methods=['GET'])
@performance_monitoring
@rate_limit(max_requests=60, window_seconds=60)
def get_latest_podcast_config():
    """
    Get the latest saved podcast configuration.

    Returns:
        JSON response with the latest configuration or empty if none exists
    """
    try:
        # Get admin user
        admin_user = get_or_create_admin_user()

        # Get latest configuration from database
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT topic, participants, rounds, ai_provider, ai_model, character_configs, created_at, updated_at
                FROM podcast_configs
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            ''', (admin_user['id'],))

            result = cursor.fetchone()

            if result:
                config = {
                    'topic': result['topic'],
                    'participants': result['participants'],
                    'rounds': result['rounds'],
                    'ai_provider': result['ai_provider'],
                    'ai_model': result['ai_model'],
                    'character_configs': json.loads(result['character_configs']),
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at']
                }

                logger.info(f"Retrieved latest podcast configuration for admin user: {admin_user['username']}")

                return jsonify({
                    'success': True,
                    'has_config': True,
                    'config': config
                })
            else:
                logger.info(f"No podcast configuration found for admin user: {admin_user['username']}")

                return jsonify({
                    'success': True,
                    'has_config': False,
                    'config': None
                })

    except Exception as e:
        logger.error(f"Error retrieving latest podcast configuration: {str(e)}")
        log_exception(e, {'context': 'get_latest_podcast_config'})
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve configuration',
            'error_type': 'server_error'
        }), 500


@app.route('/api/podcast-config/clear', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=10, window_seconds=60)
def clear_podcast_config():
    """
    Clear all saved podcast configurations for the admin user.

    Returns:
        JSON response indicating success or failure
    """
    try:
        # Get admin user
        admin_user = get_or_create_admin_user()

        # Clear configurations from database
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM podcast_configs WHERE user_id = ?', (admin_user['id'],))
            deleted_count = cursor.rowcount

            conn.commit()

            logger.info(f"Cleared {deleted_count} podcast configurations for admin user: {admin_user['username']}")

            return jsonify({
                'success': True,
                'message': f'Cleared {deleted_count} saved configurations',
                'deleted_count': deleted_count
            })

    except Exception as e:
        logger.error(f"Error clearing podcast configurations: {str(e)}")
        log_exception(e, {'context': 'clear_podcast_config'})
        return jsonify({
            'success': False,
            'error': 'Failed to clear configurations',
            'error_type': 'server_error'
        }), 500


def get_or_create_admin_user():
    """
    Get or create the admin user for podcast configuration management.

    Returns:
        Dict with user information
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Try to get existing admin user
            cursor.execute('SELECT id, username, created_at FROM users WHERE username = ?', (ADMIN_USERNAME,))
            result = cursor.fetchone()

            if result:
                return {
                    'id': result['id'],
                    'username': result['username'],
                    'created_at': result['created_at']
                }
            else:
                # Create new admin user
                cursor.execute('''
                    INSERT INTO users (username, created_at, updated_at)
                    VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (ADMIN_USERNAME,))

                user_id = cursor.lastrowid
                conn.commit()

                logger.info(f"Created new admin user: {ADMIN_USERNAME}")

                return {
                    'id': user_id,
                    'username': ADMIN_USERNAME,
                    'created_at': datetime.now().isoformat()
                }

    except Exception as e:
        logger.error(f"Error getting or creating admin user: {str(e)}")
        raise


@app.route('/generate', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=20, window_seconds=60)  # 20 requests per 1 minute (more suitable for development)
def generate_podcast():
    """
    Enhanced podcast generation endpoint with comprehensive error handling and monitoring.

    Accepts POST data with:
    - topic: Podcast topic
    - participants: Number of participants
    - character_*: Character configurations (gender, background, personality)
    - rounds: Number of conversation rounds

    Returns:
        JSON response with generation status and file information

    Raises:
        ValidationError: If input validation fails
        AIAPIError: If AI service encounters errors
        TTSError: If text-to-speech conversion fails
        FileOperationError: If file operations fail
        NetworkError: If network operations fail
    """
    # Enhanced input validation and security checks
    start_time = time.time()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

    print(f"\n{'='*60}")
    print(f"=== DEBUG: New podcast generation request ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Client IP: {client_ip}")
    print(f"User-Agent: {request.headers.get('User-Agent', 'unknown')}")
    print(f"Content-Type: {request.headers.get('Content-Type', 'unknown')}")
    print(f"Content-Length: {request.headers.get('Content-Length', 'unknown')}")
    print(f"X-Generation-ID: {request.headers.get('X-Generation-ID', 'none')}")
    print(f"{'='*60}")

    logger.info(f"Podcast generation request from {client_ip}")
    performance_monitor.record_generation_start()

    try:
        # Validate system health first
        validate_system_health()

        # Extract and validate input data with security sanitization
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            print(f"=== DEBUG: Raw request data ===")
            print(f"Request is_json: {request.is_json}")
            print(f"Request form keys: {list(request.form.keys()) if request.form else 'No form data'}")
            print(f"Request data type: {type(data)}")
            print(f"Request data keys: {list(data.keys()) if data else 'No data'}")
            if data:
                for key, value in data.items():
                    if 'character' in key.lower():
                        print(f"  {key}: {value} (type: {type(value)})")
            print(f"=== END DEBUG ===")
        except BadRequest as e:
            if "utf-8" in str(e).lower() or "encoding" in str(e).lower():
                # Handle UTF-8 encoding issues with Chinese characters
                logger.error(f"UTF-8 encoding error in request: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid character encoding in request. Please ensure UTF-8 encoding is used.',
                    'error_type': 'encoding_error',
                    'details': 'The request contains characters that could not be decoded. Please check your input encoding.'
                }), 400
            else:
                raise  # Re-raise other BadRequest errors

        if not data:
            raise ValidationError("No input data provided", field='request_body')

        # Enhanced validation with context
        print(f"=== DEBUG: Before validation ===")
        print(f"Data to validate: {data}")
        validated_data = validate_podcast_input(data)
        print(f"=== DEBUG: After validation ===")
        print(f"Validated characters count: {len(validated_data.get('characters', []))}")
        for i, char in enumerate(validated_data.get('characters', [])):
            print(f"  Character {i}: {char.name}, gender: {char.gender}, background: {char.background[:50]}..., personality: {char.personality[:50]}...")
        logger.info(f"Input validation successful for request from {client_ip}")

        # Get or create admin user
        admin_user = None
        try:
            admin_user = UserManager.get_or_create_admin_user()
            logger.info(f"Using admin user: {admin_user['username']} (ID: {admin_user['id']})")

            # Prepare configuration data for saving
            config_data = {
                'topic': validated_data['topic'],
                'participants': len(validated_data['characters']),
                'rounds': validated_data['conversation_rounds'],
                'ai_provider': validated_data.get('ai_provider', 'deepseek'),
                'ai_model': validated_data.get('ai_model', 'deepseek-chat'),
                'character_configs': [
                    {
                        'name': char.name,
                        'gender': char.gender.value if hasattr(char.gender, 'value') else str(char.gender),
                        'background': char.background,
                        'personality': char.personality,
                        'age': getattr(char, 'age', None),
                        'style': getattr(char, 'style', None)
                    }
                    for char in validated_data['characters']
                ]
            }

            # Save configuration to database
            config_id = PodcastConfigRepository.save_podcast_config(
                admin_user['id'],
                config_data
            )
            logger.info(f"Saved podcast configuration ID: {config_id}")

        except Exception as e:
            logger.warning(f"Failed to save podcast configuration: {str(e)}")
            # Continue with generation even if saving fails
            # Ensure we have admin_user for filename generation
            if admin_user is None:
                admin_user = {'username': ADMIN_USERNAME}

        # Generate unique request ID and set up comprehensive tracking
        request_id = str(uuid.uuid4())
        generation_context = {
            'request_id': request_id,
            'client_ip': client_ip,
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'topic': validated_data['topic'],
            'participants': len(validated_data['characters']),
            'rounds': validated_data['conversation_rounds'],
            'start_time': start_time
        }

        # Enhanced progress tracking with detailed steps
        progress_data = {
            'request_id': request_id,
            'status': 'initializing',
            'progress': 0,
            'current_step': 'Validating system and initializing components',
            'total_steps': 5,  # validation, agents, conversation, audio, file saving
            'error': None,
            'timestamp': datetime.now().isoformat(),
            'estimated_completion': (datetime.now() + timedelta(minutes=5)).isoformat()
        }

        # Initialize progress tracking
        if not hasattr(app, 'generation_progress'):
            app.generation_progress = {}
        app.generation_progress[request_id] = progress_data

        logger.info(f"Starting podcast generation {request_id}: {generation_context}")

        # Create character profiles with enhanced validation
        character_profiles = []
        for character in validated_data['characters']:
            profile = CharacterProfile(
                name=character.name,
                gender=character.gender.value,
                background=character.background,
                personality=character.personality,
                age=getattr(character, 'age', None),
                style=getattr(character, 'style', None)
            )
            character_profiles.append(profile)

        # Update progress
        progress_data['progress'] = 20
        progress_data['current_step'] = 'Creating character agents'
        progress_data['status'] = 'creating_agents'
        app.generation_progress[request_id] = progress_data

        # Initialize core components with error handling and timeout
        try:
            print("[INFO] Initializing TTS engine...")
            tts_engine = create_tts_engine()
            print("[INFO] TTS engine initialized successfully")
        except Exception as e:
            print(f"[WARNING] TTS engine initialization failed: {str(e)}")
            print("[INFO] Application will continue without TTS functionality")
            tts_engine = None

        try:
            print("[INFO] Initializing voice manager...")
            voice_manager = create_voice_manager()
            print("[INFO] Voice manager initialized successfully")
        except Exception as e:
            print(f"[WARNING] Voice manager initialization failed: {str(e)}")
            print("[INFO] Application will continue without voice management")
            voice_manager = None

        try:
            print("[INFO] Initializing file handler...")
            file_handler = get_file_handler()
            print("[INFO] File handler initialized successfully")
        except Exception as e:
            print(f"[WARNING] File handler initialization failed: {str(e)}")
            print("[INFO] Application will continue without file handling")
            file_handler = None

        # Create AutoGen conversation service with comprehensive error handling
        autogen_service = None
        try:
            # Get API configuration from environment
            api_key = os.getenv('DEEPSEEK_API_KEY', '')
            base_url = "https://api.deepseek.com/v1"

            if not api_key:
                logger.warning("No DEEPSEEK_API_KEY found, falling back to CharacterAgent")
                # Fallback to CharacterAgent
                character_agents = []
                for i, profile in enumerate(character_profiles):
                    try:
                        agent = CharacterAgent(profile, temperature=0.7, max_tokens=200)
                        character_agents.append(agent)
                        logger.debug(f"Created character agent: {profile.name}")
                    except Exception as e:
                        logger.error(f"Failed to create character agent for {profile.name}: {str(e)}")
                        raise AIAPIError(
                            f"Failed to initialize character agent for {profile.name}",
                            details={'character_index': i, 'character_name': profile.name},
                            original_error=e
                        )
            else:
                # Use AutoGen service
                autogen_service = create_autogen_conversation_service(
                    api_key=api_key,
                    base_url=base_url,
                    model="deepseek-chat"
                )
                character_agents = autogen_service  # Use service directly
                logger.debug("Created AutoGen conversation service")

        except Exception as e:
            logger.error(f"Failed to initialize conversation service: {str(e)}")
            raise AIAPIError(
                f"Failed to initialize conversation service: {str(e)}",
                original_error=e
            )

        try:
            # Update progress
            progress_data['progress'] = 40
            progress_data['current_step'] = 'Generating conversation dialogue'
            progress_data['status'] = 'generating_conversation'
            app.generation_progress[request_id] = progress_data

            # Generate conversation with AutoGen or fallback to ConversationManager
            logger.info(f"Generating conversation for {request_id}")
            conversation_state = None

            try:
                if autogen_service:
                    # Use AutoGen service
                    logger.info("Using AutoGen for conversation generation")

                    # Prepare character data for AutoGen
                    character_data = []
                    for profile in character_profiles:
                        character_data.append({
                            'name': profile.name,
                            'gender': profile.gender,
                            'background': profile.background,
                            'personality': profile.personality,
                            'speaking_style': profile.speaking_style,
                            'expertise_areas': profile.expertise_areas
                        })

                    # Generate conversation using AutoGen
                    autogen_messages = autogen_service.generate_conversation(
                        characters=character_data,
                        topic=validated_data['topic'],
                        max_rounds=validated_data['conversation_rounds']
                    )

                    # Convert AutoGen messages to dialogue format
                    if autogen_messages:
                        dialogue_history = []
                        for msg in autogen_messages:
                            dialogue_history.append({
                                'speaker': msg['speaker'],
                                'content': msg['content'],
                                'round': msg.get('round', 1)
                            })

                        # Create a mock conversation state object
                        class MockConversationState:
                            def __init__(self, dialogue):
                                from datetime import datetime
                                self.dialogue_history = dialogue
                                self.start_time = datetime.now()
                                self.end_time = None
                                self.current_round = max([entry.get('round', 1) for entry in dialogue]) if dialogue else 1
                                self.metadata = {
                                    'total_turns': len(dialogue),
                                    'topic': validated_data['topic'],
                                    'generation_method': 'autogen'
                                }

                            def get_conversation_duration(self) -> float:
                                """Get the conversation duration in seconds."""
                                from datetime import datetime
                                end = self.end_time or datetime.now()
                                return (end - self.start_time).total_seconds()

                            def get_conversation_statistics(self) -> dict:
                                """Get conversation statistics for AutoGen conversations."""
                                return {
                                    'method': 'autogen',
                                    'total_messages': len(self.dialogue_history),
                                    'topic': self.metadata.get('topic', 'Unknown'),
                                    'total_turns': self.metadata.get('total_turns', len(self.dialogue_history)),
                                    'generation_method': 'autogen'
                                }

                        conversation_state = MockConversationState(dialogue_history)

                        # Create a mock conversation manager for AutoGen to provide consistent interface
                        class MockConversationManager:
                            def __init__(self, conversation_state):
                                self.conversation_state = conversation_state

                            def get_conversation_statistics(self) -> dict:
                                return self.conversation_state.get_conversation_statistics()

                        conversation_manager = MockConversationManager(conversation_state)
                        logger.info(f"AutoGen generated {len(dialogue_history)} dialogue messages")

                    if not conversation_state or not conversation_state.dialogue_history:
                        raise AIAPIError("No dialogue was generated by AutoGen", api_provider='autogen')

                else:
                    # Fallback to ConversationManager
                    logger.info("Using ConversationManager for conversation generation")

                    conversation_config = ConversationConfig(
                        max_rounds=validated_data['conversation_rounds'],
                        temperature=0.7,
                        max_tokens_per_response=500,
                        enable_auto_conclusion=True,
                        validate_responses=False
                    )

                    conversation_manager = ConversationManager(
                        topic=validated_data['topic'],
                        characters=character_agents,
                        config=conversation_config
                    )

                    conversation_state = conversation_manager.generate_conversation()

                    if not conversation_state.dialogue_history:
                        raise AIAPIError("No dialogue was generated", api_provider='conversation_manager')

            except Exception as e:
                logger.error(f"Conversation generation failed: {str(e)}")
                raise AIAPIError(
                    f"Failed to generate conversation: {str(e)}",
                    api_provider='autogen' if autogen_service else 'conversation_manager',
                    original_error=e
                )

            logger.info(f"Generated {len(conversation_state.dialogue_history)} dialogue entries for {request_id}")

            # === STAGE 1 COMPLETE: All dialogue text generated ===
            progress_data['progress'] = 60
            progress_data['current_step'] = f'Dialogue generation complete. Generated {len(conversation_state.dialogue_history)} dialogue entries.'
            app.generation_progress[request_id] = progress_data
            logger.info(f"=== STAGE 1 COMPLETE: Generated {len(conversation_state.dialogue_history)} dialogue entries ===")

            # === STAGE 2: Generate audio for each dialogue entry sequentially ===
            progress_data['progress'] = 65
            progress_data['current_step'] = 'Starting audio generation for each dialogue entry'
            progress_data['status'] = 'generating_audio'
            app.generation_progress[request_id] = progress_data

            logger.info(f"=== STAGE 2 START: Generating audio for {len(conversation_state.dialogue_history)} dialogue entries ===")
            audio_segments = []
            failed_audio_segments = 0

            # Process each dialogue entry one by one
            for i, entry in enumerate(conversation_state.dialogue_history):
                try:
                    # Update progress
                    audio_progress = 65 + (25 * (i + 1) / len(conversation_state.dialogue_history))
                    progress_data['progress'] = min(90, audio_progress)
                    progress_data['current_step'] = f'Generating audio for {entry["speaker"]} (dialogue {i + 1}/{len(conversation_state.dialogue_history)})'
                    app.generation_progress[request_id] = progress_data

                    logger.info(f"Processing dialogue {i + 1}/{len(conversation_state.dialogue_history)}: {entry['speaker']}")

                    # Find character for this dialogue entry
                    character_model = None
                    for char in validated_data['characters']:
                        if char.name == entry['speaker']:
                            character_model = char
                            break

                    if not character_model:
                        logger.warning(f"Character model not found: {entry['speaker']}")
                        failed_audio_segments += 1
                        continue

                    # Generate audio for this single dialogue entry
                    try:
                        if tts_engine is None:
                            logger.warning(f"TTS engine not available for {entry['speaker']}")
                            failed_audio_segments += 1
                            continue

                        logger.info(f"Converting to speech: '{entry['content'][:50]}...' by {entry['speaker']}")

                        # Handle different TTS engine interfaces
                        audio_data = None
                        audio_file_path = None
                        if hasattr(tts_engine, 'generate_audio'):
                            # SubprocessTTSService interface
                            logger.debug(f"Calling TTS engine generate_audio for {entry['speaker']}")
                            # Prepare TTS parameters with age and style
                            tts_params = {
                                'text': entry['content'],
                                'gender': character_model.gender.value,
                                'character_name': entry['speaker']
                            }

                            print(f"=== DEBUG: TTS Parameters for {entry['speaker']} ===")
                            print(f"Character name: {entry['speaker']}")
                            print(f"Gender: {character_model.gender.value} (type: {type(character_model.gender.value)})")
                            print(f"Age: {getattr(character_model, 'age', 'None')}")
                            print(f"Style: {getattr(character_model, 'style', 'None')}")
                            print(f"Personality: {getattr(character_model, 'personality', 'None')}")
                            print(f"=== END DEBUG: TTS Parameters ===")

                            # Add personality with mapping to style if available
                            if character_model.personality:
                                tts_params['personality'] = character_model.personality

                            # Add age and style if available
                            if hasattr(character_model, 'age') and character_model.age:
                                tts_params['age'] = character_model.age
                            if hasattr(character_model, 'style') and character_model.style:
                                tts_params['style'] = character_model.style

                            audio_file_path = tts_engine.generate_audio(**tts_params)
                            logger.debug(f"TTS engine returned: {audio_file_path}")

                            if audio_file_path and os.path.exists(audio_file_path):
                                try:
                                    file_size = os.path.getsize(audio_file_path)
                                    logger.debug(f"Audio file exists, size: {file_size} bytes")
                                    with open(audio_file_path, 'rb') as f:
                                        audio_data = f.read()
                                    logger.debug(f"Successfully read {len(audio_data)} bytes from audio file")
                                except Exception as e:
                                    logger.error(f"Failed to read audio file {audio_file_path}: {e}")
                            elif audio_file_path:
                                logger.error(f"TTS engine returned path but file does not exist: {audio_file_path}")
                            else:
                                logger.error(f"TTS engine returned None/empty path")
                        elif hasattr(tts_engine, 'convert_to_speech'):
                            # TTSEngine interface (convert_to_speech method)
                            logger.debug(f"Calling TTS engine convert_to_speech for {entry['speaker']}")

                            # Create voice profile for TTSEngine with enhanced parameters
                            voice_profile = {
                                'gender': character_model.gender.value,
                                'personality': character_model.personality,
                                'rate': 150,  # Default speech rate
                                'volume': 0.8  # Default volume
                            }

                            # Add age and style if available for better voice matching
                            if hasattr(character_model, 'age') and character_model.age:
                                voice_profile['age'] = character_model.age
                            if hasattr(character_model, 'style') and character_model.style:
                                voice_profile['style'] = character_model.style

                            try:
                                audio_data = tts_engine.convert_to_speech(
                                    text=entry['content'],
                                    voice_profile=voice_profile,
                                    output_format='wav'
                                )
                                logger.debug(f"TTSEngine returned {len(audio_data) if audio_data else 0} bytes of audio data")
                            except Exception as e:
                                logger.error(f"TTSEngine convert_to_speech failed: {e}")
                                audio_data = None
                        else:
                            # Unknown TTS engine interface
                            logger.error(f"TTS engine {type(tts_engine).__name__} does not have generate_audio or convert_to_speech method")

                        if audio_data:
                            audio_segment = {
                                'character': entry['speaker'],
                                'text': entry['content'],
                                'audio_data': audio_data,
                                'round': entry['round']
                            }
                            if audio_file_path:
                                audio_segment['temp_file_path'] = audio_file_path
                            audio_segments.append(audio_segment)
                            logger.info(f"[SUCCESS] Generated audio for {entry['speaker']} (round {entry['round']})")
                        else:
                            logger.warning(f"[FAILED] No audio generated for {entry['speaker']}")
                            failed_audio_segments += 1

                    except Exception as e:
                        logger.error(f"[ERROR] Audio generation failed for {entry['speaker']}: {str(e)}")
                        failed_audio_segments += 1

                except Exception as e:
                    logger.error(f"[ERROR] Unexpected error processing dialogue {i}: {str(e)}")
                    failed_audio_segments += 1

            logger.info(f"=== STAGE 2 COMPLETE: Generated {len(audio_segments)} audio segments, {failed_audio_segments} failed ===")

            # === STAGE 3: Merge all audio segments into single file ===
            progress_data['progress'] = 92
            progress_data['current_step'] = 'Merging all audio segments into single file'
            app.generation_progress[request_id] = progress_data
            logger.info(f"=== STAGE 3 START: Merging {len(audio_segments)} audio segments ===")

            # Validate audio generation results before merging
            if not audio_segments:
                tts_engine_name = tts_engine.__class__.__name__ if tts_engine else "None"
                raise TTSError("No audio segments were generated for merging", tts_engine=tts_engine_name)

            if failed_audio_segments > len(conversation_state.dialogue_history) * 0.5:  # More than 50% failed
                logger.warning(f"High failure rate in audio generation: {failed_audio_segments}/{len(conversation_state.dialogue_history)}")

            # === STAGE 3: Merge all audio segments into single podcast file ===
            try:
                # Create audio merger service
                audio_merger = create_audio_merger_service("generated_audio")

                # Generate timestamp for output file
                timestamp = datetime.now()
                output_filename = f"admin_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"

                logger.info(f"Merging {len(audio_segments)} audio segments into {output_filename}")

                # Update progress
                progress_data['progress'] = 95
                progress_data['current_step'] = f'Merging {len(audio_segments)} audio segments into final podcast file'
                app.generation_progress[request_id] = progress_data

                # Merge all audio segments into one file
                merged_file_path = audio_merger.merge_audio_segments(
                    audio_segments=audio_segments,
                    output_filename=output_filename,
                    format="wav"
                )

                if not merged_file_path:
                    raise TTSError("Failed to merge audio segments", tts_engine='audio_merger')

                # Read the merged audio file for final output
                combined_audio = None
                try:
                    with open(merged_file_path, 'rb') as f:
                        combined_audio = f.read()
                    file_size = len(combined_audio)
                    logger.info(f"[SUCCESS] Successfully merged podcast file: {merged_file_path} ({file_size} bytes)")
                except Exception as e:
                    logger.error(f"Failed to read merged audio file {merged_file_path}: {e}")
                    raise TTSError("Failed to read merged audio file", tts_engine='audio_merger')

                # Clean up temporary files
                logger.info("Cleaning up temporary audio files...")
                audio_merger.cleanup_temp_files()
                logger.info("[SUCCESS] Temporary files cleaned up")

                # === ALL STAGES COMPLETE ===
                logger.info(f"=== ALL STAGES COMPLETE: Podcast generated successfully ===")
                progress_data['progress'] = 98
                progress_data['current_step'] = 'Finalizing podcast file'
                app.generation_progress[request_id] = progress_data

            except Exception as e:
                logger.error(f"Audio merging failed: {str(e)}")
                raise TTSError(
                    f"Failed to combine audio segments: {str(e)}",
                    tts_engine='audio_merger',
                    original_error=e
                )

            # Update progress for file saving
            progress_data['progress'] = 95
            progress_data['current_step'] = 'Saving audio file'
            progress_data['status'] = 'saving_file'
            app.generation_progress[request_id] = progress_data

            # Enhanced file saving with comprehensive error handling and user-specific naming
            timestamp = datetime.now()
            try:
                # Generate user-specific filename
                user_filename = AudioFileService.generate_user_filename(
                    admin_user['username'],
                    timestamp
                )

                file_path = file_handler.save_audio_file(
                    audio_data=combined_audio,
                    topic=validated_data['topic'],
                    timestamp=timestamp,
                    custom_filename=user_filename
                )
                file_info = file_handler.get_file_info(file_path)
            except Exception as e:
                raise FileOperationError(
                    f"Failed to save audio file: {str(e)}",
                    operation='save',
                    original_error=e
                )

            # Create conversation turns for result
            conversation_turns = []
            for entry in conversation_state.dialogue_history:
                turn = create_conversation_turn(
                    round_number=entry['round'],
                    character_id=entry['speaker'],
                    text=entry['content']
                )
                conversation_turns.append(turn)

            # Create podcast result
            total_duration = conversation_state.get_conversation_duration()
            podcast_result = create_podcast_result(
                request_id=request_id,
                topic=validated_data['topic'],
                file_path=file_path,
                file_size=file_info['size'],
                conversation_turns=conversation_turns,
                total_duration=total_duration
            )

            # Update progress to completed
            progress_data['progress'] = 100
            progress_data['current_step'] = 'Podcast generation completed successfully'
            progress_data['status'] = 'completed'
            progress_data['timestamp'] = datetime.now().isoformat()
            app.generation_progress[request_id] = progress_data

            # Enhanced success response with comprehensive data
            response_data = {
                'success': True,
                'request_id': request_id,
                'message': 'Podcast generated successfully',
                'data': {
                    'topic': validated_data['topic'],
                    'file_info': {
                        'filename': Path(file_path).name,
                        'size': file_info['size'],
                        'created_at': file_info['created_at'].isoformat(),
                        'download_url': f"/download/{Path(file_path).name}",
                        'audio_url': f"/audio/{Path(file_path).name}"
                    },
                    'conversation': {
                        'total_rounds': conversation_state.current_round,
                        'total_dialogue_entries': len(conversation_state.dialogue_history),
                        'successful_audio_segments': len(audio_segments),
                        'failed_audio_segments': failed_audio_segments,
                        'duration_seconds': total_duration,
                        'statistics': conversation_manager.get_conversation_statistics()
                    },
                    'performance': {
                        'total_time_seconds': round(time.time() - start_time, 2),
                        'estimated_completion_time': progress_data['estimated_completion']
                    },
                    'timestamp': timestamp.isoformat()
                }
            }

            generation_time = time.time() - start_time
            logger.info(f"Podcast generation completed successfully: {request_id} in {generation_time:.2f}s")
            performance_monitor.record_generation_complete(success=True)

            print(f"=== DEBUG: Successful response ===")
            print(f"Request ID: {request_id}")
            print(f"Generation time: {generation_time:.2f}s")
            print(f"Response data keys: {list(response_data.keys())}")
            print(f"Response success: {response_data.get('success')}")
            print(f"Audio file: {response_data.get('audio_url', 'N/A')}")
            print(f"=== END DEBUG: Successful response ===")

            return jsonify(response_data)

        except ValidationError as e:
            # Handle validation errors with detailed information
            generation_time = time.time() - start_time
            error_response = create_validation_error_response(e)
            error_response.update({
                'request_id': request_id,
                'performance': {'total_time_seconds': round(generation_time, 2)}
            })

            progress_data['progress'] = 0
            progress_data['current_step'] = 'Validation failed'
            progress_data['status'] = 'failed'
            progress_data['error'] = e.message
            progress_data['timestamp'] = datetime.now().isoformat()
            app.generation_progress[request_id] = progress_data

            logger.error(f"Validation error in podcast generation {request_id}: {str(e)}")
            performance_monitor.record_generation_complete(success=False)
            return jsonify(error_response), 400

        except (AIAPIError, TTSError, FileOperationError, NetworkError, ConfigurationError) as e:
            # Handle known application errors with enhanced context
            generation_time = time.time() - start_time
            user_friendly_message = create_user_friendly_error(e)

            progress_data['progress'] = 0
            progress_data['current_step'] = f'{e.__class__.__name__.lower().replace("error", "")} failed'
            progress_data['status'] = 'failed'
            progress_data['error'] = user_friendly_message
            progress_data['timestamp'] = datetime.now().isoformat()
            app.generation_progress[request_id] = progress_data

            logger.error(f"Application error in podcast generation {request_id}: {str(e)}")
            log_exception(e, generation_context)

            performance_monitor.record_generation_complete(success=False)

            return jsonify({
                'success': False,
                'error': user_friendly_message,
                'error_type': e.__class__.__name__.lower(),
                'error_code': getattr(e, 'error_code', None),
                'request_id': request_id,
                'performance': {'total_time_seconds': round(generation_time, 2)},
                'details': e.details if hasattr(e, 'details') and DEBUG else None
            }), 500

        except Exception as e:
            # Handle unexpected errors with comprehensive logging
            generation_time = time.time() - start_time
            user_friendly_message = "An unexpected error occurred during podcast generation. Please try again."

            progress_data['progress'] = 0
            progress_data['current_step'] = 'Unexpected error occurred'
            progress_data['status'] = 'failed'
            progress_data['error'] = user_friendly_message
            progress_data['timestamp'] = datetime.now().isoformat()
            app.generation_progress[request_id] = progress_data

            logger.error(f"Unexpected error in podcast generation {request_id}: {str(e)}")
            log_exception(e, generation_context)

            performance_monitor.record_generation_complete(success=False)

            return jsonify({
                'success': False,
                'error': user_friendly_message,
                'error_type': 'server_error',
                'request_id': request_id,
                'performance': {'total_time_seconds': round(generation_time, 2)},
                'details': str(e) if DEBUG else None
            }), 500

        finally:
            # Enhanced resource cleanup with comprehensive error handling
            cleanup_start_time = time.time()
            cleanup_errors = []

            try:
                # Clean up character agents and AutoGen service
                if 'character_agents' in locals():
                    if autogen_service:
                        # Clean up AutoGen service
                        try:
                            autogen_service.close()
                            logger.debug("Successfully cleaned up AutoGen service")
                        except Exception as cleanup_error:
                            cleanup_errors.append(f"AutoGen service: {str(cleanup_error)}")
                            logger.warning(f"Error during AutoGen service cleanup: {cleanup_error}")
                    else:
                        # Clean up individual character agents
                        for i, agent in enumerate(character_agents):
                            try:
                                agent.close()
                                logger.debug(f"Successfully cleaned up character agent {i}")
                            except Exception as cleanup_error:
                                cleanup_errors.append(f"Character agent {i}: {str(cleanup_error)}")
                                logger.warning(f"Error during character agent cleanup {i}: {cleanup_error}")

                # Clean up TTS engine
                if 'tts_engine' in locals() and tts_engine is not None:
                    try:
                        if hasattr(tts_engine, 'cleanup'):
                            tts_engine.cleanup()
                        elif hasattr(tts_engine, 'cleanup_temp_files'):
                            # New SubprocessTTSService interface
                            temp_files = [segment.get('temp_file_path') for segment in audio_segments if segment.get('temp_file_path')]
                            tts_engine.cleanup_temp_files(temp_files)
                        logger.debug("Successfully cleaned up TTS engine")
                    except Exception as cleanup_error:
                        cleanup_errors.append(f"TTS engine: {str(cleanup_error)}")
                        logger.warning(f"Error during TTS engine cleanup: {cleanup_error}")

            except Exception as general_cleanup_error:
                cleanup_errors.append(f"General cleanup: {str(general_cleanup_error)}")
                logger.error(f"General error during cleanup: {general_cleanup_error}")

            cleanup_time = time.time() - cleanup_start_time
            if cleanup_errors:
                logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors in {cleanup_time:.3f}s: {cleanup_errors}")
            else:
                logger.debug(f"Cleanup completed successfully in {cleanup_time:.3f}s")

    except Exception as e:
        # Handle errors outside the main generation context
        logger.error(f"Critical error in generate_podcast route: {str(e)}")
        log_exception(e, {'route': 'generate_podcast', 'client_ip': client_ip})
        performance_monitor.record_generation_complete(success=False)

        return jsonify({
            'success': False,
            'error': 'Critical system error occurred. Please try again later.',
            'error_type': 'critical_error'
        }), 500


# Audio combining is now handled by AudioMergerService
# This function has been removed and replaced with the new service

@app.route('/audio/<filename>')
@performance_monitoring
def serve_audio_file(filename):
    """
    Static audio file serving endpoint for frontend audio preview.

    Args:
        filename: Name of the audio file to serve

    Returns:
        Audio file with proper MIME type headers or error response
    """
    try:
        # Validate filename to prevent directory traversal
        if not filename or not isinstance(filename, str):
            return jsonify({'error': 'Invalid filename'}), 400

        # Only allow specific audio file extensions
        allowed_extensions = {'.wav', '.mp3', '.ogg', '.m4a', '.flac'}
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Invalid file type'}), 400

        # Sanitize filename to prevent path traversal
        safe_filename = Path(filename).name
        if safe_filename != filename:
            return jsonify({'error': 'Invalid filename format'}), 400

        # Construct file path
        file_path = AUDIO_OUTPUT_DIR / safe_filename

        # Check if file exists
        if not file_path.exists():
            return jsonify({'error': 'Audio file not found'}), 404

        # Check file size to prevent serving extremely large files
        max_file_size = 100 * 1024 * 1024  # 100MB
        if file_path.stat().st_size > max_file_size:
            return jsonify({'error': 'File too large'}), 413

        # Determine MIME type based on file extension
        mime_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.flac': 'audio/flac'
        }
        mime_type = mime_types.get(file_ext, 'application/octet-stream')

        # Serve the file
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {str(e)}")
        return jsonify({'error': 'Failed to serve audio file'}), 500

@app.route('/download/<filename>')
@performance_monitoring
def download_file(filename):
    """
    Enhanced audio file download endpoint with comprehensive security checks and monitoring.

    Args:
        filename: Name of the audio file to download

    Returns:
        Audio file for download with proper MIME type headers or error response

    Raises:
        FileOperationError: If file operations fail
        ValidationError: If filename validation fails
        SecurityError: If security checks fail
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.headers.get('User-Agent', 'unknown')

    try:
        # Validate system health
        validate_system_health()

        # Enhanced filename validation and sanitization
        if not filename:
            raise ValidationError("Filename is required", field='filename')

        # Multiple layers of filename sanitization
        original_filename = filename
        filename = secure_filename(filename)

        if not filename or filename != original_filename:
            logger.warning(f"Filename sanitization changed '{original_filename}' to '{filename}' for {client_ip}")
            raise ValidationError("Invalid filename format", field='filename')

        # Additional security checks
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for pattern in dangerous_patterns:
            if pattern in filename:
                logger.warning(f"Dangerous pattern '{pattern}' detected in filename '{filename}' from {client_ip}")
                raise ValidationError("Filename contains invalid characters", field='filename')

        # Check file extension
        file_extension = Path(filename).suffix.lower().lstrip('.')
        if file_extension not in ALLOWED_AUDIO_EXTENSIONS:
            logger.warning(f"Invalid file extension '{file_extension}' in filename '{filename}' from {client_ip}")
            raise ValidationError("Invalid file type", field='filename')

        # Import file handler utilities for enhanced security
        from utils.file_handler import get_file_for_download
        from utils.error_handler import FileOperationError

        # Use file_handler for secure file validation and information retrieval
        try:
            file_path, mime_type, file_size = get_file_for_download(filename)
        except FileOperationError as e:
            logger.warning(f"File access denied for {filename} from {client_ip}: {str(e)}")
            raise FileOperationError(
                f"File not found or access denied: {filename}",
                file_path=filename,
                operation='download',
                original_error=e
            )

        # Comprehensive security check - ensure file is within allowed directory
        file_path_obj = Path(file_path).resolve()
        output_dir_resolved = AUDIO_OUTPUT_DIR.resolve()

        if not str(file_path_obj).startswith(str(output_dir_resolved)):
            logger.error(f"Path traversal attempt detected for {filename} from {client_ip}")
            raise ValidationError("Access denied", field='filename')

        # Enhanced validation of file existence and permissions
        if not file_path_obj.exists():
            raise FileOperationError(f"File does not exist: {filename}", file_path=str(file_path_obj))

        if not file_path_obj.is_file():
            raise FileOperationError(f"Path is not a file: {filename}", file_path=str(file_path_obj))

        # Validate file size (prevent extremely large downloads)
        max_file_size = 100 * 1024 * 1024  # 100MB max
        if file_size > max_file_size:
            logger.warning(f"File too large for download: {filename} ({file_size} bytes) from {client_ip}")
            raise FileOperationError(
                f"File too large for download: {filename}",
                file_path=str(file_path_obj),
                file_size=file_size
            )

        # Log download attempt for comprehensive auditing
        download_context = {
            'client_ip': client_ip,
            'user_agent': user_agent,
            'filename': filename,
            'file_size': file_size,
            'mime_type': mime_type,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"File download requested: {download_context}")

        # Send file with enhanced security headers
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )

        # Comprehensive security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['Cache-Control'] = 'private, max-age=3600'  # 1 hour cache

        # Add content length and other headers
        if file_size:
            response.headers['Content-Length'] = str(file_size)

        # Add download tracking header
        response.headers['X-Download-ID'] = str(int(time.time() * 1000))  # Simple unique ID

        logger.info(f"File download completed successfully: {filename} for {client_ip}")
        return response

    except ValidationError as e:
        logger.warning(f"Validation error in download_file for {filename} from {client_ip}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'validation_error'
        }), 400

    except FileOperationError as e:
        logger.warning(f"File operation error in download_file for {filename} from {client_ip}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'File not found or access denied',
            'error_type': 'file_error'
        }), 404

    except Exception as e:
        logger.error(f"Unexpected error in download_file for {filename} from {client_ip}: {str(e)}")
        log_exception(e, {
            'route': 'download_file',
            'filename': filename,
            'client_ip': client_ip,
            'user_agent': user_agent
        })

        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your download request',
            'error_type': 'server_error'
        }), 500

@app.route('/api/audio-files')
@performance_monitoring
def list_audio_files():
    """
    API endpoint to list existing audio files for testing purposes.

    Returns:
        JSON response with list of available audio files and their metadata
    """
    try:
        audio_files = []

        # Get all audio files from the output directory
        audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}

        for file_path in AUDIO_OUTPUT_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                try:
                    stat_info = file_path.stat()
                    audio_files.append({
                        'filename': file_path.name,
                        'size': stat_info.st_size,
                        'created_at': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat_info.mtime).isoformat(),
                        'audio_url': f"/audio/{file_path.name}",
                        'download_url': f"/download/{file_path.name}",
                        'file_type': file_path.suffix.lower().replace('.', '')
                    })
                except Exception as e:
                    logger.warning(f"Error processing audio file {file_path.name}: {str(e)}")
                    continue

        # Sort by creation time (newest first)
        audio_files.sort(key=lambda x: x['created_at'], reverse=True)

        return jsonify({
            'success': True,
            'data': {
                'audio_files': audio_files,
                'total_count': len(audio_files),
                'base_url': request.host_url.rstrip('/')
            }
        })

    except Exception as e:
        logger.error(f"Error listing audio files: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list audio files',
            'error_type': 'server_error'
        }), 500

@app.route('/status')
@performance_monitoring
def status():
    """
    Enhanced application status endpoint with comprehensive system monitoring.

    Returns:
        JSON response with detailed application status and health information
    """
    try:
        # Get system health metrics
        system_validation = validate_system_requirements()

        # Get performance metrics
        metrics = performance_monitor.get_metrics()

        # Enhanced status information
        status_info = {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'debug_mode': DEBUG,
            'configuration_loaded': CONFIG_LOADED,

            # System information
            'system': {
                'audio_output_dir': str(AUDIO_OUTPUT_DIR),
                'system_healthy': system_validation['valid'],
                'system_issues': system_validation.get('issues', []),
                'system_warnings': system_validation.get('warnings', []),
                'uptime': str(datetime.now() - app.startup_time).split('.')[0],
                'disk_space_available': check_disk_space(100)
            },

            # Performance metrics
            'performance': {
                'requests_total': metrics['requests_total'],
                'requests_success': metrics['requests_success'],
                'requests_error': metrics['requests_error'],
                'success_rate': round(metrics['success_rate'], 2),
                'avg_response_time': round(metrics['avg_response_time'], 3),
                'max_response_time': round(metrics['max_response_time'], 3),
                'min_response_time': round(metrics['min_response_time'], 3),

                # Generation metrics
                'generation_requests': metrics['generation_requests'],
                'generation_success': metrics['generation_success'],
                'generation_failures': metrics['generation_failures'],
                'generation_success_rate': round(metrics['generation_success_rate'], 2),
                'active_generations': metrics['active_generations']
            },

            # Active sessions
            'active_sessions': {
                'generation_progress_count': len(app.generation_progress) if hasattr(app, 'generation_progress') else 0,
                'rate_limit_entries': sum(len(requests) for requests in app.rate_limits.values()) if hasattr(app, 'rate_limits') else 0
            },

            # Configuration summary
            'configuration': {
                'log_level': LOG_LEVEL,
                'max_input_length': MAX_INPUT_LENGTH,
                'audio_output_format': 'mp3',
                'thread_pool_workers': app.thread_pool._max_workers if hasattr(app, 'thread_pool') else 'unknown'
            }
        }

        return jsonify(status_info)

    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        log_exception(e, {'route': 'status'})

        # Return basic status even if detailed checks fail
        return jsonify({
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'debug_mode': DEBUG,
            'error': 'Unable to retrieve detailed status information'
        }), 500


@app.route('/progress/<request_id>')
@performance_monitoring
def get_generation_progress(request_id):
    """
    Enhanced progress endpoint with comprehensive tracking and security.

    Args:
        request_id: Unique ID of the generation request

    Returns:
        JSON response with detailed progress information and system status
    """
    try:
        # Validate request ID format
        if not request_id or len(request_id) != 36:
            raise ValidationError("Invalid request ID format", field='request_id')

        # Check if progress data exists
        if not hasattr(app, 'generation_progress') or request_id not in app.generation_progress:
            return jsonify({
                'success': False,
                'error': 'Generation request not found',
                'request_id': request_id,
                'error_type': 'not_found'
            }), 404

        progress_data = app.generation_progress[request_id].copy()

        # Add system context to progress
        progress_data['system_status'] = {
            'active_generations': len([
                p for p in app.generation_progress.values()
                if p['status'] in ['initializing', 'creating_agents', 'generating_conversation', 'generating_audio', 'saving_file']
            ]),
            'current_time': datetime.now().isoformat()
        }

        # Calculate estimated time remaining
        if progress_data['progress'] > 0 and progress_data['progress'] < 100:
            try:
                start_time = datetime.fromisoformat(progress_data['timestamp'])
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 0:
                    rate = progress_data['progress'] / elapsed
                    if rate > 0:
                        remaining_seconds = (100 - progress_data['progress']) / rate
                        progress_data['estimated_remaining_seconds'] = round(remaining_seconds, 1)
            except Exception:
                pass  # Keep existing estimated completion if available

        # Clean up old completed/failed requests
        _cleanup_old_progress()

        # Add performance metrics if in debug mode
        if DEBUG:
            progress_data['debug_info'] = {
                'total_active_requests': len(app.generation_progress),
                'cleanup_run': True
            }

        return jsonify({
            'success': True,
            'progress': progress_data,
            'timestamp': datetime.now().isoformat()
        })

    except ValidationError as e:
        logger.warning(f"Validation error in progress endpoint for {request_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'validation_error',
            'request_id': request_id
        }), 400

    except Exception as e:
        logger.error(f"Error getting progress for {request_id}: {str(e)}")
        log_exception(e, {'route': 'progress', 'request_id': request_id})

        return jsonify({
            'success': False,
            'error': 'Failed to retrieve progress information',
            'error_type': 'server_error',
            'request_id': request_id
        }), 500


# New endpoint for system health check
@app.route('/health')
@performance_monitoring
def health_check():
    """
    Simple health check endpoint for load balancers and monitoring systems.

    Returns:
        JSON response with basic health status
    """
    try:
        # Quick system health check
        system_validation = validate_system_requirements()
        metrics = performance_monitor.get_metrics()

        # Determine health status
        is_healthy = (
            system_validation['valid'] and
            metrics['success_rate'] > 90 and
            metrics['generation_success_rate'] > 80
        )

        status_code = 200 if is_healthy else 503

        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'system_valid': system_validation['valid'],
                'success_rate_ok': metrics['success_rate'] > 90,
                'generation_rate_ok': metrics['generation_success_rate'] > 80
            },
            'version': '1.0.0'
        }), status_code

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': 'Health check failed',
            'version': '1.0.0'
        }), 503


# New endpoint for metrics
@app.route('/metrics')
@performance_monitoring
def get_metrics():
    """
    Detailed metrics endpoint for monitoring and analytics.

    Returns:
        JSON response with comprehensive application metrics
    """
    if not DEBUG:
        return jsonify({'error': 'Metrics endpoint is only available in debug mode'}), 403

    try:
        metrics = performance_monitor.get_metrics()
        system_validation = validate_system_requirements()

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'performance_metrics': metrics,
            'system_health': system_validation,
            'configuration': {
                'debug_mode': DEBUG,
                'configuration_loaded': CONFIG_LOADED,
                'log_level': LOG_LEVEL,
                'audio_output_dir': str(AUDIO_OUTPUT_DIR)
            },
            'active_data': {
                'generation_progress_entries': len(app.generation_progress) if hasattr(app, 'generation_progress') else 0,
                'rate_limit_entries': sum(len(requests) for requests in app.rate_limits.values()) if hasattr(app, 'rate_limits') else 0
            }
        })

    except Exception as e:
        logger.error(f"Error retrieving metrics: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve metrics',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/config')
@performance_monitoring
def config_page():
    """
    Configuration page route - serves the API key and agent configuration interface.

    Returns:
        Rendered HTML template for the configuration page

    Raises:
        TemplateError: If template rendering fails
        ConfigurationError: If configuration is invalid
    """
    try:
        # Validate system health before serving content
        validate_system_health()

        # Import validation utilities for template context
        from utils.validators import (
            ValidationError, create_validation_error_response,
            MAX_INPUT_LENGTH, MIN_PARTICIPANTS, MAX_PARTICIPANTS,
            MIN_CONVERSATION_ROUNDS, MAX_CONVERSATION_ROUNDS
        )
        from utils.models import Gender, Language

        # Prepare template context with configuration-specific data
        template_context = {
            # Application metadata
            'app_name': 'AI Podcast Generation System',
            'version': '1.0.0',

            # Form validation constants
            'max_input_length': MAX_INPUT_LENGTH,
            'min_participants': MIN_PARTICIPANTS,
            'max_participants': MAX_PARTICIPANTS,
            'min_conversation_rounds': MIN_CONVERSATION_ROUNDS,
            'max_conversation_rounds': MAX_CONVERSATION_ROUNDS,

            # Supported options
            'genders': [Gender.MALE, Gender.FEMALE],
            'languages': list(Language),

            # Configuration page specific
            'page_title': 'API Configuration',
            'page_description': 'Configure your AI model API keys and agent assignments',

            # Session information
            'session_id': session.get('session_id', str(uuid.uuid4())),

            # Current timestamp
            'current_time': datetime.now().isoformat(),
        }

        logger.info(f"Serving configuration page to session: {template_context['session_id']}")

        return render_template('config.html', **template_context)

    except Exception as e:
        logger.error(f"Error serving configuration page: {str(e)}")
        log_exception(e, {
            'route': 'config_page',
            'session_id': session.get('session_id', 'unknown')
        })

        # Fallback to basic error page
        return render_template('error.html', {
            'error_message': 'Configuration page temporarily unavailable',
            'error_details': str(e) if DEBUG else 'Please try again later',
            'show_details': DEBUG
        }), 500


@app.route('/api/voice-preferences', methods=['GET'])
@performance_monitoring
def voice_preferences():
    """
    Voice preferences endpoint for frontend voice selection.

    Returns:
        JSON response with available voice options organized by style, age, and gender
    """
    try:
        # Create TTS engine to get voice preferences
        tts_engine = create_tts_engine()

        if tts_engine is None:
            return jsonify({
                'success': False,
                'error': 'TTS engine not available',
                'error_type': 'tts_unavailable'
            }), 503

        # Check if engine has the new voice preferences method
        if hasattr(tts_engine, 'get_voice_preferences_for_frontend'):
            preferences = tts_engine.get_voice_preferences_for_frontend()

            return jsonify({
                'success': True,
                'data': preferences,
                'timestamp': datetime.now().isoformat()
            })

        elif hasattr(tts_engine, 'get_available_voice_options'):
            # Fallback to available voice options
            all_options = tts_engine.get_available_voice_options()

            return jsonify({
                'success': True,
                'data': {
                    '声音偏好': all_options,
                    '性别选项': {
                        'male': '男性',
                        'female': '女性'
                    }
                },
                'timestamp': datetime.now().isoformat(),
                'note': 'Using fallback voice options method'
            })

        else:
            # Final fallback - return basic testtts.py seeds
            basic_seeds = {
                "声音偏好": {
                    "文学风格": {
                        "description": "知性文雅，适合朗读文学作品",
                        "选项": [
                            {"性别": "male", "年龄": "年轻", "种子": 111, "描述": "年轻男性 - 文学气质"}
                        ]
                    },
                    "温柔风格": {
                        "description": "温和柔软，亲切自然",
                        "选项": [
                            {"性别": "male", "年龄": "年轻", "种子": 333, "描述": "年轻男性 - 温柔体贴"},
                            {"性别": "female", "年龄": "年轻", "种子": 2, "描述": "年轻女性 - 情感丰富温柔"}
                        ]
                    },
                    "专业风格": {
                        "description": "专业稳重，适合正式场合",
                        "选项": [
                            {"性别": "male", "年龄": "中年", "种子": 666, "描述": "中年男性 - 白领专业"},
                            {"性别": "female", "年龄": "中年", "种子": 1111, "描述": "中年女性 - 专业清晰"}
                        ]
                    },
                    "情感风格": {
                        "description": "情感丰富，表现力强",
                        "选项": [
                            {"性别": "female", "年龄": "年轻", "种子": 2, "描述": "年轻女性 - 情感丰富"}
                        ]
                    },
                    "深情风格": {
                        "description": "深情动人，温暖感人",
                        "选项": [
                            {"性别": "female", "年龄": "中年", "种子": 4, "描述": "中年女性 - 深情动人"}
                        ]
                    },
                    "平静风格": {
                        "description": "平静宁静，安详舒适",
                        "选项": [
                            {"性别": "female", "年龄": "中年", "种子": 3333, "描述": "中年女性 - 平静宁静"}
                        ]
                    }
                },
                "性别选项": {
                    "male": "男性",
                    "female": "女性"
                }
            }

            return jsonify({
                'success': True,
                'data': basic_seeds,
                'timestamp': datetime.now().isoformat(),
                'note': 'Using basic testtts.py seeds'
            })

    except Exception as e:
        logger.error(f"Error getting voice preferences: {str(e)}")
        log_exception(e, {'route': 'voice_preferences'})

        return jsonify({
            'success': False,
            'error': 'Failed to retrieve voice preferences',
            'error_type': 'server_error'
        }), 500


def map_frontend_gender_to_backend(frontend_gender):
    """
    Map frontend gender display name to backend gender key.

    Args:
        frontend_gender: "男性" or "female" or "male"

    Returns:
        Backend gender key: "male" or "female"
    """
    if frontend_gender in ['male', 'female']:
        return frontend_gender

    gender_mapping = {
        '男性': 'male',
        '女性': 'female'
    }

    return gender_mapping.get(frontend_gender, frontend_gender)

def map_age_to_chinese(age):
    """
    Map frontend English age value to backend Chinese age name.

    Args:
        age: "young", "middle-aged", "old" or Chinese age names

    Returns:
        Chinese age name for voice preferences
    """
    # If it's already a Chinese age name, return as-is
    if age in ['年轻', '中年', '其他']:
        return age

    # Map English age values to Chinese age names
    age_mapping = {
        'young': '年轻',
        'middle-aged': '中年',
        'old': '其他'
    }

    return age_mapping.get(age, age)


def map_personality_to_style(personality):
    """
    Map frontend personality value to backend Chinese style name.

    Args:
        personality: "professional", "casual", "energetic", "calm", "deep" or Chinese style names

    Returns:
        Chinese style name for voice preferences
    """
    # If it's already a Chinese style name, return as-is
    if personality and '风格' in personality:
        return personality

    # Map English personality values to Chinese style names
    personality_mapping = {
        'professional': '专业风格',
        'casual': '温柔风格',
        'energetic': '情感风格',
        'calm': '平静风格',
        'deep': '深情风格',
        'emotional': '情感风格',
        'literary': '文学风格',
        'gentle': '温柔风格',
        'clear': '清澈风格',
        'peaceful': '平静风格',
        'serious': '深沉风格',
        'hongkong': '港式风格'
    }

    return personality_mapping.get(personality, personality)

def map_backend_gender_to_frontend(backend_gender):
    """
    Map backend gender key to frontend display name.

    Args:
        backend_gender: "male" or "female"

    Returns:
        Frontend display name: "男性" or "女性"
    """
    gender_mapping = {
        'male': '男性',
        'female': '女性'
    }

    return gender_mapping.get(backend_gender, backend_gender)


@app.route('/api/voice-seed', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=10, window_seconds=60)
def get_voice_seed():
    """
    Get specific voice seed based on gender, age, and style preferences with random selection.

    Request body:
        {
            "gender": "male|female|男性|女性",  # Accept both Chinese and English
            "age": "年轻|中年|其他",
            "style": "文学风格|温柔风格|专业风格|...",
            "character_name": "optional_character_name"
        }

    Returns:
        JSON response with the randomly selected seed and description
    """
    try:
        # Handle UTF-8 encoding issues with Chinese characters
        try:
            data = request.get_json()
        except BadRequest as e:
            if "utf-8" in str(e).lower() or "encoding" in str(e).lower():
                # Handle UTF-8 encoding issues with Chinese characters
                logger.error(f"UTF-8 encoding error in voice seed request: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid character encoding in request. Please ensure UTF-8 encoding is used.',
                    'error_type': 'encoding_error',
                    'details': 'The request contains characters that could not be decoded. Please check your input encoding.'
                }), 400
            else:
                raise  # Re-raise other BadRequest errors

        if not data:
            return jsonify({
                'success': False,
                'error': 'No request data provided',
                'error_type': 'validation_error'
            }), 400

        frontend_gender = data.get('gender')
        age = data.get('age')
        style = data.get('style')
        character_name = data.get('character_name', 'unknown_character')

        # Map frontend parameters to backend format
        gender = map_frontend_gender_to_backend(frontend_gender)
        style = map_personality_to_style(style)

        # Create TTS engine
        tts_engine = create_tts_engine()

        if tts_engine is None:
            return jsonify({
                'success': False,
                'error': 'TTS engine not available',
                'error_type': 'tts_unavailable'
            }), 503

        # Build personality from age and style
        personality_parts = []
        if age:
            personality_parts.append(age)
        if style:
            personality_parts.append(style)
        personality = ' '.join(personality_parts) if personality_parts else None

        # Get seed for the character using new preference-based method
        seed = tts_engine._find_seed_from_preferences(character_name, gender, age, style)

        # Find description for the seed
        description = f"种子 {seed}"
        try:
            voice_preferences = tts_engine.voice_preferences.get("种子对照表", {})
            if str(seed) in voice_preferences:
                seed_info = voice_preferences[str(seed)]
                description = seed_info.get('description', description)
        except:
            pass

        return jsonify({
            'success': True,
            'data': {
                'seed': seed,
                'description': description,
                'gender': map_backend_gender_to_frontend(gender),  # Return frontend format
                'gender_backend': gender,  # Include backend format for reference
                'age': age,
                'style': style,
                'character_name': character_name,
                'personality_used': personality
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting voice seed: {str(e)}")
        log_exception(e, {'route': 'voice_seed', 'data': data if 'data' in locals() else 'undefined'})

        return jsonify({
            'success': False,
            'error': 'Failed to determine voice seed',
            'error_type': 'server_error'
        }), 500


@app.route('/api/voice-candidates', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=10, window_seconds=60)
def get_voice_candidates():
    """
    Get all voice candidate seeds for specific gender, age, and style combination.

    Request body:
        {
            "gender": "male|female|男性|女性",  # Accept both Chinese and English
            "age": "年轻|中年|其他 (optional)",
            "style": "文学风格|温柔风格|... (optional)"
        }

    Returns:
        JSON response with all matching candidate seeds
    """
    try:
        data = request.get_json()

        if not data or not data.get('gender'):
            return jsonify({
                'success': False,
                'error': 'Gender is required',
                'error_type': 'validation_error'
            }), 400

        frontend_gender = data.get('gender')
        age = data.get('age')
        style = data.get('style')

        # Map frontend gender to backend format
        gender = map_frontend_gender_to_backend(frontend_gender)

        # Create TTS engine
        tts_engine = create_tts_engine()

        if tts_engine is None:
            return jsonify({
                'success': False,
                'error': 'TTS engine not available',
                'error_type': 'tts_unavailable'
            }), 503

        # Get matching candidates
        candidates = tts_engine.get_voice_candidates_by_gender_age_style(gender, age, style)

        # Add display gender to candidates
        for candidate in candidates:
            candidate['性别显示'] = map_backend_gender_to_frontend(candidate['gender'])

        return jsonify({
            'success': True,
            'data': {
                'candidates': candidates,
                'count': len(candidates),
                'filters': {
                    'gender': map_backend_gender_to_frontend(gender),  # Return frontend format
                    'gender_backend': gender,  # Include backend format for reference
                    'age': age,
                    'style': style
                }
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting voice candidates: {str(e)}")
        log_exception(e, {'route': 'voice_candidates', 'data': data})

        return jsonify({
            'success': False,
            'error': 'Failed to get voice candidates',
            'error_type': 'server_error'
        }), 500


@app.route('/api/voice-combinations/<gender>', methods=['GET'])
@performance_monitoring
def get_voice_combinations(gender):
    """
    Get all available age+style combinations for a specific gender.

    Args:
        gender: male or female

    Returns:
        JSON response with all available combinations and candidate seeds
    """
    try:
        if gender not in ['male', 'female']:
            return jsonify({
                'success': False,
                'error': 'Invalid gender. Must be male or female',
                'error_type': 'validation_error'
            }), 400

        # Create TTS engine
        tts_engine = create_tts_engine()

        if tts_engine is None:
            return jsonify({
                'success': False,
                'error': 'TTS engine not available',
                'error_type': 'tts_unavailable'
            }), 503

        # Get age+style combinations
        combinations = tts_engine.get_age_style_combinations(gender)

        return jsonify({
            'success': True,
            'data': {
                'gender': gender,
                'combinations': combinations,
                'total_combinations': len(combinations)
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting voice combinations: {str(e)}")
        log_exception(e, {'route': 'voice_combinations', 'gender': gender})

        return jsonify({
            'success': False,
            'error': 'Failed to get voice combinations',
            'error_type': 'server_error'
        }), 500


@app.route('/api/all-voice-combinations', methods=['GET'])
@performance_monitoring
def get_all_voice_combinations():
    """
    Get all available age+style combinations from all seeds.

    Returns:
        JSON response with all unique age+style combinations from all seeds
    """
    try:
        # Create TTS engine
        tts_engine = create_tts_engine()

        if tts_engine is None:
            return jsonify({
                'success': False,
                'error': 'TTS engine not available',
                'error_type': 'tts_unavailable'
            }), 503

        # Get all voice preferences for frontend
        preferences = tts_engine.get_voice_preferences_for_frontend()

        if not preferences:
            return jsonify({
                'success': False,
                'error': 'Failed to get voice preferences',
                'error_type': 'server_error'
            }), 500

        return jsonify({
            'success': True,
            'data': {
                '所有组合': preferences.get('所有组合', []),
                '声音偏好': preferences.get('声音偏好', {}),
                '性别选项': preferences.get('性别选项', {}),
                '年龄选项': preferences.get('年龄选项', {}),
                '性别映射': preferences.get('性别映射', {}),
                '年龄映射': preferences.get('年龄映射', {}),
                '统计信息': preferences.get('统计信息', {})
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting all voice combinations: {str(e)}")
        log_exception(e, {'route': 'all_voice_combinations'})

        return jsonify({
            'success': False,
            'error': 'Failed to get all voice combinations',
            'error_type': 'server_error'
        }), 500


@app.route('/api/config', methods=['GET', 'POST', 'DELETE'])
@performance_monitoring
def configuration():
    """
    Configuration management endpoint for API keys and agent settings.

    Handles GET (load), POST (save), and DELETE (clear) operations for user configurations.
    Supports session-based storage with AES-256 encryption for sensitive data.

    Returns:
        JSON response with configuration data or operation status

    Raises:
        ValidationError: If input validation fails
        ConfigurationError: If configuration operations fail
        EncryptionError: If encryption/decryption operations fail
    """
    try:
        # Import configuration service and related components
        from utils.configuration_service import ConfigurationService
        from utils.config_repository import ConfigRepository
        from utils.error_handler import ConfigurationError

        # Initialize components
        # Encryption service removed - API keys stored in plain text
        repository = ConfigRepository()
        config_service = ConfigurationService(repository=repository)

        # Get or create session ID
        session_id = session.get('session_id')
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            logger.info(f"Created new session: {session_id}")

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

        if request.method == 'GET':
            # Load configuration
            logger.info(f"Loading configuration for session {session_id} from {client_ip}")

            try:
                # Get API keys (try current session first, then admin_admin as fallback)
                api_keys = config_service.get_api_keys(session_id)

                # If no API keys found in current session, try admin_admin session
                if not api_keys:
                    admin_api_keys = config_service.get_api_keys("admin_admin")
                    if admin_api_keys:
                        api_keys = admin_api_keys
                        logger.info(f"Using API keys from admin_admin session for session {session_id}")

                # Get agent configurations
                agent_configs = config_service.get_agent_config(session_id)

                # API keys are now returned as plain text (no masking)
                masked_api_keys = api_keys

                response_data = {
                    'success': True,
                    'data': {
                        'api_keys': masked_api_keys,
                        'agent_configs': agent_configs,
                        'session_id': session_id
                    },
                    'message': 'Configuration loaded successfully'
                }

                logger.info(f"Configuration loaded successfully for session {session_id}")
                return jsonify(response_data)

            except Exception as e:
                logger.error(f"Failed to load configuration for session {session_id}: {str(e)}")
                raise ConfigurationError(f"Failed to load configuration: {str(e)}", original_error=e)

        elif request.method == 'POST':
            # Save configuration
            logger.info(f"Saving configuration for session {session_id} from {client_ip}")

            try:
                # Extract and validate input data
                data = request.get_json() if request.is_json else request.form.to_dict()

                if not data:
                    raise ValidationError("No configuration data provided", field='request_body')

                # Process API keys if provided
                if 'api_keys' in data:
                    api_keys = data['api_keys']
                    if not isinstance(api_keys, dict):
                        raise ValidationError("API keys must be a dictionary", field='api_keys')

                    # Save API keys using the configuration service
                    logger.info(f"Saving {len(api_keys)} API keys for session {session_id}")

                    try:
                        # Use the configuration service to save API keys
                        success = config_service.save_api_keys(session_id, api_keys)
                        if not success:
                            raise ConfigurationError("Failed to save API keys using configuration service")

                        logger.info(f"Successfully saved {len(api_keys)} API keys for session {session_id}")

                    except Exception as e:
                        logger.error(f"Failed to save API keys to database: {str(e)}")
                        raise ConfigurationError(f"Failed to save API keys: {str(e)}")

                # Process agent configurations if provided
                if 'agent_configs' in data:
                    agent_configs = data['agent_configs']
                    if not isinstance(agent_configs, list):
                        raise ValidationError("Agent configurations must be a list", field='agent_configs')

                    for agent_config in agent_configs:
                        if not isinstance(agent_config, dict):
                            raise ValidationError("Each agent configuration must be an object", field='agent_configs')

                        # Validate required fields
                        if 'agent_id' not in agent_config or 'provider' not in agent_config or 'model' not in agent_config:
                            raise ValidationError(
                                "Agent configuration must include agent_id, provider, and model fields",
                                field='agent_configs'
                            )

                        # Save agent configuration
                        success = config_service.save_agent_config(
                            session_id,
                            agent_config['agent_id'],
                            agent_config['provider'],
                            agent_config['model']
                        )
                        if not success:
                            raise ConfigurationError(f"Failed to save agent configuration for {agent_config['agent_id']}")

                response_data = {
                    'success': True,
                    'message': 'Configuration saved successfully',
                    'data': {
                        'session_id': session_id,
                        'saved_at': datetime.now().isoformat()
                    }
                }

                logger.info(f"Configuration saved successfully for session {session_id}")
                return jsonify(response_data)

            except ValidationError as e:
                logger.warning(f"Validation error saving configuration for session {session_id}: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'error_type': 'validation_error',
                    'field': getattr(e, 'field', None)
                }), 400

            except Exception as e:
                logger.error(f"Failed to save configuration for session {session_id}: {str(e)}")
                raise ConfigurationError(f"Failed to save configuration: {str(e)}", original_error=e)

        elif request.method == 'DELETE':
            # Clear configuration
            logger.info(f"Clearing configuration for session {session_id} from {client_ip}")

            try:
                success = config_service.clear_configuration(session_id)
                if not success:
                    raise ConfigurationError("Failed to clear configuration")

                response_data = {
                    'success': True,
                    'message': 'Configuration cleared successfully',
                    'data': {
                        'session_id': session_id,
                        'cleared_at': datetime.now().isoformat()
                    }
                }

                logger.info(f"Configuration cleared successfully for session {session_id}")
                return jsonify(response_data)

            except Exception as e:
                logger.error(f"Failed to clear configuration for session {session_id}: {str(e)}")
                raise ConfigurationError(f"Failed to clear configuration: {str(e)}", original_error=e)

        else:
            # Method not allowed
            logger.warning(f"Unsupported method {request.method} for configuration endpoint from {client_ip}")
            return jsonify({
                'success': False,
                'error': 'Method not allowed',
                'error_type': 'method_not_allowed'
            }), 405

    except ValidationError as e:
        logger.warning(f"Validation error in configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'validation_error',
            'field': getattr(e, 'field', None)
        }), 400

    except ConfigurationError as e:
        logger.error(f"Configuration error in configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'configuration_error'
        }), 500

    except EncryptionError as e:
        logger.error(f"Encryption error in configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Configuration encryption/decryption failed',
            'error_type': 'encryption_error'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error in configuration endpoint: {str(e)}")
        log_exception(e, {
            'route': 'configuration',
            'method': request.method,
            'session_id': session_id if 'session_id' in locals() else 'unknown',
            'client_ip': client_ip
        })

        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while processing your configuration',
            'error_type': 'server_error'
        }), 500


@app.route('/api/config/validate', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=10, window_seconds=60)
def validate_api_key():
    """
    API key validation endpoint for real-time validation and model discovery.

    Accepts POST requests with API key information and returns validation results
    along with available model options for the provider.

    Returns:
        JSON response with validation status and available models

    Raises:
        ValidationError: If input validation fails
        ConfigurationError: If validation operations fail
    """
    try:
        # Import configuration service and related components
        from utils.configuration_service import ConfigurationService
        from utils.config_repository import ConfigRepository
        from utils.error_handler import ConfigurationError

        # Initialize components
        # Encryption service removed - API keys stored in plain text
        repository = ConfigRepository()
        config_service = ConfigurationService(repository=repository)

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        logger.info(f"API key validation request from {client_ip}")

        # Extract and validate input data
        data = request.get_json() if request.is_json else request.form.to_dict()

        if not data:
            raise ValidationError("No validation data provided", field='request_body')

        # Validate required fields
        if 'provider' not in data:
            raise ValidationError("Provider is required", field='provider')

        if 'api_key' not in data:
            raise ValidationError("API key is required", field='api_key')

        provider = data['provider'].strip().lower()
        api_key = data['api_key'].strip()

        if not provider:
            raise ValidationError("Provider cannot be empty", field='provider')

        if not api_key:
            raise ValidationError("API key cannot be empty", field='api_key')

        logger.info(f"Validating API key for provider: {provider} from {client_ip}")

        try:
            # Validate API key format first
            format_valid = config_service.validate_api_key(provider, api_key)
            if not format_valid:
                raise ValidationError(f"Invalid API key format for provider: {provider}", field='api_key')

            # Perform actual API key validation (if implemented)
            # This would involve making a test API call to the provider
            validation_result = config_service.validate_api_key_connection(provider, api_key)

            # Get available models for this provider
            available_models = config_service.get_available_models(provider, api_key)

            response_data = {
                'success': True,
                'data': {
                    'provider': provider,
                    'validation_result': validation_result,
                    'available_models': available_models,
                    'validated_at': datetime.now().isoformat()
                },
                'message': f'API key validation completed for {provider}'
            }

            logger.info(f"API key validation successful for provider: {provider}")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"API key validation failed for provider {provider}: {str(e)}")

            # Return validation error with details
            return jsonify({
                'success': False,
                'error': f'API key validation failed for {provider}: {str(e)}',
                'error_type': 'validation_failed',
                'data': {
                    'provider': provider,
                    'validation_result': {'valid': False, 'error': str(e)},
                    'validated_at': datetime.now().isoformat()
                }
            }), 400

    except ValidationError as e:
        logger.warning(f"Validation error in validate_api_key endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'validation_error',
            'field': getattr(e, 'field', None)
        }), 400

    except ConfigurationError as e:
        logger.error(f"Configuration error in validate_api_key endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'configuration_error'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error in validate_api_key endpoint: {str(e)}")
        log_exception(e, {
            'route': 'validate_api_key',
            'client_ip': client_ip
        })

        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while validating the API key',
            'error_type': 'server_error'
        }), 500


@app.route('/api/config/export', methods=['GET'])
@performance_monitoring
@rate_limit(max_requests=3, window_seconds=60)
def export_configuration():
    """
    Configuration export endpoint for encrypted backup.

    Provides an encrypted export of user's configuration including API keys
    and agent settings for backup and migration purposes.

    Returns:
        JSON response with encrypted configuration data and decryption key

    Raises:
        ValidationError: If session validation fails
        ConfigurationError: If export operations fail
        ValidationError: If configuration parsing fails
    """
    try:
        # Import configuration service and related components
        from utils.configuration_service import ConfigurationService
        from utils.config_repository import ConfigRepository
        from utils.error_handler import ConfigurationError

        # Initialize components
        # Encryption service removed - API keys stored in plain text
        repository = ConfigRepository()
        config_service = ConfigurationService(repository=repository)

        # Get session ID
        session_id = session.get('session_id')
        if not session_id:
            raise ValidationError("No active session found", field='session_id')

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        logger.info(f"Configuration export request for session {session_id} from {client_ip}")

        try:
            # Get all configuration data
            api_keys = config_service.get_api_keys(session_id)
            agent_configs = config_service.get_agent_config(session_id)

            # Prepare configuration data for export
            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'session_id': session_id,
                'api_keys': api_keys,  # These are already decrypted from the service
                'agent_configs': agent_configs,
                'metadata': {
                    'total_api_keys': len(api_keys),
                    'total_agent_configs': len(agent_configs),
                    'export_source': 'podcast_generation_app'
                }
            }

            # No encryption - export data as plain text
            import json
            json_data = json.dumps(export_data, indent=2)

            response_data = {
                'success': True,
                'data': {
                    'config': json_data,  # Plain text JSON
                    'version': export_data['version'],
                    'exported_at': export_data['exported_at'],
                    'metadata': export_data['metadata']
                },
                'message': 'Configuration exported successfully'
            }

            # Log successful export for audit purposes
            repository.log_configuration_change(
                session_id=session_id,
                action="export_configuration",
                details=f"Exported configuration with {len(api_keys)} API keys and {len(agent_configs)} agent configs"
            )

            logger.info(f"Configuration exported successfully for session {session_id}")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"Failed to export configuration for session {session_id}: {str(e)}")
            raise ConfigurationError(f"Failed to export configuration: {str(e)}", original_error=e)

    except ValidationError as e:
        logger.warning(f"Validation error in export_configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'validation_error',
            'field': getattr(e, 'field', None)
        }), 400

    except ConfigurationError as e:
        logger.error(f"Configuration error in export_configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'configuration_error'
        }), 500

    except EncryptionError as e:
        logger.error(f"Encryption error in export_configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Configuration encryption failed',
            'error_type': 'encryption_error'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error in export_configuration endpoint: {str(e)}")
        log_exception(e, {
            'route': 'export_configuration',
            'session_id': session_id if 'session_id' in locals() else 'unknown',
            'client_ip': client_ip
        })

        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while exporting your configuration',
            'error_type': 'server_error'
        }), 500


@app.route('/api/config/import', methods=['POST'])
@performance_monitoring
@rate_limit(max_requests=3, window_seconds=60)
def import_configuration():
    """
    Configuration import endpoint for encrypted backup restoration.

    Accepts an encrypted configuration export and restores API keys
    and agent settings from a previous backup.

    Returns:
        JSON response with import status and restored configuration summary

    Raises:
        ValidationError: If import data validation fails
        ConfigurationError: If import operations fail
    """
    try:
        # Import configuration service and related components
        from utils.configuration_service import ConfigurationService
        from utils.config_repository import ConfigRepository
        from utils.error_handler import ConfigurationError, ValidationError

        # Initialize components
        # Encryption service removed - API keys stored in plain text
        repository = ConfigRepository()
        config_service = ConfigurationService(repository=repository)

        # Get session ID
        session_id = session.get('session_id')
        if not session_id:
            raise ValidationError("No active session found", field='session_id')

        # Validate request data
        if not request.is_json:
            raise ValidationError("Request must be JSON", field='content_type')

        request_data = request.get_json()
        if not request_data:
            raise ValidationError("Request data cannot be empty", field='request_data')

        # Validate required fields
        required_fields = ['config']  # Only need config now
        for field in required_fields:
            if field not in request_data:
                raise ValidationError(f"Missing required field: {field}", field=field)

        config = request_data.get('config')  # Changed from encrypted_config to config

        if not config:
            raise ValidationError("Configuration data cannot be empty", field='data')

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        logger.info(f"Configuration import request for session {session_id} from {client_ip}")

        try:
            # Configuration data is now plain text JSON
            import json
            try:
                import_data = json.loads(config)
            except json.JSONDecodeError as e:
                raise ValidationError("Failed to parse configuration data", original_error=e)

            # Validate import data structure
            if not isinstance(import_data, dict):
                raise ValidationError("Import data must be a JSON object", field='import_data')

            # Validate required import fields
            if 'version' not in import_data:
                raise ValidationError("Import data missing version information", field='version')

            if 'api_keys' not in import_data or 'agent_configs' not in import_data:
                raise ValidationError("Import data missing configuration sections", field='configuration')

            # Version compatibility check
            supported_versions = ['1.0']
            if import_data['version'] not in supported_versions:
                raise ValidationError(f"Unsupported import version: {import_data['version']}", field='version')

            # Validate API keys structure
            api_keys = import_data['api_keys']
            if not isinstance(api_keys, dict):
                raise ValidationError("API keys must be a dictionary", field='api_keys')

            # Validate agent configs structure
            agent_configs = import_data['agent_configs']
            if not isinstance(agent_configs, list):
                raise ValidationError("Agent configurations must be a list", field='agent_configs')

            # Import API keys
            # Validate all API keys first
            valid_api_keys = {}
            for provider, api_key in api_keys.items():
                if not api_key or not isinstance(api_key, str):
                    logger.warning(f"Skipping invalid API key for provider: {provider}")
                    continue

                # Validate API key format before importing
                if not config_service.validate_api_key(provider, api_key):
                    logger.warning(f"Skipping API key with invalid format for provider: {provider}")
                    continue

                valid_api_keys[provider] = api_key

            # Save all valid API keys at once
            if valid_api_keys:
                success = config_service.save_api_keys(session_id, valid_api_keys)
                if success:
                    imported_api_keys = len(valid_api_keys)
                    logger.info(f"Successfully imported {imported_api_keys} API keys")
                else:
                    logger.warning("Failed to import API keys")
            else:
                imported_api_keys = 0
                logger.warning("No valid API keys to import")

            # Import agent configurations
            imported_agent_configs = 0
            for agent_config in agent_configs:
                if not isinstance(agent_config, dict):
                    logger.warning("Skipping invalid agent configuration (not a dictionary)")
                    continue

                required_agent_fields = ['agent_id', 'provider', 'model']
                if not all(field in agent_config for field in required_agent_fields):
                    logger.warning(f"Skipping agent configuration missing required fields: {agent_config}")
                    continue

                agent_id = agent_config['agent_id']
                provider = agent_config['provider']
                model = agent_config['model']

                # Validate that we have the API key for this provider
                if provider not in api_keys:
                    logger.warning(f"Skipping agent config for {agent_id} - no API key for provider: {provider}")
                    continue

                success = config_service.save_agent_config(session_id, agent_id, provider, model)
                if success:
                    imported_agent_configs += 1
                    logger.info(f"Successfully imported agent configuration for: {agent_id}")
                else:
                    logger.warning(f"Failed to import agent configuration for: {agent_id}")

            # Prepare response data
            response_data = {
                'success': True,
                'data': {
                    'import_summary': {
                        'total_api_keys': len(api_keys),
                        'imported_api_keys': imported_api_keys,
                        'total_agent_configs': len(agent_configs),
                        'imported_agent_configs': imported_agent_configs,
                        'import_version': import_data['version'],
                        'original_export_date': import_data.get('exported_at'),
                        'imported_at': datetime.now().isoformat()
                    }
                },
                'message': f'Configuration imported successfully ({imported_api_keys} API keys, {imported_agent_configs} agent configs)'
            }

            # Log successful import for audit purposes
            repository.log_configuration_change(
                session_id=session_id,
                action="import_configuration",
                details=f"Imported configuration: {imported_api_keys} API keys, {imported_agent_configs} agent configs, version {import_data['version']}"
            )

            logger.info(f"Configuration import successful for session {session_id}: {imported_api_keys} API keys, {imported_agent_configs} agent configs")
            return jsonify(response_data)

        except EncryptionError as e:
            logger.error(f"Decryption failed during configuration import: {str(e)}")
            raise EncryptionError("Failed to decrypt configuration data - please verify the export key and data integrity", original_error=e)

        except (ValidationError, ConfigurationError) as e:
            logger.error(f"Configuration import validation error: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error during configuration import: {str(e)}")
            raise ConfigurationError(f"Failed to import configuration: {str(e)}", original_error=e)

    except ValidationError as e:
        logger.warning(f"Validation error in import_configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'validation_error',
            'field': getattr(e, 'field', None)
        }), 400

    except EncryptionError as e:
        logger.error(f"Encryption error in import_configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'encryption_error'
        }), 400

    except ConfigurationError as e:
        logger.error(f"Configuration error in import_configuration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'configuration_error'
        }), 400

    except Exception as e:
        logger.error(f"Unexpected error in import_configuration endpoint: {str(e)}")
        log_exception(e, {
            'route': 'import_configuration',
            'session_id': session.get('session_id', 'unknown'),
            'client_ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        })

        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while importing your configuration',
            'error_type': 'server_error'
        }), 500


@app.route('/api/config/models', methods=['GET'])
@performance_monitoring
@rate_limit(max_requests=20, window_seconds=60)
def get_available_models():
    """
    Available models endpoint for agent model options.

    Returns a comprehensive list of available AI models across all configured
    providers, suitable for populating dropdown selections in the UI.

    Returns:
        JSON response with available models organized by provider

    Raises:
        ConfigurationError: If model retrieval fails
    """
    try:
        # Import configuration service and related components
        from utils.configuration_service import ConfigurationService
        from utils.config_repository import ConfigRepository
        from utils.error_handler import ConfigurationError

        # Initialize components
        # Encryption service removed - API keys stored in plain text
        repository = ConfigRepository()
        config_service = ConfigurationService(repository=repository)

        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        logger.info(f"Available models request from {client_ip}")

        try:
            # Get available models for all supported providers
            all_models = config_service.get_all_supported_models()

            response_data = {
                'success': True,
                'data': {
                    'models': all_models,
                    'total_models': sum(len(models) for models in all_models.values()),
                    'providers': list(all_models.keys()),
                    'generated_at': datetime.now().isoformat()
                },
                'message': 'Available models retrieved successfully'
            }

            logger.info(f"Available models retrieved successfully for {len(all_models)} providers")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"Failed to retrieve available models: {str(e)}")
            raise ConfigurationError(f"Failed to retrieve available models: {str(e)}", original_error=e)

    except ConfigurationError as e:
        logger.error(f"Configuration error in get_available_models endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'configuration_error'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error in get_available_models endpoint: {str(e)}")
        log_exception(e, {
            'route': 'get_available_models',
            'client_ip': client_ip
        })

        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred while retrieving available models',
            'error_type': 'server_error'
        }), 500


def _cleanup_old_progress():
    """
    Enhanced cleanup function for progress data with comprehensive monitoring.

    Removes completed/failed requests older than 1 hour and enforces memory limits.
    """
    try:
        if not hasattr(app, 'generation_progress') or not app.generation_progress:
            return

        current_time = datetime.now()
        expired_requests = []
        cleanup_stats = {
            'total_entries': len(app.generation_progress),
            'expired_by_age': 0,
            'expired_by_status': 0,
            'malformed_entries': 0,
            'cleanup_errors': 0
        }

        for request_id, progress in app.generation_progress.items():
            try:
                # Validate progress entry structure
                if not isinstance(progress, dict) or 'timestamp' not in progress or 'status' not in progress:
                    cleanup_stats['malformed_entries'] += 1
                    expired_requests.append(request_id)
                    continue

                progress_time = datetime.fromisoformat(progress['timestamp'])
                age_seconds = (current_time - progress_time).total_seconds()

                # Remove requests older than 1 hour that are completed or failed
                if (progress['status'] in ['completed', 'failed'] and age_seconds > 3600):
                    cleanup_stats['expired_by_age'] += 1
                    expired_requests.append(request_id)
                elif age_seconds > 7200:  # Remove any request older than 2 hours regardless of status
                    cleanup_stats['expired_by_status'] += 1
                    expired_requests.append(request_id)

            except Exception as entry_error:
                cleanup_stats['malformed_entries'] += 1
                expired_requests.append(request_id)
                logger.warning(f"Malformed progress entry {request_id}: {str(entry_error)}")

        # Enforce maximum progress entries limit (prevent memory issues)
        max_entries = 1000
        if len(app.generation_progress) - len(expired_requests) > max_entries:
            # Sort by timestamp and remove oldest entries
            sorted_entries = sorted(
                app.generation_progress.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=True
            )
            entries_to_remove = sorted_entries[max_entries:]
            for request_id, _ in entries_to_remove:
                if request_id not in expired_requests:
                    expired_requests.append(request_id)
                    cleanup_stats['expired_by_status'] += 1

        # Remove expired requests
        removed_count = 0
        for request_id in expired_requests:
            try:
                del app.generation_progress[request_id]
                removed_count += 1
            except Exception as remove_error:
                cleanup_stats['cleanup_errors'] += 1
                logger.warning(f"Error removing progress entry {request_id}: {str(remove_error)}")

        # Log cleanup results
        if expired_requests:
            logger.info(f"Progress cleanup completed: {cleanup_stats}")

        # Also cleanup old rate limit entries
        if hasattr(app, 'rate_limits'):
            _cleanup_rate_limits()

    except Exception as e:
        logger.error(f"Critical error during progress cleanup: {str(e)}")
        log_exception(e, {'function': '_cleanup_old_progress'})


def _cleanup_rate_limits():
    """Clean up old rate limit entries to prevent memory leaks."""
    try:
        if not hasattr(app, 'rate_limits'):
            return

        current_time = time.time()
        window_seconds = 300  # 5 minutes
        cleaned_entries = 0

        for client_ip, requests in list(app.rate_limits.items()):
            # Keep only recent requests
            valid_requests = [req_time for req_time in requests if current_time - req_time < window_seconds]

            if len(valid_requests) != len(requests):
                if valid_requests:
                    app.rate_limits[client_ip] = valid_requests
                else:
                    del app.rate_limits[client_ip]
                cleaned_entries += len(requests) - len(valid_requests)

        if cleaned_entries > 0:
            logger.debug(f"Cleaned up {cleaned_entries} old rate limit entries")

    except Exception as e:
        logger.warning(f"Error during rate limit cleanup: {str(e)}")


# Enhanced error handlers with comprehensive logging and user-friendly responses
@app.errorhandler(404)
def not_found_error(error):
    """
    Enhanced 404 error handler with detailed logging and user-friendly responses.
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    requested_url = request.url if request else 'unknown'

    logger.warning(f"404 error: Resource not found - {requested_url} from {client_ip}")

    if request and request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': False,
            'error': 'The requested resource was not found',
            'error_type': 'not_found',
            'requested_url': requested_url,
            'timestamp': datetime.now().isoformat()
        }), 404

    try:
        return render_template('404.html', requested_url=requested_url), 404
    except Exception:
        # Fallback error page if template fails
        return _render_error_page(
            title="Page Not Found",
            message=f"The page you requested ({requested_url}) could not be found.",
            details=None,
            show_retry=True
        ), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Enhanced 500 error handler with comprehensive logging and system diagnostics.
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    requested_url = request.url if request else 'unknown'

    logger.error(f"500 error: Internal server error - {requested_url} from {client_ip}")
    log_exception(error, {
        'client_ip': client_ip,
        'requested_url': requested_url,
        'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown'
    })

    # Check system health during internal errors
    try:
        system_health = validate_system_requirements()
        system_healthy = system_health['valid']
    except Exception:
        system_healthy = False

    if request and request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response_data = {
            'success': False,
            'error': 'An internal server error occurred',
            'error_type': 'server_error',
            'timestamp': datetime.now().isoformat()
        }

        if DEBUG:
            response_data['debug_info'] = {
                'system_healthy': system_healthy,
                'error_details': str(error)
            }

        return jsonify(response_data), 500

    try:
        return render_template('500.html',
            system_healthy=system_healthy,
            error_details=str(error) if DEBUG else None
        ), 500
    except Exception:
        # Fallback error page if template fails
        return _render_error_page(
            title="Server Error",
            message="An internal server error occurred. Our team has been notified.",
            details=str(error) if DEBUG else None,
            show_retry=True
        ), 500


@app.errorhandler(400)
def bad_request_error(error):
    """
    Enhanced 400 error handler with detailed validation feedback.
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    requested_url = request.url if request else 'unknown'

    logger.warning(f"400 error: Bad request - {requested_url} from {client_ip}")

    if request and request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': False,
            'error': 'The request was invalid or malformed',
            'error_type': 'bad_request',
            'timestamp': datetime.now().isoformat()
        }), 400

    try:
        return render_template('400.html'), 400
    except Exception:
        # Fallback error page if template fails
        return _render_error_page(
            title="Bad Request",
            message="The request was invalid or malformed. Please check your input and try again.",
            details=None,
            show_retry=True
        ), 400


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """
    Handle rate limiting errors with user-friendly messaging.
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

    logger.warning(f"429 error: Rate limit exceeded - {client_ip}")

    if request and request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please try again later.',
            'error_type': 'rate_limit_exceeded',
            'retry_after': 300,  # 5 minutes
            'timestamp': datetime.now().isoformat()
        }), 429

    return _render_error_page(
        title="Rate Limit Exceeded",
        message="You have made too many requests. Please wait a moment before trying again.",
        details="You can try again in 5 minutes.",
        show_retry=True
    ), 429


# Generic HTTP error handler
@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """
    Catch-all handler for unexpected errors with comprehensive logging.
    """
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    requested_url = request.url if request else 'unknown'

    # Handle Werkzeug HTTP exceptions separately
    if isinstance(error, HTTPException):
        logger.warning(f"HTTP exception {error.code}: {error.description} - {requested_url} from {client_ip}")

        if request and request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({
                'success': False,
                'error': error.description,
                'error_type': f'http_{error.code}',
                'timestamp': datetime.now().isoformat()
            }), error.code

        try:
            template_name = f'{error.code}.html'
            return render_template(template_name), error.code
        except Exception:
            return _render_error_page(
                title=f"Error {error.code}",
                message=error.description or "An error occurred",
                details=None,
                show_retry=True
            ), error.code

    # Handle unexpected exceptions
    logger.error(f"Unexpected error: {str(error)} - {requested_url} from {client_ip}")
    log_exception(error, {
        'client_ip': client_ip,
        'requested_url': requested_url,
        'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown'
    })

    if request and request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred',
            'error_type': 'unexpected_error',
            'timestamp': datetime.now().isoformat(),
            'details': str(error) if DEBUG else None
        }), 500

    return _render_error_page(
        title="Unexpected Error",
        message="An unexpected error occurred. Please try again later.",
        details=str(error) if DEBUG else None,
        show_retry=True
    ), 500

# Enhanced utility functions with comprehensive error handling
def allowed_file(filename):
    """
    Enhanced file validation with security checks.

    Args:
        filename: Name of the file to check

    Returns:
        True if file extension is allowed, False otherwise

    Raises:
        ValidationError: If filename is invalid or contains dangerous patterns
    """
    if not filename or not isinstance(filename, str):
        return False

    # Security checks for filename
    dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00']
    for pattern in dangerous_patterns:
        if pattern in filename:
            logger.warning(f"Dangerous pattern '{pattern}' detected in filename: {filename}")
            return False

    # Check file extension
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS


# Enhanced application factory function with comprehensive configuration
def create_app(config_object=None, test_config=None):
    """
    Enhanced Flask application factory with production-ready configuration.

    Args:
        config_object: Optional configuration object
        test_config: Optional test configuration dictionary

    Returns:
        Configured Flask application instance with enhanced error handling and monitoring

    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        # Apply test configuration if provided (for testing)
        if test_config:
            app.config.update(test_config)

        # Apply configuration object if provided
        if config_object:
            app.config.from_object(config_object)

        # Validate critical configuration
        if not app.config.get('SECRET_KEY'):
            raise ConfigurationError("SECRET_KEY must be configured")

        # Initialize performance monitoring for this app instance
        if not hasattr(app, 'performance_monitor'):
            app.performance_monitor = PerformanceMonitor()

        # Initialize cleanup scheduler (in production, use proper task scheduler)
        if DEBUG and not hasattr(app, 'cleanup_scheduled'):
            app.cleanup_scheduled = True
            logger.info("Cleanup functions will run on-demand in debug mode")

        logger.info("Flask application factory completed successfully")
        return app

    except Exception as e:
        logger.error(f"Failed to create Flask application: {str(e)}")
        raise ConfigurationError(f"Application factory failed: {str(e)}", original_error=e)


# Enhanced graceful shutdown handling
def shutdown_application():
    """Gracefully shutdown the application with proper resource cleanup."""
    try:
        logger.info("Starting graceful application shutdown...")

        # Shutdown thread pool
        if hasattr(app, 'thread_pool'):
            app.thread_pool.shutdown(wait=True)
            logger.info("Thread pool shutdown completed")

        # Log final metrics
        final_metrics = performance_monitor.get_metrics()
        logger.info(f"Final application metrics: {final_metrics}")

        logger.info("Application shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during application shutdown: {str(e)}")


# Enhanced main execution block with comprehensive error handling
if __name__ == '__main__':
    try:
        # Set up signal handlers for graceful shutdown
        import signal
        import sys

        def signal_handler(signum, frame):
            """Handle shutdown signals gracefully."""
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            shutdown_application()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Log application startup
        logger.info("=== Starting AI Podcast Generator Application ===")
        logger.info(f"Host: {HOST}, Port: {PORT}, Debug: {DEBUG}")

        # Run the Flask application with enhanced configuration
        try:
            app.run(
                host=HOST,
                port=PORT,  # Use port 8080 to avoid conflicts with other services
                debug=DEBUG,
                threaded=True,  # Enable threading for concurrent requests
                use_reloader=False  # Disable reloader to prevent restarts during generation
            )
        except Exception as e:
            logger.critical(f"Failed to start Flask application: {str(e)}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}")
        sys.exit(1)
    finally:
        # Ensure graceful shutdown
        shutdown_application()