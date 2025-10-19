"""
Subprocess-based TTS Service

Simplified TTS service using subprocess calls to ChatTTS CLI
instead of complex Python API integration. Based on talk.py approach.
"""

import subprocess
import shlex
import os
import tempfile
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import intelligent seed selector
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from seed_database import get_best_seed_for_character
    SEED_SELECTOR_AVAILABLE = True
    print("[INFO] Intelligent seed selector available for subprocess service")
except ImportError as e:
    SEED_SELECTOR_AVAILABLE = False
    print(f"[WARNING] Intelligent seed selector not available for subprocess service: {e}")

# Import ChatTTS for direct API usage
try:
    import ChatTTS
    import torch
    import torchaudio
    CHATTTS_AVAILABLE = True
    print("[INFO] ChatTTS Python API available")
except ImportError as e:
    CHATTTS_AVAILABLE = False
    print(f"[WARNING] ChatTTS Python API not available: {e}")

# Import fallback TTS options
try:
    from gtts import gTTS
    import io
    from pydub import AudioSegment
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class SubprocessTTSService:
    """
    Subprocess-based TTS service for reliable audio generation.

    Uses ChatTTS CLI calls with fallbacks to gTTS and pyttsx3.
    """

    def __init__(self, output_dir: str = "generated_audio"):
        """
        Initialize the TTS service.

        Args:
            output_dir: Directory to save generated audio files
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize ChatTTS if available
        self.chattts_instance = None
        if CHATTTS_AVAILABLE:
            try:
                self.chattts_instance = ChatTTS.Chat()
                self.chattts_instance.load(compile=False)
                self.logger.info("ChatTTS instance initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize ChatTTS: {e}")
                self.chattts_instance = None

        # Voice parameter mapping based on talk.py
        self.voice_seeds = {
            'female': {
                'young': '2',          # young, emotionally rich
                'middle-aged': '4',     # middle-aged, deeply emotional
                'mature': '1111',      # middle-aged, clear and pure
                'professional': '3333', # middle-aged, calm and serene
                'casual': '2',         # default to young
                'energetic': '2',      # default to young
                'neutral': '1111'      # default to clear
            },
            'male': {
                'young': '111',        # young, literary
                'middle-aged': '333',  # middle-aged, white-collar
                'mature': '7777',      # middle-aged, hong kong-style
                'professional': '666', # middle-aged, white-collar
                'casual': '333',       # default to gentle
                'energetic': '111',    # default to literary
                'neutral': '9999'     # default to deep and resonant
            }
        }

        # Character-to-seed mapping for consistency
        self.character_seed_cache: Dict[str, int] = {}

        self.logger.info("Subprocess TTS service initialized")

    def get_voice_seed(self, gender: str, personality: str) -> str:
        """
        Get ChatTTS seed value based on gender and personality.

        Args:
            gender: Character gender ('male' or 'female')
            personality: Character personality trait

        Returns:
            ChatTTS seed string
        """
        gender_key = gender.lower()
        personality_key = personality.lower()

        # Get seed map for gender
        gender_map = self.voice_seeds.get(gender_key, self.voice_seeds['male'])

        # Return personality-specific seed or default
        return gender_map.get(personality_key, gender_map.get('neutral', '333'))

    def get_character_seed(self, character_name: str, gender: str = None, personality: str = None) -> int:
        """
        Get a consistent seed for a character to ensure voice consistency using intelligent selection.

        Args:
            character_name: Name of the character
            gender: Character gender (optional)
            personality: Character personality (optional)

        Returns:
            Seed integer for ChatTTS
        """
        # Use intelligent seed selector if available
        if SEED_SELECTOR_AVAILABLE:
            try:
                # Map gender to Chinese for seed selector
                gender_cn = None
                if gender:
                    gender_lower = gender.lower()
                    if gender_lower in ['female', '女']:
                        gender_cn = '女'
                    elif gender_lower in ['male', '男']:
                        gender_cn = '男'

                # Map personality to voice preferences for intelligent selection
                voice_preference = personality
                features = []

                if personality:
                    personality_lower = personality.lower()
                    if 'gentle' in personality_lower or '温柔' in personality_lower:
                        features.append('温柔')
                        voice_preference = '温柔'
                    elif 'professional' in personality_lower or '专业' in personality_lower:
                        features.append('知性')
                        voice_preference = '专业'
                    elif 'energetic' in personality_lower or '活力' in personality_lower:
                        features.append('时尚')
                        voice_preference = '时尚'
                    elif 'neutral' in personality_lower or '中性' in personality_lower:
                        features.append('普通')
                        voice_preference = '普通'
                    elif 'mature' in personality_lower or '成熟' in personality_lower:
                        features.append('成熟')
                        voice_preference = '成熟'

                # Use intelligent seed selection
                intelligent_seed = get_best_seed_for_character(
                    character_name=character_name,
                    gender=gender_cn,
                    age='青年',  # Default to young age
                    features=features,
                    voice_preference=voice_preference
                )

                if intelligent_seed:
                    seed_int = int(intelligent_seed)
                    self.logger.info(f"Using intelligent seed '{seed_int}' for character '{character_name}' "
                                   f"(gender: {gender}, personality: {personality})")
                    return seed_int

            except Exception as e:
                self.logger.warning(f"Intelligent seed selection failed: {e}, falling back to hash-based selection")

        # Fallback to hash-based seed generation
        # Check if we already have a seed for this character
        if character_name and character_name in self.character_seed_cache:
            return self.character_seed_cache[character_name]

        # Generate a deterministic seed based on character name
        if character_name:
            # Use hash of character name to generate a consistent seed
            hash_obj = hashlib.md5(character_name.encode())
            hash_int = int(hash_obj.hexdigest(), 16)

            # Map to a reasonable seed range (based on common ChatTTS seeds)
            seed_candidates = [2, 4, 111, 333, 666, 777, 1111, 3333, 9999]
            seed_index = hash_int % len(seed_candidates)
            seed = seed_candidates[seed_index]
        else:
            # Fallback to gender/personality-based seed
            seed_str = self.get_voice_seed(gender or 'male', personality or 'neutral')
            seed = int(seed_str) if seed_str.isdigit() else 1111

        # Cache the seed for this character
        if character_name:
            self.character_seed_cache[character_name] = seed

        self.logger.info(f"Using fallback seed '{seed}' for character '{character_name}' (gender: {gender}, personality: {personality})")
        return seed

    def generate_with_chattts(self, text: str, gender: str, personality: str,
                           output_file: Optional[str] = None, character_name: str = None) -> Optional[str]:
        """
        Generate audio using ChatTTS Python API.

        Args:
            text: Text to convert to speech
            gender: Character gender
            personality: Character personality
            output_file: Optional custom output file path
            character_name: Character name for voice consistency (optional)

        Returns:
            Path to generated audio file, or None if failed
        """
        if not CHATTTS_AVAILABLE or self.chattts_instance is None:
            self.logger.warning("ChatTTS not available, using fallback")
            return None

        try:
            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"chattts_{gender}_{personality}_{timestamp}.wav"

            output_path = self.output_dir / output_file

            # Get voice seed for character (use character name for consistency)
            seed = self.get_character_seed(character_name, gender, personality)

            self.logger.info(f"Generating ChatTTS audio for {gender} {personality} (character: {character_name}, seed: {seed}): {text[:50]}...")

            # Generate audio using ChatTTS with the proven simple approach
            with torch.no_grad():
                wavs = self.chattts_instance.infer([text])

            if wavs and len(wavs) > 0:
                # Convert to tensor and save
                audio_tensor = torch.from_numpy(wavs[0])
                torchaudio.save(str(output_path), audio_tensor.unsqueeze(0), 24000)

                if output_path.exists():
                    file_size = output_path.stat().st_size
                    self.logger.info(f"ChatTTS generation successful: {output_path} ({file_size} bytes)")
                    return str(output_path)
                else:
                    self.logger.error(f"ChatTTS failed to create audio file: {output_path}")
                    return None
            else:
                self.logger.error("ChatTTS returned empty audio")
                return None

        except Exception as e:
            self.logger.error(f"ChatTTS generation error: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_with_gtts(self, text: str, gender: str, personality: str,
                          output_file: Optional[str] = None) -> Optional[str]:
        """
        Generate audio using gTTS as fallback.

        Args:
            text: Text to convert to speech
            gender: Character gender (unused for gTTS)
            personality: Character personality (unused for gTTS)
            output_file: Optional custom output file path

        Returns:
            Path to generated audio file, or None if failed
        """
        if not GTTS_AVAILABLE:
            self.logger.warning("gTTS not available for fallback")
            return None

        try:
            # Determine language based on text content
            lang = 'en'  # Default
            if any('\u4e00' <= char <= '\u9fff' for char in text):
                lang = 'zh'  # Chinese

            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"gtts_{timestamp}.wav"

            output_path = self.output_dir / output_file

            # Generate audio using gTTS
            tts = gTTS(text=text, lang=lang, slow=False)

            # Save to temporary file first
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            tts.save(temp_path)

            # Convert to WAV using PyDub
            audio = AudioSegment.from_mp3(temp_path)
            audio.export(output_path, format="wav")

            # Clean up temporary file
            os.unlink(temp_path)

            self.logger.info(f"gTTS generation successful: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"gTTS generation error: {e}")
            return None

    def generate_with_pyttsx3(self, text: str, gender: str, personality: str,
                              output_file: Optional[str] = None) -> Optional[str]:
        """
        Generate audio using pyttsx3 as fallback.

        Args:
            text: Text to convert to speech
            gender: Character gender
            personality: Character personality
            output_file: Optional custom output file path

        Returns:
            Path to generated audio file, or None if failed
        """
        if not PYTTSX3_AVAILABLE:
            self.logger.warning("pyttsx3 not available for fallback")
            return None

        try:
            # Initialize pyttsx3 engine
            engine = pyttsx3.init()

            # Get available voices
            voices = engine.getProperty('voices')

            # Try to select appropriate voice based on gender
            if voices:
                if gender == 'female' and len(voices) > 1:
                    engine.setProperty('voice', voices[1].id)
                elif voices:
                    engine.setProperty('voice', voices[0].id)

            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"pyttsx3_{timestamp}.wav"

            output_path = self.output_dir / output_file

            # Generate audio
            engine.save_to_file(text, output_path)

            self.logger.info(f"pyttsx3 generation successful: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"pyttsx3 generation error: {e}")
            return None

    def generate_audio(self, text: str, gender: str, personality: str,
                        output_file: Optional[str] = None,
                        preferred_engine: str = 'chattts', character_name: str = None) -> Optional[str]:
        """
        Generate audio using the specified or fallback TTS engines.

        Args:
            text: Text to convert to speech
            gender: Character gender
            personality: Character personality
            output_file: Optional custom output file path
            preferred_engine: Preferred TTS engine ('chattts', 'gtts', 'pyttsx3')
            character_name: Character name for voice consistency (optional)

        Returns:
            Path to generated audio file, or None if all engines fail
        """
        self.logger.info(f"Generating audio for {gender} {personality} character")

        # Try preferred engine first
        engines = [preferred_engine]

        # Add other engines based on availability
        if preferred_engine != 'chattts':
            engines.append('chattts')
        if preferred_engine != 'gtts' and GTTS_AVAILABLE:
            engines.append('gtts')
        if preferred_engine != 'pyttsx3' and PYTTSX3_AVAILABLE:
            engines.append('pyttsx3')

        # Try each engine in order
        for engine in engines:
            self.logger.info(f"Trying {engine} TTS engine")

            if engine == 'chattts':
                result = self.generate_with_chattts(text, gender, personality, output_file, character_name)
            elif engine == 'gtts':
                result = self.generate_with_gtts(text, gender, personality, output_file)
            elif engine == 'pyttsx3':
                result = self.generate_with_pyttsx3(text, gender, personality, output_file)

            if result:
                return result

        self.logger.error("All TTS engines failed to generate audio")
        return None

    def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """
        Clean up temporary audio files.

        Args:
            file_paths: List of file paths to clean up
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up {file_path}: {e}")


# Factory function for creating TTS service
def create_subprocess_tts_service(output_dir: str = "generated_audio") -> SubprocessTTSService:
    """
    Create a subprocess-based TTS service instance.

    Args:
        output_dir: Directory to save generated audio files

    Returns:
        SubprocessTTSService instance
    """
    return SubprocessTTSService(output_dir)