#!/usr/bin/env python3
"""
小智服务器门面类
统一管理所有协议服务器的启动和停止
"""

import asyncio
from typing import Dict, Any, Optional
from config.logger import setup_logging
from core.servers.multi_protocol_server import MultiProtocolServer

logger = setup_logging()
TAG = __name__


class XiaozhiServerFacade:
    """
    小智服务器门面类
    提供统一的服务器管理接口，屏蔽内部协议复杂性

    功能：
    - 协议管理
    - 本地 ASR 模型预加载
    - 优雅启动和停止
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化服务器门面

        Args:
            config: 服务器配置字典
        """
        self.config = config
        self.multi_protocol_server: Optional[MultiProtocolServer] = None
        self.shared_asr_manager = None  # 共享 ASR 管理器
        self._retired_shared_asr_managers = []
        self.is_initialized = False
        self.is_running = False
        self.last_update_error = None
        self._cleanup_pending = False

        # 处理协议配置
        self._setup_protocol_config()

    def _setup_protocol_config(self):
        """设置协议配置"""
        try:
            protocols = self.config.get("protocols", {})
            if not isinstance(protocols, dict):
                protocols = {}
            requested = protocols.get("enabled_protocols")
            requested = requested if isinstance(requested, list) else []
            websocket_enabled = protocols.get("websocket_enabled")
            if websocket_enabled is None:
                websocket_enabled = not protocols or "websocket" in requested

            enabled_protocols = []
            if websocket_enabled:
                enabled_protocols.append("websocket")

            self.config["enabled_protocols"] = enabled_protocols
            logger.info(f"启用的协议: {enabled_protocols}")

        except Exception as e:
            logger.error(f"设置协议配置失败: {e}")
            # 使用最基本的配置
            self.config["enabled_protocols"] = ["websocket"]

    async def initialize(self):
        """初始化服务器"""
        if self.is_initialized:
            logger.bind(tag=TAG).warning("服务器已经初始化")
            return

        try:
            logger.bind(tag=TAG).info("正在初始化小智服务器...")

            # 检查并预加载本地 ASR 模型（关键步骤）
            await self._preload_asr_if_needed()

            # 创建多协议服务器
            self.multi_protocol_server = MultiProtocolServer(self.config)
            self.multi_protocol_server.set_management_owner(self)

            self.is_initialized = True
            logger.bind(tag=TAG).info("小智服务器初始化完成")

        except Exception as e:
            logger.bind(tag=TAG).error(f"初始化服务器失败: {e}")
            raise

    async def _preload_asr_if_needed(self):
        """
        检查并预加载本地 ASR 模型

        如果配置使用本地 ASR 模型（如 FunASR），则在服务器启动时预加载，
        避免首次语音识别时的延迟导致客户端超时。
        """
        try:
            # 获取 ASR 配置
            selected_asr = self.config.get("selected_module", {}).get("ASR")
            if not selected_asr:
                logger.bind(tag=TAG).info("未配置 ASR 模块，跳过预加载")
                return

            # 获取 ASR 类型
            asr_config = self.config.get("ASR", {}).get(selected_asr, {})
            asr_type = asr_config.get("type", selected_asr)

            # 导入 SharedASRManager 检查是否为本地模型
            from core.providers.asr.shared_asr_manager import SharedASRManager

            if SharedASRManager.is_local_model_type(asr_type):
                logger.bind(tag=TAG).info(
                    f"检测到本地 ASR 模型: {asr_type}，开始预加载..."
                )

                # 创建全局 ASR 管理器
                self.shared_asr_manager = SharedASRManager(self.config, asr_type)

                # 预加载模型
                await self.shared_asr_manager.initialize()

                # 将管理器放入配置中供后续使用
                self.config['_shared_asr_manager'] = self.shared_asr_manager

                logger.bind(tag=TAG).info(
                    f"ASR 模型预加载完成，类型: {asr_type}"
                )
            else:
                logger.bind(tag=TAG).info(
                    f"ASR 类型为远程服务: {asr_type}，无需预加载"
                )

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR 预加载失败: {e}")
            # 预加载失败不影响服务器启动，继续使用懒加载模式
            logger.bind(tag=TAG).warning("将回退到懒加载模式")

    async def start(self):
        """启动服务器"""
        if self._cleanup_pending:
            raise RuntimeError("上次停止尚未完成，请先重试 stop 清理残留资源")
        if not self.is_initialized:
            await self.initialize()

        if self.is_running:
            logger.warning("服务器已经在运行中")
            return

        try:
            logger.info("正在启动小智服务器...")

            # 启动多协议服务器
            await self.multi_protocol_server.start()

            self.is_running = True
            logger.info("小智服务器启动成功")

        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            self.is_running = False
            # initialize() may already own a shared ASR manager and partially
            # started listeners. Release both before propagating startup failure.
            try:
                await self.stop()
            except Exception as cleanup_error:
                logger.bind(tag=TAG).error(
                    f"启动失败后的资源清理失败: {cleanup_error}"
                )
            raise

    async def stop(self):
        """停止服务器"""
        if (
            not self.is_running
            and self.multi_protocol_server is None
            and self.shared_asr_manager is None
            and not self._retired_shared_asr_managers
        ):
            logger.bind(tag=TAG).info("服务器未在运行")
            return

        logger.bind(tag=TAG).info("正在停止小智服务器...")
        errors = []
        protocols_stopped = self.multi_protocol_server is None
        if self.multi_protocol_server:
            try:
                await self.multi_protocol_server.stop()
            except Exception as e:
                errors.append(("多协议服务器", e))
                logger.bind(tag=TAG).error(f"停止多协议服务器失败: {e}")
            else:
                self.multi_protocol_server = None
                protocols_stopped = True

        if self.shared_asr_manager and protocols_stopped:
            logger.bind(tag=TAG).info("正在关闭共享 ASR 管理器...")
            try:
                await self.shared_asr_manager.shutdown()
            except Exception as e:
                errors.append(("共享 ASR", e))
                logger.bind(tag=TAG).error(f"关闭共享 ASR 管理器失败: {e}")
            else:
                self.shared_asr_manager = None
                self.config.pop('_shared_asr_manager', None)
        elif self.shared_asr_manager:
            logger.bind(tag=TAG).warning(
                "协议服务器仍持有连接，延后关闭共享 ASR 管理器"
            )

        if protocols_stopped and self._retired_shared_asr_managers:
            remaining_retired = []
            for manager in self._retired_shared_asr_managers:
                try:
                    await manager.shutdown()
                except Exception as e:
                    remaining_retired.append(manager)
                    errors.append(("旧共享 ASR", e))
                    logger.bind(tag=TAG).error(
                        f"关闭旧共享ASR管理器失败: {e}"
                    )
            self._retired_shared_asr_managers = remaining_retired

        self.is_running = False
        self.is_initialized = bool(
            self.multi_protocol_server
            or self.shared_asr_manager
            or self._retired_shared_asr_managers
        )
        if not self.is_initialized:
            self.shared_asr_manager = None
            self.config.pop('_shared_asr_manager', None)
            logger.bind(tag=TAG).info("小智服务器已停止")
        else:
            logger.bind(tag=TAG).warning(
                "服务器部分资源停止失败，已保留所有权供重试清理"
            )

        if errors:
            self._cleanup_pending = True
            details = ", ".join(f"{owner}: {error}" for owner, error in errors)
            raise RuntimeError(f"停止服务器时发生错误: {details}")
        self._cleanup_pending = False

    async def restart(self):
        """重启服务器"""
        logger.info("重启小智服务器...")
        await self.stop()
        await asyncio.sleep(1)  # 等待清理完成
        await self.start()

    async def update_config(
        self, new_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新服务器配置

        Args:
            new_config: 新的配置字典

        Returns:
            bool: 更新是否成功
        """
        old_config = self.config
        old_shared_manager = self.shared_asr_manager
        prepared_shared_manager = old_shared_manager
        owns_prepared_manager = False
        try:
            logger.info("更新服务器配置...")
            self.last_update_error = None

            if new_config is None:
                from config.config_loader import get_config_from_api_async

                new_config = await get_config_from_api_async(self.config)
                if new_config is None:
                    raise RuntimeError("获取新配置失败")

            # 使用新顶层对象，避免 MultiProtocolServer 的旧配置引用被原地改写，
            # 从而导致协议/端口变化无法被检测。
            merged_config = dict(self.config)
            merged_config.update(new_config)
            self.config = merged_config
            self._setup_protocol_config()

            from core.utils.config_validation import validate_config_components
            from core.utils.util import check_asr_update
            from core.providers.asr.shared_asr_manager import SharedASRManager

            ok, error_msg = await validate_config_components(self.config, logger)
            if not ok:
                raise RuntimeError(f"配置校验失败: {error_msg}")

            selected_asr = self.config.get("selected_module", {}).get("ASR")
            asr_config = self.config.get("ASR", {}).get(selected_asr, {})
            asr_type = asr_config.get("type", selected_asr) if selected_asr else None
            needs_new_asr = check_asr_update(old_config, self.config)

            if asr_type and SharedASRManager.is_local_model_type(asr_type):
                if not (
                    old_shared_manager
                    and not needs_new_asr
                    and old_shared_manager.is_ready()
                ):
                    prepared_shared_manager = SharedASRManager(self.config, asr_type)
                    await prepared_shared_manager.initialize()
                    owns_prepared_manager = True
                self.config["_shared_asr_manager"] = prepared_shared_manager
            else:
                prepared_shared_manager = None
                self.config.pop("_shared_asr_manager", None)

            # 已初始化时即更新实例集合；运行中会完成监听器切换。
            if self.multi_protocol_server:
                success = await self.multi_protocol_server.update_config(self.config)
                if success:
                    logger.info("服务器配置更新成功")
                else:
                    raise RuntimeError("多协议服务器配置更新失败")

            self.shared_asr_manager = prepared_shared_manager
            if (
                old_shared_manager
                and old_shared_manager is not prepared_shared_manager
            ):
                try:
                    await old_shared_manager.shutdown()
                except Exception as e:
                    # 新配置已经提交，保留旧资源所有权供 stop 重试。
                    self._retired_shared_asr_managers.append(
                        old_shared_manager
                    )
                    logger.bind(tag=TAG).error(f"关闭旧共享ASR管理器失败: {e}")

            logger.info("配置更新完成")
            return True

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            self.last_update_error = str(e)
            if owns_prepared_manager and prepared_shared_manager:
                try:
                    await prepared_shared_manager.shutdown()
                except Exception as cleanup_error:
                    self._retired_shared_asr_managers.append(
                        prepared_shared_manager
                    )
                    logger.bind(tag=TAG).error(
                        f"回滚新共享ASR管理器失败: {cleanup_error}"
                    )
            self.config = old_config
            self.shared_asr_manager = old_shared_manager
            if self.multi_protocol_server:
                self.is_running = self.multi_protocol_server.is_running
                if (
                    self.multi_protocol_server.server_tasks
                    and not self.multi_protocol_server.is_running
                ):
                    self._cleanup_pending = True
            return False

    def get_last_update_error(self) -> str:
        return self.last_update_error or ""

    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        base_status = {
            'is_initialized': self.is_initialized,
            'is_running': self.is_running,
            'enabled_protocols': self.config.get('enabled_protocols', [])
        }

        if self.multi_protocol_server:
            server_status = self.multi_protocol_server.get_server_status()
            base_status.update(server_status)

        # 添加 ASR 状态
        if self.shared_asr_manager:
            base_status['asr'] = {
                'mode': 'shared',
                'ready': self.shared_asr_manager.is_ready(),
                'queue_status': self.shared_asr_manager.get_queue_status()
            }
        else:
            base_status['asr'] = {'mode': 'lazy_load'}

        return base_status

    def get_active_connections_count(self) -> Dict[str, int]:
        """获取各协议的活跃连接数"""
        if self.multi_protocol_server:
            return self.multi_protocol_server.get_active_connections_count()
        return {}

    def get_supported_protocols(self) -> list:
        """获取支持的协议列表"""
        if self.multi_protocol_server:
            return self.multi_protocol_server.get_supported_protocols()
        return ['websocket']

    def is_protocol_enabled(self, protocol: str) -> bool:
        """检查协议是否启用"""
        enabled_protocols = self.config.get('enabled_protocols', [])
        return protocol in enabled_protocols

    async def broadcast_message(self, message: Dict[str, Any], protocol: Optional[str] = None):
        """
        向所有连接广播消息

        Args:
            message: 要广播的消息
            protocol: 指定协议，None表示向所有协议广播
        """
        if self.multi_protocol_server:
            await self.multi_protocol_server.broadcast_message(message, protocol)

    def get_websocket_info(self) -> Dict[str, Any]:
        """获取WebSocket连接信息"""
        if not self.is_protocol_enabled('websocket'):
            return {'enabled': False}

        server_config = self.config.get('server', {})
        return {
            'enabled': True,
            'host': server_config.get('ip', '0.0.0.0'),
            'port': server_config.get('port', 8000),
            'path': '/xiaozhi/v1/'
        }

    def get_connection_info(self) -> Dict[str, Any]:
        """获取所有协议的连接信息"""
        return {
            'websocket': self.get_websocket_info(),
            'active_connections': self.get_active_connections_count()
        }
