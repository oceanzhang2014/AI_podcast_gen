"""
ChatTTS Service

This module provides a dedicated ChatTTS-only service for audio generation.
It uses the ChatTTS Python API directly without any fallback TTS engines,
as requested by the user.
"""

import os
import torch
import logging
import numpy as np
import tempfile
import torio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import ChatTTS
    CHATTTS_AVAILABLE = True
except ImportError:
    CHATTTS_AVAILABLE = False

from utils.error_handler import get_logger, handle_errors


@dataclass
class ChatTTSConfig:
    """Configuration for ChatTTS generation."""
    use_spk_emb: bool = True
    seed: int = 42
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 20
    refine_text: bool = True
    skip_refine_text: bool = False


class ChatTTSService:
    """
    Dedicated ChatTTS service using Python API directly.

    This service only uses ChatTTS without any fallback TTS engines,
    providing the best possible ChatTTS integration.
    """

    def __init__(self, output_dir: str = "generated_audio", device: str = "cuda"):
        """
        Initialize ChatTTS service.

        Args:
            output_dir: Directory to save generated audio files
            device: Device to use ('cuda' or 'cpu')
        """
        self.logger = get_logger()

        if not CHATTTS_AVAILABLE:
            raise ImportError("ChatTTS is not available. Install with: pip install chattts")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize ChatTTS
        self.logger.info("Initializing ChatTTS...")
        self.chat = ChatTTS.Chat()

        # Load models
        self.logger.info("Loading ChatTTS models...")
        success = self.chat.load(
            device=device,
            compile=False  # Disable compilation for faster initialization
        )

        if not success:
            raise RuntimeError("Failed to load ChatTTS models")

        self.logger.info("ChatTTS models loaded successfully")

        # Voice parameter mapping for different character types
        self.voice_params = {
            'male_professional': {'seed': 666, 'temperature': 0.7},
            'male_casual': {'seed': 333, 'temperature': 0.8},
            'male_energetic': {'seed': 999, 'temperature': 0.9},
            'female_professional': {'seed': 2, 'temperature': 0.6},
            'female_casual': {'seed': 777, 'temperature': 0.7},
            'female_energetic': {'seed': 444, 'temperature': 0.8},
        }

        self.device = device
        self.logger.info(f"ChatTTS service initialized on device: {device}")

    def _get_voice_params(self, gender: str, personality: str) -> Dict[str, Any]:
        """
        Get voice parameters based on gender and personality.

        Args:
            gender: 'male' or 'female'
            personality: 'professional', 'casual', 'energetic', etc.

        Returns:
            Dictionary of voice parameters
        """
        voice_type = f"{gender}_{personality}"
        default_params = {'seed': 42, 'temperature': 0.7}

        return self.voice_params.get(voice_type, default_params)

    @handle_errors("ChatTTS audio generation", reraise=True)
    def generate_audio(
        self,
        text: str,
        gender: str,
        personality: str = "professional",
        output_file: Optional[str] = None,
        language: str = "zh"
    ) -> Optional[str]:
        """
        Generate audio using ChatTTS Python API.

        Args:
            text: Text to convert to speech
            gender: 'male' or 'female'
            personality: Personality type (professional, casual, energetic, etc.)
            output_file: Optional output filename
            language: Language code (zh, en, etc.)

        Returns:
            Path to generated audio file, or None if failed
        """
        try:
            self.logger.info(f"Generating ChatTTS audio for {gender} {personality} character")

            # Generate output filename if not provided
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"chattts_{gender}_{personality}_{timestamp}.wav"

            output_path = self.output_dir / output_file

            # Get voice parameters
            voice_params = self._get_voice_params(gender, personality)
            seed = voice_params['seed']
            temperature = voice_params['temperature']

            # Prepare text for ChatTTS
            if language == 'zh' and not any('\u4e00' <= char <= '\u9fff' for char in text):
                # For Chinese language preference, add Chinese characters if needed
                text = text + "，谢谢。"

            # Log generation parameters
            self.logger.info(f"ChatTTS generation params: seed={seed}, temperature={temperature}")
            self.logger.info(f"Text to synthesize: {text[:100]}...")

            # Set seed for reproducibility
            torch.manual_seed(seed)
            np.random.seed(seed)

            # Generate audio using ChatTTS
            with torch.no_grad():
                # Refine text if enabled
                if not self.chat.skip_refine_text:
                    refined_text = self.chat.infer(text,
                                               skip_refine_text=False,
                                               refine_text_only=True)
                    if refined_text and len(refined_text) > 0:
                        text = refined_text[0]
                        self.logger.info(f"Refined text: {text}")

                # Generate audio
                wavs = self.chat.infer(text,
                                      use_decoder=True,
                                      skip_refine_text=self.chat.skip_refine_text,
                                      do_text_normalization=True,
                                      do_homophone_replacement=True)

                if not wavs or len(wavs) == 0:
                    raise RuntimeError("ChatTTS failed to generate audio")

                audio_data = wavs[0]

            # Save audio to file using torio
            sample_rate = 24000  # ChatTTS default sample rate

            # Ensure audio data is in the right format
            if isinstance(audio_data, torch.Tensor):
                if audio_data.dim() == 1:
                    audio_data = audio_data.unsqueeze(0)  # Add channel dimension if needed
                audio_data = audio_data.cpu().numpy()

            # Save using scipy or soundfile (more reliable than torio)
            try:
                import soundfile as sf
                # Ensure audio data is in the right format
                if isinstance(audio_data, torch.Tensor):
                    audio_data = audio_data.cpu().numpy()
                if audio_data.shape[0] == 1:  # Remove channel dimension if mono
                    audio_data = audio_data[0]
                sf.write(str(output_path), audio_data, sample_rate)
            except ImportError:
                # Fallback to scipy
                try:
                    from scipy.io import wavfile
                    if isinstance(audio_data, torch.Tensor):
                        audio_data = audio_data.cpu().numpy()
                    if audio_data.shape[0] == 1:
                        audio_data = audio_data[0]
                    # Convert to int16 for wav file
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    wavfile.write(str(output_path), sample_rate, audio_int16)
                except ImportError:
                    # Last resort: use pydub
                    try:
                        from pydub import AudioSegment
                        # Convert numpy to audio segment
                        if isinstance(audio_data, torch.Tensor):
                            audio_data = audio_data.cpu().numpy()
                        if audio_data.shape[0] == 1:
                            audio_data = audio_data[0]
                        # Normalize to 16-bit PCM
                        audio_normalized = np.int16(audio_data * 32767)
                        audio_segment = AudioSegment(
                            audio_normalized.tobytes(),
                            frame_rate=sample_rate,
                            sample_width=2,
                            channels=1
                        )
                        audio_segment.export(str(output_path), format="wav")
                    except Exception as save_error:
                        raise RuntimeError(f"Failed to save audio with any method: {save_error}")

            # Verify file was created
            if not output_path.exists():
                raise RuntimeError("Audio file was not created")

            file_size = output_path.stat().st_size
            self.logger.info(f"ChatTTS generation successful: {output_path} ({file_size} bytes)")

            return str(output_path)

        except Exception as e:
            self.logger.error(f"ChatTTS generation failed: {str(e)}")
            raise

    def set_voice_params(self, voice_type: str, params: Dict[str, Any]) -> None:
        """
        Set custom voice parameters for a voice type.

        Args:
            voice_type: Voice type identifier (e.g., 'male_professional')
            params: Dictionary of parameters (seed, temperature, etc.)
        """
        self.voice_params[voice_type] = params
        self.logger.info(f"Updated voice parameters for {voice_type}")

    def list_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of available voice configurations.

        Returns:
            Dictionary of voice types and their parameters
        """
        return self.voice_params.copy()

    def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self, 'chat'):
            del self.chat
        self.logger.info("ChatTTS service cleaned up")


def create_chattts_service(
    output_dir: str = "generated_audio",
    device: str = "cuda"
) -> ChatTTSService:
    """
    Create a ChatTTS service instance.

    Args:
        output_dir: Directory to save generated audio files
        device: Device to use ('cuda' or 'cpu')

    Returns:
        ChatTTSService instance
    """
    return ChatTTSService(output_dir=output_dir, device=device)


# Test function
def test_chattts_service():
    """Test the ChatTTS service."""
    try:
        service = create_chattts_service()

        # Test generation
        test_text = "你好，这是一个测试。Hello, this is a test."
        result = service.generate_audio(test_text, "female", "professional", "test_chattts.wav")

        if result:
            print(f"✅ ChatTTS test successful: {result}")
            return True
        else:
            print("❌ ChatTTS test failed")
            return False

    except Exception as e:
        print(f"❌ ChatTTS test error: {e}")
        return False


if __name__ == "__main__":
    test_chattts_service()