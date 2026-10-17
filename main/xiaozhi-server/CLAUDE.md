# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **xiaozhi-esp32-server** - a WebSocket-based AI voice assistant server for ESP32 devices. The system provides real-time voice interaction with support for VAD, ASR, LLM, TTS, and a plugin-based smart home device control system.

## Core Architecture

### System Flow
```
ESP32 Device → WebSocket → VAD → ASR → [Plugin Preprocessing] → [Intent Handler] → LLM → TTS → Device
```

### Key Components

**1. Main Entry Points**
- `app.py` - Main application entry, starts WebSocket and HTTP servers
- `core/websocket_server.py` - WebSocket server, handles connections
- `core/connection.py` - ConnectionHandler, manages per-device session state

**2. Audio Processing Pipeline**
- `core/handle/receiveAudioHandle.py` - Audio message handling, VAD detection
- `core/providers/vad/` - Voice Activity Detection
- `core/providers/asr/` - Automatic Speech Recognition
- `core/providers/llm/` - Large Language Model integration
- `core/providers/tts/` - Text-to-Speech synthesis

**3. Plugin System (Critical Path)**
- `plugins/` - Plugin framework and smart home control
  - `base.py` - BasePlugin interface
  - `manager.py` - Plugin orchestration
  - `register.py` - MCP function registration
  - `preprocess_plugin/` - Smart home device control plugin
    - `__init__.py` - Intent recognition & device matching engine
    - `intents.yaml` - YAML-based intent configuration

**4. Message Handlers**
- `core/handle/` - Various message handlers
  - `textHandler/` - Text message handlers (MCP, IoT, hello, abort, server)

**5. Unified Tool System**
- `core/providers/tools/` - Unified tool handler for all tool types
  - `unified_tool_handler.py` - Main entry point
  - `server_plugins/` - Server-side plugin execution
  - `server_mcp/` - Server MCP client
  - `device_iot/` - IoT device control
  - `device_mcp/` - Device MCP client
  - `mcp_endpoint/` - External MCP endpoint integration

## Development Commands

### Running the Server
```bash
# Start the main server
uv run python app.py

# With custom config
uv run python app.py --config data/.config.yaml
```

### Running Tests
```bash
# Test plugin system (smart home intent recognition)
uv run python test_plugin.py

# Test MCP functions
uv run python test_mcp_functions.py
```

### Configuration Management
```bash
# Create custom config override
mkdir -p data
touch data/.config.yaml

# Config priority: data/.config.yaml > config.yaml
```

## Plugin System Details

### Smart Home Preprocessing Plugin
The `PreprocessPlugin` provides YAML-based intent recognition for smart home control.

#### Core Rules (11 Rules)

**Rule 1: Operation Template Matching**
- Each operation has independent templates defined in `operation_templates`
- Templates: `{action_word} {area} {deviceName}`, `{action_word} {deviceName}`, etc.
- Example: "打开筒灯" matches `{action_word} {deviceName}`

**Rule 2: Device List Construction**
- Build candidate device list based on operation's supported device classes
- From `device_class_operations`: `light: [turn_on, turn_off, bright, dim]`, `switch: [turn_on, turn_off]`

**Rule 3: Device Class Support**
- Each device class supports specific operations
- **Configurable via YAML**: `device_class_operations` in `intents.yaml`
- Example: `light` supports `set_brightness`, `switch` only supports `turn_on`/`turn_off`
- **User Customizable**: Add new device types or modify existing ones without code changes

**Rule 4: Operation Matching**
- Extract action from command using `action_mapping`
- Example: "打开" → `turn_on`

**Rule 5: Slots Definition**
- `request_word`: ["请", "帮我", "给我", "我要"]
- `all_word`: ["全部", "所有", "都"]
- `area` and `deviceName` are dynamically matched from device list

**Rule 6: Dynamic Matching**
- `area` and `deviceName` are extracted from actual device list
- Not predefined in YAML

**Rule 7: Response Randomization**
- Multiple response templates per operation
- Random selection from `responses.{operation}`

**Rule 8: Default Area Restriction**
- When `{area}` not in template/command, restrict to `default_area`
- Configurable via `global.restrict_to_default_area`

**Rule 9: Default Device Rule**
- **Critical**: When `deviceName` is substring of multiple devices AND no `{all_word}` AND default devices exist
- **Logic**: Return only devices that match default device names
- **Example**:
  - Config: `default_devices: ["客厅吊灯"]`
  - Command: "打开筒灯"
  - Matched: ["左筒灯", "右筒灯", "厨房筒灯"]
  - Result: `[]` (empty, because "客厅吊灯" not in matched devices)

**Rule 10: No Default Device**
- When `default_devices` is empty, return all matched devices
- Example: `default_devices: []` → returns all "筒灯" variants

