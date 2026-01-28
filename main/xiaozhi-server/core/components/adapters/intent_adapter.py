from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import intent
from config.logger import setup_logging

logger = setup_logging()


class IntentAdapter(Component):
    """Intent组件适配器：将现有Intent组件包装为新的组件接口"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.INTENT, config)
        self._intent_instance = None
    
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
            
            # 注册资源以便清理
            self.add_resource(self._intent_instance)
            
            # 设置LLM（如果需要）
            if intent_type in ["intent_llm", "function_call"]:
                llm_component = context.components.get('llm')
                if llm_component and hasattr(llm_component, 'llm_instance'):
                    if hasattr(self._intent_instance, 'set_llm'):
                        self._intent_instance.set_llm(llm_component.llm_instance)
            
            logger.info(f"Intent组件初始化完成: {intent_type}")
            
        except Exception as e:
            logger.error(f"Intent组件初始化失败: {e}")
            raise
    
    async def _do_cleanup(self) -> None:
        """清理Intent组件"""
        if self._intent_instance:
            try:
                # 关闭Intent实例
                if hasattr(self._intent_instance, 'close'):
                    await self._intent_instance.close()
                elif hasattr(self._intent_instance, 'cleanup'):
                    await self._intent_instance.cleanup()
                
                logger.info("Intent组件清理完成")
                
            except Exception as e:
                logger.error(f"Intent组件清理失败: {e}")
            finally:
                self._intent_instance = None
    
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


