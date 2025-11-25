"""
特性开关

提供并行优化各功能的开关控制。
支持:
- 全局配置
- 运行时动态调整
- 降级联动
"""

import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class FeatureFlag(Enum):
    """特性标识"""
    PARALLEL_EXECUTION = "parallel_execution"       # 并行执行
    TRANSITION_RESPONSE = "transition_response"     # 过渡响应
    SMART_INTERRUPTION = "smart_interruption"       # 智能打断
    SECURITY_GUARDRAILS = "security_guardrails"     # 安全防护
    PERFORMANCE_TRACING = "performance_tracing"     # 性能追踪
    LLM_COMPILER = "llm_compiler"                   # LLMCompiler 架构
    PRIORITY_QUEUE = "priority_queue"               # 优先级队列
    STATE_MACHINE = "state_machine"                 # 状态机


@dataclass
class FeatureConfig:
    """特性配置"""
    enabled: bool = True
    description: str = ""
    requires: list = field(default_factory=list)    # 依赖的其他特性
    conflicts: list = field(default_factory=list)   # 冲突的特性


class FeatureFlagManager:
    """
    特性开关管理器

    特性:
    - 线程安全
    - 依赖检查
    - 冲突检测
    - 变更通知
    """

    # 默认特性配置
    DEFAULT_CONFIGS: Dict[FeatureFlag, FeatureConfig] = {
        FeatureFlag.PARALLEL_EXECUTION: FeatureConfig(
            enabled=True,
            description="启用工具并行执行",
            requires=[FeatureFlag.LLM_COMPILER],
        ),
        FeatureFlag.TRANSITION_RESPONSE: FeatureConfig(
            enabled=True,
            description="启用过渡响应",
        ),
        FeatureFlag.SMART_INTERRUPTION: FeatureConfig(
            enabled=True,
            description="启用智能打断（<400ms）",
            requires=[FeatureFlag.STATE_MACHINE],
        ),
        FeatureFlag.SECURITY_GUARDRAILS: FeatureConfig(
            enabled=True,
            description="启用安全防护层",
        ),
        FeatureFlag.PERFORMANCE_TRACING: FeatureConfig(
            enabled=True,
            description="启用性能追踪",
        ),
        FeatureFlag.LLM_COMPILER: FeatureConfig(
            enabled=True,
            description="启用 LLMCompiler 架构",
            requires=[FeatureFlag.STATE_MACHINE],
        ),
        FeatureFlag.PRIORITY_QUEUE: FeatureConfig(
            enabled=True,
            description="启用 TTS 优先级队列",
        ),
        FeatureFlag.STATE_MACHINE: FeatureConfig(
            enabled=True,
            description="启用会话状态机",
        ),
    }

    def __init__(self):
        self._lock = threading.RLock()
        self._flags: Dict[FeatureFlag, bool] = {}
        self._configs: Dict[FeatureFlag, FeatureConfig] = {}
        self._listeners: Dict[FeatureFlag, list] = {}

        # 初始化默认配置
        for flag, config in self.DEFAULT_CONFIGS.items():
            self._flags[flag] = config.enabled
            self._configs[flag] = config

    def is_enabled(self, flag: FeatureFlag) -> bool:
        """检查特性是否启用"""
        with self._lock:
            return self._flags.get(flag, False)

    def enable(self, flag: FeatureFlag, force: bool = False) -> bool:
        """
        启用特性

        Args:
            flag: 特性标识
            force: 强制启用（忽略依赖检查）

        Returns:
            bool: 是否成功
        """
        with self._lock:
            config = self._configs.get(flag)
            if not config:
                logger.bind(tag=TAG).error(f"未知特性: {flag.value}")
                return False

            # 检查依赖
            if not force:
                for dep in config.requires:
                    if isinstance(dep, FeatureFlag) and not self._flags.get(dep, False):
                        logger.bind(tag=TAG).warning(
                            f"无法启用 {flag.value}: 依赖 {dep.value} 未启用"
                        )
                        return False

            # 检查冲突
            for conflict in config.conflicts:
                if isinstance(conflict, FeatureFlag) and self._flags.get(conflict, False):
                    logger.bind(tag=TAG).warning(
                        f"无法启用 {flag.value}: 与 {conflict.value} 冲突"
                    )
                    return False

            old_value = self._flags.get(flag, False)
            self._flags[flag] = True

            if not old_value:
                self._notify_listeners(flag, True)
                logger.bind(tag=TAG).info(f"特性已启用: {flag.value}")

            return True

    def disable(self, flag: FeatureFlag, cascade: bool = True) -> bool:
        """
        禁用特性

        Args:
            flag: 特性标识
            cascade: 级联禁用依赖此特性的其他特性

        Returns:
            bool: 是否成功
        """
        with self._lock:
            old_value = self._flags.get(flag, False)
            self._flags[flag] = False

            if old_value:
                self._notify_listeners(flag, False)
                logger.bind(tag=TAG).info(f"特性已禁用: {flag.value}")

            # 级联禁用
            if cascade:
                for other_flag, config in self._configs.items():
                    if flag in config.requires and self._flags.get(other_flag, False):
                        self.disable(other_flag, cascade=True)

            return True

    def toggle(self, flag: FeatureFlag) -> bool:
        """切换特性状态"""
        with self._lock:
            if self._flags.get(flag, False):
                return self.disable(flag)
            else:
                return self.enable(flag)

    def set_enabled(self, flag: FeatureFlag, enabled: bool) -> bool:
        """设置特性状态"""
        if enabled:
            return self.enable(flag)
        else:
            return self.disable(flag)

    def add_listener(
        self,
        flag: FeatureFlag,
        callback: Callable[[bool], None],
    ) -> None:
        """添加变更监听器"""
        with self._lock:
            if flag not in self._listeners:
                self._listeners[flag] = []
            self._listeners[flag].append(callback)

    def remove_listener(
        self,
        flag: FeatureFlag,
        callback: Callable[[bool], None],
    ) -> None:
        """移除变更监听器"""
        with self._lock:
            if flag in self._listeners:
                try:
                    self._listeners[flag].remove(callback)
                except ValueError:
                    pass

    def _notify_listeners(self, flag: FeatureFlag, enabled: bool) -> None:
        """通知监听器"""
        listeners = self._listeners.get(flag, [])
        for callback in listeners:
            try:
                callback(enabled)
            except Exception as e:
                logger.bind(tag=TAG).error(f"监听器回调失败: {e}")

    def get_all_flags(self) -> Dict[str, bool]:
        """获取所有特性状态"""
        with self._lock:
            return {flag.value: enabled for flag, enabled in self._flags.items()}

    def get_enabled_flags(self) -> list:
        """获取已启用的特性列表"""
        with self._lock:
            return [
                flag.value for flag, enabled in self._flags.items()
                if enabled
            ]

    def get_disabled_flags(self) -> list:
        """获取已禁用的特性列表"""
        with self._lock:
            return [
                flag.value for flag, enabled in self._flags.items()
                if not enabled
            ]

    def load_from_config(self, config: Dict[str, bool]) -> None:
        """从配置加载特性状态"""
        with self._lock:
            for flag_name, enabled in config.items():
                try:
                    flag = FeatureFlag(flag_name)
                    self.set_enabled(flag, enabled)
                except ValueError:
                    logger.bind(tag=TAG).warning(f"未知特性配置: {flag_name}")

    def export_config(self) -> Dict[str, bool]:
        """导出特性配置"""
        return self.get_all_flags()

    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        with self._lock:
            for flag, config in self.DEFAULT_CONFIGS.items():
                self._flags[flag] = config.enabled
            logger.bind(tag=TAG).info("特性开关已重置为默认值")

    def enable_all(self) -> None:
        """启用所有特性"""
        with self._lock:
            for flag in FeatureFlag:
                self.enable(flag, force=True)
            logger.bind(tag=TAG).info("所有特性已启用")

    def disable_all(self) -> None:
        """禁用所有特性"""
        with self._lock:
            for flag in FeatureFlag:
                self._flags[flag] = False
            logger.bind(tag=TAG).info("所有特性已禁用")

    def get_feature_info(self, flag: FeatureFlag) -> Dict[str, Any]:
        """获取特性详细信息"""
        with self._lock:
            config = self._configs.get(flag)
            if not config:
                return {}

            return {
                "name": flag.value,
                "enabled": self._flags.get(flag, False),
                "description": config.description,
                "requires": [f.value for f in config.requires if isinstance(f, FeatureFlag)],
                "conflicts": [f.value for f in config.conflicts if isinstance(f, FeatureFlag)],
            }

    def get_all_feature_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有特性详细信息"""
        with self._lock:
            return {
                flag.value: self.get_feature_info(flag)
                for flag in FeatureFlag
            }


# 全局特性开关管理器实例
_global_manager: Optional[FeatureFlagManager] = None
_manager_lock = threading.Lock()


def get_feature_manager() -> FeatureFlagManager:
    """获取全局特性开关管理器"""
    global _global_manager
    with _manager_lock:
        if _global_manager is None:
            _global_manager = FeatureFlagManager()
        return _global_manager


def is_enabled(flag: FeatureFlag) -> bool:
    """检查特性是否启用（全局函数）"""
    return get_feature_manager().is_enabled(flag)


def enable(flag: FeatureFlag) -> bool:
    """启用特性（全局函数）"""
    return get_feature_manager().enable(flag)


def disable(flag: FeatureFlag) -> bool:
    """禁用特性（全局函数）"""
    return get_feature_manager().disable(flag)


