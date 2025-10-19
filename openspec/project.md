# Project Context

## Purpose
Production-ready web application that creates AI-powered podcast conversations using character agents with distinct personalities, text-to-speech synthesis, and a web interface for configuration and generation.

## Tech Stack
- **Backend**: Python 3.8+, Flask web framework
- **AI APIs**: DeepSeek API (deepseek-chat), BigModel/GLM API (glm-4)
- **Text-to-Speech**: ChatTTS (primary), gTTS (fallback), pyttsx3 (fallback)
- **Audio Processing**: FFmpeg, PyDub, torio extension
- **Database**: SQLite for configuration storage
- **Frontend**: Bootstrap 5.1.3, JavaScript, responsive design
- **Output Format**: MP3 audio files

## Project Conventions

### Code Style
- **Modular Design**: Clear separation of concerns (agents/, tts/, utils/)
- **Error Handling**: Comprehensive custom exception hierarchy throughout
- **Configuration**: Environment-based with fallback defaults
- **Logging**: Detailed logging with structured format
- **Naming**: snake_case for Python files and variables, descriptive function names

### Architecture Patterns
- **Flask Application Pattern**: Main app.py with modular imports
- **Factory Pattern**: For TTS engines and AI clients
- **Repository Pattern**: For configuration and data persistence
- **Decorator Pattern**: For performance monitoring and rate limiting
- **Observer Pattern**: For progress tracking and real-time updates

### Testing Strategy
- Manual testing focused on audio generation quality
- Integration testing for AI API interactions
- Performance testing for concurrent generation tasks
- Security testing for input validation and rate limiting

### Git Workflow
- Feature-based development with descriptive commits
- Documentation updates tracked alongside code changes
- Configuration changes committed separately from feature changes

## Domain Context
- **Podcast Generation**: Creates multi-character AI conversations (2-6 participants, 3-12 rounds)
- **Character Agents**: Each agent has name, gender, background, personality traits
- **Bilingual Support**: Chinese (primary) and English language support
- **Voice Synthesis**: Gender-based voice selection with natural speech patterns
- **Real-time Progress**: WebSocket-like progress tracking during generation

## Important Constraints
- **API Dependencies**: Requires valid DEEPSEEK_API_KEY or BIGMODEL_API_KEY
- **System Requirements**: FFmpeg installation required for audio processing
- **Memory Requirements**: 4GB+ RAM recommended for generation tasks
- **Rate Limiting**: Built-in protection against API abuse
- **File Security**: Path validation and secure file handling for uploads/downloads
- **Concurrent Users**: Rate limiting prevents system overload

## External Dependencies
- **DeepSeek API**: Primary AI conversation generation
- **BigModel API**: Alternative AI conversation provider
- **ChatTTS**: High-quality natural voice synthesis
- **FFmpeg**: System dependency for audio manipulation and MP3 encoding, 已安装“ffmpeg version 2025-10-16-git-cd4b01707d-full_build-www.gyan.dev Copyright (c) 2000-2025 the FFmpeg developers built with gcc 15.2.0 (Rev8, Built by MSYS2 project)”已加入系统变量C:\Program Files\ffmpeg-master-latest-win64-gpl\bin
- **cuda**: 已安装cuda 12.8环境，并加入系统变量中C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8
- **Bootstrap CDN**: Frontend UI framework and icons
- **SQLite**: Local database for configuration persistence
