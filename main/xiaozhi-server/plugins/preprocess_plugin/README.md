# PreprocessPlugin - 智能家居指令预处理插件

## 📋 项目概述

PreprocessPlugin 是 xiaozhi-esp32-server 的核心智能设备控制插件，通过 **YAML 配置驱动** 和 **模板匹配引擎** 实现精确的语音指令意图识别。

### 核心特性

- ✅ **11条完整规则链** - 覆盖所有智能设备控制场景
- ✅ **模板回溯机制** - 多模板顺序执行，智能匹配
- ✅ **三态返回系统** - 执行/拦截/放行，灵活集成
- ✅ **MCP函数注册** - 提供设备查询和控制接口
- ✅ **配置热加载** - 无需重启即可更新规则

---

## 🏗️ 系统架构

### 处理流程

```
用户语音指令
    ↓
命令映射（最高优先级）
    ↓
模板匹配 + 关键词提取
    ↓
设备查找 + 区域过滤
    ↓
操作支持检查
    ↓
默认设备规则
    ↓
响应生成 + API调用
```

### 核心组件

```python
class PreprocessPlugin(BasePlugin):
    """主插件 - 集成到插件系统"""

class TemplateMatcher:
    """模板匹配器 - 提取操作和关键词"""

# 辅助方法
_get_all_areas()                    # 提取所有区域
_find_devices_by_name_and_area()    # 设备查找
_filter_by_area()                   # 区域过滤
_filter_supported_devices()         # 操作支持检查
_apply_default_device_rule()        # 默认设备规则
```

---

## 📦 安装与配置

### 1. 文件结构

```
plugins/preprocess_plugin/
├── __init__.py          # 主插件代码
├── intents.yaml         # 配置文件
└── README.md           # 本文档
```

### 2. 配置文件详解

**`intents.yaml`** - 核心配置文件

```yaml
# 全局配置
global:
  default_area: "客厅"                    # 默认区域
  restrict_to_default_area: true         # 规则8：严格区域限制
  reply_on_no_match: false               # 无匹配时：false=放行LLM, true=拦截回复

# 默认设备（规则9,10）
default_devices:
  - "客厅吊灯"                           # 子串匹配时的默认设备

# 操作映射（规则4）
action_mapping:
  turn_on: ["打开", "开启", "开", "启动"]
  turn_off: ["关闭", "关", "关上", "停止"]
  bright: ["调亮", "调亮一点", "调亮些", "加亮"]
  dim: ["调暗", "调暗一点", "调暗些", "减亮"]

# 模板定义（规则1）
operation_templates:
  turn_on:
    - "{action_word} {all_word} {deviceName}"    # 打开所有灯
    - "{action_word} {area} {deviceName}"        # 打开客厅灯
    - "{request_word} {action_word} {deviceName}" # 请打开灯
    - "{action_word} {deviceName}"               # 打开灯

# Slots配置（规则5,11）
slots_config:
  request_word: ["请", "帮我", "给我", "我要"]
  all_word: ["全部", "所有", "都"]

# 响应模板（规则7）
responses:
  turn_on:
    - "已打开{deviceName}"
    - "好的，已打开{deviceName}"
    - "收到，正在打开{deviceName}"

# 命令映射（最高优先级）
command_mappings:
  "开灯":
    action: "turn_on"
    devices: ["客厅吊灯", "厨房筒灯"]
```

### 3. 集成到系统

```python
from plugins.preprocess_plugin import PreprocessPlugin
from plugins.base import PluginAction

# 初始化
plugin = PreprocessPlugin(logger=logger)

# 在消息处理中使用
async def handle_message(conn, text):
    response, action = await plugin.pre_process_text(conn, text)

    if action == PluginAction.CLOSE:
        await conn.send_message(response)
        await conn.close()
    else:
        # 放行给LLM
        await send_to_llm(response)
```

---

## 🎯 11条核心规则详解

