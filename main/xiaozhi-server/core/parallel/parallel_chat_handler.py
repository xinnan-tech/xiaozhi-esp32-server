"""
并行优化聊天处理器

整合所有并行优化组件，提供增强版的 chat() 方法。
兼容现有 ConnectionHandler 接口，可通过特性开关启用/禁用。

"""

import asyncio
import json
import time
import uuid
from typing import Optional, Any, Dict, List, Callable
from config.logger import setup_logging

from .state_machine import ConversationState, ConversationStateMachine
from .performance_tracer import PerformanceTracer, TracePhase
from .interruption_handler import InterruptionHandler, InterruptionConfig
from .transition_generator import TransitionResponseGenerator
from .security_guardrails import SecurityGuardrails
from .llm_compiler_orchestrator import LLMCompilerOrchestrator
from .degradation_manager import DegradationManager, DegradationLevel, get_degradation_manager
from .feature_flags import FeatureFlag, get_feature_manager
from .priority_queue import PriorityLevel

TAG = __name__
logger = setup_logging()


class ParallelChatHandler:
    """
    并行优化聊天处理器

    使用方式:
        handler = ParallelChatHandler(conn)
        await handler.chat(query)
    """

    def __init__(self, conn: Any):
        """
        初始化并行聊天处理器

        Args:
            conn: ConnectionHandler 实例
        """
        self.conn = conn
        self.session_id = conn.session_id
        self.logger = conn.logger

        # 获取全局管理器
        self.feature_manager = get_feature_manager()
        self.degradation_manager = get_degradation_manager()

        # 初始化组件
        self._init_components()

        # 回调
        self._on_transition: Optional[Callable[[str], None]] = None
        self._on_response: Optional[Callable[[str], None]] = None

    def _init_components(self) -> None:
        """初始化各组件"""
        # 状态机
        if self.feature_manager.is_enabled(FeatureFlag.STATE_MACHINE):
            self.state_machine = ConversationStateMachine(
                session_id=self.session_id,
                on_state_change=self._on_state_change,
            )
        else:
            self.state_machine = None

        # 性能追踪
        if self.feature_manager.is_enabled(FeatureFlag.PERFORMANCE_TRACING):
            self.tracer = PerformanceTracer(self.session_id)
        else:
            self.tracer = None

        # 打断处理
        if self.feature_manager.is_enabled(FeatureFlag.SMART_INTERRUPTION):
            self.interruption_handler = InterruptionHandler(
                config=InterruptionConfig(target_response_ms=400),
                on_interrupt=self._handle_interrupt,
            )
        else:
            self.interruption_handler = None

        # 过渡响应
        if self.feature_manager.is_enabled(FeatureFlag.TRANSITION_RESPONSE):
            self.transition_generator = TransitionResponseGenerator()
        else:
            self.transition_generator = None

        # 安全防护
        if self.feature_manager.is_enabled(FeatureFlag.SECURITY_GUARDRAILS):
            self.security = SecurityGuardrails(
                strict_mode=False,
                on_confirm_request=self._request_user_confirmation,
            )
        else:
            self.security = None

        # LLMCompiler 编排器
        if (
            self.feature_manager.is_enabled(FeatureFlag.LLM_COMPILER)
            and hasattr(self.conn, 'func_handler')
            and self.conn.func_handler
        ):
            self.orchestrator = LLMCompilerOrchestrator(
                tool_handler=self.conn.func_handler,
                session_id=self.session_id,
                enable_parallel=self.feature_manager.is_enabled(FeatureFlag.PARALLEL_EXECUTION),
                enable_transition=self.feature_manager.is_enabled(FeatureFlag.TRANSITION_RESPONSE),
                enable_security=self.feature_manager.is_enabled(FeatureFlag.SECURITY_GUARDRAILS),
            )
        else:
            self.orchestrator = None

    def _on_state_change(
        self,
        old_state: ConversationState,
        new_state: ConversationState,
    ) -> None:
        """状态变更回调"""
        self.logger.bind(tag=TAG).debug(
            f"[{self.session_id}] 状态: {old_state.value} → {new_state.value}"
        )

    def _handle_interrupt(self) -> None:
        """打断处理回调"""
        self.logger.bind(tag=TAG).info(f"[{self.session_id}] 收到打断信号")
        if hasattr(self.conn, 'client_abort'):
            self.conn.client_abort = True
        if hasattr(self.conn, 'clear_queues'):
            self.conn.clear_queues()

    async def _request_user_confirmation(self, prompt: str) -> str:
        """请求用户确认"""
        # 播放确认提示
        if hasattr(self.conn, 'tts') and self.conn.tts:
            from core.providers.tts.dto.dto import ContentType
            self.conn.tts.tts_one_sentence(
                self.conn,
                ContentType.TEXT,
                content_detail=prompt,
            )

        # 等待用户响应（简化实现，实际需要集成 ASR）
        # TODO: 集成实际的 ASR 等待逻辑
        await asyncio.sleep(5.0)
        return "取消"  # 默认取消

    async def chat(self, query: str, depth: int = 0) -> bool:
        """
        增强版聊天方法

        Args:
            query: 用户查询
            depth: 递归深度（用于工具调用后的再次查询）

        Returns:
            bool: 是否成功
        """
        start_time = time.time()

        # 记录请求开始
        self.logger.bind(tag=TAG).info(f"[{self.session_id}] 并行聊天开始: {query}")

        # 检查是否使用并行优化
        if not self._should_use_parallel():
            self.logger.bind(tag=TAG).debug("并行优化已禁用，使用原始 chat 方法")
            return self.conn.chat(query, depth)

        try:
            # 开始追踪
            if self.tracer:
                self.tracer.start_trace()

            # 状态转换
            if self.state_machine:
                self.state_machine.transition_to(ConversationState.PROCESSING_INTENT)

            # 重置打断状态
            if self.interruption_handler:
                self.interruption_handler.reset()

            # 初始化会话
            if depth == 0:
                self.conn.sentence_id = str(uuid.uuid4().hex)
                self.conn.llm_finish_task = False
                self.conn.dialogue.put_message("user", query)
                self._send_first_message()

            # 获取 LLM 响应
            result = await self._process_with_llm(query, depth)

            # 记录性能
            duration_ms = (time.time() - start_time) * 1000
            self.degradation_manager.record_request(
                latency_ms=duration_ms,
                success=result,
            )

            if self.tracer:
                metrics = self.tracer.finish_trace()
                self.logger.bind(tag=TAG).info(
                    f"[{self.session_id}] 聊天完成: "
                    f"TTFR={metrics.ttfr_ms:.1f}ms, "
                    f"总耗时={metrics.total_duration_ms:.1f}ms"
                )

            return result

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"[{self.session_id}] 聊天错误: {e}")

            # 记录错误
            self.degradation_manager.record_request(
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
            )

            # 状态转换到错误
            if self.state_machine:
                self.state_machine.transition_to(ConversationState.ERROR)

            # 降级到原始方法
            self.logger.bind(tag=TAG).info("降级到原始 chat 方法")
            return self.conn.chat(query, depth)

        finally:
            if self.state_machine:
                self.state_machine.transition_to(ConversationState.IDLE)
            self.conn.llm_finish_task = True

    def _should_use_parallel(self) -> bool:
        """检查是否应该使用并行优化"""
        # 检查特性开关
        if not self.feature_manager.is_enabled(FeatureFlag.LLM_COMPILER):
            return False

        # 检查降级状态
        if self.degradation_manager.current_level >= DegradationLevel.MINIMAL:
            return False

        # 检查必要组件
        if not hasattr(self.conn, 'func_handler') or not self.conn.func_handler:
            return False

        return True

    def _send_first_message(self) -> None:
        """发送首条消息标记"""
        from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType

        if hasattr(self.conn, 'tts') and self.conn.tts:
            self.conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.conn.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )

    async def _process_with_llm(self, query: str, depth: int) -> bool:
        """使用 LLM 处理查询"""
        from core.utils.dialogue import Message
        from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType

        # 获取对话历史
        memory_str = None
        if self.conn.memory:
            try:
                memory_str = await self.conn.memory.query_memory(query)
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"记忆查询失败: {e}")

        dialogue_history = self.conn.dialogue.get_llm_dialogue_with_memory(
            memory_str, self.conn.config.get("voiceprint", {})
        )

        # 获取可用函数
        functions = None
        if self.conn.intent_type == "function_call" and hasattr(self.conn, 'func_handler'):
            functions = self.conn.func_handler.get_functions()

        # 调用 LLM
        if self.tracer:
            with self.tracer.trace(TracePhase.RESPONSE_GENERATION):
                llm_responses = await self._call_llm(dialogue_history, functions)
        else:
            llm_responses = await self._call_llm(dialogue_history, functions)

        # 处理响应
        return await self._process_llm_response(query, llm_responses, functions, depth)

    async def _call_llm(
        self,
        dialogue_history: List[Dict],
        functions: Optional[List[Dict]],
    ) -> Any:
        """调用 LLM"""
        loop = asyncio.get_event_loop()

        if self.conn.intent_type == "function_call" and functions:
            return await loop.run_in_executor(
                None,
                lambda: list(self.conn.llm.response_with_functions(
                    self.conn.session_id,
                    dialogue_history,
                    functions=functions,
                ))
            )
        else:
            return await loop.run_in_executor(
                None,
                lambda: list(self.conn.llm.response(
                    self.conn.session_id,
                    dialogue_history,
                ))
            )

    async def _process_llm_response(
        self,
        query: str,
        llm_responses: List,
        functions: Optional[List[Dict]],
        depth: int,
    ) -> bool:
        """处理 LLM 响应"""
        from core.utils.dialogue import Message
        from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
        from core.utils.util import extract_json_from_string
        from plugins_func.register import Action

        response_message = []
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""

        for response in llm_responses:
            # 检查打断
            if self.conn.client_abort:
                break

            if self.conn.intent_type == "function_call" and functions:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None

                if content:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    tool_call_flag = True

                if tools_call:
                    tool_call_flag = True
                    if tools_call[0].id:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response

            # 发送文本到 TTS（非工具调用时）
            if content and not tool_call_flag:
                response_message.append(content)

                # 记录 TTFR
                if self.tracer and len(response_message) == 1:
                    self.tracer.record_ttfr()

                self.conn.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=self.conn.sentence_id,
                        sentence_type=SentenceType.MIDDLE,
                        content_type=ContentType.TEXT,
                        content_detail=content,
                    )
                )

        # 处理工具调用
        if tool_call_flag:
            return await self._handle_tool_call(
                query, function_name, function_id, function_arguments,
                content_arguments, response_message, depth
            )

        # 存储对话
        if response_message:
            text_buff = "".join(response_message)
            self.conn.tts_MessageText = text_buff
            self.conn.dialogue.put(Message(role="assistant", content=text_buff))

        # 发送结束标记
        if depth == 0:
            self.conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.conn.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )

        return True

    async def _handle_tool_call(
        self,
        query: str,
        function_name: Optional[str],
        function_id: Optional[str],
        function_arguments: str,
        content_arguments: str,
        response_message: List[str],
        depth: int,
    ) -> bool:
        """处理工具调用"""
        from core.utils.dialogue import Message
        from core.utils.util import extract_json_from_string
        from plugins_func.register import Action

        # 解析函数调用
        if not function_id:
            extracted = extract_json_from_string(content_arguments)
            if extracted:
                try:
                    args_json = json.loads(extracted)
                    function_name = args_json["name"]
                    function_arguments = json.dumps(
                        args_json["arguments"], ensure_ascii=False
                    )
                    function_id = str(uuid.uuid4().hex)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"解析函数调用失败: {e}")
                    return False

        if not function_name:
            return False

        self.logger.bind(tag=TAG).info(
            f"工具调用: {function_name}, 参数: {function_arguments}"
        )

        # 使用编排器执行（如果可用）
        if self.orchestrator and self.feature_manager.is_enabled(FeatureFlag.PARALLEL_EXECUTION):
            tool_calls = [{
                "id": function_id,
                "name": function_name,
                "arguments": json.loads(function_arguments) if function_arguments else {},
            }]

            # 过渡响应回调
            async def on_transition(text: str):
                from core.providers.tts.dto.dto import ContentType
                if self.tracer:
                    self.tracer.record_ttfr()
                self.conn.tts.tts_one_sentence(
                    self.conn, ContentType.TEXT, content_detail=text
                )

            # 执行
            if self.tracer:
                with self.tracer.trace(TracePhase.TOOL_EXECUTION):
                    result = await self.orchestrator.execute(
                        query, tool_calls, on_transition
                    )
            else:
                result = await self.orchestrator.execute(query, tool_calls, on_transition)

            # 处理结果
            if result.success:
                tool_result = next(iter(result.results.values()), None)
                if tool_result:
                    return await self._handle_tool_result(
                        tool_result, function_name, function_id,
                        function_arguments, query, depth
                    )

        else:
            # 使用原始方法
            function_call_data = {
                "name": function_name,
                "id": function_id,
                "arguments": function_arguments,
            }

            # 生成过渡响应
            if self.transition_generator:
                transition = self.transition_generator.generate(
                    function_name, query,
                    json.loads(function_arguments) if function_arguments else {}
                )
                if transition.text:
                    if self.tracer:
                        self.tracer.record_ttfr()
                    from core.providers.tts.dto.dto import ContentType
                    self.conn.tts.tts_one_sentence(
                        self.conn, ContentType.TEXT, content_detail=transition.text
                    )

            # 执行工具
            result = await self.conn.func_handler.handle_llm_function_call(
                self.conn, function_call_data
            )

            return await self._handle_tool_result(
                result, function_name, function_id,
                function_arguments, query, depth
            )

        return True

    async def _handle_tool_result(
        self,
        result: Any,
        function_name: str,
        function_id: str,
        function_arguments: str,
        query: str,
        depth: int,
    ) -> bool:
        """处理工具执行结果"""
        from core.utils.dialogue import Message
        from core.providers.tts.dto.dto import ContentType
        from plugins_func.register import Action

        if not result:
            return False

        if result.action == Action.RESPONSE:
            text = result.response
            if text:
                self.conn.tts.tts_one_sentence(
                    self.conn, ContentType.TEXT, content_detail=text
                )
                self.conn.dialogue.put(Message(role="assistant", content=text))

        elif result.action == Action.REQLLM:
            text = result.result
            if text:
                # 记录工具调用
                self.conn.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[{
                            "id": function_id,
                            "function": {
                                "arguments": function_arguments or "{}",
                                "name": function_name,
                            },
                            "type": "function",
                            "index": 0,
                        }],
                    )
                )
                self.conn.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=function_id,
                        content=text,
                    )
                )
                # 递归调用
                return await self.chat(text, depth=depth + 1)

        elif result.action in [Action.NOTFOUND, Action.ERROR]:
            text = result.response or result.result
            if text:
                self.conn.tts.tts_one_sentence(
                    self.conn, ContentType.TEXT, content_detail=text
                )
                self.conn.dialogue.put(Message(role="assistant", content=text))

        return True

    async def handle_user_interruption(self, speech: str) -> bool:
        """处理用户打断"""
        if not self.interruption_handler:
            return False

        # TTS 停止回调
        def stop_tts():
            if hasattr(self.conn, 'clear_queues'):
                self.conn.clear_queues()

        # 即时响应回调
        async def immediate_response(text: str):
            from core.providers.tts.dto.dto import ContentType
            if text and hasattr(self.conn, 'tts'):
                self.conn.tts.tts_one_sentence(
                    self.conn, ContentType.TEXT, content_detail=text
                )

        return await self.interruption_handler.handle_interruption(
            speech,
            tts_stop_callback=stop_tts,
            immediate_response_callback=lambda t: asyncio.create_task(immediate_response(t)),
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "session_id": self.session_id,
            "features": self.feature_manager.get_all_flags(),
            "degradation_level": self.degradation_manager.current_level.name,
        }

        if self.state_machine:
            stats["state_machine"] = self.state_machine.get_statistics()

        if self.tracer:
            stats["performance"] = self.tracer.get_all_statistics()

        if self.interruption_handler:
            stats["interruption"] = self.interruption_handler.get_statistics()

        if self.transition_generator:
            stats["transition"] = self.transition_generator.get_statistics()

        if self.security:
            stats["security"] = self.security.get_statistics()

        return stats