**Rule 11: All Word Handling**
- When `{all_word}` present, operate on ALL devices matching substring
- Example: "打开所有筒灯" → ["左筒灯", "右筒灯", "厨房筒灯"]

#### Configuration: `plugins/preprocess_plugin/intents.yaml`

```yaml
# 全局配置
global:
  default_area: "客厅"
  no_match_action: "pass"  # or "fail"
  restrict_to_default_area: true

# 默认设备配置（规则9,10）
default_devices:
  - "客厅吊灯"  # 只有这个设备时，"打开筒灯"会匹配失败

# 操作映射（规则4）
action_mapping:
  turn_on: ["打开", "开启", "开", "启动"]
  turn_off: ["关闭", "关", "关上", "停止"]

# 设备类别操作支持（规则3）
# 用户可自定义每个设备类型支持的操作
device_class_operations:
  light: ["turn_on", "turn_off", "set_brightness"]
  switch: ["turn_on", "turn_off"]
  curtain: ["turn_on", "turn_off"]
  fan: ["turn_on", "turn_off"]
  outlet: ["turn_on", "turn_off"]
  lock: ["turn_on", "turn_off"]  # lock 的 turn_on=unlock, turn_off=lock
  # 示例：用户可添加更多设备类别
  # air_conditioner: ["turn_on", "turn_off", "set_temperature"]
  # heater: ["turn_on", "turn_off", "set_temperature"]

# 按操作定义的模板（规则1）
operation_templates:
  turn_on:
    - "{action_word} {area} {deviceName}"
    - "{action_word} {deviceName}"

# Slots配置（规则5）
slots_config:
  request_word: ["请", "帮我", "给我", "我要"]
  all_word: ["全部", "所有", "都"]

# 响应配置（规则7）
responses:
  turn_on:
    - "已打开{deviceName}"
    - "好的，已打开{deviceName}"
```

#### Processing Flow

1. **Command Mapping** (Highest Priority)
   - Check exact match in `command_mappings`
   - Example: "开灯" → turn_on["客厅吊灯", "厨房筒灯"]

2. **Operation Template Matching** (Rule 1)
   - Extract action: "打开" → `turn_on`
   - Match against `operation_templates.turn_on`

3. **Extract Keywords** (Rule 5,6)
   - Area: None (from "打开筒灯")
   - Device keyword: "筒灯"

4. **Build Candidate Devices** (Rule 2,3)
   - Get devices with `device_class` supporting `turn_on`
   - Result: All switch/light devices

5. **Apply {all_word} Rule** (Rule 11)
   - Check if command contains "全部"/"所有"/"都"
   - If yes: return all matching devices

6. **Substring Matching** (Rule 4)
   - Filter candidates where `device_keyword in device_name`
   - Example: "筒灯" in ["左筒灯", "右筒灯", "厨房筒灯"] → all match

7. **Apply Default Device Rule** (Rule 9,10)
   - **Rule 9**: If `default_devices` exists and multiple matches
     - Return only devices where `device_name in default_devices`
     - **Problem**: "筒灯" not in ["客厅吊灯"] → returns []
   - **Rule 10**: If no `default_devices`, return all matches

8. **Operation Verification**
   - Filter by `device_class_operations`

9. **Response Generation**
   - Random selection from `responses.{operation}`

#### Example: "打开筒灯" Analysis

**Scenario**: Devices = ["左筒灯", "右筒灯", "客厅吊灯"], Config = `default_devices: ["客厅吊灯"]`

| Step | Result | Notes |
|------|--------|-------|
| 1. Command Mapping | No match | "打开筒灯" not in mappings |
| 2. Template Match | ✅ `{action_word} {deviceName}` | action="打开", keyword="筒灯" |
| 3. Keywords | area=None, keyword="筒灯" | No area in command |
| 4. Candidates | All devices supporting turn_on | ["左筒灯", "右筒灯", "客厅吊灯"] |
| 5. {all_word} | No | Command doesn't contain "全部" |
| 6. Substring | ["左筒灯", "右筒灯"] | "筒灯" in these names |
| 7. Default Device | ❌ [] | "客厅吊灯" not in ["左筒灯", "右筒灯"] |
| 8. Final | Empty → Pass to LLM | No devices to operate |

**Expected Behavior per Rules 9-10**:
- If `default_devices: ["客厅吊灯"]` → Returns [] (no match)
- If `default_devices: []` → Returns ["左筒灯", "右筒灯"] (Rule 10)
- If `default_devices: ["筒灯"]` → Returns ["左筒灯", "右筒灯"] (Rule 9, substring match)

#### Key Issues Found

1. **Rule 9 Implementation Bug**:
   - Current: `default_name in device_name` checks if default is substring of device
   - Should be: `device_name in default_names OR device_name matches default pattern`
   - Impact: "打开筒灯" fails when default is "客厅吊灯"

