from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import intent, llm
from config.logger import setup_logging

logger = setup_logging()


class IntentAdapter(Component):
    """Intent组件适配器：将现有Intent组件包装为新的组件接口"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.INTENT, config)
        self._intent_instance = None
        self._owned_llm_instance = None

    async def _do_initialize(self, context: Any) -> None:
        """初始化Intent组件"""
        try:
            # 获取Intent配置
            selected_module = self.config.get("selected_module", {}).get("Intent")
            if not selected_module:
                raise ValueError("未配置Intent模块")

            # 获取Intent类型
            intent_type = (
                selected_module
                if "type" not in self.config["Intent"][selected_module]
                else self.config["Intent"][selected_module]["type"]
            )

            # 创建Intent实例
            self._intent_instance = intent.create_instance(
                intent_type,
                self.config["Intent"][selected_module],
            )

            # intent_llm 可配置独立模型；未配置时回退主 LLM。
            if intent_type == "intent_llm":
                llm_component = None
                if getattr(context, "component_manager", None):
                    llm_component = await context.component_manager.get_component(ComponentType.LLM, context)
                main_llm = getattr(llm_component, "llm_instance", None)
                intent_config = self.config["Intent"][selected_module]
                dedicated_llm_name = intent_config.get("llm")
                selected_llm = main_llm
                if (
                    dedicated_llm_name
                    and dedicated_llm_name in self.config.get("LLM", {})
                ):
                    dedicated_config = self.config["LLM"][dedicated_llm_name]
                    dedicated_type = dedicated_config.get("type", dedicated_llm_name)
                    self._owned_llm_instance = llm.create_instance(
                        dedicated_type, dedicated_config
                    )
                    selected_llm = self._owned_llm_instance
                    logger.info(f"为意图识别创建专用LLM: {dedicated_llm_name}")
                if selected_llm and hasattr(self._intent_instance, "set_llm"):
                    self._intent_instance.set_llm(selected_llm)

            logger.info(f"Intent组件初始化完成: {intent_type}")

        except Exception as e:
            logger.error(f"Intent组件初始化失败: {e}")
            raise

    async def _do_cleanup(self) -> None:
        """清理Intent组件"""
        if self._intent_instance:
            instance = self._intent_instance
            await self._close_resource(instance)
            self._intent_instance = None
            logger.info("Intent组件清理完成")
        if self._owned_llm_instance:
            instance = self._owned_llm_instance
            await self._close_resource(instance)
            self._owned_llm_instance = None

    @property
    def intent_instance(self):
        """获取Intent实例"""
        return self._intent_instance


class IntentFactory(ComponentFactory):
    """Intent组件工厂"""

    def create(self, config: Dict[str, Any]) -> Component:
        return IntentAdapter(config)

    def get_component_type(self) -> ComponentType:
        return ComponentType.INTENT
