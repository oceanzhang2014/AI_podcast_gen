"""
Data models for podcast generation system.

This module defines the core data structures used throughout the podcast
generation process, including requests, characters, conversations, and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class RequestStatus(Enum):
    """Status of podcast generation request."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Gender(Enum):
    """Gender options for characters."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Language(Enum):
    """Language options for characters."""
    CHINESE = "chinese"
    ENGLISH = "english"


@dataclass
class Character:
    """Represents a podcast character with personality traits."""
    id: str
    name: str
    gender: Gender
    background: str
    personality: str
    age: Optional[str] = None
    style: Optional[str] = None
    voice_profile: Optional[str] = None
    language: Language = Language.CHINESE

    def __post_init__(self):
        """Validate character data after initialization."""
        if not self.id.strip():
            raise ValueError("Character ID cannot be empty")
        if not self.name.strip():
            raise ValueError("Character name cannot be empty")
        if not self.background.strip():
            raise ValueError("Character background cannot be empty")
        if not self.personality.strip():
            raise ValueError("Character personality cannot be empty")


@dataclass
class ConversationTurn:
    """Represents a single turn in the podcast conversation."""
    round_number: int
    character_id: str
    text: str
    audio_data: Optional[bytes] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate conversation turn data after initialization."""
        if self.round_number <= 0:
            raise ValueError("Round number must be positive")
        if not self.character_id.strip():
            raise ValueError("Character ID cannot be empty")
        if not self.text.strip():
            raise ValueError("Conversation text cannot be empty")


@dataclass
class PodcastRequest:
    """Represents a podcast generation request."""
    topic: str
    participant_count: int
    conversation_rounds: int
    characters: List[Character]
    created_at: datetime = field(default_factory=datetime.now)
    status: RequestStatus = RequestStatus.PENDING

    def __post_init__(self):
        """Validate podcast request data after initialization."""
        if not self.topic.strip():
            raise ValueError("Topic cannot be empty")
        if self.participant_count <= 0:
            raise ValueError("Participant count must be positive")
        if self.conversation_rounds <= 0:
            raise ValueError("Conversation rounds must be positive")
        if len(self.characters) != self.participant_count:
            raise ValueError("Number of characters must match participant count")
        if not self.characters:
            raise ValueError("At least one character is required")


@dataclass
class PodcastResult:
    """Represents the result of a completed podcast generation."""
    request_id: str
    topic: str
    total_duration: float
    file_path: str
    file_size: int
    conversation_turns: List[ConversationTurn]
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate podcast result data after initialization."""
        if not self.request_id.strip():
            raise ValueError("Request ID cannot be empty")
        if not self.topic.strip():
            raise ValueError("Topic cannot be empty")
        if self.total_duration < 0:
            raise ValueError("Total duration cannot be negative")
        if not self.file_path.strip():
            raise ValueError("File path cannot be empty")
        if self.file_size <= 0:
            raise ValueError("File size must be positive")
        if not self.conversation_turns:
            raise ValueError("At least one conversation turn is required")


@dataclass
class VoiceProfile:
    """Represents a TTS voice profile configuration."""
    id: str
    name: str
    gender: Gender
    language: Language
    description: Optional[str] = None

    def __post_init__(self):
        """Validate voice profile data after initialization."""
        if not self.id.strip():
            raise ValueError("Voice profile ID cannot be empty")
        if not self.name.strip():
            raise ValueError("Voice profile name cannot be empty")


# Factory functions for creating model instances
def create_character(character_id: str, name: str, gender: str, background: str,
                   personality: str, language: str = "chinese", age: str = None, style: str = None) -> Character:
    """Create a Character instance with validation."""
    try:
        gender_enum = Gender(gender.lower())
        language_enum = Language(language.lower())
    except ValueError as e:
        raise ValueError(f"Invalid gender or language value: {e}")

    return Character(
        id=character_id,
        name=name,
        gender=gender_enum,
        background=background,
        personality=personality,
        age=age,
        style=style,
        language=language_enum
    )


def create_podcast_request(topic: str, characters: List[Character],
                          conversation_rounds: int) -> PodcastRequest:
    """Create a PodcastRequest instance with validation."""
    return PodcastRequest(
        topic=topic,
        participant_count=len(characters),
        conversation_rounds=conversation_rounds,
        characters=characters
    )


def create_conversation_turn(round_number: int, character_id: str, text: str) -> ConversationTurn:
    """Create a ConversationTurn instance with validation."""
    return ConversationTurn(
        round_number=round_number,
        character_id=character_id,
        text=text
    )


def create_podcast_result(request_id: str, topic: str, file_path: str,
                         file_size: int, conversation_turns: List[ConversationTurn],
                         total_duration: float = 0.0) -> PodcastResult:
    """Create a PodcastResult instance with validation."""
    return PodcastResult(
        request_id=request_id,
        topic=topic,
        total_duration=total_duration,
        file_path=file_path,
        file_size=file_size,
        conversation_turns=conversation_turns
    )