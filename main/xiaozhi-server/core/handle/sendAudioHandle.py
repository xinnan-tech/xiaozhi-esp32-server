from config.logger import setup_logging
import json
import asyncio
import time
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji

TAG = __name__
logger = setup_logging()

async def sendAudioMessage(conn, audios, text, text_index=0):
    # 发送句子开始消息
    if text_index == conn.tts_first_text_index:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
    await send_tts_message(conn, "sentence_start", text)

    # 初始化流控参数
    frame_duration = 60  # 毫秒
    start_time = time.perf_counter()  # 使用高精度计时器
    play_position = 0  # 已播放的时长（毫秒）

    for opus_packet in audios:
        if conn.client_abort:
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
    await send_tts_message(conn, "sentence_end", text)
    # 发送结束消息（如果是最后一个文本）
    if conn.llm_finish_task and text_index == conn.tts_last_text_index:
        await send_tts_message(conn, 'stop', None)

async def send_tts_message(conn, state, text=None):
    """发送 TTS 状态消息"""
    message = {
        "type": "tts",
        "state": state,
        "session_id": conn.session_id
    }
    if text is not None:
        message["text"] = text

    await conn.websocket.send(json.dumps(message))
    if state == "stop":
        conn.clearSpeakStatus()


async def send_stt_message(conn, text):
    """发送 STT 状态消息"""
    stt_text = get_string_no_punctuation_or_emoji(text)
    await conn.websocket.send(json.dumps({
        "type": "stt",
        "text": stt_text,
        "session_id": conn.session_id}
    ))
    await conn.websocket.send(
        json.dumps({
            "type": "llm",
            "text": "😊",
            "emotion": "happy",
            "session_id": conn.session_id}
        ))
    await send_tts_message(conn, "start")
