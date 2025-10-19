"""
TTS Engine wrapper for podcast generation system.

This module provides a unified interface for Text-to-Speech conversion
using open-source TTS libraries with support for multiple voice profiles
and audio formats.

Purpose: Convert text to speech with different voice characteristics.
"""

import os
import io
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, BinaryIO
from dataclasses import dataclass
from datetime import datetime

try:
    import numpy as np
except ImportError:
    np = None

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import pydub
    from pydub import AudioSegment
except ImportError:
    pydub = None
    AudioSegment = None

# Import ChatTTS for TTS functionality
try:
    import torch
    import ChatTTS
    import ChatTTS.core
    Chat = ChatTTS.Chat
    print("[INFO] ChatTTS TTS engine initialized successfully")
except ImportError as e:
    print(f"[WARNING] Failed to import ChatTTS: {e}")
    print("[INFO] Falling back to basic TTS functionality")
    Chat = None
    ChatTTS = None
except Exception as e:
    print(f"[ERROR] ChatTTS initialization failed: {e}")
    print("[INFO] ChatTTS temporarily disabled due to torio FFmpeg compatibility issues")
    print("[INFO] Basic web interface will be available without TTS functionality")
    Chat = None
    ChatTTS = None

# Fallback TTS options removed as requested by user (ChatTTS-only configuration)
# gTTS and pyttsx3 imports commented out to prioritize ChatTTS usage
# try:
#     from gtts import gTTS
#     GTTS_AVAILABLE = True
#     print("[INFO] gTTS (Google Text-to-Speech) available as fallback")
# except ImportError:
#     GTTS_AVAILABLE = False
#     gTTS = None
#     print("[WARNING] gTTS not available, install with: pip install gTTS")

# try:
#     import pyttsx3
#     PYTTSX3_AVAILABLE = True
#     print("[INFO] pyttsx3 (offline TTS) available as fallback")
# except ImportError:
#     PYTTSX3_AVAILABLE = False
#     pyttsx3 = None
#     print("[WARNING] pyttsx3 not available, install with: pip install pyttsx3")

# Import error handling utilities
from utils.error_handler import (
    TTSError, FileOperationError, ValidationError, ConfigurationError,
    get_logger, tts_retry, handle_errors
)

# Import configuration
try:
    from config import (
        TTS_ENGINE, CHATTTS_MODEL_PATH, CHATTTS_DEVICE, CHATTTS_ENABLE_CUDA,
        CHATTTS_REFINE_TEXT, CHATTTS_TEMPERATURE, CHATTTS_TOP_P, CHATTTS_TOP_K,
        CHATTTS_EOS, AUDIO_OUTPUT_DIR, AUDIO_FORMAT, AUDIO_SAMPLE_RATE,
        AUDIO_QUALITY, VOICE_PROFILES, CHATTTS_VOICE_PRESETS
    )
except (ValueError, ImportError) as e:
    # Fallback defaults for testing/development
    TTS_ENGINE = 'chattts'
    CHATTTS_MODEL_PATH = '2Noise/ChatTTS'
    CHATTTS_DEVICE = 'cpu'
    CHATTTS_ENABLE_CUDA = False
    CHATTTS_REFINE_TEXT = True
    CHATTTS_TEMPERATURE = 0.3
    CHATTTS_TOP_P = 0.7
    CHATTTS_TOP_K = 20
    CHATTTS_EOS = [",", ".", "!", "?", "~", "。", "！", "？", "…", "~"]
    AUDIO_OUTPUT_DIR = Path('generated_audio')
    AUDIO_FORMAT = 'mp3'
    AUDIO_SAMPLE_RATE = 22050
    AUDIO_QUALITY = 'high'
    VOICE_PROFILES = {
        'male': {'professional': {'rate': 140, 'volume': 0.85, 'chattts_seed': 42}},
        'female': {'professional': {'rate': 145, 'volume': 0.85, 'chattts_seed': 111}},
        'other': {'neutral': {'rate': 150, 'volume': 0.85, 'chattts_seed': 555}}
    }
    CHATTTS_VOICE_PRESETS = {}


