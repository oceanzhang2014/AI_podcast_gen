# AI Podcast Generator

A production-ready web application that creates engaging podcast conversations using AI-powered characters and text-to-speech synthesis.

## 🚀 Features

- **AI-Powered Conversations**: Generate realistic podcast dialogues using advanced AI models
- **Character Customization**: Create unique characters with personalities, backgrounds, and voices
- **Text-to-Speech**: High-quality voice synthesis with multiple voice options
- **Real-time Progress**: Live progress tracking during generation
- **Production Ready**: Comprehensive error handling, logging, and monitoring
- **Security First**: Input validation, rate limiting, and secure file handling
- **Performance Optimized**: Caching, resource pooling, and background processing
- **Git Management Tools**: Built-in Git tools for easy version control and deployment

## 📋 Requirements

- Python 3.8+
- DEEPSEEK_API_KEY or BIGMODEL_API_KEY environment variable
- Git for Windows (for Git management tools)
- 4GB+ RAM recommended
- 2GB+ disk space for audio files

## 🛠️ Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/oceanzhang2014/AI_podcast_gen.git
cd AI_podcast_gen
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Required: AI API Keys (at least one)
DEEPSEEK_API_KEY=your-deepseek-api-key
BIGMODEL_API_KEY=your-bigmodel-api-key

# Optional: Custom Configuration
SECRET_KEY=your-secret-key
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
LOG_LEVEL=INFO
```

### 3. Run the Application

```bash
./venv/Scripts/python.exe app.py
```

Visit `http://localhost:5000` to start generating podcasts!

## 📖 Usage Guide

### Creating a Podcast

1. **Enter a Topic**: Describe your podcast topic in detail
2. **Set Participants**: Choose 2-6 participants for the conversation
3. **Configure Characters**: For each participant, provide:
   - Name
   - Gender (affects voice selection)
   - Background (expertise, experience, perspective)
   - Personality (speaking style and tone)
4. **Set Conversation Length**: Choose 3-12 rounds for desired duration
5. **Generate**: Click "Generate Podcast" and wait for completion

### Git Management Tools

Use the included Git管理工具.bat for easy version control:

```bash
# Double-click Git管理工具.bat for interactive menu
# Or use command line:
Git管理工具.bat save "Your commit message"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (development/production) | `development` |
| `SECRET_KEY` | Flask secret key | auto-generated |
| `DEEPSEEK_API_KEY` | DeepSeek API key | required |
| `BIGMODEL_API_KEY` | BigModel API key | required |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_INPUT_LENGTH` | Maximum input characters | `1000` |
| `CACHE_ENABLED` | Enable performance caching | `true` |

## 🏗️ Architecture

```
AI_podcast_gen/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── run.py                 # Application startup script
├── requirements.txt       # Python dependencies
├── Git管理工具.bat          # Git management interface
├── gitcode/               # Git tools directory
│   ├── git_manager.bat     # Git operations menu
│   ├── git_save.bat        # Save and push script
│   ├── git_push.bat        # Push only script
│   └── ...                # Other Git utilities
├── utils/
│   ├── error_handler.py   # Error handling utilities
│   ├── validators.py      # Input validation
│   ├── performance.py     # Performance optimization
│   └── ...               # Utility modules
├── agents/
│   ├── character_agent.py # AI character management
│   └── conversation_manager.py # Dialogue generation
├── tts/
│   ├── tts_engine.py      # Text-to-speech engine
│   └── voice_manager.py   # Voice selection
├── templates/             # HTML templates
├── static/               # Static assets
└── generated_audio/      # Output directory
```

## 🔒 Security Features

- **Input Validation**: All user inputs are validated and sanitized
- **Rate Limiting**: Protection against abuse and DoS attacks
- **File Security**: Secure file upload/download with path validation
- **XSS Protection**: Output encoding and input sanitization
- **Secure Headers**: HTTP security headers for all responses

## 📊 Performance Features

- **Intelligent Caching**: TTL-based caching for expensive operations
- **Resource Pooling**: Efficient management of AI API connections
- **Background Processing**: Asynchronous task execution
- **Performance Monitoring**: Real-time metrics and alerting
- **Memory Management**: Automatic cleanup of old data

## 🐛 Troubleshooting

### Common Issues

**Git Management Tools Not Working**
- Ensure Git for Windows is installed
- Check that Git is in system PATH
- Run Git管理工具.bat as Administrator if needed

**API Key Not Working**
- Verify API key is correctly set in environment variables
- Check API key permissions and quota
- Ensure network connectivity to API services

**Generation Failed**
- Check system logs for detailed error messages
- Verify all character fields are filled correctly
- Try reducing conversation complexity

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- DeepSeek AI for conversation generation capabilities
- BigModel (GLM) for AI services
- ChatTTS for text-to-speech synthesis
- Flask web framework
- Bootstrap for UI components

---

**AI Podcast Generator** - Create engaging conversations with AI-powered characters. 🎙️✨
