"""
Audio Merger Service

This module provides PyDub-based audio merging functionality for combining
individual character audio segments into a single podcast file.
"""

import os
import tempfile
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, BinaryIO
from pathlib import Path

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

from utils.error_handler import get_logger, handle_errors


class AudioMergerService:
    """
    Service for merging individual audio segments into a single podcast file.

    This service uses PyDub AudioSegment to combine audio files with proper
    format handling and temporary file management.
    """

    def __init__(self, output_dir: str = "generated_audio"):
        """
        Initialize the audio merger service.

        Args:
            output_dir: Directory to save final merged audio files
        """
        self.logger = get_logger()

        if not PYDUB_AVAILABLE:
            raise ImportError("PyDub is not available. Install with: pip install pydub")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_files: List[str] = []

        # Thread lock for preventing concurrent access to temporary files
        self._lock = threading.Lock()
        # Thread-local storage for temporary files
        self._thread_local = threading.local()

        self.logger.info("Audio merger service initialized")

    @handle_errors("Audio merging", reraise=True)
    def merge_audio_segments(
        self,
        audio_segments: List[Dict[str, Any]],
        output_filename: Optional[str] = None,
        format: str = "wav"
    ) -> Optional[str]:
        """
        Merge multiple audio segments into a single file.

        Args:
            audio_segments: List of dictionaries containing audio data and metadata
            output_filename: Optional custom output filename
            format: Output audio format (wav, mp3, etc.)

        Returns:
            Path to merged audio file, or None if failed
        """
        if not audio_segments:
            self.logger.warning("No audio segments provided for merging")
            return None

        # Use thread lock for the entire merging process to prevent conflicts
        with self._lock:
            try:
                # Generate output filename if not provided
                if not output_filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    thread_id = threading.get_ident()
                    output_filename = f"podcast_{timestamp}_thread{thread_id}.{format}"

                output_path = self.output_dir / output_filename

                # Start with empty audio segment
                combined_audio = AudioSegment.empty()

                self.logger.info(f"Starting to merge {len(audio_segments)} audio segments")

                # Process each audio segment with retry mechanism
                for i, segment in enumerate(audio_segments):
                    max_retries = 3
                    for retry in range(max_retries):
                        try:
                            audio_segment = None

                            # First try to use temp_file_path if available (most efficient)
                            temp_file_path = segment.get('temp_file_path')
                            if temp_file_path and os.path.exists(temp_file_path):
                                try:
                                    audio_segment = AudioSegment.from_file(temp_file_path)
                                    self.logger.debug(f"Loaded audio from temp file: {temp_file_path}")
                                except Exception as e:
                                    self.logger.warning(f"Failed to load from temp file {temp_file_path}: {e}")

                            # Fallback: convert audio data to AudioSegment
                            if audio_segment is None:
                                audio_data = segment.get('audio_data')
                                if not audio_data:
                                    self.logger.warning(f"No audio data in segment {i}")
                                    break

                                audio_segment = self._convert_audio_data(audio_data, format)
                                if audio_segment:
                                    self.logger.debug(f"Converted audio data for segment {i}")

                            if audio_segment:
                                combined_audio += audio_segment
                                self.logger.debug(f"Added segment {i} to combined audio")
                                break  # Success, exit retry loop
                            else:
                                self.logger.warning(f"Failed to process segment {i}, attempt {retry + 1}")

                        except Exception as e:
                            if retry < max_retries - 1:
                                self.logger.warning(f"Failed to process audio segment {i}, attempt {retry + 1}: {str(e)}")
                                # Brief sleep before retry
                                import time
                                time.sleep(0.1)
                            else:
                                self.logger.error(f"Failed to process audio segment {i} after {max_retries} attempts: {str(e)}")
                                break

                if len(combined_audio) == 0:
                    self.logger.error("No valid audio segments were merged")
                    return None

                # Export combined audio
                combined_audio.export(output_path, format=format)
                file_size = os.path.getsize(output_path)

                self.logger.info(f"Successfully merged audio into {output_path} ({file_size} bytes)")
                return str(output_path)

            except Exception as e:
                self.logger.error(f"Audio merging failed: {str(e)}")
                return None

    def _convert_audio_data(self, audio_data: bytes, target_format: str = "wav") -> Optional[AudioSegment]:
        """
        Convert raw audio data to PyDub AudioSegment.

        Args:
            audio_data: Raw audio data bytes
            target_format: Target audio format

        Returns:
            AudioSegment instance or None if conversion failed
        """
        # Use thread lock to prevent concurrent access to temporary files
        with self._lock:
            try:
                # Initialize thread-local temp files list if not exists
                if not hasattr(self._thread_local, 'temp_files'):
                    self._thread_local.temp_files = []

                # Try to create AudioSegment from raw data
                # First attempt: assume it's already in a supported format
                try:
                    # Create a unique temporary file with thread ID
                    thread_id = threading.get_ident()
                    with tempfile.NamedTemporaryFile(
                        suffix=f'.{target_format}',
                        delete=False,
                        prefix=f'audio_{thread_id}_'
                    ) as temp_file:
                        temp_file.write(audio_data)
                        temp_file.flush()
                        temp_file_path = temp_file.name

                    # Track this temporary file for cleanup
                    self._thread_local.temp_files.append(temp_file_path)

                    # Load audio from temporary file
                    audio = AudioSegment.from_file(temp_file_path)

                    return audio
                except Exception as e:
                    self.logger.debug(f"Failed to load audio directly: {e}")

                    # Second attempt: try to detect format and convert
                    try:
                        # Write to temporary file and let pydub detect format
                        thread_id = threading.get_ident()
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            prefix=f'audio_{thread_id}_'
                        ) as temp_file:
                            temp_file.write(audio_data)
                            temp_file.flush()
                            temp_file_path = temp_file.name

                        # Track this temporary file for cleanup
                        self._thread_local.temp_files.append(temp_file_path)

                        # Try to determine format from file content
                        audio = AudioSegment.from_file(temp_file_path)

                        return audio
                    except Exception as e2:
                        self.logger.warning(f"Failed to convert audio data: {e2}")
                        return None

            except Exception as e:
                self.logger.error(f"Audio data conversion failed: {e}")
                return None

    @handle_errors("Audio file merging", reraise=True)
    def merge_audio_files(
        self,
        audio_files: List[str],
        output_filename: Optional[str] = None,
        format: str = "wav"
    ) -> Optional[str]:
        """
        Merge multiple audio files into a single file.

        Args:
            audio_files: List of paths to audio files
            output_filename: Optional custom output filename
            format: Output audio format

        Returns:
            Path to merged audio file, or None if failed
        """
        if not audio_files:
            self.logger.warning("No audio files provided for merging")
            return None

        try:
            # Generate output filename if not provided
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"merged_podcast_{timestamp}.{format}"

            output_path = self.output_dir / output_filename

            # Start with empty audio segment
            combined_audio = AudioSegment.empty()

            self.logger.info(f"Starting to merge {len(audio_files)} audio files")

            # Process each audio file
            for audio_file in audio_files:
                try:
                    if not os.path.exists(audio_file):
                        self.logger.warning(f"Audio file not found: {audio_file}")
                        continue

                    # Load audio file
                    audio = AudioSegment.from_file(audio_file)
                    combined_audio += audio
                    self.logger.debug(f"Added {audio_file} to combined audio")

                except Exception as e:
                    self.logger.error(f"Failed to process audio file {audio_file}: {str(e)}")
                    continue

            if len(combined_audio) == 0:
                self.logger.error("No valid audio files were merged")
                return None

            # Export combined audio
            combined_audio.export(output_path, format=format)
            file_size = os.path.getsize(output_path)

            self.logger.info(f"Successfully merged audio files into {output_path} ({file_size} bytes)")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"Audio file merging failed: {str(e)}")
            return None

    def get_audio_info(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with audio information or None if failed
        """
        try:
            if not os.path.exists(audio_path):
                return None

            audio = AudioSegment.from_file(audio_path)
            file_size = os.path.getsize(audio_path)

            return {
                'file_path': audio_path,
                'file_size_bytes': file_size,
                'duration_seconds': len(audio) / 1000.0,
                'sample_rate': audio.frame_rate,
                'channels': audio.channels,
                'sample_width': audio.sample_width
            }

        except Exception as e:
            self.logger.error(f"Failed to get audio info for {audio_path}: {e}")
            return None

    def cleanup_temp_files(self):
        """Clean up temporary files created during processing."""
        with self._lock:
            # Clean up global temp files
            for temp_file in self.temp_files[:]:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {e}")

            self.temp_files = []

            # Clean up thread-local temp files
            if hasattr(self._thread_local, 'temp_files'):
                for temp_file in self._thread_local.temp_files[:]:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            self.logger.debug(f"Cleaned up thread-local temporary file: {temp_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up thread-local {temp_file}: {e}")

                self._thread_local.temp_files = []

            self.logger.debug("Cleaned up all temporary files")

    def validate_audio_format(self, audio_data: bytes) -> bool:
        """
        Validate if audio data is in a supported format.

        Args:
            audio_data: Raw audio data bytes

        Returns:
            True if format is supported, False otherwise
        """
        try:
            # Try to create AudioSegment from data
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()

                # Try to load with pydub
                AudioSegment.from_file(temp_file.name)
                return True
        except Exception:
            return False

    def convert_audio_format(
        self,
        input_path: str,
        output_path: str,
        target_format: str
    ) -> bool:
        """
        Convert audio file to different format.

        Args:
            input_path: Path to input audio file
            output_path: Path to output audio file
            target_format: Target audio format

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            if not os.path.exists(input_path):
                self.logger.error(f"Input file not found: {input_path}")
                return False

            # Load audio
            audio = AudioSegment.from_file(input_path)

            # Export in target format
            audio.export(output_path, format=target_format)

            self.logger.info(f"Converted {input_path} to {output_path} ({target_format})")
            return True

        except Exception as e:
            self.logger.error(f"Audio format conversion failed: {e}")
            return False

    def close(self):
        """Clean up resources."""
        self.cleanup_temp_files()
        self.logger.info("Audio merger service closed")


# Factory function
def create_audio_merger_service(output_dir: str = "generated_audio") -> AudioMergerService:
    """
    Create an audio merger service instance.

    Args:
        output_dir: Directory to save final merged audio files

    Returns:
        AudioMergerService instance
    """
    return AudioMergerService(output_dir)