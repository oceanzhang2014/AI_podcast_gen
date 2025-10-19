"""
Voice Manager for podcast generation system.

This module provides intelligent voice selection and configuration for TTS synthesis,
mapping character traits to appropriate voice profiles with support for multiple
languages and personality types.

Purpose: Map character traits to appropriate TTS voices.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

# Import existing components
from utils.models import Gender, Language, Character
from utils.validators import ValidationError, validate_gender, validate_language
from utils.error_handler import get_logger, handle_errors

# Import configuration with fallback defaults for testing
try:
    from config import (
        VOICE_PROFILES, CHATTTS_VOICE_PRESETS, TTS_VOICE_RATE, TTS_VOICE_VOLUME,
        CHATTTS_TEMPERATURE, CHATTTS_TOP_P, CHATTTS_TOP_K
    )
except (ValueError, ImportError):
    # Fallback defaults for testing/development
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
    CHATTTS_VOICE_PRESETS = {}
    TTS_VOICE_RATE = 150
    TTS_VOICE_VOLUME = 0.9
    CHATTTS_TEMPERATURE = 0.3
    CHATTTS_TOP_P = 0.7
    CHATTTS_TOP_K = 20


@dataclass
class VoiceSelection:
    """Represents a selected voice configuration for TTS synthesis."""

    voice_id: str
    gender: Gender
    personality: str
    language: Language
    rate: int
    volume: float
    seed: Optional[int] = None

    # ChatTTS specific parameters
    temperature: Optional[float] = None
    top_P: Optional[float] = None
    top_K: Optional[int] = None
    prompt: Optional[str] = None

    # Additional voice characteristics
    pitch_adjustment: float = 1.0
    emphasis_strength: float = 1.0


class VoiceManager:
    """
    Voice manager for intelligent voice selection and configuration.

    This class provides methods to select appropriate voice profiles based on
    character traits, configure voice parameters, and ensure consistency across
    the podcast generation process.
    """

    def __init__(self):
        """Initialize the voice manager."""
        self.logger = get_logger()
        self._validate_voice_profiles()
        self.logger.info("Voice manager initialized successfully")

    def _validate_voice_profiles(self) -> None:
        """
        Validate that voice profiles are properly configured.

        Raises:
            ConfigurationError: If voice profiles are invalid
        """
        if not VOICE_PROFILES:
            raise ValidationError("No voice profiles configured")

        required_genders = ['male', 'female', 'other']
        for gender in required_genders:
            if gender not in VOICE_PROFILES:
                self.logger.warning(f"Missing voice profiles for gender: {gender}")

        # Validate each voice profile has required parameters
        for gender, personalities in VOICE_PROFILES.items():
            for personality, config in personalities.items():
                required_params = ['rate', 'volume']
                for param in required_params:
                    if param not in config:
                        self.logger.warning(
                            f"Voice profile {gender}_{personality} missing parameter: {param}"
                        )

    @handle_errors("voice selection", reraise=True)
    def select_voice(self, gender: Union[str, Gender], personality: str,
                    language: Union[str, Language] = Language.CHINESE) -> VoiceSelection:
        """
        Select optimal voice based on gender, personality, and language.

        Args:
            gender: Character gender (string or Gender enum)
            personality: Character personality traits
            language: Character language (string or Language enum)

        Returns:
            VoiceSelection with optimal voice configuration

        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate inputs
        validated_gender = validate_gender(gender) if isinstance(gender, str) else gender
        validated_language = validate_language(language) if isinstance(language, str) else language

        if not personality or not isinstance(personality, str):
            raise ValidationError("Personality must be a non-empty string")

        personality = personality.strip().lower()

        # Map personality to standard categories
        mapped_personality = self._map_personality(personality)

        # Find matching voice profile
        voice_profile = self._find_voice_profile(validated_gender, mapped_personality)

        # Create voice selection
        voice_selection = self._create_voice_selection(
            validated_gender, mapped_personality, validated_language, voice_profile
        )

        self.logger.info(
            f"Selected voice: {voice_selection.voice_id} "
            f"for {validated_gender.value} {mapped_personality} character "
            f"speaking {validated_language.value}"
        )

        return voice_selection

    def _map_personality(self, personality: str) -> str:
        """
        Map free-form personality description to standard categories.

        Args:
            personality: Personality description string

        Returns:
            Standardized personality category
        """
        # Personality keyword mappings
        personality_mappings = {
            'professional': ['professional', 'formal', 'business', 'academic', 'expert', 'serious', 'official'],
            'casual': ['casual', 'informal', 'friendly', 'relaxed', 'conversational', 'normal', 'regular'],
            'energetic': ['energetic', 'enthusiastic', 'excited', 'lively', 'dynamic', 'passionate', 'bold'],
            'calm': ['calm', 'gentle', 'soothing', 'quiet', 'soft', 'peaceful', 'mellow', 'relaxed'],
            'neutral': ['neutral', 'balanced', 'moderate', 'standard', 'default']
        }

        personality_lower = personality.lower()

        # Find best matching category
        best_match = 'neutral'  # Default fallback
        best_score = 0

        for category, keywords in personality_mappings.items():
            score = sum(1 for keyword in keywords if keyword in personality_lower)
            if score > best_score:
                best_score = score
                best_match = category

        # If no keywords match, try to infer from tone indicators
        if best_score == 0:
            if any(word in personality_lower for word in ['!', 'excited', 'love', 'amazing']):
                best_match = 'energetic'
            elif any(word in personality_lower for word in ['calm', 'peace', 'quiet']):
                best_match = 'calm'
            elif any(word in personality_lower for word in ['professional', 'work', 'business']):
                best_match = 'professional'
            else:
                best_match = 'casual'

        self.logger.debug(f"Mapped personality '{personality}' to '{best_match}'")
        return best_match

    def _find_voice_profile(self, gender: Gender, personality: str) -> Dict[str, Any]:
        """
        Find matching voice profile configuration.

        Args:
            gender: Validated gender enum
            personality: Mapped personality category

        Returns:
            Voice profile configuration dictionary

        Raises:
            ValidationError: If no matching profile found
        """
        gender_key = gender.value

        # Try to find exact match
        if (gender_key in VOICE_PROFILES and
            personality in VOICE_PROFILES[gender_key]):
            return VOICE_PROFILES[gender_key][personality]

        # Fallback strategies
        # 1. Try neutral personality for same gender
        if (gender_key in VOICE_PROFILES and
            'neutral' in VOICE_PROFILES[gender_key]):
            self.logger.warning(
                f"Personality '{personality}' not found for {gender_key}, "
                f"using neutral profile"
            )
            return VOICE_PROFILES[gender_key]['neutral']

        # 2. Try professional personality for same gender
        if (gender_key in VOICE_PROFILES and
            'professional' in VOICE_PROFILES[gender_key]):
            self.logger.warning(
                f"Personality '{personality}' not found for {gender_key}, "
                f"using professional profile"
            )
            return VOICE_PROFILES[gender_key]['professional']

        # 3. Try other gender with same personality
        for other_gender in VOICE_PROFILES:
            if personality in VOICE_PROFILES[other_gender]:
                self.logger.warning(
                    f"Gender {gender_key} not found for personality '{personality}', "
                    f"using {other_gender} profile"
                )
                return VOICE_PROFILES[other_gender][personality]

        # 4. Final fallback to other/neutral
        if 'other' in VOICE_PROFILES and 'neutral' in VOICE_PROFILES['other']:
            self.logger.warning(
                f"No matching profile found, using other/neutral fallback"
            )
            return VOICE_PROFILES['other']['neutral']

        # 5. Hardcoded fallback
        self.logger.error("No voice profiles available, using hardcoded fallback")
        return {
            'rate': TTS_VOICE_RATE,
            'volume': TTS_VOICE_VOLUME,
            'chattts_seed': 555
        }

    def _create_voice_selection(self, gender: Gender, personality: str,
                              language: Language, voice_profile: Dict[str, Any]) -> VoiceSelection:
        """
        Create VoiceSelection object from profile configuration.

        Args:
            gender: Validated gender enum
            personality: Mapped personality category
            language: Validated language enum
            voice_profile: Voice profile configuration

        Returns:
            VoiceSelection object
        """
        voice_id = f"{gender.value}_{personality}"

        # Base voice parameters from profile
        rate = voice_profile.get('rate', TTS_VOICE_RATE)
        volume = voice_profile.get('volume', TTS_VOICE_VOLUME)
        seed = voice_profile.get('chattts_seed')

        # Create base voice selection
        voice_selection = VoiceSelection(
            voice_id=voice_id,
            gender=gender,
            personality=personality,
            language=language,
            rate=rate,
            volume=volume,
            seed=seed
        )

        # Add ChatTTS preset parameters if available
        preset_key = f"{gender.value}_{personality}"
        if preset_key in CHATTTS_VOICE_PRESETS:
            preset = CHATTTS_VOICE_PRESETS[preset_key]
            voice_selection.temperature = preset.get('temperature', CHATTTS_TEMPERATURE)
            voice_selection.top_P = preset.get('top_P', CHATTTS_TOP_P)
            voice_selection.top_K = preset.get('top_K', CHATTTS_TOP_K)
            voice_selection.prompt = preset.get('prompt')
        else:
            # Use default ChatTTS parameters
            voice_selection.temperature = CHATTTS_TEMPERATURE
            voice_selection.top_P = CHATTTS_TOP_P
            voice_selection.top_K = CHATTTS_TOP_K

        return voice_selection

    @handle_errors("voice configuration", reraise=True)
    def configure_voice_parameters(self, voice_selection: VoiceSelection,
                                 custom_params: Optional[Dict[str, Any]] = None) -> VoiceSelection:
        """
        Configure and customize voice parameters based on character traits.

        Args:
            voice_selection: Base voice selection to customize
            custom_params: Optional custom parameters to apply

        Returns:
            Configured VoiceSelection with customized parameters

        Raises:
            ValidationError: If parameters are invalid
        """
        if not isinstance(voice_selection, VoiceSelection):
            raise ValidationError("voice_selection must be a VoiceSelection object")

        # Create a copy to avoid modifying the original
        configured_voice = VoiceSelection(
            voice_id=voice_selection.voice_id,
            gender=voice_selection.gender,
            personality=voice_selection.personality,
            language=voice_selection.language,
            rate=voice_selection.rate,
            volume=voice_selection.volume,
            seed=voice_selection.seed,
            temperature=voice_selection.temperature,
            top_P=voice_selection.top_P,
            top_K=voice_selection.top_K,
            prompt=voice_selection.prompt,
            pitch_adjustment=voice_selection.pitch_adjustment,
            emphasis_strength=voice_selection.emphasis_strength
        )

        # Apply language-specific adjustments
        configured_voice = self._apply_language_adjustments(configured_voice)

        # Apply personality-specific enhancements
        configured_voice = self._apply_personality_enhancements(configured_voice)

        # Apply custom parameters if provided
        if custom_params:
            configured_voice = self._apply_custom_parameters(configured_voice, custom_params)

        # Validate final configuration
        self._validate_voice_configuration(configured_voice)

        self.logger.debug(f"Configured voice parameters for {configured_voice.voice_id}")
        return configured_voice

    def _apply_language_adjustments(self, voice_selection: VoiceSelection) -> VoiceSelection:
        """
        Apply language-specific voice adjustments.

        Args:
            voice_selection: Voice selection to adjust

        Returns:
            Adjusted voice selection
        """
        if voice_selection.language == Language.CHINESE:
            # Chinese speech typically benefits from slightly slower rate
            voice_selection.rate = int(voice_selection.rate * 0.95)
            # Slightly lower temperature for more stable Chinese pronunciation
            if voice_selection.temperature:
                voice_selection.temperature *= 0.9
        elif voice_selection.language == Language.ENGLISH:
            # English speech can handle slightly faster rate
            voice_selection.rate = int(voice_selection.rate * 1.05)
            # Slightly higher temperature for more expressive English
            if voice_selection.temperature:
                voice_selection.temperature *= 1.1

        return voice_selection

    def _apply_personality_enhancements(self, voice_selection: VoiceSelection) -> VoiceSelection:
        """
        Apply personality-specific voice enhancements.

        Args:
            voice_selection: Voice selection to enhance

        Returns:
            Enhanced voice selection
        """
        if voice_selection.personality == 'energetic':
            # Increase rate and volume for energetic personalities
            voice_selection.rate = int(voice_selection.rate * 1.1)
            voice_selection.volume = min(1.0, voice_selection.volume * 1.1)
            voice_selection.emphasis_strength = 1.2
            # Higher temperature for more variation
            if voice_selection.temperature:
                voice_selection.temperature *= 1.2

        elif voice_selection.personality == 'calm':
            # Decrease rate for calm personalities
            voice_selection.rate = int(voice_selection.rate * 0.9)
            voice_selection.emphasis_strength = 0.8
            # Lower temperature for more consistency
            if voice_selection.temperature:
                voice_selection.temperature *= 0.8

        elif voice_selection.personality == 'professional':
            # Moderate adjustments for professional speech
            voice_selection.emphasis_strength = 1.0
            # Standard temperature for clear speech
            if voice_selection.temperature:
                voice_selection.temperature = max(0.2, voice_selection.temperature * 0.9)

        elif voice_selection.personality == 'casual':
            # Natural conversational adjustments
            voice_selection.emphasis_strength = 1.1
            # Moderate temperature for natural variation
            if voice_selection.temperature:
                voice_selection.temperature *= 1.05

        return voice_selection

    def _apply_custom_parameters(self, voice_selection: VoiceSelection,
                               custom_params: Dict[str, Any]) -> VoiceSelection:
        """
        Apply custom parameters to voice selection.

        Args:
            voice_selection: Voice selection to modify
            custom_params: Custom parameters to apply

        Returns:
            Modified voice selection
        """
        # Validate and apply rate adjustment
        if 'rate_adjustment' in custom_params:
            adjustment = custom_params['rate_adjustment']
            if isinstance(adjustment, (int, float)) and 0.5 <= adjustment <= 2.0:
                voice_selection.rate = int(voice_selection.rate * adjustment)
            else:
                self.logger.warning(f"Invalid rate_adjustment: {adjustment}")

        # Validate and apply volume adjustment
        if 'volume_adjustment' in custom_params:
            adjustment = custom_params['volume_adjustment']
            if isinstance(adjustment, (int, float)) and 0.5 <= adjustment <= 1.5:
                voice_selection.volume = min(1.0, voice_selection.volume * adjustment)
            else:
                self.logger.warning(f"Invalid volume_adjustment: {adjustment}")

        # Validate and apply pitch adjustment
        if 'pitch_adjustment' in custom_params:
            adjustment = custom_params['pitch_adjustment']
            if isinstance(adjustment, (int, float)) and 0.5 <= adjustment <= 2.0:
                voice_selection.pitch_adjustment = adjustment
            else:
                self.logger.warning(f"Invalid pitch_adjustment: {adjustment}")

        # Apply custom ChatTTS parameters
        chattts_params = ['temperature', 'top_P', 'top_K']
        for param in chattts_params:
            if param in custom_params:
                value = custom_params[param]
                if isinstance(value, (int, float)) and 0.0 <= value <= 1.0:
                    setattr(voice_selection, param, value)
                else:
                    self.logger.warning(f"Invalid {param}: {value}")

        # Apply custom prompt
        if 'custom_prompt' in custom_params:
            prompt = custom_params['custom_prompt']
            if isinstance(prompt, str) and len(prompt.strip()) > 0:
                voice_selection.prompt = prompt.strip()
            else:
                self.logger.warning("Invalid custom_prompt: must be non-empty string")

        return voice_selection

    def _validate_voice_configuration(self, voice_selection: VoiceSelection) -> None:
        """
        Validate voice configuration parameters.

        Args:
            voice_selection: Voice selection to validate

        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate rate
        if not isinstance(voice_selection.rate, int) or voice_selection.rate < 50 or voice_selection.rate > 300:
            raise ValidationError("Voice rate must be between 50 and 300 words per minute")

        # Validate volume
        if not isinstance(voice_selection.volume, (int, float)) or voice_selection.volume < 0.0 or voice_selection.volume > 1.0:
            raise ValidationError("Voice volume must be between 0.0 and 1.0")

        # Validate ChatTTS parameters
        if voice_selection.temperature is not None:
            if not isinstance(voice_selection.temperature, (int, float)) or voice_selection.temperature < 0.0 or voice_selection.temperature > 1.0:
                raise ValidationError("Temperature must be between 0.0 and 1.0")

        if voice_selection.top_P is not None:
            if not isinstance(voice_selection.top_P, (int, float)) or voice_selection.top_P < 0.0 or voice_selection.top_P > 1.0:
                raise ValidationError("top_P must be between 0.0 and 1.0")

        if voice_selection.top_K is not None:
            if not isinstance(voice_selection.top_K, int) or voice_selection.top_K < 1 or voice_selection.top_K > 100:
                raise ValidationError("top_K must be between 1 and 100")

    def get_available_voices(self, language: Optional[Union[str, Language]] = None) -> List[Dict[str, Any]]:
        """
        Get list of available voice configurations.

        Args:
            language: Optional language filter

        Returns:
            List of available voice configurations
        """
        available_voices = []

        validated_language = None
        if language:
            validated_language = validate_language(language) if isinstance(language, str) else language

        for gender_key, personalities in VOICE_PROFILES.items():
            try:
                gender_enum = Gender(gender_key)
            except ValueError:
                continue

            for personality in personalities:
                # Create voice selection
                voice_selection = self.select_voice(gender_enum, personality,
                                                  validated_language or Language.CHINESE)

                voice_info = {
                    'id': voice_selection.voice_id,
                    'name': f"{gender_enum.value.title()} {personality.title()}",
                    'gender': gender_enum.value,
                    'personality': personality,
                    'language': [validated_language.value] if validated_language else ['chinese', 'english'],
                    'rate': voice_selection.rate,
                    'volume': voice_selection.volume,
                    'has_seed': voice_selection.seed is not None,
                    'chattts_params': {
                        'temperature': voice_selection.temperature,
                        'top_P': voice_selection.top_P,
                        'top_K': voice_selection.top_K,
                        'has_prompt': voice_selection.prompt is not None
                    }
                }

                available_voices.append(voice_info)

        return available_voices

    def select_voice_for_character(self, character: Character,
                                 custom_params: Optional[Dict[str, Any]] = None) -> VoiceSelection:
        """
        Select and configure voice for a specific character.

        Args:
            character: Character object
            custom_params: Optional custom parameters

        Returns:
            Configured voice selection for the character
        """
        # Base voice selection
        voice_selection = self.select_voice(
            character.gender,
            character.personality,
            character.language
        )

        # Apply configuration
        configured_voice = self.configure_voice_parameters(voice_selection, custom_params)

        self.logger.info(f"Selected voice '{configured_voice.voice_id}' for character '{character.name}'")
        return configured_voice


# Factory function for creating voice managers
def create_voice_manager() -> VoiceManager:
    """
    Create a VoiceManager instance.

    Returns:
        VoiceManager instance
    """
    return VoiceManager()