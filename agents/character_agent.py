"""
Character Agent module for podcast generation system.

This module provides the CharacterAgent class that creates AI agents representing
individual podcast characters with distinct personalities, backgrounds, and
communication styles. Each agent maintains character consistency throughout
the conversation while generating contextually appropriate responses.

Purpose: Create AI agents that maintain character personality and generate
personality-consistent dialogue for podcast conversations.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import re
import json

from utils.ai_client import AIMessage, AIResponse, UnifiedAIClient, create_ai_client
from utils.error_handler import (
    AIAPIError, ValidationError, get_logger,
    handle_errors, ai_api_retry
)


@dataclass
class CharacterProfile:
    """Represents a character's profile with personality traits and background."""
    name: str
    gender: str
    background: str
    personality: str
    age: Optional[str] = None
    style: Optional[str] = None
    speaking_style: str = ""
    expertise_areas: List[str] = field(default_factory=list)
    common_phrases: List[str] = field(default_factory=list)
    emotional_tone: str = "neutral"
    communication_level: str = "professional"  # casual, professional, academic

    def __post_init__(self):
        """Validate character profile after initialization."""
        if not self.name or not self.name.strip():
            raise ValidationError("Character name cannot be empty", field="name")

        if not self.gender or self.gender.lower() not in ['male', 'female', 'other']:
            raise ValidationError(
                "Gender must be 'male', 'female', or 'other'",
                field="gender",
                value=self.gender
            )

        if not self.background or not self.background.strip():
            raise ValidationError("Character background cannot be empty", field="background")

        if not self.personality or not self.personality.strip():
            raise ValidationError("Character personality cannot be empty", field="personality")


