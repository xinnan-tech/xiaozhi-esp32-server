# 🎯 **LIVEKIT MIGRATION PLAN**
## Replace xiaozhi-server with agent-starter-python + LiveKit

---

## **🏗️ CURRENT ARCHITECTURE vs TARGET ARCHITECTURE**

### **Current Flow:**
```
ESP32 Device → MQTT Gateway → xiaozhi-server → Manager-API → Database
                     ↕️                    ↕️
                WebSocket           Config/Chat History
```

### **Target Flow:**
```
ESP32 Device → MQTT Gateway → agent-starter-python (LiveKit) → Manager-API → Database
                     ↕️                           ↕️
                WebRTC/LiveKit              Config/Chat History
```

---

## **📋 DETAILED TASK BREAKDOWN**

### **PHASE 1: Agent-Starter-Python Modifications**

#### **1.1 Configuration Management Integration**
**File: `src/config_loader.py` (NEW)**
```python
# Integration with manager-api for dynamic configuration
- Load agent configuration from manager-api instead of .env
- Support for multiple model providers (ASR, LLM, TTS, VAD)
- Dynamic agent personality/system prompts
- Multi-language support
```

**Tasks:**
- [ ] Create HTTP client for manager-api communication
- [ ] Implement configuration polling/caching mechanism
- [ ] Add support for all model types from manager-api
- [ ] Handle configuration updates without restart

#### **1.2 Database Integration & Chat History**
**File: `src/database_client.py` (NEW)**
```python
# Direct database connection to manager-api MySQL
- Chat history reporting in real-time
- Audio data storage and retrieval
- Session management
- Device/agent binding validation
```

**Tasks:**
- [ ] Add MySQL connector and ORM (SQLAlchemy)
- [ ] Implement chat history models matching manager-api schema
- [ ] Create real-time chat/audio logging
- [ ] Add session tracking and management

#### **1.3 Enhanced Agent Class**
**File: `src/agent.py` (MODIFY)**
```python
class XiaozhiAgent(Agent):
    def __init__(self, agent_config, device_info):
        # Dynamic system prompt from database
        # Configurable model pipeline
        # Custom function tools from MCP integration
        # Multi-language support
```

**Tasks:**
- [ ] Replace static configuration with dynamic loading
- [ ] Add multi-language support and locale handling
- [ ] Implement custom function tools from manager-api
- [ ] Add device-specific personalization
- [ ] Support memory/context from previous conversations

#### **1.4 MQTT Gateway Integration**
**File: `src/mqtt_client.py` (NEW)**
```python
# Bridge between ESP32 MQTT and LiveKit
- Device authentication and binding
- Command/control message handling
- Status reporting back to manager-api
- OTA update coordination
```

**Tasks:**
- [ ] Implement MQTT client for ESP32 communication
- [ ] Add device authentication using MAC address
- [ ] Create message routing between MQTT and LiveKit
- [ ] Handle device commands and status updates

#### **1.5 LiveKit Room Management**
**File: `src/room_manager.py` (NEW)**
```python
# Dynamic room creation and management
- Device-based room naming (MAC address)
- Room lifecycle management
- Participant authentication
- Recording and analytics
```

**Tasks:**
- [ ] Implement room creation per device/agent pair
- [ ] Add JWT token generation for device access
- [ ] Create room cleanup and management
- [ ] Add participant authentication and authorization

### **PHASE 2: Manager-API Modifications**

#### **2.1 LiveKit Integration Endpoints**
**File: `AgentController.java` (MODIFY)**

**New Endpoints:**
- [ ] `GET /agent/livekit-config/{macAddress}` - Get LiveKit configuration for device
- [ ] `POST /agent/livekit-token/{macAddress}` - Generate LiveKit JWT token
- [ ] `POST /agent/room/create` - Create LiveKit room for device
- [ ] `DELETE /agent/room/{roomId}` - Clean up LiveKit room

