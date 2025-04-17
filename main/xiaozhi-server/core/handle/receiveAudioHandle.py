from config.logger import setup_logging
import time
import asyncio
from core.utils.util import remove_punctuation_and_length
from core.handle.sendAudioHandle import send_stt_message
from core.handle.helloHandle import checkWakeupWords

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
        conn.asr_audio.append(audio)
        conn.asr_audio = conn.asr_audio[
            -10:
        ]  # 保留最新的10帧音频内容，解决ASR句首丢字问题
        return
    conn.client_no_voice_last_time = 0.0
    conn.asr_audio.append(audio)
    # 如果本段有声音，且已经停止了
    if conn.client_voice_stop:
        conn.client_abort = False
        conn.asr_server_receive = False
        # 音频太短了，无法识别
        if len(conn.asr_audio) < 15:
            conn.asr_server_receive = True
        else:
            text, _ = await conn.asr.speech_to_text(conn.asr_audio, conn.session_id)
            logger.bind(tag=TAG).info(f"识别文本: {text}")
            text_len, _ = remove_punctuation_and_length(text)
            if text_len > 0:
                await startToChat(conn, text)
            else:
                conn.asr_server_receive = True
        conn.asr_audio.clear()
        conn.reset_vad_states()


async def handle_user_intent(conn, text):
    # 检查是否有明确的退出命令
    if await check_direct_exit(conn, text):
        return True
    # 检查是否是唤醒词
    if await checkWakeupWords(conn, text):
        return True
    
    return False


async def check_direct_exit(conn, text):
    """检查是否有明确的退出命令"""
    _, text = remove_punctuation_and_length(text)
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            logger.bind(tag=TAG).info(f"识别到明确的退出命令: {text}")
            await send_stt_message(conn, text)
            await conn.close()
            return True
    return False

async def startToChat(conn, text):
    if conn.need_bind:
        await check_bind_device(conn)
        return
    # 首先进行意图分析
    intent_handled = await handle_user_intent(conn, text)

    if intent_handled:
        # 如果意图已被处理，不再进行聊天
        conn.asr_server_receive = True
        return

    # 意图未被处理，继续常规聊天流程
    await send_stt_message(conn, text)
    if conn.use_function_call_mode:
        # 使用支持function calling的聊天方法
        conn.executor.submit(conn.chat_with_function_calling, text)
    elif conn.use_function_call_by_prompt:
        conn.executor.submit(conn.chat_with_function_calling, text, False, True)
    else:
        conn.executor.submit(conn.chat, text)


async def no_voice_close_connect(conn):
    if conn.client_no_voice_last_time == 0.0:
        conn.client_no_voice_last_time = time.time() * 1000
    else:
        no_voice_time = time.time() * 1000 - conn.client_no_voice_last_time
        close_connection_no_voice_time = int(
            conn.config.get("close_connection_no_voice_time", 120)
        )
        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            conn.asr_server_receive = False
            prompt = (
                "请你以“时间过得真快”未来头，用富有感情、依依不舍的话来结束这场对话吧。"
            )
            await startToChat(conn, prompt)


async def check_bind_device(conn):
    if conn.bind_code:
        # 确保bind_code是6位数字
        if len(conn.bind_code) != 6:
            logger.bind(tag=TAG).error(f"无效的绑定码格式: {conn.bind_code}")
            text = "绑定码格式错误，请检查配置。"
            await send_stt_message(conn, text)
            return

        text = f"请登录控制面板，输入{conn.bind_code}，绑定设备。"
        await send_stt_message(conn, text)
        conn.tts_first_text_index = 0
        conn.tts_last_text_index = 6
        conn.llm_finish_task = True

        # 播放提示音
        music_path = "config/assets/bind_code.wav"
        opus_packets, _ = conn.tts.audio_to_opus_data(music_path)
        conn.audio_play_queue.put((opus_packets, text, 0))

        # 逐个播放数字
        for i in range(6):  # 确保只播放6位数字
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets, _ = conn.tts.audio_to_opus_data(num_path)
                conn.audio_play_queue.put((num_packets, None, i + 1))
            except Exception as e:
                logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                continue
    else:
        text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
        await send_stt_message(conn, text)
        conn.tts_first_text_index = 0
        conn.tts_last_text_index = 0
        conn.llm_finish_task = True
        music_path = "config/assets/bind_not_found.wav"
        opus_packets, _ = conn.tts.audio_to_opus_data(music_path)
        conn.audio_play_queue.put((opus_packets, text, 0))
