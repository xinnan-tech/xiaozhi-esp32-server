from typing import Dict, Any
from core.components.component_manager import ComponentManager, ComponentType
from core.components.adapters.tts_adapter import TTSFactory
from core.components.adapters.asr_adapter import ASRFactory
from core.components.adapters.vad_adapter import VADFactory
from core.components.adapters.llm_adapter import LLMFactory
from core.components.adapters.memory_adapter import MemoryFactory
from core.components.adapters.intent_adapter import IntentFactory
from config.logger import setup_logging

logger = setup_logging()


class ComponentRegistry:
    """组件注册器：统一管理所有组件工厂的注册"""
    
    _factories_registered = False
    
    @classmethod
    def create_component_manager(cls, config: Dict[str, Any]) -> ComponentManager:
        """创建并配置组件管理器"""
        manager = ComponentManager(config)
        
        # 只在第一次时记录注册日志
        if not cls._factories_registered:
            logger.info("注册组件工厂")
            cls._factories_registered = True
        
        # 注册所有组件工厂（每个manager都需要注册，但不重复记录日志）
        manager.register_factory(TTSFactory())
        manager.register_factory(ASRFactory())
        manager.register_factory(VADFactory())
        manager.register_factory(LLMFactory())
        manager.register_factory(MemoryFactory())
        manager.register_factory(IntentFactory())
        
        # 设置组件初始化顺序（考虑依赖关系）
        # VAD -> ASR -> LLM -> Memory/Intent -> TTS
        initialization_order = [
            ComponentType.VAD,
            ComponentType.ASR,
            ComponentType.LLM,
            ComponentType.MEMORY,
            ComponentType.INTENT,
            ComponentType.TTS,
        ]
        manager.set_initialization_order(initialization_order)
        
        if not cls._factories_registered:
            logger.info("组件管理器创建完成，已注册所有组件工厂")
        
        return manager
    
    @staticmethod
    def get_required_components(config: Dict[str, Any]) -> list[ComponentType]:
        """根据配置获取需要的组件类型"""
        required = []
        selected_modules = config.get("selected_module", {})
        
        if selected_modules.get("VAD"):
            required.append(ComponentType.VAD)
        if selected_modules.get("ASR"):
            required.append(ComponentType.ASR)
        if selected_modules.get("LLM"):
            required.append(ComponentType.LLM)
        if selected_modules.get("TTS"):
            required.append(ComponentType.TTS)
        if selected_modules.get("Memory"):
            required.append(ComponentType.MEMORY)
        if selected_modules.get("Intent"):
            required.append(ComponentType.INTENT)
        
        return required


