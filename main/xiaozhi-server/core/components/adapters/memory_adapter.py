from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import llm, memory
from config.logger import setup_logging

logger = setup_logging()


class MemoryAdapter(Component):
    """Memory组件适配器：将现有Memory组件包装为新的组件接口"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.MEMORY, config)
        self._memory_instance = None
        self._owned_llm_instance = None

    async def _do_initialize(self, context: Any) -> None:
        """初始化Memory组件"""
        try:
            # 获取Memory配置
            selected_module = self.config.get("selected_module", {}).get("Memory")
            if not selected_module:
                raise ValueError("未配置Memory模块")

            # 获取Memory类型
            memory_type = (
                selected_module
                if "type" not in self.config["Memory"][selected_module]
                else self.config["Memory"][selected_module]["type"]
            )

            # 创建Memory实例
            self._memory_instance = memory.create_instance(
                memory_type,
                self.config["Memory"][selected_module],
                self.config.get("summaryMemory", None),
            )

            # 初始化记忆模块
            main_llm = None
            if hasattr(self._memory_instance, 'init_memory'):
                # 需要LLM实例来初始化记忆
                llm_component = None
                if getattr(context, "component_manager", None):
                    llm_component = await context.component_manager.get_component(ComponentType.LLM, context)
                if llm_component and hasattr(llm_component, 'llm_instance'):
                    main_llm = llm_component.llm_instance
                    self._memory_instance.init_memory(
                        role_id=context.device_id,
                        llm=main_llm,
                        summary_memory=self.config.get("summaryMemory", None),
                        save_to_file=not self.config.get("read_config_from_api", False),
                    )

            memory_config = self.config["Memory"][selected_module]
            dedicated_llm_name = memory_config.get("llm")
            if (
                memory_type == "mem_local_short"
                and dedicated_llm_name
                and dedicated_llm_name in self.config.get("LLM", {})
            ):
                dedicated_config = self.config["LLM"][dedicated_llm_name]
                dedicated_type = dedicated_config.get("type", dedicated_llm_name)
                self._owned_llm_instance = llm.create_instance(
                    dedicated_type, dedicated_config
                )
                self._memory_instance.set_llm(self._owned_llm_instance)
                logger.info(f"为记忆总结创建专用LLM: {dedicated_llm_name}")
            elif main_llm and hasattr(self._memory_instance, "set_llm"):
                self._memory_instance.set_llm(main_llm)

            logger.info(f"Memory组件初始化完成: {memory_type}")

        except Exception as e:
            logger.error(f"Memory组件初始化失败: {e}")
            raise

    async def _do_cleanup(self) -> None:
        """清理Memory组件"""
        if self._memory_instance:
            instance = self._memory_instance
            await self._close_resource(instance)
            self._memory_instance = None
            logger.info("Memory组件清理完成")
        if self._owned_llm_instance:
            instance = self._owned_llm_instance
            await self._close_resource(instance)
            self._owned_llm_instance = None

    @property
    def memory_instance(self):
        """获取Memory实例"""
        return self._memory_instance


class MemoryFactory(ComponentFactory):
    """Memory组件工厂"""

    def create(self, config: Dict[str, Any]) -> Component:
        return MemoryAdapter(config)

    def get_component_type(self) -> ComponentType:
        return ComponentType.MEMORY
