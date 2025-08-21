# Xiaozhi ESP32 Server - Database Relationship Matrix

## 📊 Table Relationship Matrix

This document provides a structured text-based view of all database relationships in the Xiaozhi ESP32 Server system.

### 🔗 Relationship Matrix Table

```
┌─────────────────────────┬─────────────────────────┬──────────┬─────────────────────────────────────┐
│ FROM TABLE              │ TO TABLE                │ TYPE     │ DESCRIPTION                         │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ sys_user                │ sys_user_token          │ 1:1      │ User authentication tokens          │
│ sys_user                │ ai_agent                │ 1:M      │ User owns multiple AI agents        │
│ sys_user                │ ai_device               │ 1:M      │ User owns multiple ESP32 devices    │
│ sys_user                │ ai_voiceprint           │ 1:M      │ User has multiple voiceprints       │
│ sys_user                │ ai_chat_history         │ 1:M      │ User participates in multiple chats │
│ sys_user                │ ai_chat_message         │ 1:M      │ User sends multiple messages        │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ sys_dict_type           │ sys_dict_data           │ 1:M      │ Dictionary type contains entries    │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_model_config         │ ai_tts_voice            │ 1:M      │ TTS model provides multiple voices  │
│ ai_model_config         │ ai_agent (asr_model)    │ 1:M      │ ASR model used by multiple agents   │
│ ai_model_config         │ ai_agent (vad_model)    │ 1:M      │ VAD model used by multiple agents   │
│ ai_model_config         │ ai_agent (llm_model)    │ 1:M      │ LLM model used by multiple agents   │
│ ai_model_config         │ ai_agent (vllm_model)   │ 1:M      │ VLLM model used by multiple agents  │
│ ai_model_config         │ ai_agent (tts_model)    │ 1:M      │ TTS model used by multiple agents   │
│ ai_model_config         │ ai_agent (mem_model)    │ 1:M      │ Memory model used by multiple agents│
│ ai_model_config         │ ai_agent (intent_model) │ 1:M      │ Intent model used by multiple agents│
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_tts_voice            │ ai_agent                │ 1:M      │ Voice used by multiple agents       │
│ ai_tts_voice            │ ai_agent_template       │ 1:M      │ Voice used by multiple templates    │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_agent_template       │ ai_agent                │ Template │ Template basis for agent creation   │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_agent                │ ai_device               │ 1:M      │ Agent assigned to multiple devices  │
│ ai_agent                │ ai_voiceprint           │ 1:M      │ Agent recognizes multiple voices    │
│ ai_agent                │ ai_chat_history         │ 1:M      │ Agent in multiple chat sessions     │
│ ai_agent                │ ai_agent_chat_history   │ 1:M      │ Agent in multiple device chats      │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_device               │ ai_chat_history         │ 1:M      │ Device used in multiple chats       │
│ ai_device               │ ai_agent_chat_history   │ 1:M      │ Device connects via MAC address     │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_chat_history         │ ai_chat_message         │ 1:M      │ Chat session contains messages      │
├─────────────────────────┼─────────────────────────┼──────────┼─────────────────────────────────────┤
│ ai_agent_chat_history   │ ai_agent_chat_audio     │ 1:1      │ Chat entry may have audio data      │
└─────────────────────────┴─────────────────────────┴──────────┴─────────────────────────────────────┘
```

## 🎯 Foreign Key Reference Table

### Primary Foreign Key Relationships

```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┬─────────────────┐
│ TABLE                   │ FOREIGN KEY COLUMN      │ REFERENCES              │ CONSTRAINT TYPE │
├─────────────────────────┼─────────────────────────┼─────────────────────────┼─────────────────┤
│ sys_user_token          │ user_id                 │ sys_user.id             │ UNIQUE          │
│ sys_dict_data           │ dict_type_id            │ sys_dict_type.id        │ NOT NULL        │
│ ai_tts_voice            │ tts_model_id            │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ user_id                 │ sys_user.id             │ NULL ALLOWED    │
│ ai_agent                │ asr_model_id            │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ vad_model_id            │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ llm_model_id            │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ vllm_model_id           │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ tts_model_id            │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ tts_voice_id            │ ai_tts_voice.id         │ NULL ALLOWED    │
│ ai_agent                │ mem_model_id            │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_agent                │ intent_model_id         │ ai_model_config.id      │ NULL ALLOWED    │
│ ai_device               │ user_id                 │ sys_user.id             │ NULL ALLOWED    │
│ ai_device               │ agent_id                │ ai_agent.id             │ NULL ALLOWED    │
│ ai_voiceprint           │ user_id                 │ sys_user.id             │ NULL ALLOWED    │
│ ai_voiceprint           │ agent_id                │ ai_agent.id             │ NULL ALLOWED    │
│ ai_chat_history         │ user_id                 │ sys_user.id             │ NULL ALLOWED    │
│ ai_chat_history         │ agent_id                │ ai_agent.id             │ NULL ALLOWED    │
│ ai_chat_history         │ device_id               │ ai_device.id            │ NULL ALLOWED    │
│ ai_chat_message         │ user_id                 │ sys_user.id             │ NULL ALLOWED    │
│ ai_chat_message         │ chat_id                 │ ai_chat_history.id      │ NULL ALLOWED    │
│ ai_agent_chat_history   │ agent_id                │ ai_agent.id             │ NULL ALLOWED    │
│ ai_agent_chat_history   │ audio_id                │ ai_agent_chat_audio.id  │ NULL ALLOWED    │
└─────────────────────────┴─────────────────────────┴─────────────────────────┴─────────────────┘
```