#### **2.2 Real-time Chat History API**
**File: `AgentChatHistoryController.java` (MODIFY)**

**New Endpoints:**
- [ ] `POST /agent/chat-history/stream` - Real-time chat history streaming
- [ ] `WebSocket /agent/chat-history/live/{agentId}` - Live chat monitoring
- [ ] `GET /agent/chat-history/session/{sessionId}/download` - Export session data

#### **2.3 Configuration Distribution API**
**File: `ConfigController.java` (MODIFY)**

**Modified Endpoints:**
- [ ] `POST /config/livekit-agent` - Get agent configuration for LiveKit
- [ ] `GET /config/livekit-server` - Get LiveKit server connection details
- [ ] `POST /config/update-agent/{agentId}` - Hot-reload agent configuration

#### **2.4 Device Management Updates**
**File: `DeviceController.java` (MODIFY)**

**New Features:**
- [ ] LiveKit room ID tracking in device entity
- [ ] Real-time device status via LiveKit presence
- [ ] Audio quality metrics from LiveKit
- [ ] Connection status monitoring

### **PHASE 3: Database Schema Updates**

#### **3.1 Device Entity Extensions**
```sql
ALTER TABLE ai_device ADD COLUMN livekit_room_id VARCHAR(255);
ALTER TABLE ai_device ADD COLUMN last_livekit_session VARCHAR(255);
ALTER TABLE ai_device ADD COLUMN connection_status ENUM('online', 'offline', 'connecting');
ALTER TABLE ai_device ADD COLUMN audio_quality_score DECIMAL(3,2);
```

#### **3.2 Chat History Extensions**
```sql
ALTER TABLE ai_agent_chat_history ADD COLUMN livekit_session_id VARCHAR(255);
ALTER TABLE ai_agent_chat_history ADD COLUMN participant_id VARCHAR(255);
ALTER TABLE ai_agent_chat_history ADD COLUMN audio_duration_ms INT;
ALTER TABLE ai_agent_chat_history ADD COLUMN transcription_confidence DECIMAL(3,2);
```

#### **3.3 New LiveKit Configuration Table**
```sql
CREATE TABLE ai_livekit_config (
    id VARCHAR(36) PRIMARY KEY,
    server_url VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    api_secret VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **PHASE 4: ESP32 Firmware Updates**

#### **4.1 LiveKit Client Integration**
**Tasks:**
- [ ] Replace WebSocket client with LiveKit ESP32 SDK
- [ ] Implement WebRTC audio streaming
- [ ] Add JWT token authentication
- [ ] Update connection management for LiveKit rooms

#### **4.2 MQTT Bridge Maintenance**
**Tasks:**
- [ ] Keep MQTT for device control and status
- [ ] Route audio through LiveKit WebRTC
- [ ] Maintain backward compatibility during transition
- [ ] Add configuration switching mechanism

### **PHASE 5: Deployment & Migration**

#### **5.1 Gradual Migration Strategy**
```
Current: xiaozhi-server → Parallel: Both Systems → Gradual Device Migration → Full LiveKit Migration → Decommission xiaozhi-server
```

**Tasks:**
- [ ] Deploy agent-starter-python alongside xiaozhi-server
- [ ] Create device migration flags in manager-api
- [ ] Implement A/B testing for device groups
- [ ] Monitor performance and stability metrics
- [ ] Gradual traffic migration (10%, 50%, 100%)

#### **5.2 Configuration Migration**
**Tasks:**
- [ ] Export existing agent configurations
- [ ] Map xiaozhi-server configs to LiveKit format
- [ ] Migrate chat history and session data
- [ ] Update device firmware OTA for LiveKit support

---

## **🔄 MINIMAL CHANGES APPROACH**

### **Immediate Quick Wins (Minimal Impact):**

1. **Keep Manager-API Structure Intact**
   - No major database schema changes initially
   - Reuse existing device/agent management
   - Maintain current web dashboard

2. **Bridge Pattern Implementation**
   - agent-starter-python acts as xiaozhi-server replacement
   - Same HTTP APIs for configuration loading
   - Same chat history reporting endpoints
   - Same device binding process

3. **Gradual Feature Addition**
   - Start with basic voice interaction
   - Add advanced features incrementally
   - Maintain backward compatibility

### **Configuration Loading (Minimal Changes)**

**Current xiaozhi-server:**
```python
config = get_config_from_api(device_mac)
# Initialize ASR, LLM, TTS, VAD modules
```

**New agent-starter-python:**
```python
config = get_config_from_manager_api(device_mac)
session = AgentSession(
    llm=create_llm_from_config(config['llm']),
    stt=create_stt_from_config(config['asr']),
    tts=create_tts_from_config(config['tts']),
    vad=create_vad_from_config(config['vad'])
)
```

### **Function Calls & Tools Integration**

**Current MCP Integration:**
- [ ] Map existing MCP tools to LiveKit function_tool decorator
- [ ] Maintain same tool discovery and execution
- [ ] Bridge MCP protocol to LiveKit agent tools

**Example:**
```python
@function_tool
async def iot_device_control(context: RunContext, device: str, action: str):
    # Same underlying MCP call as xiaozhi-server
    return await mcp_client.call_tool("iot_device_control", device, action)