@dataclass
class VoiceProfile:
    """Voice profile configuration for TTS synthesis."""

    gender: str  # 'male', 'female', 'other'
    personality: str  # 'professional', 'casual', 'energetic', 'calm', 'neutral'
    rate: int  # Speech rate in words per minute
    volume: float  # Volume level (0.0 to 1.0)
    pitch: Optional[float] = None  # Pitch multiplier
    seed: Optional[int] = None  # Random seed for reproducibility

    # ChatTTS specific parameters
    temperature: Optional[float] = None
    top_P: Optional[float] = None
    top_K: Optional[int] = None
    prompt: Optional[str] = None


class TTSEngine:
    """
    Text-to-Speech engine wrapper with support for multiple voice profiles.

    This class provides a unified interface for converting text to speech using
    open-source TTS libraries, with support for different voice characteristics
    and audio formats.
    """

    def __init__(self, engine: str = None):
        """
        Initialize TTS engine.

        Args:
            engine: TTS engine to use ('chattts', 'azure', etc.)

        Raises:
            ConfigurationError: If required dependencies are missing
        """
        self.logger = get_logger()
        self.engine_name = engine or TTS_ENGINE
        self._tts_model = None
        self._is_initialized = False

        # Validate dependencies
        self._validate_dependencies()

        # Initialize engine
        self._initialize_engine()

    def _validate_dependencies(self) -> None:
        """
        Validate that required dependencies are available.

        Raises:
            ConfigurationError: If required dependencies are missing
        """
        missing_deps = []

        if self.engine_name == 'chattts':
            if Chat is None:
                missing_deps.append('chattts')
            if np is None:
                missing_deps.append('numpy')
            if sf is None:
                missing_deps.append('soundfile')

        if pydub is None:
            missing_deps.append('pydub')

        if missing_deps:
            raise ConfigurationError(
                f"Missing required dependencies for {self.engine_name}: {', '.join(missing_deps)}. "
                f"Install with: pip install {' '.join(missing_deps)}",
                config_key='TTS_ENGINE',
                config_value=self.engine_name
            )

    def _initialize_engine(self) -> None:
        """
        Initialize the TTS engine based on configuration.

        Raises:
            TTSError: If engine initialization fails
        """
        try:
            if self.engine_name == 'chattts':
                self._initialize_chattts()
            else:
                raise TTSError(
                    f"Unsupported TTS engine: {self.engine_name}",
                    tts_engine=self.engine_name
                )

            self._is_initialized = True
            self.logger.info(f"Successfully initialized TTS engine: {self.engine_name}")

        except Exception as e:
            error_msg = f"Failed to initialize TTS engine {self.engine_name}: {str(e)}"
            self.logger.error(error_msg)
            raise TTSError(error_msg, tts_engine=self.engine_name, original_error=e)

    def _initialize_chattts(self) -> None:
        """Initialize ChatTTS model."""
        try:
            self.logger.info(f"Initializing ChatTTS with model: {CHATTTS_MODEL_PATH}")

            # Configure device
            device = CHATTTS_DEVICE
            if CHATTTS_ENABLE_CUDA and device == 'cpu':
                try:
                    import torch
                    if torch.cuda.is_available():
                        device = 'cuda'
                        self.logger.info("CUDA detected and enabled for ChatTTS")
                except ImportError:
                    self.logger.warning("PyTorch not available, falling back to CPU")

            # Initialize ChatTTS
            self._tts_model = Chat()

            # Load model with enhanced error handling for Windows
            self.logger.info(f"Loading ChatTTS model from: {CHATTTS_MODEL_PATH}")

            try:
                # Try loading with different strategies for Windows compatibility
                load_success = self._tts_model.load(
                    source='local' if os.path.exists(CHATTTS_MODEL_PATH) else 'huggingface',
                    compile=False,  # Disable compilation for better compatibility
                    force_redownload=False  # Avoid unnecessary downloads
                )

                if not load_success:
                    raise TTSError("ChatTTS.load() returned False", tts_engine='chattts')

            except Exception as load_error:
                self.logger.warning(f"Primary model loading failed: {load_error}")

                # Try alternative loading strategy
                try:
                    self.logger.info("Trying alternative model loading strategy...")
                    load_success = self._tts_model.load(
                        source='huggingface',  # Force huggingface source
                        compile=False,
                        force_redownload=False
                    )

                    if not load_success:
                        raise TTSError("Alternative ChatTTS.load() returned False", tts_engine='chattts')

                except Exception as alt_error:
                    self.logger.error(f"Alternative model loading also failed: {alt_error}")
                    raise TTSError(
                        f"ChatTTS model loading failed. Primary error: {load_error}, Alternative error: {alt_error}",
                        tts_engine='chattts',
                        original_error=load_error
                    )

            self._chattts_device = device
            self.logger.info("ChatTTS model loaded successfully")

            # Verify model is actually working by testing a simple inference
            try:
                self.logger.info("Verifying ChatTTS model functionality...")

                # Create a simple test voice profile instead of relying on VOICE_PROFILES
                from utils.models import VoiceProfile
                test_voice_profile = VoiceProfile(
                    gender='male',
                    personality='neutral',
                    rate=150,
                    volume=0.9
                )

                test_params = self._prepare_chattts_params(test_voice_profile)
                test_result = self._tts_model.infer(['Hello'], **test_params)

                if test_result and len(test_result) > 0:
                    self.logger.info("ChatTTS model verification successful")
                else:
                    self.logger.warning("ChatTTS model verification returned empty result")

            except Exception as verify_error:
                self.logger.error(f"ChatTTS model verification failed: {verify_error}")
                # Don't fail initialization for verification errors, just log warning
                self.logger.warning("Continuing without ChatTTS verification (may cause runtime errors)")

        except Exception as e:
            raise TTSError(
                f"ChatTTS initialization failed: {str(e)}",
                tts_engine='chattts',
                original_error=e
            )

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voice profiles.

        Returns:
            List of available voice profiles with their properties
        """
        voices = []

        for gender, personalities in VOICE_PROFILES.items():
            for personality, config in personalities.items():
                voice_profile = VoiceProfile(
                    gender=gender,
                    personality=personality,
                    rate=config.get('rate', 150),
                    volume=config.get('volume', 0.85),
                    seed=config.get('chattts_seed')
                )

                # Add ChatTTS preset parameters if available
                preset_key = f"{gender}_{personality}"
                if preset_key in CHATTTS_VOICE_PRESETS:
                    preset = CHATTTS_VOICE_PRESETS[preset_key]
                    voice_profile.temperature = preset.get('temperature', CHATTTS_TEMPERATURE)
                    voice_profile.top_P = preset.get('top_P', CHATTTS_TOP_P)
                    voice_profile.top_K = preset.get('top_K', CHATTTS_TOP_K)
                    voice_profile.prompt = preset.get('prompt')

                voices.append({
                    'id': preset_key,
                    'name': f"{gender.title()} {personality.title()}",
                    'gender': gender,
                    'personality': personality,
                    'language': ['en', 'zh'],  # Support English and Chinese
                    'config': voice_profile.__dict__
                })

        return voices

    @tts_retry(max_retries=3)
    @handle_errors("TTS conversion", reraise=True)
    def convert_to_speech(self, text: str, voice_profile: Union[str, VoiceProfile, Dict[str, Any]],
                         output_format: str = None) -> bytes:
        """
        Convert text to speech using specified voice profile.

        Args:
            text: Text to convert to speech
            voice_profile: Voice profile (name string, VoiceProfile object, or dict)
            output_format: Output audio format (mp3, wav, etc.)

        Returns:
            Audio data as bytes

        Raises:
            TTSError: If text-to-speech conversion fails
            ValidationError: If input parameters are invalid
        """
        if not self._is_initialized:
            raise TTSError("TTS engine not initialized", tts_engine=self.engine_name)

        # Validate inputs
        if not text or not text.strip():
            raise ValidationError("Text cannot be empty", field='text')

        if len(text) > 10000:  # Prevent excessively long inputs
            raise ValidationError(
                "Text too long (maximum 10000 characters)",
                field='text',
                validation_rule='max_length'
            )

        # Parse voice profile
        voice_config = self._parse_voice_profile(voice_profile)

        # Set output format
        output_format = output_format or AUDIO_FORMAT

        try:
            self.logger.info(f"Converting text to speech using {self.engine_name} with voice: {voice_config.gender}_{voice_config.personality}")

            # Generate audio based on engine
            if self.engine_name == 'chattts':
                audio_data = self._convert_with_chattts(text, voice_config)
            else:
                raise TTSError(f"Unsupported TTS engine: {self.engine_name}")

            # Convert to desired format
            audio_bytes = self._convert_audio_format(audio_data, output_format, voice_config)

            self.logger.info(f"Successfully converted {len(text)} characters to audio ({len(audio_bytes)} bytes)")
            return audio_bytes

        except Exception as e:
            if isinstance(e, (TTSError, ValidationError)):
                raise

            # Wrap unexpected errors
            raise TTSError(
                f"Text-to-speech conversion failed: {str(e)}",
                tts_engine=self.engine_name,
                voice_profile=f"{voice_config.gender}_{voice_config.personality}",
                text_snippet=text[:100] + "..." if len(text) > 100 else text,
                original_error=e
            )

    def _parse_voice_profile(self, voice_profile: Union[str, VoiceProfile, Dict[str, Any]]) -> VoiceProfile:
        """
        Parse voice profile from various input formats.

        Args:
            voice_profile: Voice profile in various formats

        Returns:
            VoiceProfile object

        Raises:
            ValidationError: If voice profile is invalid
        """
        if isinstance(voice_profile, VoiceProfile):
            return voice_profile

        if isinstance(voice_profile, dict):
            return VoiceProfile(**voice_profile)

        # Handle VoiceSelection objects from VoiceManager
        if hasattr(voice_profile, '__class__') and voice_profile.__class__.__name__ == 'VoiceSelection':
            # Convert VoiceSelection to VoiceProfile
            voice_profile_obj = voice_profile
            return VoiceProfile(
                gender=voice_profile_obj.gender.value if hasattr(voice_profile_obj.gender, 'value') else str(voice_profile_obj.gender),
                personality=voice_profile_obj.personality,
                rate=voice_profile_obj.rate,
                volume=voice_profile_obj.volume,
                seed=voice_profile_obj.seed,
                temperature=voice_profile_obj.temperature,
                top_P=voice_profile_obj.top_P,
                top_K=voice_profile_obj.top_K,
                prompt=voice_profile_obj.prompt
            )

        if isinstance(voice_profile, str):
            # Look up preset voice profile
            for gender, personalities in VOICE_PROFILES.items():
                for personality, config in personalities.items():
                    if voice_profile.lower() == f"{gender}_{personality}":
                        voice_obj = VoiceProfile(
                            gender=gender,
                            personality=personality,
                            rate=config.get('rate', 150),
                            volume=config.get('volume', 0.85),
                            seed=config.get('chattts_seed')
                        )

                        # Add ChatTTS preset parameters
                        preset_key = f"{gender}_{personality}"
                        if preset_key in CHATTTS_VOICE_PRESETS:
                            preset = CHATTTS_VOICE_PRESETS[preset_key]
                            voice_obj.temperature = preset.get('temperature', CHATTTS_TEMPERATURE)
                            voice_obj.top_P = preset.get('top_P', CHATTTS_TOP_P)
                            voice_obj.top_K = preset.get('top_K', CHATTTS_TOP_K)
                            voice_obj.prompt = preset.get('prompt')

                        return voice_obj

            # Fallback to default profile if not found
            self.logger.warning(f"Unknown voice profile '{voice_profile}', using default")
            return VoiceProfile(
                gender='female',
                personality='professional',
                rate=145,
                volume=0.85,
                seed=111
            )

        raise ValidationError(f"Invalid voice profile type: {type(voice_profile)}")

    def _convert_with_chattts(self, text: str, voice_config: VoiceProfile) -> np.ndarray:
        """
        Convert text to speech using ChatTTS.

        Args:
            text: Text to convert
            voice_config: Voice configuration

        Returns:
            Audio data as numpy array
        """
        try:
            # Validate input text
            if not text or not text.strip():
                raise ValidationError("Text cannot be empty")

            # Prepare ChatTTS parameters
            params = self._prepare_chattts_params(voice_config)

            # Log parameters for debugging (excluding sensitive data)
            self.logger.debug(f"ChatTTS parameters: {list(params.keys())}")

            # Preprocess text to avoid narrow() errors
            processed_text = self._preprocess_text_for_chattts(text)
            self.logger.debug(f"Original text length: {len(text)}, Processed: {len(processed_text)}")

            # Generate audio with better error handling
            try:
                wavs = self._tts_model.infer(
                    [processed_text],
                    **params
                )
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    # Handle API parameter errors specifically
                    invalid_param = str(e).split("'")[1] if "'" in str(e) else "unknown"
                    raise TTSError(
                        f"ChatTTS API parameter '{invalid_param}' is not supported. "
                        f"This may be due to ChatTTS library version incompatibility.",
                        tts_engine='chattts',
                        voice_profile=f"{voice_config.gender}_{voice_config.personality}",
                        original_error=e
                    )
                else:
                    # Re-raise other TypeError exceptions
                    raise

            if not wavs or len(wavs) == 0:
                raise TTSError("ChatTTS returned no audio data", tts_engine='chattts')

            audio_data = wavs[0]

            # Validate audio data
            if audio_data is None:
                raise TTSError("ChatTTS returned None audio data", tts_engine='chattts')

            if not isinstance(audio_data, (np.ndarray, list)):
                raise TTSError(f"ChatTTS returned invalid audio data type: {type(audio_data)}", tts_engine='chattts')

            # Convert to numpy array if needed
            if isinstance(audio_data, list):
                audio_data = np.array(audio_data)

            # Check audio data dimensions and length
            if audio_data.size == 0:
                raise TTSError("ChatTTS returned empty audio data", tts_engine='chattts')

            if len(audio_data.shape) == 0:
                raise TTSError("ChatTTS returned scalar audio data", tts_engine='chattts')

            self.logger.debug(f"Audio data shape: {audio_data.shape}, dtype: {audio_data.dtype}")

            # Apply post-processing if needed
            audio_data = self._post_process_audio(audio_data, voice_config)

            return audio_data

        except (ValidationError, TTSError):
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            # Handle unexpected errors
            raise TTSError(
                f"ChatTTS synthesis failed: {str(e)}",
                tts_engine='chattts',
                voice_profile=f"{voice_config.gender}_{voice_config.personality}",
                original_error=e
            )

    def _prepare_chattts_params(self, voice_config: VoiceProfile) -> Dict[str, Any]:
        """
        Prepare ChatTTS inference parameters with ultra-safe defaults for Chinese text.

        Args:
            voice_config: Voice configuration

        Returns:
            Dictionary of ChatTTS parameters
        """
        # Use only supported ChatTTS parameters to avoid API errors
        params = {
            'use_decoder': True,
            'do_text_normalization': False,  # Disable to avoid complex processing
            'skip_refine_text': True,  # Skip refinement to avoid encoding issues
            'do_homophone_replacement': False,  # Disable to reduce complexity
        }

        # Note: seed parameter is also not supported by this ChatTTS version
        # Only use the core parameters that work reliably

        self.logger.debug(f"Using minimal ChatTTS parameters: {list(params.keys())}")
        return params

    def _preprocess_text_for_chattts(self, text: str) -> str:
        """
        Advanced text preprocessing to avoid ChatTTS narrow() errors and encoding issues.

        Args:
            text: Original text

        Returns:
            Processed text safe for ChatTTS
        """
        if not text:
            return "Hello"

        try:
            # Step 1: Clean and normalize text encoding
            cleaned_text = text.strip()

            # Step 2: Handle encoding issues - force proper UTF-8 encoding
            if isinstance(cleaned_text, bytes):
                cleaned_text = cleaned_text.decode('utf-8', errors='ignore')
            else:
                # Re-encode to ensure proper UTF-8
                cleaned_text = cleaned_text.encode('utf-8', errors='ignore').decode('utf-8')

            # Step 3: Remove problematic Unicode characters
            problematic_chars = [
                # Special quotes
                ''', ''', ''', ''', ''', ''',
                # Special dashes and punctuation
                '…', '—', '–', '•', '·',
                # Other problematic symbols
                '□', '■', '▪', '▫', '○', '●', '◐', '◑', '◒', '◓',
                # Invalid control characters
                '\u0000', '\u0001', '\u0002', '\u0003', '\u0004', '\u0005',
                '\u0006', '\u0007', '\u0008', '\u000b', '\u000c', '\u000e',
                '\u000f', '\u0010', '\u0011', '\u0012', '\u0013', '\u0014',
                '\u0015', '\u0016', '\u0017', '\u0018', '\u0019', '\u001a',
                '\u001b', '\u001c', '\u001d', '\u001e', '\u001f'
            ]

            # Replace problematic characters with safe alternatives
            replacements = {
                ''': "'",
                ''': "'",
                ''': '"',
                ''': '"',
                ''': '"',
                ''': '"',
                '…': '...',
                '—': '--',
                '–': '-',
                '•': '·',
                '·': '.',
            }

            for old, new in replacements.items():
                cleaned_text = cleaned_text.replace(old, new)

            # Remove remaining problematic characters
            for char in problematic_chars:
                cleaned_text = cleaned_text.replace(char, '')

            # Step 4: Handle Chinese text specifically
            chinese_char_count = sum(1 for char in cleaned_text if '\u4e00' <= char <= '\u9fff')

            if chinese_char_count > 0:
                # For Chinese text, ensure proper spacing and structure
                # Add spaces between Chinese and English/numbers
                import re
                cleaned_text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z0-9])', r'\1 \2', cleaned_text)
                cleaned_text = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fff])', r'\1 \2', cleaned_text)

                # Remove excessive spacing
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

                # Ensure Chinese text doesn't have trailing punctuation that causes issues
                cleaned_text = re.sub(r'[，。！？；：]$', '', cleaned_text)

            # Step 5: General text cleanup
            # Remove excessive whitespace
            cleaned_text = ' '.join(cleaned_text.split())

            # Step 6: Length optimization - 更保守的长度限制以避免narrow()错误
            if len(cleaned_text) > 200:  # 严格限制在200字符以内
                # Truncate very long texts at word boundaries
                if chinese_char_count > 0:
                    # For Chinese text, truncate at sentence boundaries
                    sentences = re.split(r'[。！？]', cleaned_text)
                    if len(sentences) > 1:
                        cleaned_text = '。'.join(sentences[:2]) + '。'
                    else:
                        cleaned_text = cleaned_text[:150] + '...'
                else:
                    cleaned_text = cleaned_text[:197] + '...'
                self.logger.warning(f"Text truncated to {len(cleaned_text)} characters to avoid ChatTTS narrow() error")

            elif len(cleaned_text) < 2:
                # Ensure minimum length
                cleaned_text = "Hello world"
                self.logger.warning("Text too short, replaced with minimal content")

            # Step 7: Final validation and safety checks
            # Ensure text doesn't end with problematic characters
            while cleaned_text and cleaned_text[-1] in '.,;:!?…。，！？；：':
                cleaned_text = cleaned_text[:-1]

            # Ensure we have valid content
            if not cleaned_text or len(cleaned_text.strip()) < 1:
                cleaned_text = "Hello world"

            # Log preprocessing for debugging
            self.logger.debug(f"Text preprocessing: {len(text)} -> {len(cleaned_text)} chars")
            if chinese_char_count > 0:
                self.logger.debug(f"Chinese characters detected: {chinese_char_count}")

            return cleaned_text.strip()

        except Exception as e:
            self.logger.error(f"Text preprocessing failed: {str(e)}")
            # Return safe fallback text
            return "Hello world"

    def _post_process_audio(self, audio_data: np.ndarray, voice_config: VoiceProfile) -> np.ndarray:
        """
        Apply post-processing to audio data.

        Args:
            audio_data: Raw audio data
            voice_config: Voice configuration

        Returns:
            Processed audio data
        """
        try:
            # Apply volume adjustment
            if voice_config.volume != 1.0:
                audio_data = audio_data * voice_config.volume

            # Ensure audio is in proper format
            audio_data = np.clip(audio_data, -1.0, 1.0)

            # Convert to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            return audio_data

        except Exception as e:
            self.logger.warning(f"Audio post-processing failed: {str(e)}")
            return audio_data

    def _convert_audio_format(self, audio_data: np.ndarray, output_format: str,
                            voice_config: VoiceProfile) -> bytes:
        """
        Convert audio data to specified format.

        Args:
            audio_data: Audio data as numpy array
            output_format: Desired output format
            voice_config: Voice configuration

        Returns:
            Audio data as bytes
        """
        try:
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_wav_path = temp_file.name

            try:
                # Save as WAV first
                sf.write(temp_wav_path, audio_data, AUDIO_SAMPLE_RATE)

                # Load with pydub for format conversion
                audio = AudioSegment.from_wav(temp_wav_path)

                # Apply rate adjustment if needed
                if voice_config.rate != 150:  # Default rate
                    # Convert percentage change to playback speed
                    speed_factor = voice_config.rate / 150.0
                    if speed_factor != 1.0:
                        # Change playback speed (this also affects pitch)
                        audio = audio._spawn(audio.raw_data, overrides={
                            "frame_rate": int(audio.frame_rate * speed_factor)
                        }).set_frame_rate(audio.frame_rate)

                # Convert to desired format
                if output_format.lower() == 'mp3':
                    # Set MP3 quality based on configuration
                    bitrate = "192k" if AUDIO_QUALITY == 'high' else "128k" if AUDIO_QUALITY == 'medium' else "96k"
                    buffer = io.BytesIO()
                    audio.export(buffer, format='mp3', bitrate=bitrate)
                    return buffer.getvalue()

                elif output_format.lower() == 'wav':
                    with open(temp_wav_path, 'rb') as f:
                        return f.read()

                elif output_format.lower() == 'ogg':
                    buffer = io.BytesIO()
                    audio.export(buffer, format='ogg')
                    return buffer.getvalue()

                else:
                    # Default to MP3 for unknown formats
                    buffer = io.BytesIO()
                    audio.export(buffer, format='mp3')
                    return buffer.getvalue()

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_wav_path)
                except OSError:
                    pass

        except Exception as e:
            raise TTSError(
                f"Audio format conversion failed: {str(e)}",
                tts_engine=self.engine_name,
                original_error=e
            )

    def save_audio_file(self, audio_data: bytes, filename: str,
                       output_dir: Union[str, Path] = None) -> Path:
        """
        Save audio data to file.

        Args:
            audio_data: Audio data as bytes
            filename: Output filename
            output_dir: Output directory (optional)

        Returns:
            Path to saved file

        Raises:
            FileOperationError: If file saving fails
        """
        try:
            # Determine output directory
            output_dir = Path(output_dir) if output_dir else AUDIO_OUTPUT_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            # Ensure filename has correct extension
            if not filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                filename += f".{AUDIO_FORMAT}"

            # Create full file path
            file_path = output_dir / filename

            # Write audio data
            with open(file_path, 'wb') as f:
                f.write(audio_data)

            self.logger.info(f"Audio file saved: {file_path}")
            return file_path

        except Exception as e:
            raise FileOperationError(
                f"Failed to save audio file: {str(e)}",
                file_path=str(file_path) if 'file_path' in locals() else filename,
                operation='write',
                original_error=e
            )

    def cleanup(self) -> None:
        """Clean up resources used by the TTS engine."""
        try:
            if self._tts_model and hasattr(self._tts_model, 'cleanup'):
                self._tts_model.cleanup()

            self._tts_model = None
            self._is_initialized = False

            self.logger.info("TTS engine cleaned up successfully")

        except Exception as e:
            self.logger.warning(f"Error during TTS engine cleanup: {str(e)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    # Fallback TTS methods removed as requested by user (ChatTTS-only configuration)
    # def _convert_with_gtts(self, text: str, voice_config: VoiceProfile) -> np.ndarray:
    #     """
    #     Convert text to speech using Google TTS (gTTS).
    #
    #     Args:
    #         text: Text to convert
    #         voice_config: Voice configuration
    #
    #     Returns:
    #         Audio data as numpy array
    #
    #     Raises:
    #         TTSError: If gTTS conversion fails
    #     """
    #     try:
    #         import io
    #         from pydub import AudioSegment
    #
    #         # Determine language based on text content
    #         lang = 'en'  # Default
    #         if any('\u4e00' <= char <= '\u9fff' for char in text):
    #             lang = 'zh'  # Chinese
    #         elif any('\u0400' <= char <= '\u04ff' for char in text):
    #             lang = 'ru'  # Russian
    #
    #         # Create gTTS object
    #         tts = gTTS(text=text, lang=lang, slow=False)
    #
    #         # Generate audio to bytes buffer
    #         audio_buffer = io.BytesIO()
    #         tts.write_to_fp(audio_buffer)
    #         audio_buffer.seek(0)
    #
    #         # Convert to numpy array
    #         audio = AudioSegment.from_mp3(audio_buffer)
    #         audio_data = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0
    #
    #         # Convert to stereo if needed
    #         if audio.channels == 2:
    #             audio_data = audio_data.reshape((-1, 2))
    #         else:
    #             audio_data = audio_data.reshape((-1, 1))
    #
    #         return audio_data
    #
    #     except Exception as e:
    #         raise TTSError(f"gTTS conversion failed: {str(e)}", tts_engine='gtts', original_error=e)

    # def _convert_with_pyttsx3(self, text: str, voice_config: VoiceProfile) -> np.ndarray:
    #     """
    #     Convert text to speech using pyttsx3 (offline TTS).
    #
    #     Args:
    #         text: Text to convert
    #         voice_config: Voice configuration
    #
    #     Returns:
    #         Audio data as numpy array
    #
    #     Raises:
    #         TTSError: If pyttsx3 conversion fails
    #     """
    #     try:
    #         import sounddevice as sd
    #         import soundfile as sf
    #
    #         # Initialize pyttsx3 engine
    #         engine = pyttsx3.init()
    #
    #         # Configure voice
    #         voices = engine.getProperty('voices')
    #         if voices:
    #             # Try to find appropriate voice based on gender
    #             if voice_config.gender == 'female' and len(voices) > 1:
    #                 engine.setProperty('voice', voices[1].id)
    #             else:
    #                 engine.setProperty('voice', voices[0].id)
    #
    #         # Set rate (adjust based on voice_config.rate if available)
    #         rate = engine.getProperty('rate')
    #         if hasattr(voice_config, 'rate'):
    #             engine.setProperty('rate', int(rate * voice_config.rate / 150))  # Normalize rate
    #         else:
    #             engine.setProperty('rate', int(rate * 0.9))  # Slightly slower
    #
    #         # Save to temporary file
    #         import tempfile
    #         with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
    #             temp_path = temp_file.name
    #
    #         engine.save_to_file(text, temp_path)
    #         engine.runAndWait()
    #
    #         # Load the audio file
    #         try:
    #             audio_data, sample_rate = sf.read(temp_path)
    #             return audio_data.reshape((-1, 1)) if len(audio_data.shape) == 1 else audio_data
    #         finally:
    #             # Clean up temporary file
    #             import os
    #             try:
    #                 os.unlink(temp_path)
    #             except:
    #                 pass
    #
    #     except Exception as e:
    #         raise TTSError(f"pyttsx3 conversion failed: {str(e)}", tts_engine='pyttsx3', original_error=e)


# Factory function for creating TTS engines
def create_tts_engine(engine: str = None):
    """
    Create a TTS engine instance.

    Args:
        engine: TTS engine type (optional)

    Returns:
        TTS engine instance (either TTSEngine or ChatTTSEngine)
    """
    # Force use of the working ChatTTSEngine
    try:
        # Try direct import first
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from chattts_engine import create_chatts_engine
        chattts_engine = create_chatts_engine("generated_audio")
        if hasattr(chattts_engine, 'chat') and chattts_engine.chat is not None:  # Check if ChatTTS initialized successfully
            print("[INFO] Using ChatTTSEngine (based on success demo)")
            return chattts_engine
        else:
            print("[WARNING] ChatTTSEngine chat instance is None")
    except Exception as e:
        print(f"[WARNING] Failed to initialize ChatTTSEngine: {e}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")

    # Fallback to original TTSEngine
    print("[INFO] Using fallback TTSEngine")
    return TTSEngine(engine)