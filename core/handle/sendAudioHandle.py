import traceback

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


async def sendAudioMessageStream(conn, audios_queue, text):
    # 发送句子开始消息
    if text == conn.tts_first_text:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts_start_speak_time = time.perf_counter()
    await send_tts_message(conn, "sentence_start", text)

    # 初始化流控参数
    frame_duration = 60  # 毫秒
    start_time = time.perf_counter()  # 使用高精度计时器
    play_position = 0  # 已播放的时长（毫秒）
    time_out_stop = False
    while True:
        try:
            start_get_queue = time.time()
            # 尝试获取数据，如果没有数据，则等待一小段时间再试
            audio_data_chunke = None
            try:
                audio_data_chunke = audios_queue.get(timeout=5)  # 设置超时为1秒
            except Exception as e:
                # 如果超时，继续等待
                print(f"获取队列超时～{e}")

            audio_opus_datas = audio_data_chunke.get('data') if audio_data_chunke else None
            duration =  audio_data_chunke.get('duration') if audio_data_chunke else 0

            if audio_data_chunke:
                start_time = time.time()
            # 检查是否超过 5 秒没有数据
            if time.time() - start_time > 5:
                logger.bind(tag=TAG).error("超过5秒没有数据，退出。")
                time_out_stop = True
                break

            if audio_data_chunke and audio_data_chunke.get("end", True):
                break

            if audio_opus_datas:
                queue_duration = time.time() - start_get_queue
                last_duration = conn.tts_duration - queue_duration
                if last_duration <= 0:
                    last_duration = 0
                conn.tts_duration = duration + last_duration + 0.5
                for opus_packet in audio_opus_datas:
                    await conn.websocket.send(opus_packet)
                start_time = time.time()  # 更新获取数据的时间
        except Exception as e:
            logger.bind(tag=TAG).error(f"发生错误: {e}")
            traceback.print_exc()  # 打印错误堆栈
    await send_tts_message(conn, "sentence_end", text)
    # 发送结束消息（如果是最后一个文本）
    if (conn.llm_finish_task and text == conn.tts_last_text) or time_out_stop:
        if conn.tts_duration > 0:
            await asyncio.sleep(conn.tts_duration)
        await send_tts_message(conn, 'stop', None)
        if await isLLMWantToFinish(text):
            await conn.close()

async def sendAudioMessage(conn, audios, text):
    # 发送句子开始消息
    if text == conn.tts_first_text:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts_start_speak_time = time.perf_counter()
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
    if conn.llm_finish_task and text == conn.tts_last_text:
        await send_tts_message(conn, 'stop', None)
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
