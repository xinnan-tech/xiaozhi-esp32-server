# MQTT Integration Guide

## Overview
The MQTT Gateway bridges ESP32 devices (using MQTT) with LiveKit cloud for audio streaming. **Important: xiaozhi-server is a WebSocket server and does NOT connect to the MQTT gateway as a client.**

## Architecture
```
xiaozhi-server (Python WebSocket Server :8000)
     ↓ (OTA config)         
     ↓                      LiveKit Cloud
     ↓                           ↑
Devices (ESP32) ←→ MQTT ←→ MQTT Gateway (Node.js)
                    ↓           ↓
                   UDP      UDP Audio
```

## Connection Flow

### 1. xiaozhi-server Role
- Acts as WebSocket server on port 8000
- Provides OTA configuration to devices
- Does NOT connect to MQTT gateway
- Does NOT use MQTT client credentials

### 2. Device Obtains Configuration
ESP32 devices get MQTT credentials from xiaozhi-server's OTA endpoint (`/toy/ota/`)

### 3. ESP32 Device MQTT Authentication (Devices Only)
```python
# Client ID format - ONLY used by ESP32 devices, NOT by xiaozhi-server
client_id = "GID_test@@@00_16_3e_ac_b5_38@@@db4ead3e-c5e2-4dd4-bbf1"

# Username: Base64 encoded JSON
username = base64({"ip": "192.168.1.10"})

# Password: HMAC-SHA256 signature  
password = base64(hmac_sha256(secret_key, client_id + "|" + username))
```

### 4. MQTT Gateway Configuration
```yaml
# config.yaml
server:
  mqtt_gateway:
    enabled: true
    broker: 192.168.1.111
    port: 1883
    udp_port: 8884
```

## MQTT Topics

### Subscribed Topics
- `devices/p2p/{mac_address}` - Device-specific P2P messages

### Published Topics  
- `device-server` - All device-to-server messages

## Message Types

### Session Management
```json
// hello - Establish session
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

// goodbye - Terminate session
{
  "type": "goodbye",
  "session_id": "uuid"
}
```

### Audio Control
```json
// tts - Text-to-Speech control
{
  "type": "tts",
  "state": "start|sentence_start|stop",
  "session_id": "uuid",
  "text": "optional preview text"
}

// stt - Speech-to-Text result
{
  "type": "stt", 
  "text": "transcribed text",
  "session_id": "uuid"
}

// listen - Request speech processing
{
  "type": "listen",
  "session_id": "uuid",
  "state": "detect",
  "text": "trigger phrase"
}
```

### Control Messages
```json
// abort - Stop current operation
{
  "type": "abort",
  "session_id": "uuid"
}

// record_stop - Stop recording
{
  "type": "record_stop",
  "session_id": "uuid"
}

// llm - AI response
{
  "type": "llm",
  "text": "response",
  "emotion": "happy",
  "session_id": "uuid"
}
```

## Audio Streaming
- Protocol: UDP with AES-128-CTR encryption
- Format: Opus codec, 16kHz, mono, 20ms frames
- Encryption: Packet header as nonce
- Header: `[type:1, flags:1, len:2, ssrc:4, timestamp:4, sequence:4]`

## Implementation Files

### Server Side
- `core/api/ota_handler.py` - MQTT credential generation
- `config/config_loader.py` - MQTT configuration loading

### MQTT Gateway
- `mqtt-gateway/app.js` - Main gateway logic
- `mqtt-gateway/mqtt-protocol.js` - MQTT protocol handling
- `mqtt-gateway/config/mqtt.json` - Gateway configuration

### Message Flow
1. Device connects with MQTT credentials
2. Sends `hello` to establish session
3. Receives UDP encryption keys
4. Audio streams via encrypted UDP
5. Control messages via MQTT topics
6. Session ends with `goodbye`

## Port Summary
- MQTT: 1883 (TCP)
- WebSocket: 8000 (TCP)
- UDP Audio: 8884 (UDP)