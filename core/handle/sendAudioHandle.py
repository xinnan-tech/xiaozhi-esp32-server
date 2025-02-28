from config.logger import setup_logging
import json
import asyncio
import time
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji

TAG = __name__
logger = setup_logging()


async def isLLMWantToFinish(last_text):
    _, last_text_without_punctuation = remove_punctuation_and_length(last_text)
    if "再见" in last_text_without_punctuation or "拜拜" in last_text_without_punctuation:
        return True
    return False


async def sendAudioMessage(conn, audios, text):
    # 发送 tts.start
    if text == conn.tts_first_text:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts_start_speak_time = time.time()
    await send_tts_message(conn, "sentence_start", text)

    # 发送音频数据
    frame_duration = 60  # 初始帧持续时间（毫秒）
    start_time = time.time()  # 记录开始时间
    for idx, opus_packet in enumerate(audios):
        if conn.client_abort:
            return
        # 计算当前包的预期发送时间
        expected_time = start_time + idx * (frame_duration / 1000)
        current_time = time.time()
        # 如果未到预期时间则等待差值
        if current_time < expected_time:
            await asyncio.sleep(expected_time - current_time)
        # 发送音频包
        await conn.websocket.send(opus_packet)

    if conn.llm_finish_task and text == conn.tts_last_text:
        await send_tts_message(conn, 'stop')
        if await isLLMWantToFinish(text):
            await conn.close()


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