| # | 规则 | 实现位置 | 说明 |
|---|------|----------|------|
| **1** | 操作独立模板 | `operation_templates` | turn_on/turn_off/bright/dim 各有独立模板 |
| **2** | 设备列表构建 | `_find_devices_by_name_and_area()` | 根据设备名动态查找 |
| **3** | 设备类别支持 | `_filter_supported_devices()` | light支持4种操作，switch支持2种 |
| **4** | 操作匹配 | `action_mapping` | 动作词到操作的映射 |
| **5** | Slots定义 | `slots_config` | request_word, all_word 可匹配内容 |
| **6** | 动态匹配 | 模板匹配器 | area和deviceName从设备列表动态提取 |
| **7** | 响应随机 | `_get_response()` | 多个响应模板随机选择 |
| **8** | 默认区域限制 | `_filter_by_area()` | 无区域时只匹配默认区域设备 |
| **9** | 默认设备 | `_apply_default_device_rule()` | 子串匹配时优先默认设备（精准匹配） |
| **10** | 无默认设备时全部 | `_apply_default_device_rule()` | 默认设备为空时返回所有匹配 |
| **11** | all_word处理 | 模板匹配器 | 支持"全部"/"所有"/"都"操作所有设备 |

---

## 🎯 使用示例

### 场景1：精确指定设备

**指令**: `"打开客厅吊灯"`

```python
# 处理流程
1. 模板匹配: {action_word} {area} {deviceName}
   → action="turn_on", area="客厅", device_name="吊灯"
2. 设备查找: ["客厅吊灯"]
3. 匹配成功
4. 返回: {"response": "已打开客厅吊灯", "devices": ["客厅吊灯"]}
```

### 场景2：默认区域匹配

**指令**: `"打开吊灯"`
**配置**: `default_area="客厅"`, `restrict_to_default_area=true`

```python
# 处理流程
1. 模板匹配: {action_word} {deviceName}
   → action="turn_on", area=None, device_name="吊灯"
2. 设备查找: ["左筒灯", "右筒灯", "客厅吊灯", "厨房筒灯"]
3. 区域过滤(无area + restrict_to_default_area=true):
   → 只保留客厅区域: ["左筒灯", "右筒灯", "客厅吊灯"]
4. 默认设备规则(default_devices=["客厅吊灯"]):
   → 精准匹配: ["客厅吊灯"]
5. 返回: {"response": "已打开客厅吊灯", "devices": ["客厅吊灯"]}
```

### 场景3：所有设备（规则11）

**指令**: `"打开所有灯"`
**设备**: ["左筒灯", "右筒灯", "客厅吊灯", "厨房筒灯", "悬浮灯带"]

```python
# 处理流程
1. 模板匹配: {action_word} {all_word} {deviceName}
   → action="turn_on", has_all_word=True, device_name="灯"
2. 设备查找: 所有包含"灯"的设备
   → ["左筒灯", "右筒灯", "客厅吊灯", "厨房筒灯", "悬浮灯带"]
3. 区域过滤: 跳过（因为有 all_word）
4. 操作支持: 全部支持 turn_on
5. 默认设备规则: **跳过**（因为有 all_word）
6. 返回: 打开所有5个设备 ✅

# 关键修复：has_all_word=True 时跳过默认设备规则
```

### 场景4：无默认设备（规则10）

**配置**: `default_devices: []`

```python
# 指令: "打开灯"
# 设备: ["左筒灯", "右筒灯", "客厅吊灯"]

# 处理流程
1. 模板匹配: {action_word} {deviceName}
   → device_name="灯"
2. 设备查找: ["左筒灯", "右筒灯", "客厅吊灯"]
3. 区域过滤: ["左筒灯", "右筒灯"] (客厅区域)
4. 默认设备规则: **返回所有匹配**（因为 default_devices 为空）
5. 返回: 打开左筒灯、右筒灯 ✅
```

### 场景5：命令映射（最高优先级）

**配置**:
```yaml
command_mappings:
  "开灯":
    action: "turn_on"
    devices: ["客厅吊灯", "厨房筒灯"]
```

**指令**: `"开灯"`

```python
# 处理流程
1. 命令映射检查: 直接匹配
2. 跳过所有模板匹配
3. 返回: {"devices": ["客厅吊灯", "厨房筒灯"]}
```

### 场景6：亮度调节

