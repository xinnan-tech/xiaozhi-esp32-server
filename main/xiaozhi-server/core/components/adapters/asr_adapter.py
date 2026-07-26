from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import asr
from core.utils.modules_initialize import initialize_asr
from config.logger import setup_logging

logger = setup_logging()
TAG = __name__


class ASRAdapter(Component):
    """
    ASR组件适配器：将现有ASR组件包装为新的组件接口

    支持两种模式：
    1. 共享实例模式：使用 SharedASRManager 的全局共享实例
    2. 独立实例模式：每个连接创建独立的 ASR 实例（原有逻辑）
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.ASR, config)
        self._asr_instance = None
        self._delete_audio = config.get("delete_audio", True)
        self._using_shared = False  # 是否使用共享实例
        self._shared_owner = None

    async def _do_initialize(self, context: Any) -> None:
        """初始化ASR组件"""
        try:
            # 获取ASR配置
            selected_module = self.config.get("selected_module", {}).get("ASR")
            if not selected_module:
                raise ValueError("未配置ASR模块")

            # 检查是否有全局共享 ASR 管理器
            shared_manager = getattr(context, 'shared_asr_manager', None)

            acquired_manager = None
            if shared_manager and hasattr(shared_manager, "acquire_for_config"):
                acquired_manager = await shared_manager.acquire_for_config(
                    self.config
                )
            elif (
                shared_manager
                and shared_manager.is_ready()
                and shared_manager.matches_config(self.config)
            ):
                acquired_manager = shared_manager

            if acquired_manager is not None:
                # 使用共享实例模式
                logger.bind(tag=TAG).info(f"使用共享 ASR 实例: {selected_module}")
                from core.providers.asr.shared_asr_proxy import SharedASRProxy
                self._asr_instance = SharedASRProxy(acquired_manager)
                self._using_shared = True
                self._shared_owner = shared_manager
            else:
                # 使用独立实例模式（原有逻辑）
                if shared_manager and shared_manager.is_ready():
                    logger.bind(tag=TAG).info(
                        f"连接ASR配置与共享实例不匹配，使用独立实例: {selected_module}"
                    )
                logger.bind(tag=TAG).info(f"使用独立 ASR 实例: {selected_module}")
                self._asr_instance = initialize_asr(self.config)
                self._using_shared = False

            # Legacy providers inspect conn.asr while handling stream state.
            context.asr = self._asr_instance

            # 打开音频通道（如果需要）
            if hasattr(self._asr_instance, 'open_audio_channels'):
                await self._asr_instance.open_audio_channels(context)

            logger.bind(tag=TAG).info(
                f"ASR组件初始化完成: {selected_module}, "
                f"共享模式: {self._using_shared}"
            )

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR组件初始化失败: {e}")
            raise

    async def _do_cleanup(self) -> None:
        """清理ASR组件"""
        if self._asr_instance:
            instance = self._asr_instance
            if self._using_shared:
                await self._close_resource(instance)
                if self._shared_owner and hasattr(
                    self._shared_owner, "release_for_config"
                ):
                    await self._shared_owner.release_for_config(instance.manager)
                logger.bind(tag=TAG).debug("共享 ASR 代理已释放")
            else:
                await self._close_resource(instance)
                if hasattr(instance, 'cleanup_audio_files'):
                    instance.cleanup_audio_files()
                logger.bind(tag=TAG).info("ASR组件清理完成")
            self._asr_instance = None
            self._using_shared = False
            self._shared_owner = None

    @property
    def asr_instance(self):
        """获取ASR实例"""
        return self._asr_instance


class ASRFactory(ComponentFactory):
    """ASR组件工厂"""

    def create(self, config: Dict[str, Any]) -> Component:
        return ASRAdapter(config)

    def get_component_type(self) -> ComponentType:
        return ComponentType.ASR
