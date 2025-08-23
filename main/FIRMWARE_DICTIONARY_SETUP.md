# Firmware Dictionary Setup Guide

## Adding Firmware Types to Dictionary Management

To properly display firmware information for your devices, you need to add the following dictionary entries in the web dashboard:

### Step 1: Access Dictionary Management
1. Login to your web dashboard
2. Navigate to **Dictionary Management** section

### Step 2: Find or Create FIRMWARE_TYPE Dictionary Type
1. Look for "FIRMWARE_TYPE" in the left panel
2. If it doesn't exist, click "Add Dictionary Type" and create:
   - Dictionary Type Name: `Firmware Type`
   - Dictionary Type Code: `FIRMWARE_TYPE`

### Step 3: Add Device Model Entries
Click on FIRMWARE_TYPE and add the following dictionary data entries:

#### Entry 1: DOIT AI Kit
- **Dictionary Label**: `DOIT AI-01 Kit`
- **Dictionary Value**: `doit-ai-01-kit`
- **Sort**: `1`

#### Entry 2: ESP32 Generic
- **Dictionary Label**: `ESP32 Generic`
- **Dictionary Value**: `esp32-generic`
- **Sort**: `2`

#### Entry 3: ESP32-S3 DevKit
- **Dictionary Label**: `ESP32-S3 DevKit`
- **Dictionary Value**: `esp32s3-devkit`
- **Sort**: `3`

#### Entry 4: XIAO ESP32S3
- **Dictionary Label**: `XIAO ESP32S3`
- **Dictionary Value**: `xiao-esp32s3`
- **Sort**: `4`

#### Entry 5: M5Stack Core
- **Dictionary Label**: `M5Stack Core`
- **Dictionary Value**: `m5stack-core`
- **Sort**: `5`

## Current Device Information from Logs

Your connected device is reporting:
- **Device Name**: doit-ai-01-kit
- **Firmware Version**: 1.7.6
- **Protocol Version**: 2024-11-05
- **MAC Address**: 68:25:DD:BB:4D:44

## Firmware Management Display

After adding these dictionary entries, the Firmware Management and Device Management pages will properly display:
- Device model names (instead of raw codes)
- Firmware versions
- Device capabilities

## Verification Steps

1. After adding dictionary entries, go to **Device Management**
2. You should see "DOIT AI-01 Kit" instead of "doit-ai-01-kit"
3. The firmware version "1.7.6" should be displayed in the table
4. In **Firmware Management**, you can now add OTA updates for these device types

## Backend Integration

The system is already configured to:
1. Log firmware details when devices connect via MCP protocol
2. Store firmware version in the database (appVersion field)
3. Display firmware info in Device Management table

The enhanced logging shows:
```
============================================================
DEVICE CONNECTED - Firmware Details:
  Device Name: doit-ai-01-kit
  Firmware Version: 1.7.6
  Protocol Version: 2024-11-05
  Device ID: 68_25_dd_bb_4d_44
  MAC Address: 68:25:DD:BB:4D:44
  Capabilities: ['tools']
============================================================
```

## Next Steps

1. Add the dictionary entries as described above
2. Verify device display in Device Management
3. Upload firmware files in Firmware Management for OTA updates
4. Configure auto-update settings per device if needed