**指令**: `"把客厅吊灯调亮80%"`

```python
# 处理流程
1. 模板匹配: {action_word} {area} {deviceName}
   → action="bright", area="客厅", device_name="吊灯"
2. 设备查找: ["客厅吊灯"]
3. 操作支持: light 类型支持 bright
4. 亮度提取: 80%
5. 返回: {"response": "已将客厅吊灯亮度调整为80%", "action": "bright"}
```

---

## 🔧 核心方法

### 1. 插件入口

```python
async def pre_process_text(self, conn, text) -> (response, PluginAction):
    """
    三态返回：
    - PluginAction.CLOSE: 成功匹配，执行操作，关闭会话
    - PluginAction.RELEASE: 未匹配，放行给LLM
    - PluginAction.INTERCEPT: 拦截但不关闭
    """
```

### 2. 主处理流程

```python
def process(self, text: str, devices: List[Dict]) -> Dict[str, Any]:
    """
    返回格式：
    {
        "processed": True,      # 是否处理完成
        "response": "已打开...", # 响应消息
        "action": "turn_on",    # 操作类型
        "devices": ["客厅吊灯"], # 设备列表
        "confidence": 1.0       # 置信度
    }
    """
```

### 3. 模板匹配器

```python
def match_with_extraction(self, command: str, available_areas: set) -> Optional[Dict]:
    """
    返回：
    {
        "action": "turn_on",
        "device_name": "筒灯",
        "area": "客厅",        # 可能为 None
        "has_all_word": False,
        "has_request_word": False
    }
    """
```

---

## 📊 配置优先级

1. **command_mappings** - 最高优先级，直接返回
2. **operation_templates** - 模板匹配 + 设备验证
3. **has_all_word 检查** - 跳过默认设备规则
4. **默认设备规则** - 规则9,10
5. **默认区域限制** - 规则8

---

## 🧪 测试验证

### 运行测试

```bash
cd plugins/preprocess_plugin
uv run python test_plugin.py
```

### 测试覆盖

| 测试场景 | 预期结果 | 状态 |
|----------|----------|------|
| 打开客厅灯 | 已打开客厅吊灯 | ✅ |
| 打开所有灯 | 打开所有灯设备 | ✅ |
| 打开所有吊灯 | 打开所有吊灯设备 | ✅ |
| 打开灯 | 打开客厅吊灯（默认） | ✅ |
| 打开吊灯 | 打开客厅吊灯（默认） | ✅ |
| 打开客厅筒灯 | 左筒灯+右筒灯 | ✅ |
| 打开厨房筒灯 | 厨房筒灯 | ✅ |
| 开灯 | 客厅吊灯+厨房筒灯（命令映射） | ✅ |

---

## ⚙️ 关键配置说明

### default_devices 配置

```yaml
# 场景A：控制特定设备
default_devices: ["客厅吊灯"]
# "打开灯" → 只打开客厅吊灯

# 场景B：控制设备家族
default_devices: ["筒灯"]
# "打开灯" → 打开所有筒灯（左筒灯、右筒灯、厨房筒灯）

# 场景C：无默认，控制所有匹配
default_devices: []
# "打开灯" → 打开所有灯设备
```

### restrict_to_default_area

```yaml
restrict_to_default_area: true
# "打开吊灯" → 只在客厅查找

restrict_to_default_area: false
# "打开吊灯" → 在所有区域查找
```

### reply_on_no_match

```yaml
reply_on_no_match: true
# 无匹配设备时，拦截并回复

reply_on_no_match: false
# 无匹配设备时，放行给LLM
```

---

## 🔍 调试技巧

### 1. 查看详细日志

```python
# 在配置中设置
global:
  reply_on_no_match: false  # 放行模式便于调试
```

### 2. 打印设备列表

**指令**: `"打印设备列表"`

```python
# 返回自然语言格式的设备信息
"""
当前设备列表：

- 客厅吊灯（客厅）：开启，switch
- 左筒灯（客厅）：关闭，switch
- 右筒灯（客厅）：关闭，switch
- 厨房筒灯（厨房）：关闭，switch
- 悬浮灯带（卧室）：关闭，light
- 餐桌吊灯（餐厅）：关闭，switch
"""
```

