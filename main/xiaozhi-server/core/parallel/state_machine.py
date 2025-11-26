"""
会话状态机

线程安全的状态机实现，支持智能打断。


状态流转图:
    IDLE → PROCESSING_INTENT → PLAYING_TRANSITION → EXECUTING_TOOLS
      ↑                                                    ↓
      └──────────── SPEAKING ←── GENERATING_RESPONSE ←─────┘
                       ↓
                  INTERRUPTED → PROCESSING_INTENT (新查询)
"""

import time
import threading
from enum import Enum
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ConversationState(Enum):
    """会话状态枚举"""
    IDLE = "idle"                           # 空闲状态
    PROCESSING_INTENT = "processing_intent"  # 处理意图
    PLAYING_TRANSITION = "playing_transition"  # 播放过渡响应
    EXECUTING_TOOLS = "executing_tools"      # 执行工具
    GENERATING_RESPONSE = "generating_response"  # 生成响应
    SPEAKING = "speaking"                    # 播放语音
    INTERRUPTED = "interrupted"              # 被用户打断
    BACKCHANNELING = "backchanneling"        # 发送反馈信号
    ERROR = "error"                          # 错误状态


# 合法的状态转换映射
# 优化：支持并发场景下的状态转换（如工具调用触发新查询、用户打断等）
VALID_TRANSITIONS: Dict[ConversationState, List[ConversationState]] = {
    ConversationState.IDLE: [
        ConversationState.PROCESSING_INTENT,
        ConversationState.ERROR,
    ],
    ConversationState.PROCESSING_INTENT: [
        ConversationState.PLAYING_TRANSITION,
        ConversationState.EXECUTING_TOOLS,
        ConversationState.GENERATING_RESPONSE,
        ConversationState.SPEAKING,
        ConversationState.IDLE,
        ConversationState.INTERRUPTED,
        ConversationState.ERROR,
    ],
    ConversationState.PLAYING_TRANSITION: [
        ConversationState.EXECUTING_TOOLS,
        ConversationState.GENERATING_RESPONSE,
        ConversationState.SPEAKING,  # 过渡响应后可直接进入播放
        ConversationState.IDLE,
        ConversationState.INTERRUPTED,
        ConversationState.ERROR,
    ],
    ConversationState.EXECUTING_TOOLS: [
        ConversationState.GENERATING_RESPONSE,
        ConversationState.SPEAKING,
        ConversationState.PROCESSING_INTENT,  # 工具执行后可能触发新查询
        ConversationState.IDLE,
        ConversationState.INTERRUPTED,
        ConversationState.ERROR,
    ],
    ConversationState.GENERATING_RESPONSE: [
        ConversationState.SPEAKING,
        ConversationState.PROCESSING_INTENT,  # 工具调用后触发新查询（递归调用）
        ConversationState.PLAYING_TRANSITION,  # 并发场景：生成响应时播放过渡
        ConversationState.EXECUTING_TOOLS,     # 并发场景：响应中触发工具调用
        ConversationState.IDLE,
        ConversationState.INTERRUPTED,
        ConversationState.ERROR,
    ],
    ConversationState.SPEAKING: [
        ConversationState.PROCESSING_INTENT,  # 播放时用户新查询
        ConversationState.IDLE,
        ConversationState.INTERRUPTED,
        ConversationState.ERROR,
    ],
    ConversationState.INTERRUPTED: [
        ConversationState.PROCESSING_INTENT,  # 打断后处理新查询
        ConversationState.IDLE,
        ConversationState.ERROR,
    ],
    ConversationState.BACKCHANNELING: [
        ConversationState.SPEAKING,
        ConversationState.PROCESSING_INTENT,
        ConversationState.IDLE,
        ConversationState.INTERRUPTED,
        ConversationState.ERROR,
    ],
    ConversationState.ERROR: [
        ConversationState.IDLE,
        ConversationState.PROCESSING_INTENT,  # 错误恢复后可处理新查询
    ],
}


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: ConversationState
    to_state: ConversationState
    timestamp: float
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationStateMachine:
    """
    会话状态机

    线程安全实现，支持：
    - 合法状态转换验证
    - 智能打断处理
    - 状态转换回调
    - 性能追踪
    """

    def __init__(
        self,
        session_id: str,
        on_state_change: Optional[Callable[[ConversationState, ConversationState], None]] = None,
    ):
        self.session_id = session_id
        self._state = ConversationState.IDLE
        self._lock = threading.RLock()  # 使用可重入锁
        self._state_enter_time = time.time()
        self._on_state_change = on_state_change
        self._transition_history: List[StateTransition] = []
        self._max_history_size = 100

    @property
    def state(self) -> ConversationState:
        """获取当前状态（线程安全）"""
        with self._lock:
            return self._state

    @property
    def state_duration_ms(self) -> float:
        """获取当前状态持续时间（毫秒）"""
        with self._lock:
            return (time.time() - self._state_enter_time) * 1000

    def transition_to(
        self,
        new_state: ConversationState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        尝试转换到新状态

        Args:
            new_state: 目标状态
            metadata: 附加元数据

        Returns:
            bool: 转换是否成功
        """
        with self._lock:
            old_state = self._state

            # 验证状态转换合法性
            if not self._is_valid_transition(old_state, new_state):
                logger.bind(tag=TAG).warning(
                    f"[{self.session_id}] 非法状态转换: {old_state.value} → {new_state.value}"
                )
                return False

            # 记录转换
            now = time.time()
            duration_ms = (now - self._state_enter_time) * 1000
            transition = StateTransition(
                from_state=old_state,
                to_state=new_state,
                timestamp=now,
                duration_ms=duration_ms,
                metadata=metadata or {},
            )
            self._record_transition(transition)

            # 执行转换
            self._state = new_state
            self._state_enter_time = now

            logger.bind(tag=TAG).debug(
                f"[{self.session_id}] 状态转换: {old_state.value} → {new_state.value} "
                f"(耗时 {duration_ms:.1f}ms)"
            )

            # 触发回调
            if self._on_state_change:
                try:
                    self._on_state_change(old_state, new_state)
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"[{self.session_id}] 状态变更回调错误: {e}"
                    )

            return True

    def _is_valid_transition(
        self,
        from_state: ConversationState,
        to_state: ConversationState,
    ) -> bool:
        """验证状态转换是否合法"""
        if from_state == to_state:
            return True  # 允许保持当前状态
        valid_targets = VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_targets

    def _record_transition(self, transition: StateTransition) -> None:
        """记录状态转换历史"""
        self._transition_history.append(transition)
        # 限制历史记录大小
        if len(self._transition_history) > self._max_history_size:
            self._transition_history = self._transition_history[-self._max_history_size:]

    def can_interrupt(self) -> bool:
        """检查当前状态是否可以被打断"""
        interruptible_states = [
            ConversationState.PLAYING_TRANSITION,
            ConversationState.EXECUTING_TOOLS,
            ConversationState.GENERATING_RESPONSE,
            ConversationState.SPEAKING,
        ]
        with self._lock:
            return self._state in interruptible_states

    def is_busy(self) -> bool:
        """检查是否正在处理中"""
        busy_states = [
            ConversationState.PROCESSING_INTENT,
            ConversationState.PLAYING_TRANSITION,
            ConversationState.EXECUTING_TOOLS,
            ConversationState.GENERATING_RESPONSE,
            ConversationState.SPEAKING,
        ]
        with self._lock:
            return self._state in busy_states

    def is_idle(self) -> bool:
        """检查是否空闲"""
        with self._lock:
            return self._state == ConversationState.IDLE

    def reset(self) -> None:
        """重置到空闲状态"""
        with self._lock:
            self._state = ConversationState.IDLE
            self._state_enter_time = time.time()
            logger.bind(tag=TAG).debug(f"[{self.session_id}] 状态机重置")

    def get_statistics(self) -> Dict[str, Any]:
        """获取状态机统计信息"""
        with self._lock:
            state_durations: Dict[str, float] = {}
            for transition in self._transition_history:
                state_name = transition.from_state.value
                state_durations[state_name] = (
                    state_durations.get(state_name, 0) + transition.duration_ms
                )

            return {
                "session_id": self.session_id,
                "current_state": self._state.value,
                "current_state_duration_ms": self.state_duration_ms,
                "total_transitions": len(self._transition_history),
                "state_durations_ms": state_durations,
            }

    def get_last_transitions(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的状态转换记录"""
        with self._lock:
            recent = self._transition_history[-count:]
            return [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "timestamp": t.timestamp,
                    "duration_ms": t.duration_ms,
                    "metadata": t.metadata,
                }
                for t in recent
            ]