2. **Default Device Configuration**:
   - Current config only has "客厅吊灯"
   - Should include "筒灯" to match "左筒灯" and "右筒灯"
   - Or leave empty to match all variants

3. **Response for Multiple Devices**:
   - Current: Random template with single device name
   - Should: Handle multiple devices (e.g., "已打开左筒灯、右筒灯")

#### Configuration Examples

**Scenario 1: Control specific default device**
```yaml
default_devices: ["客厅吊灯"]
# "开灯" → ["客厅吊灯"]
# "打开筒灯" → [] (pass to LLM)
```

**Scenario 2: Control device family**
```yaml
default_devices: ["筒灯"]
# "开灯" → ["客厅吊灯", "筒灯"]
# "打开筒灯" → ["左筒灯", "右筒灯"]
```

**Scenario 3: No default, control all matches**
```yaml
default_devices: []
# "开灯" → ["客厅吊灯", "筒灯", "射灯", "灯带"]
# "打开筒灯" → ["左筒灯", "右筒灯"]
```

**Scenario 4: Use {all_word}**
```yaml
default_devices: ["客厅吊灯"]
# "打开所有筒灯" → ["左筒灯", "右筒灯"] (Rule 11 overrides Rule 9)
```

### Customizing Device Class Operations (Rule 3)

The `device_class_operations` configuration allows users to define which operations are supported by each device type without modifying code.

#### Example 1: Add Air Conditioner Support
```yaml
device_class_operations:
  light: ["turn_on", "turn_off", "set_brightness"]
  switch: ["turn_on", "turn_off"]
  # Add new device type
  air_conditioner: ["turn_on", "turn_off", "set_temperature"]
```

Then add corresponding templates in `operation_templates`:
```yaml
operation_templates:
  set_temperature:
    - "{request_word} {deviceName} {construct_word} {temperature_value}"
    - "{deviceName} {temperature_value}度"
```

#### Example 2: Remove Unwanted Operations
```yaml
# Only allow on/off for lights (no brightness control)
device_class_operations:
  light: ["turn_on", "turn_off"]
  switch: ["turn_on", "turn_off"]
```

#### Example 3: Custom Device Types
```yaml
device_class_operations:
  # Standard devices
  light: ["turn_on", "turn_off", "set_brightness"]
  switch: ["turn_on", "turn_off"]

  # Custom devices
  projector: ["turn_on", "turn_off"]
  humidifier: ["turn_on", "turn_off", "set_humidity"]
  speaker: ["turn_on", "turn_off", "set_volume"]
```

**Key Benefits:**
- ✅ No code changes required
- ✅ Hot reload supported (changes take effect immediately)
- ✅ Easy to extend with new device types
- ✅ Can restrict operations per device class

### Plugin Architecture
```python
# Base plugin interface
class BasePlugin:
    async def pre_process_text(self, conn, text):
        # Returns: (processed_text, PluginAction)
        # PluginAction: RELEASE, INTERCEPT, or CLOSE
        return text, PluginAction.RELEASE
```

### MCP Function Registration
```python
from plugins import register_function, ToolType

@register_function(
    name="get_weather",
    description="Get weather information",
    tool_type=ToolType.SERVER_PLUGIN
)
async def get_weather(location: str):
    # Function implementation
    pass
```

## Key Configuration Files

### `config.yaml` - Main Configuration
- Server settings (IP, ports)
- Module selection (VAD, ASR, LLM, TTS, Intent, Memory)
- Logging configuration
- TTS/audio parameters

### `plugins/preprocess_plugin/intents.yaml` - Intent Configuration
```yaml
intents:
  LightControlIntent:
    data:
      - sentences:
          - "{action_word} {device}"
          - "{action_word} {area} {device}"
    speech:
      text: "正在控制{device}"

expansion_rules:
  action_word:
    values: ["打开", "关闭", "开", "关"]
  device:
    values: ["灯", "空调", "窗帘"]

regex_patterns:
  brightness_command:
    - r'将(.+?)亮度调整为(\d+)'
    - r'亮度(\d+)%'

feature_flags:
  enable_brightness_control: true
  enable_switch_control: true

default_area:
  name: "客厅"
```

## Important Patterns

### Async Event Loop Handling
```python
# Check for running event loop before creating tasks
import asyncio
try:
    loop = asyncio.get_running_loop()
    loop.create_task(async_task())
except RuntimeError:
    # No running loop, handle appropriately
    pass
```

### Device Matching Algorithm
The system uses a sophisticated scoring algorithm:
1. **Area filtering** - Respects default area ("客厅") unless "all" keywords present
2. **Name matching** - Dynamic keyword extraction from device names
3. **Type filtering** - Domain-based filtering (e.g., only lights for brightness)
4. **Scoring** - Multi-factor scoring with tie-breaking