### 3. 常见问题排查

| 问题 | 检查点 |
|------|--------|
| 指令无响应 | 1. 模板是否匹配<br>2. 设备是否存在<br>3. 操作是否支持 |
| 匹配到错误设备 | 1. default_devices 配置<br>2. 区域过滤设置 |
| 无法打开所有设备 | 1. all_word 是否在 slots_config<br>2. has_all_word 是否被正确处理 |
| 亮度调节失败 | 1. 设备类型是否为 light<br>2. brightness 值提取是否正确 |

---

## 📝 MCP函数

插件自动注册以下MCP函数：

### get_devices
- **描述**: 获取当前系统中的所有设备列表
- **返回**: 自然语言格式的设备信息

### turn_on_device
- **描述**: 打开指定的一个或多个设备
- **参数**: `devices: ["客厅吊灯", "筒灯"]`
- **返回**: 操作结果

### turn_off_device
- **描述**: 关闭指定的一个或多个设备
- **参数**: `devices: ["客厅吊灯", "筒灯"]`
- **返回**: 操作结果

---

## ⚠️ 重要注意事项

### 1. 模板顺序很重要

```yaml
operation_templates.turn_on:
  - "{action_word} {all_word} {deviceName}"    # 必须在前
  - "{action_word} {area} {deviceName}"
  - "{action_word} {deviceName}"
```

**原因**: "打开所有灯" 需要优先匹配包含 all_word 的模板

### 2. has_all_word 的处理

**关键修复**（第335-340行）：
```python
if has_all_word:
    final_devices = supported_devices  # 跳过默认设备规则
else:
    final_devices = self._apply_default_device_rule(supported_devices)
```

**问题**: 如果不检查 has_all_word，"打开所有灯" 只会返回默认设备

### 3. 设备数据格式

```python
{
    "names": "客厅吊灯",      # 设备名称（必须唯一）
    "areas": "客厅",          # 区域
    "device_class": "light",  # 设备类型
    "state": "on"             # 当前状态
}
```

### 4. 区域提取逻辑

- 模板包含 `{area}` → 必须从命令中提取实际存在的区域
- 模板不包含 `{area}` → 区域为 None，后续可能应用默认区域限制

---

## 🔄 版本历史

### 当前版本：v2.0

**主要更新**：
- ✅ 模板回溯机制 - 支持多模板顺序执行
- ✅ has_all_word 修复 - "打开所有灯" 正确工作
- ✅ 简化处理流程 - 从10步优化为3步核心流程
- ✅ 配置类型优化 - reply_on_no_match 改为 bool 类型

**修复的问题**：
- ❌ ~~"打开所有灯" 只打开默认设备~~
- ❌ ~~"打开所有吊灯" 只打开客厅吊灯~~
- ❌ ~~模板匹配失败无法回溯~~

---

## 📞 技术支持

### 检查清单

1. **配置文件语法** - `intents.yaml` 格式正确
2. **设备API可用** - 能够获取设备列表
3. **模板顺序正确** - all_word 模板在前
4. **has_all_word 处理** - 第335-340行代码正确

### 日志位置

```
tmp/server.log  # 详细处理日志
```

### 测试工具

```bash
# 快速测试
uv run python test_plugin.py
```

---

## 🎓 最佳实践

### 1. 配置 all_word 模板

```yaml
operation_templates:
  turn_on:
    - "{action_word} {all_word} {deviceName}"  # 必须在第一位置
    - "{action_word} {area} {deviceName}"
    - "{action_word} {deviceName}"
```

### 2. 合理配置默认设备

```yaml
# 如果希望"打开灯"控制特定设备
default_devices: ["客厅吊灯"]

# 如果希望"打开灯"控制所有灯
default_devices: []
```

### 3. 使用命令映射

对于常用指令，使用 command_mappings 提高效率：
```yaml
command_mappings:
  "开灯":
    action: "turn_on"
    devices: ["客厅吊灯", "厨房筒灯"]
```

---

**文档版本**: v2.0
**最后更新**: 2025-12-30
**状态**: ✅ 生产就绪
