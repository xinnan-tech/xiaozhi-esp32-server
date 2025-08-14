# Agent Base Prompt System Documentation

## Overview

The Xiaozhi server uses a sophisticated prompt system that combines user configuration with a template-based enhancement system. The `agent-base-prompt.txt` file serves as a template that wraps around user-defined prompts from configuration files, adding personality, behavior rules, and dynamic context. This document explains how the entire prompt system works, its architecture, and how it integrates with the configuration system.

## Architecture Overview

```
Configuration Loading (data/.config.yaml + config.yaml)
         ↓
   User Prompt Extraction (prompt field)
         ↓
   Template Processing (agent-base-prompt.txt)
         ↓
   Dynamic Context Injection (time, weather, location)
         ↓
   PromptManager (Enhanced Prompt Generation)
         ↓
   Dialogue System (Integration)
         ↓
   AI Assistant (Behavior)
```

## Configuration System Integration

### Configuration File Priority

The system uses a **two-tier configuration approach**:

1. **Primary Configuration**: `data/.config.yaml` (user customizations)
2. **Default Configuration**: `config.yaml` (system defaults)
3. **Merge Strategy**: User config overrides defaults using recursive merge

### Configuration Loading Process

**Location**: `main/xiaozhi-server/config/config_loader.py`

```python
def load_config():
    default_config_path = get_project_dir() + "config.yaml"
    custom_config_path = get_project_dir() + "data/.config.yaml"
    
    # Load both configurations
    default_config = read_config(default_config_path)
    custom_config = read_config(custom_config_path)
    
    # Merge with custom taking precedence
    config = merge_configs(default_config, custom_config)
    return config
```

### User Prompt Integration

The `prompt` field from your configuration becomes the foundation:

**From `data/.config.yaml`**:
```yaml
prompt: |
  You are Cheeko, a friendly, curious, and playful AI friend for children aged 4+. 
  You talk in short, clear, and fun sentences.
  # ... your custom prompt content
```

This prompt becomes the `{{base_prompt}}` variable in the template system.

## File Structure and Purpose

### Location
- **File Path**: `main/xiaozhi-server/agent-base-prompt.txt`
- **Type**: Jinja2 Template
- **Encoding**: UTF-8

### Template Variables

The prompt template uses Jinja2 syntax with the following dynamic variables:

| Variable | Description | Source | Cached |
|----------|-------------|---------|---------|
| `{{base_prompt}}` | User's custom prompt from config | Configuration | ✓ |
| `{{current_time}}` | Current timestamp | System time | ✗ |
| `{{today_date}}` | Today's date (YYYY-MM-DD) | System time | ✗ |
| `{{today_weekday}}` | Day of week in Chinese | System time | ✗ |
| `{{lunar_date}}` | Chinese lunar calendar date | cnlunar library | ✗ |
| `{{local_address}}` | User's location based on IP | IP geolocation API | ✓ |
| `{{weather_info}}` | 7-day weather forecast | Weather API | ✓ |
| `{{emojiList}}` | Allowed emoji list | Static configuration | ✓ |

## System Components

### 1. PromptManager Class

**Location**: `main/xiaozhi-server/core/utils/prompt_manager.py`

**Key Methods**:
- `_load_base_template()`: Loads and caches the template file
- `get_quick_prompt()`: Fast initialization with basic prompt
- `build_enhanced_prompt()`: Creates full prompt with dynamic data
- `update_context_info()`: Updates cached context information

**Caching Strategy**:
```python
# Cache types used
CacheType.CONFIG      # Template and device prompts
CacheType.LOCATION    # IP-based location data
CacheType.WEATHER     # Weather forecast data
CacheType.DEVICE_PROMPT # Device-specific enhanced prompts
```

### 2. Connection Integration

**Location**: `main/xiaozhi-server/core/connection.py`

**Initialization Flow**:
1. **Quick Start**: Uses `get_quick_prompt()` for immediate response capability
2. **Enhancement**: Calls `build_enhanced_prompt()` for full context
3. **Update**: Uses `change_system_prompt()` to apply to dialogue system

### 3. Dialogue System Integration

