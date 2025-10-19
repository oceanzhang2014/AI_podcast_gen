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

## 📋 Requirements

- Python 3.8+
- DEEPSEEK_API_KEY or BIGMODEL_API_KEY environment variable
- 4GB+ RAM recommended
- 2GB+ disk space for audio files

## 🛠️ Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd podcast-generation
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

### Tips for Best Results

- **Be Specific**: Detailed topics create better conversations
- **Diverse Characters**: Different perspectives make engaging discussions
- **Rich Backgrounds**: Detailed character backgrounds improve dialogue quality
- **Appropriate Length**: 8 rounds typically produce 15-20 minute podcasts

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

### Production Deployment

For production deployment:

```bash
export FLASK_ENV=production
export SECRET_KEY=your-secure-secret-key
export LOG_LEVEL=INFO
export CACHE_ENABLED=true
export RATE_LIMIT_ENABLED=true

# Use production web server
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

## 🏗️ Architecture

```
podcast-generation/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── run.py                 # Application startup script
├── requirements.txt       # Python dependencies
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

## 🔍 Monitoring

### Health Check Endpoint

```bash
curl http://localhost:5000/health
```

### Application Status

```bash
curl http://localhost:5000/status
```

### Performance Metrics (Debug Mode Only)

```bash
curl http://localhost:5000/metrics
```

## 🚨 Error Handling

The application includes comprehensive error handling:

- **Graceful Degradation**: Fallback mechanisms for failed operations
- **User-Friendly Messages**: Clear error descriptions for users
- **Detailed Logging**: Comprehensive error logging for debugging
- **Retry Mechanisms**: Automatic retry for transient failures

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=utils tests/

# Run specific test file
pytest test_error_handling.py
```

### Test Coverage

- Unit tests for all utility functions
- Integration tests for API endpoints
- Error handling validation
- Performance testing
- Security testing

## 📝 API Documentation

### Generate Podcast

```http
POST /generate
Content-Type: application/json

{
    "topic": "The impact of AI on creative industries",
    "participants": 2,
    "rounds": 8,
    "characters": [
        {
            "name": "Dr. Sarah Chen",
            "gender": "female",
            "background": "AI researcher with 10 years experience",
            "personality": "Thoughtful and analytical"
        },
        {
            "name": "Marcus Rodriguez",
            "gender": "male",
            "background": "Digital artist exploring AI tools",
            "personality": "Creative and curious"
        }
    ]
}
```

### Get Generation Progress

```http
GET /progress/{request_id}
```

### Download Audio File

```http
GET /download/{filename}
```

## 🐛 Troubleshooting

### Common Issues

**API Key Not Working**
- Verify API key is correctly set in environment variables
- Check API key permissions and quota
- Ensure network connectivity to API services

**Generation Failed**
- Check system logs for detailed error messages
- Verify all character fields are filled correctly
- Try reducing conversation complexity

**Slow Performance**
- Check system resource usage
- Verify caching is enabled
- Monitor API service response times

**File Download Issues**
- Verify file exists in generated_audio directory
- Check file permissions
- Ensure file format is supported

### Debug Mode

Enable detailed debugging:

```bash
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
python run.py
```

### Log Files

Check application logs:

```bash
tail -f podcast_generation_development.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Ensure all tests pass
- Add error handling for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- DeepSeek AI for conversation generation capabilities
- BigModel (GLM) for AI services
- ChatTTS for text-to-speech synthesis
- Flask web framework
- Bootstrap for UI components

## 📞 Support

- **Documentation**: See [DOCUMENTATION.md](DOCUMENTATION.md) for detailed information
- **Issues**: Report bugs via GitHub Issues
- **Features**: Request features via GitHub Discussions
- **Security**: Report security issues privately

---

**AI Podcast Generator** - Create engaging conversations with AI-powered characters. 🎙️✨