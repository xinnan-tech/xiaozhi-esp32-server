from config.logger import setup_logging
import json
import asyncio
import time
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji

TAG = __name__
logger = setup_logging()


async def isLLMWantToFinish(conn):
    first_text = conn.tts_first_text
    last_text = conn.tts_last_text
    _, last_text_without_punctuation = remove_punctuation_and_length(last_text)
    if "再见" in last_text_without_punctuation or "拜拜" in last_text_without_punctuation:
        return True
    _, first_text_without_punctuation = remove_punctuation_and_length(first_text)
    if "再见" in first_text_without_punctuation or "拜拜" in first_text_without_punctuation:
        return True
    return False


async def sendAudioMessage(conn, audios, duration, text):
    base_delay = conn.tts_duration

    # 发送 tts.start
    if text == conn.tts_first_text:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts_start_speak_time = time.time()

    # 发送 sentence_start（每个音频文件之前发送一次）
    sentence_task = asyncio.create_task(
        schedule_with_interrupt(base_delay, send_tts_message(conn, "sentence_start", text))
    )
    conn.scheduled_tasks.append(sentence_task)

    conn.tts_duration += duration

    # 发送音频数据
    for idx, opus_packet in enumerate(audios):
        await conn.websocket.send(opus_packet)

    if conn.llm_finish_task and text == conn.tts_last_text:
        stop_duration = conn.tts_duration - (time.time() - conn.tts_start_speak_time)
        stop_task = asyncio.create_task(
            schedule_with_interrupt(stop_duration, send_tts_message(conn, 'stop'))
        )
        conn.scheduled_tasks.append(stop_task)
        if await isLLMWantToFinish(conn):
            finish_task = asyncio.create_task(
                schedule_with_interrupt(stop_duration, await conn.close())
            )
            conn.scheduled_tasks.append(finish_task)


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


async def schedule_with_interrupt(delay, coro):
    """可中断的延迟调度"""
    try:
        await asyncio.sleep(delay)
        await coro
    except asyncio.CancelledError:
        pass
