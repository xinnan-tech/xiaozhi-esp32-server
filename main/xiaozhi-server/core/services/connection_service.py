import asyncio
import time
import threading
from typing import Dict, Any
from urllib.parse import parse_qs, urlparse

from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.components.component_registry import ComponentRegistry
from core.components.component_manager import ComponentType
from core.pipeline.message_pipeline import MessagePipeline
from core.processors.message_router import MessageRouter
from config.logger import setup_logging
from config.config_loader import get_private_config_from_api
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.utils.util import check_vad_update, check_asr_update, filter_sensitive_info

logger = setup_logging()
TAG = __name__


class ConnectionService:
    """连接服务：统一管理连接生命周期，替代ConnectionHandler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # 创建统一消息路由器
        self.message_router = MessageRouter()
        
        # 创建消息处理管道
        self.message_pipeline = MessagePipeline()
        self._setup_pipeline()
    
    def _setup_pipeline(self):
        """设置消息处理管道"""
        # 使用统一的MessageRouter替代单独的processor
        self.message_pipeline.add_processor(self.message_router)
    
    async def handle_connection(self, transport: TransportInterface, headers: Dict[str, str]):
        """处理新连接"""
        # 创建会话上下文
        context = SessionContext()
        context.config = self.config
        context.headers = headers
        
        # 设置transport接口
        context.transport = transport
        
        # 传入共享 ASR 管理器
        # 这使得 ASRAdapter 可以使用预加载的模型实例
        if '_shared_asr_manager' in self.config:
            context.shared_asr_manager = self.config['_shared_asr_manager']
            logger.bind(tag=TAG).debug("连接使用共享 ASR 实例")
        
        # 兼容性：设置websocket属性（如果transport是WebSocket）
        if hasattr(transport, '_websocket'):
            context.websocket = transport._websocket
        
        # 从headers或URL参数中提取设备信息
        await self._extract_device_info(context, headers)
        
        # 创建组件管理器
        component_manager = ComponentRegistry.create_component_manager(self.config)
        
        # 设置绑定检查事件
        bind_completed_event = asyncio.Event()
        last_bind_prompt_time = 0
        bind_prompt_interval = 60  # 绑定提示播放间隔(秒)
        
        # 启动超时检查任务
        timeout_task = None
        # 后台初始化任务
        init_task = None
        
        try:
            logger.bind(tag=TAG).info(f"新连接建立: {context.device_id} from {context.client_ip}")
            
            # 在后台初始化配置和组件（非阻塞）
            init_task = asyncio.create_task(
                self._background_initialize(context, component_manager, bind_completed_event)
            )
            
            # 启动超时检查
            timeout_task = asyncio.create_task(self._check_timeout(context, transport))
            
            # 处理消息流
            async for message in transport.receive():
                try:
                    # 检查绑定状态
                    should_process = await self._check_bind_status(
                        context, transport, bind_completed_event,
                        last_bind_prompt_time, bind_prompt_interval
                    )
                    if not should_process:
                        last_bind_prompt_time = time.time()
                        continue
                    
                    await self.message_pipeline.process_message(context, transport, message)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"处理消息时出错: {e}")
                    # 继续处理其他消息，不中断连接
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接处理出错: {e}")
        finally:
            # 清理资源
            if timeout_task and not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass
            
            if init_task and not init_task.done():
                init_task.cancel()
                try:
                    await init_task
                except asyncio.CancelledError:
                    pass
            
            # 保存记忆（异步，不阻塞关闭）
            await self._save_memory_async(context)
            
            # 清理组件
            try:
                await component_manager.cleanup_all()
            except Exception as e:
                logger.bind(tag=TAG).error(f"组件清理失败: {e}")
            
            # 执行会话清理回调
            try:
                await context.run_cleanup()
            except Exception as e:
                logger.bind(tag=TAG).error(f"会话清理失败: {e}")
            
            # 关闭传输层
            try:
                await transport.close()
            except Exception as e:
                logger.bind(tag=TAG).error(f"关闭传输层失败: {e}")
            
            logger.bind(tag=TAG).info(f"连接已关闭: {context.device_id}")
    
    async def _extract_device_info(self, context: SessionContext, headers: Dict[str, str]):
        """
        从headers中提取设备信息
        """
        context.device_id = headers.get("device-id")
        context.headers["client-id"] = headers.get("client-id")
        context.client_ip = headers.get("x-real-ip") or headers.get("x-forwarded-for", "unknown")
        
        if context.client_ip and "," in context.client_ip:
            context.client_ip = context.client_ip.split(",")[0].strip()
    
    async def _initialize_components(self, context: SessionContext, component_manager):
        """初始化必要的组件"""
        try:
            # 设置组件管理器到上下文
            context.component_manager = component_manager
            
            # 根据配置确定需要初始化的组件
            required_components = ComponentRegistry.get_required_components(context.config)
            
            # 按需初始化组件
            for component_type in required_components:
                component = await component_manager.get_component(component_type, context)
                if component:
                    logger.bind(tag=TAG).info(f"组件初始化成功: {component_type.value}")
                else:
                    logger.bind(tag=TAG).warning(f"组件初始化失败: {component_type.value}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"组件初始化出错: {e}")
            raise
    
    async def _background_initialize(
        self, 
        context: SessionContext, 
        component_manager, 
        bind_completed_event: asyncio.Event
    ):
        """在后台初始化配置和组件"""
        try:
            await self._initialize_private_config(context, bind_completed_event)
            await self._initialize_components(context, component_manager)
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"后台初始化失败: {e}")
            # 即使初始化失败，也要设置绑定完成事件，避免消息一直被丢弃
            bind_completed_event.set()
    
    async def _initialize_private_config(
        self, 
        context: SessionContext, 
        bind_completed_event: asyncio.Event
    ):
        """从API异步获取差异化配置"""
        if not context.read_config_from_api:
            context.need_bind = False
            bind_completed_event.set()
            return
        
        try:
            begin_time = time.time()
            
            # 在线程池中执行同步API调用
            loop = asyncio.get_event_loop()
            private_config = await loop.run_in_executor(
                None,
                get_private_config_from_api,
                context.config,
                context.device_id,
                context.headers.get("client-id", context.device_id)
            )
            
            if private_config:
                private_config["delete_audio"] = bool(context.config.get("delete_audio", True))
                logger.bind(tag=TAG).info(
                    f"{time.time() - begin_time:.2f}秒，获取差异化配置成功"
                )
                
                # 检查是否需要更新 VAD/ASR
                init_vad = check_vad_update(context.common_config, private_config)
                init_asr = check_asr_update(context.common_config, private_config)
                
                # 合并私有配置
                context.private_config = private_config
                context.config.update(private_config)
                
                context.need_bind = False
            else:
                context.need_bind = False
                
            bind_completed_event.set()
            
        except DeviceNotFoundException:
            logger.bind(tag=TAG).warning(f"设备 {context.device_id} 未找到，需要绑定")
            context.need_bind = True
            bind_completed_event.set()
        except DeviceBindException as e:
            logger.bind(tag=TAG).warning(f"设备绑定异常: {e}")
            context.need_bind = True
            context.bind_code = getattr(e, 'bind_code', None)
            bind_completed_event.set()
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            context.need_bind = True
            bind_completed_event.set()
    
    async def _check_bind_status(
        self,
        context: SessionContext,
        transport: TransportInterface,
        bind_completed_event: asyncio.Event,
        last_bind_prompt_time: float,
        bind_prompt_interval: int
    ) -> bool:
        """
        检查设备绑定状态
        
        Returns:
            bool: True 表示可以处理消息，False 表示需要丢弃消息
        """
        # 如果还没获取到真实绑定状态，等待一下
        if not bind_completed_event.is_set():
            try:
                await asyncio.wait_for(bind_completed_event.wait(), timeout=1)
            except asyncio.TimeoutError:
                # 超时仍未获取到真实状态，丢弃消息并提示绑定
                await self._prompt_bind_if_needed(
                    context, transport, last_bind_prompt_time, bind_prompt_interval
                )
                return False
        
        # 检查是否需要绑定
        if context.need_bind:
            await self._prompt_bind_if_needed(
                context, transport, last_bind_prompt_time, bind_prompt_interval
            )
            return False
        
        return True
    
    async def _prompt_bind_if_needed(
        self,
        context: SessionContext,
        transport: TransportInterface,
        last_prompt_time: float,
        prompt_interval: int
    ):
        """如果需要，播放绑定提示"""
        current_time = time.time()
        if current_time - last_prompt_time >= prompt_interval:
            try:
                # 复用现有的绑定提示逻辑
                from core.handle.receiveAudioHandle import check_bind_device
                asyncio.create_task(check_bind_device(context))
            except Exception as e:
                logger.bind(tag=TAG).error(f"播放绑定提示失败: {e}")
    
    async def _save_memory_async(self, context: SessionContext):
        """异步保存记忆（不阻塞连接关闭）"""
        try:
            # 获取 memory 组件
            memory = None
            if context.component_manager:
                memory = context.component_manager.get("memory")
            
            if memory and context.dialogue and hasattr(memory, 'save_memory'):
                # 在线程中异步保存，不等待完成
                def save_memory_task():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            memory.save_memory(context.dialogue.dialogue, context.session_id)
                        )
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass
                
                # 启动线程保存记忆，不等待完成
                threading.Thread(target=save_memory_task, daemon=True).start()
                logger.bind(tag=TAG).debug("记忆保存任务已启动")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动记忆保存失败: {e}")
    
    async def _check_timeout(self, context: SessionContext, transport: TransportInterface):
        """定期检查连接超时"""
        timeout_seconds = context.config.get("close_connection_no_voice_time", 120)
        check_interval = min(30, timeout_seconds // 4)  # 检查间隔为超时时间的1/4，最多30秒
        
        try:
            while transport.is_connected:
                await asyncio.sleep(check_interval)
                
                if context.is_timeout(timeout_seconds):
                    logger.bind(tag=TAG).info(f"连接超时，关闭连接: {context.session_id}")
                    await transport.close()
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.bind(tag=TAG).error(f"超时检查出错: {e}")
