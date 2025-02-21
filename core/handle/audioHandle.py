from config.logger import setup_logging
import json
import asyncio
import time
from core.utils.util import remove_punctuation_and_length, get_string_no_punctuation_or_emoji
import os
from pydub import AudioSegment
from pydub.playback import play
from concurrent.futures import ThreadPoolExecutor
import re
import uuid
import tempfile
import winsound  # Windows专用
import pygame
import traceback
import random
import difflib

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
        
        # 添加音乐命令处理
        if await handleMusicCommand(conn, text_without_punctuation):
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
            prompt = "时间过得真快，我都好久没说话了。请你用十个字左右话跟我告别，以“再见”或“拜拜”为结尾"
            await startToChat(conn, prompt)


async def play_local_music(conn, specific_file=None):
    """通过websocket发送音乐到端侧设备播放"""
    try:
        music_dir = os.path.abspath(conn.config.get("music_dir", "./music"))
        logger.bind(tag=TAG).info(f"音乐目录路径: {music_dir}")
        
        if not os.path.exists(music_dir):
            logger.bind(tag=TAG).error(f"音乐目录不存在: {music_dir}")
            return

        if specific_file:
            music_path = os.path.join(music_dir, specific_file)
            if not os.path.exists(music_path):
                logger.bind(tag=TAG).error(f"指定的音乐文件不存在: {music_path}")
                return
            selected_music = specific_file
        else:
            music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
            if not music_files:
                logger.bind(tag=TAG).error("未找到MP3音乐文件")
                return
            selected_music = random.choice(music_files)
            music_path = os.path.join(music_dir, selected_music)

        logger.bind(tag=TAG).info(f"准备播放: {selected_music}")
        
        # 发送TTS start消息
        await conn.websocket.send(json.dumps({
            "type": "tts",
            "state": "start",
            "session_id": conn.session_id
        }))

        # 发送sentence_start消息
        await conn.websocket.send(json.dumps({
            "type": "tts",
            "state": "sentence_start",
            "text": f"正在播放：{selected_music.replace('.mp3', '')}",
            "session_id": conn.session_id
        }))

        conn.is_playing_music = True
        
        try:
            logger.bind(tag=TAG).debug("开始转换音乐文件为opus格式")
            opus_packets, duration = conn.tts.wav_to_opus_data(music_path)
            logger.bind(tag=TAG).info(f"转换完成，获得 {len(opus_packets)} 个数据包，时长 {duration} 秒")
            
            # 发送sentence_end消息
            await conn.websocket.send(json.dumps({
                "type": "tts",
                "state": "sentence_end",
                "session_id": conn.session_id
            }))

            # 发送新的sentence_start消息
            await conn.websocket.send(json.dumps({
                "type": "tts",
                "state": "sentence_start",
                "text": selected_music,
                "session_id": conn.session_id
            }))
            
            # 计算每个数据包的播放时间（毫秒）
            packet_duration = (duration * 1000) / len(opus_packets)  # 每个包的持续时间（毫秒）
            logger.bind(tag=TAG).info(f"每个数据包的播放时间: {packet_duration:.2f}ms")
            
            total_sent = 0
            start_time = time.time()
            
            for i, opus_packet in enumerate(opus_packets):
                if not conn.is_playing_music:
                    break
                    
                # 计算应该经过的时间
                expected_time = start_time + (i * packet_duration / 1000)
                current_time = time.time()
                
                # 如果发送太快，等待一下
                if current_time < expected_time:
                    await asyncio.sleep(expected_time - current_time)
                
                await conn.websocket.send(opus_packet)
                total_sent += len(opus_packet)
                
                # 每100个包记录一次进度
                if i % 100 == 0:
                    logger.bind(tag=TAG).debug(f"已发送 {i}/{len(opus_packets)} 个数据包")
                
            logger.bind(tag=TAG).info(f"音乐数据发送完成，共发送 {total_sent} 字节")

            # 发送sentence_end消息
            await conn.websocket.send(json.dumps({
                "type": "tts",
                "state": "sentence_end",
                "session_id": conn.session_id
            }))
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"音乐转换或发送失败: {str(e)}")
            import traceback
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
        import traceback
        logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
    finally:
        conn.is_playing_music = False
        # 发送TTS stop消息
        await conn.websocket.send(json.dumps({
            "type": "tts",
            "state": "stop",
            "session_id": conn.session_id
        }))


async def handleMusicCommand(conn, text):
    """处理音乐播放指令（增强版）"""
    # 去除所有标点符号和空格
    clean_text = re.sub(r'[^\w\s]', '', text).strip()
    
    logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")
    
    # 1. 尝试匹配具体歌名
    music_dir = os.path.abspath(conn.config.get("music_dir", "./music"))
    logger.bind(tag=TAG).debug(f"音乐目录: {music_dir}")
    
    if os.path.exists(music_dir):
        music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
        logger.bind(tag=TAG).debug(f"找到的音乐文件: {music_files}")
        
        # 从用户输入中提取可能的歌名
        potential_song = None
        for keyword in ["听", "播放", "放"]:
            if keyword in clean_text:
                parts = clean_text.split(keyword)
                if len(parts) > 1:
                    potential_song = parts[1].strip()
                    break
        
        if potential_song:
            # 使用模糊匹配找到最匹配的歌曲
            best_match = None
            highest_ratio = 0
            
            for music_file in music_files:
                song_name = os.path.splitext(music_file)[0]
                # 计算相似度
                ratio = difflib.SequenceMatcher(None, potential_song, song_name).ratio()
                if ratio > highest_ratio and ratio > 0.4:  # 设置最小匹配阈值
                    highest_ratio = ratio
                    best_match = music_file
            
            if best_match:
                logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match} (匹配度: {highest_ratio})")
                await play_local_music(conn, specific_file=best_match)
                return True
            else:
                logger.bind(tag=TAG).info(f"未找到匹配的歌曲: {potential_song}")
    
    # 2. 检查是否是通用播放音乐命令
    music_related_keywords = conn.config.get("music_commands", [])
    if any(cmd in clean_text for cmd in music_related_keywords):
        await play_local_music(conn)
        return True
        
    return False
