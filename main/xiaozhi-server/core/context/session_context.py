import copy
import uuid
import time
import queue
import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable, Awaitable, Union
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Dialogue
from core.auth import AuthMiddleware
from core.utils.prompt_manager import PromptManager
from core.utils.voiceprint_provider import VoiceprintProvider
from config.logger import setup_logging


@dataclass
class SessionContext:
    """
    会话上下文：完全替换ConnectionHandler的所有功能
    承载单连接生命周期内的状态、组件、资源管理
    与传输层解耦，支持WebSocket/MQTT/UDP等多协议
    """

    # === 基础标识 ===
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: Optional[str] = None
    client_ip: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # === 配置管理 ===
    config: Dict[str, Any] = field(default_factory=dict)
    common_config: Dict[str, Any] = field(default_factory=dict)
    private_config: Dict[str, Any] = field(default_factory=dict)
    selected_module_str: str = ""
    
    # === 认证与绑定 ===
    is_authenticated: bool = False
    need_bind: bool = False
    bind_code: Optional[str] = None
    read_config_from_api: bool = False
    max_output_size: int = 0
    chat_history_conf: int = 0
    
    # === 会话状态 ===
    is_speaking: bool = False
    listen_mode: str = "auto"
    abort_requested: bool = False
    close_after_chat: bool = False
    just_woken_up: bool = False
    load_function_plugin: bool = False
    intent_type: str = "nointent"
    
    # === 音频相关 ===
    audio_format: str = "opus"
    client_have_voice: bool = False
    client_voice_stop: bool = False
    client_audio_buffer: bytearray = field(default_factory=bytearray)
    client_voice_window: deque = field(default_factory=lambda: deque(maxlen=5))
    last_is_voice: bool = False
    audio_flow_control: Dict[str, Any] = field(default_factory=dict)
    
    # === ASR相关 ===
    asr_audio: List[bytes] = field(default_factory=list)
    asr_audio_queue: queue.Queue = field(default_factory=queue.Queue)
    asr_priority_thread: Optional[threading.Thread] = None
    
    # === LLM相关 ===
    llm_finish_task: bool = True
    dialogue: Optional[Dialogue] = None
    current_speaker: Optional[str] = None
    sentence_id: Optional[str] = None
    
    # === TTS相关 ===
    tts_MessageText: str = ""
    
    # === IoT相关 ===
    iot_descriptors: Dict[str, Any] = field(default_factory=dict)
    func_handler: Optional[Any] = None
    
    # === 时间管理 ===
    last_activity_time_ms: float = field(default_factory=lambda: time.time() * 1000)
    created_at: float = field(default_factory=lambda: time.time())
    timeout_seconds: int = 180  # 默认超时时间
    timeout_task: Optional[asyncio.Task] = None

    # === 组件实例 ===
    # components属性通过@property方法提供，指向component_manager
    
    # === 其他状态 ===
    welcome_msg: Optional[Dict[str, Any]] = None
    prompt: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    mcp_client: Optional[Any] = None
    cmd_exit: List[str] = field(default_factory=list)
    
    # === 线程与并发 ===
    loop: Optional[asyncio.AbstractEventLoop] = None
    stop_event: Optional[threading.Event] = None
    executor: Optional[ThreadPoolExecutor] = None
    
    # === 队列管理 ===
    report_queue: queue.Queue = field(default_factory=queue.Queue)
    report_thread: Optional[threading.Thread] = None
    report_asr_enable: bool = False
    report_tts_enable: bool = False
    
    # === 组件管理器 ===
    component_manager: Optional[Any] = None
    
    # === 兼容属性（用于向后兼容TTS处理） ===
    tts: Optional[Any] = None
    websocket: Optional[Any] = None  # 兼容旧TTS组件
    transport: Optional[Any] = None  # 新的transport接口
    
    # === 工具类 ===
    auth: Optional[AuthMiddleware] = None
    prompt_manager: Optional[PromptManager] = None
    voiceprint_provider: Optional[VoiceprintProvider] = None
    server: Optional[Any] = None  # WebSocket服务器引用
    
    # === 会话级清理回调 ===
    _cleanup_callbacks: List[Callable[[], Union[None, Awaitable[None]]]] = field(default_factory=list)

    def __post_init__(self):
        """初始化后处理"""
        # 深拷贝配置避免污染
        if self.config:
            self.common_config = self.config
            self.config = copy.deepcopy(self.config)
            
            # 从配置中读取相关设置
            self.read_config_from_api = self.config.get("read_config_from_api", False)
            self.max_output_size = self.config.get("max_output_size", 0)
            self.chat_history_conf = self.config.get("chat_history_conf", 0)
            self.cmd_exit = self.config.get("exit_commands", [])
            self.timeout_seconds = int(self.config.get("close_connection_no_voice_time", 120)) + 60
            
            # 初始化认证中间件
            self.auth = AuthMiddleware(self.config)
            
            # 初始化提示词管理器
            self.prompt_manager = PromptManager(self.config, setup_logging())
        
        # 初始化对话管理
        if not self.dialogue:
            self.dialogue = Dialogue()
        
        # 初始化线程相关
        if not self.loop:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                
        if not self.stop_event:
            self.stop_event = threading.Event()
            
        if not self.executor:
            self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 初始化上报设置
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

    def update_activity(self) -> None:
        """刷新最后活跃时间"""
        self.last_activity_time_ms = time.time() * 1000
    
    def clearSpeakStatus(self) -> None:
        """清除服务端讲话状态（兼容方法）"""
        self.is_speaking = False
        logger = setup_logging()
        logger.debug("清除服务端讲话状态")
    
    def reset_vad_states(self) -> None:
        """重置VAD状态（兼容方法）"""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_stop = False
        logger = setup_logging()
        logger.debug("VAD states reset.")

    def is_timeout(self, timeout_seconds: int) -> bool:
        """检查是否超时"""
        now_ms = time.time() * 1000
        return (now_ms - self.last_activity_time_ms) > (timeout_seconds * 1000)

    def register_cleanup(self, callback: Callable[[], Union[None, Awaitable[None]]]) -> None:
        """注册会话结束时需要执行的清理回调"""
        self._cleanup_callbacks.append(callback)

    async def run_cleanup(self) -> None:
        """执行所有注册的清理回调"""
        logger = setup_logging()
        logger.info(f"Session {self.session_id} 开始执行会话级清理 ({len(self._cleanup_callbacks)} 个回调)")
        
        # 停止所有线程
        if self.stop_event:
            self.stop_event.set()
        
        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=False)
        
        # 取消超时任务
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        
        # 执行清理回调
        for callback in reversed(self._cleanup_callbacks):
            try:
                result = callback()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Session {self.session_id} 清理回调执行失败: {e}", exc_info=True)
        
        self._cleanup_callbacks.clear()
        logger.info(f"Session {self.session_id} 会话级清理完成")

    # === 兼容旧代码的属性访问 ===
    @property
    def client_is_speaking(self) -> bool:
        """兼容旧代码的属性名"""
        return self.is_speaking
    
    @client_is_speaking.setter
    def client_is_speaking(self, value: bool):
        self.is_speaking = value
    
    @property
    def client_listen_mode(self) -> str:
        """兼容旧代码的属性名"""
        return self.listen_mode
    
    @client_listen_mode.setter
    def client_listen_mode(self, value: str):
        self.listen_mode = value
    
    @property
    def client_abort(self) -> bool:
        """兼容旧代码的属性名"""
        return self.abort_requested
    
    @client_abort.setter
    def client_abort(self, value: bool):
        self.abort_requested = value
    
    @property
    def components(self):
        """组件访问器（兼容属性）"""
        return self.component_manager
    
    @components.setter
    def components(self, value):
        """组件设置器（兼容属性）- 实际设置到component_manager"""
        # 如果尝试设置components，我们忽略它或者给出警告
        # 因为components应该通过component_manager管理
        logger = setup_logging()
        logger.warning("尝试直接设置components属性，请使用component_manager")

    @property
    def last_activity_time(self) -> float:
        """兼容旧代码：返回毫秒级时间戳"""
        return self.last_activity_time_ms

    @last_activity_time.setter
    def last_activity_time(self, value: float):
        """兼容旧代码：接受毫秒级时间戳"""
        self.last_activity_time_ms = value

    # === 日志相关 ===
    @property
    def logger(self):
        """获取日志记录器"""
        return setup_logging()

    # === 工具方法 ===
    def get_component(self, component_name: str) -> Optional[Any]:
        """获取组件实例"""
        return self.components.get(component_name)
    
    def set_component(self, component_name: str, component_instance: Any) -> None:
        """设置组件实例"""
        if self.component_manager:
            self.component_manager._components[component_name] = component_instance
    
    def has_component(self, component_name: str) -> bool:
        """检查是否有指定组件"""
        return component_name in self.components
    
    def clear_audio_buffer(self) -> None:
        """清空音频缓冲区"""
        self.client_audio_buffer.clear()
        self.asr_audio.clear()
        
        # 清空队列
        try:
            while not self.asr_audio_queue.empty():
                self.asr_audio_queue.get_nowait()
        except queue.Empty:
            pass
    
    def reset_voice_state(self) -> None:
        """重置语音状态"""
        self.client_have_voice = False
        self.client_voice_stop = False
        self.last_is_voice = False
        self.client_voice_window.clear()
    
    def initialize_private_config(self) -> None:
        """初始化差异化配置（从ConnectionHandler迁移）"""
        from config.config_loader import get_private_config_from_api
        from config.manage_api_client import DeviceNotFoundException, DeviceBindException
        
        if not self.read_config_from_api:
            return
            
        try:
            # 获取设备私有配置
            private_config = get_private_config_from_api(
                self.config, self.device_id, self.headers.get("client-id")
            )
            
            if private_config:
                self.private_config = private_config
                # 合并私有配置到主配置
                self.config.update(private_config)
                
        except DeviceNotFoundException:
            self.logger.error(f"设备 {self.device_id} 未找到")
            self.need_bind = True
        except DeviceBindException as e:
            self.logger.error(f"设备绑定异常: {e}")
            self.need_bind = True
            self.bind_code = str(e)
        except Exception as e:
            self.logger.error(f"获取私有配置失败: {e}")
    
    async def initialize_components(self) -> None:
        """异步初始化组件（从ConnectionHandler迁移）"""
        if not self.component_manager:
            return
            
        try:
            # 初始化各个组件
            from core.components.component_registry import ComponentType
            
            # 按依赖顺序初始化组件
            component_types = [
                ComponentType.VAD,
                ComponentType.ASR, 
                ComponentType.LLM,
                ComponentType.MEMORY,
                ComponentType.INTENT,
                ComponentType.TTS
            ]
            
            for component_type in component_types:
                try:
                    component = await self.component_manager.get_component(component_type, self)
                    if component:
                        self.logger.info(f"组件 {component_type} 初始化成功")
                except Exception as e:
                    self.logger.error(f"组件 {component_type} 初始化失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"组件初始化失败: {e}")
    
    def __str__(self) -> str:
        return f"SessionContext(session_id={self.session_id}, device_id={self.device_id})"
    
    def __repr__(self) -> str:
        return self.__str__()