@dataclass
class ConversationContext:
    """Represents the context of a conversation for generating responses."""
    topic: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    current_round: int = 1
    max_rounds: int = 10
    other_characters: List[str] = field(default_factory=list)
    conversation_goals: List[str] = field(default_factory=list)

    def add_message(self, speaker: str, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append({
            'speaker': speaker,
            'content': content,
            'round': self.current_round
        })

    def get_recent_context(self, num_messages: int = 5) -> List[Dict[str, str]]:
        """Get the most recent messages from conversation history."""
        return self.conversation_history[-num_messages:] if self.conversation_history else []


class CharacterAgent:
    """
    AI agent representing a podcast character with personality-based response generation.

    This class creates and manages AI agents for podcast characters, ensuring that
    generated responses reflect the character's configured personality, background,
    and communication style while maintaining context awareness.
    """

    def __init__(
        self,
        profile: CharacterProfile,
        ai_provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize a character agent.

        Args:
            profile: CharacterProfile containing character details
            ai_provider: Specific AI provider to use (None for automatic selection)
            temperature: AI model temperature for response generation (0.0 to 1.0)
            max_tokens: Maximum tokens in generated responses

        Raises:
            ValidationError: If character profile is invalid
            ConfigurationError: If AI client configuration fails
        """
        self.logger = get_logger()
        self.profile = profile
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Validate profile
        if not isinstance(profile, CharacterProfile):
            raise ValidationError(
                "Profile must be a CharacterProfile instance",
                field="profile",
                value=type(profile).__name__
            )

        # Initialize AI client
        try:
            self.ai_client = create_ai_client(provider=ai_provider)
            self.logger.info(f"Initialized CharacterAgent for '{profile.name}' with AI provider")
        except Exception as e:
            raise AIAPIError(
                f"Failed to initialize AI client for character '{profile.name}': {str(e)}",
                original_error=e
            )

        # Build character system prompt
        self._system_prompt = self._build_character_prompt()

        # Response generation statistics
        self.response_count = 0
        self.validation_failures = 0

        self.logger.info(f"CharacterAgent initialized successfully for '{profile.name}'")

    def _build_character_prompt(self) -> str:
        """
        Build a comprehensive system prompt that defines the character's personality and behavior.

        Returns:
            System prompt string for the AI model
        """
        prompt_parts = [
            f"你是{self.profile.name}，一位播客参与者，具有以下特征：",
            f"",
            f"**性别：** {self.profile.gender}",
            f"**背景：** {self.profile.background}",
            f"**性格：** {self.profile.personality}",
        ]

        # Add speaking style if specified
        if self.profile.speaking_style:
            prompt_parts.append(f"**说话风格：** {self.profile.speaking_style}")

        # Add expertise areas
        if self.profile.expertise_areas:
            areas_str = "、".join(self.profile.expertise_areas)
            prompt_parts.append(f"**专业领域：** {areas_str}")

        # Add common phrases
        if self.profile.common_phrases:
            phrases_str = "、".join(f'"{phrase}"' for phrase in self.profile.common_phrases)
            prompt_parts.append(f"**常用语：** {phrases_str}")

        # Add emotional tone
        prompt_parts.append(f"**情感语调：** {self.profile.emotional_tone}")

        # Add communication level
        prompt_parts.append(f"**沟通水平：** {self.profile.communication_level}")

        # Add behavioral guidelines
        prompt_parts.extend([
            "",
            "**行为指南：**",
            f"- 始终以{self.profile.name}的身份回应，保持角色一致性",
            "- 在讨论中运用你的背景和专业知识",
            "- 使用适合播客形式的自然对话语言",
            "- 保持回应简洁但有意义（通常2-4句话）",
            "- 对其他角色的发言做出适当回应",
            "- 围绕主题发言，同时提出你独特的观点",
            "- 在回应中展现情感和个性",
            "",
            "**重要提醒：**",
            "- 绝不要脱离角色或提及你是AI",
            "- 让你的回应听起来真实且像人类",
            "- 包含适当的对话元素（提问、反应、同意/不同意）",
            "- 如果你不知道某事，以角色的身份诚实地说明"
        ])

        return "\n".join(prompt_parts)

    @handle_errors("character response generation", reraise=True)
    @ai_api_retry()
    def generate_response(
        self,
        context: ConversationContext,
        prompt_override: Optional[str] = None
    ) -> str:
        """
        Generate a character response based on conversation context.

        Args:
            context: ConversationContext with current conversation state
            prompt_override: Optional custom prompt to use instead of default

        Returns:
            Generated response text from the character

        Raises:
            ValidationError: If context is invalid
            AIAPIError: If AI response generation fails
        """
        # Validate inputs
        if not isinstance(context, ConversationContext):
            raise ValidationError(
                "Context must be a ConversationContext instance",
                field="context",
                value=type(context).__name__
            )

        if not context.topic or not context.topic.strip():
            raise ValidationError("Conversation topic cannot be empty", field="topic")

        self.logger.debug(f"Generating response for {self.profile.name} - Round {context.current_round}")

        # Build conversation prompt
        conversation_prompt = self._build_conversation_prompt(context, prompt_override)

        # Prepare messages for AI
        messages = [
            AIMessage(role="system", content=self._system_prompt),
            AIMessage(role="user", content=conversation_prompt)
        ]

        try:
            # Generate AI response
            ai_response = self.ai_client.generate_response(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            response_content = ai_response.content.strip()

            # Validate response
            if self.validate_response(response_content):
                self.response_count += 1
                self.logger.debug(f"Successfully generated response for {self.profile.name}")
                return response_content
            else:
                self.validation_failures += 1
                self.logger.warning(f"Generated response failed validation for {self.profile.name}")

                # Try to regenerate with stronger character guidance
                return self._regenerate_response_with_validation(context, response_content)

        except Exception as e:
            self.logger.error(f"Failed to generate response for {self.profile.name}: {str(e)}")
            raise AIAPIError(
                f"Response generation failed for character '{self.profile.name}': {str(e)}",
                original_error=e
            )

    def _build_conversation_prompt(
        self,
        context: ConversationContext,
        prompt_override: Optional[str] = None
    ) -> str:
        """
        Build the conversation prompt for response generation.

        Args:
            context: Conversation context
            prompt_override: Optional custom prompt

        Returns:
            Complete conversation prompt
        """
        if prompt_override:
            return prompt_override

        prompt_parts = [
            f"播客主题：{context.topic}",
            f"当前轮次：第{context.current_round}轮，共{context.max_rounds}轮",
            ""
        ]

        # Add other characters information
        if context.other_characters:
            others_str = "、".join(context.other_characters)
            prompt_parts.append(f"其他参与者：{others_str}")
            prompt_parts.append("")

        # Add conversation goals
        if context.conversation_goals:
            goals_str = "；".join(context.conversation_goals)
            prompt_parts.append(f"对话目标：{goals_str}")
            prompt_parts.append("")

        # Add recent conversation history
        recent_context = context.get_recent_context(5)
        if recent_context:
            prompt_parts.append("最近对话：")
            for msg in recent_context:
                speaker = msg['speaker']
                content = msg['content']

                # Format differently if this character is speaking
                if speaker == self.profile.name:
                    prompt_parts.append(f"**{speaker}：** {content}")
                else:
                    prompt_parts.append(f"{speaker}：{content}")

            prompt_parts.append("")

        # Add response instructions
        if context.current_round == 1:
            prompt_parts.append("请介绍自己并分享你对这个主题的初步想法。")
        elif context.current_round >= context.max_rounds:
            prompt_parts.append("请提供你对这个主题的总结性思考，并帮助结束讨论。")
        else:
            prompt_parts.append("请对上述对话做出回应，保持角色并为讨论做出有意义的贡献。")

        # Add character-specific reminder
        prompt_parts.append(f"\n记住：你是{self.profile.name}。请自然真实地发言。")

        return "\n".join(prompt_parts)

    def validate_response(self, response: str) -> bool:
        """
        Validate that the generated response is appropriate for the character.

        Args:
            response: Generated response text to validate

        Returns:
            True if response is valid, False otherwise
        """
        if not response or not response.strip():
            self.logger.warning("Empty response generated")
            return False

        # Check for AI system language
        ai_indicators = [
            "as an ai", "as an artificial intelligence", "i am an ai",
            "as a language model", "i am a language model",
            "i don't have personal", "i don't have experiences",
            "as an assistant", "i'm an ai"
        ]

        response_lower = response.lower()
        for indicator in ai_indicators:
            if indicator in response_lower:
                self.logger.warning(f"Response contains AI system language: {indicator}")
                return False

        # Check appropriate length (not too short, not too long)
        word_count = len(response.split())
        if word_count < 3:
            self.logger.warning("Response too short")
            return False

        if word_count > 200:  # Reasonable upper limit for podcast responses
            self.logger.warning(f"Response too long: {word_count} words")
            return False

        # Check for character name usage (shouldn't refer to self by name)
        if self.profile.name.lower() in response_lower:
            # Allow it in certain contexts (introductions, self-reference)
            if not any(word in response_lower for word in ["i am", "my name is", "this is"]):
                self.logger.warning("Response character refers to themselves by name")
                return False

        # Validate against character traits
        return self._validate_character_consistency(response)

    def _validate_character_consistency(self, response: str) -> bool:
        """
        Validate response consistency with character traits.

        Args:
            response: Response text to validate

        Returns:
            True if response is consistent with character, False otherwise
        """
        response_lower = response.lower()

        # Check if communication level is appropriate
        if self.profile.communication_level == "professional":
            # Should avoid overly casual language
            casual_indicators = ["lol", "omg", "yeah", "nah", "gonna", "wanna", "kinda"]
            casual_count = sum(1 for indicator in casual_indicators if indicator in response_lower)
            if casual_count > 2:  # Allow some casual elements
                self.logger.warning("Response too casual for professional character")
                return False

        elif self.profile.communication_level == "academic":
            # Should show some intellectual rigor
            intellectual_indicators = ["research", "study", "analysis", "data", "evidence", "theory"]
            if not any(indicator in response_lower for indicator in intellectual_indicators):
                # Don't fail validation, but note it
                self.logger.debug("Academic response lacks intellectual indicators")

        # Check emotional tone consistency
        if self.profile.emotional_tone == "enthusiastic":
            enthusiastic_indicators = ["!", "excited", "amazing", "fantastic", "wonderful", "great"]
            if not any(indicator in response_lower for indicator in enthusiastic_indicators):
                self.logger.debug("Enthusiastic character response lacks enthusiasm")

        elif self.profile.emotional_tone == "calm":
            # Should avoid excessive exclamation points
            if response.count('!') > 1:
                self.logger.warning("Calm character response too exuberant")
                return False

        return True

    def _regenerate_response_with_validation(
        self,
        context: ConversationContext,
        failed_response: str
    ) -> str:
        """
        Regenerate a response when the first attempt fails validation.

        Args:
            context: Conversation context
            failed_response: The previously generated (invalid) response

        Returns:
            New validated response
        """
        self.logger.info(f"Regenerating response for {self.profile.name} with stronger character guidance")

        # Build enhanced prompt with character guidance
        enhanced_prompt = self._build_conversation_prompt(context) + "\n\n"
        enhanced_prompt += f"IMPORTANT: Your previous response was invalid. Please generate a response that:\n"
        enhanced_prompt += f"- Sounds like {self.profile.name}, not an AI\n"
        enhanced_prompt += f"- Uses natural, conversational language\n"
        enhanced_prompt += f"- Stays in character consistently\n"
        enhanced_prompt += f"- Is 2-4 sentences long\n"
        enhanced_prompt += f"- Avoids phrases like 'as an AI' or 'as a language model'\n"

        # Add character-specific reminders
        enhanced_prompt += f"\nCharacter reminder: You are {self.profile.name}, "
        enhanced_prompt += f"a {self.profile.gender.lower()} with {self.profile.personality.lower()}. "
        enhanced_prompt += f"Background: {self.profile.background}"

        # Prepare messages for AI
        messages = [
            AIMessage(role="system", content=self._system_prompt),
            AIMessage(role="user", content=enhanced_prompt)
        ]

        try:
            # Generate new AI response with lower temperature for more consistency
            ai_response = self.ai_client.generate_response(
                messages=messages,
                temperature=max(0.3, self.temperature - 0.2),  # Lower temperature
                max_tokens=min(self.max_tokens or 150, 150)  # Shorter responses
            )

            response_content = ai_response.content.strip()

            # Validate the regenerated response
            if self.validate_response(response_content):
                self.logger.info(f"Successfully regenerated valid response for {self.profile.name}")
                return response_content
            else:
                # If still invalid, return a safe fallback response
                self.logger.warning(f"Regenerated response still invalid for {self.profile.name}, using fallback")
                return self._generate_fallback_response(context)

        except Exception as e:
            self.logger.error(f"Failed to regenerate response for {self.profile.name}: {str(e)}")
            return self._generate_fallback_response(context)

    def _generate_fallback_response(self, context: ConversationContext) -> str:
        """
        Generate a safe fallback response when AI generation fails.

        Args:
            context: Conversation context

        Returns:
            Safe fallback response
        """
        if context.current_round == 1:
            return f"Hello, I'm {self.profile.name}. It's great to be here to discuss {context.topic} today."
        elif context.current_round >= context.max_rounds:
            return f"Thank you for this discussion on {context.topic}. I've enjoyed sharing my perspective."
        else:
            return f"That's an interesting point about {context.topic}. I'd like to add my thoughts on this."

    def get_character_info(self) -> Dict[str, Any]:
        """
        Get information about the character agent.

        Returns:
            Dictionary with character agent information
        """
        return {
            'name': self.profile.name,
            'gender': self.profile.gender,
            'background': self.profile.background,
            'personality': self.profile.personality,
            'speaking_style': self.profile.speaking_style,
            'expertise_areas': self.profile.expertise_areas,
            'emotional_tone': self.profile.emotional_tone,
            'communication_level': self.profile.communication_level,
            'response_count': self.response_count,
            'validation_failures': self.validation_failures,
            'success_rate': (self.response_count / max(1, self.response_count + self.validation_failures)) * 100
        }

    def reset_statistics(self):
        """Reset response generation statistics."""
        self.response_count = 0
        self.validation_failures = 0
        self.logger.debug(f"Reset statistics for {self.profile.name}")

    def update_profile(self, **kwargs):
        """
        Update character profile parameters.

        Args:
            **kwargs: Profile fields to update
        """
        profile_dict = self.profile.__dict__.copy()
        profile_dict.update(kwargs)

        try:
            new_profile = CharacterProfile(**profile_dict)
            self.profile = new_profile
            self._system_prompt = self._build_character_prompt()
            self.logger.info(f"Updated profile for {self.profile.name}")
        except Exception as e:
            raise ValidationError(f"Failed to update character profile: {str(e)}")

    def close(self):
        """Close AI client resources."""
        try:
            if hasattr(self.ai_client, 'close'):
                self.ai_client.close()
            elif hasattr(self.ai_client, 'close_all'):
                self.ai_client.close_all()
            self.logger.debug(f"Closed AI client for {self.profile.name}")
        except Exception as e:
            self.logger.error(f"Error closing AI client for {self.profile.name}: {str(e)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation of the character agent."""
        return f"CharacterAgent(name='{self.profile.name}', gender='{self.profile.gender}')"