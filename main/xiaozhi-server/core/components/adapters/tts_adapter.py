from typing import Any, Dict
from core.components.component_manager import Component, ComponentType, ComponentFactory
from core.utils import tts
from config.logger import setup_logging

logger = setup_logging()


class TTSAdapter(Component):
    """TTS组件适配器：将现有TTS组件包装为新的组件接口"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ComponentType.TTS, config)
        self._tts_instance = None
        self._delete_audio = config.get("delete_audio", True)
    
    async def _do_initialize(self, context: Any) -> None:
        """初始化TTS组件"""
        try:
            # 获取TTS配置
            selected_module = self.config.get("selected_module", {}).get("TTS")
            if not selected_module:
                raise ValueError("未配置TTS模块")
            
            # 获取TTS类型
            tts_type = (
                selected_module
                if "type" not in self.config["TTS"][selected_module]
                else self.config["TTS"][selected_module]["type"]
            )
            
            # 创建TTS实例
            self._tts_instance = tts.create_instance(
                tts_type,
                self.config["TTS"][selected_module],
                str(self._delete_audio).lower() in ("true", "1", "yes"),
            )
            
            # 注册资源以便清理
            self.add_resource(self._tts_instance)
            
            # 打开音频通道
            if hasattr(self._tts_instance, 'open_audio_channels'):
                await self._tts_instance.open_audio_channels(context)
            
            # 设置兼容属性（用于向后兼容）
            if hasattr(context, 'tts'):
                context.tts = self._tts_instance
            
            logger.info(f"TTS组件初始化完成: {tts_type}")
            
        except Exception as e:
            logger.error(f"TTS组件初始化失败: {e}")
            raise
    
    async def _do_cleanup(self) -> None:
        """清理TTS组件"""
        if self._tts_instance:
            try:
                # 关闭TTS实例
                if hasattr(self._tts_instance, 'close'):
                    await self._tts_instance.close()
                
                # 清理音频文件
                if hasattr(self._tts_instance, 'cleanup_audio_files'):
                    self._tts_instance.cleanup_audio_files()
                
                logger.info("TTS组件清理完成")
                
            except Exception as e:
                logger.error(f"TTS组件清理失败: {e}")
            finally:
                self._tts_instance = None
    
    @property
    def tts_instance(self):
        """获取TTS实例"""
        return self._tts_instance


class TTSFactory(ComponentFactory):
    """TTS组件工厂"""
    
    def create(self, config: Dict[str, Any]) -> Component:
        return TTSAdapter(config)
    
    def get_component_type(self) -> ComponentType:
        return ComponentType.TTS


