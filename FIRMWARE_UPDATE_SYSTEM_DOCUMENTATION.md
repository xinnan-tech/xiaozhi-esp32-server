# Firmware Update System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Firmware Upload Process](#firmware-upload-process)
5. [OTA Update Flow](#ota-update-flow)
6. [API Endpoints](#api-endpoints)
7. [Database Schema](#database-schema)
8. [Configuration](#configuration)
9. [Security Features](#security-features)
10. [Device-Server Communication](#device-server-communication)

---

## Overview

The Xiaozhi ESP32 Server implements a comprehensive Over-The-Air (OTA) firmware update system that allows remote firmware updates for ESP32 devices. The system supports automatic version checking, secure firmware distribution, and device-specific update policies.

### Key Features
- Automatic version comparison and update detection
- Secure firmware storage with MD5 hash verification
- Per-device update control (auto-update enable/disable)
- Download attempt limiting (3 attempts per UUID)
- Support for multiple firmware types (.bin and .apk)
- RESTful API for firmware management

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   ESP32 Device  │────▶│   Manager API    │────▶│ Firmware Store │
│                 │◀────│   (Java Spring)  │◀────│  (uploadfile/) │
└─────────────────┘     └──────────────────┘     └────────────────┘
        │                        │                         │
        │                        ▼                         │
        │                ┌──────────────────┐            │
        │                │   Database       │            │
        │                │   (ai_ota)       │            │
        │                └──────────────────┘            │
        │                                                 │
        ▼                                                 │
┌─────────────────┐                                      │
│  Xiaozhi Server │                                      │
│   (Python)      │◀──────────────────────────────────────┘
└─────────────────┘
```

---

## Components

### 1. Manager API (Java Spring Boot)
- **Location**: `main/manager-api/`
- **Main Controllers**:
  - `OTAController.java`: Handles device OTA check requests
  - `OTAMagController.java`: Manages firmware upload/download
- **Services**:
  - `OtaServiceImpl.java`: Business logic for OTA operations
  - `DeviceServiceImpl.java`: Device management and update checks

### 2. Xiaozhi Server (Python)
- **Location**: `main/xiaozhi-server/`
- **OTA Handler**: `core/api/ota_handler.py`
- Provides fallback OTA endpoint for direct device connections

### 3. Firmware Storage
- **Location**: `main/manager-api/uploadfile/`
- Files stored with MD5 hash as filename
- Supported formats: `.bin`, `.apk`

---

## Firmware Upload Process

### Step 1: Admin Upload
```http
POST /otaMag/upload
Content-Type: multipart/form-data
```

**Process Flow**:
1. Admin uploads firmware file through web interface
2. System validates file extension (.bin or .apk only)
3. MD5 hash calculated for the file
4. File saved as: `uploadfile/{md5_hash}.{extension}`
5. If file already exists (same MD5), returns existing path
6. Path returned to admin for database entry

**Code Location**: `OTAMagController.java:231-279`

### Step 2: Database Registration
Admin creates OTA entry with:
- **Firmware Name**: Descriptive name
- **Type**: Device type (e.g., "esp32-generic", "doit-ai-01-kit")
- **Version**: Semantic version (e.g., "1.7.6")
- **File Path**: Path from upload step
- **Size**: File size in bytes
- **Remark**: Optional description

---

## OTA Update Flow

### 1. Device Check Request
```http
POST /ota/
Headers:
  Device-Id: {MAC_ADDRESS}
  Client-Id: {CLIENT_ID}
Body:
{
  "application": {
    "version": "1.7.6"
  },
  "board": {
    "type": "esp32-generic"
  }
}
```

### 2. Server Processing
**Location**: `DeviceServiceImpl.java - checkDeviceActive()`

1. **Device Validation**:
   - Verify MAC address format
   - Check if device is registered in database

2. **Update Decision Logic**:
   ```java
   if (device == null) {
     // Device not registered - no update
     return current_firmware_info;
   }
   
   if (device.autoUpdate != 0) {
     // Check for newer version
     OtaEntity latest = getLatestOta(device.type);
     if (compareVersions(latest.version, current.version) > 0) {
       // Generate download URL
       return firmware_with_download_url;
     }
   }
   ```

3. **Download URL Generation**:
   - Create temporary UUID
   - Store OTA ID in Redis: `ota:id:{uuid}`
   - Generate URL: `/otaMag/download/{uuid}`
   - URL valid for 3 download attempts

### 3. Server Response
```json
{
  "server_time": {
    "timestamp": 1703123456789,
    "timezone_offset": 480
  },
  "firmware": {
    "version": "1.7.7",
    "url": "http://server:8002/otaMag/download/abc-123-def"
  },
  "websocket": {
    "url": "ws://server:8000/xiaozhi/v1/"
  },
  "mqtt": {
    "endpoint": "broker:1883",
    "client_id": "GID_test@@@mac@@@uuid",
    "username": "base64_encoded_data",
    "password": "hmac_signature"
  }
}
```

### 4. Firmware Download
**Endpoint**: `GET /otaMag/download/{uuid}`

**Process**:
1. Validate UUID exists in Redis
2. Check download count (max 3 attempts)
3. Retrieve firmware file from storage
4. Return file as binary stream
5. Increment download counter
6. Clean up after 3 downloads

**Security Features**:
- UUID expires after use
- Download attempt limiting
- File path validation
- Safe filename generation

---

## API Endpoints

### OTA Check Endpoints

#### POST /ota/
- **Purpose**: Device firmware update check
- **Headers**: Device-Id, Client-Id
- **Response**: Update information if available

#### POST /ota/activate
- **Purpose**: Quick device activation check
- **Headers**: Device-Id, Client-Id
- **Response**: 200 if registered, 202 if not

### Management Endpoints

#### GET /otaMag
- **Purpose**: List all firmware entries
- **Permission**: superAdmin
- **Parameters**: page, limit

#### POST /otaMag
- **Purpose**: Create firmware entry
- **Permission**: superAdmin
- **Body**: OtaEntity

#### PUT /otaMag/{id}
- **Purpose**: Update firmware entry
- **Permission**: superAdmin

#### DELETE /otaMag/{id}
- **Purpose**: Delete firmware entry
- **Permission**: superAdmin

#### POST /otaMag/upload
- **Purpose**: Upload firmware file
- **Permission**: superAdmin
- **Returns**: File path for database

#### GET /otaMag/download/{uuid}
- **Purpose**: Download firmware file
- **Public**: Yes (with valid UUID)
- **Limit**: 3 attempts per UUID

---

## Database Schema

### Table: `ai_ota`
```sql
CREATE TABLE ai_ota (
    id VARCHAR(36) PRIMARY KEY,
    firmware_name VARCHAR(255),
    type VARCHAR(100),           -- Device type
    version VARCHAR(50),          -- Semantic version
    size BIGINT,                  -- File size in bytes
    remark TEXT,                  -- Description
    firmware_path VARCHAR(500),   -- File storage path
    sort INT,                     -- Display order
    updater BIGINT,
    update_date DATETIME,
    creator BIGINT,
    create_date DATETIME
);
```

### Table: `ai_device`
```sql
CREATE TABLE ai_device (
    id VARCHAR(36) PRIMARY KEY,
    mac_address VARCHAR(50),
    app_version VARCHAR(50),     -- Current firmware version
    auto_update TINYINT,         -- 0=disabled, 1=enabled
    -- other fields...
);
```

---

## Configuration

### System Parameters
Configure in `sys_params` table or through Parameter Management UI:

1. **server.websocket**
   - WebSocket server URL for device connections
   - Example: `ws://server:8000/xiaozhi/v1/`

2. **server.ota**
   - OTA server base URL
   - Example: `http://server:8002/xiaozhi/`

### Device Types
Configure in Dictionary Management (FIRMWARE_TYPE):
- `doit-ai-01-kit`: DOIT AI-01 Kit
- `esp32-generic`: ESP32 Generic
- `esp32s3-devkit`: ESP32-S3 DevKit
- `xiao-esp32s3`: XIAO ESP32S3
- `m5stack-core`: M5Stack Core

---

## Security Features

### 1. File Upload Security
- Extension validation (.bin, .apk only)
- MD5 hash verification
- Duplicate detection
- Admin permission required

### 2. Download Security
- Temporary UUID generation
- Redis-based token management
- Download attempt limiting (3 max)
- Automatic cleanup after use

### 3. Version Control
- Semantic versioning comparison
- Per-device update control
- Type-specific firmware matching

### 4. MQTT Authentication
- HMAC-SHA256 signature generation
- Base64 encoded credentials
- Session-specific UUIDs

---

## Device-Server Communication

### 1. Initial Connection
Device connects to OTA endpoint with:
- MAC address as Device-Id
- Current firmware version
- Board type information

### 2. Update Check Flow
```
Device                    Manager API              Database
  │                           │                       │
  ├──POST /ota/──────────────▶│                       │
  │  (version, type)          │                       │
  │                           ├──Check Device────────▶│
  │                           │◀─────────────────────┤
  │                           │                       │
  │                           ├──Get Latest OTA──────▶│
  │                           │◀─────────────────────┤
  │                           │                       │
  │◀──Response────────────────┤                       │
  │  (download URL if update) │                       │
  │                           │                       │
  ├──GET /download/{uuid}────▶│                       │
  │                           │                       │
  │◀──Firmware Binary─────────┤                       │
```

### 3. Fallback Support
If Manager API unavailable, devices can connect to:
- Xiaozhi Server OTA endpoint: `http://server:8003/ota/`
- Provides basic connectivity information
- No firmware updates (returns current version)

---

## Version Comparison Logic

The system uses semantic versioning (MAJOR.MINOR.PATCH):

```java
private int compareVersions(String v1, String v2) {
    String[] parts1 = v1.split("\\.");
    String[] parts2 = v2.split("\\.");
    
    for (int i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        int num1 = i < parts1.length ? Integer.parseInt(parts1[i]) : 0;
        int num2 = i < parts2.length ? Integer.parseInt(parts2[i]) : 0;
        
        if (num1 != num2) {
            return Integer.compare(num1, num2);
        }
    }
    return 0;
}
```

**Examples**:
- 1.7.7 > 1.7.6 ✓ (Update available)
- 2.0.0 > 1.9.9 ✓ (Major update)
- 1.7.6 = 1.7.6 ✗ (No update)

---

## Troubleshooting

### Common Issues

1. **"OTA接口不正常，缺少websocket地址"**
   - Solution: Configure `server.websocket` parameter

2. **"OTA接口不正常，缺少ota地址"**
   - Solution: Configure `server.ota` parameter

3. **Firmware file not found**
   - Check file exists in `uploadfile/` directory
   - Verify path in database matches actual file

4. **Device not receiving updates**
   - Check `auto_update` flag is enabled (not 0)
   - Verify device type matches firmware type
   - Ensure version number is higher

5. **Download limit exceeded**
   - UUID expired after 3 attempts
   - Generate new download link

---

## Best Practices

1. **Version Management**
   - Use semantic versioning consistently
   - Test firmware thoroughly before deployment
   - Keep previous versions for rollback

2. **Security**
   - Regular security audits of firmware
   - Monitor download patterns for abuse
   - Use HTTPS in production

3. **Device Management**
   - Group devices by type for targeted updates
   - Implement staged rollouts for critical updates
   - Monitor update success rates

4. **Storage Management**
   - Regular cleanup of old firmware files
   - Backup firmware files externally
   - Monitor disk space usage

---

## Future Enhancements

Potential improvements to consider:
- Delta updates for bandwidth optimization
- Rollback mechanism for failed updates
- Update scheduling and staging
- Device group management
- Update progress tracking
- Firmware signing and verification
- Automated testing before deployment

---

*Last Updated: 2025-08-25*
*Document Version: 1.0.0*