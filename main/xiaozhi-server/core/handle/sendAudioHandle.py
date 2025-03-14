# 导入所需的模块
from config.logger import setup_logging  # 导入日志设置模块
import json  # 导入JSON模块，用于处理JSON数据
import asyncio  # 导入异步IO模块，用于处理异步任务
import time  # 导入时间模块，用于处理时间相关的操作
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji  # 导入工具函数，用于处理文本

# 定义当前模块的标签，通常用于日志记录
TAG = __name__

# 设置日志记录器
logger = setup_logging()

async def isLLMWantToFinish(last_text):
    """判断LLM是否想要结束对话"""
    _, last_text_without_punctuation = remove_punctuation_and_length(last_text)  # 去除标点符号并获取文本
    if "再见" in last_text_without_punctuation or "拜拜" in last_text_without_punctuation:  # 如果文本中包含“再见”或“拜拜”
        return True  # 返回True，表示LLM想要结束对话
    return False  # 否则返回False

async def sendAudioMessage(conn, audios, text, text_index=0):
    """发送音频消息"""
    # 如果是第一段语音，记录日志
    if text_index == conn.tts_first_text_index:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")

    # 发送句子开始消息
    await send_tts_message(conn, "sentence_start", text)

    # 初始化流控参数
    frame_duration = 60  # 每帧音频的时长（毫秒）
    start_time = time.perf_counter()  # 使用高精度计时器记录开始时间
    play_position = 0  # 已播放的时长（毫秒）

    # 遍历音频包并发送
    for opus_packet in audios:
        if conn.client_abort:  # 如果客户端中止，直接返回
            return

        # 计算当前包的预期发送时间
        expected_time = start_time + (play_position / 1000)
        current_time = time.perf_counter()

        # 等待直到预期时间
        delay = expected_time - current_time
        if delay > 0:
            await asyncio.sleep(delay)

        # 发送音频包
        await conn.websocket.send(opus_packet)
        play_position += frame_duration  # 更新播放位置

    # 发送句子结束消息
    await send_tts_message(conn, "sentence_end", text)

    # 如果是最后一个文本且任务完成，发送停止消息
    if conn.llm_finish_task and text_index == conn.tts_last_text_index:
        await send_tts_message(conn, 'stop', None)
        if await isLLMWantToFinish(text):  # 如果LLM想要结束对话
            await conn.close()  # 关闭连接

async def send_tts_message(conn, state, text=None):
    """发送 TTS 状态消息"""
    message = {
        "type": "tts",  # 消息类型为TTS
        "state": state,  # TTS状态
        "session_id": conn.session_id  # 会话ID
    }
    if text is not None:  # 如果文本不为空，添加到消息中
        message["text"] = text

    # 发送JSON格式的消息
    await conn.websocket.send(json.dumps(message))
    if state == "stop":  # 如果状态为停止，清除说话状态
        conn.clearSpeakStatus()

async def send_stt_message(conn, text):
    """发送 STT 状态消息"""
    stt_text = get_string_no_punctuation_or_emoji(text)  # 去除标点符号和表情符号
    # 发送STT消息
    await conn.websocket.send(json.dumps({
        "type": "stt",  # 消息类型为STT
        "text": stt_text,  # 识别到的文本
        "session_id": conn.session_id  # 会话ID
    }))
    # 发送LLM消息（表情）
    await conn.websocket.send(
        json.dumps({
            "type": "llm",  # 消息类型为LLM
            "text": "😊",  # 表情符号
            "emotion": "happy",  # 情绪状态
            "session_id": conn.session_id  # 会话ID
        }))
    # 发送TTS开始消息
    await send_tts_message(conn, "start")