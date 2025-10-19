## MODIFIED Requirements
### Requirement: Subprocess-based TTS Generation
The system SHALL generate speech audio using subprocess calls to ChatTTS CLI instead of Python API integration.

#### Scenario: Generate single character audio
- **WHEN** a character's dialogue text is provided with voice parameters
- **THEN** the system executes `chattts` CLI with appropriate seed parameters to generate audio file

#### Scenario: Handle TTS CLI failures
- **WHEN** ChatTTS CLI subprocess fails or is unavailable
- **THEN** the system automatically falls back to gTTS or pyttsx3 for audio generation

### Requirement: Voice Parameter Mapping
The system SHALL map character gender and personality to ChatTTS seed values for voice selection.

#### Scenario: Map character to ChatTTS seed
- **WHEN** a female character with casual personality is provided
- **THEN** the system uses seed "2" for young, emotionally rich voice
- **WHEN** a male character with professional personality is provided
- **THEN** the system uses seed "333" for young, gentle voice

### Requirement: Simplified TTS Service Interface
The system SHALL provide a simple TTS service that accepts text and voice parameters and returns audio file paths.

#### Scenario: Request audio generation
- **WHEN** the podcast generation system requests audio for text
- **THEN** the TTS service generates an audio file and returns the file path
- **AND** the audio file is saved in the configured output directory with timestamp naming