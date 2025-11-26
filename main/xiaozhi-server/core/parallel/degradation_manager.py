"""
降级管理器

5层降级策略，保证系统可用性:
1. 全功能模式
2. 禁用并行优化
3. 禁用过渡响应
4. 禁用智能打断
5. 极简模式（最小功能集）

根据系统状态和错误率自动降级/恢复。
"""

import time
import threading
from enum import IntEnum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class DegradationLevel(IntEnum):
    """降级级别（数值越大功能越少）"""
    FULL = 0           # 全功能
    NO_PARALLEL = 1    # 禁用并行
    NO_TRANSITION = 2  # 禁用过渡响应
    NO_INTERRUPT = 3   # 禁用智能打断
    MINIMAL = 4        # 极简模式


@dataclass
class DegradationState:
    """降级状态"""
    level: DegradationLevel
    reason: str
    triggered_at: float
    auto_recover_at: Optional[float] = None


@dataclass
class HealthMetrics:
    """健康指标"""
    error_rate: float = 0.0           # 错误率
    avg_latency_ms: float = 0.0       # 平均延迟
    p99_latency_ms: float = 0.0       # P99 延迟
    timeout_rate: float = 0.0         # 超时率
    memory_usage_pct: float = 0.0     # 内存使用率
    cpu_usage_pct: float = 0.0        # CPU 使用率


@dataclass
class DegradationConfig:
    """降级配置"""
    # 触发阈值
    error_rate_threshold: float = 0.1      # 错误率阈值
    latency_threshold_ms: float = 5000     # 延迟阈值
    timeout_rate_threshold: float = 0.05   # 超时率阈值
    memory_threshold_pct: float = 90       # 内存阈值

    # 恢复配置
    auto_recover: bool = True              # 自动恢复
    recover_delay_seconds: float = 300     # 恢复延迟（5分钟）
    recover_threshold_ratio: float = 0.5   # 恢复阈值比例

    # 监控配置
    check_interval_seconds: float = 10     # 检查间隔
    window_size: int = 100                 # 统计窗口大小


