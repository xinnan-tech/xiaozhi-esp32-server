import traceback

from config.logger import setup_logging
import json
import asyncio
import time
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji

TAG = __name__
logger = setup_logging()


async def sendAudioMessageStream(conn, audios_queue, text, text_index=0, llm_finish_task=False):
    # 发送句子开始消息
    if text_index == conn.tts_first_text_index:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
    await send_tts_message(conn, "sentence_start", text)

    # 初始化流控参数
    frame_duration = 60  # 毫秒
    start_time = time.time()  # 使用高精度计时器
    # 初始化流控参数
    frame_duration = 60  # 毫秒
    start_time_chunk = time.perf_counter()  # 使用高精度计时器
    play_position = 0  # 已播放的时长（毫秒）
    while True:
        try:
            start_get_queue = time.time()
            # 尝试获取数据，如果没有数据，则等待一小段时间再试
            audio_data_chunke = None
            try:
                audio_data_chunke = audios_queue.get(timeout=5)  # 设置超时为1秒
            except Exception as e:
                # 如果超时，继续等待
                logger.bind(tag=TAG).error(f"获取队列超时～{e}")

            audio_opus_datas = audio_data_chunke.get('data') if audio_data_chunke else None
            duration = audio_data_chunke.get('duration') if audio_data_chunke else 0

            if audio_data_chunke:
                start_time = time.time()
            # 检查是否超过 5 秒没有数据
            if time.time() - start_time > 15:
                logger.bind(tag=TAG).error("超过15秒没有数据，退出。")
                break

            if audio_data_chunke and audio_data_chunke.get("end", True):
                break

            if audio_opus_datas:
                for opus_packet in audio_opus_datas:
                    if conn.client_abort:
                        return
                    # 计算当前包的预期发送时间
                    # 计算当前包的预期发送时间
                    expected_time = start_time_chunk + (play_position / 1000)
                    current_time = time.perf_counter()

                    # 等待直到预期时间
                    delay = expected_time - current_time
                    if delay > 0:
                        await asyncio.sleep(delay)
                    logger.bind(tag=TAG).info(f'发送数据长度：{len(opus_packet)}')
                    await conn.websocket.send(opus_packet)
                    play_position += frame_duration  # 更新播放位置
                start_time = time.time()  # 更新获取数据的时间
        except Exception as e:
            logger.bind(tag=TAG).error(f"发生错误: {e}")
            traceback.print_exc()  # 打印错误堆栈
    await send_tts_message(conn, "sentence_end", text)

    print(f'{text_index}-{conn.tts_last_text_index}')
    # 发送结束消息（如果是最后一个文本）
    logger.bind(tag=TAG).info(f"{conn.llm_finish_task},{text_index},{conn.tts_last_text_index}")
    if conn.llm_finish_task and text_index == conn.tts_last_text_index:
        expected_time = start_time_chunk + (play_position / 1000)
        current_time = time.perf_counter()
        # 等待直到预期时间
        delay = expected_time - current_time
        if delay > 0:
            await asyncio.sleep(delay)
        await send_tts_message(conn, 'stop', None)
        if conn.close_after_chat or "拜拜" in text or "再见" in text:
            await conn.close()



async def sendAudioMessage(conn, audios, text, text_index=0):
    # 发送句子开始消息
    if text_index == conn.tts_first_text_index:
        logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
    await send_tts_message(conn, "sentence_start", text)

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

    await send_tts_message(conn, "sentence_end", text)

    # 发送结束消息（如果是最后一个文本）
    if conn.llm_finish_task and text_index == conn.tts_last_text_index:
        await send_tts_message(conn, 'stop', None)
        if conn.close_after_chat:
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
