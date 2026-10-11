import json
import uuid
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.dialogue import Message
from core.providers.tts.dto.dto import ContentType
from core.handle.helloHandle import checkWakeupWords
from plugins_func.register import Action, ActionResponse
from core.handle.sendAudioHandle import send_stt_message
from core.handle.reportHandle import enqueue_tool_report
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType

TAG = __name__


async def handle_user_intent(conn: "ConnectionHandler", text):
    # Preprocess the input text and handle possible JSON-wrapped payloads.
    try:
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                text = parsed_data["content"]  # Extract content for intent analysis.
                conn.current_speaker = parsed_data.get("speaker")  # Preserve speaker info.
    except (json.JSONDecodeError, TypeError):
        pass

    # Check for explicit exit commands first.
    _, filtered_text = remove_punctuation_and_length(text)
    if await check_direct_exit(conn, filtered_text):
        return True

    # Do not interrupt an explicit exit flow once it has started.
    if conn.is_exiting:
        return True

    # Check whether the message is just a wake word.
    if await checkWakeupWords(conn, filtered_text):
        return True

    if conn.intent_type == "function_call":
        # In function-calling mode, skip legacy intent analysis entirely.
        return False
    # Otherwise, analyze the user intent with the configured LLM.
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        return False
    # Generate a sentence ID for the new turn.
    conn.sentence_id = str(uuid.uuid4().hex)
    # Handle the detected intent result.
    return await process_intent_result(conn, intent_result, text)


async def check_direct_exit(conn: "ConnectionHandler", text):
    """Check whether the user issued a direct exit command."""
    _, text = remove_punctuation_and_length(text)
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            conn.logger.bind(tag=TAG).info(f"Detected explicit exit command: {text}")
            await send_stt_message(conn, text)
            await conn.close()
            return True
    return False


async def analyze_intent_with_llm(conn: "ConnectionHandler", text):
    """Analyze user intent through the configured LLM-backed intent service."""
    if not hasattr(conn, "intent") or not conn.intent:
        conn.logger.bind(tag=TAG).warning("Intent recognition service is not initialized")
        return None

    # Provide dialogue history to the intent detector.
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        return intent_result
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Intent recognition failed: {str(e)}")

    return None


async def process_intent_result(
    conn: "ConnectionHandler", intent_result, original_text
):
    """Process the intent recognition result."""
    try:
        # Try to parse the result as JSON.
        intent_data = json.loads(intent_result)

        # Check whether the result contains a function call.
        if "function_call" in intent_data:
            # A function call was returned directly from the intent detector.
            conn.logger.bind(tag=TAG).debug(
                f"Detected function_call intent result: {intent_data['function_call']['name']}"
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

                    current_time, today_date, today_weekday, formatted_date = get_current_time_info()

                    # Build a context-aware base prompt.
                    context_prompt = f"""Current time: {current_time}
Today's date: {today_date} ({today_weekday})

Please answer the user's question using the information above: {original_text}"""

                    # Use async calls to avoid blocking the event loop and affecting audio playback on other devices
                    try:
                        response = asyncio.run_coroutine_threadsafe(
                            conn.intent.replyResult(context_prompt, original_text),
                            conn.loop,
                        ).result()
                    except Exception as e:
                        conn.logger.bind(tag=TAG).error(f"LLM reply generation failed: {e}")
                        response = None
                    if response:
                        speak_txt(conn, response)

                conn.executor.submit(process_context_result)
                return True

            function_args = {}
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
                if function_args is None:
                    function_args = {}
            # Normalize arguments to a JSON string.
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)
            conn.client_abort = False

            # Prepare tool-call input for reporting.
            tool_input = {}
            if function_args:
                if isinstance(function_args, str):
                    tool_input = json.loads(function_args) if function_args else {}
                elif isinstance(function_args, dict):
                    tool_input = function_args

            # Report the tool call.
            enqueue_tool_report(conn, function_name, tool_input)

            # Execute the tool call and result handling on the executor.
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))

                # Tool calls use a configurable timeout; default to 30 seconds.
                tool_call_timeout = int(conn.config.get("tool_call_timeout", 30))
                # Route all tool calls through the unified tool handler.
                try:
                    result = asyncio.run_coroutine_threadsafe(
                        conn.func_handler.handle_llm_function_call(
                            conn, function_call_data
                        ),
                        conn.loop,
                    ).result(timeout=tool_call_timeout)
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"Tool call failed: {e}")
                    result = ActionResponse(
                        action=Action.ERROR, result="The tool call timed out. Please try again in a moment.", response="The tool call timed out. Please try again in a moment."
                    )

                # Report the tool-call result.
                if result:
                    enqueue_tool_report(conn, function_name, tool_input, str(result.result) if result.result else None, report_tool_call=False)

                    if result.action == Action.RESPONSE:  # Reply directly to the client.
                        text = result.response
                        if text is not None:
                            speak_txt(conn, text)
                    elif result.action == Action.REQLLM:  # Ask the LLM to produce a follow-up reply.
                        text = result.result
                        conn.dialogue.put(Message(role="tool", content=text))
                        # Use async calls to avoid blocking the event loop and affecting audio playback on other devices
                        try:
                            llm_result = asyncio.run_coroutine_threadsafe(
                                conn.intent.replyResult(text, original_text),
                                conn.loop,
                            ).result()
                        except Exception as e:
                            conn.logger.bind(tag=TAG).error(f"LLM reply generation failed: {e}")
                            llm_result = text
                        if llm_result is None:
                            llm_result = text
                        speak_txt(conn, llm_result)
                    elif (
                        result.action == Action.NOTFOUND
                        or result.action == Action.ERROR
                    ):
                        text = result.response if result.response else result.result
                        if text is not None:
                            speak_txt(conn, text)
                    elif function_name != "play_music":
                        # For backward compatibility with original code
                        # Use the most recent text result when available.
                        text = result.response
                        if text is None:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)

            # Submit the function execution flow to the thread pool.
            conn.executor.submit(process_function_call)
            return True
        return False
    except json.JSONDecodeError as e:
        conn.logger.bind(tag=TAG).error(f"Error while processing intent result: {e}")
        return False


def speak_txt(conn: "ConnectionHandler", text):
    # Store text for sentence-level reporting and streaming subtitles.
    conn.tts.store_tts_text(conn.sentence_id, text)
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