**Location**: `main/xiaozhi-server/core/utils/dialogue.py`

**Integration Method**:
- `update_system_message()`: Updates or creates system message in dialogue
- System prompt becomes the foundation for all AI responses
- Maintains conversation context with enhanced prompt

## Prompt Template Structure

### Core Sections

#### 1. Identity Section
```xml
<identity>
{{base_prompt}}
</identity>
```
- Contains user's custom prompt from configuration
- Defines the AI's basic role and personality

#### 2. Emotion Section
```xml
<emotion>
【Core Goal】You are not a cold machine! Please keenly perceive user emotions...
</emotion>
```
- Defines emotional response patterns
- Specifies emoji usage rules
- Sets tone for interactions

#### 3. Communication Style
```xml
<communication_style>
【Core Goal】Use **natural, warm, conversational** human dialogue style...
</communication_style>
```
- Establishes conversation patterns
- Defines language style and formality
- Sets response format requirements

#### 4. Length Constraints
```xml
<communication_length_constraint>
【Core Goal】All long text content output... **single reply length must not exceed 300 characters**
</communication_length_constraint>
```
- Enforces response length limits
- Defines segmentation strategies
- Guides content delivery approach

#### 5. Speaker Recognition
```xml
<speaker_recognition>
- **Recognition Prefix:** When user format is `{"speaker":"someone","content":"xxx"}`...
</speaker_recognition>
```
- Handles voice recognition integration
- Defines personalization rules
- Sets name-calling behavior

#### 6. Tool Calling Rules
```xml
<tool_calling>
【Core Principle】Prioritize using `<context>` information, **only call tools when necessary**...
</tool_calling>
```
- Defines when and how to use available functions
- Sets priority for context vs. tool usage
- Establishes calling patterns

#### 7. Dynamic Context
```xml
<context>
【Important! The following information is provided in real-time...】
- **Current Time:** {{current_time}}
- **Today's Date:** {{today_date}} ({{today_weekday}})
- **Today's Lunar Calendar:** {{lunar_date}}
- **User's City:** {{local_address}}
- **Local 7-day Weather Forecast:** {{weather_info}}
</context>
```
- Provides real-time contextual information
- Updates automatically with fresh data
- Eliminates need for certain tool calls

#### 8. Memory Section
```xml
<memory>
</memory>
```
- Placeholder for conversation history
- Populated by dialogue system
- Maintains conversation continuity

## Complete Processing Flow

### Stage 1: Configuration Loading
1. **File Reading**: System loads both `config.yaml` and `data/.config.yaml`
2. **Merging**: Custom config overrides defaults using `merge_configs()`
3. **Caching**: Merged configuration stored in CONFIG cache
4. **User Prompt Extraction**: `config["prompt"]` becomes the base prompt

### Stage 2: Template Loading
1. **Template Reading**: `PromptManager` loads `agent-base-prompt.txt`
2. **Template Caching**: Template stored in CONFIG cache for reuse
3. **Validation**: Checks file existence and readability

### Stage 3: Quick Initialization (Fast Startup)
```python
# Fast startup process - uses user prompt directly
user_prompt = config["prompt"]  # From data/.config.yaml
prompt = prompt_manager.get_quick_prompt(user_prompt)
connection.change_system_prompt(prompt)
```

### Stage 4: Context Enhancement (Full Integration)
```python
# Gather dynamic context data
prompt_manager.update_context_info(connection, client_ip)

# Build enhanced prompt with template
enhanced_prompt = prompt_manager.build_enhanced_prompt(
    user_prompt,  # Your prompt from data/.config.yaml
    device_id, 
    client_ip
)

# Apply enhanced prompt
connection.change_system_prompt(enhanced_prompt)
```

### Stage 5: Template Processing
```python
# Jinja2 template rendering
template = Template(agent_base_prompt_template)
enhanced_prompt = template.render(
    base_prompt=user_prompt,  # Your custom prompt
    current_time="{{current_time}}",
    today_date=today_date,
    today_weekday=today_weekday,
    lunar_date=lunar_date,
    local_address=local_address,
    weather_info=weather_info,
    emojiList=EMOJI_List
)
```

