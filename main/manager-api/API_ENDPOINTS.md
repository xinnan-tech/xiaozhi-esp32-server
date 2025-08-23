# Cheeko Server Manager API Endpoints

## Base Configuration
```bash
# Set base URL and token variables
BASE_URL="http://localhost:8002/xiaozhi"
TOKEN="your-auth-token-here"

# For authenticated requests, add header: -H "token: $TOKEN"
```

## Authentication & User Management

### Login Controller
```bash
# Get captcha
curl -X GET "$BASE_URL/user/captcha"

# Send SMS verification code
curl -X POST "$BASE_URL/user/smsVerification" \
  -H "Content-Type: application/json" \
  -d '{"mobile": "1234567890"}'

# User login
curl -X POST "$BASE_URL/user/login" \
  -H "Content-Type: application/json" \
  -d '{"mobile": "1234567890", "password": "password123", "captcha": "captcha_code", "uuid": "captcha_uuid"}'

# User registration (now returns token like login)
curl -X POST "$BASE_URL/user/register" \
  -H "Content-Type: application/json" \
  -d '{"mobile": "1234567890", "password": "password123", "verificationCode": "123456"}'

# Get user info
curl -X GET "$BASE_URL/user/info" \
  -H "token: $TOKEN"

# Change password
curl -X PUT "$BASE_URL/user/change-password" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"oldPassword": "old_password", "newPassword": "new_password"}'

# Retrieve password (forgot password)
curl -X PUT "$BASE_URL/user/retrieve-password" \
  -H "Content-Type: application/json" \
  -d '{"mobile": "1234567890", "newPassword": "new_password", "verificationCode": "123456"}'

# Get public configuration
curl -X GET "$BASE_URL/user/pub-config"
```

## Agent Management

### Agent Controller
```bash
# Get user's agent list
curl -X GET "$BASE_URL/agent/list" \
  -H "token: $TOKEN"

# Get all agents (admin only)
curl -X GET "$BASE_URL/agent/all" \
  -H "token: $TOKEN"

# Get agent by ID
curl -X GET "$BASE_URL/agent/{id}" \
  -H "token: $TOKEN"

# Create new agent
curl -X POST "$BASE_URL/agent" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent Name",
    "prompt": "Agent prompt",
    "llm": "LLM model",
    "tts": "TTS model",
    "asr": "ASR model",
    "vad": "VAD model"
  }'

# Update agent memory by device ID
curl -X PUT "$BASE_URL/agent/saveMemory/{macAddress}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"memory": "updated memory content"}'

# Update agent
curl -X PUT "$BASE_URL/agent/{id}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Agent Name",
    "prompt": "Updated prompt"
  }'

# Delete agent
curl -X DELETE "$BASE_URL/agent/{id}" \
  -H "token: $TOKEN"

# Get agent templates
curl -X GET "$BASE_URL/agent/template" \
  -H "token: $TOKEN"

# Get agent sessions
curl -X GET "$BASE_URL/agent/{id}/sessions" \
  -H "token: $TOKEN"

# Get agent chat history
curl -X GET "$BASE_URL/agent/{id}/chat-history/{sessionId}" \
  -H "token: $TOKEN"

# Get recent 50 chat messages for user
curl -X GET "$BASE_URL/agent/{id}/chat-history/user" \
  -H "token: $TOKEN"

# Get audio content by audio ID
curl -X GET "$BASE_URL/agent/{id}/chat-history/audio?audioId={audioId}" \
  -H "token: $TOKEN"

# Get audio download ID
curl -X POST "$BASE_URL/agent/audio/{audioId}" \
  -H "token: $TOKEN"

# Play audio
curl -X GET "$BASE_URL/agent/play/{uuid}" \
  -H "token: $TOKEN"
```

### Agent Chat History Controller
```bash
# Upload chat history file
curl -X POST "$BASE_URL/agent/chat-history/report" \
  -H "token: $TOKEN" \
  -F "file=@/path/to/chat_history.json" \
  -F "deviceId=device123"
```

