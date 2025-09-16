# 🚀 How to Run the Agent Project

## Prerequisites

- Python 3.9 or higher
- LiveKit server running (cloud or local)
- Environment variables configured

## 📋 Setup Instructions

### 1. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using the project's pyproject.toml
pip install -e .
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# AI Models Configuration
LLM_MODEL=openai/gpt-oss-20b
STT_MODEL=whisper-large-v3-turbo
TTS_MODEL=playai-tts
TTS_VOICE=Aaliyah-PlayAI
STT_LANGUAGE=en

# Agent Settings
PREEMPTIVE_GENERATION=false
NOISE_CANCELLATION=true

# Groq API Configuration (if using Groq providers)
GROQ_API_KEY=your_groq_api_key
```

## 🎯 Running the Agent

### Method 1: Using New Organized Structure (Recommended)

```bash
# Development mode
python main.py dev

# Production mode
python main.py start
```

### Method 2: Using LiveKit CLI with Original Structure

```bash
# Development mode
python -m livekit.agents.cli dev src.agent

# Production mode
python -m livekit.agents.cli start src.agent
```

### Method 3: Using UV (if available)

```bash
# Development mode
uv run python main.py dev

# Production mode
uv run python main.py start
```

## 🔧 Development Options

### Run with Custom Configuration

```bash
# Specify custom environment file
python main.py dev --env-file .env.local

# Run with verbose logging
python main.py dev --log-level debug

# Run on specific port
python main.py dev --port 8080
```

### Testing the Agent

1. **Start the Agent**:
   ```bash
   python main.py dev
   ```

2. **Connect a Client**:
   - Use LiveKit's example web client
   - Or build your own client using LiveKit SDKs
   - Room name format: `agent-room-{timestamp}`

3. **Test Voice Interaction**:
   - Join the room with audio enabled
   - Speak to the agent
   - Agent will respond with AI-generated speech

## 🏗️ Project Structure

```
agent-starter-python/
├── main.py                 # New organized entry point ⭐
├── src/
│   ├── agent/             # Agent classes
│   │   └── main_agent.py  # Assistant agent with function tools
│   ├── config/            # Configuration management
│   │   └── config_loader.py
│   ├── providers/         # AI service providers
│   │   └── provider_factory.py
│   ├── handlers/          # Event handlers
│   │   └── chat_logger.py
│   └── utils/             # Utility functions
│       └── helpers.py
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── pyproject.toml        # Project configuration
```

## 🎭 Available Function Tools

The agent comes with built-in function tools:

- **`lookup_weather`**: Get weather information for any location
  ```
  "What's the weather in New York?"
  ```

## 🔍 Monitoring & Debugging

### View Agent Logs

The agent provides detailed logging:

```bash
# Run with debug logging
python main.py dev --log-level debug
```

### Monitor Events

The agent publishes events via data channel:
- `agent_state_changed`
- `user_input_transcribed`
- `speech_created`
- `agent_false_interruption`

### Usage Metrics

Usage metrics are automatically collected and logged on shutdown.

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Ensure you're in the project directory
   cd agent-starter-python
   python main.py dev
   ```

2. **Environment Variables Not Found**:
   ```bash
   # Check .env file exists and is configured
   ls -la .env
   cat .env
   ```

3. **LiveKit Connection Issues**:
   - Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`
   - Check if LiveKit server is running
   - Ensure network connectivity

4. **Audio Issues**:
   - Check microphone permissions
   - Verify audio codecs are supported
   - Test with different browsers/clients

### Debug Mode

Run in debug mode for detailed logs:

```bash
python main.py dev --log-level debug
```

### Test Configuration

Test if configuration is loaded correctly:

```bash
python -c "
from src.config.config_loader import ConfigLoader
ConfigLoader.load_env()
config = ConfigLoader.get_groq_config()
print('Configuration:', config)
"
```

## 🔄 Switching Between Structures

You can easily switch between the organized and original structure:

**Organized (Recommended)**:
```bash
python main.py dev
```

**Original**:
```bash
python -m livekit.agents.cli dev src.agent
```

Both methods provide identical functionality!

## 📞 Support

- Check logs for detailed error messages
- Verify all environment variables are set
- Ensure LiveKit server is accessible
- Test with minimal configuration first

Happy coding! 🎉