"""
并行优化模块

基于 LLMCompiler (ICML 2024) 架构，实现语音对话的并行优化。

核心组件:
- ConversationStateMachine: 状态机管理（线程安全 + 打断状态）
- InterruptionHandler: 智能打断处理器（<400ms响应）
- PerformanceTracer: 性能追踪
- TransitionResponseGenerator: 过渡响应生成器
- SecurityGuardrails: 安全防护层
- LLMCompilerOrchestrator: 并行执行编排器
- DegradationManager: 降级管理器
- FeatureFlagManager: 特性开关管理器

性能指标（基于 LLMCompiler 论文）:
- 延迟降低: 3.7x
- 成本节省: 6.7x
- 准确率提升: ~9%
- TTFR: <500ms
- 打断响应: <400ms
"""

from .state_machine import ConversationState, ConversationStateMachine
from .performance_tracer import (
    PerformanceTracer,
    PerformanceTracerFactory,
    TracePhase,
)
from .interruption_handler import (
    InterruptionHandler,
    InterruptionType,
    InterruptionConfig,
)
from .transition_generator import (
    TransitionResponseGenerator,
    TransitionResponse,
    ResponseLevel,
)
from .security_guardrails import (
    SecurityGuardrails,
    SecurityLevel,
    SecurityAction,
)
from .priority_queue import (
    TTSPriorityQueue,
    TTSMessageQueue,
    PriorityLevel,
    PriorityItem,
)
from .llm_compiler_orchestrator import (
    LLMCompilerOrchestrator,
    ExecutionPlan,
    ExecutionResult,
    ToolTask,
    ToolStatus,
)
from .degradation_manager import (
    DegradationManager,
    DegradationLevel,
    DegradationConfig,
    get_degradation_manager,
    is_feature_enabled,
)
from .feature_flags import (
    FeatureFlagManager,
    FeatureFlag,
    get_feature_manager,
    is_enabled,
    enable,
    disable,
)
from .parallel_chat_handler import ParallelChatHandler
from .smart_interruption import (
    SmartInterruptionManager,
    SmartInterruptionConfig,
    InterruptionDecision,
    smart_interrupt_check,
    should_skip_vad_interrupt,
)

__all__ = [
    # 状态机
    "ConversationState",
    "ConversationStateMachine",
    # 性能追踪
    "PerformanceTracer",
    "PerformanceTracerFactory",
    "TracePhase",
    # 打断处理
    "InterruptionHandler",
    "InterruptionType",
    "InterruptionConfig",
    # 过渡响应
    "TransitionResponseGenerator",
    "TransitionResponse",
    "ResponseLevel",
    # 安全防护
    "SecurityGuardrails",
    "SecurityLevel",
    "SecurityAction",
    # 优先级队列
    "TTSPriorityQueue",
    "TTSMessageQueue",
    "PriorityLevel",
    "PriorityItem",
    # LLMCompiler 编排器
    "LLMCompilerOrchestrator",
    "ExecutionPlan",
    "ExecutionResult",
    "ToolTask",
    "ToolStatus",
    # 降级管理
    "DegradationManager",
    "DegradationLevel",
    "DegradationConfig",
    "get_degradation_manager",
    "is_feature_enabled",
    # 特性开关
    "FeatureFlagManager",
    "FeatureFlag",
    "get_feature_manager",
    "is_enabled",
    "enable",
    "disable",
    # 并行聊天处理器
    "ParallelChatHandler",
    # 智能打断
    "SmartInterruptionManager",
    "SmartInterruptionConfig",
    "InterruptionDecision",
    "smart_interrupt_check",
    "should_skip_vad_interrupt",
]

