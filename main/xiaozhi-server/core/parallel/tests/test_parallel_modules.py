"""
并行优化模块单元测试

测试目标:
- 模块导入正常
- 核心组件功能正确
- 性能指标符合预期
"""

import asyncio
import time
import unittest
from unittest.mock import MagicMock, AsyncMock


class TestStateMachine(unittest.TestCase):
    """状态机测试"""

    def test_initial_state(self):
        """测试初始状态"""
        from core.parallel.state_machine import (
            ConversationStateMachine,
            ConversationState,
        )

        sm = ConversationStateMachine("test-session")
        self.assertEqual(sm.state, ConversationState.IDLE)

    def test_valid_transition(self):
        """测试合法状态转换"""
        from core.parallel.state_machine import (
            ConversationStateMachine,
            ConversationState,
        )

        sm = ConversationStateMachine("test-session")

        # IDLE -> PROCESSING_INTENT
        result = sm.transition_to(ConversationState.PROCESSING_INTENT)
        self.assertTrue(result)
        self.assertEqual(sm.state, ConversationState.PROCESSING_INTENT)

    def test_invalid_transition(self):
        """测试非法状态转换"""
        from core.parallel.state_machine import (
            ConversationStateMachine,
            ConversationState,
        )

        sm = ConversationStateMachine("test-session")

        # IDLE -> SPEAKING (非法)
        result = sm.transition_to(ConversationState.SPEAKING)
        self.assertFalse(result)
        self.assertEqual(sm.state, ConversationState.IDLE)

    def test_can_interrupt(self):
        """测试可打断状态"""
        from core.parallel.state_machine import (
            ConversationStateMachine,
            ConversationState,
        )

        sm = ConversationStateMachine("test-session")

        # 空闲状态不可打断
        self.assertFalse(sm.can_interrupt())

        # 转换到可打断状态
        sm.transition_to(ConversationState.PROCESSING_INTENT)
        sm.transition_to(ConversationState.SPEAKING)
        self.assertTrue(sm.can_interrupt())


class TestPerformanceTracer(unittest.TestCase):
    """性能追踪器测试"""

    def test_basic_tracing(self):
        """测试基本追踪"""
        from core.parallel.performance_tracer import (
            PerformanceTracer,
            TracePhase,
        )

        tracer = PerformanceTracer("test-session")
        tracer.start_trace()

        with tracer.trace(TracePhase.INTENT_DETECTION):
            time.sleep(0.01)  # 10ms

        metrics = tracer.finish_trace()
        self.assertGreater(metrics.total_duration_ms, 10)

    def test_ttfr_recording(self):
        """测试 TTFR 记录"""
        from core.parallel.performance_tracer import (
            PerformanceTracer,
            TracePhase,
        )

        tracer = PerformanceTracer("test-session")
        tracer.start_trace()

        time.sleep(0.01)  # 10ms
        ttfr = tracer.record_ttfr()

        self.assertGreater(ttfr, 10)


class TestInterruptionHandler(unittest.TestCase):
    """打断处理器测试"""

    def test_explicit_interruption_detection(self):
        """测试明确打断检测"""
        from core.parallel.interruption_handler import (
            InterruptionHandler,
            InterruptionType,
        )

        handler = InterruptionHandler()

        # 明确打断
        result = handler._detect_interruption("等等，我想问")
        self.assertEqual(result, InterruptionType.EXPLICIT)

    def test_implicit_interruption_detection(self):
        """测试隐式打断检测"""
        from core.parallel.interruption_handler import (
            InterruptionHandler,
            InterruptionType,
        )

        handler = InterruptionHandler()

        # 隐式打断
        result = handler._detect_interruption("帮我查一下天气")
        self.assertEqual(result, InterruptionType.IMPLICIT)

    def test_response_time(self):
        """测试响应时间 < 400ms"""
        from core.parallel.interruption_handler import (
            InterruptionHandler,
            InterruptionConfig,
        )

        config = InterruptionConfig(target_response_ms=400)
        handler = InterruptionHandler(config=config)

        start = time.time()

        # 同步检测
        result = handler._detect_interruption("停")
        elapsed = (time.time() - start) * 1000

        self.assertIsNotNone(result)
        self.assertLess(elapsed, 50)  # 检测应 < 50ms


class TestTransitionGenerator(unittest.TestCase):
    """过渡响应生成器测试"""

    def test_rule_mapping(self):
        """测试规则映射"""
        from core.parallel.transition_generator import (
            TransitionResponseGenerator,
            ResponseLevel,
        )

        generator = TransitionResponseGenerator()

        # 精确匹配
        response = generator.generate("payment_check")
        self.assertEqual(response.level, ResponseLevel.RULE)
        self.assertIn("查询", response.text)

    def test_generation_speed(self):
        """测试生成速度 < 50ms"""
        from core.parallel.transition_generator import TransitionResponseGenerator

        generator = TransitionResponseGenerator()

        start = time.time()
        response = generator.generate("order_search")
        elapsed = (time.time() - start) * 1000

        self.assertLess(elapsed, 50)


