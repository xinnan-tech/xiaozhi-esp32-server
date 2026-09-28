# 统一插件系统

## 概述

本系统提供统一的插件管理机制，支持两种类型的插件：

1. **拦截插件 (Interceptors)** - 通过 `BasePlugin` 类实现，用于预处理用户输入
2. **MCP函数插件** - 通过 `@register_function` 装饰器注册，提供工具函数

## 目录结构

```
plugins/
├── __init__.py              # 统一扫描和注册逻辑
├── base.py                  # BasePlugin 基类和 PluginAction 枚举
├── manager.py               # PluginManager 插件管理器
├── register.py              # @register_function 装饰器和注册系统
├── loadplugins.py           # 模块自动导入工具
│
├── functions/               # 扁平结构的MCP函数（兼容旧版）
│   └── ... (可选)
│
└── preprocess_plugin/       # 插件示例：智能家居预处理
    ├── __init__.py          # 插件主类
    ├── mcp_functions.py     # MCP函数定义
    └── intents.yaml         # 配置文件
```

## 插件开发

### 创建拦截插件

```python
# plugins/my_interceptor/__init__.py
from plugins.base import BasePlugin, PluginAction

class MyInterceptor(BasePlugin):
    def __init__(self, logger=None):
        self.name = "MyInterceptor"
        self.description = "我的拦截插件"
        self.logger = logger

    async def pre_process_text(self, conn, text):
        # 返回 (处理后的文本, 动作)
        if "特殊指令" in text:
            return "已处理", PluginAction.CLOSE
        return text, PluginAction.RELEASE
```

### 创建MCP函数插件

```python
# plugins/my_tools/__init__.py
from plugins.register import register_function, ToolType, ActionResponse, Action

@register_function("get_time", {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前时间",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}, ToolType.WAIT)
async def get_time():
    return ActionResponse(Action.RESPONSE, "当前时间...", None)
```

### 创建混合插件（推荐）

```python
# plugins/my_plugin/__init__.py
from plugins.base import BasePlugin, PluginAction
from plugins.register import register_function, ToolType, ActionResponse, Action
from .config import load_config  # 可选：插件自己的配置

# 1. 定义拦截逻辑
class MyPlugin(BasePlugin):
    def __init__(self, logger=None):
        self.name = "MyPlugin"
        self.description = "我的混合插件"
        self.logger = logger
        self.config = load_config()

    async def pre_process_text(self, conn, text):
        # 拦截逻辑
        return text, PluginAction.RELEASE

# 2. 定义MCP函数
@register_function("my_tool", {...}, ToolType.WAIT)
async def my_tool(param):
    return ActionResponse(Action.REQLLM, "结果", None)
```

## 使用插件

### 服务器启动时自动扫描

在 `core/connection.py` 中：

```python
from plugins import scan_plugins, register_plugins_to_conn

# 扫描所有插件（只需调用一次）
scan_plugins()

class ConnectionHandler:
    async def handle_connection(self, ws):
        # 注册插件到此连接
        register_plugins_to_conn(self)
        ...
```

### 插件执行流程

```
用户输入 → receiveAudioHandle.py → conn.plugin_manager.process_text()
                                      ↓
                              插件1.pre_process_text()
                                      ↓
                              插件2.pre_process_text()
                                      ↓
                              ... → 返回 (text, action)
```

## PluginAction 枚举

- `RELEASE` - 放行，继续原有流程
- `INTERCEPT` - 拦截，返回结果但不关闭
- `CLOSE` - 拦截并关闭连接

## 向后兼容

旧代码仍可使用以下路径：

- `core.plugin` → 实际导入 `plugins`
- `plugins_func.register` → 实际导入 `plugins.register`
- `core.plugin.preprocess_plugin` → 实际导入 `plugins.preprocess_plugin`

## 测试

```bash
# 测试插件扫描
uv run python -c "
from plugins import scan_plugins
scan_plugins()
print('插件扫描完成')
"

# 测试MCP函数注册
uv run python -c "
from plugins import scan_plugins
from plugins.register import all_function_registry
scan_plugins()
print('已注册函数:', list(all_function_registry.keys()))
"

# 测试拦截插件注册
uv run python -c "
from plugins import scan_plugins, register_plugins_to_conn
from plugins.manager import PluginManager

class MockConn:
    def __init__(self):
        self.plugin_manager = PluginManager()

scan_plugins()
conn = MockConn()
register_plugins_to_conn(conn)
print(f'已注册插件: {len(conn.plugin_manager.plugins)}')
"
```

## 优势

1. **统一管理** - 所有插件在 `plugins/` 目录下
2. **即插即用** - 自动扫描，无需手动导入
3. **灵活结构** - 每个插件可包含子目录和配置文件
4. **能力融合** - 一个插件可同时包含拦截和MCP能力
5. **易于扩展** - 新插件只需创建子目录
6. **向后兼容** - 旧代码无需修改
