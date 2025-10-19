## Context
The current system suffers from complex ChatTTS integration issues including DLL loading problems, API parameter incompatibility, and initialization failures. The existing agent system uses custom CharacterAgent classes that may be over-engineered for simple dialogue generation. We need a more robust, simpler approach.

## Goals / Non-Goals
- **Goals**: Reliable audio generation, simplified architecture, maintain existing functionality
- **Non-Goals**: Advanced TTS features, complex audio processing, multi-format support

## Decisions
- **Decision**: Use subprocess ChatTTS CLI calls instead of Python API
  - **Rationale**: talk.py demonstrates this works reliably, avoids Python API complexity
- **Decision**: Replace custom agents with autogen ConversableAgent
  - **Rationale**: Proven library for dialogue generation, simpler implementation
- **Decision**: Use PyDub for audio merging
  - **Rationale**: Simple, reliable audio concatenation without complex dependencies

## Risks / Trade-offs
- **Risk**: ChatTTS CLI dependency
  - **Mitigation**: Fallback to gTTS if CLI unavailable
- **Risk**: autogen dependency complexity
  - **Mitigation**: Simple agent configuration, no complex workflows
- **Trade-off**: Less TTS customization for reliability

## Migration Plan
1. Implement new subprocess-based TTS service
2. Replace agent system with autogen ConversableAgent
3. Update podcast generation flow
4. Test and validate audio output quality

## Open Questions
- Should we maintain fallback TTS options for redundancy?
- How to handle voice parameter mapping for different ChatTTS seeds?