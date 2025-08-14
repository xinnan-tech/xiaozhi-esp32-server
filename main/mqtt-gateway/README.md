# MQTT+UDP to WebSocket Bridge Service

## Project Overview

This is a bridge service for IoT device communication that implements conversion from MQTT and UDP protocols to WebSocket. The service allows devices to transmit control messages through MQTT protocol while efficiently transmitting audio data through UDP protocol, bridging this data to WebSocket services.

## Features

- **Multi-protocol Support**: Simultaneous support for MQTT, UDP, and WebSocket protocols
- **Audio Data Transmission**: Transmission mechanism optimized for audio data streams
- **Encrypted Communication**: Uses AES-128-CTR encryption for UDP data transmission
- **Session Management**: Complete device session lifecycle management
- **Auto Reconnection**: Automatic reconnection mechanism when connections are lost
- **Heartbeat Detection**: Periodic checking of connection active status
- **Development/Production Environment Configuration**: Support for configuration switching between different environments

## Technical Architecture

- **MQTT Server**: Handles device control messages
- **UDP Server**: Handles efficient audio data transmission
- **WebSocket Client**: Connects to chat servers
- **Bridge Layer**: Converts and routes messages between different protocols

## Project Structure

```
├── app.js                # Main application entry point
├── mqtt-protocol.js      # MQTT protocol implementation
├── ecosystem.config.js   # PM2 configuration file
├── package.json          # Project dependencies
├── .env                  # Environment variable configuration
├── utils/
│   ├── config-manager.js # Configuration management tool
│   ├── mqtt_config_v2.js # MQTT configuration validation tool
│   └── weixinAlert.js    # WeChat alert tool
└── config/               # Configuration file directory
```

## Dependencies

- **debug**: Debug log output
- **dotenv**: Environment variable management
- **ws**: WebSocket client
- **events**: Node.js event module

## Installation Requirements

- Node.js 14.x or higher
- npm or yarn package manager
- PM2 (for production environment deployment)

## Installation Steps

1. Clone repository

```bash
git clone <repository-url>
cd mqtt-websocket-bridge
```

2. Install dependencies

```bash
npm install
```

3. Create configuration file

```bash
mkdir -p config
cp config/mqtt.json.example config/mqtt.json
```

4. Edit configuration file `config/mqtt.json` and set appropriate parameters

## Configuration Instructions

Configuration file `config/mqtt.json` needs to contain the following content:

```json
{
  "debug": false,
  "development": {
    "mac_addresss": ["aa:bb:cc:dd:ee:ff"],
    "chat_servers": ["wss://dev-chat-server.example.com/ws"]
  },
  "production": {
    "chat_servers": ["wss://chat-server.example.com/ws"]
  }
}
```

## Environment Variables

Create `.env` file and set the following environment variables:

```
MQTT_PORT=1883       # MQTT server port
UDP_PORT=8884        # UDP server port
PUBLIC_IP=your-ip    # Server public IP
```

## Running the Service

### Development Environment

```bash
# Run directly
node app.js

# Run in debug mode
DEBUG=mqtt-server node app.js
```

### Production Environment (Using PM2)

```bash
# Install PM2
npm install -g pm2

# Start service
pm2 start ecosystem.config.js

# View logs
pm2 logs xz-mqtt

# Monitor service
pm2 monit
```

The service will start on the following ports:

- MQTT Server: Port 1883 (can be modified via environment variables)
- UDP Server: Port 8884 (can be modified via environment variables)

## Protocol Description

### Device Connection Flow

1. Device connects to server via MQTT protocol
2. Device sends `hello` message containing audio parameters and features
3. Server creates WebSocket connection to chat server
4. Server returns UDP connection parameters to device
5. Device sends audio data via UDP
6. Server forwards audio data to WebSocket
7. Control messages returned by WebSocket are sent to device via MQTT

### Message Format

#### Hello Message (Device -> Server)

```json
{
  "type": "hello",
  "version": 3,
  "audio_params": { ... },
  "features": { ... }
}
```

#### Hello Response (Server -> Device)

```json
{
  "type": "hello",
  "version": 3,
  "session_id": "uuid",
  "transport": "udp",
  "udp": {
    "server": "server-ip",
    "port": 8884,
    "encryption": "aes-128-ctr",
    "key": "hex-encoded-key",
    "nonce": "hex-encoded-nonce"
  },
  "audio_params": { ... }
}
```

## Security Description

- UDP communication uses AES-128-CTR encryption
- Each session uses a unique encryption key
- Uses sequence numbers to prevent replay attacks
- Device authentication via MAC address
- Supports device grouping and UUID verification

## Performance Optimization

- Uses pre-allocated buffers to reduce memory allocation
- UDP protocol for efficient audio data transmission
- Periodic cleanup of inactive connections
- Connection count and active connection monitoring
- Support for multi-chat server load balancing

## Troubleshooting

- Check if device MAC address format is correct
- Ensure UDP port is open in firewall
- Enable debug mode to view detailed logs
- Check if chat server address in configuration file is correct
- Verify device authentication information is correct

## Development Guide

### Adding New Features

1. Modify `mqtt-protocol.js` to support new MQTT functionality
2. Add new message handling methods in `MQTTConnection` class
3. Update configuration manager to support new configuration options
4. Add new WebSocket handling logic in `WebSocketBridge` class

### Debugging Tips

```bash
# Enable all debug output
DEBUG=* node app.js

# Enable only MQTT server debugging
DEBUG=mqtt-server node app.js
```
