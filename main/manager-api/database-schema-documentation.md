# Xiaozhi ESP32 Server - Database Schema Documentation

## 📋 Overview

This document provides a comprehensive overview of the database schema for the Xiaozhi ESP32 Server system. The system is designed to manage AI-powered voice assistants that run on ESP32 devices, with a web-based management interface.

## 🗄️ Database Structure

The database consists of **16 main tables** organized into **6 functional categories**:

### 1. 🔐 System Management Tables (5 tables)

#### `sys_user` - System Users
**Purpose**: Manages user accounts and authentication
```sql
CREATE TABLE sys_user (
  id bigint NOT NULL COMMENT 'User ID',
  username varchar(50) NOT NULL COMMENT 'Username',
  password varchar(100) COMMENT 'Password',
  super_admin tinyint unsigned COMMENT 'Super Admin (0:No 1:Yes)',
  status tinyint COMMENT 'Status (0:Disabled 1:Active)',
  create_date datetime COMMENT 'Creation Time',
  updater bigint COMMENT 'Updater',
  creator bigint COMMENT 'Creator',
  update_date datetime COMMENT 'Update Time',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username)
);
```

#### `sys_user_token` - User Authentication Tokens
**Purpose**: Manages user session tokens for API authentication
```sql
CREATE TABLE sys_user_token (
  id bigint NOT NULL COMMENT 'Token ID',
  user_id bigint NOT NULL COMMENT 'User ID',
  token varchar(100) NOT NULL COMMENT 'User Token',
  expire_date datetime COMMENT 'Expiration Date',
  update_date datetime COMMENT 'Update Time',
  create_date datetime COMMENT 'Creation Time',
  PRIMARY KEY (id),
  UNIQUE KEY user_id (user_id),
  UNIQUE KEY token (token)
);
```

#### `sys_params` - System Parameters
**Purpose**: Stores system configuration parameters
```sql
CREATE TABLE sys_params (
  id bigint NOT NULL COMMENT 'Parameter ID',
  param_code varchar(32) COMMENT 'Parameter Code',
  param_value varchar(2000) COMMENT 'Parameter Value',
  param_type tinyint unsigned default 1 COMMENT 'Type (0:System 1:Non-System)',
  remark varchar(200) COMMENT 'Remark',
  creator bigint COMMENT 'Creator',
  create_date datetime COMMENT 'Creation Time',
  updater bigint COMMENT 'Updater',
  update_date datetime COMMENT 'Update Time',
  PRIMARY KEY (id),
  UNIQUE KEY uk_param_code (param_code)
);
```

#### `sys_dict_type` - Dictionary Types
**Purpose**: Defines dictionary categories for system data
```sql
CREATE TABLE sys_dict_type (
  id bigint NOT NULL COMMENT 'Dictionary Type ID',
  dict_type varchar(100) NOT NULL COMMENT 'Dictionary Type',
  dict_name varchar(255) NOT NULL COMMENT 'Dictionary Name',
  remark varchar(255) COMMENT 'Remark',
  sort int unsigned COMMENT 'Sort Order',
  creator bigint COMMENT 'Creator',
  create_date datetime COMMENT 'Creation Time',
  updater bigint COMMENT 'Updater',
  update_date datetime COMMENT 'Update Time',
  PRIMARY KEY (id),
  UNIQUE KEY(dict_type)
);
```

#### `sys_dict_data` - Dictionary Data
**Purpose**: Stores dictionary data entries
```sql
CREATE TABLE sys_dict_data (
  id bigint NOT NULL COMMENT 'Dictionary Data ID',
  dict_type_id bigint NOT NULL COMMENT 'Dictionary Type ID',
  dict_label varchar(255) NOT NULL COMMENT 'Dictionary Label',
  dict_value varchar(255) COMMENT 'Dictionary Value',
  remark varchar(255) COMMENT 'Remark',
  sort int unsigned COMMENT 'Sort Order',
  creator bigint COMMENT 'Creator',
  create_date datetime COMMENT 'Creation Time',
  updater bigint COMMENT 'Updater',
  update_date datetime COMMENT 'Update Time',
  PRIMARY KEY (id),
  UNIQUE KEY uk_dict_type_value (dict_type_id, dict_value),
  KEY idx_sort (sort)
);
```

### 2. 🤖 AI Model Configuration Tables (3 tables)

