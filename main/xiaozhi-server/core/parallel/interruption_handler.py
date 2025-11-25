"""
智能打断处理器

功能:
- 快速检测打断意图
- 立即停止当前TTS
- 状态转换管理
- 打断反馈响应
"""

import time
import asyncio
import threading
from typing import Optional, Callable, List, Set
from dataclasses import dataclass, field
from enum import Enum
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class InterruptionType(Enum):
    """打断类型"""
    EXPLICIT = "explicit"      # 明确打断（等等、打住、停）
    IMPLICIT = "implicit"      # 隐式打断（我想问、我要、帮我）
    BACKCHANNEL = "backchannel"  # 反馈信号（嗯、好的、继续）


@dataclass
class InterruptionEvent:
    """打断事件"""
    type: InterruptionType
    trigger_text: str
    timestamp: float
    response_time_ms: float = 0.0
    handled: bool = False


@dataclass
class InterruptionConfig:
    """打断配置"""
    enabled: bool = True
    target_response_ms: float = 400.0       # 目标响应时间
    min_speech_length: int = 2              # 最小语音长度
    debounce_ms: float = 200.0              # 防抖时间
    enable_backchannel: bool = True         # 启用反馈信号处理


class InterruptionHandler:
    """
    智能打断处理器

    目标: <400ms 响应用户打断
    """

    # 明确打断词列表
    EXPLICIT_PATTERNS: List[str] = [
        "等等", "打住", "停", "不对", "算了", "取消",
        "等一下", "停一下", "暂停", "别说了", "够了",
    ]

    # 隐式打断词列表
    IMPLICIT_PATTERNS: List[str] = [
        "我想问", "我要", "帮我", "能不能", "可以",
        "我需要", "请问", "告诉我",
    ]

    # 反馈信号词列表
    BACKCHANNEL_PATTERNS: List[str] = [
        "嗯", "好的", "继续", "是的", "对", "明白",
    ]

    def __init__(
        self,
        config: Optional[InterruptionConfig] = None,
        on_interrupt: Optional[Callable[[], None]] = None,
    ):
        self.config = config or InterruptionConfig()
        self._on_interrupt = on_interrupt
        self._lock = threading.Lock()
        self._interrupted = False
        self._last_interrupt_time: float = 0.0
        self._interrupt_history: List[InterruptionEvent] = []
        self._max_history_size = 50
        
        # 性能统计
        self._total_interrupts = 0
        self._total_response_time_ms = 0.0

    @property
    def is_interrupted(self) -> bool:
        """检查是否已被打断"""
        with self._lock:
            return self._interrupted

    def reset(self) -> None:
        """重置打断状态"""
        with self._lock:
            self._interrupted = False
            logger.bind(tag=TAG).debug("打断状态已重置")

    async def handle_interruption(
        self,
        user_speech: str,
        tts_stop_callback: Optional[Callable[[], None]] = None,
        immediate_response_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        处理用户打断

        Args:
            user_speech: 用户语音内容
            tts_stop_callback: TTS停止回调
            immediate_response_callback: 即时响应回调

        Returns:
            bool: 是否成功处理打断
        """
        if not self.config.enabled:
            return False

        start_time = time.time()

        # 防抖检查
        with self._lock:
            if (start_time - self._last_interrupt_time) * 1000 < self.config.debounce_ms:
                logger.bind(tag=TAG).debug("打断防抖中，跳过处理")
                return False

        # 检测打断意图（目标 <50ms）
        interruption_type = self._detect_interruption(user_speech)
        if not interruption_type:
            return False

        with self._lock:
            # 1. 设置打断标志
            self._interrupted = True
            self._last_interrupt_time = start_time

            # 2. 停止当前TTS（目标 <100ms）
            if tts_stop_callback:
                try:
                    tts_stop_callback()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"TTS停止回调失败: {e}")

            # 3. 触发打断回调
            if self._on_interrupt:
                try:
                    self._on_interrupt()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"打断回调失败: {e}")

        # 4. 立即响应用户（目标 <200ms）
        if immediate_response_callback:
            response = self._get_interruption_response(interruption_type)
            try:
                immediate_response_callback(response)
            except Exception as e:
                logger.bind(tag=TAG).error(f"即时响应回调失败: {e}")

        # 记录性能
        elapsed_ms = (time.time() - start_time) * 1000
        event = InterruptionEvent(
            type=interruption_type,
            trigger_text=user_speech,
            timestamp=start_time,
            response_time_ms=elapsed_ms,
            handled=True,
        )
        self._record_event(event)

        logger.bind(tag=TAG).info(
            f"打断处理完成: type={interruption_type.value}, "
            f"耗时={elapsed_ms:.1f}ms, 目标<{self.config.target_response_ms}ms"
        )

        # 性能检查
        if elapsed_ms > self.config.target_response_ms:
            logger.bind(tag=TAG).warning(
                f"打断响应超时: {elapsed_ms:.1f}ms > {self.config.target_response_ms}ms"
            )

        return True

    def _detect_interruption(
        self,
        speech: str,
    ) -> Optional[InterruptionType]:
        """
        快速检测打断意图（目标 <50ms）

        Returns:
            InterruptionType or None
        """
        if not speech or len(speech) < self.config.min_speech_length:
            return None

        speech_lower = speech.strip()

        # 明确打断检测（优先级最高）
        for pattern in self.EXPLICIT_PATTERNS:
            if pattern in speech_lower:
                return InterruptionType.EXPLICIT

        # 隐式打断检测
        for pattern in self.IMPLICIT_PATTERNS:
            if pattern in speech_lower:
                return InterruptionType.IMPLICIT

        # 反馈信号检测
        if self.config.enable_backchannel:
            for pattern in self.BACKCHANNEL_PATTERNS:
                if speech_lower == pattern or speech_lower.startswith(pattern):
                    return InterruptionType.BACKCHANNEL

        return None

    def _get_interruption_response(
        self,
        interruption_type: InterruptionType,
    ) -> str:
        """获取打断响应话术"""
        responses = {
            InterruptionType.EXPLICIT: "好的，您说",
            InterruptionType.IMPLICIT: "好的，我听着",
            InterruptionType.BACKCHANNEL: "",  # 反馈信号不需要响应
        }
        return responses.get(interruption_type, "好的")

    def _record_event(self, event: InterruptionEvent) -> None:
        """记录打断事件"""
        with self._lock:
            self._interrupt_history.append(event)
            if len(self._interrupt_history) > self._max_history_size:
                self._interrupt_history = self._interrupt_history[-self._max_history_size:]

            # 更新统计
            self._total_interrupts += 1
            self._total_response_time_ms += event.response_time_ms

    def get_statistics(self) -> dict:
        """获取打断统计信息"""
        with self._lock:
            if self._total_interrupts == 0:
                avg_response_time = 0.0
            else:
                avg_response_time = self._total_response_time_ms / self._total_interrupts

            response_times = [e.response_time_ms for e in self._interrupt_history]

            return {
                "total_interrupts": self._total_interrupts,
                "avg_response_time_ms": round(avg_response_time, 1),
                "target_response_ms": self.config.target_response_ms,
                "success_rate": (
                    sum(1 for e in self._interrupt_history if e.response_time_ms < self.config.target_response_ms)
                    / len(self._interrupt_history)
                    if self._interrupt_history
                    else 1.0
                ),
                "min_response_ms": min(response_times) if response_times else 0,
                "max_response_ms": max(response_times) if response_times else 0,
            }

    def is_backchannel(self, speech: str) -> bool:
        """检查是否是反馈信号"""
        if not speech:
            return False
        speech_lower = speech.strip()
        for pattern in self.BACKCHANNEL_PATTERNS:
            if speech_lower == pattern:
                return True
        return False

    def add_custom_pattern(
        self,
        pattern: str,
        pattern_type: InterruptionType,
    ) -> None:
        """添加自定义打断词"""
        with self._lock:
            if pattern_type == InterruptionType.EXPLICIT:
                if pattern not in self.EXPLICIT_PATTERNS:
                    self.EXPLICIT_PATTERNS.append(pattern)
            elif pattern_type == InterruptionType.IMPLICIT:
                if pattern not in self.IMPLICIT_PATTERNS:
                    self.IMPLICIT_PATTERNS.append(pattern)
            elif pattern_type == InterruptionType.BACKCHANNEL:
                if pattern not in self.BACKCHANNEL_PATTERNS:
                    self.BACKCHANNEL_PATTERNS.append(pattern)

    def get_recent_events(self, count: int = 10) -> List[dict]:
        """获取最近的打断事件"""
        with self._lock:
            recent = self._interrupt_history[-count:]
            return [
                {
                    "type": e.type.value,
                    "trigger_text": e.trigger_text,
                    "timestamp": e.timestamp,
                    "response_time_ms": e.response_time_ms,
                    "handled": e.handled,
                }
                for e in recent
            ]


