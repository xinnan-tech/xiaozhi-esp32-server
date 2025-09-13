# MQTT Gateway Communication Flow & Message Types

This document provides a comprehensive analysis of the MQTT gateway communication flow and all message types exchanged between the main server (xiaozhi-server), MQTT gateway, and clients.

## 🔄 Communication Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐    MQTT    ┌─────────────────┐
│   Main Server   │ ◄──────────────► │  MQTT Gateway   │ ◄─────────► │     Client      │
│ (xiaozhi-server)│                  │    (Node.js)    │             │   (ESP32/Test)  │
└─────────────────┘                  └─────────────────┘             └─────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  UDP Audio      │
                                    │  Streaming      │
                                    └─────────────────┘
```

### Key Components:

1. **Main Server (xiaozhi-server)**: Python-based AI server handling TTS/STT/LLM processing
2. **MQTT Gateway**: Node.js bridge converting between WebSocket (server) and MQTT (client)
3. **Client**: ESP32 device or test client connecting via MQTT
4. **UDP Audio Stream**: Encrypted real-time audio data transmission

## 📤 Message Flow Triggers

### 1. Client → MQTT Gateway → Server
Clients publish to the `"device-server"` topic, which the MQTT gateway forwards to the main server via WebSocket:

```javascript
// Client publishes to "device-server" topic
mqtt_client.publish("device-server", JSON.stringify({
    "type": "hello",
    "version": 3,
    "transport": "mqtt",
    "audio_params": {...},
    "features": [...]
}))
```

### 2. Server → MQTT Gateway → Client  
The server sends messages via WebSocket to the MQTT gateway, which publishes to the client's unique P2P topic:

```javascript
// Gateway publishes to client's P2P topic: "devices/p2p/{mac_address}"
connection.sendMqttMessage(JSON.stringify({
    "type": "tts",
    "state": "start", 
    "session_id": session_id
}))
```

### 3. Audio Streaming (Server ↔ Client)
Real-time audio data bypasses MQTT and flows directly via encrypted UDP packets for low latency.

## 📨 Complete MQTT Message Types

### 🔄 Connection & Session Management

#### 1. `hello` - Session Initiation
**Direction**: Client → Server, Server → Client  
**Purpose**: Establish session and exchange capabilities

**Client Request:**
```json
{
  "type": "hello",
  "version": 3,
  "transport": "mqtt",
  "audio_params": {
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 20,
    "format": "opus"
  },
  "features": ["tts", "asr", "vad"]
}
```

**Server Response:**
```json
{
  "type": "hello",
  "version": 3,
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058",
  "transport": "udp",
  "udp": {
    "server": "64.227.170.31",
    "port": 8884,
    "encryption": "aes-128-ctr",
    "key": "b6e228c4e0f5d0b93e6fac787786d303",
    "nonce": "010000008e863dda0000000000000000"
  },
  "audio_params": {
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 20,
    "format": "opus"
  }
}
```

#### 2. `goodbye` - Session Termination
**Direction**: Client ↔ Server  
**Purpose**: Clean session termination

```json
{
  "type": "goodbye",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

### 🎤 Speech Recognition Messages

#### 3. `stt` - Speech-to-Text Results
**Direction**: Server → Client  
**Purpose**: Send transcribed speech back to client

```json
{
  "type": "stt",
  "text": "hello baby",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

#### 4. `listen` - Request Speech Processing
**Direction**: Client → Server  
**Purpose**: Request server to start listening/processing speech

```json
{
  "type": "listen",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058",
  "state": "detect",
  "text": "hello baby"
}
```

### 🔊 Text-to-Speech Control Messages

#### 5. `tts` - TTS Playback Control
**Direction**: Server → Client  
**Purpose**: Control TTS playback states

**Available States**: `start`, `sentence_start`, `stop`

**TTS Start:**
```json
{
  "type": "tts",
  "state": "start",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

**Sentence Start (with text preview):**
```json
{
  "type": "tts",
  "state": "sentence_start",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058",
  "text": "Hi there"
}
```

**TTS Stop:**
```json
{
  "type": "tts",
  "state": "stop",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

**Note**: There is no `sentence_stop` or `sentence_end` state. Individual sentences are marked with `sentence_start`, and the entire TTS session ends with `stop`.

### 🤖 AI Response Messages

#### 6. `llm` - Large Language Model Response
**Direction**: Server → Client  
**Purpose**: Send AI-generated response with emotion context

```json
{
  "type": "llm",
  "text": "😊",
  "emotion": "happy",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

### ⏹️ Control Messages

#### 7. `abort` - Abort Current Operation
**Direction**: Client → Server  
**Purpose**: Stop current TTS playback or processing

```json
{
  "type": "abort",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

#### 8. `record_stop` - Stop Audio Recording
**Direction**: Server → Client  
**Purpose**: Instruct client to stop recording audio

```json
{
  "type": "record_stop",
  "session_id": "db4ead3e-c5e2-4dd4-bbf1-0295195e5058"
}
```

## 🎯 Server Message Trigger Points

### In `core/handle/sendAudioHandle.py`:
- **`send_tts_message()`**: Triggers TTS state messages (`start`, `sentence_start`, `stop`)
- **`send_stt_message()`**: Triggers STT transcription messages
- **`sendAudioMessage()`**: Coordinates TTS playback with state messages
- Called during the audio processing pipeline

### In `core/handle/helloHandle.py`:
- **`handleHelloMessage()`**: Triggers the initial hello response with session details
- **`checkWakeupWords()`**: Can trigger STT and TTS messages for wake word responses
- **`wakeupWordsResponse()`**: Generates dynamic wake word responses

### In MQTT Gateway (`mqtt-gateway/app.js`):
- **`parseHelloMessage()`**: Processes hello messages and sends session details
- **`parseOtherMessage()`**: Forwards messages between server and client
- **`sendMqttMessage()`**: Publishes messages to client's P2P topic
- **`sendUdpMessage()`**: Handles encrypted audio streaming via UDP

## 📊 Typical Message Flow Sequence

### 1. Session Establishment
```
Client → MQTT Gateway: hello (with capabilities)
MQTT Gateway → Server: hello (forwarded via WebSocket)
Server → MQTT Gateway: hello (with session_id and UDP details)
MQTT Gateway → Client: hello (published to P2P topic)
```

### 2. Audio Setup
```
Client: Establishes UDP connection using provided encryption keys
Client: Sends UDP ping to confirm connection
```

### 3. Conversation Flow
```
Client → Server: listen (request to start conversation)
Server → Client: stt (transcription of client speech)
Server → Client: tts (state: "start")
Server → Client: tts (state: "sentence_start", text: preview)
Server → Client: llm (AI response with emotion)
Server ⟶ Client: [UDP Audio Stream] (actual TTS audio)
Server → Client: tts (state: "stop")
```

### 4. Session Termination
```
Client → Server: goodbye
Server → Client: goodbye (acknowledgment)
```

## 🔧 Implementation Details

### MQTT Topics
- **Uplink**: `device-server` (client to server messages)
- **Downlink**: `devices/p2p/{mac_address}` (server to specific client)

### Audio Streaming
- **Protocol**: UDP with AES-128-CTR encryption
- **Format**: Opus codec, 16kHz, mono
- **Frame Duration**: 20ms per packet
- **Encryption**: Header used as nonce, payload encrypted

### Session Management
- **Session ID**: UUID generated for each connection
- **Authentication**: HMAC-SHA256 signed client credentials
- **Keep-alive**: MQTT ping/pong mechanism

### Error Handling
- **Timeout**: Automatic retry for failed messages
- **Connection Loss**: Graceful degradation and reconnection
- **Audio Issues**: Buffer management for packet loss

## 🚨 Key Observations

- **Hybrid Protocol**: MQTT for control messages, UDP for real-time audio streaming
- **Session-based**: All messages include `session_id` for correlation
- **Bidirectional**: Both client and server can initiate certain message types
- **State Machine**: TTS has multiple states for precise playback control
- **Real-time Audio**: Audio packets bypass MQTT for optimal latency
- **P2P Topics**: Each client has a unique MQTT topic for targeted messaging
- **Encryption**: End-to-end encryption for audio data
- **Scalable**: Architecture supports multiple concurrent clients

## 📚 Related Files

### Server-side:
- `core/handle/sendAudioHandle.py` - TTS/STT message handling
- `core/handle/helloHandle.py` - Session establishment
- `core/websocket_server.py` - WebSocket connection management

### MQTT Gateway:
- `mqtt-gateway/app.js` - Main gateway implementation
- `mqtt-gateway/mqtt-protocol.js` - MQTT protocol handling
- `mqtt-gateway/utils/mqtt_config_v2.js` - Client authentication

### Client:
- `client.py` - Test client implementation
- Client logs show actual message flow in practice

---
*Generated on: 2025-09-12*  
*Analysis based on xiaozhi-esp32-server codebase and client logs*