#### `ai_model_provider` - Model Providers
**Purpose**: Manages AI model providers (OpenAI, Alibaba, etc.)
```sql
CREATE TABLE ai_model_provider (
  id VARCHAR(32) NOT NULL COMMENT 'Provider ID',
  model_type VARCHAR(20) COMMENT 'Model Type (Memory/ASR/VAD/LLM/TTS)',
  provider_code VARCHAR(50) COMMENT 'Provider Code',
  name VARCHAR(50) COMMENT 'Provider Name',
  fields JSON COMMENT 'Provider Fields (JSON format)',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Order',
  creator BIGINT COMMENT 'Creator',
  create_date DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater',
  update_date DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id),
  INDEX idx_ai_model_provider_model_type (model_type)
);
```

#### `ai_model_config` - Model Configurations
**Purpose**: Stores specific AI model configurations
```sql
CREATE TABLE ai_model_config (
  id VARCHAR(32) NOT NULL COMMENT 'Model Config ID',
  model_type VARCHAR(20) COMMENT 'Model Type (Memory/ASR/VAD/LLM/TTS)',
  model_code VARCHAR(50) COMMENT 'Model Code',
  model_name VARCHAR(50) COMMENT 'Model Name',
  is_default TINYINT(1) DEFAULT 0 COMMENT 'Is Default (0:No 1:Yes)',
  is_enabled TINYINT(1) DEFAULT 0 COMMENT 'Is Enabled',
  config_json JSON COMMENT 'Model Configuration (JSON)',
  doc_link VARCHAR(200) COMMENT 'Documentation Link',
  remark VARCHAR(255) COMMENT 'Remark',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Order',
  creator BIGINT COMMENT 'Creator',
  create_date DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater',
  update_date DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id),
  INDEX idx_ai_model_config_model_type (model_type)
);
```

#### `ai_tts_voice` - TTS Voice Configurations
**Purpose**: Manages Text-to-Speech voice options
```sql
CREATE TABLE ai_tts_voice (
  id VARCHAR(32) NOT NULL COMMENT 'Voice ID',
  tts_model_id VARCHAR(32) COMMENT 'TTS Model ID',
  name VARCHAR(20) COMMENT 'Voice Name',
  tts_voice VARCHAR(50) COMMENT 'Voice Code',
  languages VARCHAR(50) COMMENT 'Supported Languages',
  voice_demo VARCHAR(500) DEFAULT NULL COMMENT 'Voice Demo URL',
  remark VARCHAR(255) COMMENT 'Remark',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Order',
  creator BIGINT COMMENT 'Creator',
  create_date DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater',
  update_date DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id),
  INDEX idx_ai_tts_voice_tts_model_id (tts_model_id)
);
```

### 3. 🧠 AI Agent Management Tables (2 tables)

#### `ai_agent_template` - Agent Templates
**Purpose**: Predefined AI agent configurations that users can use as starting points
```sql
CREATE TABLE ai_agent_template (
  id VARCHAR(32) NOT NULL COMMENT 'Agent Template ID',
  agent_code VARCHAR(36) COMMENT 'Agent Code',
  agent_name VARCHAR(64) COMMENT 'Agent Name',
  asr_model_id VARCHAR(32) COMMENT 'ASR Model ID',
  vad_model_id VARCHAR(64) COMMENT 'VAD Model ID',
  llm_model_id VARCHAR(32) COMMENT 'LLM Model ID',
  vllm_model_id VARCHAR(32) COMMENT 'VLLM Model ID',
  tts_model_id VARCHAR(32) COMMENT 'TTS Model ID',
  tts_voice_id VARCHAR(32) COMMENT 'TTS Voice ID',
  mem_model_id VARCHAR(32) COMMENT 'Memory Model ID',
  intent_model_id VARCHAR(32) COMMENT 'Intent Model ID',
  system_prompt TEXT COMMENT 'System Prompt',
  lang_code VARCHAR(10) COMMENT 'Language Code',
  language VARCHAR(10) COMMENT 'Interaction Language',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Weight',
  creator BIGINT COMMENT 'Creator ID',
  created_at DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater ID',
  updated_at DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id)
);
```

#### `ai_agent` - User AI Agents
**Purpose**: User-created AI agents with custom configurations
```sql
CREATE TABLE ai_agent (
  id VARCHAR(32) NOT NULL COMMENT 'Agent ID',
  user_id BIGINT COMMENT 'Owner User ID',
  agent_code VARCHAR(36) COMMENT 'Agent Code',
  agent_name VARCHAR(64) COMMENT 'Agent Name',
  asr_model_id VARCHAR(32) COMMENT 'ASR Model ID',
  vad_model_id VARCHAR(64) COMMENT 'VAD Model ID',
  llm_model_id VARCHAR(32) COMMENT 'LLM Model ID',
  vllm_model_id VARCHAR(32) COMMENT 'VLLM Model ID',
  tts_model_id VARCHAR(32) COMMENT 'TTS Model ID',
  tts_voice_id VARCHAR(32) COMMENT 'TTS Voice ID',
  mem_model_id VARCHAR(32) COMMENT 'Memory Model ID',
  intent_model_id VARCHAR(32) COMMENT 'Intent Model ID',
  system_prompt TEXT COMMENT 'System Prompt',
  lang_code VARCHAR(10) COMMENT 'Language Code',
  language VARCHAR(10) COMMENT 'Interaction Language',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Weight',
  creator BIGINT COMMENT 'Creator ID',
  created_at DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater ID',
  updated_at DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id),
  INDEX idx_ai_agent_user_id (user_id)
);
```