### Stage 6: Dialogue Integration
```python
# System message update
dialogue.update_system_message(enhanced_prompt)
```

## Caching Strategy

### Cache Levels

1. **Template Cache** (CONFIG)
   - Stores the raw template file
   - Persistent until manual invalidation
   - Shared across all connections

2. **Device Cache** (DEVICE_PROMPT)
   - Stores device-specific enhanced prompts
   - Includes personalization data
   - Per-device isolation

3. **Context Cache** (LOCATION, WEATHER)
   - Location data cached by IP address
   - Weather data cached by location
   - Time-based expiration

### Cache Keys
```python
f"prompt_template:{template_path}"     # Template cache
f"device_prompt:{device_id}"           # Device-specific prompt
f"{client_ip}"                         # Location cache
f"{location}"                          # Weather cache
```

## Configuration Integration

### Configuration File Relationship

#### `data/.config.yaml` (User Configuration - Priority 1)
```yaml
# Your custom configuration - overrides defaults
prompt: |
  You are Cheeko, a friendly, curious, and playful AI friend for children aged 4+. 
  You talk in short, clear, and fun sentences.
  # ... your custom personality and behavior

selected_module:
  LLM: GroqLLM
  TTS: elevenlabs
  VAD: TenVAD_ONNX
  ASR: SherpaASR

LLM:
  GroqLLM:
    api_key: your_groq_api_key
    model_name: openai/gpt-oss-20b

plugins:
  play_music:
    music_dir: "./music"
  get_weather:
    api_key: "your_weather_api_key"
```

#### `config.yaml` (Default Configuration - Priority 2)
```yaml
# System defaults - used when not overridden
prompt: |
  你是小智/小志，来自中国台湾省的00后女生...
  # Default personality

selected_module:
  VAD: SileroVAD
  ASR: FunASR
  LLM: ChatGLMLLM
  TTS: EdgeTTS

# ... extensive default configurations
```

#### `agent-base-prompt.txt` (Template - Enhancement Layer)
```xml
<identity>
{{base_prompt}}  <!-- Your prompt from data/.config.yaml -->
</identity>

<emotion>
【Core Goal】You are not a cold machine! Please keenly perceive user emotions...
</emotion>

<context>
- **Current Time:** {{current_time}}
- **Today's Date:** {{today_date}} ({{today_weekday}})
- **User's City:** {{local_address}}
- **Local 7-day Weather Forecast:** {{weather_info}}
</context>
```

### Configuration Merge Process

```python
# config_loader.py
def merge_configs(default_config, custom_config):
    """
    Recursively merges configurations
    custom_config takes precedence over default_config
    """
    merged = dict(default_config)
    
    for key, value in custom_config.items():
        if key in merged and isinstance(merged[key], Mapping):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value  # Custom overrides default
    
    return merged
```

### Environment Variables and API Keys
- Weather API keys (configured in `data/.config.yaml`)
- LLM API keys (GroqLLM, ChatGLM, etc.)
- TTS service keys (ElevenLabs, etc.)
- Cache settings and timeouts

## Error Handling

### Common Issues and Solutions

1. **Missing Template File**
   ```python
   # Fallback to user prompt only
   if not os.path.exists(template_path):
       logger.warning("未找到agent-base-prompt.txt文件")
       return user_prompt
   ```

2. **Template Rendering Errors**
   ```python
   # Graceful degradation
   except Exception as e:
       logger.error(f"构建增强提示词失败: {e}")
       return user_prompt
   ```

3. **Context Data Failures**
   ```python
   # Default values for missing context
   local_address = cache_manager.get(CacheType.LOCATION, client_ip) or "未知位置"
   weather_info = cache_manager.get(CacheType.WEATHER, local_address) or "天气信息获取失败"
   ```

## Performance Considerations

### Optimization Strategies

1. **Template Caching**: Template loaded once and reused
2. **Context Caching**: Location and weather data cached with TTL
3. **Device Caching**: Enhanced prompts cached per device
4. **Lazy Loading**: Context data fetched asynchronously

