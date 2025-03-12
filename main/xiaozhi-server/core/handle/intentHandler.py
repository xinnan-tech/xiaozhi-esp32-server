from config.logger import setup_logging
import json
from core.handle.sendAudioHandle import send_stt_message
from core.utils.dialogue import Message
from config.functionCallConfig import FunctionCallConfig
import asyncio
from enum import Enum

TAG = __name__
logger = setup_logging()


class Action(Enum):
    NOTFOUND = (0, "没有找到函数")
    NONE = (1, "啥也不干")
    RESPONSE = (2, "直接回复")
    REQLLM = (3, "调用函数后再请求llm生成回复")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class ActionResponse:
    def __init__(self, action: Action, result, response):
        self.action = action  # 动作类型
        self.result = result  # 动作产生的结果
        self.response = response  # 直接回复的内容


def get_functions():
    """获取功能调用配置"""
    return FunctionCallConfig


def handle_llm_function_call(conn, function_call_data):
    try:
        function_name = function_call_data["name"]

        if function_name == "handle_exit_intent":
            # 处理退出意图
            try:
                say_goodbye = json.loads(function_call_data["arguments"]).get("say_goodbye", "再见")
                conn.close_after_chat = True
                logger.bind(tag=TAG).info(f"退出意图已处理:{say_goodbye}")
                return ActionResponse(action=Action.RESPONSE, result="退出意图已处理", response=say_goodbye)
            except Exception as e:
                logger.bind(tag=TAG).error(f"处理退出意图错误: {e}")

        elif function_name == "play_music":
            # 处理音乐播放意图
            try:
                song_name = "random"
                arguments = function_call_data["arguments"]
                if arguments is not None and len(arguments) > 0:
                    args = json.loads(arguments)
                    song_name = args.get("song_name", "random")
                music_intent = f"播放音乐 {song_name}" if song_name != "random" else "随机播放音乐"

                # 执行音乐播放命令
                future = asyncio.run_coroutine_threadsafe(
                    conn.music_handler.handle_music_command(conn, music_intent),
                    conn.loop
                )
                future.result()
                return ActionResponse(action=Action.RESPONSE, result="退出意图已处理", response="还想听什么歌？")
            except Exception as e:
                logger.bind(tag=TAG).error(f"处理音乐意图错误: {e}")
        else:
            return ActionResponse(action=Action.NOTFOUND, result="没有找到对应的函数", response="没有找到对应的函数处理相对于的功能呢，你可以需要添加预设的对应函数处理呢")
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理function call错误: {e}")

    return None


async def handle_user_intent(conn, text):
    """
    Handle user intent before starting chat
    
    Args:
        conn: Connection object
        text: User's text input
    
    Returns:
        bool: True if intent was handled, False if should proceed to chat
    """
    # 检查是否有明确的退出命令
    if await check_direct_exit(conn, text):
        return True

    if conn.use_function_call_mode:
        # 使用支持function calling的聊天方法,不再进行意图分析
        return False

    # 使用LLM进行意图分析
    intent = await analyze_intent_with_llm(conn, text)

    if not intent:
        return False

    # 处理各种意图
    return await process_intent_result(conn, intent, text)


async def check_direct_exit(conn, text):
    """检查是否有明确的退出命令"""
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            logger.bind(tag=TAG).info(f"识别到明确的退出命令: {text}")
            await conn.close()
            return True
    return False


async def analyze_intent_with_llm(conn, text):
    """使用LLM分析用户意图"""
    if not hasattr(conn, 'intent') or not conn.intent:
        logger.bind(tag=TAG).warning("意图识别服务未初始化")
        return None

    # 对话历史记录
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(dialogue.dialogue, text)

        # 尝试解析JSON结果
        try:
            intent_data = json.loads(intent_result)
            if "intent" in intent_data:
                return intent_data["intent"]
        except json.JSONDecodeError:
            # 如果不是JSON格式，尝试直接获取意图文本
            return intent_result.strip()

    except Exception as e:
        logger.bind(tag=TAG).error(f"意图识别失败: {str(e)}")

    return None


async def process_intent_result(conn, intent, original_text):
    """处理意图识别结果"""
    # 处理退出意图
    if "结束聊天" in intent:
        logger.bind(tag=TAG).info(f"识别到退出意图: {intent}")

        # 如果正在播放音乐，可以关了 TODO

        # 如果是明确的离别意图，发送告别语并关闭连接
        await send_stt_message(conn, original_text)
        conn.executor.submit(conn.chat_and_close, original_text)
        return True

    # 处理播放音乐意图
    if "播放音乐" in intent:
        logger.bind(tag=TAG).info(f"识别到音乐播放意图: {intent}")
        await conn.music_handler.handle_music_command(conn, intent)
        return True

    # 其他意图处理可以在这里扩展

    # 默认返回False，表示继续常规聊天流程
    return False
