"""
LLMCompiler 编排器

基于 LLMCompiler (ICML 2024) 的三组件架构:
- Function Calling Planner: 规划执行计划
- Task Fetching Unit: 依赖分析与任务分发
- Parallel Executor: 并行执行

参考论文: https://arxiv.org/abs/2312.04511
"""

import asyncio
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Set, AsyncIterator, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from config.logger import setup_logging

from .state_machine import ConversationState, ConversationStateMachine
from .performance_tracer import PerformanceTracer, TracePhase
from .transition_generator import TransitionResponseGenerator
from .security_guardrails import SecurityGuardrails
from .interruption_handler import InterruptionHandler

TAG = __name__
logger = setup_logging()


class ToolStatus(Enum):
    """工具执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolTask:
    """工具任务"""
    id: str
    name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: ToolStatus = ToolStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration_ms(self) -> float:
        """执行耗时（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


@dataclass
class ExecutionPlan:
    """执行计划"""
    query: str
    intent: str
    tasks: List[ToolTask]
    stages: List[List[str]]  # 执行阶段，每个阶段包含可并行执行的任务ID
    transition_response: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class ExecutionResult:
    """执行结果"""
    plan: ExecutionPlan
    success: bool
    results: Dict[str, Any]
    errors: Dict[str, str]
    total_duration_ms: float
    parallel_factor: float  # 并行因子 = 串行耗时 / 实际耗时
    interrupted: bool = False


class FunctionCallingPlanner:
    """
    Function Calling Planner

    职责:
    - 分析用户意图
    - 选择需要调用的工具
    - 生成过渡响应
    """

    def __init__(
        self,
        transition_generator: TransitionResponseGenerator,
    ):
        self.transition_generator = transition_generator

    async def plan(
        self,
        query: str,
        available_tools: List[Dict[str, Any]],
        selected_tools: List[Dict[str, Any]],
    ) -> ExecutionPlan:
        """
        生成执行计划

        Args:
            query: 用户查询
            available_tools: 可用工具列表
            selected_tools: LLM 选择的工具调用

        Returns:
            ExecutionPlan
        """
        # 1. 提取意图
        intent = self._extract_intent(query, selected_tools)

        # 2. 创建任务列表
        tasks = []
        for tool_call in selected_tools:
            task = ToolTask(
                id=tool_call.get("id", str(uuid.uuid4().hex)),
                name=tool_call["name"],
                arguments=tool_call.get("arguments", {}),
            )
            tasks.append(task)

        # 3. 分析依赖关系
        self._analyze_dependencies(tasks)

        # 4. 生成执行阶段
        stages = self._build_execution_stages(tasks)

        # 5. 生成过渡响应（如果有工具调用）
        transition_response = None
        if tasks:
            first_tool = tasks[0].name
            transition = self.transition_generator.generate(
                tool_name=first_tool,
                query=query,
                arguments=tasks[0].arguments,
            )
            transition_response = transition.text

        return ExecutionPlan(
            query=query,
            intent=intent,
            tasks=tasks,
            stages=stages,
            transition_response=transition_response,
        )

    def _extract_intent(
        self,
        query: str,
        tools: List[Dict[str, Any]],
    ) -> str:
        """提取用户意图"""
        if not tools:
            return "general_query"

        # 根据工具名推断意图
        tool_names = [t["name"] for t in tools]
        if any("payment" in name for name in tool_names):
            return "payment_query"
        if any("order" in name for name in tool_names):
            return "order_query"
        if any("weather" in name for name in tool_names):
            return "weather_query"
        if any("music" in name or "play" in name for name in tool_names):
            return "media_control"
        if any("hass" in name or "iot" in name for name in tool_names):
            return "iot_control"

        return "tool_execution"

    def _analyze_dependencies(self, tasks: List[ToolTask]) -> None:
        """分析任务依赖关系"""
        # 简单的依赖规则：
        # 1. 验证类工具应先执行
        # 2. 查询类工具可并行
        # 3. 操作类工具依赖查询结果

        verify_tasks = []
        query_tasks = []
        action_tasks = []

        for task in tasks:
            name = task.name.lower()
            if "verify" in name or "auth" in name:
                verify_tasks.append(task)
            elif "query" in name or "get" in name or "search" in name or "check" in name:
                query_tasks.append(task)
            else:
                action_tasks.append(task)

        # 查询和操作依赖验证
        verify_ids = [t.id for t in verify_tasks]
        for task in query_tasks + action_tasks:
            task.dependencies = verify_ids

    def _build_execution_stages(
        self,
        tasks: List[ToolTask],
    ) -> List[List[str]]:
        """构建执行阶段"""
        if not tasks:
            return []

        # 使用拓扑排序构建阶段
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: len(t.dependencies) for t in tasks}
        stages = []

        while any(d >= 0 for d in in_degree.values()):
            # 找出所有入度为0的任务（可并行执行）
            stage = [
                task_id for task_id, degree in in_degree.items()
                if degree == 0
            ]

            if not stage:
                # 有循环依赖，强制添加剩余任务
                stage = [
                    task_id for task_id, degree in in_degree.items()
                    if degree > 0
                ]

            stages.append(stage)

            # 更新入度
            for task_id in stage:
                in_degree[task_id] = -1  # 已处理
                # 减少依赖此任务的其他任务的入度
                for other in tasks:
                    if task_id in other.dependencies:
                        in_degree[other.id] = max(0, in_degree[other.id] - 1)

        return stages


