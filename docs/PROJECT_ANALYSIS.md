# 小智 ESP32 服务器项目解析文档

> 项目地址：https://github.com/xinnan-tech/xiaozhi-esp32-server  
> 文档生成时间：2026-04-04  
> 文档版本：1.0

---

## 目录

1. [项目整体架构和设计理念](#1-项目整体架构和设计理念)
2. [主要模块划分和职责](#2-主要模块划分和职责)
3. [技术栈详解](#3-技术栈详解)
4. [核心代码结构和关键文件](#4-核心代码结构和关键文件)
5. [数据流和通信协议](#5-数据流和通信协议)
6. [部署方式](#6-部署方式)
7. [完整的项目目录树结构](#7-完整的项目目录树结构)
8. [API 接口说明](#8-api-接口说明)
9. [配置文件说明](#9-配置文件说明)

---

## 1. 项目整体架构和设计理念

### 1.1 项目概述

**小智 ESP32 服务器**（xiaozhi-esp32-server）是一个专为基于 ESP32 的智能硬件提供支持的**综合性后端系统**。项目基于人机共生智能理论和技术研发，为开源智能硬件项目 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 提供后端服务。

**核心功能**：
- 支持 MQTT+UDP 协议、WebSocket 协议、MCP 接入点、声纹识别、知识库
- 提供完整的语音交互能力（语音识别、大语言模型对话、语音合成）
- 支持 IoT 设备控制和智能家居集成
- 提供 Web 管理控制台和移动端管理应用

### 1.2 设计理念

#### 1.2.1 分布式多组件协作架构

系统采用**分布式、多组件协作**的架构设计，确保模块化、可维护性和可扩展性：

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户交互层                                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │ ESP32 设备   │  │ Web 管理控制台│  │ 移动端管理应用       │    │
│  │ (客户端)    │  │ (Vue.js)     │  │ (uni-app)          │    │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬──────────┘    │
│         │ WebSocket       │ HTTP/REST          │ HTTP/REST      │
└─────────┼─────────────────┼────────────────────┼────────────────┘
          │                 │                    │
┌─────────▼─────────────────▼────────────────────▼────────────────┐
│                     服务层                                       │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │  xiaozhi-server     │  │      manager-api                │  │
│  │  (Python AI 引擎)    │  │  (Java Spring Boot 管理后端)     │  │
│  │  - WebSocket 8000   │  │  - RESTful API 8002             │  │
│  │  - HTTP 8003        │  │  - MySQL/Redis                  │  │
│  │  - AI 服务集成       │  │  - 配置管理                     │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2.2 核心设计原则

1. **前后端分离**：Web 管理前端（Vue.js）与后端 API（Java Spring Boot）完全分离
2. **核心服务与管理服务分离**：AI 引擎（xiaozhi-server）专注于实时语音处理，管理服务（manager-api）专注于配置和数据持久化
3. **模块化插件化**：通过 Provider 模式和插件系统实现 AI 服务的灵活切换和功能扩展
4. **配置驱动**：支持本地配置文件和远程 API 配置，实现动态配置更新
5. **多协议支持**：同时支持 WebSocket（实时通信）、HTTP/REST（管理接口）、MQTT+UDP（IoT 控制）

### 1.3 系统特性

- **实时语音交互**：低延迟 WebSocket 双向通信，支持流式 ASR 和 TTS
- **多 AI 服务集成**：支持多种 LLM、ASR、TTS、VAD 服务提供商
- **声纹识别**：支持多用户声纹注册、管理和实时识别
- **意图识别**：支持 function_call 和 intent_llm 两种意图识别方案
- **记忆系统**：支持本地短期记忆、mem0ai 接口记忆、PowerMem 智能记忆
- **知识库集成**：支持 RAGFlow 知识库检索增强生成
- **工具调用**：支持客户端 IOT 协议、MCP 协议、服务端 MCP 协议、MCP 接入点协议
- **OTA 升级**：支持 ESP32 设备固件空中升级

---

## 2. 主要模块划分和职责

### 2.1 main/ 目录结构

```
main/
├── xiaozhi-server/        # Python AI 引擎 (核心)
├── manager-api/           # Java 管理后端
├── manager-web/           # Vue.js Web 管理前端
├── manager-mobile/        # uni-app 移动端管理应用
└── README.md              # 技术文档
```

### 2.2 xiaozhi-server 模块 (Python AI 引擎)

**端口**：8000(WebSocket)、8003(HTTP)  
**语言**：Python 3.10+  
**职责**：实时语音交互处理、AI 服务集成、ESP32 设备通信

#### 2.2.1 核心目录结构

```
xiaozhi-server/
├── app.py                      # 应用入口
├── config/                     # 配置管理
│   ├── config_loader.py        # 配置加载器
│   ├── manage_api_client.py    # manager-api 客户端
│   ├── settings.py             # 设置管理
│   └── logger.py               # 日志系统
├── core/                       # 核心业务逻辑
│   ├── websocket_server.py     # WebSocket 服务器
│   ├── connection.py           # 连接处理器
│   ├── http_server.py          # HTTP 服务器 (OTA)
│   ├── auth.py                 # 认证管理
│   ├── handle/                 # 消息处理器
│   ├── providers/              # AI 服务提供者
│   └── utils/                  # 工具函数
├── plugins_func/               # 插件系统
│   ├── functions/              # 插件函数
│   ├── loadplugins.py          # 插件加载器
│   └── register.py             # 插件注册
├── models/                     # 本地模型
├── music/                      # 音乐文件
├── test/                       # 测试页面
└── requirements.txt            # Python 依赖
```

#### 2.2.2 核心组件职责

| 组件 | 职责 |
|------|------|
| `app.py` | 应用入口，启动 WebSocket 和 HTTP 服务器，初始化全局资源 |
| `WebSocketServer` | 监听 ESP32 设备连接，为每个连接创建独立的 ConnectionHandler |
| `ConnectionHandler` | 管理单个设备会话的完整生命周期，协调 VAD/ASR/LLM/TTS 等组件 |
| `handle/*` | 消息处理模块 (音频接收、文本处理、意图识别、音频发送等) |
| `providers/*` | AI 服务提供者抽象，支持多种 ASR/LLM/TTS/VAD 服务 |
| `plugins_func/*` | 插件系统，支持函数调用和 IoT 设备控制 |

### 2.3 manager-api 模块 (Java 管理后端)

**端口**：8002  
**语言**：Java 21 + Spring Boot 3  
**职责**：配置管理、用户管理、设备管理、数据持久化

#### 2.3.1 核心目录结构

```
manager-api/
├── src/main/java/xiaozhi/
│   ├── AdminApplication.java       # Spring Boot 启动类
│   ├── common/                     # 通用组件
│   │   ├── annotation/             # 自定义注解
│   │   ├── aspect/                 # AOP 切面
│   │   ├── config/                 # 配置类
│   │   ├── dao/                    # 基础 DAO
│   │   ├── entity/                 # 基础实体
│   │   ├── exception/              # 异常处理
│   │   ├── service/                # 基础服务
│   │   ├── utils/                  # 工具类
│   │   └── validator/              # 校验器
│   └── modules/                    # 业务模块
│       ├── agent/                  # 智能体管理
│       ├── config/                 # 配置管理
│       ├── device/                 # 设备管理
│       ├── knowledge/              # 知识库管理
│       ├── llm/                    # LLM 配置
│       ├── model/                  # 模型管理
│       ├── security/               # 安全管理
│       ├── sms/                    # 短信服务
│       ├── sys/                    # 系统管理
│       ├── timbre/                 # 音色管理
│       └── voiceclone/             # 声音克隆
├── src/main/resources/
│   ├── application.yml             # Spring Boot 配置
│   ├── db/changelog/               # Liquibase 数据库变更
│   └── mapper/                     # MyBatis XML 映射
└── pom.xml                         # Maven 配置
```

#### 2.3.2 业务模块职责

| 模块 | 职责 |
|------|------|
| `agent` | 智能体管理 (创建、配置、对话历史、MCP 接入点) |
| `config` | 为 xiaozhi-server 提供配置接口 |
| `device` | ESP32 设备注册、管理、OTA 升级 |
| `knowledge` | 知识库管理 (RAGFlow 集成) |
| `llm` | LLM 模型配置管理 |
| `model` | AI 模型管理 |
| `security` | 用户认证、授权、OAuth2、密码加密 |
| `sms` | 短信验证码服务 (阿里云 SMS) |
| `sys` | 系统管理 (用户、角色、字典、参数) |
| `timbre` | TTS 音色管理 |
| `voiceclone` | 声音克隆管理 |

### 2.4 manager-web 模块 (Vue.js Web 前端)

**端口**：8001  
**框架**：Vue 2 + Element UI  
**职责**：提供图形化管理界面

### 2.5 manager-mobile 模块 (移动端管理应用)

**框架**：uni-app v3 + Vue 3 + Vite  
**职责**：提供移动端管理界面

**平台兼容性**：H5、iOS、Android、微信小程序

---

## 3. 技术栈详解

### 3.1 Python 部分 (xiaozhi-server)

#### 3.1.1 核心技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主要编程语言 |
| Asyncio | - | 异步编程框架，处理并发 WebSocket 连接 |
| websockets | 14.2 | WebSocket 服务器实现 |
| aiohttp/aiohttp_cors | 3.13.2/0.8.1 | 异步 HTTP 客户端/服务器 |
| PyYAML/ruamel.yaml | 0.18.16 | YAML 配置解析 |
| loguru | 0.7.3 | 日志系统 |
| FFmpeg | - | 音频处理和格式转换 (外部依赖) |
| opuslib_next | 1.1.5 | Opus 音频编解码 |
| pydub | 0.25.1 | 音频处理 |

#### 3.1.2 AI 服务集成

| 服务类型 | 支持平台 | 本地/云端 |
|----------|----------|-----------|
| **ASR (语音识别)** | FunASR、SherpaASR、讯飞、百度、腾讯、阿里、火山、OpenAI | 本地 + 云端 |
| **LLM (大语言模型)** | 阿里百炼、火山引擎、DeepSeek、智谱、Gemini、Ollama、Dify、FastGPT、Coze | 云端 |
| **VLLM (视觉模型)** | 阿里百炼、智谱 ChatGLMVLLM | 云端 |
| **TTS (语音合成)** | EdgeTTS、讯飞、火山、腾讯、阿里、FishSpeech、GPT_SOVITS、PaddleSpeech | 本地 + 云端 |
| **VAD (语音活动检测)** | SileroVAD | 本地 |
| **Voiceprint (声纹识别)** | 3D-Speaker | 本地 |
| **Memory (记忆)** | mem0ai、PowerMem、本地短期记忆 | 本地 + 云端 |
| **Intent (意图识别)** | function_call、intent_llm | 云端 |

### 3.2 Java 部分 (manager-api)

#### 3.2.1 核心技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Java | 21 | 主要编程语言 |
| Spring Boot | 3.4.3 | Web 应用框架 |
| Spring MVC | - | RESTful API |
| MyBatis-Plus | 3.5.5 | ORM 框架 |
| MySQL | - | 关系型数据库 |
| Redis | - | 缓存 |
| Druid | 1.2.20 | 数据库连接池 |
| Apache Shiro | 2.0.2 | 安全框架 (认证/授权) |
| Liquibase | 4.20.0 | 数据库版本控制 |
| Knife4j | 4.6.0 | API 文档生成 |

### 3.3 Vue.js 部分 (manager-web)

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | 2.6.14 | 前端框架 |
| Vue Router | 3.6.5 | 路由管理 |
| Vuex | 3.6.2 | 状态管理 |
| Element UI | 2.15.14 | UI 组件库 |
| Flyio | 0.6.14 | HTTP 客户端 |

### 3.4 uni-app 部分 (manager-mobile)

| 技术 | 版本 | 用途 |
|------|------|------|
| uni-app | v3 | 跨端框架 |
| Vue 3 | 3.4.21 | 前端框架 |
| Vite | 5.2.8 | 构建工具 |
| Pinia | 2.0.36 | 状态管理 |
| alova | 3.3.3 | 请求库 |

---

## 4. 核心代码结构和关键文件

### 4.1 xiaozhi-server 核心代码

#### 4.1.1 应用入口 (app.py)

```python
async def main():
    check_ffmpeg_installed()
    config = load_config()
    
    # auth_key 优先级：配置文件 server.auth_key > manager-api.secret > 自动生成
    auth_key = config["server"].get("auth_key", "")
    if not auth_key or len(auth_key) == 0 or "你" in auth_key:
        auth_key = config.get("manager-api", {}).get("secret", "")
        if not auth_key or len(auth_key) == 0 or "你" in auth_key:
            auth_key = str(uuid.uuid4().hex)
    
    config["server"]["auth_key"] = auth_key
    
    # 启动全局 GC 管理器 (5 分钟清理一次)
    gc_manager = get_gc_manager(interval_seconds=300)
    await gc_manager.start()
    
    # 启动 WebSocket 服务器
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())
    
    # 启动 Simple HTTP 服务器 (OTA)
    ota_server = SimpleHttpServer(config)
    ota_task = asyncio.create_task(ota_server.start())
    
    # 阻塞直到收到退出信号
    await wait_for_exit()
```

**关键点**：
- 自动配置 auth_key(用于 JWT 认证)
- 启动 WebSocket 服务器 (8000 端口) 和 HTTP 服务器 (8003 端口)
- 全局 GC 管理器定期清理资源

#### 4.1.2 WebSocket 服务器 (core/websocket_server.py)

```python
class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.config_lock = asyncio.Lock()
        
        # 初始化 AI 模块
        modules = initialize_modules(...)
        self._vad = modules["vad"]
        self._asr = modules["asr"]
        self._llm = modules["llm"]
        self._intent = modules["intent"]
        self._memory = modules["memory"]
    
    async def _handle_connection(self, websocket):
        # 1. 认证
        await self._handle_auth(websocket)
        
        # 2. 创建 ConnectionHandler
        handler = ConnectionHandler(
            self.config, self._vad, self._asr, self._llm,
            self._memory, self._intent, self
        )
        
        # 3. 处理连接
        await handler.handle_connection(websocket)
    
    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件"""
        async with self.config_lock:
            new_config = await get_config_from_api_async(self.config)
            update_vad = check_vad_update(self.config, new_config)
            update_asr = check_asr_update(self.config, new_config)
            self.config = new_config
            modules = initialize_modules(...)
```

**关键点**：
- 每个 WebSocket 连接创建独立的 ConnectionHandler
- 支持动态配置更新 (从 manager-api 拉取)
- 配置更新时按需重新初始化 AI 模块

#### 4.1.3 Provider 模式 (core/providers/)

```
core/providers/
├── asr/           # 语音识别
│   ├── base.py    # 抽象基类
│   ├── fun_local.py
│   ├── aliyun.py
│   └── ...
├── llm/           # 大语言模型
│   ├── base.py
│   ├── openai/
│   ├── AliBL/
│   └── ...
├── tts/           # 语音合成
│   ├── base.py
│   ├── edge.py
│   ├── fishspeech.py
│   └── ...
├── vad/           # 语音活动检测
│   ├── base.py
│   └── silero.py
├── memory/        # 记忆
│   ├── base.py
│   ├── mem0ai/
│   └── powermem/
└── intent/        # 意图识别
    ├── base.py
    ├── function_call/
    └── intent_llm/
```

**Provider 基类示例**：

```python
class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_chunk: bytes) -> str:
        """将音频片段转换为文本"""
        pass
    
    @abstractmethod
    def get_interface_type(self) -> InterfaceType:
        """返回接口类型 (流式/非流式)"""
        pass
```

**优势**：
- 统一接口，不同实现可互换
- 用户通过配置文件切换服务提供商
- 添加新服务只需实现 Provider 接口

#### 4.1.4 插件系统 (plugins_func/)

```python
class ToolType(Enum):
    NONE = (1, "调用完工具后，不做其他操作")
    WAIT = (2, "调用工具，等待函数返回")
    CHANGE_SYS_PROMPT = (3, "修改系统提示词")
    SYSTEM_CTL = (4, "系统控制")
    IOT_CTL = (5, "IOT 设备控制")
    MCP_CLIENT = (6, "MCP 客户端")

# 插件注册装饰器
def register_function(name, desc, type=None):
    def decorator(func):
        all_function_registry[name] = FunctionItem(name, desc, func, type)
        return func
    return decorator
```

**内置插件**：
- `get_weather` - 天气查询
- `get_news_from_chinanews` - 新闻获取
- `get_news_from_newsnow` - 新闻聚合
- `play_music` - 音乐播放
- `hass_set_state` - Home Assistant 控制
- `search_from_ragflow` - 知识库检索

### 4.2 manager-api 核心代码

#### 4.2.1 Controller 示例

```java
@RestController
@RequestMapping("/agent")
public class AgentController {
    
    @Autowired
    private AgentService agentService;
    
    @GetMapping("/list")
    public Result<List<AgentDTO>> list(@RequestParam Long userId) {
        List<AgentDTO> agents = agentService.listByUser(userId);
        return new Result<List<AgentDTO>>().ok(agents);
    }
    
    @PostMapping("/create")
    public Result<AgentDTO> create(@RequestBody AgentCreateDTO dto) {
        AgentDTO agent = agentService.create(dto);
        return new Result<AgentDTO>().ok(agent);
    }
}
```

#### 4.2.2 Service 层示例

```java
@Service
public class AgentServiceImpl implements AgentService {
    
    @Autowired
    private AgentDao agentDao;
    
    @Autowired
    private RedisUtils redisUtils;
    
    @Override
    @Transactional
    public AgentDTO create(AgentCreateDTO dto) {
        // 1. 创建智能体实体
        AgentEntity entity = new AgentEntity();
        BeanUtils.copyProperties(dto, entity);
        
        // 2. 保存到数据库
        agentDao.insert(entity);
        
        // 3. 缓存到 Redis
        redisUtils.set("agent:" + entity.getId(), entity, 3600);
        
        return convertToDTO(entity);
    }
}
```

---

## 5. 数据流和通信协议

### 5.1 核心语音交互流程 (ESP32 ↔ xiaozhi-server)

**通信协议**：WebSocket(全双工实时通信)  
**协议文档**：https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh

#### 5.1.1 连接建立与握手

1. ESP32 设备向 `ws://<服务器 IP>:8000/xiaozhi/v1/` 发起 WebSocket 连接
2. 请求头携带 `device-id`和`client-id`
3. WebSocketServer 验证设备 (可选 JWT 认证或白名单)
4. 验证通过后创建 ConnectionHandler 实例
5. 执行 hello 握手协议，交换设备信息

#### 5.1.2 音频上行流程 (ESP32 → Server)

```
ESP32 麦克风
    ↓ (原始音频 PCM/Opus)
WebSocket 二进制消息
    ↓
receiveAudioHandle.py
    ↓
VAD (语音活动检测)
    ↓ (有效语音片段)
ASR (语音识别)
    ↓ (文本)
Intent (意图识别)
    ↓
LLM (大语言模型)
    ↓ (回复文本)
TTS (语音合成)
    ↓ (音频流)
WebSocket 二进制消息
    ↓
ESP32 扬声器播放
```

#### 5.1.3 关键消息类型

| 消息类型 | 方向 | 格式 | 说明 |
|----------|------|------|------|
| `hello` | 双向 | JSON | 握手协议，交换设备信息 |
| `listen` | 设备→服务器 | JSON | 开始监听指令 |
| `audio` | 双向 | 二进制 (Opus) | 音频数据流 |
| `tts` | 服务器→设备 | JSON | TTS 状态通知 |
| `iot` | 双向 | JSON | IoT 设备控制指令 |
| `mcp` | 双向 | JSON | MCP 协议消息 |
| `abort` | 设备→服务器 | JSON | 中断当前 TTS 播放 |

### 5.2 管理与配置流程 (manager-web ↔ manager-api ↔ xiaozhi-server)

**通信协议**：HTTP/REST (JSON)

#### 5.2.1 管理员配置流程

```
管理员 (浏览器)
    ↓ (HTTP POST/PUT)
manager-web (Vue.js)
    ↓ (HTTP REST API)
manager-api (Spring Boot)
    ↓ (JDBC)
MySQL 数据库
    ↓ (缓存)
Redis
```

#### 5.2.2 配置同步流程

```
xiaozhi-server 启动
    ↓
config_loader.py
    ↓ (HTTP GET)
manager-api /config/server
    ↓ (JSON)
合并本地 config.yaml 和远程配置
    ↓
initialize_modules()
    ↓
AI 服务提供者初始化完成
```

**动态配置更新**：
- xiaozhi-server 定期或按需从 manager-api 拉取配置
- 配置更新时按需重新初始化 AI 模块 (避免不必要的开销)
- 使用 `asyncio.Lock` 保证配置更新的原子性

### 5.3 MCP 协议 (Module Communication Protocol)

**用途**：服务器与 ESP32 设备之间的模块通信

#### 5.3.1 MCP 接入点模式

```
ESP32 设备
    ↓ (WebSocket)
xiaozhi-server
    ↓ (WebSocket)
MCP 接入点 (外部 MCP 服务)
    ↓
MCP 工具 (计算器、天气等)
```

**配置示例**：
```yaml
mcp_endpoint: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc
```

#### 5.3.2 工具调用流程

1. LLM 生成函数调用请求 (JSON Schema)
2. functionHandler.py 解析请求
3. 从插件注册表查找对应函数
4. 执行插件函数
5. 返回结果给 LLM
6. LLM 生成最终回复

### 5.4 OTA 升级流程

**通信协议**：HTTP + WebSocket

```
管理员 (manager-web)
    ↓ (上传固件)
manager-api
    ↓ (存储固件 + 元数据)
MySQL
    ↓ (触发更新)
xiaozhi-server
    ↓ (WebSocket 指令)
ESP32 设备
    ↓ (HTTP GET)
/xiaozhi/ota/ 端点
    ↓
下载固件并刷写
```

---

## 6. 部署方式

### 6.1 部署架构对比

| 部署方式 | 特点 | 适用场景 | 配置要求 |
|---------|------|---------|---------|
| **最简化安装** | 智能对话、单智能体管理 | 低配置环境，数据存储在配置文件 | 2 核 2G(全 API) / 2 核 4G(FunASR) |
| **全模块安装** | 完整功能，多用户管理，智控台 | 生产环境，数据存储在数据库 | 2 核 4G(全 API) / 4 核 8G(FunASR) |

### 6.2 Docker 部署 (推荐)

#### 6.2.1 最简化部署 (仅 xiaozhi-server)

**目录结构**：
```
xiaozhi-server/
├── docker-compose.yml
├── data/
│   └── .config.yaml
└── models/
    └── SenseVoiceSmall/
        └── model.pt
```

**启动命令**：
```bash
docker compose up -d
docker logs -f xiaozhi-esp32-server
```

**访问地址**：
- WebSocket: `ws://<IP>:8000/xiaozhi/v1/`
- OTA: `http://<IP>:8003/xiaozhi/ota/`
- 视觉分析：`http://<IP>:8003/mcp/vision/explain`

#### 6.2.2 全模块部署 (所有组件)

**目录结构**：
```
xiaozhi-server/
├── docker-compose_all.yml
├── data/
│   └── .config.yaml
└── models/
    └── SenseVoiceSmall/
        └── model.pt
```

**启动命令**：
```bash
docker compose -f docker-compose_all.yml up -d
docker logs -f xiaozhi-esp32-server-web
```

**访问地址**：
- 管理后台：`http://<IP>:8002/`
- WebSocket: `ws://<IP>:8000/xiaozhi/v1/`
- OTA: `http://<IP>:8002/xiaozhi/ota/`

**组件说明**：
- `xiaozhi-esp32-server`: Python AI 引擎
- `xiaozhi-esp32-server-web`: Java 管理后端 + Vue 前端
- `xiaozhi-esp32-server-db`: MySQL 数据库
- `xiaozhi-esp32-server-redis`: Redis 缓存

### 6.3 源码部署

#### 6.3.1 Python 环境准备

```bash
# 创建 conda 环境
conda create -n xiaozhi-esp32-server python=3.10 -y
conda activate xiaozhi-esp32-server

# 安装依赖
conda install libopus ffmpeg -y
cd main/xiaozhi-server
pip install -r requirements.txt
```

#### 6.3.2 Java 环境准备

```bash
# 要求：JDK 21, Maven 3.6+
cd main/manager-api
mvn clean install
```

#### 6.3.3 启动服务

```bash
# 启动 xiaozhi-server
conda activate xiaozhi-esp32-server
cd main/xiaozhi-server
python app.py

# 启动 manager-api
cd main/manager-api
mvn spring-boot:run

# 启动 manager-web
cd main/manager-web
npm install
npm run serve
```

### 6.4 配置文件说明

**config.yaml 核心配置**：

```yaml
server:
  ip: 0.0.0.0
  port: 8000          # WebSocket 端口
  http_port: 8003     # HTTP 端口
  auth:
    enabled: false    # 是否启用认证
    allowed_devices:  # 设备白名单
      - "11:22:33:44:55:66"

selected_module:
  VAD: SileroVAD
  ASR: FunASR
  LLM: ChatGLMLLM
  TTS: EdgeTTS
  Memory: nomem
  Intent: function_call

# AI 服务配置
ASR:
  FunASR:
    type: fun_local
    model_dir: models/SenseVoiceSmall

LLM:
  ChatGLMLLM:
    type: openai
    base_url: https://api.openai.com/v1
    api_key: 你的密钥
    model_name: glm-4-flash
```

---

## 7. 完整的项目目录树结构

```
xiaozhi-esp32-server/
├── .github/                          # GitHub 配置
│   ├── ISSUE_TEMPLATE/               # Issue 模板
│   └── workflows/                    # CI/CD 工作流
├── docs/                             # 文档目录
│   ├── docker/                       # Docker 相关文档
│   ├── images/                       # 文档图片
│   ├── Deployment.md                 # 部署文档 (简化版)
│   ├── Deployment_all.md             # 部署文档 (完整版)
│   ├── FAQ.md                        # 常见问题
│   ├── mcp-endpoint-integration.md   # MCP 接入点教程
│   ├── ota-upgrade-guide.md          # OTA 升级指南
│   └── ...                           # 其他集成文档
├── main/                             # 主要代码目录
│   ├── xiaozhi-server/               # Python AI 引擎
│   │   ├── app.py                    # 应用入口
│   │   ├── config.yaml               # 配置文件
│   │   ├── requirements.txt          # Python 依赖
│   │   ├── docker-compose.yml        # Docker 配置
│   │   ├── docker-compose_all.yml    # Docker 全量配置
│   │   ├── config/                   # 配置管理
│   │   ├── core/                     # 核心业务
│   │   │   ├── websocket_server.py   # WebSocket 服务器
│   │   │   ├── connection.py         # 连接处理器
│   │   │   ├── http_server.py        # HTTP 服务器
│   │   │   ├── auth.py               # 认证管理
│   │   │   ├── handle/               # 消息处理器
│   │   │   ├── providers/            # AI 服务提供者
│   │   │   └── utils/                # 工具函数
│   │   ├── plugins_func/             # 插件系统
│   │   ├── models/                   # 本地模型
│   │   ├── music/                    # 音乐文件
│   │   ├── test/                     # 测试页面
│   │   └── performance_tester/       # 性能测试工具
│   │
│   ├── manager-api/                  # Java 管理后端
│   │   ├── pom.xml                   # Maven 配置
│   │   ├── src/main/java/xiaozhi/
│   │   │   ├── AdminApplication.java # 启动类
│   │   │   ├── common/               # 通用组件
│   │   │   └── modules/              # 业务模块
│   │   │       ├── agent/            # 智能体管理
│   │   │       ├── config/           # 配置管理
│   │   │       ├── device/           # 设备管理
│   │   │       ├── knowledge/        # 知识库
│   │   │       ├── security/         # 安全管理
│   │   │       └── sys/              # 系统管理
│   │   └── src/main/resources/
│   │       ├── application.yml       # Spring Boot 配置
│   │       └── db/changelog/         # Liquibase 变更
│   │
│   ├── manager-web/                  # Vue.js Web 前端
│   │   ├── package.json              # npm 配置
│   │   └── src/
│   │       ├── main.js               # 应用入口
│   │       ├── App.vue               # 根组件
│   │       ├── router/               # 路由
│   │       ├── store/                # Vuex
│   │       ├── apis/                 # API 封装
│   │       ├── views/                # 页面
│   │       └── components/           # 组件
│   │
│   └── manager-mobile/               # uni-app 移动端
│       ├── package.json              # npm 配置
│       └── src/
│           ├── main.ts               # 应用入口
│           ├── pages/                # 页面
│           ├── api/                  # API 封装
│           └── store/                # Pinia
│
├── Dockerfile-server                 # Server Docker 配置
├── Dockerfile-server-base            # Server 基础镜像
├── Dockerfile-web                    # Web Docker 配置
├── docker-setup.sh                   # Docker 安装脚本
├── README.md                         # 项目说明
├── README_en.md                      # 英文说明
└── LICENSE                           # MIT 许可证
```

---

## 8. API 接口说明

### 8.1 xiaozhi-server API

#### 8.1.1 WebSocket 接口

**地址**：`ws://{host}:8000/xiaozhi/v1/?device-id={device_id}&client-id={client_id}`

**连接请求头**：
```
device-id: 设备 MAC 地址
client-id: 客户端标识
authorization: Bearer {token}  (可选，认证时)
```

**消息格式**：
```json
// hello 消息 (设备→服务器)
{
  "type": "hello",
  "version": 1,
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 24000,
    "channels": 1,
    "frame_duration": 60
  }
}

// listen 消息 (设备→服务器)
{
  "type": "listen",
  "mode": "auto",  // auto: 自动检测，manual: 手动模式
  "state": "start" // start, stop, detect
}

// abort 消息 (设备→服务器)
{
  "type": "abort"
}
```

#### 8.1.2 HTTP 接口

**OTA 接口**：
```
GET /xiaozhi/ota/
返回固件下载链接
```

**视觉分析接口**：
```
POST /mcp/vision/explain
Authorization: Bearer {token}
Content-Type: application/json

请求体:
{
  "image": "base64 编码的图片",
  "question": "请描述这张图片"
}

响应:
{
  "result": "图片描述文本"
}
```

### 8.2 manager-api API

**API 文档地址**：`http://{host}:8002/xiaozhi/doc.html` (Knife4j)

#### 8.2.1 用户认证接口

```
POST /sys/login
请求体:
{
  "username": "admin",
  "password": "password123",
  "captcha": "验证码"
}

响应:
{
  "code": 0,
  "data": {
    "token": "JWT token",
    "expire": 7200,
    "userInfo": {...}
  }
}
```

#### 8.2.2 智能体管理接口

```
GET /agent/list?userId={userId}
返回智能体列表

POST /agent/create
请求体:
{
  "userId": 1,
  "name": "我的智能体",
  "prompt": "角色设定",
  "selected_module": {
    "LLM": "ChatGLMLLM",
    "TTS": "EdgeTTS"
  }
}

PUT /agent/{id}
更新智能体配置

DELETE /agent/{id}
删除智能体
```

#### 8.2.3 设备管理接口

```
GET /device/list?userId={userId}
返回设备列表

POST /device/bind
绑定设备:
{
  "userId": 1,
  "deviceMac": "11:22:33:44:55:66",
  "bindCode": "123456"
}

POST /device/ota/trigger
触发 OTA 升级:
{
  "deviceId": 1,
  "firmwareVersion": "1.0.1"
}
```

#### 8.2.4 配置管理接口

```
GET /config/server
获取服务器配置 (xiaozhi-server 启动时调用)

GET /config/agent/{agentId}
获取智能体配置

PUT /config/update
更新配置
```

#### 8.2.5 知识库接口

```
GET /knowledge/dataset/list
获取知识库列表

POST /knowledge/document/upload
上传文档到知识库

GET /knowledge/chat
知识库检索问答
```

### 8.3 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 9. 配置文件说明

### 9.1 xiaozhi-server 配置文件

**文件位置**：
- 主配置：`main/xiaozhi-server/config.yaml`
- 覆盖配置：`main/xiaozhi-server/data/.config.yaml` (优先级更高)

**配置加载逻辑**：
1. 优先读取 `data/.config.yaml`
2. 如果配置项不存在，回退到 `config.yaml`
3. 如果配置了 `manager-api.url`，从 API 拉取配置并覆盖本地配置

#### 9.1.1 服务器基础配置

```yaml
server:
  ip: 0.0.0.0                    # 监听地址
  port: 8000                     # WebSocket 端口
  http_port: 8003                # HTTP 端口
  websocket: ws://你的域名:8000/xiaozhi/v1/
  vision_explain: http://你的域名:8003/mcp/vision/explain
  auth:
    enabled: false               # 是否启用认证
    allowed_devices:             # 设备白名单
      - "11:22:33:44:55:66"
  mqtt_gateway: null             # MQTT 网关地址
  mqtt_signature_key: null       # MQTT 签名密钥
```

#### 9.1.2 日志配置

```yaml
log:
  log_format: "<green>{time:YYMMDD HH:mm:ss}</green>[{version}]-<level>{level}</level>-<light-green>{message}</light-green>"
  log_level: INFO                # INFO, DEBUG
  log_dir: tmp                   # 日志目录
  log_file: "server.log"
```

#### 9.1.3 模块选择配置

```yaml
selected_module:
  VAD: SileroVAD                 # 语音活动检测
  ASR: FunASR                    # 语音识别
  LLM: ChatGLMLLM                # 大语言模型
  VLLM: ChatGLMVLLM              # 视觉模型
  TTS: EdgeTTS                   # 语音合成
  Memory: nomem                  # 记忆模块
  Intent: function_call          # 意图识别
```

#### 9.1.4 ASR 配置示例

```yaml
ASR:
  FunASR:
    type: fun_local
    model_dir: models/SenseVoiceSmall
    output_dir: tmp/asr
    
  FunASRServer:
    type: fun_server
    url: http://127.0.0.1:10095
    
  DoubaoASR:
    type: doubao
    appid: 你的appid
    access_token: 你的 token
```

#### 9.1.5 LLM 配置示例

```yaml
LLM:
  ChatGLMLLM:
    type: openai
    base_url: https://open.bigmodel.cn/api/paas/v4/
    api_key: 你的智谱 API 密钥
    model_name: glm-4-flash
    
  AliBL:
    type: openai
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: 你的阿里百炼密钥
    model_name: qwen-turbo
    
  Ollama:
    type: ollama
    base_url: http://localhost:11434
    model_name: llama2
```

#### 9.1.6 TTS 配置示例

```yaml
TTS:
  EdgeTTS:
    type: edge
    voice: zh-CN-XiaoxiaoNeural
    
  HuoshanDoubleStreamTTS:
    type: huoshan_double_stream
    appid: 你的火山引擎 appid
    access_token: 你的火山引擎 token
    voice: BV001_streaming
    
  FishSpeech:
    type: fishspeech
    url: http://127.0.0.1:8080
    speaker: 默认说话人
```

#### 9.1.7 意图识别配置

```yaml
Intent:
  function_call:
    type: function_call
    functions:
      - change_role           # 角色切换
      - get_weather           # 天气查询
      - get_news_from_newsnow # 新闻获取
      - play_music            # 音乐播放
      - hass_set_state        # Home Assistant 控制
```

#### 9.1.8 插件配置

```yaml
plugins:
  get_weather:
    api_host: "mj7p3y7naa.re.qweatherapi.com"
    api_key: "你的天气 API 密钥"
    default_location: "广州"
    
  home_assistant:
    devices:
      - 客厅，玩具灯，switch.cuco_cn_460494544_cp1_on_p_2_1
      - 卧室，台灯，switch.iot_cn_831898993_socn1_on_p_2_1
    base_url: http://homeassistant.local:8123
    api_key: 你的 Home Assistant API 令牌
    
  play_music:
    music_dir: "./music"
    music_ext: [".mp3", ".wav", ".p3"]
    refresh_time: 300
```

#### 9.1.9 声纹识别配置

```yaml
voiceprint:
  url: http://localhost:8005      # 声纹服务地址
  speakers:
    - "test1，张三，张三是一个程序员"
    - "test2，李四，李四是一个产品经理"
  similarity_threshold: 0.4       # 识别相似度阈值
```

#### 9.1.10 记忆模块配置

```yaml
Memory:
  mem0ai:
    type: mem0ai
    api_key: 你的 mem0ai 密钥
    
  powermem:
    type: powermem
    enable_user_profile: true
    db_type: sqlite
    llm_provider: openai
    llm_model: glm-4-flash
```

### 9.2 manager-api 配置文件

**文件位置**：`main/manager-api/src/main/resources/application.yml`

```yaml
server:
  port: 8002
  servlet:
    context-path: /xiaozhi

spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://localhost:3306/xiaozhi?useUnicode=true&characterEncoding=utf-8
    username: root
    password: your_password
    
  redis:
    host: localhost
    port: 6379
    password: 
    database: 0

mybatis-plus:
  mapper-locations: classpath*:/mapper/**/*.xml
  typeAliasesPackage: xiaozhi.modules.*.entity
  configuration:
    map-underscore-to-camel-case: true
    cache-enabled: false
```

### 9.3 manager-web 配置文件

**文件位置**：`main/manager-web/.env`

```env
# 开发环境
VUE_APP_API_BASE_URL=http://localhost:8002/xiaozhi

# 生产环境
# VUE_APP_API_BASE_URL=http://your-domain:8002/xiaozhi
```

### 9.4 配置优先级

```
最高优先级
    ↓
1. manager-api 返回的配置 (如果配置了 read_config_from_api)
2. data/.config.yaml 的配置
3. config.yaml 的配置
    ↓
最低优先级
```

### 9.5 配置热更新

xiaozhi-server 支持配置热更新：

1. 在 manager-web 修改配置并保存
2. manager-api 更新数据库中的配置
3. xiaozhi-server 定期或通过触发器从 manager-api 拉取新配置
4. 检查 VAD/ASR 是否需要更新
5. 按需重新初始化 AI 模块
6. 新配置生效，无需重启服务

---

## 附录

### A. 常见问题

**Q1: 为什么连接后提示认证失败？**
A: 检查 `server.auth.enabled` 配置，如果启用认证，需要在请求头携带有效的 JWT token，或将设备加入白名单。

**Q2: ASR 识别失败怎么办？**
A: 检查 FunASR 模型文件是否下载完整，或切换到云端 ASR 服务 (如讯飞、阿里)。

**Q3: 如何查看 API 文档？**
A: 启动 manager-api 后，访问 `http://localhost:8002/xiaozhi/doc.html` 查看 Knife4j 生成的 API 文档。

**Q4: 如何添加自定义插件？**
A: 在 `plugins_func/functions/` 目录下创建新的 Python 文件，使用 `@register_function` 装饰器注册函数。

### B. 性能测试

项目提供性能测试工具：

```bash
# 测试 ASR 响应速度
python performance_tester/performance_tester_asr.py

# 测试 LLM 响应速度
python performance_tester/performance_tester_llm.py

# 测试 TTS 响应速度
python performance_tester/performance_tester_tts.py
```

### C. 相关资源

- **项目仓库**: https://github.com/xinnan-tech/xiaozhi-esp32-server
- **ESP32 固件**: https://github.com/78/xiaozhi-esp32
- **通信协议文档**: https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh
- **常见问题**: https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/FAQ.md

---

**文档结束**