### Agent MCP Access Point Controller
```bash
# Get agent MCP access address
curl -X GET "$BASE_URL/agent/mcp/address/{agentId}" \
  -H "token: $TOKEN"

# Get agent MCP tools list
curl -X GET "$BASE_URL/agent/mcp/tools/{agentId}" \
  -H "token: $TOKEN"
```

### Agent Voice Print Controller
```bash
# Create voice print
curl -X POST "$BASE_URL/agent/voice-print" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": 1,
    "name": "Voice Print Name",
    "voiceData": "base64_encoded_voice_data"
  }'

# Update voice print
curl -X PUT "$BASE_URL/agent/voice-print" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "name": "Updated Voice Print",
    "voiceData": "updated_base64_voice_data"
  }'

# Delete voice print
curl -X DELETE "$BASE_URL/agent/voice-print/{id}" \
  -H "token: $TOKEN"

# Get voice prints for agent
curl -X GET "$BASE_URL/agent/voice-print/list/{agentId}" \
  -H "token: $TOKEN"
```

## Device Management

### Device Controller
```bash
# Bind device to agent
curl -X POST "$BASE_URL/device/bind/{agentId}/{deviceCode}" \
  -H "token: $TOKEN"

# Register device
curl -X POST "$BASE_URL/device/register" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "device123",
    "type": "ESP32",
    "firmwareVersion": "1.0.0"
  }'

# Get user's bound devices
curl -X GET "$BASE_URL/device/bind/{agentId}" \
  -H "token: $TOKEN"

# Unbind device
curl -X POST "$BASE_URL/device/unbind" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"deviceId": "device123", "agentId": 1}'

# Update device info
curl -X PUT "$BASE_URL/device/update/{id}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Device Name", "description": "Updated description"}'

# Manually add device
curl -X POST "$BASE_URL/device/manual-add" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "manual_device_123",
    "name": "Manual Device",
    "type": "ESP32"
  }'
```

### OTA Controller
```bash
# Check OTA version and activation status
curl -X POST "$BASE_URL/ota/" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "device123",
    "currentVersion": "1.0.0",
    "type": "ESP32"
  }'

# Quick check device activation status
curl -X POST "$BASE_URL/ota/activate" \
  -H "Content-Type: application/json" \
  -d '{"deviceId": "device123"}'

# Get OTA status info
curl -X GET "$BASE_URL/ota/"
```

### OTA Management Controller
```bash
# Get OTA firmware list (paginated)
curl -X GET "$BASE_URL/otaMag?page=1&limit=10" \
  -H "token: $TOKEN"

# Get OTA firmware by ID
curl -X GET "$BASE_URL/otaMag/{id}" \
  -H "token: $TOKEN"

# Save new OTA firmware info
curl -X POST "$BASE_URL/otaMag" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "2.0.0",
    "type": "ESP32",
    "description": "New firmware version",
    "url": "http://example.com/firmware.bin"
  }'

# Delete OTA firmware
curl -X DELETE "$BASE_URL/otaMag/{id}" \
  -H "token: $TOKEN"

# Update OTA firmware info
curl -X PUT "$BASE_URL/otaMag/{id}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "2.0.1",
    "description": "Updated firmware"
  }'

# Get firmware download URL
curl -X GET "$BASE_URL/otaMag/getDownloadUrl/{id}" \
  -H "token: $TOKEN"

# Download firmware file
curl -X GET "$BASE_URL/otaMag/download/{uuid}" \
  -o firmware.bin

# Upload firmware file
curl -X POST "$BASE_URL/otaMag/upload" \
  -H "token: $TOKEN" \
  -F "file=@/path/to/firmware.bin" \
  -F "version=2.0.0" \
  -F "type=ESP32"
```

## Model Management

