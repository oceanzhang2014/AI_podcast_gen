## Why
The current TTS system is experiencing multiple technical failures with ChatTTS including "narrow(): length must be non-negative" errors and initialization failures. The existing complex TTS engine architecture is prone to compatibility issues and lacks robustness. We need to simplify and make the audio generation more reliable while maintaining the same podcast generation functionality.

## What Changes
- Replace complex ChatTTS TTS engine with simpler subprocess-based ChatTTS CLI calls (following talk.py pattern)
- Integrate autogen ConversableAgent for character dialogue generation instead of current agent system
- Implement PyDub-based audio merging for combining individual character audio segments
- Maintain existing web interface and configuration system
- Keep all current podcast generation features (multi-character, multi-round, voice selection)

## Impact
- **Affected specs**: tts-engine, dialogue-generation, audio-processing
- **Affected code**: tts/tts_engine.py, agents/, app.py (podcast generation endpoint)
- **Breaking changes**: Internal TTS engine API, agent initialization patterns
- **Migration impact**: Low - external API and web interface remain unchanged