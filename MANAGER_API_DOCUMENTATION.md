# Manager API Documentation Guide

## Swagger/OpenAPI Documentation

The Manager API includes built-in Swagger/OpenAPI documentation using SpringDoc OpenAPI v2.8.8.

### Accessing Swagger UI

Once the Manager API is running, you can access the interactive API documentation at:

```
http://localhost:8080/swagger-ui/index.html
```

Replace `localhost:8080` with your actual server address and port.

### API Groups

The API is organized into the following groups:

1. **Device APIs** (`/device/**`)
   - Device registration
   - Device management
   - Device binding/unbinding
   - Device status reporting

2. **Agent APIs** (`/agent/**`)
   - Agent management
   - Agent configuration
   - Agent templates
   - Chat history
   - Memory management
   - Voice print management
   - MCP access points

3. **Model APIs** (`/models/**`)
   - Model configuration
   - Model providers
   - Voice models
   - LLM models
   - TTS/ASR/VAD models

4. **OTA APIs** (`/ota/**`)
   - Over-the-air updates
   - Firmware management
   - Update status

5. **Timbre APIs** (`/ttsVoice/**`)
   - TTS voice management
   - Voice configuration

6. **Admin APIs** (`/admin/**`)
   - User management
   - System administration
   - Server management

7. **User APIs** (`/user/**`)
   - User authentication
   - User profile
   - Password management

8. **Config APIs** (`/config/**`)
   - System configuration
   - Agent model configuration

### OpenAPI JSON Specification

You can access the raw OpenAPI specification at:

```
http://localhost:8080/v3/api-docs
```

For specific API groups:
```
http://localhost:8080/v3/api-docs/device
http://localhost:8080/v3/api-docs/agent
http://localhost:8080/v3/api-docs/models
http://localhost:8080/v3/api-docs/ota
http://localhost:8080/v3/api-docs/timbre
http://localhost:8080/v3/api-docs/admin
http://localhost:8080/v3/api-docs/user
http://localhost:8080/v3/api-docs/config
```

## Key API Endpoints

### Authentication
- `POST /login` - User login
- `POST /logout` - User logout
- `POST /user/register` - User registration

### Agent Management
- `GET /agent/list` - Get user's agents
- `GET /agent/{id}` - Get agent details
- `POST /agent` - Create new agent
- `PUT /agent/{id}` - Update agent
- `DELETE /agent/{id}` - Delete agent
- `PUT /agent/saveMemory/{macAddress}` - Update agent memory

### Device Management
- `POST /device/register` - Register device
- `POST /device/bind` - Bind device to user
- `POST /device/unbind` - Unbind device
- `GET /device/list` - Get user's devices
- `POST /device/report` - Device status report

### Model Configuration
- `GET /models/provider` - Get model providers
- `POST /models/provider` - Add model provider
- `PUT /models/provider/{id}` - Update model provider
- `DELETE /models/provider/{id}` - Delete model provider
- `GET /models/config` - Get model configurations
- `GET /models/voice/{modelId}` - Get voice options for TTS model

### Configuration
- `GET /config/agentModels` - Get agent model configuration
- `POST /config/agentModels` - Update agent model configuration

## API Authentication

Most API endpoints require authentication. The API uses Shiro for security:

1. **Login** to get a session token:
```bash
POST /login
Content-Type: application/json

{
  "username": "your-username",
  "password": "your-password"
}
```

2. **Use the token** in subsequent requests (stored in cookies/session)

3. **Permissions** are role-based:
   - `sys:role:normal` - Normal user permissions
   - `sys:role:superAdmin` - Administrator permissions

## Example API Calls

### Create Memory Provider
```bash
POST /models/provider
Content-Type: application/json

{
  "modelType": "Memory",
  "providerCode": "mem0ai",
  "name": "Mem0 Memory Provider",
  "fields": [
    {
      "key": "api_key",
      "label": "API Key",
      "type": "password",
      "value": "your-mem0-api-key"
    }
  ],
  "sort": 1
}
```

### Update Agent Memory
```bash
PUT /agent/saveMemory/{macAddress}
Content-Type: application/json

{
  "summaryMemory": "Memory configuration instructions"
}
```

### Get Agent Configuration
```bash
GET /agent/{agentId}
```

## Data Models

The API uses DTOs (Data Transfer Objects) for request/response:

- **AgentDTO** - Agent information
- **AgentMemoryDTO** - Agent memory update
- **DeviceDTO** - Device information
- **ModelConfigDTO** - Model configuration
- **ModelProviderDTO** - Model provider configuration

All DTOs include Swagger annotations for documentation.

## Error Handling

The API returns standardized error responses:

```json
{
  "code": 0,     // 0 for success, non-zero for errors
  "msg": "Success or error message",
  "data": {}     // Response data
}
```

Common error codes:
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not found
- `500` - Internal server error

## Development Tips

1. **Use Swagger UI** for testing APIs directly in the browser
2. **Check annotations** in controller classes for detailed API documentation
3. **Review DTOs** for request/response structures
4. **Monitor logs** for debugging API issues

## Additional Resources

- Controller classes in: `src/main/java/xiaozhi/modules/*/controller/`
- DTO classes in: `src/main/java/xiaozhi/modules/*/dto/`
- Entity classes in: `src/main/java/xiaozhi/modules/*/entity/`
- Service implementations in: `src/main/java/xiaozhi/modules/*/service/`