from config.logger import setup_logging
import json
import uuid
from core.handle.sendAudioHandle import send_stt_message
from core.handle.helloHandle import checkWakeupWords
from core.utils.util import remove_punctuation_and_length
from core.utils.dialogue import Message
from loguru import logger

TAG = __name__
logger = setup_logging()


async def handle_user_intent(conn, text):
    # 检查是否有明确的退出命令
    if await check_direct_exit(conn, text):
        return True
    # 检查是否是唤醒词
    if await checkWakeupWords(conn, text):
        return True

    if conn.use_function_call_mode:
        # 使用支持function calling的聊天方法,不再进行意图分析
        return False
    # 使用LLM进行意图分析
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        return False
    # 处理各种意图
    return await process_intent_result(conn, intent_result, text)


async def check_direct_exit(conn, text):
    """检查是否有明确的退出命令"""
    _, text = remove_punctuation_and_length(text)
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            logger.bind(tag=TAG).info(f"识别到明确的退出命令: {text}")
            await send_stt_message(conn, text)
            await conn.close()
            return True
    return False


async def analyze_intent_with_llm(conn, text):
    """使用LLM分析用户意图"""
    if not hasattr(conn, "intent") or not conn.intent:
        logger.bind(tag=TAG).warning("意图识别服务未初始化")
        return None

    # 对话历史记录
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        return intent_result
    except Exception as e:
        logger.bind(tag=TAG).error(f"意图识别失败: {str(e)}")

    return None


async def process_intent_result(conn, intent_result, original_text):
    """处理意图识别结果"""
    try:
        # 尝试将结果解析为JSON
        intent_data = json.loads(intent_result)

        # 检查是否有function_call
        if "function_call" in intent_data:
            # 直接从意图识别获取了function_call
            logger.bind(tag=TAG).debug(
                f"检测到function_call格式的意图结果: {intent_data['function_call']['name']}"
            )
            function_name = intent_data["function_call"]["name"]
            if function_name == "continue_chat":
                return False

            if function_name == "play_music":
                funcItem = conn.func_handler.get_function(function_name)
                if not funcItem:
                    conn.func_handler.function_registry.register_function("play_music")

            function_args = None
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
            # 确保参数是字符串格式的JSON
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)

            # 使用executor执行函数调用和结果处理
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))
                result = conn.func_handler.handle_llm_function_call(
                    conn, function_call_data
                )
                if result and function_name != "play_music":
                    # 获取当前最新的文本索引
                    text = result.response
                    if text is None:
                        text = result.result
                    if text is not None:
                        text_index = (
                            conn.tts_last_text_index + 1
                            if hasattr(conn, "tts_last_text_index")
                            else 0
                        )
                        conn.recode_first_last_text(text, text_index)
                        future = conn.executor.submit(
                            conn.speak_and_play, text, text_index
                        )
                        conn.llm_finish_task = True
                        conn.tts_queue.put(future)
                        conn.dialogue.put(Message(role="assistant", content=text))

            # 将函数执行放在线程池中
            conn.executor.submit(process_function_call)
            return True
        return False
    except json.JSONDecodeError as e:
        logger.bind(tag=TAG).error(f"处理意图结果时出错: {e}")
        return False


def extract_text_in_brackets(s):
    """
    从字符串中提取中括号内的文字

    :param s: 输入字符串
    :return: 中括号内的文字，如果不存在则返回空字符串
    """
    left_bracket_index = s.find("[")
    right_bracket_index = s.find("]")

    if (
        left_bracket_index != -1
        and right_bracket_index != -1
        and left_bracket_index < right_bracket_index
    ):
        return s[left_bracket_index + 1 : right_bracket_index]
    else:
        return ""
