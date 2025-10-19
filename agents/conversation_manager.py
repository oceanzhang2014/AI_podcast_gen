"""
Conversation Manager module for podcast generation system.

This module provides the ConversationManager class that orchestrates multi-character
dialogue generation for podcast conversations. It manages conversation flow,
ensures natural turn-taking between characters, handles conversation round management,
and provides mechanisms for natural conversation conclusions.

Purpose: Orchestrate dialogue between multiple characters with proper flow management
and natural conversation endings.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import time
import uuid
from datetime import datetime

from agents.character_agent import CharacterAgent, ConversationContext
from utils.error_handler import (
    AIAPIError, ValidationError, get_logger,
    handle_errors, ai_api_retry
)


@dataclass
class ConversationState:
    """Represents the current state of a conversation."""
    conversation_id: str
    topic: str
    characters: List[CharacterAgent]
    current_round: int = 1
    max_rounds: int = 10
    is_active: bool = True
    is_concluding: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Conversation history
    dialogue_history: List[Dict[str, Any]] = field(default_factory=list)
    round_summaries: List[str] = field(default_factory=list)

    # Statistics
    total_tokens_used: int = 0
    total_response_time: float = 0.0
    failed_generations: int = 0

    def add_dialogue_entry(self, character_name: str, content: str, round_num: int,
                          response_time: float = 0.0, tokens_used: int = 0):
        """Add a dialogue entry to the conversation history."""
        entry = {
            'id': str(uuid.uuid4()),
            'character': character_name,
            'content': content,
            'round': round_num,
            'timestamp': datetime.now().isoformat(),
            'response_time': response_time,
            'tokens_used': tokens_used
        }
        self.dialogue_history.append(entry)
        self.total_response_time += response_time
        self.total_tokens_used += tokens_used

    def get_current_round_dialogue(self) -> List[Dict[str, Any]]:
        """Get all dialogue entries from the current round."""
        return [entry for entry in self.dialogue_history if entry['round'] == self.current_round]

    def get_recent_dialogue(self, num_entries: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent dialogue entries."""
        return self.dialogue_history[-num_entries:] if self.dialogue_history else []

    def mark_completed(self):
        """Mark the conversation as completed."""
        self.is_active = False
        self.end_time = datetime.now()

    def get_conversation_duration(self) -> float:
        """Get the conversation duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def get_average_response_time(self) -> float:
        """Get the average response time across all dialogue entries."""
        if not self.dialogue_history:
            return 0.0
        return self.total_response_time / len(self.dialogue_history)


@dataclass
class ConversationConfig:
    """Configuration for conversation generation."""
    max_rounds: int = 10
    min_rounds: int = 3
    temperature: float = 0.7
    max_tokens_per_response: int = 200
    enable_auto_conclusion: bool = True
    conclusion_threshold_rounds: int = 2  # Start concluding 2 rounds before max
    retry_failed_responses: bool = True
    max_retries_per_response: int = 2
    response_timeout: float = 30.0

    # Conversation flow control
    randomize_turn_order: bool = False
    enforce_character_balance: bool = True  # Try to balance speaking time
    pause_between_rounds: float = 0.5  # Seconds to pause between rounds

    # Quality control
    min_response_length: int = 10
    max_response_length: int = 300
    validate_responses: bool = True


class ConversationManager:
    """
    Orchestrates multi-character dialogue generation for podcast conversations.

    This class manages the flow of conversation between multiple AI characters,
    ensures proper turn-taking, handles conversation round management, and provides
    mechanisms for natural conversation conclusions.
    """

    def __init__(
        self,
        topic: str,
        characters: List[CharacterAgent],
        config: Optional[ConversationConfig] = None
    ):
        """
        Initialize the conversation manager.

        Args:
            topic: The main topic for the podcast conversation
            characters: List of CharacterAgent instances participating in the conversation
            config: Optional conversation configuration

        Raises:
            ValidationError: If topic is empty or no characters provided
        """
        self.logger = get_logger()

        # Validate inputs
        if not topic or not topic.strip():
            raise ValidationError("Conversation topic cannot be empty", field="topic")

        if not characters or len(characters) < 2:
            raise ValidationError(
                "At least two characters are required for a conversation",
                field="characters",
                value=len(characters) if characters else 0
            )

        # Initialize configuration
        self.config = config or ConversationConfig()

        # Store conversation parameters
        self.topic = topic.strip()
        self.characters = characters
        self.character_names = [char.profile.name for char in characters]

        # Initialize conversation state
        self.conversation_state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            topic=self.topic,
            characters=self.characters,
            max_rounds=self.config.max_rounds
        )

        # Initialize turn management
        self.current_speaker_index = 0
        self.speaker_rotation_order = list(range(len(characters)))

        # Create initial conversation context
        self.conversation_context = ConversationContext(
            topic=self.topic,
            max_rounds=self.config.max_rounds,
            other_characters=[name for name in self.character_names if name != characters[0].profile.name]
        )

        self.logger.info(
            f"ConversationManager initialized for topic '{self.topic}' with "
            f"{len(characters)} characters: {', '.join(self.character_names)}"
        )

    @handle_errors("conversation generation", reraise=True)
    def generate_conversation(self) -> ConversationState:
        """
        Generate a complete conversation between all characters.

        Returns:
            ConversationState with the complete conversation dialogue

        Raises:
            AIAPIError: If AI API calls fail repeatedly
            ValidationError: If conversation parameters are invalid
        """
        self.logger.info(f"Starting conversation generation: {self.conversation_state.conversation_id}")

        try:
            # Generate conversation round by round
            for round_num in range(1, self.config.max_rounds + 1):
                self.conversation_state.current_round = round_num
                self.conversation_context.current_round = round_num

                # Check if we should start concluding the conversation
                if self._should_start_concluding(round_num):
                    self.conversation_state.is_concluding = True
                    self.logger.info(f"Starting conversation conclusion in round {round_num}")

                # Generate dialogue for this round
                self._generate_round_dialogue(round_num)

                # Add small pause between rounds for more natural flow
                if self.config.pause_between_rounds > 0:
                    time.sleep(self.config.pause_between_rounds)

                # Check if conversation should end early
                if self._should_end_early(round_num):
                    self.logger.info(f"Ending conversation early after round {round_num}")
                    break

            # Generate natural conclusion
            if self.config.enable_auto_conclusion:
                self.conclude_conversation()

            # Mark conversation as completed
            self.conversation_state.mark_completed()

            self.logger.info(
                f"Conversation completed: {self.conversation_state.conversation_id} - "
                f"{len(self.conversation_state.dialogue_history)} dialogue entries, "
                f"{self.conversation_state.get_conversation_duration():.2f}s duration"
            )

            return self.conversation_state

        except Exception as e:
            self.logger.error(f"Conversation generation failed: {str(e)}")
            self.conversation_state.mark_completed()
            raise

    def _generate_round_dialogue(self, round_num: int):
        """
        Generate dialogue for a specific round.

        Args:
            round_num: The current round number
        """
        self.logger.debug(f"Generating dialogue for round {round_num}")

        # Determine speaking order for this round
        speaker_order = self._get_speaker_order(round_num)

        # Generate responses from each character
        for character_index in speaker_order:
            character = self.characters[character_index]

            try:
                # Generate character response
                response_start_time = time.time()
                response_content = self._generate_character_response(character, round_num)
                response_time = time.time() - response_start_time

                # Add to conversation history
                self.conversation_state.add_dialogue_entry(
                    character_name=character.profile.name,
                    content=response_content,
                    round_num=round_num,
                    response_time=response_time
                )

                # Update conversation context
                self.conversation_context.add_message(
                    speaker=character.profile.name,
                    content=response_content
                )

                self.logger.debug(
                    f"Generated response from {character.profile.name} in {response_time:.2f}s"
                )

            except Exception as e:
                self.logger.error(f"Failed to generate response from {character.profile.name}: {str(e)}")
                self.conversation_state.failed_generations += 1

                # Try to generate fallback response
                try:
                    fallback_response = character._generate_fallback_response(self.conversation_context)
                    self.conversation_state.add_dialogue_entry(
                        character_name=character.profile.name,
                        content=fallback_response,
                        round_num=round_num,
                        response_time=0.0
                    )
                    self.conversation_context.add_message(
                        speaker=character.profile.name,
                        content=fallback_response
                    )
                except Exception as fallback_error:
                    self.logger.error(f"Fallback response also failed for {character.profile.name}: {str(fallback_error)}")

        # Generate round summary
        round_dialogue = self.conversation_state.get_current_round_dialogue()
        round_summary = self._generate_round_summary(round_dialogue, round_num)
        self.conversation_state.round_summaries.append(round_summary)

    def _generate_character_response(self, character: CharacterAgent, round_num: int) -> str:
        """
        Generate a response from a specific character.

        Args:
            character: The character to generate response for
            round_num: Current round number

        Returns:
            Generated response content
        """
        # Update conversation context with other characters
        self.conversation_context.other_characters = [
            name for name in self.character_names if name != character.profile.name
        ]

        # Add round-specific guidance if concluding
        if self.conversation_state.is_concluding:
            prompt_override = self._build_conclusion_prompt(character.profile.name, round_num)
        else:
            prompt_override = None

        # Generate response with retry logic
        max_attempts = self.config.max_retries_per_response + 1 if self.config.retry_failed_responses else 1

        for attempt in range(max_attempts):
            try:
                response = character.generate_response(
                    context=self.conversation_context,
                    prompt_override=prompt_override
                )

                # Validate response if enabled
                if self.config.validate_responses:
                    if self._validate_character_response(response, character):
                        return response
                    else:
                        self.logger.warning(
                            f"Response validation failed for {character.profile.name}, attempt {attempt + 1}"
                        )
                        if attempt == max_attempts - 1:
                            # Return response anyway after all retries
                            return response
                else:
                    return response

            except Exception as e:
                self.logger.warning(
                    f"Response generation attempt {attempt + 1} failed for {character.profile.name}: {str(e)}"
                )
                if attempt == max_attempts - 1:
                    raise

        # This should not be reached, but just in case
        return character._generate_fallback_response(self.conversation_context)

    def _get_speaker_order(self, round_num: int) -> List[int]:
        """
        Determine the speaking order for the current round.

        Args:
            round_num: Current round number

        Returns:
            List of character indices in speaking order
        """
        if self.config.randomize_turn_order:
            # Randomize order each round
            import random
            order = list(range(len(self.characters)))
            random.shuffle(order)
            return order
        else:
            # Use rotating order
            if round_num == 1:
                # First character speaks first in first round
                return list(range(len(self.characters)))
            else:
                # Rotate order based on previous round
                return self.speaker_rotation_order

    def _should_start_concluding(self, round_num: int) -> bool:
        """
        Determine if the conversation should start concluding.

        Args:
            round_num: Current round number

        Returns:
            True if conversation should start concluding
        """
        if not self.config.enable_auto_conclusion:
            return False

        # Start concluding when approaching max rounds
        rounds_remaining = self.config.max_rounds - round_num
        return rounds_remaining <= self.config.conclusion_threshold_rounds

    def _should_end_early(self, round_num: int) -> bool:
        """
        Determine if the conversation should end early.

        Args:
            round_num: Current round number

        Returns:
            True if conversation should end early
        """
        # Don't end before minimum rounds
        if round_num < self.config.min_rounds:
            return False

        # Check if conversation is getting repetitive
        recent_dialogue = self.conversation_state.get_recent_dialogue(6)
        if len(recent_dialogue) >= 6:
            # Simple check for very short responses (might indicate conversation fatigue)
            avg_length = sum(len(entry['content'].split()) for entry in recent_dialogue[-4:]) / 4
            if avg_length < 15:  # Very short responses
                self.logger.info("Ending conversation early due to short responses")
                return True

        return False

    def _build_conclusion_prompt(self, character_name: str, round_num: int) -> str:
        """
        Build a prompt for generating conclusion responses.

        Args:
            character_name: Name of the character
            round_num: Current round number

        Returns:
            Conclusion prompt string
        """
        prompt_parts = [
            f"Podcast Topic: {self.topic}",
            f"Current Round: {round_num} of {self.config.max_rounds}",
            "",
            "IMPORTANT: This is one of the final rounds of the conversation. Please help wrap up the discussion by:",
            "- Summarizing your key points on this topic",
            "- Providing final thoughts or insights",
            "- Thanking other participants",
            "- Offering a natural conclusion to your contribution",
            "",
            "Keep your response concise and forward-looking, as if naturally concluding a podcast discussion.",
            "",
            f"Remember: You are {character_name}. Speak naturally and authentically."
        ]

        return "\n".join(prompt_parts)

    def _validate_character_response(self, response: str, character: CharacterAgent) -> bool:
        """
        Validate a character response against quality criteria.

        Args:
            response: The response to validate
            character: The character who generated the response

        Returns:
            True if response meets quality criteria
        """
        # Check length constraints
        word_count = len(response.split())
        if word_count < self.config.min_response_length:
            self.logger.warning(f"Response too short: {word_count} words")
            return False

        if word_count > self.config.max_response_length:
            self.logger.warning(f"Response too long: {word_count} words")
            return False

        # Use character's built-in validation
        return character.validate_response(response)

    def _generate_round_summary(self, round_dialogue: List[Dict[str, Any]], round_num: int) -> str:
        """
        Generate a summary of the current round's dialogue.

        Args:
            round_dialogue: List of dialogue entries for this round
            round_num: Round number

        Returns:
            Round summary string
        """
        if not round_dialogue:
            return f"Round {round_num}: No dialogue generated"

        participants = [entry['character'] for entry in round_dialogue]
        participant_str = ", ".join(participants)

        return f"Round {round_num}: Discussion with {participant_str}"

    @handle_errors("conversation conclusion", reraise=True)
    def conclude_conversation(self) -> Dict[str, str]:
        """
        Generate natural conversation conclusions from each character.

        Returns:
            Dictionary mapping character names to their conclusion statements
        """
        self.logger.info("Generating conversation conclusions")

        conclusions = {}

        for character in self.characters:
            try:
                # Build conclusion prompt
                conclusion_prompt = self._build_final_conclusion_prompt(character.profile.name)

                # Update context to indicate final conclusion
                original_round = self.conversation_context.current_round
                self.conversation_context.current_round = self.config.max_rounds + 1

                # Generate conclusion
                conclusion = character.generate_response(
                    context=self.conversation_context,
                    prompt_override=conclusion_prompt
                )

                conclusions[character.profile.name] = conclusion

                # Add to conversation history
                self.conversation_state.add_dialogue_entry(
                    character_name=character.profile.name,
                    content=conclusion,
                    round_num=self.config.max_rounds + 1,
                    response_time=0.0
                )

                # Restore original round number
                self.conversation_context.current_round = original_round

                self.logger.debug(f"Generated conclusion from {character.profile.name}")

            except Exception as e:
                self.logger.error(f"Failed to generate conclusion from {character.profile.name}: {str(e)}")
                # Use fallback conclusion
                fallback = f"Thank you for this discussion on {self.topic}. It's been great sharing my perspective."
                conclusions[character.profile.name] = fallback

        return conclusions

    def _build_final_conclusion_prompt(self, character_name: str) -> str:
        """
        Build a prompt for final conclusion statements.

        Args:
            character_name: Name of the character

        Returns:
            Final conclusion prompt string
        """
        prompt_parts = [
            f"Podcast Topic: {self.topic}",
            "",
            "This is the FINAL opportunity to speak in this podcast conversation. Please provide a brief, natural closing statement that:",
            "- Summarizes your main contribution to the discussion",
            "- Thanks the other participants and listeners",
            "- Provides a sense of closure to the podcast episode",
            "- Stays true to your character's personality and perspective",
            "",
            "Keep it concise and authentic, as if wrapping up a real podcast episode.",
            "",
            f"Remember: You are {character_name}. This is your final word on this topic."
        ]

        return "\n".join(prompt_parts)

    def get_conversation_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the conversation.

        Returns:
            Dictionary with conversation statistics
        """
        if not self.conversation_state.dialogue_history:
            return {}

        # Character-specific statistics
        character_stats = {}
        for character_name in self.character_names:
            character_entries = [
                entry for entry in self.conversation_state.dialogue_history
                if entry['character'] == character_name
            ]

            if character_entries:
                total_words = sum(len(entry['content'].split()) for entry in character_entries)
                avg_response_time = sum(entry['response_time'] for entry in character_entries) / len(character_entries)

                character_stats[character_name] = {
                    'total_responses': len(character_entries),
                    'total_words': total_words,
                    'average_words_per_response': total_words / len(character_entries),
                    'average_response_time': avg_response_time,
                    'first_response_round': character_entries[0]['round'],
                    'last_response_round': character_entries[-1]['round']
                }

        return {
            'conversation_id': self.conversation_state.conversation_id,
            'topic': self.topic,
            'total_rounds': self.conversation_state.current_round,
            'max_rounds': self.config.max_rounds,
            'total_dialogue_entries': len(self.conversation_state.dialogue_history),
            'total_words_spoken': sum(len(entry['content'].split()) for entry in self.conversation_state.dialogue_history),
            'conversation_duration': self.conversation_state.get_conversation_duration(),
            'average_response_time': self.conversation_state.get_average_response_time(),
            'failed_generations': self.conversation_state.failed_generations,
            'success_rate': ((len(self.conversation_state.dialogue_history) - self.conversation_state.failed_generations) /
                           max(1, len(self.conversation_state.dialogue_history))) * 100,
            'character_statistics': character_stats,
            'is_completed': not self.conversation_state.is_active
        }

    def export_conversation(self, format_type: str = "dict") -> Union[Dict[str, Any], str]:
        """
        Export the conversation in the specified format.

        Args:
            format_type: Export format ('dict', 'json', 'transcript')

        Returns:
            Conversation data in the specified format
        """
        export_data = {
            'conversation_id': self.conversation_state.conversation_id,
            'topic': self.topic,
            'characters': [
                {
                    'name': char.profile.name,
                    'gender': char.profile.gender,
                    'background': char.profile.background,
                    'personality': char.profile.personality
                }
                for char in self.characters
            ],
            'configuration': {
                'max_rounds': self.config.max_rounds,
                'temperature': self.config.temperature,
                'enable_auto_conclusion': self.config.enable_auto_conclusion
            },
            'dialogue': self.conversation_state.dialogue_history,
            'statistics': self.get_conversation_statistics(),
            'created_at': self.conversation_state.start_time.isoformat(),
            'completed_at': self.conversation_state.end_time.isoformat() if self.conversation_state.end_time else None
        }

        if format_type == "dict":
            return export_data
        elif format_type == "json":
            import json
            return json.dumps(export_data, indent=2)
        elif format_type == "transcript":
            return self._format_transcript(export_data)
        else:
            raise ValidationError(f"Unsupported export format: {format_type}")

    def _format_transcript(self, conversation_data: Dict[str, Any]) -> str:
        """
        Format conversation data as a readable transcript.

        Args:
            conversation_data: Complete conversation data

        Returns:
            Formatted transcript string
        """
        lines = []
        lines.append(f"PODCAST TRANSCRIPT")
        lines.append(f"Topic: {conversation_data['topic']}")
        lines.append(f"Conversation ID: {conversation_data['conversation_id']}")
        lines.append(f"Participants: {', '.join([char['name'] for char in conversation_data['characters']])}")
        lines.append(f"Generated: {conversation_data['created_at']}")
        lines.append("=" * 80)
        lines.append("")

        # Group dialogue by round
        current_round = 1
        for entry in conversation_data['dialogue']:
            if entry['round'] != current_round:
                current_round = entry['round']
                lines.append("")
                lines.append(f"--- ROUND {current_round} ---")
                lines.append("")

            lines.append(f"{entry['character']}: {entry['content']}")

        # Add statistics
        lines.append("")
        lines.append("=" * 80)
        lines.append("CONVERSATION STATISTICS")
        lines.append(f"Total rounds: {conversation_data['statistics']['total_rounds']}")
        lines.append(f"Total dialogue entries: {conversation_data['statistics']['total_dialogue_entries']}")
        lines.append(f"Total words: {conversation_data['statistics']['total_words_spoken']}")
        lines.append(f"Duration: {conversation_data['statistics']['conversation_duration']:.2f} seconds")

        return "\n".join(lines)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up resources."""
        try:
            # Close all character agents
            for character in self.characters:
                character.close()
        except Exception as e:
            self.logger.error(f"Error closing conversation manager: {str(e)}")

    def __repr__(self) -> str:
        """String representation of the conversation manager."""
        return (
            f"ConversationManager(id='{self.conversation_state.conversation_id}', "
            f"topic='{self.topic}', characters={len(self.characters)})"
        )