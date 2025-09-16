# 🚀 Agent Structure Migration Plan

## 📊 Current agent-starter-python vs Target Structure

### Current Simple Structure
```
agent-starter-python/
├── src/
│   ├── agent.py           # Single file with everything
│   └── __init__.py
├── .env                   # Basic configuration
├── requirements.txt       # Minimal dependencies
└── README.md
```

### Target Organized Structure (Based on Main Server Architecture)
```
agent-starter-python/
├── src/
│   ├── agent/             # Agent classes
│   │   ├── __init__.py
│   │   └── main_agent.py  # Enhanced agent class
│   ├── config/            # Configuration management
│   │   ├── __init__.py
│   │   ├── config_loader.py
│   │   └── settings.py
│   ├── providers/         # AI service providers
│   │   ├── __init__.py
│   │   ├── provider_factory.py
│   │   ├── llm/           # LLM providers
│   │   ├── stt/           # Speech-to-Text providers
│   │   ├── tts/           # Text-to-Speech providers
│   │   └── vad/           # Voice Activity Detection
│   ├── database/          # Database integration
│   │   ├── __init__.py
│   │   └── db_client.py
│   ├── memory/            # Memory management
│   │   ├── __init__.py
│   │   └── memory_adapter.py
│   ├── tools/             # MCP tools integration
│   │   ├── __init__.py
│   │   └── mcp_adapter.py
│   ├── handlers/          # Event handlers
│   │   ├── __init__.py
│   │   └── chat_logger.py
│   ├── room/              # Room management
│   │   ├── __init__.py
│   │   └── room_manager.py
│   ├── mqtt/              # MQTT bridge (optional)
│   │   ├── __init__.py
│   │   └── mqtt_bridge.py
│   └── utils/             # Utility functions
│       ├── __init__.py
│       └── helpers.py
├── config/                # Configuration files
│   ├── config.yaml
│   └── providers.yaml
├── .env                   # Environment variables
├── requirements.txt       # Dependencies
└── main.py               # Entry point
```

## 🎯 What This Migration Does

### ✅ **ONLY File Structure Changes**
- **No functionality changes** - Same LiveKit agent behavior
- **No API changes** - Same LiveKit integration
- **No performance changes** - Same runtime performance
- **Just better organization** - Modular, maintainable code structure

### 📁 **File Movement Plan**

#### Current `src/agent.py` → Split into:
1. **`src/agent/main_agent.py`** - Core agent class
2. **`src/handlers/chat_logger.py`** - Event handlers
3. **`src/providers/provider_factory.py`** - Provider creation
4. **`src/config/config_loader.py`** - Configuration management

#### New Structure Benefits:
1. **Modular Design** - Each component in its own file
2. **Easy Testing** - Can test individual components
3. **Scalable** - Easy to add new providers/tools
4. **Maintainable** - Clear separation of concerns

## 🔧 Implementation Plan

### Phase 1: File Structure Creation
**Goal**: Create directory structure without changing functionality

```bash
# Create directories
mkdir -p src/{agent,config,providers,database,memory,tools,handlers,room,mqtt,utils}
mkdir -p config

# Create __init__.py files
touch src/{agent,config,providers,database,memory,tools,handlers,room,mqtt,utils}/__init__.py
```

### Phase 2: Code Extraction (No Logic Changes)
**Goal**: Move existing code into organized files

#### 2.1 Extract Agent Class
**File**: `src/agent/main_agent.py`
```python
# Move Assistant class from src/agent.py
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant..."""
        )

    # Same function_tool methods as before
```

#### 2.2 Extract Configuration
**File**: `src/config/config_loader.py`
```python
from dotenv import load_dotenv
import os

class ConfigLoader:
    @staticmethod
    def load_env():
        """Load environment variables - same as before"""
        load_dotenv(".env")

    @staticmethod
    def get_groq_config():
        """Get Groq configuration from environment"""
        return {
            'llm_model': os.getenv('LLM_MODEL', 'openai/gpt-oss-20b'),
            'stt_model': os.getenv('STT_MODEL', 'whisper-large-v3-turbo'),
            'tts_model': os.getenv('TTS_MODEL', 'playai-tts'),
            'tts_voice': os.getenv('TTS_VOICE', 'Aaliyah-PlayAI')
        }
```