### 4. 📱 Device Management Tables (1 table)

#### `ai_device` - ESP32 Device Information
**Purpose**: Manages ESP32 devices and their configurations
```sql
CREATE TABLE ai_device (
  id VARCHAR(32) NOT NULL COMMENT 'Device ID',
  user_id BIGINT COMMENT 'Associated User ID',
  mac_address VARCHAR(50) COMMENT 'MAC Address',
  last_connected_at DATETIME COMMENT 'Last Connection Time',
  auto_update TINYINT UNSIGNED DEFAULT 0 COMMENT 'Auto Update (0:Off 1:On)',
  board VARCHAR(50) COMMENT 'Hardware Model',
  alias VARCHAR(64) DEFAULT NULL COMMENT 'Device Alias',
  agent_id VARCHAR(32) COMMENT 'Assigned Agent ID',
  app_version VARCHAR(20) COMMENT 'Firmware Version',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Order',
  creator BIGINT COMMENT 'Creator',
  create_date DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater',
  update_date DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id),
  INDEX idx_ai_device_created_at (mac_address)
);
```

### 5. 🔊 Voice Recognition Tables (1 table)

#### `ai_voiceprint` - Voice Print Recognition
**Purpose**: Stores voice print data for user identification
```sql
CREATE TABLE ai_voiceprint (
  id VARCHAR(32) NOT NULL COMMENT 'Voiceprint ID',
  name VARCHAR(64) COMMENT 'Voiceprint Name',
  user_id BIGINT COMMENT 'User ID',
  agent_id VARCHAR(32) COMMENT 'Associated Agent ID',
  agent_code VARCHAR(36) COMMENT 'Associated Agent Code',
  agent_name VARCHAR(36) COMMENT 'Associated Agent Name',
  description VARCHAR(255) COMMENT 'Voiceprint Description',
  embedding LONGTEXT COMMENT 'Voice Feature Vector (JSON)',
  memory TEXT COMMENT 'Associated Memory Data',
  sort INT UNSIGNED DEFAULT 0 COMMENT 'Sort Weight',
  creator BIGINT COMMENT 'Creator ID',
  created_at DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater ID',
  updated_at DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id)
);
```

### 6. 💬 Chat & Communication Tables (4 tables)

#### `ai_chat_history` - Web Chat Sessions
**Purpose**: Manages web-based chat sessions
```sql
CREATE TABLE ai_chat_history (
  id VARCHAR(32) NOT NULL COMMENT 'Chat Session ID',
  user_id BIGINT COMMENT 'User ID',
  agent_id VARCHAR(32) DEFAULT NULL COMMENT 'Chat Agent',
  device_id VARCHAR(32) DEFAULT NULL COMMENT 'Device ID',
  message_count INT COMMENT 'Message Count',
  creator BIGINT COMMENT 'Creator',
  create_date DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater',
  update_date DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id)
);
```

#### `ai_chat_message` - Web Chat Messages
**Purpose**: Stores individual chat messages from web interface
```sql
CREATE TABLE ai_chat_message (
  id VARCHAR(32) NOT NULL COMMENT 'Message ID',
  user_id BIGINT COMMENT 'User ID',
  chat_id VARCHAR(64) COMMENT 'Chat History ID',
  role ENUM('user', 'assistant') COMMENT 'Role (user/assistant)',
  content TEXT COMMENT 'Message Content',
  prompt_tokens INT UNSIGNED DEFAULT 0 COMMENT 'Prompt Tokens',
  total_tokens INT UNSIGNED DEFAULT 0 COMMENT 'Total Tokens',
  completion_tokens INT UNSIGNED DEFAULT 0 COMMENT 'Completion Tokens',
  prompt_ms INT UNSIGNED DEFAULT 0 COMMENT 'Prompt Time (ms)',
  total_ms INT UNSIGNED DEFAULT 0 COMMENT 'Total Time (ms)',
  completion_ms INT UNSIGNED DEFAULT 0 COMMENT 'Completion Time (ms)',
  creator BIGINT COMMENT 'Creator',
  create_date DATETIME COMMENT 'Creation Time',
  updater BIGINT COMMENT 'Updater',
  update_date DATETIME COMMENT 'Update Time',
  PRIMARY KEY (id),
  INDEX idx_ai_chat_message_user_id_chat_id_role (user_id, chat_id),
  INDEX idx_ai_chat_message_created_at (create_date)
);
```

