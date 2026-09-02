import json
import uuid
import asyncio
from core.utils.dialogue import Message
from core.providers.tts.dto.dto import ContentType
from core.handle.helloHandle import checkWakeupWords
from plugins_func.register import Action, ActionResponse
from core.handle.sendAudioHandle import send_stt_message
from core.utils.util import remove_punctuation_and_length
from core.utils.exit_handler import is_exit_command, handle_exit
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType

TAG = __name__


async def handle_user_intent(conn, text):
    # Preprocess input text, handle potential JSON format
    try:
        if text.strip().startswith('{') and text.strip().endswith('}'):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                text = parsed_data["content"]  # Extract content for intent analysis
                conn.current_speaker = parsed_data.get("speaker")  # Keep speaker info
    except (json.JSONDecodeError, TypeError):
        pass

    # Check for direct exit command
    _, filtered_text = remove_punctuation_and_length(text)
    if await check_direct_exit(conn, filtered_text):
        return True

    # Check for wake word
    if await checkWakeupWords(conn, filtered_text):
        return True

    if conn.intent_type == "function_call":
        # Use chat method supporting function calling, skip intent analysis
        return False
    # Use LLM for intent analysis
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        return False
    # Generate sentence_id at session start
    conn.sentence_id = str(uuid.uuid4().hex)
    # Handle various intents
    return await process_intent_result(conn, intent_result, text)


async def check_direct_exit(conn, text):
    """Check for explicit exit command"""
    _, text = remove_punctuation_and_length(text)
    if is_exit_command(text, conn.cmd_exit):
        conn.logger.bind(tag=TAG).info(f"Detected explicit exit command: {text}")
        await send_stt_message(conn, text)
        handle_exit(conn)
        return True
    return False


async def analyze_intent_with_llm(conn, text):
    """Analyze user intent with LLM"""
    if not hasattr(conn, "intent") or not conn.intent:
        conn.logger.bind(tag=TAG).warning("Intent service not initialized")
        return None

    # Dialogue history
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        return intent_result
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Intent recognition failed: {str(e)}")

    return None


async def process_intent_result(conn, intent_result, original_text):
    """Process intent recognition result"""
    try:
        # Try to parse result as JSON
        intent_data = json.loads(intent_result)

        # Check for function_call
        if "function_call" in intent_data:
            # Got function_call directly from intent
            conn.logger.bind(tag=TAG).debug(
                f"Detected function_call intent format: {intent_data['function_call']['name']}"
            )
            function_name = intent_data["function_call"]["name"]
            if function_name == "continue_chat":
                return False

            if function_name == "result_for_context":
                await send_stt_message(conn, original_text)
                conn.client_abort = False
                
                def process_context_result():
                    conn.dialogue.put(Message(role="user", content=original_text))
                    
                    from core.utils.current_time import get_current_time_info

                    current_time, today_date, today_weekday, lunar_date = get_current_time_info()
                    
                    # Build base prompt with context
                    # Prepend current system prompt (persona) if available
                    base_system = conn.prompt if hasattr(conn, "prompt") and conn.prompt else ""
                    
                    context_prompt = f"""{base_system}
                                        Current Time: {current_time}
                                        Date: {today_date} ({today_weekday})
                                        Lunar Date: {lunar_date}

                                        Please answer the user's question based on the above information: {original_text}"""
                    
                    response = conn.intent.replyResult(context_prompt, original_text)
                    speak_txt(conn, response)
                
                conn.executor.submit(process_context_result)
                return True

            function_args = {}
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
                if function_args is None:
                    function_args = {}
            # Ensure args are JSON string
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)
            conn.client_abort = False

            # Use executor to handle tool call and result processing
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))

                # Use unified tool handler
                try:
                    result = asyncio.run_coroutine_threadsafe(
                        conn.func_handler.handle_llm_function_call(
                            conn, function_call_data
                        ),
                        conn.loop,
                    ).result()
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"工具调用失败: {e}")
                    result = ActionResponse(
                        action=Action.ERROR, result=str(e), response=str(e)
                    )

                if result:
                    if result.action == Action.RESPONSE:  # 直接回复前端
                        text = result.response
                        if text is not None:
                            speak_txt(conn, text)
                    elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
                        text = result.result
                        conn.logger.bind(tag=TAG).info(f"Tool output for LLM generation: {text}")
                        conn.dialogue.put(Message(role="tool", content=text))
                        llm_result = conn.intent.replyResult(text, original_text)
                        if llm_result is None:
                            llm_result = text
                        speak_txt(conn, llm_result)
                    elif (
                        result.action == Action.NOTFOUND
                        or result.action == Action.ERROR
                    ):
                        text = result.response
                        if not text:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)
                    elif function_name != "play_music":
                        # For backward compatibility with original code
                        # 获取当前最新的文本索引
                        text = result.response
                        if text is None:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)

            # Execute function in thread pool
            conn.executor.submit(process_function_call)
            return True
        return False
    except json.JSONDecodeError as e:
        conn.logger.bind(tag=TAG).error(f"Error processing intent result: {e}")
        return False


def speak_txt(conn, text):
    # Log text
    conn.tts_MessageText = text

    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )
    conn.dialogue.put(Message(role="assistant", content=text))