```

---

## **🚀 IMPLEMENTATION PRIORITY**

### **Phase 1 (2-3 weeks): Core Replacement**
1. Create configuration loader for manager-api
2. Modify agent.py for dynamic configuration
3. Add basic chat history reporting
4. Test with single device

### **Phase 2 (2-3 weeks): Full Integration**
1. MQTT gateway integration
2. Room management and JWT tokens
3. Manager-API endpoint updates
4. Multi-device testing

### **Phase 3 (1-2 weeks): Migration & Polish**
1. Device firmware updates
2. Gradual migration tools
3. Performance optimization
4. Documentation and training

---

## **⚡ EXPECTED BENEFITS**

1. **Better Real-time Performance**: WebRTC vs WebSocket
2. **Improved Audio Quality**: Built-in noise cancellation, echo cancellation
3. **Scalability**: LiveKit's distributed architecture
4. **Modern Tech Stack**: Active development and community
5. **Advanced Features**: Video support, screen sharing, recording
6. **Reduced Complexity**: Eliminate custom WebSocket management

---

## **🔧 EXISTING ARCHITECTURE ANALYSIS**

### **Current xiaozhi-server Components:**
- **WebSocket Server**: Handles ESP32 device connections
- **Module Pipeline**: VAD → ASR → LLM → TTS → Intent
- **Configuration Management**: Dynamic config loading from manager-api
- **MQTT Bridge**: Communication with MQTT gateway
- **Memory Management**: Conversation context and history
- **Tool Integration**: MCP protocol for external tools

### **Manager-API Integration Points:**
- **Agent Management**: CRUD operations for AI agents
- **Device Binding**: MAC address-based device registration
- **Configuration Distribution**: Model pipeline settings
- **Chat History Collection**: Conversation logging and storage
- **User Management**: Multi-tenant user system
- **OTA Updates**: Firmware distribution

### **Key Files to Modify:**

#### **agent-starter-python:**
- `src/agent.py` - Main agent class
- `src/config_loader.py` - NEW: Manager-API integration
- `src/database_client.py` - NEW: Direct DB access
- `src/mqtt_client.py` - NEW: MQTT bridge
- `src/room_manager.py` - NEW: LiveKit room management
- `.env` - Configuration parameters

#### **manager-api:**
- `AgentController.java` - LiveKit endpoints
- `ConfigController.java` - LiveKit configuration
- `DeviceController.java` - LiveKit device management
- Database schema updates

This plan provides a comprehensive roadmap for migrating from xiaozhi-server to LiveKit while maintaining system functionality and minimizing disruption.