class DegradationManager:
    """
    降级管理器

    功能:
    - 自动降级和恢复
    - 健康指标监控
    - 特性开关管理
    """

    # 降级级别对应的功能配置
    LEVEL_FEATURES: Dict[DegradationLevel, Dict[str, bool]] = {
        DegradationLevel.FULL: {
            "parallel_execution": True,
            "transition_response": True,
            "smart_interruption": True,
            "security_guardrails": True,
            "performance_tracing": True,
        },
        DegradationLevel.NO_PARALLEL: {
            "parallel_execution": False,
            "transition_response": True,
            "smart_interruption": True,
            "security_guardrails": True,
            "performance_tracing": True,
        },
        DegradationLevel.NO_TRANSITION: {
            "parallel_execution": False,
            "transition_response": False,
            "smart_interruption": True,
            "security_guardrails": True,
            "performance_tracing": True,
        },
        DegradationLevel.NO_INTERRUPT: {
            "parallel_execution": False,
            "transition_response": False,
            "smart_interruption": False,
            "security_guardrails": True,
            "performance_tracing": True,
        },
        DegradationLevel.MINIMAL: {
            "parallel_execution": False,
            "transition_response": False,
            "smart_interruption": False,
            "security_guardrails": True,  # 安全始终开启
            "performance_tracing": False,
        },
    }

    def __init__(self, config: Optional[DegradationConfig] = None):
        self.config = config or DegradationConfig()
        self._lock = threading.Lock()
        self._current_level = DegradationLevel.FULL
        self._state_history: List[DegradationState] = []
        self._max_history_size = 100

        # 健康指标
        self._request_times: List[float] = []
        self._error_count = 0
        self._timeout_count = 0
        self._total_requests = 0

        # 回调
        self._on_level_change: Optional[Callable[[DegradationLevel], None]] = None

        # 手动覆盖
        self._manual_override: Optional[DegradationLevel] = None

    @property
    def current_level(self) -> DegradationLevel:
        """获取当前降级级别"""
        with self._lock:
            if self._manual_override is not None:
                return self._manual_override
            return self._current_level

    @property
    def features(self) -> Dict[str, bool]:
        """获取当前可用特性"""
        return self.LEVEL_FEATURES[self.current_level]

    def is_feature_enabled(self, feature: str) -> bool:
        """检查特性是否启用"""
        return self.features.get(feature, False)

    def record_request(
        self,
        latency_ms: float,
        success: bool = True,
        timeout: bool = False,
    ) -> None:
        """记录请求指标"""
        with self._lock:
            self._total_requests += 1
            self._request_times.append(latency_ms)

            if not success:
                self._error_count += 1
            if timeout:
                self._timeout_count += 1

            # 限制窗口大小
            if len(self._request_times) > self.config.window_size:
                self._request_times = self._request_times[-self.config.window_size:]

            # 检查是否需要降级
            self._check_degradation()

    def _check_degradation(self) -> None:
        """检查是否需要降级"""
        metrics = self._calculate_metrics()

        # 决定目标降级级别
        target_level = DegradationLevel.FULL

        # 错误率检查
        if metrics.error_rate > self.config.error_rate_threshold:
            target_level = max(target_level, DegradationLevel.NO_PARALLEL)
            if metrics.error_rate > self.config.error_rate_threshold * 2:
                target_level = max(target_level, DegradationLevel.NO_TRANSITION)

        # 延迟检查
        if metrics.avg_latency_ms > self.config.latency_threshold_ms:
            target_level = max(target_level, DegradationLevel.NO_TRANSITION)

        # 超时率检查
        if metrics.timeout_rate > self.config.timeout_rate_threshold:
            target_level = max(target_level, DegradationLevel.NO_INTERRUPT)
            if metrics.timeout_rate > self.config.timeout_rate_threshold * 2:
                target_level = max(target_level, DegradationLevel.MINIMAL)

        # 应用降级
        if target_level > self._current_level:
            self._apply_degradation(target_level, metrics)
        elif target_level < self._current_level and self.config.auto_recover:
            self._try_recover(target_level, metrics)

    def _calculate_metrics(self) -> HealthMetrics:
        """计算健康指标"""
        metrics = HealthMetrics()

        if self._total_requests > 0:
            metrics.error_rate = self._error_count / self._total_requests
            metrics.timeout_rate = self._timeout_count / self._total_requests

        if self._request_times:
            metrics.avg_latency_ms = sum(self._request_times) / len(self._request_times)
            sorted_times = sorted(self._request_times)
            p99_idx = min(int(len(sorted_times) * 0.99), len(sorted_times) - 1)
            metrics.p99_latency_ms = sorted_times[p99_idx]

        return metrics

    def _apply_degradation(
        self,
        level: DegradationLevel,
        metrics: HealthMetrics,
    ) -> None:
        """应用降级"""
        if level == self._current_level:
            return

        old_level = self._current_level
        self._current_level = level

        reason = self._build_degradation_reason(metrics)
        state = DegradationState(
            level=level,
            reason=reason,
            triggered_at=time.time(),
            auto_recover_at=(
                time.time() + self.config.recover_delay_seconds
                if self.config.auto_recover
                else None
            ),
        )
        self._record_state(state)

        logger.bind(tag=TAG).warning(
            f"系统降级: {old_level.name} -> {level.name}, 原因: {reason}"
        )

        if self._on_level_change:
            try:
                self._on_level_change(level)
            except Exception as e:
                logger.bind(tag=TAG).error(f"降级回调失败: {e}")

    def _try_recover(
        self,
        target_level: DegradationLevel,
        metrics: HealthMetrics,
    ) -> None:
        """尝试恢复"""
        if not self._state_history:
            return

        last_state = self._state_history[-1]
        if last_state.auto_recover_at and time.time() < last_state.auto_recover_at:
            return  # 还未到恢复时间

        # 检查指标是否满足恢复条件
        threshold_ratio = self.config.recover_threshold_ratio
        can_recover = (
            metrics.error_rate < self.config.error_rate_threshold * threshold_ratio
            and metrics.avg_latency_ms < self.config.latency_threshold_ms * threshold_ratio
            and metrics.timeout_rate < self.config.timeout_rate_threshold * threshold_ratio
        )

        if can_recover:
            old_level = self._current_level
            self._current_level = target_level

            state = DegradationState(
                level=target_level,
                reason="自动恢复",
                triggered_at=time.time(),
            )
            self._record_state(state)

            logger.bind(tag=TAG).info(
                f"系统恢复: {old_level.name} -> {target_level.name}"
            )

            if self._on_level_change:
                try:
                    self._on_level_change(target_level)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"恢复回调失败: {e}")

    def _build_degradation_reason(self, metrics: HealthMetrics) -> str:
        """构建降级原因"""
        reasons = []

        if metrics.error_rate > self.config.error_rate_threshold:
            reasons.append(f"错误率={metrics.error_rate:.1%}")
        if metrics.avg_latency_ms > self.config.latency_threshold_ms:
            reasons.append(f"延迟={metrics.avg_latency_ms:.0f}ms")
        if metrics.timeout_rate > self.config.timeout_rate_threshold:
            reasons.append(f"超时率={metrics.timeout_rate:.1%}")

        return ", ".join(reasons) if reasons else "未知原因"

    def _record_state(self, state: DegradationState) -> None:
        """记录状态"""
        self._state_history.append(state)
        if len(self._state_history) > self._max_history_size:
            self._state_history = self._state_history[-self._max_history_size:]

    def set_manual_override(self, level: Optional[DegradationLevel]) -> None:
        """设置手动覆盖级别"""
        with self._lock:
            self._manual_override = level
            if level is not None:
                logger.bind(tag=TAG).info(f"手动设置降级级别: {level.name}")
            else:
                logger.bind(tag=TAG).info("清除手动降级覆盖")

    def force_level(self, level: DegradationLevel, reason: str = "手动触发") -> None:
        """强制设置降级级别"""
        with self._lock:
            old_level = self._current_level
            self._current_level = level

            state = DegradationState(
                level=level,
                reason=reason,
                triggered_at=time.time(),
            )
            self._record_state(state)

            logger.bind(tag=TAG).warning(
                f"强制降级: {old_level.name} -> {level.name}, 原因: {reason}"
            )

    def reset(self) -> None:
        """重置降级状态"""
        with self._lock:
            self._current_level = DegradationLevel.FULL
            self._manual_override = None
            self._request_times.clear()
            self._error_count = 0
            self._timeout_count = 0
            self._total_requests = 0
            logger.bind(tag=TAG).info("降级状态已重置")

    def on_level_change(
        self,
        callback: Callable[[DegradationLevel], None],
    ) -> None:
        """设置级别变更回调"""
        self._on_level_change = callback

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            metrics = self._calculate_metrics()
            return {
                "current_level": self._current_level.name,
                "manual_override": (
                    self._manual_override.name
                    if self._manual_override
                    else None
                ),
                "features": self.features,
                "metrics": {
                    "error_rate": metrics.error_rate,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "p99_latency_ms": metrics.p99_latency_ms,
                    "timeout_rate": metrics.timeout_rate,
                },
                "thresholds": {
                    "error_rate": self.config.error_rate_threshold,
                    "latency_ms": self.config.latency_threshold_ms,
                    "timeout_rate": self.config.timeout_rate_threshold,
                },
                "total_requests": self._total_requests,
                "state_changes": len(self._state_history),
            }

    def get_state_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取状态变更历史"""
        with self._lock:
            recent = self._state_history[-count:]
            return [
                {
                    "level": s.level.name,
                    "reason": s.reason,
                    "triggered_at": s.triggered_at,
                    "auto_recover_at": s.auto_recover_at,
                }
                for s in recent
            ]


# 全局降级管理器实例
_global_manager: Optional[DegradationManager] = None
_manager_lock = threading.Lock()


def get_degradation_manager() -> DegradationManager:
    """获取全局降级管理器"""
    global _global_manager
    with _manager_lock:
        if _global_manager is None:
            _global_manager = DegradationManager()
        return _global_manager


def is_feature_enabled(feature: str) -> bool:
    """检查特性是否启用（全局函数）"""
    return get_degradation_manager().is_feature_enabled(feature)




