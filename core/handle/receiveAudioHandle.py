from config.logger import setup_logging
import time
from core.utils.util import remove_punctuation_and_length
from core.handle.sendAudioHandle import send_stt_message

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
        # 音频太短了，无法识别
        if len(conn.asr_audio) < 3:
            conn.asr_server_receive = True
        else:
            text, file_path = await conn.asr.speech_to_text(conn.asr_audio, conn.session_id)
            logger.bind(tag=TAG).info(f"识别文本: {text}")
            text_len, text_without_punctuation = remove_punctuation_and_length(text)
            if await conn.music_handler.handle_music_command(conn, text_without_punctuation):
                conn.asr_server_receive = True
                conn.asr_audio.clear()
                return
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
            await conn.close()
            return True
    return False


async def startToChat(conn, text):
    # 异步发送 stt 信息
    await send_stt_message(conn, text)
    conn.executor.submit(conn.chat, text)


async def no_voice_close_connect(conn):
    if conn.client_no_voice_last_time == 0.0:
        conn.client_no_voice_last_time = time.time() * 1000
    else:
        no_voice_time = time.time() * 1000 - conn.client_no_voice_last_time
        close_connection_no_voice_time = conn.config.get("close_connection_no_voice_time", 120)
        if no_voice_time > 1000 * close_connection_no_voice_time:
            conn.client_abort = False
            conn.asr_server_receive = False
            prompt = "时间过得真快，我都好久没说话了。请你用十个字左右话跟我告别，以“再见”或“拜拜”为结尾"
            await startToChat(conn, prompt)