### Memory Usage
- Template: ~2-5KB per instance
- Enhanced prompt: ~5-15KB per device
- Context cache: ~1KB per location/weather entry

## Customization Guide

### Modifying Your AI's Personality

#### Option 1: Update User Configuration (Recommended)
1. **Edit `data/.config.yaml`**: Modify the `prompt` field
2. **Keep Template**: Leave `agent-base-prompt.txt` unchanged
3. **Restart Server**: Changes take effect on restart
4. **Benefits**: Your changes persist through updates

**Example**:
```yaml
# data/.config.yaml
prompt: |
  You are Alex, a tech-savvy assistant who loves explaining complex topics simply.
  You use analogies and real-world examples.
  You're enthusiastic about helping users learn new things.
```

#### Option 2: Modify the Template (Advanced)
1. **Edit Template File**: Modify `agent-base-prompt.txt`
2. **Clear Cache**: Restart server or clear CONFIG cache
3. **Test Changes**: Verify with new connections
4. **Warning**: Changes may be lost during system updates

### Adding New Template Variables

1. **Update Template**: Add `{{new_variable}}` placeholder in `agent-base-prompt.txt`
2. **Modify PromptManager**: Add variable to `build_enhanced_prompt()` method
3. **Update Context**: Add data source for the new variable
4. **Test Integration**: Verify variable substitution works

**Example**:
```python
# In prompt_manager.py
enhanced_prompt = template.render(
    base_prompt=user_prompt,
    # ... existing variables
    new_variable=get_new_data(),  # Add your new variable
)
```

### Custom Template Sections

You can add custom sections to the template:

```xml
<custom_behavior>
- Always ask follow-up questions to keep conversations engaging
- Use emojis from the approved list: {{emojiList}}
- Adapt your language complexity based on user responses
</custom_behavior>

<domain_expertise>
When discussing {{domain_topic}}:
- Provide practical examples
- Reference current best practices
- Suggest hands-on exercises
</domain_expertise>
```

### Configuration-Based Customization

#### Response Length Control
```yaml
# data/.config.yaml
response_constraints:
  max_words: 50
  enforce_limit: true
```

#### Module Selection
```yaml
# data/.config.yaml
selected_module:
  LLM: GroqLLM      # Fast inference
  TTS: elevenlabs   # High-quality voice
  VAD: TenVAD_ONNX  # Cross-platform VAD
  ASR: SherpaASR    # Local speech recognition
```

#### Plugin Configuration
```yaml
# data/.config.yaml
plugins:
  play_music:
    music_dir: "./my_music"
    music_ext: [".mp3", ".wav", ".flac"]
  get_weather:
    api_key: "your_api_key"
    default_location: "New York"
```

## Troubleshooting

### Debug Commands
```python
# Check template loading
logger.debug("Template loaded successfully")

# Verify variable substitution
logger.info(f"Enhanced prompt length: {len(enhanced_prompt)}")

# Monitor cache usage
cache_manager.get_stats()
```

### Common Problems

1. **Variables Not Substituting**: Check Jinja2 syntax
2. **Context Data Missing**: Verify API keys and network
3. **Cache Issues**: Clear relevant cache types
4. **Performance Problems**: Check cache hit rates

## Best Practices

### Template Design
- Keep sections focused and clear
- Use consistent formatting
- Document all variables
- Test with various scenarios

### Performance
- Cache frequently used data
- Minimize API calls
- Use appropriate cache TTLs
- Monitor memory usage

### Maintenance
- Regular template reviews
- Cache cleanup procedures
- Performance monitoring
- Error log analysis

## Special Case: Function Calling for Non-Native LLM Providers

### System Prompt for Function Calls

Some LLM providers (Dify, Coze) don't support native OpenAI-style function calling. For these providers, the system uses a separate mechanism:

**File**: `main/xiaozhi-server/core/providers/llm/system_prompt.py`

#### How It Works

1. **Detection**: When using Dify or Coze LLM providers with functions available
2. **Injection**: Function calling instructions are appended to the **user message** (not system prompt)
3. **Template**: Provides detailed JSON formatting instructions for tool usage

#### Example Flow

