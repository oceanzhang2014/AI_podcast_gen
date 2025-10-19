"""
File handler utilities for podcast generation system.

This module provides comprehensive file handling functionality including:
- Audio file creation and storage with standardized naming
- File cleanup and storage management
- File serving and download functionality
- Validation and error handling for file operations

Purpose: Manage audio file storage, access, and maintenance throughout the podcast generation system.
"""

import os
import shutil
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import re

# Import configuration and error handling
try:
    from config import (
        AUDIO_OUTPUT_DIR, AUDIO_FORMAT, MAX_FILE_AGE_DAYS,
        MAX_STORAGE_MB, ALLOWED_AUDIO_EXTENSIONS
    )
except (ValueError, ImportError):
    # Fallback defaults for testing/development
    AUDIO_OUTPUT_DIR = Path('generated_audio')
    AUDIO_FORMAT = 'mp3'
    MAX_FILE_AGE_DAYS = 7
    MAX_STORAGE_MB = 1000
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}

from .error_handler import (
    FileOperationError,
    get_logger,
    handle_errors,
    translate_exception,
    check_disk_space
)
from .models import PodcastResult


class FileHandler:
    """
    Handles audio file operations for the podcast generation system.

    Provides methods for saving, naming, cleaning up, and serving audio files
    with proper error handling and logging.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the file handler.

        Args:
            output_dir: Directory for audio file storage (defaults to config value)
        """
        self.output_dir = output_dir or AUDIO_OUTPUT_DIR
        self.logger = get_logger()

        # Ensure output directory exists
        self._ensure_output_directory()

    def _ensure_output_directory(self) -> None:
        """
        Create output directory if it doesn't exist.

        Raises:
            FileOperationError: If directory cannot be created
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Test write permissions
            test_file = self.output_dir / '.write_test'
            test_file.write_text('test')
            test_file.unlink()

            self.logger.debug(f"Output directory ready: {self.output_dir}")

        except Exception as e:
            error = translate_exception(e, "output_directory_creation")
            error.file_path = str(self.output_dir)
            error.operation = "create_directory"
            raise error

    @handle_errors("generate_filename")
    def generate_filename(self, topic: str, timestamp: Optional[datetime] = None) -> str:
        """
        Generate a standardized filename for audio files.

        Format: podcast_{timestamp}.{format}

        Args:
            topic: The podcast topic (kept for backward compatibility, not used in filename)
            timestamp: Optional timestamp for filename (defaults to current time)

        Returns:
            Generated filename string
        """
        # Use provided timestamp or current time
        if timestamp is None:
            timestamp = datetime.now()

        # Format timestamp as YYYYMMDD_HHMMSS
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Generate filename with timestamp only
        filename = f"podcast_{timestamp_str}.{AUDIO_FORMAT}"

        self.logger.debug(f"Generated filename: {filename}")
        return filename

    def _sanitize_topic(self, topic: str) -> str:
        """
        Sanitize topic string for safe filename usage.

        Args:
            topic: Raw topic string

        Returns:
            Sanitized topic string safe for filenames
        """
        # Remove or replace special characters
        sanitized = re.sub(r'[^\w\s-]', '', topic.strip())

        # Replace spaces and multiple hyphens with single hyphen
        sanitized = re.sub(r'[-\s]+', '-', sanitized)

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')

        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip('-')

        # Ensure we have something left
        if not sanitized:
            sanitized = "untitled"

        return sanitized.lower()

    @handle_errors("save_audio_file")
    def save_audio_file(self, audio_data: bytes, topic: str,
                       timestamp: Optional[datetime] = None) -> str:
        """
        Save audio data to file with standardized naming.

        Args:
            audio_data: Raw audio data in bytes
            topic: Topic for filename generation
            timestamp: Optional timestamp for filename

        Returns:
            Full path to saved file

        Raises:
            FileOperationError: If file cannot be saved
            ValidationError: If audio data is invalid
        """
        if not audio_data:
            raise FileOperationError("Audio data cannot be empty")

        if len(audio_data) == 0:
            raise FileOperationError("Audio data length cannot be zero")

        # Check disk space before saving
        if not check_disk_space(len(audio_data) // (1024 * 1024) + 10):  # +10MB buffer
            raise FileOperationError("Insufficient disk space to save audio file")

        # Generate filename
        filename = self.generate_filename(topic, timestamp)
        file_path = self.output_dir / filename

        try:
            # Write audio data to file
            file_path.write_bytes(audio_data)

            # Verify file was written correctly
            if not file_path.exists():
                raise FileOperationError(f"Failed to create audio file: {filename}")

            actual_size = file_path.stat().st_size
            if actual_size != len(audio_data):
                raise FileOperationError(
                    f"File size mismatch. Expected: {len(audio_data)}, Actual: {actual_size}"
                )

            self.logger.info(f"Audio file saved successfully: {filename} ({actual_size} bytes)")
            return str(file_path)

        except Exception as e:
            # Clean up partial file if it exists
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

            error = translate_exception(e, "audio_file_save")
            error.file_path = str(file_path)
            error.operation = "write"
            error.file_size = len(audio_data)
            raise error

    @handle_errors("get_file_info")
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about an audio file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information

        Raises:
            FileOperationError: If file doesn't exist or cannot be accessed
        """
        path = Path(file_path)

        if not path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")

        if not path.is_file():
            raise FileOperationError(f"Path is not a file: {file_path}")

        try:
            stat = path.stat()
            return {
                'path': str(path),
                'name': path.name,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'extension': path.suffix.lower(),
                'is_audio': path.suffix.lower() in ALLOWED_AUDIO_EXTENSIONS
            }
        except Exception as e:
            error = translate_exception(e, "file_info_retrieval")
            error.file_path = file_path
            error.operation = "stat"
            raise error

    @handle_errors("cleanup_old_files")
    def cleanup_old_files(self, max_age_days: Optional[int] = None,
                         force_cleanup: bool = False) -> Dict[str, Any]:
        """
        Clean up old audio files based on age and storage limits.

        Args:
            max_age_days: Maximum age in days (defaults to config value)
            force_cleanup: Force cleanup even if storage limits not exceeded

        Returns:
            Dictionary with cleanup results

        Raises:
            FileOperationError: If cleanup operations fail
        """
        max_age = max_age_days or MAX_FILE_AGE_DAYS
        cutoff_date = datetime.now() - timedelta(days=max_age)

        cleanup_results = {
            'deleted_files': [],
            'freed_bytes': 0,
            'errors': [],
            'total_files_checked': 0,
            'cleanup_reason': []
        }

        try:
            # Get all audio files
            audio_files = list(self.output_dir.glob(f"*.{AUDIO_FORMAT}"))
            audio_files.extend(self.output_dir.glob("*.wav"))
            audio_files.extend(self.output_dir.glob("*.ogg"))
            audio_files.extend(self.output_dir.glob("*.m4a"))

            cleanup_results['total_files_checked'] = len(audio_files)

            # Check storage usage
            total_size = sum(f.stat().st_size for f in audio_files if f.exists())
            max_storage_bytes = MAX_STORAGE_MB * 1024 * 1024

            should_cleanup_by_age = True
            should_cleanup_by_storage = total_size > max_storage_bytes or force_cleanup

            if should_cleanup_by_storage:
                cleanup_results['cleanup_reason'].append(f"Storage limit exceeded: {total_size / (1024*1024):.1f}MB > {MAX_STORAGE_MB}MB")

            if should_cleanup_by_age:
                cleanup_results['cleanup_reason'].append(f"Age limit: {max_age} days")

            # Sort files by modification time (oldest first)
            audio_files.sort(key=lambda f: f.stat().st_mtime)

            for file_path in audio_files:
                try:
                    if not file_path.exists():
                        continue

                    file_info = self.get_file_info(str(file_path))

                    # Delete if too old
                    delete_file = False
                    delete_reason = ""

                    if should_cleanup_by_age and file_info['created_at'] < cutoff_date:
                        delete_file = True
                        delete_reason = f"Older than {max_age} days"

                    # Delete if storage limit exceeded (oldest files first)
                    elif should_cleanup_by_storage and total_size > max_storage_bytes:
                        delete_file = True
                        delete_reason = "Storage limit cleanup"

                    if delete_file:
                        file_size = file_info['size']
                        file_path.unlink()

                        cleanup_results['deleted_files'].append({
                            'path': str(file_path),
                            'name': file_info['name'],
                            'size': file_size,
                            'reason': delete_reason
                        })
                        cleanup_results['freed_bytes'] += file_size
                        total_size -= file_size

                        self.logger.info(f"Deleted old audio file: {file_path.name} ({delete_reason})")

                except Exception as e:
                    error_msg = f"Failed to process file {file_path.name}: {str(e)}"
                    cleanup_results['errors'].append(error_msg)
                    self.logger.warning(error_msg)

            # Log cleanup summary
            if cleanup_results['deleted_files']:
                freed_mb = cleanup_results['freed_bytes'] / (1024 * 1024)
                self.logger.info(
                    f"Cleanup completed: Deleted {len(cleanup_results['deleted_files'])} files, "
                    f"freed {freed_mb:.1f}MB"
                )
            else:
                self.logger.debug("No files needed cleanup")

            return cleanup_results

        except Exception as e:
            error = translate_exception(e, "file_cleanup")
            error.operation = "cleanup"
            raise error

    @handle_errors("get_file_for_download")
    def get_file_for_download(self, filename: str) -> Tuple[str, str, int]:
        """
        Get file information for download purposes.

        Args:
            filename: Name of the file to download

        Returns:
            Tuple of (file_path, mime_type, file_size)

        Raises:
            FileOperationError: If file doesn't exist or is invalid
        """
        # Validate filename
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            raise FileOperationError(f"Invalid filename: {filename}")

        file_path = self.output_dir / filename

        if not file_path.exists():
            raise FileOperationError(f"File not found: {filename}")

        if not file_path.is_file():
            raise FileOperationError(f"Path is not a file: {filename}")

        # Get file extension and determine MIME type
        extension = file_path.suffix.lower()
        mime_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4'
        }

        mime_type = mime_types.get(extension, 'application/octet-stream')

        # Get file size
        file_size = file_path.stat().st_size

        self.logger.info(f"Preparing file for download: {filename} ({file_size} bytes)")

        return str(file_path), mime_type, file_size

    @handle_errors("list_audio_files")
    def list_audio_files(self, include_info: bool = False) -> List[Dict[str, Any]]:
        """
        List all audio files in the output directory.

        Args:
            include_info: Whether to include detailed file information

        Returns:
            List of file information dictionaries
        """
        audio_files = []

        # Get all audio files
        for ext in ['.mp3', '.wav', '.ogg', '.m4a']:
            for file_path in self.output_dir.glob(f"*{ext}"):
                if file_path.is_file():
                    if include_info:
                        try:
                            file_info = self.get_file_info(str(file_path))
                            audio_files.append(file_info)
                        except Exception as e:
                            self.logger.warning(f"Failed to get info for {file_path.name}: {e}")
                    else:
                        audio_files.append({
                            'name': file_path.name,
                            'path': str(file_path)
                        })

        # Sort by creation time (newest first)
        if include_info:
            audio_files.sort(key=lambda f: f['created_at'], reverse=True)
        else:
            audio_files.sort(key=lambda f: Path(f['path']).stat().st_ctime, reverse=True)

        return audio_files

    @handle_errors("get_storage_info")
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage usage information.

        Returns:
            Dictionary with storage information
        """
        try:
            audio_files = self.list_audio_files(include_info=True)
            total_size = sum(f['size'] for f in audio_files)
            file_count = len(audio_files)

            # Get disk space info
            disk_usage = shutil.disk_usage(self.output_dir)

            return {
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'max_storage_mb': MAX_STORAGE_MB,
                'storage_usage_percent': round((total_size / (MAX_STORAGE_MB * 1024 * 1024)) * 100, 2),
                'disk_free_bytes': disk_usage.free,
                'disk_free_gb': round(disk_usage.free / (1024 * 1024 * 1024), 2),
                'output_directory': str(self.output_dir),
                'max_file_age_days': MAX_FILE_AGE_DAYS
            }
        except Exception as e:
            error = translate_exception(e, "storage_info")
            raise error


# Global file handler instance
_file_handler_instance = None


def get_file_handler() -> FileHandler:
    """
    Get the global file handler instance.

    Returns:
        FileHandler instance
    """
    global _file_handler_instance
    if _file_handler_instance is None:
        _file_handler_instance = FileHandler()
    return _file_handler_instance


# Convenience functions for common operations
def save_audio_file(audio_data: bytes, topic: str,
                   timestamp: Optional[datetime] = None) -> str:
    """
    Save audio data to file with standardized naming.

    Args:
        audio_data: Raw audio data in bytes
        topic: Topic for filename generation
        timestamp: Optional timestamp for filename

    Returns:
        Full path to saved file
    """
    return get_file_handler().save_audio_file(audio_data, topic, timestamp)


def generate_filename(topic: str, timestamp: Optional[datetime] = None) -> str:
    """
    Generate a standardized filename for audio files.

    Args:
        topic: The podcast topic for filename generation
        timestamp: Optional timestamp for filename

    Returns:
        Generated filename string
    """
    return get_file_handler().generate_filename(topic, timestamp)


def cleanup_old_files(max_age_days: Optional[int] = None) -> Dict[str, Any]:
    """
    Clean up old audio files based on age and storage limits.

    Args:
        max_age_days: Maximum age in days (defaults to config value)

    Returns:
        Dictionary with cleanup results
    """
    return get_file_handler().cleanup_old_files(max_age_days)


def get_file_for_download(filename: str) -> Tuple[str, str, int]:
    """
    Get file information for download purposes.

    Args:
        filename: Name of the file to download

    Returns:
        Tuple of (file_path, mime_type, file_size)
    """
    return get_file_handler().get_file_for_download(filename)


def list_audio_files(include_info: bool = False) -> List[Dict[str, Any]]:
    """
    List all audio files in the output directory.

    Args:
        include_info: Whether to include detailed file information

    Returns:
        List of file information dictionaries
    """
    return get_file_handler().list_audio_files(include_info)


def get_storage_info() -> Dict[str, Any]:
    """
    Get storage usage information.

    Returns:
        Dictionary with storage information
    """
    return get_file_handler().get_storage_info()