### Model Controller
```bash
# Get all model names
curl -X GET "$BASE_URL/models/names" \
  -H "token: $TOKEN"

# Get LLM model codes
curl -X GET "$BASE_URL/models/llm/names" \
  -H "token: $TOKEN"

# Get model providers for type
curl -X GET "$BASE_URL/models/{modelType}/provideTypes" \
  -H "token: $TOKEN"

# Get model configuration list
curl -X GET "$BASE_URL/models/list" \
  -H "token: $TOKEN"

# Add model configuration
curl -X POST "$BASE_URL/models/{modelType}/{provideCode}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Model Name",
    "apiKey": "api_key_here",
    "config": {"temperature": 0.7}
  }'

# Edit model configuration
curl -X PUT "$BASE_URL/models/{modelType}/{provideCode}/{id}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Model",
    "config": {"temperature": 0.8}
  }'

# Delete model configuration
curl -X DELETE "$BASE_URL/models/{id}" \
  -H "token: $TOKEN"

# Get model configuration
curl -X GET "$BASE_URL/models/{id}" \
  -H "token: $TOKEN"

# Enable/disable model
curl -X PUT "$BASE_URL/models/enable/{id}/{status}" \
  -H "token: $TOKEN"

# Set default model
curl -X PUT "$BASE_URL/models/default/{id}" \
  -H "token: $TOKEN"

# Get model voices
curl -X GET "$BASE_URL/models/{modelId}/voices" \
  -H "token: $TOKEN"
```

### Model Provider Controller
```bash
# Get model providers (paginated)
curl -X GET "$BASE_URL/models/provider?page=1&limit=10" \
  -H "token: $TOKEN"

# Add model provider
curl -X POST "$BASE_URL/models/provider" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Provider Name",
    "code": "provider_code",
    "type": "LLM"
  }'

# Edit model provider
curl -X PUT "$BASE_URL/models/provider" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "name": "Updated Provider"
  }'

# Delete model provider
curl -X POST "$BASE_URL/models/provider/delete" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'

# Get plugin names
curl -X GET "$BASE_URL/models/provider/plugin/names" \
  -H "token: $TOKEN"
```

## Configuration

### Config Controller
```bash
# Get server configuration
curl -X POST "$BASE_URL/config/server-base" \
  -H "Content-Type: application/json" \
  -d '{"deviceId": "device123"}'

# Get agent models
curl -X POST "$BASE_URL/config/agent-models" \
  -H "Content-Type: application/json" \
  -d '{"agentId": 1}'
```

## TTS Voice/Timbre Management

### Timbre Controller
```bash
# Get timbre list (paginated)
curl -X GET "$BASE_URL/ttsVoice?page=1&limit=10" \
  -H "token: $TOKEN"

# Save new timbre
curl -X POST "$BASE_URL/ttsVoice" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Voice Name",
    "voiceId": "voice_123",
    "provider": "elevenlabs"
  }'

# Update timbre
curl -X PUT "$BASE_URL/ttsVoice/{id}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Voice Name"
  }'

# Delete timbre
curl -X POST "$BASE_URL/ttsVoice/delete" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'
```

## Admin Functions

### Admin Controller
```bash
# Get users (paginated)
curl -X GET "$BASE_URL/admin/users?page=1&limit=10" \
  -H "token: $TOKEN"

# Reset user password
curl -X PUT "$BASE_URL/admin/users/{id}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "new_password"}'

# Delete user
curl -X DELETE "$BASE_URL/admin/users/{id}" \
  -H "token: $TOKEN"

# Batch change user status
curl -X PUT "$BASE_URL/admin/users/changeStatus/{status}" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"userIds": [1, 2, 3]}'

# Get all devices (paginated)
curl -X GET "$BASE_URL/admin/device/all?page=1&limit=10" \
  -H "token: $TOKEN"
```

### Server Side Management Controller
```bash
# Get WebSocket server list
curl -X GET "$BASE_URL/admin/server/server-list" \
  -H "token: $TOKEN"

# Notify Python server to update config
curl -X POST "$BASE_URL/admin/server/emit-action" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "UPDATE_CONFIG",
    "payload": {"config": "value"}
  }'
```

### System Dictionary Data Controller
```bash
# Get dictionary data (paginated)
curl -X GET "$BASE_URL/admin/dict/data/page?page=1&limit=10" \
  -H "token: $TOKEN"

# Get dictionary data by ID
curl -X GET "$BASE_URL/admin/dict/data/{id}" \
  -H "token: $TOKEN"

# Save dictionary data
curl -X POST "$BASE_URL/admin/dict/data/save" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dictType": "status",
    "dictLabel": "Active",
    "dictValue": "1"
  }'

# Update dictionary data
curl -X PUT "$BASE_URL/admin/dict/data/update" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "dictLabel": "Updated Label"
  }'

# Delete dictionary data
curl -X POST "$BASE_URL/admin/dict/data/delete" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'

# Get dictionary data by type
curl -X GET "$BASE_URL/admin/dict/data/type/{dictType}" \
  -H "token: $TOKEN"
```

