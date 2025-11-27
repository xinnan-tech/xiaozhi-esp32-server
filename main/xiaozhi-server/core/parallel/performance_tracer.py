"""
性能追踪器

用于追踪和分析语音对话各阶段的性能指标。
支持分布式追踪、阶段计时、性能统计。

"""

import time
import threading
import statistics
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import contextmanager
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TracePhase(Enum):
    """追踪阶段枚举"""
    TOTAL = "total"                         # 总耗时
    INTENT_DETECTION = "intent_detection"   # 意图识别
    TRANSITION_RESPONSE = "transition_response"  # 过渡响应
    TOOL_PLANNING = "tool_planning"         # 工具规划
    TOOL_EXECUTION = "tool_execution"       # 工具执行
    RESPONSE_GENERATION = "response_generation"  # 响应生成
    TTS_SYNTHESIS = "tts_synthesis"         # TTS合成
    AUDIO_PLAYBACK = "audio_playback"       # 音频播放
    INTERRUPTION = "interruption"           # 打断处理
    MEMORY_QUERY = "memory_query"           # 记忆查询


@dataclass
class TraceSpan:
    """追踪跨度"""
    phase: TracePhase
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["TraceSpan"] = field(default_factory=list)
    error: Optional[str] = None

    def finish(self) -> None:
        """完成跨度"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@dataclass
class PerformanceMetrics:
    """性能指标汇总"""
    ttfr_ms: float = 0.0                    # 首次响应时间
    total_duration_ms: float = 0.0          # 总耗时
    phase_durations: Dict[str, float] = field(default_factory=dict)
    parallel_factor: float = 1.0            # 并行因子
    tool_count: int = 0                     # 工具调用数
    interrupted: bool = False               # 是否被打断


class PerformanceTracer:
    """
    性能追踪器

    提供:
    - 上下文管理器方式的阶段计时
    - 嵌套追踪支持
    - 自动性能统计
    - 阈值告警
    """

    # 性能阈值 (毫秒)
    THRESHOLDS = {
        TracePhase.TOTAL: 3000,              # 总耗时 < 3秒
        TracePhase.INTENT_DETECTION: 300,    # 意图识别 < 300ms
        TracePhase.TRANSITION_RESPONSE: 100,  # 过渡响应 < 100ms
        TracePhase.TOOL_PLANNING: 200,       # 工具规划 < 200ms
        TracePhase.TOOL_EXECUTION: 2000,     # 工具执行 < 2秒
        TracePhase.RESPONSE_GENERATION: 1500,  # 响应生成 < 1.5秒
        TracePhase.TTS_SYNTHESIS: 800,       # TTS合成 < 800ms
        TracePhase.INTERRUPTION: 400,        # 打断处理 < 400ms (2025标准)
    }

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._lock = threading.Lock()
        self._root_span: Optional[TraceSpan] = None
        self._current_span: Optional[TraceSpan] = None
        self._span_stack: List[TraceSpan] = []
        self._ttfr_recorded = False
        self._ttfr_time: Optional[float] = None
        self._start_time: Optional[float] = None
        
        # 历史统计
        self._phase_history: Dict[TracePhase, List[float]] = {
            phase: [] for phase in TracePhase
        }
        self._max_history_size = 100

    def start_trace(self) -> None:
        """开始新的追踪"""
        with self._lock:
            self._start_time = time.time()
            self._root_span = TraceSpan(
                phase=TracePhase.TOTAL,
                start_time=self._start_time,
            )
            self._current_span = self._root_span
            self._span_stack = [self._root_span]
            self._ttfr_recorded = False
            self._ttfr_time = None

    def finish_trace(self) -> PerformanceMetrics:
        """完成追踪并返回性能指标"""
        with self._lock:
            if self._root_span:
                self._root_span.finish()
                self._record_phase_duration(
                    TracePhase.TOTAL,
                    self._root_span.duration_ms,
                )
                self._check_threshold(
                    TracePhase.TOTAL,
                    self._root_span.duration_ms,
                )

            return self._build_metrics()

    @contextmanager
    def trace(
        self,
        phase: TracePhase,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        上下文管理器方式的阶段追踪

        用法:
            with tracer.trace(TracePhase.TOOL_EXECUTION):
                execute_tool()
        """
        span = TraceSpan(
            phase=phase,
            start_time=time.time(),
            metadata=metadata or {},
        )

        with self._lock:
            if self._current_span:
                self._current_span.children.append(span)
            self._span_stack.append(span)
            self._current_span = span

        try:
            yield span
        except Exception as e:
            span.error = str(e)
            raise
        finally:
            span.finish()
            with self._lock:
                if self._span_stack:
                    self._span_stack.pop()
                self._current_span = (
                    self._span_stack[-1] if self._span_stack else None
                )
                self._record_phase_duration(phase, span.duration_ms)
                self._check_threshold(phase, span.duration_ms)

    def record_ttfr(self) -> float:
        """
        记录首次响应时间 (TTFR)

        Returns:
            float: TTFR（毫秒）
        """
        with self._lock:
            if not self._ttfr_recorded and self._start_time:
                self._ttfr_time = time.time()
                self._ttfr_recorded = True
                ttfr_ms = (self._ttfr_time - self._start_time) * 1000
                logger.bind(tag=TAG).info(
                    f"[{self.session_id}] TTFR: {ttfr_ms:.1f}ms"
                )
                return ttfr_ms
            return 0.0

    def _record_phase_duration(
        self,
        phase: TracePhase,
        duration_ms: float,
    ) -> None:
        """记录阶段耗时到历史"""
        history = self._phase_history[phase]
        history.append(duration_ms)
        if len(history) > self._max_history_size:
            self._phase_history[phase] = history[-self._max_history_size:]

    def _check_threshold(
        self,
        phase: TracePhase,
        duration_ms: float,
    ) -> None:
        """检查阈值并告警"""
        threshold = self.THRESHOLDS.get(phase)
        if threshold and duration_ms > threshold:
            logger.bind(tag=TAG).warning(
                f"[{self.session_id}] 性能告警: {phase.value} "
                f"耗时 {duration_ms:.1f}ms 超过阈值 {threshold}ms"
            )

    def _build_metrics(self) -> PerformanceMetrics:
        """构建性能指标"""
        metrics = PerformanceMetrics()

        if self._root_span:
            metrics.total_duration_ms = self._root_span.duration_ms

        if self._ttfr_time and self._start_time:
            metrics.ttfr_ms = (self._ttfr_time - self._start_time) * 1000

        # 收集各阶段耗时
        for phase, history in self._phase_history.items():
            if history:
                metrics.phase_durations[phase.value] = history[-1]

        return metrics

    def get_phase_statistics(
        self,
        phase: TracePhase,
    ) -> Dict[str, float]:
        """获取指定阶段的统计信息"""
        with self._lock:
            history = self._phase_history.get(phase, [])
            if not history:
                return {}

            return {
                "count": len(history),
                "avg_ms": statistics.mean(history),
                "min_ms": min(history),
                "max_ms": max(history),
                "p50_ms": statistics.median(history),
                "p95_ms": (
                    sorted(history)[int(len(history) * 0.95)]
                    if len(history) >= 20
                    else max(history)
                ),
                "p99_ms": (
                    sorted(history)[int(len(history) * 0.99)]
                    if len(history) >= 100
                    else max(history)
                ),
            }

    def get_all_statistics(self) -> Dict[str, Any]:
        """获取所有阶段的统计信息"""
        with self._lock:
            return {
                "session_id": self.session_id,
                "phases": {
                    phase.value: self.get_phase_statistics(phase)
                    for phase in TracePhase
                    if self._phase_history.get(phase)
                },
            }

    def to_dict(self) -> Dict[str, Any]:
        """导出追踪数据"""
        with self._lock:
            if not self._root_span:
                return {}

            def span_to_dict(span: TraceSpan) -> Dict[str, Any]:
                return {
                    "phase": span.phase.value,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration_ms": span.duration_ms,
                    "metadata": span.metadata,
                    "error": span.error,
                    "children": [span_to_dict(c) for c in span.children],
                }

            return {
                "session_id": self.session_id,
                "ttfr_ms": (
                    (self._ttfr_time - self._start_time) * 1000
                    if self._ttfr_time and self._start_time
                    else None
                ),
                "trace": span_to_dict(self._root_span),
            }


class PerformanceTracerFactory:
    """性能追踪器工厂"""

    _instances: Dict[str, PerformanceTracer] = {}
    _lock = threading.Lock()

    @classmethod
    def get_tracer(cls, session_id: str) -> PerformanceTracer:
        """获取或创建追踪器实例"""
        with cls._lock:
            if session_id not in cls._instances:
                cls._instances[session_id] = PerformanceTracer(session_id)
            return cls._instances[session_id]

    @classmethod
    def remove_tracer(cls, session_id: str) -> None:
        """移除追踪器实例"""
        with cls._lock:
            cls._instances.pop(session_id, None)

    @classmethod
    def get_global_statistics(cls) -> Dict[str, Any]:
        """获取全局统计信息"""
        with cls._lock:
            all_stats = {}
            for session_id, tracer in cls._instances.items():
                all_stats[session_id] = tracer.get_all_statistics()
            return all_stats