class TaskFetchingUnit:
    """
    Task Fetching Unit

    职责:
    - 依赖分析
    - 任务分发
    - 优先级排序
    """

    def dispatch(
        self,
        plan: ExecutionPlan,
    ) -> List[List[ToolTask]]:
        """
        分发任务

        Args:
            plan: 执行计划

        Returns:
            按阶段分组的任务列表
        """
        task_map = {t.id: t for t in plan.tasks}
        staged_tasks = []

        for stage_ids in plan.stages:
            stage_tasks = [task_map[tid] for tid in stage_ids if tid in task_map]
            staged_tasks.append(stage_tasks)

        return staged_tasks


class ParallelExecutor:
    """
    Parallel Executor

    职责:
    - 并行执行任务
    - 超时控制
    - 异常处理
    """

    def __init__(
        self,
        tool_executor: Any,  # UnifiedToolHandler
        security: SecurityGuardrails,
        default_timeout: float = 30.0,
    ):
        self.tool_executor = tool_executor
        self.security = security
        self.default_timeout = default_timeout

    async def execute_parallel(
        self,
        staged_tasks: List[List[ToolTask]],
        interrupt_checker: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        并行执行任务

        Args:
            staged_tasks: 按阶段分组的任务
            interrupt_checker: 打断检查函数

        Returns:
            执行结果字典
        """
        results = {}

        for stage_idx, stage in enumerate(staged_tasks):
            if not stage:
                continue

            # 检查是否被打断
            if interrupt_checker and interrupt_checker():
                logger.bind(tag=TAG).info("执行被打断")
                break

            logger.bind(tag=TAG).debug(
                f"执行阶段 {stage_idx + 1}/{len(staged_tasks)}: "
                f"{[t.name for t in stage]}"
            )

            # 并行执行当前阶段的所有任务
            stage_results = await self._execute_stage(stage, interrupt_checker)
            results.update(stage_results)

        return results

    async def _execute_stage(
        self,
        tasks: List[ToolTask],
        interrupt_checker: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """执行一个阶段的任务"""
        results = {}

        # 创建异步任务
        async_tasks = []
        for task in tasks:
            async_tasks.append(self._execute_task(task, interrupt_checker))

        # 并行执行
        completed = await asyncio.gather(*async_tasks, return_exceptions=True)

        # 收集结果
        for task, result in zip(tasks, completed):
            if isinstance(result, Exception):
                task.status = ToolStatus.FAILED
                task.error = str(result)
                results[task.id] = {"error": str(result)}
            else:
                task.status = ToolStatus.COMPLETED
                task.result = result
                results[task.id] = result

        return results

    async def _execute_task(
        self,
        task: ToolTask,
        interrupt_checker: Optional[callable] = None,
    ) -> Any:
        """执行单个任务"""
        task.status = ToolStatus.RUNNING
        task.start_time = time.time()

        try:
            # 安全验证
            allowed, error = await self.security.validate_and_confirm(
                task.name,
                task.arguments,
            )
            if not allowed:
                task.status = ToolStatus.FAILED
                task.error = error
                task.end_time = time.time()
                return {"error": error}

            # 检查打断
            if interrupt_checker and interrupt_checker():
                task.status = ToolStatus.CANCELLED
                task.end_time = time.time()
                return {"cancelled": True}

            # 执行工具
            result = await asyncio.wait_for(
                self.tool_executor.tool_manager.execute_tool(
                    task.name,
                    task.arguments,
                ),
                timeout=self.default_timeout,
            )

            task.end_time = time.time()
            return result

        except asyncio.TimeoutError:
            task.status = ToolStatus.FAILED
            task.error = "执行超时"
            task.end_time = time.time()
            return {"error": "执行超时"}

        except Exception as e:
            task.status = ToolStatus.FAILED
            task.error = str(e)
            task.end_time = time.time()
            logger.bind(tag=TAG).error(f"任务执行失败: {task.name} - {e}")
            return {"error": str(e)}


class LLMCompilerOrchestrator:
    """
    LLMCompiler 编排器

    基于 LLMCompiler 的三组件架构，实现并行 function calling。

    """

    def __init__(
        self,
        tool_handler: Any,  # UnifiedToolHandler
        session_id: str,
        enable_parallel: bool = True,
        enable_transition: bool = True,
        enable_security: bool = True,
    ):
        self.tool_handler = tool_handler
        self.session_id = session_id
        self.enable_parallel = enable_parallel
        self.enable_transition = enable_transition
        self.enable_security = enable_security

        # 初始化组件
        self.state_machine = ConversationStateMachine(session_id)
        self.tracer = PerformanceTracer(session_id)
        self.transition_generator = TransitionResponseGenerator()
        self.security = SecurityGuardrails(strict_mode=False)
        self.interruption_handler = InterruptionHandler()

        # 三组件架构
        self.planner = FunctionCallingPlanner(self.transition_generator)
        self.dispatcher = TaskFetchingUnit()
        self.executor = ParallelExecutor(
            tool_executor=tool_handler,
            security=self.security,
        )

    async def execute(
        self,
        query: str,
        tool_calls: List[Dict[str, Any]],
        on_transition: Optional[callable] = None,
    ) -> ExecutionResult:
        """
        执行查询

        Args:
            query: 用户查询
            tool_calls: LLM 返回的工具调用列表
            on_transition: 过渡响应回调

        Returns:
            ExecutionResult
        """
        start_time = time.time()
        self.tracer.start_trace()
        self.interruption_handler.reset()

        try:
            # 1. 状态转换
            self.state_machine.transition_to(ConversationState.PROCESSING_INTENT)

            # 2. Planner: 生成执行计划
            with self.tracer.trace(TracePhase.TOOL_PLANNING):
                available_tools = (
                    self.tool_handler.get_functions()
                    if self.tool_handler
                    else []
                )
                plan = await self.planner.plan(query, available_tools, tool_calls)

            # 3. 播放过渡响应（并行 Track 1）
            transition_task = None
            if self.enable_transition and plan.transition_response and on_transition:
                self.state_machine.transition_to(ConversationState.PLAYING_TRANSITION)
                with self.tracer.trace(TracePhase.TRANSITION_RESPONSE):
                    transition_task = asyncio.create_task(
                        self._play_transition(plan.transition_response, on_transition)
                    )
                    # 记录 TTFR
                    self.tracer.record_ttfr()

            # 4. Dispatcher: 分发任务
            staged_tasks = self.dispatcher.dispatch(plan)

            # 5. Executor: 并行执行（并行 Track 2）
            self.state_machine.transition_to(ConversationState.EXECUTING_TOOLS)
            with self.tracer.trace(TracePhase.TOOL_EXECUTION):
                results = await self.executor.execute_parallel(
                    staged_tasks,
                    interrupt_checker=lambda: self.interruption_handler.is_interrupted,
                )

            # 6. 等待过渡响应完成
            if transition_task:
                await transition_task

            # 7. 计算性能指标
            total_duration = (time.time() - start_time) * 1000
            parallel_factor = self._calculate_parallel_factor(plan.tasks, total_duration)

            # 8. 状态转换
            self.state_machine.transition_to(ConversationState.GENERATING_RESPONSE)

            # 构建结果
            errors = {
                task.id: task.error
                for task in plan.tasks
                if task.status == ToolStatus.FAILED
            }

            return ExecutionResult(
                plan=plan,
                success=len(errors) == 0,
                results=results,
                errors=errors,
                total_duration_ms=total_duration,
                parallel_factor=parallel_factor,
                interrupted=self.interruption_handler.is_interrupted,
            )

        except Exception as e:
            self.state_machine.transition_to(ConversationState.ERROR)
            logger.bind(tag=TAG).error(f"执行失败: {e}")
            raise

        finally:
            metrics = self.tracer.finish_trace()
            logger.bind(tag=TAG).info(
                f"执行完成: TTFR={metrics.ttfr_ms:.1f}ms, "
                f"总耗时={metrics.total_duration_ms:.1f}ms"
            )

    async def _play_transition(
        self,
        text: str,
        callback: callable,
    ) -> None:
        """播放过渡响应"""
        try:
            await callback(text)
        except Exception as e:
            logger.bind(tag=TAG).error(f"过渡响应播放失败: {e}")

    def _calculate_parallel_factor(
        self,
        tasks: List[ToolTask],
        actual_duration: float,
    ) -> float:
        """计算并行因子"""
        if not tasks or actual_duration <= 0:
            return 1.0

        # 计算串行耗时
        serial_duration = sum(
            task.duration_ms for task in tasks
            if task.duration_ms > 0
        )

        if serial_duration <= 0:
            return 1.0

        return serial_duration / actual_duration

    def handle_interruption(self, user_speech: str) -> bool:
        """处理用户打断"""
        return asyncio.run(
            self.interruption_handler.handle_interruption(user_speech)
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "session_id": self.session_id,
            "state_machine": self.state_machine.get_statistics(),
            "performance": self.tracer.get_all_statistics(),
            "transition": self.transition_generator.get_statistics(),
            "security": self.security.get_statistics(),
            "interruption": self.interruption_handler.get_statistics(),
        }