### System Dictionary Type Controller
```bash
# Get dictionary types (paginated)
curl -X GET "$BASE_URL/admin/dict/type/page?page=1&limit=10" \
  -H "token: $TOKEN"

# Get dictionary type by ID
curl -X GET "$BASE_URL/admin/dict/type/{id}" \
  -H "token: $TOKEN"

# Save dictionary type
curl -X POST "$BASE_URL/admin/dict/type/save" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dictType": "new_type",
    "dictName": "New Type Name"
  }'

# Update dictionary type
curl -X PUT "$BASE_URL/admin/dict/type/update" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "dictName": "Updated Type Name"
  }'

# Delete dictionary type
curl -X POST "$BASE_URL/admin/dict/type/delete" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'
```

### System Parameters Controller
```bash
# Get system parameters (paginated)
curl -X GET "$BASE_URL/admin/params/page?page=1&limit=10" \
  -H "token: $TOKEN"

# Get parameter by ID
curl -X GET "$BASE_URL/admin/params/{id}" \
  -H "token: $TOKEN"

# Save parameter
curl -X POST "$BASE_URL/admin/params" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "paramCode": "param_code",
    "paramValue": "param_value"
  }'

# Update parameter
curl -X PUT "$BASE_URL/admin/params" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "paramValue": "updated_value"
  }'

# Delete parameter
curl -X POST "$BASE_URL/admin/params/delete" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'
```

## Mobile Parent Profile Management

### Mobile Parent Profile Controller
```bash
# Get parent profile
curl -X GET "$BASE_URL/api/mobile/profile" \
  -H "token: $TOKEN"

# Create parent profile
curl -X POST "$BASE_URL/api/mobile/profile/create" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fullName": "John Doe",
    "email": "john@example.com",
    "phoneNumber": "+1234567890",
    "preferredLanguage": "en",
    "timezone": "UTC",
    "notificationPreferences": "{\"push\":true,\"email\":true,\"daily_summary\":true}",
    "onboardingCompleted": false
  }'

# Update parent profile
curl -X PUT "$BASE_URL/api/mobile/profile/update" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fullName": "John Smith",
    "phoneNumber": "+1234567891"
  }'

# Accept terms and privacy policy
curl -X POST "$BASE_URL/api/mobile/profile/accept-terms" \
  -H "token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "termsAccepted": true,
    "privacyAccepted": true
  }'

# Complete onboarding
curl -X POST "$BASE_URL/api/mobile/profile/complete-onboarding" \
  -H "token: $TOKEN"

# Delete parent profile
curl -X DELETE "$BASE_URL/api/mobile/profile" \
  -H "token: $TOKEN"
```

## Notes

1. Replace `{id}`, `{agentId}`, `{deviceCode}`, etc. with actual values
2. Most endpoints require authentication via the `token` header
3. The base URL assumes the application is running on `http://localhost:8002/xiaozhi`
4. Adjust the JSON payloads according to your specific requirements
5. For file uploads, replace `/path/to/file` with actual file paths
6. Pagination parameters typically include `page` and `limit` query parameters
7. Admin endpoints require admin privileges
8. Mobile parent profile endpoints are designed for the Flutter mobile app integration

## Testing Authentication Flow

```bash
# 1. Get captcha
CAPTCHA_RESPONSE=$(curl -s -X GET "$BASE_URL/user/captcha")
echo $CAPTCHA_RESPONSE

# 2. Login (extract token from response)
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/user/login" \
  -H "Content-Type: application/json" \
  -d '{"mobile": "your_mobile", "password": "your_password"}')
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.data.token')
echo "Token: $TOKEN"

# 3. Use token for authenticated requests
curl -X GET "$BASE_URL/user/info" \
  -H "token: $TOKEN"
```