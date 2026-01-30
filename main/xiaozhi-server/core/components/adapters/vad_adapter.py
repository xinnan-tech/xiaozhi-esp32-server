from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import vad
from config.logger import setup_logging

logger = setup_logging()


class VADAdapter(Component):
    """VAD组件适配器：将现有VAD组件包装为新的组件接口"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.VAD, config)
        self._vad_instance = None
    
    async def _do_initialize(self, context: Any) -> None:
        """初始化VAD组件"""
        try:
            # 获取VAD配置
            selected_module = self.config.get("selected_module", {}).get("VAD")
            if not selected_module:
                raise ValueError("未配置VAD模块")
            
            # 获取VAD类型
            vad_type = (
                selected_module
                if "type" not in self.config["VAD"][selected_module]
                else self.config["VAD"][selected_module]["type"]
            )
            
            # 创建VAD实例
            self._vad_instance = vad.create_instance(
                vad_type,
                self.config["VAD"][selected_module],
            )
            
            # 注册资源以便清理
            self.add_resource(self._vad_instance)
            
            logger.info(f"VAD组件初始化完成: {vad_type}")
            
        except Exception as e:
            logger.error(f"VAD组件初始化失败: {e}")
            raise
    
    async def _do_cleanup(self) -> None:
        """清理VAD组件"""
        if self._vad_instance:
            try:
                # 关闭VAD实例
                if hasattr(self._vad_instance, 'close'):
                    await self._vad_instance.close()
                elif hasattr(self._vad_instance, 'cleanup'):
                    await self._vad_instance.cleanup()
                
                logger.info("VAD组件清理完成")
                
            except Exception as e:
                logger.error(f"VAD组件清理失败: {e}")
            finally:
                self._vad_instance = None
    
    @property
    def vad_instance(self):
        """获取VAD实例"""
        return self._vad_instance


class VADFactory(ComponentFactory):
    """VAD组件工厂"""
    
    def create(self, config: Dict[str, Any]) -> Component:
        return VADAdapter(config)
    
    def get_component_type(self) -> ComponentType:
        return ComponentType.VAD


