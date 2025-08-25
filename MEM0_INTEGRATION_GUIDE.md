# Mem0 Integration Guide for Xiaozhi ESP32 Server

## Overview
Mem0 is a memory management system integrated into the Xiaozhi ESP32 server that provides persistent memory capabilities for AI agents. This guide explains how to configure and use mem0 with both the manager API and web dashboard.

## Architecture

### Components
1. **Memory Provider** (`main/xiaozhi-server/core/providers/memory/mem0ai/mem0ai.py`)
   - Handles memory storage and retrieval
   - Integrates with Mem0 cloud service
   - Provides search and query capabilities

2. **Manager API** (`main/manager-api`)
   - REST endpoints for memory configuration
   - Agent memory management
   - Database persistence

3. **Web Dashboard** (`main/manager-web`)
   - UI for configuring memory providers
   - Agent memory settings
   - Visual management interface

## Configuration

### 1. Setting Up Mem0 API Key

#### Via Web Dashboard:
1. Navigate to **Provider Management** page
2. Click **Add** button
3. Select **Memory Module** as Category
4. Choose **mem0ai** as Provider Code
5. Enter configuration:
   ```json
   {
     "api_key": "your-mem0-api-key",
     "api_version": "v1.1"
   }
   ```
6. Save the provider configuration

#### Via Manager API:
```bash
POST /api/model/provider
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
    },
    {
      "key": "api_version",
      "label": "API Version",
      "type": "text",
      "value": "v1.1"
    }
  ],
  "sort": 1
}
```

### 2. Configuring Agent Memory

#### Via Web Dashboard:
1. Go to **Agent Management**
2. Create or edit an agent
3. In the agent configuration, enable memory:
   - Toggle **Enable Memory** option
   - Select **mem0ai** as memory provider
   - Configure summary memory prompt

#### Via Manager API:
```bash
POST /api/agent
Content-Type: application/json

{
  "name": "My AI Assistant",
  "summaryMemory": "Build a dynamic memory network that retains key information while intelligently maintaining information evolution trajectories within limited space. Summarize important user information from conversations to provide more personalized service in future interactions.",
  "memoryProvider": "mem0ai",
  "enableMemory": true
}
```

### 3. Updating Agent Memory

The system supports dynamic memory updates through the API:

```bash
PUT /api/agent/saveMemory/{macAddress}
Content-Type: application/json

{
  "summaryMemory": "Updated memory instructions for the agent"
}
```

## Memory Flow

### 1. Memory Save Process
```python
# When a conversation occurs:
1. Messages are collected from the dialogue
2. System filters out system messages
3. Formatted messages are sent to Mem0 API
4. Memory is associated with the agent's role_id
5. Result is logged for debugging
```

### 2. Memory Query Process
```python
# When agent needs to recall information:
1. Query string is sent to search method
2. Mem0 searches memories for the user_id (role_id)
3. Results are formatted with timestamps
4. Memories are sorted by recency (newest first)
5. Formatted memory string is returned to agent
```

## Integration Points

### WebSocket Server Integration
The memory provider is initialized in `websocket_server.py`:
- Checks if "Memory" is in selected_modules
- Creates memory provider instance
- Passes to ConnectionHandler for use during conversations

### Connection Handler
In `connection.py`, the memory provider:
- Saves conversation memories after each interaction
- Queries memories when needed for context
- Integrates with the dialogue flow

## API Endpoints

### Provider Management
- `GET /api/model/provider` - List all providers including memory
- `POST /api/model/provider` - Add new memory provider
- `PUT /api/model/provider/{id}` - Update memory provider configuration
- `DELETE /api/model/provider/{id}` - Remove memory provider

### Agent Memory Management
- `GET /api/agent/{id}` - Get agent details including memory settings
- `PUT /api/agent/{id}` - Update agent including memory configuration
- `PUT /api/agent/saveMemory/{macAddress}` - Update memory by device MAC

## Database Schema

