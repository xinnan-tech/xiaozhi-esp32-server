from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import llm
from config.logger import setup_logging

logger = setup_logging()


class LLMAdapter(Component):
    """LLM组件适配器：将现有LLM组件包装为新的组件接口"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.LLM, config)
        self._llm_instance = None
    
    async def _do_initialize(self, context: Any) -> None:
        """初始化LLM组件"""
        try:
            # 获取LLM配置
            selected_module = self.config.get("selected_module", {}).get("LLM")
            if not selected_module:
                raise ValueError("未配置LLM模块")
            
            # 获取LLM类型
            llm_type = (
                selected_module
                if "type" not in self.config["LLM"][selected_module]
                else self.config["LLM"][selected_module]["type"]
            )
            
            # 创建LLM实例
            self._llm_instance = llm.create_instance(
                llm_type,
                self.config["LLM"][selected_module],
            )
            
            # 注册资源以便清理
            self.add_resource(self._llm_instance)
            
            logger.info(f"LLM组件初始化完成: {llm_type}")
            
        except Exception as e:
            logger.error(f"LLM组件初始化失败: {e}")
            raise
    
    async def _do_cleanup(self) -> None:
        """清理LLM组件"""
        if self._llm_instance:
            try:
                # 关闭LLM实例
                if hasattr(self._llm_instance, 'close'):
                    await self._llm_instance.close()
                elif hasattr(self._llm_instance, 'cleanup'):
                    await self._llm_instance.cleanup()
                
                logger.info("LLM组件清理完成")
                
            except Exception as e:
                logger.error(f"LLM组件清理失败: {e}")
            finally:
                self._llm_instance = None
    
    @property
    def llm_instance(self):
        """获取LLM实例"""
        return self._llm_instance


class LLMFactory(ComponentFactory):
    """LLM组件工厂"""
    
    def create(self, config: Dict[str, Any]) -> Component:
        return LLMAdapter(config)
    
    def get_component_type(self) -> ComponentType:
        return ComponentType.LLM