#### 2.3 Extract Provider Creation
**File**: `src/providers/provider_factory.py`
```python
import livekit.plugins.groq as groq
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

class ProviderFactory:
    @staticmethod
    def create_llm(config):
        """Create LLM provider - same logic as before"""
        return groq.LLM(model=config['llm_model'])

    @staticmethod
    def create_stt(config):
        """Create STT provider - same logic as before"""
        return groq.STT(model=config['stt_model'], language="en")

    @staticmethod
    def create_tts(config):
        """Create TTS provider - same logic as before"""
        return groq.TTS(model=config['tts_model'], voice=config['tts_voice'])

    @staticmethod
    def create_vad():
        """Create VAD provider - same logic as before"""
        return silero.VAD.load()
```

#### 2.4 Extract Event Handlers
**File**: `src/handlers/chat_logger.py`
```python
import json
import asyncio
import logging

logger = logging.getLogger("chat_logger")

class ChatEventHandler:
    @staticmethod
    def setup_session_handlers(session, ctx):
        """Setup all event handlers - same logic as current agent.py"""

        @session.on("agent_false_interruption")
        def _on_agent_false_interruption(ev):
            # Same code as current implementation
            logger.info("False positive interruption, resuming")
            # ... rest of the handler code

        @session.on("agent_state_changed")
        def _on_agent_state_changed(ev):
            # Same code as current implementation
            logger.info(f"Agent state changed: {ev}")
            # ... rest of the handler code

        # All other handlers exactly as they are now
```

### Phase 3: Update Entry Point
**File**: `main.py` (new main entry point)
```python
from livekit.agents import WorkerOptions, cli
from src.agent.main_agent import Assistant
from src.config.config_loader import ConfigLoader
from src.providers.provider_factory import ProviderFactory
from src.handlers.chat_logger import ChatEventHandler

def prewarm(proc):
    """Same prewarm logic"""
    proc.userdata["vad"] = ProviderFactory.create_vad()

async def entrypoint(ctx):
    """Same entrypoint logic, just organized"""
    # Load configuration
    ConfigLoader.load_env()
    config = ConfigLoader.get_groq_config()

    # Create providers
    llm = ProviderFactory.create_llm(config)
    stt = ProviderFactory.create_stt(config)
    tts = ProviderFactory.create_tts(config)
    vad = ctx.proc.userdata["vad"]

    # Create session (same as before)
    session = AgentSession(
        llm=llm, stt=stt, tts=tts,
        turn_detection=MultilingualModel(),
        vad=vad, preemptive_generation=False
    )

    # Setup handlers
    ChatEventHandler.setup_session_handlers(session, ctx)

    # Start session (same as before)
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
```

## ✅ **Key Points**

### **No Functional Changes**
- Same LiveKit agent behavior
- Same Groq providers
- Same event handling
- Same room management
- Same CLI interface

### **Only Organizational Changes**
- Better file structure
- Modular components
- Easier to maintain
- Easier to extend
- Easier to test

### **Backward Compatibility**
- Same `.env` file format
- Same command line usage
- Same LiveKit integration
- Same requirements.txt

## 🚀 **Migration Steps**

1. **Create new file structure** (5 minutes)
2. **Move code into organized files** (30 minutes)
3. **Update imports** (10 minutes)
4. **Test functionality** (15 minutes)
5. **Update documentation** (10 minutes)

**Total Time**: ~1 hour

**Risk Level**: Very Low (just file organization)

**Testing**: Same existing tests work unchanged

This migration gives you the organized structure of the main server while keeping all LiveKit functionality exactly the same!