#### `ai_agent_chat_history` - Device Chat History
**Purpose**: Stores chat interactions from ESP32 devices
```sql
CREATE TABLE ai_agent_chat_history (
  id BIGINT AUTO_INCREMENT COMMENT 'Primary Key ID' PRIMARY KEY,
  mac_address VARCHAR(50) COMMENT 'MAC Address',
  agent_id VARCHAR(32) COMMENT 'Agent ID',
  session_id VARCHAR(50) COMMENT 'Session ID',
  chat_type TINYINT(3) COMMENT 'Message Type (1:User, 2:Agent)',
  content VARCHAR(1024) COMMENT 'Chat Content',
  audio_id VARCHAR(32) COMMENT 'Audio ID',
  created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL COMMENT 'Creation Time',
  updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL ON UPDATE CURRENT_TIMESTAMP(3) COMMENT 'Update Time',
  INDEX idx_ai_agent_chat_history_mac (mac_address),
  INDEX idx_ai_agent_chat_history_session_id (session_id),
  INDEX idx_ai_agent_chat_history_agent_id (agent_id),
  INDEX idx_ai_agent_chat_history_agent_session_created (agent_id, session_id, created_at)
);
```

#### `ai_agent_chat_audio` - Device Chat Audio Data
**Purpose**: Stores audio data from device interactions
```sql
CREATE TABLE ai_agent_chat_audio (
  id VARCHAR(32) COMMENT 'Audio ID' PRIMARY KEY,
  audio LONGBLOB COMMENT 'Audio OPUS Data'
);
```

## 🔗 Key Relationships

### Primary Relationships:
1. **`sys_user`** → **`ai_agent`** (One-to-Many): Users can create multiple AI agents
2. **`sys_user`** → **`ai_device`** (One-to-Many): Users can own multiple ESP32 devices
3. **`ai_agent`** → **`ai_device`** (One-to-Many): An agent can be assigned to multiple devices
4. **`ai_model_config`** → **`ai_agent`** (Many-to-Many): Agents use multiple model configurations
5. **`ai_tts_voice`** → **`ai_agent`** (Many-to-One): Agents use specific TTS voices

### Secondary Relationships:
1. **`sys_dict_type`** → **`sys_dict_data`** (One-to-Many)
2. **`sys_user`** → **`sys_user_token`** (One-to-One)
3. **`ai_agent_template`** → **`ai_agent`** (Template-based creation)
4. **`ai_device`** → **`ai_agent_chat_history`** (via MAC address)
5. **`ai_agent_chat_history`** → **`ai_agent_chat_audio`** (One-to-One)

## 🎯 System Architecture Insights

### AI Model Pipeline:
The system supports a modular AI pipeline with separate configurations for:
- **ASR** (Automatic Speech Recognition)
- **VAD** (Voice Activity Detection)
- **LLM** (Large Language Model)
- **VLLM** (Vision Large Language Model)
- **TTS** (Text-to-Speech)
- **Memory** (Conversation Memory)
- **Intent** (Intent Recognition)

### Multi-Channel Communication:
1. **Web Interface**: `ai_chat_history` + `ai_chat_message`
2. **Device Interface**: `ai_agent_chat_history` + `ai_agent_chat_audio`

### User Management:
- Role-based access with super admin capabilities
- Token-based authentication for API access
- User ownership of agents, devices, and voiceprints

### Device Management:
- MAC address-based device identification
- Firmware version tracking
- Auto-update capabilities
- Agent assignment per device

## 📊 Database Statistics

- **Total Tables**: 16
- **System Tables**: 5
- **AI Configuration Tables**: 3
- **Agent Management Tables**: 2
- **Device Management Tables**: 1
- **Voice Recognition Tables**: 1
- **Communication Tables**: 4

## 🔧 Technical Notes

### Indexing Strategy:
- Primary keys on all tables
- Foreign key indexes for performance
- Composite indexes for complex queries
- Time-based indexes for chat history

### Data Types:
- **VARCHAR(32)** for UUIDs and IDs
- **JSON** for flexible configuration storage
- **LONGTEXT/LONGBLOB** for large data (embeddings, audio)
- **DATETIME(3)** for millisecond precision timestamps

### Character Set:
- **utf8mb4** for full Unicode support including emojis

---

*Generated on: 2025-08-20*  
*Database Version: Latest*  
*Documentation Version: 1.0*
