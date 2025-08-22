# Device Activation and Registration Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Activation Methods](#activation-methods)
4. [Step-by-Step Process](#step-by-step-process)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)
8. [Database Schema](#database-schema)

---

## Overview

The Xiaozhi ESP32 Server system uses a secure device activation mechanism to register and manage IoT devices. This system ensures that only authorized devices can connect to the server and prevents unauthorized access.

### Key Components

- **Manager API** (Port 8002): Java backend that handles device registration and management
- **Main Server** (Port 8000/8003): Python server that handles device communication
- **MQTT Gateway** (Port 1883): Optional MQTT broker for device communication
- **Database**: MySQL database storing device information and configurations

### Activation Flow

```
Device → OTA Request → Manager API → Generate Code → User Binds → Device Registered
```

---

## Architecture

### System Components

```
┌─────────────────┐
│   ESP32 Device  │
│  (Client/Device) │
└────────┬────────┘
         │
         ▼ OTA Request (Port 8002)
┌─────────────────┐
│   Manager API   │ ◄──── Generates 6-digit code
│  (Java Backend) │ ◄──── Stores in Redis
└────────┬────────┘
         │
         ▼ After Binding
┌─────────────────┐
│   Main Server   │ ◄──── WebSocket Communication
│ (Python Server) │ ◄──── Audio/Command Processing
└─────────────────┘
```

### Data Flow

1. **Device → Manager API**: Initial OTA configuration request
2. **Manager API → Redis**: Store activation code and device info
3. **Manager API → Device**: Return activation code
4. **User → Admin Panel**: Enter activation code
5. **Admin Panel → Database**: Create device record
6. **Device → Main Server**: Normal operation begins

---

## Activation Methods

### Method 1: Verification Code Binding (Recommended)

This is the primary method for device activation, suitable for production environments.

#### How It Works

1. **Device Request**: Unregistered device sends OTA request with MAC address
2. **Code Generation**: Manager API generates a 6-digit activation code
3. **Code Storage**: Code stored in Redis with 5-minute expiration
4. **User Binding**: User enters code in admin panel
5. **Device Registration**: Device record created in database

#### Advantages
- Secure and user-friendly
- No manual database access required
- Automatic expiration of unused codes
- Supports multiple users and roles

### Method 2: Direct Database Registration (Development Only)

For development and testing, devices can be added directly to the database.

#### SQL Command

```sql
INSERT INTO device (
    id,
    device_id,
    device_name,
    board,
    app_version,
    mac_address,
    agent_id,
    user_id,
    creator,
    auto_update,
    created_at,
    updated_at
) VALUES (
    '68:25:dd:ba:39:78',           -- Device MAC (use as ID)
    '68:25:dd:ba:39:78',           -- Device MAC
    'Test ESP32 Device',            -- Device name
    'esp32',                        -- Board type
    '1.7.6',                        -- Firmware version
    '68:25:dd:ba:39:78',           -- MAC address
    (SELECT id FROM agent_template WHERE is_default = 1 LIMIT 1),
    1,                              -- Admin user ID
    1,                              -- Creator ID
    1,                              -- Auto-update enabled
    NOW(),                          -- Created timestamp
    NOW()                           -- Updated timestamp
);
```

#### Advantages
- Quick setup for testing
- No UI interaction required
- Batch device registration possible

#### Disadvantages
- Requires database access
- No automatic validation
- Not suitable for production

---

## Step-by-Step Process

### For Device Manufacturers/Developers

#### 1. Configure Device Client

```python
# client.py configuration
SERVER_IP = "192.168.1.105"  # Your server IP
OTA_PORT = 8002              # Manager API port
MQTT_BROKER_HOST = "192.168.1.105"
```

#### 2. Device Sends OTA Request

```python
# Request format
headers = {"device-id": "68:25:dd:ba:39:78"}
data = {
    "application": {
        "version": "1.7.6"
    },
    "client_id": "unique-session-id"
}
response = requests.post(
    f"http://{SERVER_IP}:{OTA_PORT}/xiaozhi/ota/", 
    headers=headers, 
    json=data
)
```

#### 3. Handle Activation Response

```python
# Response when device not registered
{
    "activation": {
        "code": "123456",
        "message": "http://xiaozhi.server.com\n123456",
        "challenge": "68:25:dd:ba:39:78"
    },
    "server_time": {...},
    "firmware": {...}
}
```

### For End Users

#### 1. Get Activation Code

- Device will display or log the 6-digit code
- Code is valid for 5 minutes
- Code format: 6 random digits (e.g., "123456")

#### 2. Access Admin Panel

1. Open browser: `http://your-server-ip:8002`
2. Login with admin credentials
3. Navigate to "Device Management" (设备管理)

#### 3. Bind Device

1. Click "Bind Device" (绑定设备)
2. Enter the 6-digit activation code
3. Select Agent/Profile for the device
4. Click "Confirm" to complete binding

#### 4. Verify Activation

- Device status changes to "Online"
- Device can now communicate with server
- Full features are enabled

### For System Administrators

#### 1. Server Configuration

**Manager API Configuration** (`application.yml`):
```yaml
server:
  port: 8002
  servlet:
    context-path: /xiaozhi

spring:
  redis:
    host: localhost
    port: 6379
```

**Main Server Configuration** (`.config.yaml`):
```yaml
read_config_from_api: true
manager-api:
  url: http://192.168.1.105:8002/xiaozhi
  secret: your-secret-key
```

#### 2. Database Setup

Required tables:
- `device`: Stores device information
- `agent_template`: Stores agent configurations
- `sys_params`: System parameters

#### 3. Monitor Activation Logs

**Manager API Logs**:
```
🔐 Generated NEW activation code for device 68:25:dd:ba:39:78: 123456
📱 Please bind device using code: 123456 at http://xiaozhi.server.com
```

**Main Server Logs**:
```
OTA request device ID: 68:25:dd:ba:39:78
Device activated successfully
```

---

## Configuration

### Manager API Settings

#### System Parameters (sys_params table)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `server.websocket` | WebSocket URL for devices | `ws://192.168.1.105:8000/xiaozhi/v1/` |
| `server.ota` | OTA endpoint URL | `http://192.168.1.105:8002/xiaozhi/ota/` |
| `server.fronted_url` | Admin panel URL | `http://xiaozhi.server.com` |

### Redis Configuration

#### Activation Code Storage

```
Key Format: ota:activation:code:{6-digit-code}
Value: Device MAC address
TTL: 300 seconds (5 minutes)

Key Format: ota:activation:data:{safe_device_id}
Value: JSON with device details
TTL: 300 seconds (5 minutes)
```

### Security Considerations

1. **Code Expiration**: Activation codes expire after 5 minutes
2. **Code Uniqueness**: 6-digit random codes (1 million combinations)
3. **Rate Limiting**: Implement rate limiting on OTA endpoint
4. **HTTPS**: Use HTTPS in production environments
5. **Authentication**: Manager API requires authentication for binding

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Device Not Getting Activation Code

**Symptoms**:
- Device connects but no activation code generated
- Manager API shows no device query

**Solutions**:
1. Verify device is connecting to Manager API port (8002), not Main Server (8003)
2. Check Manager API is running and accessible
3. Verify Redis is running and accessible
4. Check network connectivity

**Debug Commands**:
```bash
# Test Manager API endpoint
curl -X POST http://192.168.1.105:8002/xiaozhi/ota/ \
  -H "device-id: 68:25:dd:ba:39:78" \
  -H "Content-Type: application/json" \
  -d '{"application":{"version":"1.7.6"}}'
```

#### Issue 2: Activation Code Not Working

**Symptoms**:
- Code entered but binding fails
- "Invalid activation code" error

**Solutions**:
1. Ensure code is entered within 5 minutes
2. Verify code is typed correctly (6 digits)
3. Check Redis for stored activation data
4. Ensure device MAC matches stored data

**Debug Commands**:
```bash
# Check Redis for activation code
redis-cli GET "ota:activation:code:123456"
```

#### Issue 3: Device Already Registered

**Symptoms**:
- Device exists in database
- No activation code generated
- "Version information not found" error

**Solutions**:
1. Remove device from database if re-registration needed
2. Or update device record directly
3. Check device binding status

**SQL Commands**:
```sql
-- Check if device exists
SELECT * FROM device WHERE device_id = '68:25:dd:ba:39:78';

-- Remove device for re-registration
DELETE FROM device WHERE device_id = '68:25:dd:ba:39:78';
```

#### Issue 4: Configuration Mismatch

**Symptoms**:
- Device connects to wrong server
- WebSocket URL incorrect
- MQTT credentials missing

**Solutions**:
1. Verify all configuration files are synchronized
2. Check `read_config_from_api` setting
3. Ensure Manager API has correct parameters
4. Restart all services after configuration changes

---

## API Reference

### OTA Endpoint

**Endpoint**: `POST /xiaozhi/ota/`

**Request Headers**:
```json
{
  "device-id": "68:25:dd:ba:39:78",
  "Content-Type": "application/json"
}
```

**Request Body**:
```json
{
  "application": {
    "version": "1.7.6"
  },
  "client_id": "unique-session-id",
  "board": {
    "type": "esp32"
  }
}
```

**Response (Unregistered Device)**:
```json
{
  "activation": {
    "code": "123456",
    "message": "http://xiaozhi.server.com\n123456",
    "challenge": "68:25:dd:ba:39:78"
  },
  "server_time": {
    "timestamp": 1755844295654,
    "timezone_offset": 480
  },
  "firmware": {
    "version": "1.0.0",
    "url": ""
  },
  "websocket": {
    "url": "ws://192.168.1.105:8000/xiaozhi/v1/"
  },
  "mqtt_gateway": {
    "enabled": true,
    "broker": "192.168.1.105",
    "port": 1883,
    "udp_port": 8884
  }
}
```

**Response (Registered Device)**:
```json
{
  "server_time": {...},
  "firmware": {...},
  "websocket": {...},
  "mqtt": {
    "client_id": "GID_test@@@68_25_dd_ba_39_78@@@uuid",
    "username": "base64-encoded-data",
    "password": "base64-encoded-signature"
  }
}
```

### Device Binding Endpoint

**Endpoint**: `POST /device/bind/{agentId}/{deviceCode}`

**Parameters**:
- `agentId`: Agent template ID
- `deviceCode`: 6-digit activation code

**Response**:
```json
{
  "code": 0,
  "msg": "success"
}
```

---

## Database Schema

### Device Table

```sql
CREATE TABLE `device` (
  `id` varchar(50) PRIMARY KEY,
  `device_id` varchar(50) NOT NULL,
  `device_name` varchar(100),
  `board` varchar(50),
  `app_version` varchar(20),
  `mac_address` varchar(50),
  `agent_id` varchar(50),
  `user_id` bigint,
  `bind_status` tinyint DEFAULT 0,
  `online_status` tinyint DEFAULT 0,
  `last_online` datetime,
  `ip_address` varchar(50),
  `created_at` datetime,
  `updated_at` datetime,
  `bind_code` varchar(10),
  `bind_time` datetime,
  KEY `idx_device_id` (`device_id`),
  KEY `idx_mac_address` (`mac_address`),
  KEY `idx_user_id` (`user_id`)
);
```

### Agent Template Table

```sql
CREATE TABLE `agent_template` (
  `id` varchar(50) PRIMARY KEY,
  `agent_name` varchar(100),
  `is_default` tinyint DEFAULT 0,
  `asr_model_id` varchar(50),
  `tts_model_id` varchar(50),
  `llm_model_id` varchar(50),
  `vad_model_id` varchar(50),
  -- other configuration fields
);
```

---

## Best Practices

### For Production Deployment

1. **Use HTTPS**: Always use HTTPS for OTA endpoints
2. **Implement Rate Limiting**: Prevent activation code brute force
3. **Log All Activations**: Maintain audit trail
4. **Monitor Failed Attempts**: Detect potential security issues
5. **Regular Cleanup**: Remove expired activation data from Redis
6. **Backup Device Data**: Regular database backups
7. **Use Strong Secrets**: Generate strong secrets for API authentication

### For Development

1. **Use Test Devices**: Maintain separate test device pool
2. **Mock Activation**: Create mock activation endpoints for testing
3. **Automate Testing**: Create automated tests for activation flow
4. **Document MAC Addresses**: Keep track of test device MACs
5. **Use Docker**: Containerize services for consistent environment

### Security Recommendations

1. **Network Isolation**: Isolate device network from main network
2. **API Authentication**: Implement JWT or OAuth for API access
3. **Device Certificates**: Consider using device certificates for production
4. **Encrypted Communication**: Use TLS for all communications
5. **Regular Updates**: Keep all components updated
6. **Access Control**: Implement role-based access control
7. **Audit Logging**: Log all device registration activities

---

## Appendix

### Testing Tools

#### Test OTA Connection Script

```python
# test_ota.py
import requests
import json

device_mac = "68:25:dd:ba:39:78"
manager_api_url = "http://192.168.1.105:8002/xiaozhi/ota/"

headers = {"device-id": device_mac}
data = {
    "application": {"version": "1.7.6"},
    "client_id": "test-client"
}

response = requests.post(manager_api_url, headers=headers, json=data)
print(json.dumps(response.json(), indent=2))

activation = response.json().get("activation")
if activation:
    print(f"\n🔐 ACTIVATION CODE: {activation.get('code')}")
```

### Monitoring Commands

```bash
# Monitor Manager API logs
tail -f manager-api.log | grep -E "activation|device"

# Monitor Redis
redis-cli MONITOR | grep "ota:activation"

# Check device status in database
mysql -u root -p xiaozhi_db -e "SELECT * FROM device WHERE online_status = 1;"
```

### Environment Variables

```bash
# .env file for Manager API
SPRING_PROFILES_ACTIVE=prod
REDIS_HOST=localhost
REDIS_PORT=6379
DB_HOST=localhost
DB_PORT=3306
DB_NAME=xiaozhi_db

# .env file for Main Server
MANAGER_API_URL=http://192.168.1.105:8002/xiaozhi
MANAGER_API_SECRET=your-secret-key
MQTT_BROKER_HOST=192.168.1.105
MQTT_BROKER_PORT=1883
```

---

## Support and Resources

- **GitHub Repository**: [xiaozhi-esp32-server](https://github.com/your-repo)
- **Documentation**: [Official Docs](https://docs.your-domain.com)
- **Community Forum**: [Discussion Board](https://forum.your-domain.com)
- **Issue Tracker**: [GitHub Issues](https://github.com/your-repo/issues)

---

*Last Updated: August 2024*
*Version: 1.0.0*