```python
# For Dify/Coze providers only
if len(dialogue) == 2 and functions is not None:
    last_msg = dialogue[-1]["content"]  # User message
    function_str = json.dumps(functions, ensure_ascii=False)
    
    # Append function instructions to user message
    modify_msg = get_system_prompt_for_function(function_str) + last_msg
    dialogue[-1]["content"] = modify_msg
```

#### Function Call Format Taught to AI

```xml
<tool_call>
{
    "name": "function_name",
    "arguments": {
        "param1": "value1",
        "param2": "value2"
    }
}
</tool_call>
```

### Prompt System Architecture (Complete)

```
Configuration Loading (data/.config.yaml + config.yaml)
         ↓
   User Prompt Extraction (prompt field)
         ↓
   Template Processing (agent-base-prompt.txt)
         ↓
   Dynamic Context Injection (time, weather, location)
         ↓
   PromptManager (Enhanced Prompt Generation)
         ↓
   LLM Provider Check
         ↓
   ┌─────────────────────┬─────────────────────┐
   │   Native Function   │   Non-Native        │
   │   Calling LLMs      │   Function LLMs     │
   │   (OpenAI, etc.)    │   (Dify, Coze)      │
   │                     │                     │
   │   System Prompt     │   System Prompt +   │
   │   Only              │   Function Instructions│
   │                     │   in User Message   │
   └─────────────────────┴─────────────────────┘
         ↓
   Dialogue System (Integration)
         ↓
   AI Assistant (Behavior)
```

## Key Insights

### Why This Multi-Layer System?

1. **Flexibility**: Users can customize AI personality without touching system files
2. **Consistency**: Template ensures all AIs have proper behavior guidelines
3. **Context Awareness**: Dynamic data injection keeps responses relevant
4. **Maintainability**: System updates don't overwrite user customizations
5. **Performance**: Caching at multiple levels ensures fast response times
6. **LLM Compatibility**: Handles both native and non-native function calling providers

### Best Practices

#### For Users
- **Always edit `data/.config.yaml`** for customizations
- **Keep backups** of your configuration file
- **Test changes** with simple conversations first
- **Use version control** for your config files

#### For Developers
- **Never modify user config files** programmatically
- **Use the cache system** for performance
- **Handle missing context gracefully**
- **Document new template variables**

### Common Misconceptions

❌ **"The system only uses agent-base-prompt.txt"**
✅ **Reality**: Your `data/.config.yaml` prompt is the foundation, template enhances it

❌ **"I need to edit the template for personality changes"**
✅ **Reality**: Edit the `prompt` field in `data/.config.yaml`

❌ **"Configuration changes require code modifications"**
✅ **Reality**: Most changes only require config file updates

❌ **"All LLM providers work the same way"**
✅ **Reality**: Some providers (Dify, Coze) use special function calling instructions

❌ **"Function calling instructions go in the system prompt"**
✅ **Reality**: For non-native providers, they're appended to user messages

## Related Files

### Core System Files
- `main/xiaozhi-server/config/config_loader.py` - Configuration loading and merging
- `main/xiaozhi-server/core/utils/prompt_manager.py` - Core prompt management
- `main/xiaozhi-server/core/connection.py` - Connection integration
- `main/xiaozhi-server/core/utils/dialogue.py` - Dialogue system
- `main/xiaozhi-server/core/utils/cache/manager.py` - Cache management
- `main/xiaozhi-server/core/providers/llm/system_prompt.py` - Function calling instructions for specific LLM providers

### Configuration Files
- `main/xiaozhi-server/data/.config.yaml` - **User configuration (Priority 1)**
- `main/xiaozhi-server/config.yaml` - Default configuration (Priority 2)
- `main/xiaozhi-server/agent-base-prompt.txt` - Prompt template
- `main/xiaozhi-server/core/providers/llm/system_prompt.py` - Function calling instructions template

### Related Documentation
- `docs/Deployment.md` - Configuration setup guide
- `main/xiaozhi-server/README.md` - General setup instructions

## Troubleshooting

### Common Issues

#### 1. **My prompt changes aren't taking effect**
**Solution**: 
- Verify you're editing `data/.config.yaml`, not `config.yaml`
- Restart the server to clear caches
- Check for YAML syntax errors