### Dynamic Value Extraction
For brightness commands, the system extracts values from various formats:
- "80" → 80%
- "80%" → 80%
- "亮度 80" → 80%
- "调整为 80" → 80%
- "客厅灯 80" → 80%

## Testing Strategy

### Unit Tests
- `test_plugin.py` - Full plugin system test with mock devices
- `test_mcp_functions.py` - MCP function registration tests

### Test Data
Tests use mock device data:
```python
{
    "names": "客厅吊灯",
    "domain": "switch",
    "state": "on",
    "areas": "客厅"
}
```

## Common Development Tasks

### Debugging Intent Recognition
```bash
# Run test to see matching details
uv run python test_plugin.py
```

### Modifying Intent Patterns
1. Edit `plugins/preprocess_plugin/intents.yaml`
2. Run `uv run python test_plugin.py` to verify
3. No restart needed for YAML changes (hot reload)

### Adding Device Types
1. Add to `expansion_rules.device.values` in YAML
2. Add corresponding logic if needed in `__init__.py`
3. Test with `uv run python test_plugin.py`

### Adding New MCP Functions
1. Create function in `plugins/functions/` or use `@register_function` decorator
2. Configure in `config.yaml` under `Intent.function_call.functions`
3. Function auto-registers on startup

### Adding New Plugins
```python
# 1. Create plugin directory in plugins/
# 2. Create __init__.py with BasePlugin subclass
from plugins.base import BasePlugin, PluginAction

class MyPlugin(BasePlugin):
    def __init__(self, logger=None):
        super().__init__(logger)
        self.name = "MyPlugin"
        self.description = "My custom plugin"

    async def pre_process_text(self, conn, text):
        # Your logic here
        if "special" in text:
            return "Processed", PluginAction.INTERCEPT
        return text, PluginAction.RELEASE

# 3. Plugin auto-registers via scan_plugins()
```

### Performance Considerations
- Device list is cached after first API fetch
- Template matching is O(n) where n = number of templates
- Device scoring is O(m×k) where m = devices, k = search terms
- Use `feature_flags` to disable unused intents

## Troubleshooting

### Common Issues
1. **Plugin not loading**: Check `scan_plugins()` in `plugins/__init__.py`
2. **Intent not matching**: Verify YAML syntax and expansion_rules
3. **Device not found**: Check area filtering and default_area config
4. **API failures**: Verify device_api_url in `plugins/preprocess_plugin/__init__.py`

### Logs
- Check `tmp/server.log` for detailed logs
- Use `log_level: DEBUG` in config for verbose output
- Plugin logs use `conn.logger.bind(tag=TAG)`

## File Structure Summary
```
xiaozhi-server/
├── app.py                          # Main entry
├── config.yaml                     # Default config
├── core/
│   ├── websocket_server.py        # WebSocket server
│   ├── connection.py              # Session handler
│   ├── handle/                    # Message handlers
│   │   ├── textHandler/           # Text message handlers
│   │   └── receiveAudioHandle.py  # Audio handling
│   └── providers/                 # Module providers
│       ├── vad/                   # Voice Activity Detection
│       ├── asr/                   # Automatic Speech Recognition
│       ├── llm/                   # Large Language Model
│       ├── tts/                   # Text-to-Speech
│       ├── intent/                # Intent recognition
│       ├── memory/                # Memory storage
│       └── tools/                 # Unified tool handler
│           ├── unified_tool_handler.py
│           ├── server_plugins/    # Server-side plugins
│           ├── server_mcp/        # Server MCP client
│           ├── device_iot/        # IoT device control
│           ├── device_mcp/        # Device MCP client
│           └── mcp_endpoint/      # External MCP endpoint
├── plugins/                        # Plugin system
│   ├── __init__.py                # Plugin scanner
│   ├── base.py                    # BasePlugin interface
│   ├── manager.py                 # Plugin manager
│   ├── register.py                # MCP function registration
│   ├── loadplugins.py             # Function loader
│   └── preprocess_plugin/         # Smart home plugin
│       ├── __init__.py            # Intent engine
│       └── intents.yaml           # Intent config
├── plugins_func/                   # Legacy MCP functions
│   ├── register.py
│   └── functions/
├── test_plugin.py                 # Plugin tests
├── test_mcp_functions.py          # MCP function tests
└── data/
    └── .config.yaml               # Custom config (create this)
```

## Notes for Claude
- This is a production-ready voice assistant server
- The plugin system is the key innovation for smart home control
- YAML configuration allows non-code customization
- All async operations must handle event loop detection
- Device matching uses sophisticated scoring, not simple string matching
- Test files are comprehensive and should be run after any changes
- The system supports both legacy `plugins_func/` and new `plugins/` architecture
- Hot reload is supported for YAML configuration changes
- Plugin scanning happens at startup via `scan_plugins()` call in `connection.py`