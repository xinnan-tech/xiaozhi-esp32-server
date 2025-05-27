import time
import copy
from core.utils.util import remove_punctuation_and_length
from core.handle.sendAudioHandle import send_stt_message
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import audio_to_data

TAG = __name__


async def handleAudioMessage(conn, audio):
    if conn.vad is None:
        return
    if not conn.asr_server_receive:
        conn.logger.bind(tag=TAG).debug(f"前期数据处理中，暂停接收")
        return
    if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
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

           
            # 极简流式声纹检测调用
            is_owner,score = await conn.speaker.handle_audio_data(conn.asr_audio, conn.session_id)
            if is_owner:
                conn.logger.bind(tag=TAG).info(f"流式识别到主人音频，score={score}")
            else:
                conn.logger.bind(tag=TAG).info(f"流式未识别为主人，忽略音频，score={score}")

            raw_text, _ = await conn.asr.speech_to_text(
                conn.asr_audio, conn.session_id
            )  # 确保ASR模块返回原始文本
            conn.logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
            text_len, _ = remove_punctuation_and_length(raw_text)
            if text_len > 0:
                # 使用自定义模块进行上报
                enqueue_asr_report(conn, raw_text, copy.deepcopy(conn.asr_audio))

                await startToChat(conn, raw_text)
            else:
                conn.asr_server_receive = True
        conn.asr_audio.clear()
        conn.reset_vad_states()


async def startToChat(conn, text):
    if conn.need_bind:
        await check_bind_device(conn)
        return

    # 如果当日的输出字数大于限定的字数
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return

    # 首先进行意图分析
    intent_handled = await handle_user_intent(conn, text)

    if intent_handled:
        # 如果意图已被处理，不再进行聊天
        conn.asr_server_receive = True
        return

    # 意图未被处理，继续常规聊天流程
    await send_stt_message(conn, text)
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
            end_prompt = conn.config.get("end_prompt", {})
            if end_prompt and end_prompt.get("enable", True) is False:
                conn.logger.bind(tag=TAG).info("结束对话，无需发送结束提示语")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "请你以“时间过得真快”未来头，用富有感情、依依不舍的话来结束这场对话吧。！"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
    await send_stt_message(conn, text)
    conn.tts_first_text_index = 0
    conn.tts_last_text_index = 0
    conn.llm_finish_task = True
    file_path = "config/assets/max_output_size.wav"
    opus_packets, _ = audio_to_data(file_path)
    conn.audio_play_queue.put((opus_packets, text, 0))
    conn.close_after_chat = True


async def check_bind_device(conn):
    if conn.bind_code:
        # 确保bind_code是6位数字
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"无效的绑定码格式: {conn.bind_code}")
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
        opus_packets, _ = audio_to_data(music_path)
        conn.audio_play_queue.put((opus_packets, text, 0))

        # 逐个播放数字
        for i in range(6):  # 确保只播放6位数字
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets, _ = audio_to_data(num_path)
                conn.audio_play_queue.put((num_packets, None, i + 1))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                continue
    else:
        text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
        await send_stt_message(conn, text)
        conn.tts_first_text_index = 0
        conn.tts_last_text_index = 0
        conn.llm_finish_task = True
        music_path = "config/assets/bind_not_found.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.audio_play_queue.put((opus_packets, text, 0))