#### 2. **Template variables showing as literal text**
**Solution**:
- Check Jinja2 syntax in `agent-base-prompt.txt`
- Verify variable names match those in `prompt_manager.py`
- Ensure template file encoding is UTF-8

#### 3. **Context data not updating**
**Solution**:
- Check API keys for weather/location services
- Verify network connectivity
- Clear relevant cache types manually

#### 4. **Configuration merge not working**
**Solution**:
- Ensure proper YAML indentation
- Check for duplicate keys
- Validate YAML syntax with online tools

#### 5. **Function calling not working with Dify/Coze**
**Solution**:
- Verify `system_prompt.py` exists and is accessible
- Check that functions are properly formatted in JSON
- Ensure the LLM provider is correctly identified as Dify or Coze
- Verify the function instructions are being appended to user messages

### Debug Commands
```python
# Check configuration loading
logger.debug("Configuration loaded successfully")

# Verify prompt enhancement
logger.info(f"Enhanced prompt length: {len(enhanced_prompt)}")

# Monitor cache usage
cache_manager.get_stats()

# Check template rendering
logger.debug(f"Template variables: {template_vars}")
```

### Performance Monitoring

#### Cache Hit Rates
- **Template Cache**: Should be near 100% after first load
- **Device Cache**: High hit rate indicates good personalization
- **Context Cache**: Monitor TTL effectiveness

#### Memory Usage
- **Template**: ~2-5KB per instance
- **Enhanced Prompt**: ~5-15KB per device
- **Context Cache**: ~1KB per location/weather entry

## Example: Complete Flow

### 1. User Configuration
```yaml
# data/.config.yaml
prompt: |
  You are Jamie, a helpful coding mentor who explains things step by step.
  You use practical examples and encourage best practices.

selected_module:
  LLM: GroqLLM  # Native function calling support
```

### 2. Template Processing
```xml
<!-- agent-base-prompt.txt -->
<identity>
You are Jamie, a helpful coding mentor who explains things step by step.
You use practical examples and encourage best practices.
</identity>

<emotion>
【Core Goal】You are not a cold machine! Please keenly perceive user emotions...
</emotion>

<context>
- **Current Time:** 2025-01-13 14:30:00
- **Today's Date:** 2025-01-13 (Monday)
- **User's City:** San Francisco
- **Local 7-day Weather Forecast:** Sunny, 72°F...
</context>
```

### 3. Final Enhanced Prompt
The system combines your custom personality with behavioral guidelines, emotional intelligence, and real-time context to create a comprehensive system prompt that guides the AI's responses.

### 4. LLM Provider-Specific Handling

#### For Native Function Calling LLMs (OpenAI, Groq, etc.)
```
System Prompt: [Enhanced prompt from above]
User Message: "Can you help me debug this Python code?"
Functions: [Available as separate function definitions]
```

#### For Non-Native Function Calling LLMs (Dify, Coze)
```
System Prompt: [Enhanced prompt from above]
User Message: [Function calling instructions from system_prompt.py] + "Can you help me debug this Python code?"
Functions: [Embedded in the instruction template]
```

**Example of function instructions appended to user message:**
```
====
TOOL USE

You have access to a set of tools that are executed upon the user's approval...

<tool_call>
{
    "name": "function_name",
    "arguments": {
        "param1": "value1"
    }
}
</tool_call>

# Tools
[Function definitions in JSON format]
====

USER CHAT CONTENT
Can you help me debug this Python code?
```

## Version History

- **v1.0**: Initial template system
- **v1.1**: Added caching layer
- **v1.2**: Enhanced context integration
- **v1.3**: Device-specific prompts
- **v1.4**: Performance optimizations
- **v2.0**: **Configuration system integration** (Current)
  - Added `data/.config.yaml` priority system
  - Implemented configuration merging
  - Enhanced user customization capabilities

---

*This documentation reflects the current dual-configuration system where user prompts from `data/.config.yaml` are enhanced by the `agent-base-prompt.txt` template. Please update when making changes to either the configuration or prompt systems.*