class TestPriorityQueue(unittest.TestCase):
    """优先级队列测试"""

    def test_priority_order(self):
        """测试优先级排序"""
        from core.parallel.priority_queue import (
            TTSPriorityQueue,
            PriorityLevel,
        )

        queue = TTSPriorityQueue()

        # 放入不同优先级
        queue.put("normal", PriorityLevel.NORMAL)
        queue.put("interrupt", PriorityLevel.INTERRUPT)
        queue.put("transition", PriorityLevel.TRANSITION)

        # 应按优先级顺序取出
        item1 = queue.get()
        item2 = queue.get()
        item3 = queue.get()

        self.assertEqual(item1.content, "interrupt")
        self.assertEqual(item2.content, "transition")
        self.assertEqual(item3.content, "normal")


class TestSecurityGuardrails(unittest.TestCase):
    """安全防护层测试"""

    def test_allowlist(self):
        """测试白名单验证"""
        from core.parallel.security_guardrails import SecurityGuardrails

        security = SecurityGuardrails(strict_mode=True)

        # 白名单内
        self.assertTrue(security._validate_allowlist("payment_check"))

        # 白名单外
        self.assertFalse(security._validate_allowlist("unknown_tool"))

    def test_critical_operation_detection(self):
        """测试关键操作检测"""
        from core.parallel.security_guardrails import SecurityGuardrails

        security = SecurityGuardrails()

        # 关键操作
        self.assertTrue(security._is_critical_operation("order_cancel"))
        self.assertTrue(security._is_critical_operation("payment_refund"))

        # 非关键操作
        self.assertFalse(security._is_critical_operation("payment_check"))


class TestDegradationManager(unittest.TestCase):
    """降级管理器测试"""

    def test_initial_level(self):
        """测试初始降级级别"""
        from core.parallel.degradation_manager import (
            DegradationManager,
            DegradationLevel,
        )

        manager = DegradationManager()
        self.assertEqual(manager.current_level, DegradationLevel.FULL)

    def test_feature_flags(self):
        """测试特性开关"""
        from core.parallel.degradation_manager import (
            DegradationManager,
            DegradationLevel,
        )

        manager = DegradationManager()

        # 全功能模式
        self.assertTrue(manager.features["parallel_execution"])
        self.assertTrue(manager.features["transition_response"])

        # 手动降级
        manager.force_level(DegradationLevel.NO_PARALLEL)
        self.assertFalse(manager.features["parallel_execution"])
        self.assertTrue(manager.features["transition_response"])


class TestFeatureFlags(unittest.TestCase):
    """特性开关测试"""

    def test_default_flags(self):
        """测试默认特性开关"""
        from core.parallel.feature_flags import (
            FeatureFlagManager,
            FeatureFlag,
        )

        manager = FeatureFlagManager()

        # 默认应启用
        self.assertTrue(manager.is_enabled(FeatureFlag.STATE_MACHINE))
        self.assertTrue(manager.is_enabled(FeatureFlag.PERFORMANCE_TRACING))

    def test_enable_disable(self):
        """测试启用/禁用"""
        from core.parallel.feature_flags import (
            FeatureFlagManager,
            FeatureFlag,
        )

        manager = FeatureFlagManager()

        # 禁用
        manager.disable(FeatureFlag.PARALLEL_EXECUTION)
        self.assertFalse(manager.is_enabled(FeatureFlag.PARALLEL_EXECUTION))

        # 重新启用
        manager.enable(FeatureFlag.PARALLEL_EXECUTION)
        self.assertTrue(manager.is_enabled(FeatureFlag.PARALLEL_EXECUTION))


class TestModuleImports(unittest.TestCase):
    """模块导入测试"""

    def test_all_imports(self):
        """测试所有模块可正常导入"""
        from core.parallel import (
            # 状态机
            ConversationState,
            ConversationStateMachine,
            # 性能追踪
            PerformanceTracer,
            TracePhase,
            # 打断处理
            InterruptionHandler,
            InterruptionType,
            # 过渡响应
            TransitionResponseGenerator,
            TransitionResponse,
            # 安全防护
            SecurityGuardrails,
            SecurityLevel,
            # 优先级队列
            TTSPriorityQueue,
            PriorityLevel,
            # LLMCompiler
            LLMCompilerOrchestrator,
            ExecutionPlan,
            # 降级管理
            DegradationManager,
            DegradationLevel,
            # 特性开关
            FeatureFlagManager,
            FeatureFlag,
            # 并行处理器
            ParallelChatHandler,
        )

        # 验证导入成功
        self.assertIsNotNone(ConversationState)
        self.assertIsNotNone(ConversationStateMachine)
        self.assertIsNotNone(PerformanceTracer)
        self.assertIsNotNone(LLMCompilerOrchestrator)


if __name__ == "__main__":
    unittest.main()





