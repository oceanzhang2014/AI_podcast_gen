"""
Audio Processing Package

This package provides audio processing services for the podcast generation system,
including audio merging, format conversion, and file management.
"""

from .audio_merger import AudioMergerService, create_audio_merger_service

__all__ = [
    'AudioMergerService',
    'create_audio_merger_service'
]