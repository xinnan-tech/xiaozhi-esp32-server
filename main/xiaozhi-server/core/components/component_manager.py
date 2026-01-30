import asyncio
import weakref
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Generic
from enum import Enum
from config.logger import setup_logging

T = TypeVar('T')

logger = setup_logging()


class ComponentType(Enum):
    """组件类型枚举"""
    TTS = "tts"
    ASR = "asr" 
    VAD = "vad"
    LLM = "llm"
    MEMORY = "memory"
    INTENT = "intent"


class ComponentState(Enum):
    """组件状态枚举"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    CLEANING = "cleaning"
    CLEANED = "cleaned"


class Component(ABC):
    """组件基类：定义统一的组件接口和生命周期管理"""
    
    def __init__(self, component_type: ComponentType, config: Dict[str, Any]):
        self.component_type = component_type
        self.config = config
        self.state = ComponentState.UNINITIALIZED
        self._initialization_lock = asyncio.Lock()
        self._cleanup_lock = asyncio.Lock()
        self._dependencies: Dict[str, 'Component'] = {}
        self._dependents: weakref.WeakSet['Component'] = weakref.WeakSet()
        self._resources: list = []  # 存储需要清理的资源
        
    @abstractmethod
    async def _do_initialize(self, context: Any) -> None:
        """子类实现具体的初始化逻辑"""
        pass
    
    @abstractmethod
    async def _do_cleanup(self) -> None:
        """子类实现具体的清理逻辑"""
        pass
    
    async def initialize(self, context: Any) -> None:
        """初始化组件（带锁保护）"""
        async with self._initialization_lock:
            if self.state != ComponentState.UNINITIALIZED:
                return
                
            try:
                self.state = ComponentState.INITIALIZING
                logger.info(f"正在初始化组件: {self.component_type.value}")
                
                # 初始化依赖组件
                await self._initialize_dependencies(context)
                
                # 执行具体初始化
                await self._do_initialize(context)
                
                self.state = ComponentState.READY
                logger.info(f"组件初始化完成: {self.component_type.value}")
                
            except Exception as e:
                self.state = ComponentState.ERROR
                logger.error(f"组件初始化失败: {self.component_type.value}, 错误: {e}")
                raise
    
    async def cleanup(self) -> None:
        """清理组件（带锁保护）"""
        async with self._cleanup_lock:
            if self.state in [ComponentState.CLEANING, ComponentState.CLEANED]:
                return
                
            try:
                self.state = ComponentState.CLEANING
                logger.info(f"正在清理组件: {self.component_type.value}")
                
                # 清理依赖此组件的其他组件
                await self._cleanup_dependents()
                
                # 执行具体清理
                await self._do_cleanup()
                
                # 清理资源
                await self._cleanup_resources()
                
                self.state = ComponentState.CLEANED
                logger.info(f"组件清理完成: {self.component_type.value}")
                
            except Exception as e:
                logger.error(f"组件清理失败: {self.component_type.value}, 错误: {e}")
                # 即使清理失败，也标记为已清理，避免重复清理
                self.state = ComponentState.CLEANED
    
    def add_dependency(self, name: str, component: 'Component') -> None:
        """添加依赖组件"""
        self._dependencies[name] = component
        component._dependents.add(self)
    
    def add_resource(self, resource: Any) -> None:
        """添加需要清理的资源"""
        self._resources.append(resource)
    
    async def _initialize_dependencies(self, context: Any) -> None:
        """初始化依赖组件"""
        for name, dep in self._dependencies.items():
            if dep.state == ComponentState.UNINITIALIZED:
                await dep.initialize(context)
    
    async def _cleanup_dependents(self) -> None:
        """清理依赖此组件的其他组件"""
        for dependent in list(self._dependents):
            await dependent.cleanup()
    
    async def _cleanup_resources(self) -> None:
        """清理所有注册的资源"""
        for resource in self._resources:
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
                elif hasattr(resource, 'cleanup'):
                    if asyncio.iscoroutinefunction(resource.cleanup):
                        await resource.cleanup()
                    else:
                        resource.cleanup()
            except Exception as e:
                logger.warning(f"清理资源时出错: {e}")
        self._resources.clear()


class ComponentFactory(ABC):
    """组件工厂基类"""
    
    @abstractmethod
    def create(self, config: Dict[str, Any]) -> Component:
        """创建组件实例"""
        pass
    
    @abstractmethod
    def get_component_type(self) -> ComponentType:
        """获取组件类型"""
        pass


class ComponentManager:
    """
    组件管理器：统一管理连接期内的组件实例生命周期。
    支持分类管理、依赖注入、按需懒加载与统一清理。
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._components: Dict[str, Component] = {}
        self._factories: Dict[ComponentType, ComponentFactory] = {}
        self._initialization_order: list[ComponentType] = []
        
    def register_factory(self, factory: ComponentFactory) -> None:
        """注册组件工厂"""
        component_type = factory.get_component_type()
        self._factories[component_type] = factory
        logger.debug(f"注册组件工厂: {component_type.value}")
    
    def set_initialization_order(self, order: list[ComponentType]) -> None:
        """设置组件初始化顺序"""
        self._initialization_order = order
    
    async def get_component(self, component_type: ComponentType, context: Any) -> Optional[Component]:
        """获取组件实例（按需创建）"""
        key = component_type.value
        
        if key not in self._components:
            factory = self._factories.get(component_type)
            if factory is None:
                logger.warning(f"未找到组件工厂: {component_type.value}")
                return None
                
            try:
                instance = factory.create(self._config)
                await instance.initialize(context)
                self._components[key] = instance
                logger.info(f"组件创建并初始化完成: {component_type.value}")
            except Exception as e:
                logger.error(f"组件创建失败: {component_type.value}, 错误: {e}")
                return None
                
        return self._components.get(key)
    
    def get(self, component_name: str) -> Optional[Component]:
        """获取已初始化的组件实例（兼容接口）"""
        return self._components.get(component_name)
    
    async def initialize_all(self, context: Any) -> None:
        """按顺序初始化所有组件"""
        for component_type in self._initialization_order:
            await self.get_component(component_type, context)
    
    async def cleanup_all(self) -> None:
        """清理所有组件（逆序清理）"""
        # 按逆序清理，确保依赖关系正确
        for component_type in reversed(self._initialization_order):
            key = component_type.value
            if key in self._components:
                component = self._components[key]
                await component.cleanup()
                del self._components[key]
        
        # 清理可能遗漏的组件
        remaining_components = list(self._components.values())
        for component in remaining_components:
            await component.cleanup()
        
        self._components.clear()
        logger.info("所有组件已清理完成")
    
    def get_component_status(self) -> Dict[str, str]:
        """获取所有组件状态"""
        return {
            name: component.state.value 
            for name, component in self._components.items()
        }