## 📋 Table Dependency Hierarchy

### Level 0 (Independent Tables)
```
sys_user                 ← Root entity (users)
sys_dict_type           ← System dictionaries
sys_params              ← System parameters
ai_model_provider       ← AI model providers
ai_model_config         ← AI model configurations
ai_agent_chat_audio     ← Audio data storage
```

### Level 1 (Depends on Level 0)
```
sys_user_token          ← Depends on: sys_user
sys_dict_data           ← Depends on: sys_dict_type
ai_tts_voice            ← Depends on: ai_model_config
ai_agent_template       ← Independent template definitions
```

### Level 2 (Depends on Level 0-1)
```
ai_agent                ← Depends on: sys_user, ai_model_config, ai_tts_voice
```

### Level 3 (Depends on Level 0-2)
```
ai_device               ← Depends on: sys_user, ai_agent
ai_voiceprint           ← Depends on: sys_user, ai_agent
ai_chat_history         ← Depends on: sys_user, ai_agent, ai_device
ai_agent_chat_history   ← Depends on: ai_agent, ai_agent_chat_audio
```

### Level 4 (Depends on Level 0-3)
```
ai_chat_message         ← Depends on: sys_user, ai_chat_history
```

## 🔄 Data Flow Patterns

### User-Centric Flow
```
sys_user
├── Creates → ai_agent (using ai_agent_template)
├── Owns → ai_device
├── Trains → ai_voiceprint
├── Participates → ai_chat_history
└── Sends → ai_chat_message
```

### AI Agent Configuration Flow
```
ai_model_config
├── ASR Model → ai_agent.asr_model_id
├── VAD Model → ai_agent.vad_model_id
├── LLM Model → ai_agent.llm_model_id
├── VLLM Model → ai_agent.vllm_model_id
├── TTS Model → ai_agent.tts_model_id
├── Memory Model → ai_agent.mem_model_id
└── Intent Model → ai_agent.intent_model_id

ai_tts_voice → ai_agent.tts_voice_id
```

### Communication Flow
```
Web Interface:
sys_user → ai_chat_history → ai_chat_message

Device Interface:
ai_device (via MAC) → ai_agent_chat_history → ai_agent_chat_audio
```

### Device Management Flow
```
sys_user → ai_device → ai_agent (assignment)
ai_device → ai_agent_chat_history (via MAC address)
```

## 📊 Relationship Statistics

### Relationship Type Distribution
```
One-to-One:     2 relationships (8.0%)
One-to-Many:   20 relationships (80.0%)
Many-to-Many:   3 relationships (12.0%) [via foreign keys]
Template:       1 relationship (4.0%)
```

### Table Connection Density
```
Most Connected Tables:
1. sys_user (6 outgoing relationships)
2. ai_agent (4 outgoing relationships)
3. ai_model_config (7 outgoing relationships)
4. ai_device (2 outgoing relationships)

Least Connected Tables:
1. sys_params (0 relationships)
2. ai_model_provider (0 relationships)
3. ai_agent_chat_audio (1 incoming relationship)
```

### Critical Path Analysis
```
Core User Journey:
sys_user → ai_agent → ai_device → ai_agent_chat_history

Essential Configuration:
ai_model_config → ai_agent → ai_device

Communication Channels:
1. Web: sys_user → ai_chat_history → ai_chat_message
2. Device: ai_device → ai_agent_chat_history → ai_agent_chat_audio
```

---
*Generated: 2025-08-20 | Version: 1.0 | Format: Structured Text Matrix*
