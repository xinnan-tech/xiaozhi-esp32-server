# Agent Structure Organization

## New Organized Structure

```
agent-starter-python/
├── main.py                     # New main entry point (organized)
├── src/
│   ├── agent_original_backup.py # Backup of original agent.py
│   ├── agent.py                 # Original agent file (kept for reference)
│   ├── agent/
│   │   └── main_agent.py        # Agent class (Assistant)
│   ├── config/
│   │   └── config_loader.py     # Configuration management
│   ├── providers/
│   │   └── provider_factory.py  # AI provider factory (LLM, STT, TTS, VAD)
│   ├── handlers/
│   │   └── chat_logger.py       # Event handlers for chat logging
│   ├── utils/
│   │   └── helpers.py           # Utility functions (UsageManager)
│   ├── database/               # Ready for database integration
│   ├── memory/                 # Ready for memory management
│   ├── tools/                  # Ready for MCP tools
│   ├── room/                   # Ready for room management
│   └── mqtt/                   # Ready for MQTT bridge
├── .env                        # Configuration file
└── requirements.txt            # Dependencies (updated)
```

## How to Use

### Run with New Organized Structure
```bash
python main.py dev
```

### Run with Original Structure (for comparison)
```bash
python -m livekit.agents.cli --dev src.agent
```

## Key Features

### ✅ Preserved Functionality
- Same LiveKit agent behavior
- Same Groq providers (LLM, STT, TTS)
- Same event handling
- Same room management
- Same CLI interface

### ✅ Better Organization
- **Modular design**: Each component in its own module
- **Easy to extend**: Add new providers, tools, or handlers easily
- **Better testing**: Can test individual components
- **Maintainable**: Clear separation of concerns

### ✅ Configuration Management
- Environment-based configuration
- Factory pattern for providers
- Easy to add new configuration options

## Components

### ConfigLoader (`src/config/config_loader.py`)
- Loads environment variables
- Provides structured configuration for all components

### ProviderFactory (`src/providers/provider_factory.py`)
- Creates AI providers (LLM, STT, TTS, VAD)
- Centralizes provider creation logic

### Assistant (`src/agent/main_agent.py`)
- Main agent class with function tools
- Same behavior as original agent

### ChatEventHandler (`src/handlers/chat_logger.py`)
- Handles all LiveKit events
- Data channel communication
- Same event handling logic

### UsageManager (`src/utils/helpers.py`)
- Usage tracking and metrics
- Utility functions

## Migration Complete ✅

The agent now has the same organized structure as the main server while maintaining 100% LiveKit functionality!