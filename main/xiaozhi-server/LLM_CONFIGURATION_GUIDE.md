# LLM Configuration Guide for Xiaozhi ESP32 Server

## Table of Contents
1. [Overview](#overview)
2. [Supported LLM Providers](#supported-llm-providers)
3. [Adding LLM via Dashboard](#adding-llm-via-dashboard)
4. [Configuration Examples](#configuration-examples)
5. [Testing and Validation](#testing-and-validation)
6. [Troubleshooting](#troubleshooting)
7. [Performance Optimization](#performance-optimization)
8. [API Reference](#api-reference)

---

## Overview

The Xiaozhi ESP32 Server supports multiple Large Language Model (LLM) providers through a unified OpenAI-compatible interface. This guide explains how to add, configure, and manage different LLM providers through the Manager API dashboard.

### Architecture

```
┌─────────────────┐
│   ESP32 Device  │
│   (Audio Input) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Main Server   │
│  (Python/ASR)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LLM Provider  │ ◄── Groq, OpenAI, Anthropic, etc.
│  (API Service)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   TTS Engine    │
│ (Audio Output)  │
└─────────────────┘
```

---

## Supported LLM Providers

### OpenAI-Compatible Providers

Any provider that implements the OpenAI API standard can be integrated:

| Provider | Base URL | Models | Notes |
|----------|----------|--------|-------|
| **Groq** | `https://api.groq.com/openai/v1` | llama-3.3-70b, mixtral-8x7b | Ultra-fast inference |
| **OpenAI** | `https://api.openai.com/v1` | gpt-4, gpt-3.5-turbo | Industry standard |
| **Anthropic** | `https://api.anthropic.com/v1` | claude-3-opus, claude-3-sonnet | Via adapter |
| **DeepSeek** | `https://api.deepseek.com/v1` | deepseek-coder, deepseek-chat | Code-focused |
| **Together AI** | `https://api.together.xyz/v1` | Various open models | Multiple models |
| **Perplexity** | `https://api.perplexity.ai` | pplx-70b, pplx-7b | Search-enhanced |
| **Local (Ollama)** | `http://localhost:11434/v1` | llama2, mistral, etc. | Self-hosted |

---

## Adding LLM via Dashboard

### Step 1: Access the Dashboard

1. Navigate to: `http://192.168.1.105:8002`
2. Login with admin credentials
3. Go to **"模型配置"** (Model Configuration)

### Step 2: Fill in the Add Model Form

#### Model Information Fields

| Field | Chinese | Description | Example |
|-------|---------|-------------|---------|
| **Enable** | 启用 | Enable the model | ✅ Checked |
| **Model Name** | 模型名称 | Display name | `Groq LLM` |
| **Model Code** | 模型代码 | Unique identifier | `LLM_GroqLLM` |
| **Provider** | 提供商 | Provider type | `OpenAI接口` |
| **Sort Order** | 排序 | Display order | `1` |
| **Documentation URL** | 文档URL | API documentation | `https://console.groq.com/docs` |
| **Remarks** | 备注 | Description | `Fast inference with Llama models` |

#### Configuration Fields

| Field | Chinese | Description | Example |
|-------|---------|-------------|---------|
| **Base URL** | 基础URL | API endpoint | `https://api.groq.com/openai/v1` |
| **Model Name** | 模型名称 | Specific model | `llama-3.3-70b-versatile` |
| **API Key** | API密钥 | Authentication | `gsk_ReBJtpG...` |
| **Temperature** | 温度 | Randomness (0-1) | `0.7` |
| **Max Tokens** | 最大令牌数 | Response length | `2048` |
| **Top P** | top_p值 | Nucleus sampling | `1.0` |
| **Top K** | top_k值 | Top-k sampling | `0` |
| **Frequency Penalty** | 频率惩罚 | Repetition control | `0` |

### Step 3: Save and Apply

1. Click **保存** (Save)
2. Go to **智能体模板** (Agent Templates)
3. Select the new LLM model
4. Save the agent configuration
5. Restart the main server

---

## Configuration Examples

### Example 1: Groq (Recommended for Speed)

**Use Case**: Fast responses for real-time conversation with children

```json
{
  "model_name": "Groq LLM",
  "model_code": "LLM_GroqLLM",
  "provider": "OpenAI接口",
  "config": {
    "base_url": "https://api.groq.com/openai/v1",
    "model_name": "llama-3.3-70b-versatile",
    "api_key": "gsk_YOUR_API_KEY",
    "temperature": 0.7,
    "max_tokens": 150,
    "top_p": 0.9,
    "frequency_penalty": 0.3
  }
}
```

**Form Fields**:
- 基础URL: `https://api.groq.com/openai/v1`
- 模型名称: `llama-3.3-70b-versatile`
- API密钥: `gsk_YOUR_API_KEY`
- 温度: `0.7`
- 最大令牌数: `150` (shorter for child-friendly responses)
- top_p值: `0.9`
- 频率惩罚: `0.3` (reduce repetition)

### Example 2: OpenAI GPT-4

**Use Case**: Most advanced reasoning and creativity

```json
{
  "model_name": "OpenAI GPT-4",
  "model_code": "LLM_GPT4",
  "provider": "OpenAI接口",
  "config": {
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4-turbo-preview",
    "api_key": "sk-YOUR_API_KEY",
    "temperature": 0.8,
    "max_tokens": 200,
    "top_p": 1.0,
    "frequency_penalty": 0.2
  }
}
```

### Example 3: Local Ollama

**Use Case**: Privacy-focused, no internet required

```json
{
  "model_name": "Local Llama",
  "model_code": "LLM_Ollama",
  "provider": "OpenAI接口",
  "config": {
    "base_url": "http://localhost:11434/v1",
    "model_name": "llama2:13b",
    "api_key": "not-needed",
    "temperature": 0.7,
    "max_tokens": 200,
    "top_p": 0.95
  }
}
```

### Example 4: DeepSeek (Chinese + English)

**Use Case**: Bilingual support

```json
{
  "model_name": "DeepSeek Chat",
  "model_code": "LLM_DeepSeek",
  "provider": "OpenAI接口",
  "config": {
    "base_url": "https://api.deepseek.com/v1",
    "model_name": "deepseek-chat",
    "api_key": "YOUR_DEEPSEEK_KEY",
    "temperature": 0.7,
    "max_tokens": 200
  }
}
```

---

## System Prompt Configuration

For child-friendly AI interactions, configure the system prompt appropriately:

### Example: Cheeko - Child-Friendly Assistant

```yaml
prompt: |
  You are Cheeko, a friendly, curious, and playful AI friend for children aged 4+.
  You talk in short, clear, and fun sentences.
  You always:
  1. Start with a cheerful greeting if it's the first message
  2. Answer in simple and imaginative ways using age-appropriate words
  3. Praise or encourage the child after they respond
  4. End every message with a fun follow-up question
  5. Use a warm and positive tone at all times
  6. Avoid scary, negative, or boring content
  7. Keep responses under 50 words
  8. Never say "I don't know" - make playful guesses instead
  9. Remember you're a voice agent - responses will be spoken aloud

response_constraints:
  max_words: 50
  enforce_limit: true
```

---

## Testing and Validation

### Step 1: Test API Connection

```python
# test_llm.py
import requests
import json

def test_llm_connection(base_url, api_key, model_name):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, I'm working!' in a fun way."}
        ],
        "temperature": 0.7,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

# Test Groq
test_llm_connection(
    base_url="https://api.groq.com/openai/v1",
    api_key="gsk_YOUR_API_KEY",
    model_name="llama-3.3-70b-versatile"
)
```

### Step 2: Validate in System

1. Check Manager API logs:
```bash
tail -f manager-api.log | grep -i "llm"
```

2. Check Main Server logs:
```bash
# Should see:
# Loading LLM configuration: LLM_GroqLLM
# LLM initialized successfully
```

3. Test with device:
- Connect device
- Speak a test phrase
- Verify LLM response

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "API Key Invalid"

**Symptoms**:
- 401 Unauthorized error
- "Invalid API key" in logs

**Solutions**:
1. Verify API key is correct and active
2. Check API key has proper permissions
3. Ensure no extra spaces in API key field
4. For Groq, verify at: https://console.groq.com/keys

#### Issue 2: "Model Not Found"

**Symptoms**:
- 404 error
- "Model does not exist" error

**Solutions**:
1. Verify model name is exact (case-sensitive)
2. Check provider's model list
3. For Groq models:
   - `llama-3.3-70b-versatile`
   - `llama-3.1-8b-instant`
   - `mixtral-8x7b-32768`
   - `gemma2-9b-it`

#### Issue 3: "Rate Limit Exceeded"

**Symptoms**:
- 429 Too Many Requests
- Intermittent failures

**Solutions**:
1. Check API rate limits
2. Implement retry logic
3. Consider upgrading API plan
4. Add multiple API keys for load balancing

#### Issue 4: "Timeout Errors"

**Symptoms**:
- Request timeout
- Slow responses

**Solutions**:
1. Increase timeout settings
2. Use faster models (e.g., llama-3.1-8b-instant)
3. Reduce max_tokens
4. Check network connectivity

#### Issue 5: "Response Too Long"

**Symptoms**:
- Responses cut off
- TTS fails with long text

**Solutions**:
1. Reduce max_tokens (recommended: 50-150 for children)
2. Add response constraints in prompt
3. Implement response splitting

---

## Performance Optimization

### Model Selection Guidelines

| Use Case | Recommended Model | Settings |
|----------|------------------|----------|
| **Real-time chat** | Groq llama-3.1-8b-instant | temp=0.7, max_tokens=100 |
| **Creative stories** | GPT-4 or Claude-3 | temp=0.9, max_tokens=200 |
| **Educational** | llama-3.3-70b-versatile | temp=0.5, max_tokens=150 |
| **Local/Offline** | Ollama llama2:7b | temp=0.7, max_tokens=100 |
| **Bilingual** | DeepSeek-chat | temp=0.7, max_tokens=150 |

### Optimization Tips

1. **Response Time**:
   - Use smaller models for faster responses
   - Set appropriate max_tokens (50-150 for children)
   - Enable streaming if supported

2. **Quality vs Speed**:
   ```
   Fast: llama-3.1-8b-instant (50-100ms)
   Balanced: llama-3.3-70b-versatile (200-500ms)
   Best: GPT-4 (1-3s)
   ```

3. **Cost Optimization**:
   - Monitor token usage
   - Use smaller models for simple queries
   - Implement caching for common responses
   - Set daily limits

4. **Child-Friendly Settings**:
   - Temperature: 0.6-0.8 (balanced creativity)
   - Max tokens: 50-150 (short attention spans)
   - Frequency penalty: 0.2-0.4 (reduce repetition)
   - Presence penalty: 0.1-0.3 (topic variety)

---

## API Reference

### Model Configuration Schema

```typescript
interface LLMConfig {
  // Basic Information
  id: string;              // Unique identifier (e.g., "LLM_GroqLLM")
  model_type: "LLM";       // Always "LLM" for language models
  model_code: string;      // Code identifier
  model_name: string;      // Display name
  is_default: boolean;     // Set as default model
  is_enabled: boolean;     // Enable/disable model
  
  // Configuration
  config_json: {
    type: "openai";        // Provider type
    base_url: string;      // API endpoint
    api_key: string;       // Authentication key
    model_name: string;    // Specific model to use
    temperature?: number;  // 0.0 - 1.0
    max_tokens?: number;   // Maximum response length
    top_p?: number;        // Nucleus sampling
    top_k?: number;        // Top-k sampling
    frequency_penalty?: number;  // Repetition penalty
    presence_penalty?: number;   // Topic penalty
    stop?: string[];       // Stop sequences
    stream?: boolean;      // Enable streaming
  };
  
  // Metadata
  doc_link?: string;       // Documentation URL
  remark?: string;         // Description/notes
  sort?: number;           // Display order
}
```

### Database Table Structure

```sql
CREATE TABLE `ai_model_config` (
  `id` varchar(50) PRIMARY KEY,
  `model_type` varchar(20) NOT NULL,
  `model_code` varchar(50) NOT NULL,
  `model_name` varchar(100) NOT NULL,
  `is_default` tinyint DEFAULT 0,
  `is_enabled` tinyint DEFAULT 1,
  `config_json` text NOT NULL,
  `doc_link` varchar(500),
  `remark` text,
  `sort` int DEFAULT 0,
  `creator` bigint,
  `create_date` datetime,
  `updater` bigint,
  `update_date` datetime,
  UNIQUE KEY `uk_model_code` (`model_code`),
  KEY `idx_model_type` (`model_type`)
);
```

---

## Best Practices

### Security

1. **API Key Management**:
   - Never commit API keys to version control
   - Use environment variables in production
   - Rotate keys regularly
   - Monitor usage for anomalies

2. **Access Control**:
   - Limit dashboard access
   - Use role-based permissions
   - Audit configuration changes
   - Implement IP whitelisting

### Reliability

1. **Fallback Configuration**:
   ```json
   {
     "primary": "LLM_GroqLLM",
     "fallback": "LLM_Ollama",
     "timeout": 5000
   }
   ```

2. **Health Checks**:
   - Implement periodic health checks
   - Monitor response times
   - Track error rates
   - Set up alerts

### Child Safety

1. **Content Filtering**:
   - Implement safety filters
   - Review model outputs
   - Set appropriate temperature
   - Use system prompts effectively

2. **Response Guidelines**:
   - Keep responses short (< 50 words)
   - Use simple vocabulary
   - Maintain positive tone
   - Avoid complex topics

---

## Monitoring and Logs

### Key Metrics to Monitor

1. **Performance Metrics**:
   - Response time (p50, p95, p99)
   - Token usage per request
   - Error rate
   - Timeout rate

2. **Usage Metrics**:
   - Requests per minute
   - Active devices
   - Token consumption
   - Cost per day

3. **Quality Metrics**:
   - User engagement
   - Conversation length
   - Completion rate
   - Feedback scores

### Log Analysis

```bash
# Check LLM initialization
grep "LLM.*init" /var/log/xiaozhi/main.log

# Monitor API calls
tail -f /var/log/xiaozhi/api.log | grep -E "groq|openai|llm"

# Track errors
grep -E "ERROR.*LLM|LLM.*failed" /var/log/xiaozhi/error.log

# Response time analysis
awk '/LLM response time/ {sum+=$NF; count++} END {print "Avg:", sum/count}' main.log
```

---

## Appendix

### A. Groq Model Specifications

| Model | Context | Speed | Best For |
|-------|---------|-------|----------|
| **llama-3.3-70b-versatile** | 8k | Fast | General purpose |
| **llama-3.1-8b-instant** | 8k | Fastest | Real-time chat |
| **mixtral-8x7b-32768** | 32k | Medium | Long context |
| **gemma2-9b-it** | 8k | Fast | Instruction following |

### B. Temperature Guidelines

| Temperature | Character | Use Case |
|------------|-----------|----------|
| 0.1 - 0.3 | Focused | Facts, education |
| 0.4 - 0.6 | Balanced | General conversation |
| 0.7 - 0.8 | Creative | Stories, imagination |
| 0.9 - 1.0 | Random | Brainstorming |

### C. Quick Setup Script

```bash
#!/bin/bash
# quick_setup_groq.sh

# Configuration
API_KEY="gsk_YOUR_API_KEY"
MODEL="llama-3.3-70b-versatile"
DB_NAME="xiaozhi_db"

# Insert into database
mysql -u root -p $DB_NAME << EOF
INSERT INTO ai_model_config (
    id, model_type, model_code, model_name,
    is_default, is_enabled, config_json,
    doc_link, remark, sort, create_date
) VALUES (
    'LLM_GroqLLM', 'LLM', 'LLM_GroqLLM', 'Groq LLM',
    0, 1,
    '{"type":"openai","base_url":"https://api.groq.com/openai/v1",
      "api_key":"${API_KEY}","model_name":"${MODEL}",
      "temperature":0.7,"max_tokens":150}',
    'https://console.groq.com/docs',
    'Groq Cloud - Fast inference', 1, NOW()
) ON DUPLICATE KEY UPDATE
    config_json = VALUES(config_json),
    update_date = NOW();
EOF

echo "✅ Groq LLM added successfully!"
echo "🔄 Please restart the main server to apply changes."
```

---

## Support Resources

- **Groq Documentation**: https://console.groq.com/docs
- **OpenAI API Reference**: https://platform.openai.com/docs
- **Ollama Models**: https://ollama.ai/library
- **Community Forum**: https://github.com/xinnan-tech/xiaozhi-esp32-server/discussions

---

*Last Updated: December 2024*
*Version: 1.0.0*