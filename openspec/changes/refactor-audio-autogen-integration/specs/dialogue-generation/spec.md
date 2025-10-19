## MODIFIED Requirements
### Requirement: AutoGen Agent Integration
The system SHALL use autogen ConversableAgent for character dialogue generation instead of custom CharacterAgent classes.

#### Scenario: Initialize conversational agents
- **WHEN** podcast generation begins with configured characters
- **THEN** each character is initialized as a ConversableAgent with their personality system message
- **AND** agents are configured with the project's LLM API settings

#### Scenario: Generate multi-turn conversation
- **WHEN** the first character initiates conversation with initial topic
- **THEN** autogen manages the conversation flow between agents for specified number of turns
- **AND** each agent responds according to their character personality and context

#### Scenario: Extract dialogue from chat history
- **WHEN** autogen completes the conversation
- **THEN** the system extracts all message content from chat history in chronological order
- **AND** each message is associated with the speaking character for audio generation

### Requirement: Character Personality Configuration
The system SHALL configure each ConversableAgent with detailed system messages defining character traits and dialogue style.

#### Scenario: Configure male professional character
- **WHEN** creating a male character with professional personality
- **THEN** the agent receives system message describing professional traits and dialogue patterns
- **AND** the agent maintains consistent character voice throughout conversation

#### Scenario: Configure female casual character
- **WHEN** creating a female character with casual personality
- **THEN** the agent receives system message describing casual traits and dialogue style
- **AND** the agent responds in a relaxed, natural manner appropriate to casual setting