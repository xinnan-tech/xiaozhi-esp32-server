import logging
import json
import asyncio
import time
import traceback

import numpy as np
import opuslib
import torch
import torchaudio

from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji

logger = logging.getLogger(__name__)


def resample_audio(audio, original_sample_rate, target_sample_rate=16000):
    """ 使用 torchaudio 对音频进行重采样 """
    if original_sample_rate != target_sample_rate:
        resampler = torchaudio.transforms.Resample(orig_freq=original_sample_rate, new_freq=target_sample_rate)
        audio = resampler(audio)
    return audio


def opus_to_pcm(opus_data, original_sample_rate):
    """ 将 Opus 音频解码为 PCM """
    decoder = opuslib.Decoder(original_sample_rate, 1)
    pcm_data = decoder.decode(opus_data, 1440)  # 24000 采样率每帧1440个样本（60ms）
    return pcm_data


def pcm_to_opus(pcm_data, sample_rate):
    """ 将 PCM 数据编码为 Opus 格式 """
    encoder = opuslib.Encoder(sample_rate, 1, opuslib.APPLICATION_AUDIO)
    opus_data = encoder.encode(pcm_data,960)
    return opus_data


def convert_opus_24k_to_16k(opus_data_24k):
    # 解码 Opus 24k 数据为 PCM
    pcm_data = opus_to_pcm(opus_data_24k, 24000)

    # 将 PCM 数据重采样到 16k
    waveform = torch.from_numpy(np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0)  # 转换为 float32 张量
    resampled_waveform = resample_audio(waveform, 24000, 16000)

    # 转换回 int16 格式的 PCM 数据
    resampled_pcm_data = (resampled_waveform.numpy() * 32768.0).astype(np.int16)

    # 重新编码为 Opus 格式
    opus_data_16k = pcm_to_opus(resampled_pcm_data.tobytes(), 16000)
    return opus_data_16k

async def handleAudioMessage(conn, audio):
    # 24k转16k
    audio = convert_opus_24k_to_16k(audio)
    if not conn.asr_server_receive:
        logger.debug(f"前期数据处理中，暂停接收")
        return
    if conn.client_listen_mode == "auto":
        have_voice = conn.vad.is_vad(conn, audio)
    else:
        have_voice = conn.client_have_voice

    # 如果本次没有声音，本段也没声音，就把声音丢弃了
    if have_voice == False and conn.client_have_voice == False:
        conn.asr_audio.clear()
        return
    conn.asr_audio.append(audio)
    # 如果本段有声音，且已经停止了
    if conn.client_voice_stop:
        conn.client_abort = False
        conn.asr_server_receive = False
        text, file_path = conn.asr.speech_to_text(conn.asr_audio, conn.session_id)
        logger.info(f"识别文本: {text}")
        text_len = remove_punctuation_and_length(text)
        if text_len > 0:
            await startToChat(conn, text)
        else:
            conn.asr_server_receive = True
        conn.asr_audio.clear()
        conn.reset_vad_states()

async def startToChat(conn, text):
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
    conn.executor.submit(conn.chat, text)

async def sendAudioMessageStream(conn, audios_queue, duration, text):
    base_delay = conn.tts_duration

    if text == conn.tts_first_text:
        conn.tts_start_speak_time = time.time()
        await conn.websocket.send(json.dumps({
            "type": "tts",
            "state": "start",
            "session_id": conn.session_id
        }))

    # 调度文字显示任务
    text_task = asyncio.create_task(
        schedule_with_interrupt(
            base_delay - 0.5,
            send_sentence_start(conn, text)
        )
    )
    conn.scheduled_tasks.append(text_task)

    conn.tts_duration = 0

    # 发送音频数据 -获取队列的数据发送
    start_time = time.time()
    check_index = 0
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


            audio_data_chunke_data = audio_data_chunke.get('data') if audio_data_chunke else None

            if audio_data_chunke:
                start_time = time.time()
            #检查是否超过 5 秒没有数据
            if time.time() - start_time > 5:
                print("超过5秒没有数据，退出。")
                break

            if audio_data_chunke and audio_data_chunke.get("end", True):
                break

            if audio_data_chunke_data:
                queue_duration = time.time() - start_get_queue
                last_duration = conn.tts_duration - queue_duration
                if last_duration <= 0 :
                    last_duration = 0
                opus_datas, duration = conn.tts.wav_to_opus_data_audio(audio_data_chunke_data)
                conn.tts_duration = duration + last_duration + 0.5
                for opus_packet in opus_datas:
                    await conn.websocket.send(opus_packet)
                print(f"已获取音频数据，长度为 {len(audio_data_chunke_data)}，总长度为 {len(audio_data_chunke_data)}")
                start_time = time.time()  # 更新获取数据的时间
        except Exception as e:
            print(f"发生错误: {e}")
            traceback.print_exc()  # 打印错误堆栈

    if conn.llm_finish_task and text == conn.tts_last_text:
        stop_duration = conn.tts_duration + 0.5
        stop_task = asyncio.create_task(
            schedule_with_interrupt(stop_duration, send_tts_stop(conn, text))
        )
        conn.scheduled_tasks.append(stop_task)

async def sendAudioMessage(conn, audios, duration, text):
    base_delay = conn.tts_duration

    if text == conn.tts_first_text:
        conn.tts_start_speak_time = time.time()
        await conn.websocket.send(json.dumps({
            "type": "tts",
            "state": "start",
            "session_id": conn.session_id
        }))

    # 调度文字显示任务
    text_task = asyncio.create_task(
        schedule_with_interrupt(
            base_delay - 0.5,
            send_sentence_start(conn, text)
        )
    )
    conn.scheduled_tasks.append(text_task)

    conn.tts_duration = conn.tts_duration + duration

    # 发送音频数据
    for opus_packet in audios:
        await conn.websocket.send(opus_packet)

    if conn.llm_finish_task and text == conn.tts_last_text:
        stop_duration = conn.tts_duration - (time.time() - conn.tts_start_speak_time)
        stop_task = asyncio.create_task(
            schedule_with_interrupt(stop_duration, send_tts_stop(conn, text))
        )
        conn.scheduled_tasks.append(stop_task)


async def send_sentence_start(conn, text):
    await conn.websocket.send(json.dumps({
        "type": "tts",
        "state": "sentence_start",
        "text": text,
        "session_id": conn.session_id
    }))


async def send_tts_stop(conn, text):
    conn.clearSpeakStatus()
    await conn.websocket.send(json.dumps({
        "type": "tts",
        "state": "sentence_end",
        "text": text,
        "session_id": conn.session_id
    }))
    await conn.websocket.send(json.dumps({
        "type": "tts",
        "state": "stop",
        "session_id": conn.session_id
    }))


async def schedule_with_interrupt(delay, coro):
    """可中断的延迟调度"""
    try:
        await asyncio.sleep(delay)
        await coro
    except asyncio.CancelledError:
        pass
