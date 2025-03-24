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

    # 播放音频
    await sendAudio(conn, audios)

    await send_tts_message(conn, "sentence_end", text)

    # 发送结束消息（如果是最后一个文本）
    if conn.llm_finish_task and text_index == conn.tts_last_text_index:
        await send_tts_message(conn, 'stop', None)
        if conn.close_after_chat:
            await conn.close()

# 播放音频
async def sendAudio(conn, audios):
    # 流控参数优化
    original_frame_duration = 60  # 原始帧时长（毫秒）
    adjusted_frame_duration = int(original_frame_duration * 0.8)  # 缩短20%
    total_frames = len(audios)  # 获取总帧数
    compensation = total_frames * (original_frame_duration - adjusted_frame_duration) / 1000  # 补偿时间（秒）

    start_time = time.perf_counter()
    play_position = 0  # 已播放时长（毫秒）

    for opus_packet in audios:
        if conn.client_abort:
            return

        # 计算带加速因子的预期时间
        expected_time = start_time + (play_position / 1000)
        current_time = time.perf_counter()

        # 流控等待（使用加速后的帧时长）
        delay = expected_time - current_time
        if delay > 0:
            await asyncio.sleep(delay)

        await conn.websocket.send(opus_packet)
        play_position += adjusted_frame_duration  # 使用调整后的帧时长

    # 补偿因加速损失的时长
    if compensation > 0:
        await asyncio.sleep(compensation)


async def send_tts_message(conn, state, text=None):
    """发送 TTS 状态消息"""
    message = {
        "type": "tts",
        "state": state,
        "session_id": conn.session_id
    }
    if text is not None:
        message["text"] = text

    # TTS播放结束
    if state == "stop":
        # 播放提示音
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get("stop_tts_notify_voice", "config/assets/tts_notify.mp3")
            audios, duration = conn.tts.audio_to_opus_data(stop_tts_notify_voice)
            await sendAudio(conn, audios)
        # 清除服务端讲话状态
        conn.clearSpeakStatus()

    # 发送消息到客户端
    await conn.websocket.send(json.dumps(message))


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
