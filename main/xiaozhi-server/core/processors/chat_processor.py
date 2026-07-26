import json
import uuid
import asyncio
import re
from typing import Any, Dict
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.dialogue import Message, Dialogue
from core.utils.util import remove_punctuation_and_length
from core.utils import textUtils
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from core.components.component_manager import ComponentType
from plugins_func.register import Action, ActionResponse
from config.logger import setup_logging

logger = setup_logging()

DIRECT_ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "direct_answer",
        "description": "当请求不匹配其他工具时直接回复用户。",
        "parameters": {
            "type": "object",
            "properties": {"response": {"type": "string"}},
            "required": ["response"],
        },
    },
}


class ChatProcessor(MessageProcessor):
    """聊天处理器：完整迁移intentHandler.py的所有功能"""

    def __init__(self):
        # 会话对话历史管理
        self._dialogues: Dict[str, Dialogue] = {}

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理聊天消息"""
        # 这个处理器不直接处理原始消息，而是被其他处理器调用
        return False

    async def handle_chat(self, context: SessionContext, transport: TransportInterface, text: str, skip_intent: bool = False, depth: int = 0):
        """处理聊天请求 - 完整迁移自handle_user_intent"""
        try:
            logger.info(f"开始处理聊天: session_id={context.session_id}, text={text[:50]}...")
            if not skip_intent:
                # 首先进行意图处理
                intent_handled = await self.handle_user_intent(context, transport, text)
                if intent_handled:
                    logger.info("意图已处理，结束聊天流程")
                    return
            else:
                logger.info("跳过意图处理，直接进入常规聊天")

            # 如果意图未处理，进行常规聊天
            logger.info("进入常规聊天流程")
            await self._regular_chat(context, transport, text, depth=depth)

        except Exception as e:
            logger.error(f"处理聊天失败: {e}")
            await self._send_error(transport, "聊天处理失败，请重试")
            await self._finish_tts_turn(context, transport)

    async def handle_user_intent(self, context: SessionContext, transport: TransportInterface, text: str):
        """处理用户意图 - 完整迁移自intentHandler.py"""
        # 预处理输入文本，处理可能的JSON格式
        try:
            if text.strip().startswith('{') and text.strip().endswith('}'):
                parsed_data = json.loads(text)
                if isinstance(parsed_data, dict) and "content" in parsed_data:
                    text = parsed_data["content"]  # 提取content用于意图分析
                    context.current_speaker = parsed_data.get("speaker")  # 保留说话人信息
        except (json.JSONDecodeError, TypeError):
            pass

        # 检查是否有明确的退出命令
        _, filtered_text = remove_punctuation_and_length(text)
        if await self._check_direct_exit(context, transport, filtered_text):
            return True

        # 检查是否是唤醒词
        if await self._check_wakeup_words(context, transport, filtered_text):
            return True

        if context.intent_type == "function_call":
            # 使用支持function calling的聊天方法,不再进行意图分析
            return False

        # 使用LLM进行意图分析
        intent_result = await self._analyze_intent_with_llm(context, text)
        if not intent_result:
            return False

        # 会话开始时生成sentence_id
        context.sentence_id = str(uuid.uuid4().hex)

        # 处理各种意图
        return await self._process_intent_result(context, transport, intent_result, text)

    def _get_dialogue(self, session_id: str) -> Dialogue:
        """获取或创建对话历史"""
        if session_id not in self._dialogues:
            self._dialogues[session_id] = Dialogue()
        return self._dialogues[session_id]

    async def _get_memory_context(self, context: SessionContext, query: str) -> str:
        """获取记忆上下文"""
        try:
            memory_component = await self._get_component(context, ComponentType.MEMORY)
            if memory_component and hasattr(memory_component, 'memory_instance'):
                memory_instance = memory_component.memory_instance
                if hasattr(memory_instance, 'query_memory'):
                    return await memory_instance.query_memory(query)
        except Exception as e:
            logger.warning(f"获取记忆上下文失败: {e}")

        return None

    async def _generate_llm_response(self, context: SessionContext, transport: TransportInterface,
                                   llm_instance, dialogue_context: list, dialogue: Dialogue):
        """生成LLM回复"""
        try:
            logger.info("开始生成LLM回复")
            # 初始化sentence_id并发送TTS FIRST标记（模拟原connection.py第692-700行）
            if not context.sentence_id:
                context.sentence_id = str(uuid.uuid4().hex)

            # 发送TTS开始标记
            await self._send_tts_first_marker(context)

            # 检查是否支持流式响应
            if hasattr(llm_instance, 'response'):
                # 使用流式响应
                response_generator = llm_instance.response(context.session_id, dialogue_context)

                response_parts = []
                first_chunk = True
                async for response_part in self._async_generator_wrapper(response_generator):
                    if context.abort_requested:
                        break

                    if response_part and len(response_part) > 0:
                        response_parts.append(response_part)
                        if first_chunk:
                            logger.info("收到LLM首段回复")
                            self._schedule_emotion(context, response_part)
                            first_chunk = False

                        # 原架构不发送流式响应给前端，直接进行TTS处理
                        # 将响应片段放入TTS队列进行语音合成
                        await self._process_response_part_for_tts(context, response_part)

                # 完整回复
                full_response = "".join(response_parts)
                if full_response:
                    # 添加助手回复到对话历史
                    dialogue.put(Message(role="assistant", content=full_response))

                    # 原架构不发送response_complete给前端，只进行TTS处理
                    # 发送TTS结束标记
                    await self._finalize_tts_response(context, full_response)

                    logger.info(f"LLM回复完成: {full_response[:100]}...")
                elif not context.abort_requested:
                    logger.warning("LLM未生成可播放内容，结束当前TTS流")
                    await self._finish_tts_turn(context, transport)

            else:
                logger.warning("LLM实例不支持流式响应")
                await self._finish_tts_turn(context, transport)

        except Exception as e:
            logger.error(f"生成LLM回复失败: {e}")
            await self._send_error(transport, "生成回复失败")
            await self._finish_tts_turn(context, transport)

    async def _generate_llm_response_with_tools(
        self,
        context: SessionContext,
        transport: TransportInterface,
        llm_instance,
        dialogue_context: list,
        dialogue: Dialogue,
        depth: int = 0,
    ):
        """生成LLM回复（支持function_call）"""
        from core.utils.util import extract_json_from_string

        MAX_DEPTH = 5
        force_final_answer = depth >= MAX_DEPTH

        functions = None
        if context.intent_type == "function_call" and context.func_handler and not force_final_answer:
            functions = list(context.func_handler.get_functions() or [])
            if depth == 0:
                functions.append(DIRECT_ANSWER_TOOL)

        try:
            # 工具结果递归沿用同一轮 TTS，仅最外层发送 FIRST。
            if depth == 0:
                await self._send_tts_first_marker(context)

            responses = llm_instance.response_with_functions(
                context.session_id,
                dialogue_context,
                functions=functions,
            )
        except Exception as e:
            logger.error(f"LLM工具调用失败: {e}")
            await self._finish_tts_turn(context, transport)
            return

        response_message = []
        tool_call_flag = False
        tool_calls_list = []
        content_arguments = ""
        first_chunk = True

        async for response in self._async_generator_wrapper(responses):
            if context.abort_requested:
                break
            if context.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if isinstance(response, dict) and "content" in response:
                    content = response.get("content")
                    tools_call = None
                if content:
                    content_arguments += content
                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    tool_call_flag = True
                if tools_call:
                    tool_call_flag = True
                    self._merge_tool_calls(tool_calls_list, tools_call)
                    for tool_call in tool_calls_list:
                        if tool_call.get("name") != "direct_answer":
                            continue
                        direct_text = self._extract_direct_answer_response(
                            tool_call.get("arguments", "")
                        )
                        sent_len = tool_call.get("_da_sent", 0)
                        safe_end = max(sent_len, len(direct_text) - 5)
                        if safe_end > sent_len:
                            delta = self._clean_response_garbage(
                                direct_text[sent_len:safe_end]
                            )
                            if delta:
                                await self._process_response_part_for_tts(
                                    context, delta
                                )
                            tool_call["_da_sent"] = safe_end
            else:
                content = response

            if content:
                if first_chunk:
                    logger.info("收到LLM首段回复")
                    self._schedule_emotion(context, content)
                    first_chunk = False
                if not tool_call_flag:
                    response_message.append(content)
                    await self._process_response_part_for_tts(context, content)

        # 处理function_call
        if tool_call_flag:
            if not tool_calls_list and content_arguments:
                a = extract_json_from_string(content_arguments)
                if a:
                    try:
                        content_arguments_json = json.loads(a)
                        tool_calls_list.append(
                            {
                                "id": str(uuid.uuid4().hex),
                                "name": content_arguments_json["name"],
                                "arguments": json.dumps(
                                    content_arguments_json["arguments"],
                                    ensure_ascii=False,
                                ),
                            }
                        )
                    except Exception:
                        response_message.append(a)
                else:
                    response_message.append(content_arguments)

            if response_message:
                text_buff = "".join(response_message)
                dialogue.put(Message(role="assistant", content=text_buff))
                response_message.clear()

            direct_answer_calls = [
                call for call in tool_calls_list if call.get("name") == "direct_answer"
            ]
            tool_calls_list = [
                call for call in tool_calls_list if call.get("name") != "direct_answer"
            ]
            for direct_call in direct_answer_calls:
                direct_text = self._clean_response_garbage(
                    self._extract_direct_answer_response(
                        direct_call.get("arguments", "")
                    )
                )
                if direct_text:
                    dialogue.put(Message(role="assistant", content=direct_text))
                    remaining = direct_text[direct_call.get("_da_sent", 0):]
                    if remaining:
                        await self._process_response_part_for_tts(
                            context, remaining
                        )

            if direct_answer_calls and not tool_calls_list:
                direct_text = "".join(
                    self._clean_response_garbage(
                        self._extract_direct_answer_response(
                            call.get("arguments", "")
                        )
                    )
                    for call in direct_answer_calls
                )
                await self._finalize_tts_response(context, direct_text)
                return

            if not tool_calls_list:
                fallback_text = "工具调用格式有误，请再试一次。"
                dialogue.put(Message(role="assistant", content=fallback_text))
                await self._process_response_part_for_tts(context, fallback_text)
                await self._finalize_tts_response(context, fallback_text)
                return

            from core.processors.report_processor import ReportProcessor

            reporter = ReportProcessor()
            timeout = max(1, int(context.config.get("tool_call_timeout", 30)))

            async def execute_tool(tool_call_data):
                try:
                    tool_input = json.loads(tool_call_data.get("arguments") or "{}")
                except (json.JSONDecodeError, TypeError):
                    tool_input = {}
                reporter.enqueue_tool_report(
                    context, tool_call_data.get("name", ""), tool_input
                )
                try:
                    result = await asyncio.wait_for(
                        context.func_handler.handle_llm_function_call(
                            context, tool_call_data
                        ),
                        timeout=timeout,
                    )
                except Exception as error:
                    logger.error(
                        f"工具调用失败: {tool_call_data.get('name')}, error={error}"
                    )
                    result = ActionResponse(
                        action=Action.ERROR,
                        result="工具调用超时或失败，请稍后再试。",
                        response="工具调用超时或失败，请稍后再试。",
                    )
                reporter.enqueue_tool_report(
                    context,
                    tool_call_data.get("name", ""),
                    tool_input,
                    str(result.result) if result.result is not None else None,
                    report_tool_call=False,
                )
                return result, tool_call_data

            tool_results = await asyncio.gather(
                *(execute_tool(tool_call_data) for tool_call_data in tool_calls_list)
            )

            if tool_results:
                await self._handle_function_result(context, transport, tool_results, depth=depth)
            return

        # 无工具调用，正常结束
        if response_message:
            full_response = "".join(response_message)
            dialogue.put(Message(role="assistant", content=full_response))
            await self._finalize_tts_response(context, full_response)
        elif not context.abort_requested:
            logger.warning("LLM工具流程未生成可播放内容，结束当前TTS流")
            await self._finish_tts_turn(context, transport)

    async def _handle_function_result(self, context: SessionContext, transport: TransportInterface, tool_results, depth: int):
        need_llm_tools = []
        completed_text = []
        record_tools = []
        for result, tool_call_data in tool_results:
            if result.action in [Action.RESPONSE, Action.NOTFOUND, Action.ERROR]:
                text = result.response if result.response else result.result
                if text:
                    completed_text.append(text)
                    context.dialogue.put(Message(role="assistant", content=text))
                    await self._process_response_part_for_tts(context, text)
            elif result.action == Action.REQLLM:
                need_llm_tools.append((result, tool_call_data))
            elif result.action == Action.RECORD:
                record_tools.append((result, tool_call_data))

        if record_tools:
            context.dialogue.put(
                Message(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": tool_call_data["id"],
                            "function": {
                                "arguments": tool_call_data.get("arguments") or "{}",
                                "name": tool_call_data["name"],
                            },
                            "type": "function",
                            "index": index,
                        }
                        for index, (_, tool_call_data) in enumerate(record_tools)
                    ],
                )
            )
            for result, tool_call_data in record_tools:
                context.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=tool_call_data["id"],
                        content=result.result or "",
                    )
                )
                if result.response:
                    completed_text.append(result.response)
                    context.dialogue.put(
                        Message(role="assistant", content=result.response)
                    )
                    await self._process_response_part_for_tts(
                        context, result.response
                    )

        if not need_llm_tools:
            await self._finalize_tts_response(
                context, "".join(completed_text)
            )
            return

        all_tool_calls = [
            {
                "id": tool_call_data["id"],
                "function": {
                    "arguments": "{}" if tool_call_data["arguments"] == "" else tool_call_data["arguments"],
                    "name": tool_call_data["name"],
                },
                "type": "function",
                "index": idx,
            }
            for idx, (_, tool_call_data) in enumerate(need_llm_tools)
        ]
        context.dialogue.put(Message(role="assistant", tool_calls=all_tool_calls))

        for result, tool_call_data in need_llm_tools:
            text = result.result
            if text:
                context.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=tool_call_data.get("id", str(uuid.uuid4())),
                        content=text,
                    )
                )

        # 继续下一轮工具结果回答
        await self._regular_chat(context, transport, "", depth=depth + 1)

    def _merge_tool_calls(self, tool_calls_list, tools_call):
        """合并工具调用列表（从旧版迁移）"""
        for tool_call in tools_call:
            tool_index = getattr(tool_call, "index", None)
            if tool_index is None:
                if tool_call.function.name:
                    tool_index = len(tool_calls_list)
                else:
                    tool_index = len(tool_calls_list) - 1 if tool_calls_list else 0

            if tool_index >= len(tool_calls_list):
                tool_calls_list.append({"id": "", "name": "", "arguments": ""})

            if tool_call.id:
                tool_calls_list[tool_index]["id"] = tool_call.id
            if tool_call.function.name:
                tool_calls_list[tool_index]["name"] = tool_call.function.name
            if tool_call.function.arguments:
                tool_calls_list[tool_index]["arguments"] += tool_call.function.arguments

    @staticmethod
    def _extract_direct_answer_response(arguments):
        if not arguments:
            return ""
        try:
            parsed = json.loads(arguments)
            if isinstance(parsed, dict):
                return str(parsed.get("response") or "")
        except (json.JSONDecodeError, TypeError):
            pass

        for marker in ('"response": "', '"response":"'):
            start = arguments.find(marker)
            if start >= 0:
                value = arguments[start + len(marker):]
                if value.endswith('"}'):
                    value = value[:-2]
                elif value.endswith('"'):
                    value = value[:-1]
                return value.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        return ""

    @staticmethod
    def _clean_response_garbage(text):
        if not text:
            return text
        garbage_chars = frozenset('\")\'}）')
        cleaned = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) <= 8 and all(
                char in garbage_chars for char in stripped
            ):
                continue
            cleaned.append(line)
        return re.sub(r'["\'}\]]+$', "", "\n".join(cleaned).rstrip()).rstrip()

    @staticmethod
    def _schedule_emotion(context: SessionContext, content: str) -> None:
        if not content or not (getattr(context, "features", None) or {}).get(
            "emoji", True
        ):
            return
        coroutine = textUtils.get_emotion(context, content)
        if hasattr(context, "create_background_task"):
            context.create_background_task(coroutine, turn_scoped=True)
        else:
            asyncio.create_task(coroutine)

    async def _async_generator_wrapper(self, generator):
        """将同步生成器包装为异步生成器"""
        try:
            def next_item():
                try:
                    return True, next(generator)
                except StopIteration:
                    return False, None

            while True:
                has_item, item = await asyncio.to_thread(next_item)
                if not has_item:
                    break
                yield item
        except Exception as e:
            logger.error(f"生成器包装失败: {e}")

    async def _send_tts_first_marker(self, context: SessionContext):
        """发送TTS开始标记"""
        try:
            tts_component = await self._get_component(context, ComponentType.TTS)
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                return

            tts_instance = tts_component.tts_instance
            if not tts_instance or not hasattr(tts_instance, 'tts_text_queue'):
                return

            # 发送TTS开始标记（模拟原connection.py第694-700行）
            tts_instance.tts_text_queue.put(TTSMessageDTO(
                sentence_id=context.sentence_id,
                sentence_type=SentenceType.FIRST,
                content_type=ContentType.ACTION
            ))

        except Exception as e:
            logger.error(f"发送TTS开始标记失败: {e}")

    async def _process_response_part_for_tts(self, context: SessionContext, response_part: str):
        """处理响应片段进行TTS - 模拟原架构逻辑"""
        try:
            tts_component = await self._get_component(context, ComponentType.TTS)
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                return

            tts_instance = tts_component.tts_instance
            if not tts_instance or not hasattr(tts_instance, 'tts_text_queue'):
                return

            # 将响应片段放入TTS队列（模拟原connection.py第782-789行逻辑）
            tts_instance.tts_text_queue.put(TTSMessageDTO(
                sentence_id=context.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.TEXT,
                content_detail=response_part
            ))

        except Exception as e:
            logger.error(f"处理TTS响应片段失败: {e}")

    async def _finalize_tts_response(self, context: SessionContext, full_response: str):
        """完成TTS响应 - 发送结束标记"""
        try:
            tts_component = await self._get_component(context, ComponentType.TTS)
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                return False

            tts_instance = tts_component.tts_instance
            if not tts_instance or not hasattr(tts_instance, 'tts_text_queue'):
                return False

            # 发送TTS结束标记（模拟原speak_txt函数逻辑）
            tts_instance.tts_text_queue.put(TTSMessageDTO(
                sentence_id=context.sentence_id,
                sentence_type=SentenceType.LAST,
                content_type=ContentType.ACTION
            ))

            # 设置LLM完成标记
            context.llm_finish_task = True
            return True

        except Exception as e:
            logger.error(f"完成TTS响应失败: {e}")
            return False

    async def _finish_tts_turn(
        self,
        context: SessionContext,
        transport: TransportInterface,
    ) -> None:
        """Guarantee that every opened device TTS stream reaches a terminal state."""
        if await self._finalize_tts_response(context, ""):
            return

        if not getattr(context, "is_speaking", False):
            return
        from core.processors.audio_send_processor import AudioSendProcessor

        sentence_id = getattr(context, "sentence_id", None)
        try:
            await AudioSendProcessor().send_tts_message(
                context,
                transport,
                "stop",
                sentence_id=sentence_id,
            )
        finally:
            context.is_speaking = False

    async def _trigger_tts(self, context: SessionContext, transport: TransportInterface, text: str):
        """触发TTS语音合成 - 完整迁移自原chat方法的TTS处理"""
        try:
            tts_component = await self._get_component(context, ComponentType.TTS)
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                logger.warning("TTS组件未初始化")
                return

            tts_instance = tts_component.tts_instance

            # 确保有sentence_id
            if not context.sentence_id:
                context.sentence_id = str(uuid.uuid4().hex)

            logger.info(f"触发TTS合成: {text[:50]}...")

            # 使用原来的TTS处理方式
            if hasattr(tts_instance, 'tts_text_queue') and hasattr(tts_instance, 'tts_one_sentence'):
                # 发送FIRST消息到TTS队列
                tts_instance.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=context.sentence_id,
                        sentence_type=SentenceType.FIRST,
                        content_type=ContentType.ACTION,
                    )
                )

                # 合成一句话
                tts_instance.tts_one_sentence(context, ContentType.TEXT, content_detail=text)

                # 发送LAST消息到TTS队列
                tts_instance.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=context.sentence_id,
                        sentence_type=SentenceType.LAST,
                        content_type=ContentType.ACTION,
                    )
                )

                logger.info("TTS合成任务已提交到队列")
            else:
                logger.warning("TTS实例不支持队列处理")

        except Exception as e:
            logger.error(f"TTS合成失败: {e}")

    async def _send_error(self, transport: TransportInterface, error_message: str):
        """发送错误消息"""
        try:
            await transport.send(json.dumps({
                "type": "error",
                "message": error_message
            }))
        except Exception as e:
            logger.error(f"发送错误消息失败: {e}")

    # === 意图处理相关方法：完整迁移自intentHandler.py ===

    async def _check_direct_exit(self, context: SessionContext, transport: TransportInterface, text: str):
        """检查是否有明确的退出命令 - 完整迁移自check_direct_exit"""
        _, text = remove_punctuation_and_length(text)
        cmd_exit = list(context.cmd_exit or [])
        extra_exit = ["退下吧", "退下", "再见", "下次聊", "闭嘴", "停止", "停下", "别说了", "不要说了"]
        for cmd in extra_exit:
            if cmd not in cmd_exit:
                cmd_exit.append(cmd)
        for cmd in cmd_exit:
            if text == cmd:
                logger.info(f"识别到明确的退出命令: {text}")
                await self._send_stt_message(context, transport, text)
                # 走结束提示语，随后回到Idle（不关闭连接）
                context.close_after_chat = True
                end_prompt = context.config.get("end_prompt", {})
                if end_prompt and end_prompt.get("enable", True) is False:
                    # 即使不播结束语，也必须发出 LAST，驱动设备回到 Idle。
                    await self._finalize_tts_response(context, "")
                    return True
                prompt = end_prompt.get("prompt")
                if not prompt:
                    prompt = "请你以“时间过得真快”开头，用富有感情、依依不舍的话来结束这场对话吧！"
                await self._regular_chat(context, transport, prompt, depth=0)
                return True
        return False

    async def _check_wakeup_words(self, context: SessionContext, transport: TransportInterface, text: str):
        """Use the single wake-word cache implementation shared with Hello."""
        from core.processors.hello_processor import HelloProcessor

        return await HelloProcessor().check_wakeup_words(
            context, transport, text
        )

    async def _analyze_intent_with_llm(self, context: SessionContext, text: str):
        """使用LLM分析用户意图 - 完整迁移自analyze_intent_with_llm"""
        intent_component = await self._get_component(context, ComponentType.INTENT)
        if not intent_component or not hasattr(intent_component, 'intent_instance'):
            logger.warning("意图识别服务未初始化")
            return None

        intent_instance = intent_component.intent_instance

        # 对话历史记录
        dialogue = context.dialogue
        if not dialogue:
            return None

        try:
            intent_result = await intent_instance.detect_intent(context, dialogue.dialogue, text)
            return intent_result
        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")

        return None

    async def _process_intent_result(self, context: SessionContext, transport: TransportInterface, intent_result: str, original_text: str):
        """处理意图识别结果 - 完整迁移自process_intent_result"""
        try:
            # 尝试将结果解析为JSON
            intent_data = json.loads(intent_result)

            function_call = intent_data.get("function_call")
            if not isinstance(function_call, dict):
                return False

            function_name = function_call.get("name")
            if not function_name:
                return False
            logger.debug(f"检测到function_call格式的意图结果: {function_name}")
            if function_name == "continue_chat":
                return False

            if function_name == "result_for_context":
                await self._send_stt_message(context, transport, original_text)
                context.abort_requested = False
                dialogue = context.dialogue
                if dialogue:
                    dialogue.put(Message(role="user", content=original_text))

                from core.utils.current_time import get_current_time_info

                current_time, today_date, today_weekday, lunar_date = (
                    get_current_time_info()
                )
                context_prompt = (
                    f"当前时间：{current_time}\n"
                    f"今天日期：{today_date} ({today_weekday})\n"
                    f"今天农历：{lunar_date}\n\n"
                    f"请根据以上信息回答用户的问题：{original_text}"
                )
                intent_component = await self._get_component(
                    context, ComponentType.INTENT
                )
                intent_instance = getattr(intent_component, "intent_instance", None)
                if intent_instance and hasattr(intent_instance, "replyResult"):
                    response = await asyncio.to_thread(
                        intent_instance.replyResult, context_prompt, original_text
                    )
                    if response:
                        await self._speak_txt(context, response)
                return True

            function_args = function_call.get("arguments") or {}
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args, ensure_ascii=False)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await self._send_stt_message(context, transport, original_text)
            context.abort_requested = False
            await self._process_function_call(
                context, transport, function_call_data, original_text
            )
            return True
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"处理意图结果时出错: {e}")
            return False

    async def _process_function_call(self, context: SessionContext, transport: TransportInterface, function_call_data: dict, original_text: str):
        """处理函数调用 - 完整迁移自process_function_call"""
        async def async_process():
            # 添加用户消息到对话历史
            dialogue = context.dialogue
            if dialogue:
                dialogue.put(Message(role="user", content=original_text))

            from core.processors.report_processor import ReportProcessor

            try:
                tool_input = json.loads(function_call_data.get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                tool_input = {}
            reporter = ReportProcessor()
            reporter.enqueue_tool_report(
                context, function_call_data.get("name", ""), tool_input
            )

            # 使用统一工具处理器处理所有工具调用
            try:
                func_handler = context.func_handler
                if not func_handler:
                    raise Exception("函数处理器未初始化")

                result = await asyncio.wait_for(
                    func_handler.handle_llm_function_call(
                        context, function_call_data
                    ),
                    timeout=max(1, int(context.config.get("tool_call_timeout", 30))),
                )
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                result = ActionResponse(
                    action=Action.ERROR, result=str(e), response=str(e)
                )

            reporter.enqueue_tool_report(
                context,
                function_call_data.get("name", ""),
                tool_input,
                str(result.result) if result and result.result is not None else None,
                report_tool_call=False,
            )

            if result:
                function_name = function_call_data.get("name", "")
                if result.action == Action.RESPONSE:  # 直接回复前端
                    text = result.response
                    if text is not None:
                        await self._speak_txt(context, text)
                elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
                    text = result.result
                    if dialogue:
                        dialogue.put(Message(role="tool", content=text))
                    intent_component = await self._get_component(context, ComponentType.INTENT)
                    if intent_component and hasattr(intent_component, 'intent_instance'):
                        intent_instance = intent_component.intent_instance
                        if hasattr(intent_instance, 'replyResult'):
                            llm_result = await asyncio.to_thread(
                                intent_instance.replyResult, text, original_text
                            )
                            if llm_result is None:
                                llm_result = text
                            await self._speak_txt(context, llm_result)
                elif (
                    result.action == Action.NOTFOUND
                    or result.action == Action.ERROR
                ):
                    text = result.response if result.response else result.result
                    if text is not None:
                        await self._speak_txt(context, text)
                elif function_name != "play_music":
                    # For backward compatibility with original code
                    # 获取当前最新的文本索引
                    text = result.response
                    if text is None:
                        text = result.result
                    if text is not None:
                        await self._speak_txt(context, text)

        # 将函数执行放在线程池中
        if hasattr(context, "create_background_task"):
            context.create_background_task(async_process(), turn_scoped=True)
        else:
            # 如果没有executor，直接执行
            await async_process()

    async def _speak_txt(self, context: SessionContext, text: str):
        """语音合成文本 - 完整迁移自speak_txt"""
        tts_component = await self._get_component(context, ComponentType.TTS)
        if not tts_component or not hasattr(tts_component, 'tts_instance'):
            return

        tts_instance = tts_component.tts_instance
        sentence_id = context.sentence_id or str(uuid.uuid4().hex)
        context.sentence_id = sentence_id

        if hasattr(tts_instance, "store_tts_text"):
            tts_instance.store_tts_text(sentence_id, text)

        # 发送TTS消息队列
        if hasattr(tts_instance, 'tts_text_queue'):
            tts_instance.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )

            # 合成一句话
            if hasattr(tts_instance, 'tts_one_sentence'):
                tts_instance.tts_one_sentence(context, ContentType.TEXT, content_detail=text)

            tts_instance.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )

        # 添加到对话历史
        dialogue = context.dialogue
        if dialogue:
            dialogue.put(Message(role="assistant", content=text))

    async def _regular_chat(self, context: SessionContext, transport: TransportInterface, text: str, depth: int = 0):
        """常规聊天处理"""
        # Match the legacy chat lifecycle: one stable ID per top-level turn.
        # Tool-call recursion keeps the same ID and its queued TTS stream.
        if depth == 0:
            context.sentence_id = uuid.uuid4().hex

        # 使用SessionContext的对话历史
        dialogue = context.dialogue
        if not dialogue:
            from core.utils.dialogue import Dialogue
            dialogue = Dialogue()
            context.dialogue = dialogue

        # 获取LLM组件
        llm_component = await self._get_component(context, ComponentType.LLM)
        if not llm_component:
            await self._send_error(transport, "LLM组件未初始化")
            await self._finish_tts_turn(context, transport)
            return

        llm_instance = getattr(llm_component, 'llm_instance', None)
        if not llm_instance:
            await self._send_error(transport, "LLM实例未就绪")
            await self._finish_tts_turn(context, transport)
            return

        logger.info("LLM实例已就绪，开始构建对话上下文")

        # 添加用户消息到对话历史（工具结果回合可能为空）
        if text:
            dialogue.put(Message(role="user", content=text))
        if depth >= 5:
            dialogue.put(
                Message(
                    role="user",
                    content="[系统提示] 已达到最大工具调用次数限制，请基于现有信息直接回答，不要再调用工具。",
                )
            )

        # 原架构不发送thinking状态给前端，直接开始处理

        # 获取记忆上下文
        memory_context = await self._get_memory_context(context, text)

        # 构建对话上下文
        dialogue_context = dialogue.get_llm_dialogue_with_memory(
            memory_context,
            context.config.get("voiceprint", {}),
            current_speaker=context.current_speaker,
        )

        # 调用LLM生成回复
        if context.intent_type == "function_call" and context.func_handler and hasattr(llm_instance, "response_with_functions"):
            await self._generate_llm_response_with_tools(
                context,
                transport,
                llm_instance,
                dialogue_context,
                dialogue,
                depth=depth,
            )
        else:
            await self._generate_llm_response(context, transport, llm_instance, dialogue_context, dialogue)

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        from core.processors.audio_send_processor import AudioSendProcessor

        await AudioSendProcessor().send_stt_message(
            context, transport, text
        )

    async def _get_component(self, context: SessionContext, component_type: ComponentType):
        if not context.component_manager:
            return None
        return await context.component_manager.get_component(component_type, context)

    def cleanup_session(self, session_id: str):
        """清理会话对话历史"""
        if session_id in self._dialogues:
            del self._dialogues[session_id]
            logger.info(f"已清理会话对话历史: {session_id}")
