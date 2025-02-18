from config.logger import setup_logging
import json
import asyncio
import time
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji

TAG = __name__
logger = setup_logging()


async def handleAudioMessage(conn, audio):
    if not conn.asr_server_receive:
        logger.bind(tag=TAG).debug(f"前期数据处理中，暂停接收")
        return
    if conn.client_listen_mode == "auto":
        have_voice = conn.vad.is_vad(conn, audio)
    else:
        have_voice = conn.client_have_voice

    # 如果本次没有声音，本段也没声音，就把声音丢弃了
    if have_voice == False and conn.client_have_voice == False:
        await no_voice_close_connect(conn)
        conn.asr_audio.clear()
        return
    conn.client_no_voice_last_time = 0.0
    conn.asr_audio.append(audio)
    # 如果本段有声音，且已经停止了
    if conn.client_voice_stop:
        conn.client_abort = False
        conn.asr_server_receive = False
        text, file_path = conn.asr.speech_to_text(conn.asr_audio, conn.session_id)
        logger.bind(tag=TAG).info(f"识别文本: {text}")
        text_len, text_without_punctuation = remove_punctuation_and_length(text)
        if text_len <= conn.max_cmd_length and await handleCMDMessage(conn, text_without_punctuation):
            return
        if text_len > 0:
            await startToChat(conn, text)
        else:
            conn.asr_server_receive = True
        conn.asr_audio.clear()
        conn.reset_vad_states()


async def handleCMDMessage(conn, text):
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            logger.bind(tag=TAG).info("识别到明确的退出命令".format(text))
            await finishToChat(conn)
            return True
    return False


async def finishToChat(conn):
    await conn.close()


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


async def startToChat(conn, text):
    # 异步发送 stt 信息
    stt_task = asyncio.create_task(
        schedule_with_interrupt(0, send_stt_message(conn, text))
    )
    conn.scheduled_tasks.append(stt_task)
    conn.executor.submit(conn.chat, text)


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
                schedule_with_interrupt(stop_duration, finishToChat(conn))
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


async def no_voice_close_connect(conn):
    if conn.client_no_voice_last_time == 0.0:
        conn.client_no_voice_last_time = time.time() * 1000
    else:
        no_voice_time = time.time() * 1000 - conn.client_no_voice_last_time
        close_connection_no_voice_time = conn.config.get("close_connection_no_voice_time", 120)
        if no_voice_time > 1000 * close_connection_no_voice_time:
            conn.client_abort = False
            conn.asr_server_receive = False
            prompt = "时间过得真快，我都好久没说话了。请你用十个字左右话跟我告别，以“再见”或“拜拜拜”为结尾"
            await startToChat(conn, prompt)
