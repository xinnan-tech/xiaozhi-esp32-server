import json
import uuid
import asyncio
from typing import Any, Dict
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.dialogue import Message, Dialogue
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from plugins_func.register import Action, ActionResponse
from config.logger import setup_logging

logger = setup_logging()


class ChatProcessor(MessageProcessor):
    """聊天处理器：完整迁移intentHandler.py的所有功能"""
    
    def __init__(self):
        # 会话对话历史管理
        self._dialogues: Dict[str, Dialogue] = {}
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理聊天消息"""
        # 这个处理器不直接处理原始消息，而是被其他处理器调用
        return False
    
    async def handle_chat(self, context: SessionContext, transport: TransportInterface, text: str):
        """处理聊天请求 - 完整迁移自handle_user_intent"""
        try:
            # 首先进行意图处理
            intent_handled = await self.handle_user_intent(context, transport, text)
            if intent_handled:
                return
                
            # 如果意图未处理，进行常规聊天
            await self._regular_chat(context, transport, text)
            
        except Exception as e:
            logger.error(f"处理聊天失败: {e}")
            await self._send_error(transport, "聊天处理失败，请重试")
    
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
            memory_component = context.components.get('memory')
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
                async for response_part in self._async_generator_wrapper(response_generator):
                    if context.abort_requested:
                        break
                    
                    if response_part and len(response_part) > 0:
                        response_parts.append(response_part)
                        
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
                
            else:
                logger.warning("LLM实例不支持流式响应")
                
        except Exception as e:
            logger.error(f"生成LLM回复失败: {e}")
            await self._send_error(transport, "生成回复失败")
    
    async def _async_generator_wrapper(self, generator):
        """将同步生成器包装为异步生成器"""
        try:
            for item in generator:
                yield item
                # 让出控制权，避免阻塞事件循环
                await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"生成器包装失败: {e}")
    
    async def _send_tts_first_marker(self, context: SessionContext):
        """发送TTS开始标记"""
        try:
            tts_component = context.components.get('tts')
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
            tts_component = context.components.get('tts')
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
            tts_component = context.components.get('tts')
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                return
                
            tts_instance = tts_component.tts_instance
            if not tts_instance or not hasattr(tts_instance, 'tts_text_queue'):
                return
            
            # 发送TTS结束标记（模拟原speak_txt函数逻辑）
            tts_instance.tts_text_queue.put(TTSMessageDTO(
                sentence_id=context.sentence_id,
                sentence_type=SentenceType.LAST,
                content_type=ContentType.ACTION
            ))
            
            # 设置LLM完成标记
            context.llm_finish_task = True
                
        except Exception as e:
            logger.error(f"完成TTS响应失败: {e}")
    
    async def _trigger_tts(self, context: SessionContext, transport: TransportInterface, text: str):
        """触发TTS语音合成 - 完整迁移自原chat方法的TTS处理"""
        try:
            tts_component = context.components.get('tts')
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
        cmd_exit = context.cmd_exit
        for cmd in cmd_exit:
            if text == cmd:
                logger.info(f"识别到明确的退出命令: {text}")
                await self._send_stt_message(context, transport, text)
                await transport.close()
                return True
        return False

    async def _check_wakeup_words(self, context: SessionContext, transport: TransportInterface, text: str):
        """检查唤醒词 - 调用TextProcessor的方法"""
        # 这里需要调用TextProcessor的checkWakeupWords方法
        # 为了避免循环依赖，我们在这里实现简化版本
        _, filtered_text = remove_punctuation_and_length(text)
        if filtered_text in context.config.get("wakeup_words", []):
            return True
        return False

    async def _analyze_intent_with_llm(self, context: SessionContext, text: str):
        """使用LLM分析用户意图 - 完整迁移自analyze_intent_with_llm"""
        intent_component = context.components.get('intent')
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

            # 检查是否有function_call
            if "function_call" in intent_data:
                # 直接从意图识别获取了function_call
                logger.debug(f"检测到function_call格式的意图结果: {intent_data['function_call']['name']}")
                function_name = intent_data["function_call"]["name"]
                if function_name == "continue_chat":
                    return False

                function_args = {}
                if "arguments" in intent_data["function_call"]:
                    function_args = intent_data["function_call"]["arguments"]
                    if function_args is None:
                        function_args = {}
                        
                # 确保参数是字符串格式的JSON
                if isinstance(function_args, dict):
                    function_args = json.dumps(function_args)

                function_call_data = {
                    "name": function_name,
                    "id": str(uuid.uuid4().hex),
                    "arguments": function_args,
                }

                await self._send_stt_message(context, transport, original_text)
                context.abort_requested = False

                # 使用executor执行函数调用和结果处理
                await self._process_function_call(context, transport, function_call_data, original_text)
                return True
            return False
        except json.JSONDecodeError as e:
            logger.error(f"处理意图结果时出错: {e}")
            return False

    async def _process_function_call(self, context: SessionContext, transport: TransportInterface, function_call_data: dict, original_text: str):
        """处理函数调用 - 完整迁移自process_function_call"""
        def process_function_call():
            # 添加用户消息到对话历史
            dialogue = context.dialogue
            if dialogue:
                dialogue.put(Message(role="user", content=original_text))

            # 使用统一工具处理器处理所有工具调用
            try:
                func_handler = context.func_handler
                if not func_handler:
                    raise Exception("函数处理器未初始化")
                    
                loop = context.loop
                result = asyncio.run_coroutine_threadsafe(
                    func_handler.handle_llm_function_call(context, function_call_data),
                    loop,
                ).result()
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                result = ActionResponse(
                    action=Action.ERROR, result=str(e), response=str(e)
                )

            if result:
                function_name = function_call_data.get("name", "")
                if result.action == Action.RESPONSE:  # 直接回复前端
                    text = result.response
                    if text is not None:
                        self._speak_txt(context, text)
                elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
                    text = result.result
                    if dialogue:
                        dialogue.put(Message(role="tool", content=text))
                    intent_component = context.components.get('intent')
                    if intent_component and hasattr(intent_component, 'intent_instance'):
                        intent_instance = intent_component.intent_instance
                        if hasattr(intent_instance, 'replyResult'):
                            llm_result = intent_instance.replyResult(text, original_text)
                            if llm_result is None:
                                llm_result = text
                            self._speak_txt(context, llm_result)
                elif (
                    result.action == Action.NOTFOUND
                    or result.action == Action.ERROR
                ):
                    text = result.result
                    if text is not None:
                        self._speak_txt(context, text)
                elif function_name != "play_music":
                    # For backward compatibility with original code
                    # 获取当前最新的文本索引
                    text = result.response
                    if text is None:
                        text = result.result
                    if text is not None:
                        self._speak_txt(context, text)

        # 将函数执行放在线程池中
        if context.executor:
            context.executor.submit(process_function_call)
        else:
            # 如果没有executor，直接执行
            process_function_call()

    def _speak_txt(self, context: SessionContext, text: str):
        """语音合成文本 - 完整迁移自speak_txt"""
        tts_component = context.components.get('tts')
        if not tts_component or not hasattr(tts_component, 'tts_instance'):
            return
            
        tts_instance = tts_component.tts_instance
        sentence_id = context.sentence_id or str(uuid.uuid4().hex)
        
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

    async def _regular_chat(self, context: SessionContext, transport: TransportInterface, text: str):
        """常规聊天处理"""
        # 使用SessionContext的对话历史
        dialogue = context.dialogue
        if not dialogue:
            from core.utils.dialogue import Dialogue
            dialogue = Dialogue()
            context.dialogue = dialogue
        
        # 获取LLM组件
        llm_component = context.components.get('llm')
        if not llm_component:
            await self._send_error(transport, "LLM组件未初始化")
            return
        
        llm_instance = getattr(llm_component, 'llm_instance', None)
        if not llm_instance:
            await self._send_error(transport, "LLM实例未就绪")
            return
        
        # 添加用户消息到对话历史
        dialogue.put(Message(role="user", content=text))
        
        # 原架构不发送thinking状态给前端，直接开始处理
        
        # 获取记忆上下文
        memory_context = await self._get_memory_context(context, text)
        
        # 构建对话上下文
        dialogue_context = dialogue.get_llm_dialogue_with_memory(
            memory_context, 
            context.config.get("voiceprint", {})
        )
        
        # 调用LLM生成回复
        await self._generate_llm_response(context, transport, llm_instance, dialogue_context, dialogue)

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        await transport.send(json.dumps({
            "type": "stt",
            "text": text,
            "session_id": context.session_id
        }))

    def cleanup_session(self, session_id: str):
        """清理会话对话历史"""
        if session_id in self._dialogues:
            del self._dialogues[session_id]
            logger.info(f"已清理会话对话历史: {session_id}")