### Model Provider Table
```sql
CREATE TABLE model_provider (
  id BIGINT PRIMARY KEY,
  model_type VARCHAR(50), -- 'Memory' for memory providers
  provider_code VARCHAR(100), -- 'mem0ai'
  name VARCHAR(255),
  fields TEXT, -- JSON configuration
  sort INT
);
```

### Agent Table
```sql
CREATE TABLE agent (
  id VARCHAR(36) PRIMARY KEY,
  summary_memory TEXT, -- Memory configuration prompt
  -- other fields...
);
```

## Best Practices

### 1. Memory Prompt Design
Create effective summary memory prompts:
```text
"Build a dynamic memory network that retains key information while intelligently maintaining information evolution trajectories. Focus on:
- User preferences and habits
- Important personal information
- Conversation context and history
- Task-specific knowledge
Summarize in a way that enables personalized and contextual responses."
```

### 2. API Key Security
- Store API keys securely in the database
- Never expose keys in logs or responses
- Use environment variables for production deployments

### 3. Memory Management
- Regularly review and update memory prompts
- Monitor memory usage through Mem0 dashboard
- Clean up outdated memories periodically

### 4. Error Handling
The system includes robust error handling:
- Gracefully handles missing API keys
- Falls back to no-memory mode if service unavailable
- Logs errors for debugging without exposing sensitive data

## Troubleshooting

### Common Issues

1. **Memory not saving**
   - Check API key configuration
   - Verify mem0ai service is accessible
   - Check logs in `tmp/server.log`

2. **No memories returned**
   - Ensure agent has role_id configured
   - Verify memories exist for the user
   - Check query format and parameters

3. **Configuration not appearing**
   - Restart the xiaozhi-server after configuration changes
   - Verify database changes are committed
   - Check provider is enabled in selected_modules

### Debug Mode
Enable debug logging to see memory operations:
```yaml
# In config.yaml
log:
  log_level: DEBUG
```

## Example Integration

### Complete Setup Flow
1. **Install dependencies**:
   ```bash
   pip install mem0ai==0.1.62
   ```

2. **Configure provider in dashboard**:
   - Navigate to Provider Management
   - Add mem0ai provider with API key

3. **Create agent with memory**:
   - Go to Agent Management
   - Create new agent
   - Enable memory and select mem0ai
   - Configure summary memory prompt

4. **Test memory functionality**:
   - Connect device to agent
   - Have conversations
   - Check Mem0 dashboard for saved memories
   - Test memory recall in subsequent conversations

## Advanced Features

### Custom Memory Formatting
The system formats memories with timestamps:
```python
[2024-03-15 14:30:45] User prefers morning meetings
[2024-03-14 10:15:23] User's favorite color is blue
[2024-03-13 09:45:12] User works in software engineering
```

### Memory Search
Query specific memories:
```python
results = memory_provider.query_memory("user preferences")
```

### Batch Operations
Process multiple agents' memories:
```python
for agent in agents:
    memory_provider.role_id = agent.id
    await memory_provider.save_memory(messages)
```

## Security Considerations

1. **API Key Protection**
   - Use environment variables
   - Encrypt keys in database
   - Rotate keys regularly

2. **Data Privacy**
   - Mem0 stores data securely
   - Implement data retention policies
   - Provide user data export/deletion options

3. **Access Control**
   - Limit memory access by role
   - Audit memory operations
   - Implement rate limiting

## Performance Optimization

1. **Caching**
   - Cache frequently accessed memories
   - Use Redis for temporary storage
   - Implement TTL for cache entries

2. **Batch Processing**
   - Group memory operations
   - Use async operations where possible
   - Implement queue for high-volume scenarios

3. **Monitoring**
   - Track memory API response times
   - Monitor error rates
   - Set up alerts for failures

## Future Enhancements

Potential improvements for mem0 integration:
- Local memory fallback option
- Memory compression algorithms
- Multi-agent memory sharing
- Memory analytics dashboard
- Automated memory pruning
- Memory export/import tools

## Support

For issues or questions:
- Check logs in `tmp/server.log`
- Review Mem0 documentation at https://docs.mem0.ai
- Contact support with error details and configuration