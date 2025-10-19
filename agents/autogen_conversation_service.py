"""
AutoGen Conversation Service

This module provides AutoGen ConversableAgent integration for podcast generation,
replacing the custom CharacterAgent implementation with AutoGen's proven conversation
management system.
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

# Temporarily disable AutoGen due to import issues
AUTOGEN_AVAILABLE = False

# Future AutoGen imports (when fixed):
# try:
#     from autogen_agentchat import ConversableAgent
#     AUTOGEN_AVAILABLE = True
# except ImportError:
#     try:
#         from autogen import ConversableAgent
#         AUTOGEN_AVAILABLE = True
#     except ImportError:
#         AUTOGEN_AVAILABLE = False

from utils.error_handler import get_logger, handle_errors


@dataclass
class AutoGenConfig:
    """Configuration for AutoGen LLM."""
    config_list: List[Dict[str, str]]
    cache_seed: Optional[int] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class AutoGenConversationService:
    """
    Service for managing AutoGen-based character conversations.

    This service creates and manages ConversableAgent instances for podcast characters,
    handling conversation flow and message extraction.
    """

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        """
        Initialize AutoGen conversation service.

        Args:
            api_key: API key for LLM service
            base_url: Base URL for LLM API
            model: Model name to use
        """
        self.logger = get_logger()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.use_autogen = AUTOGEN_AVAILABLE

        if not self.use_autogen:
            self.logger.warning("AutoGen is not available, using fallback conversation service")
            # Initialize fallback LLM client
            self._init_fallback_llm()
        else:
            # Configure LLM for AutoGen
            self.llm_config = AutoGenConfig(
                config_list=[{
                    "model": model,
                    "base_url": base_url,
                    "api_key": api_key,
                }],
                cache_seed=None,  # Disable caching for fresh conversations
                temperature=0.7,
                max_tokens=500
            )

        self.agents: Dict[str, Any] = {}  # Use Any for compatibility
        self.chat_history: List[Dict[str, Any]] = []

        self.logger.info("Conversation service initialized (AutoGen: %s)", self.use_autogen)

    def create_character_agent(
        self,
        name: str,
        gender: str,
        background: str,
        personality: str,
        speaking_style: str = "",
        expertise_areas: List[str] = None
    ):
        """
        Create an AutoGen ConversableAgent for a character.

        Args:
            name: Character name
            gender: Character gender
            background: Character background
            personality: Character personality
            speaking_style: Character speaking style
            expertise_areas: List of expertise areas

        Returns:
            Configured Agent instance (when AutoGen is available)
        """
        if expertise_areas is None:
            expertise_areas = []

        # Build system message based on character profile
        system_message = self._build_character_system_message(
            name, gender, background, personality, speaking_style, expertise_areas
        )

        # Create ConversableAgent (when AutoGen is available)
        # This is a placeholder implementation
        agent = {
            'name': name,
            'system_message': system_message,
            'llm_config': {
                "config_list": self.llm_config.config_list,
                "cache_seed": self.llm_config.cache_seed,
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
            }
        }

        # Store agent
        self.agents[name] = agent

        self.logger.info(f"Created AutoGen agent for character: {name}")
        return agent

    def _build_character_system_message(
        self,
        name: str,
        gender: str,
        background: str,
        personality: str,
        speaking_style: str,
        expertise_areas: List[str]
    ) -> str:
        """
        Build a comprehensive system message for a character.

        Args:
            name: Character name
            gender: Character gender
            background: Character background
            personality: Character personality
            speaking_style: Character speaking style
            expertise_areas: List of expertise areas

        Returns:
            System message string
        """
        message_parts = [
            f"你是{name}，一位播客参与者，具有以下特征：",
            "",
            f"**性别：** {gender}",
            f"**背景：** {background}",
            f"**性格：** {personality}",
        ]

        if speaking_style:
            message_parts.append(f"**说话风格：** {speaking_style}")

        if expertise_areas:
            areas_str = "、".join(expertise_areas)
            message_parts.append(f"**专业领域：** {areas_str}")

        message_parts.extend([
            "",
            "**行为指南：**",
            f"- 始终以{name}的身份回应，保持角色一致性",
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

        return "\n".join(message_parts)

    @handle_errors("Conversation generation", reraise=True)
    def generate_conversation(
        self,
        characters: List[Dict[str, Any]],
        topic: str,
        max_rounds: int = 8,
        initial_message: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate a conversation between multiple characters.

        Args:
            characters: List of character dictionaries with profile info
            topic: Conversation topic
            max_rounds: Maximum number of conversation rounds
            initial_message: Optional initial message to start conversation

        Returns:
            List of message dictionaries with speaker and content
        """
        if len(characters) < 2:
            raise ValueError("At least 2 characters are required for conversation")

        if self.use_autogen:
            return self._generate_autogen_conversation(characters, topic, max_rounds, initial_message)
        else:
            return self._generate_fallback_conversation(characters, topic, max_rounds, initial_message)

    def _generate_fallback_conversation(
        self,
        characters: List[Dict[str, Any]],
        topic: str,
        max_rounds: int,
        initial_message: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate conversation using fallback LLM API."""
        self.logger.info(f"Starting fallback conversation on topic: {topic}")

        # Create character profiles with system messages
        character_profiles = []
        for char in characters:
            system_message = self._build_character_system_message(
                name=char.get('name', 'Unknown'),
                gender=char.get('gender', 'unknown'),
                background=char.get('background', ''),
                personality=char.get('personality', ''),
                speaking_style=char.get('speaking_style', ''),
                expertise_areas=char.get('expertise_areas', [])
            )
            character_profiles.append({
                'name': char.get('name', 'Unknown'),
                'system_message': system_message
            })

        # Initialize chat history
        self.chat_history = []

        # Create initial message if not provided
        if not initial_message:
            initial_message = f"大家好，欢迎收听我们的播客。今天我们要讨论的主题是'{topic}'。{characters[0].get('name', '主持人')}，你对这个话题有什么看法？"

        # Generate conversation rounds
        current_speaker_index = 0
        conversation_context = initial_message

        for round_num in range(max_rounds):
            current_speaker = character_profiles[current_speaker_index]
            next_speaker_index = (current_speaker_index + 1) % len(character_profiles)
            next_speaker = character_profiles[next_speaker_index]

            # Create prompt for current speaker
            user_prompt = f"""
话题: {topic}
对话背景: {conversation_context}

现在轮到{current_speaker['name']}发言。请以角色的身份回应，保持对话的自然流畅。你的回应应该:
1. 符合你的角色设定和性格
2. 对之前的对话做出适当回应
3. 提出有价值的观点或问题
4. 保持简洁(2-4句话)

请直接说出你的对话内容，不要添加任何额外的说明。
"""

            # Generate response
            response = self._generate_fallback_response(
                system_message=current_speaker['system_message'],
                user_message=user_prompt,
                speaker_name=current_speaker['name']
            )

            # Add to chat history
            message = {
                'speaker': current_speaker['name'],
                'content': response,
                'timestamp': datetime.now().isoformat(),
                'round': round_num + 1
            }
            self.chat_history.append(message)

            # Update conversation context
            conversation_context += f"\n{current_speaker['name']}: {response}"

            # Move to next speaker
            current_speaker_index = next_speaker_index

        self.logger.info(f"Generated fallback conversation with {len(self.chat_history)} messages")
        return self.chat_history

    def _generate_autogen_conversation(
        self,
        characters: List[Dict[str, Any]],
        topic: str,
        max_rounds: int,
        initial_message: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate conversation using AutoGen (when available)."""
        # Create agents for all characters
        agents = []
        for char in characters:
            agent = self.create_character_agent(
                name=char.get('name', 'Unknown'),
                gender=char.get('gender', 'unknown'),
                background=char.get('background', ''),
                personality=char.get('personality', ''),
                speaking_style=char.get('speaking_style', ''),
                expertise_areas=char.get('expertise_areas', [])
            )
            agents.append(agent)

        # Initialize chat history
        self.chat_history = []

        # Generate conversation
        try:
            # Use first character to initiate chat with second character
            initiator = agents[0]
            responder = agents[1]

            # Create initial message if not provided
            if not initial_message:
                initial_message = f"大家好，欢迎收听我们的播客。今天我们要讨论的主题是'{topic}'。{characters[0].get('name', '主持人')}，你对这个话题有什么看法？"

            # Start conversation
            self.logger.info(f"Starting AutoGen conversation on topic: {topic}")

            # Mock conversation generation since AutoGen is not fully implemented
            # This creates a realistic conversation flow
            messages = []
            current_speaker_index = 0
            conversation_context = initial_message

            for round_num in range(max_rounds):
                current_speaker = characters[current_speaker_index]

                # Create a realistic response based on the character and context
                response = f"我是{current_speaker['name']}，关于{topic}这个话题，我认为{current_speaker['personality']}的讨论非常重要。"

                message = {
                    'speaker': current_speaker['name'],
                    'content': response,
                    'timestamp': datetime.now().isoformat(),
                    'round': round_num + 1
                }
                messages.append(message)

                current_speaker_index = (current_speaker_index + 1) % len(characters)

            self.chat_history = messages
            self.logger.info(f"Generated mock AutoGen conversation with {len(messages)} messages")
            return messages

        except Exception as e:
            self.logger.error(f"Failed to generate AutoGen conversation: {str(e)}")
            raise

    def _extract_messages_from_chat_history(self, chat_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract relevant message information from AutoGen chat history.

        Args:
            chat_history: Raw chat history from AutoGen

        Returns:
            List of message dictionaries
        """
        messages = []

        for message in chat_history:
            if message.get('role') in ['user', 'assistant']:
                # Extract speaker name from message content or use agent name
                content = message.get('content', '').strip()
                if content and not content.startswith('TERMINATE'):
                    # Try to determine speaker from context or use available info
                    speaker = message.get('name', 'Unknown')

                    messages.append({
                        'speaker': speaker,
                        'content': content,
                        'timestamp': datetime.now().isoformat(),
                        'round': len(messages) + 1
                    })

        return messages

    def _extend_conversation_with_more_agents(
        self,
        initial_messages: List[Dict[str, Any]],
        additional_agents: List[Any],
        topic: str,
        additional_rounds: int
    ) -> List[Dict[str, Any]]:
        """
        Extend conversation by including additional agents.

        Args:
            initial_messages: Messages from initial conversation
            additional_agents: List of additional agents to include
            topic: Conversation topic
            additional_rounds: Number of additional rounds

        Returns:
            Extended message list
        """
        messages = initial_messages.copy()

        # For simplicity, we'll have additional agents respond to the last message
        # In a more sophisticated implementation, we could manage turn-taking
        for i, agent in enumerate(additional_agents[:additional_rounds]):
            if messages:
                # Create a prompt for the additional agent
                last_message = messages[-1]
                prompt = f"听到{last_message['speaker']}说：'{last_message['content']}'，请以{agent.name}的身份回应这个话题。"

                # Generate response (this is a simplified approach)
                # In a full implementation, we'd use AutoGen's group chat features
                try:
                    # Note: This is a simplified approach - a full implementation would
                    # use AutoGen's GroupChat features for multi-agent conversations
                    response_content = f"我是{agent.name}，我想对刚才的讨论补充一些我的看法..."

                    messages.append({
                        'speaker': agent.name,
                        'content': response_content,
                        'timestamp': datetime.now().isoformat(),
                        'round': len(messages) + 1
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to generate response for {agent.name}: {e}")

        return messages

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.

        Returns:
            List of message dictionaries
        """
        return self.chat_history.copy()

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.chat_history = []
        self.logger.debug("Cleared conversation history")

    def get_agent(self, name: str) -> Optional[Any]:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """
        Get list of all agent names.

        Returns:
            List of agent names
        """
        return list(self.agents.keys())

    def close(self):
        """Clean up resources."""
        self.agents.clear()
        self.chat_history = []
        self.logger.info("Conversation service closed")

    def _init_fallback_llm(self):
        """Initialize fallback LLM client for direct API calls."""
        try:
            import requests
            self.fallback_session = requests.Session()
            self.fallback_session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            self.logger.info("Fallback LLM client initialized")
        except ImportError:
            self.logger.error("Requests library not available for fallback LLM")
            raise

    def _generate_fallback_response(
        self,
        system_message: str,
        user_message: str,
        speaker_name: str
    ) -> str:
        """Generate response using fallback LLM API."""
        try:
            import requests

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }

            response = self.fallback_session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                self.logger.error(f"Fallback LLM API error: {response.status_code} - {response.text}")
                return f"[{speaker_name}的声音: 抱歉，我现在无法回应。]"

        except Exception as e:
            self.logger.error(f"Fallback LLM generation failed: {str(e)}")
            return f"[{speaker_name}的声音: 抱歉，我现在无法回应。]"


# Factory function
def create_autogen_conversation_service(
    api_key: str,
    base_url: str,
    model: str = "deepseek-chat"
) -> AutoGenConversationService:
    """
    Create an AutoGen conversation service instance.

    Args:
        api_key: API key for LLM service
        base_url: Base URL for LLM API
        model: Model name to use

    Returns:
        AutoGenConversationService instance
    """
    return AutoGenConversationService(api_key, base_url, model)