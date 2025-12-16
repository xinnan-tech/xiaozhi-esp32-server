import json
import time
import asyncio
from core.utils import textUtils
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import (
    SentenceType,
    MessageTag,
)
from core.utils.textUtils import strip_emotion_tags
from core.utils.opus import pack_opus_with_header
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

async def sendAudioMessage(conn, sentenceType, audios, text, message_tag=MessageTag.NORMAL):
    if conn.tts.tts_audio_first_sentence:
        conn.tts.tts_audio_first_sentence = False
        await send_tts_message(conn, "start", None, message_tag)
        
        # 记录首句 TTS 播放时间（端到端延迟的终点）
        first_audio_time = time.time() * 1000
        
        # 计算 TTS 首包延迟（输入到输出）
        tts_first_package_delay = 0
        if hasattr(conn, '_latency_tts_first_text_time') and conn._latency_tts_first_text_time:
            tts_first_package_delay = first_audio_time - conn._latency_tts_first_text_time
        
        # 计算端到端延迟
        e2e_total_delay = 0
        if hasattr(conn, '_latency_voice_end_time'):
            e2e_total_delay = first_audio_time - conn._latency_voice_end_time
        
        conn.logger.bind(tag=TAG).info(
            f"🔊 [延迟追踪] 首句TTS开始播放 | "
            f"TTS首包延迟: {tts_first_package_delay:.0f}ms | "
            f"⏱️  端到端总延迟: {e2e_total_delay:.0f}ms (用户说完→首句播放) | "
            f"文本: {text if text else '(无文本)'}"
        )

    if sentenceType == SentenceType.FIRST:
        await send_tts_message(conn, "sentence_start", text, message_tag)

    await sendAudio(conn, audios, message_tag=message_tag)
    # 发送句子开始消息
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).info(f"发送音频消息: {sentenceType}, {text}")

    # 发送结束消息（如果是最后一个文本）
    # 条件1: llm_finish_task=True 且 LAST (正常结束)
    # 条件2: LAST 且 MOCK (超时触发的结束)
    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None, message_tag)
        if message_tag == MessageTag.MOCK:
            return
        conn.client_is_speaking = False
        if conn.close_after_chat:
            await conn.close()


def calculate_timestamp_and_sequence(conn, start_time, packet_index, frame_duration=60):
    """
    计算音频数据包的时间戳和序列号
    Args:
        conn: 连接对象
        start_time: 起始时间（性能计数器值）
        packet_index: 数据包索引
        frame_duration: 帧时长（毫秒），匹配 Opus 编码
    Returns:
        tuple: (timestamp, sequence)
    """
    # 计算时间戳（使用播放位置计算）
    timestamp = int((start_time + packet_index * frame_duration / 1000) * 1000) % (
        2**32
    )

    # 计算序列号
    if hasattr(conn, "audio_flow_control"):
        sequence = conn.audio_flow_control["sequence"]
    else:
        sequence = packet_index  # 如果没有流控状态，直接使用索引

    return timestamp, sequence


async def _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence):
    """
    发送带16字节头部的opus数据包给mqtt_gateway
    Args:
        conn: 连接对象
        opus_packet: opus数据包
        timestamp: 时间戳
        sequence: 序列号
    """
    # 为opus数据包添加16字节头部
    header = bytearray(16)
    header[0] = 1  # type
    header[2:4] = len(opus_packet).to_bytes(2, "big")  # payload length
    header[4:8] = sequence.to_bytes(4, "big")  # sequence
    header[8:12] = timestamp.to_bytes(4, "big")  # 时间戳
    header[12:16] = len(opus_packet).to_bytes(4, "big")  # opus长度

    # 发送包含头部的完整数据包
    complete_packet = bytes(header) + opus_packet
    await conn.websocket.send(complete_packet)

async def _send_audio_with_header(conn, audios, message_tag=MessageTag.NORMAL):
    if audios is None or len(audios) == 0:
        return
    complete_packet = pack_opus_with_header(audios, message_tag)
    await conn.websocket.send(complete_packet)


# 播放音频
async def sendAudio(conn, audios, frame_duration=60, message_tag=MessageTag.NORMAL):
    """
    发送单个opus包，支持流控
    Args:
        conn: 连接对象
        opus_packet: 单个opus数据包
        pre_buffer: 快速发送音频
        frame_duration: 帧时长（毫秒），匹配 Opus 编码
    """
    if audios is None or len(audios) == 0:
        return

    # 获取发送延迟配置
    send_delay = conn.config.get("tts_audio_send_delay", -1) / 1000.0

    if isinstance(audios, bytes):
        if conn.client_abort:
            return

        conn.last_activity_time = time.time() * 1000

        # 获取或初始化流控状态
        if not hasattr(conn, "audio_flow_control"):
            conn.audio_flow_control = {
                "last_send_time": 0,
                "packet_count": 0,
                "start_time": time.perf_counter(),
                "sequence": 0,  # 添加序列号
            }

        flow_control = conn.audio_flow_control
        current_time = time.perf_counter()
        
        # 流控配置
        pre_buffer_count = conn.config.get("tts_audio_pre_buffer_count", 8)  # 预缓冲包数（约480ms）
        speed_multiplier = conn.config.get("tts_audio_speed_multiplier", 1.0)  # 发送速度倍率
        
        if send_delay > 0:
            # 使用固定延迟
            await asyncio.sleep(send_delay)
        elif flow_control["packet_count"] < pre_buffer_count:
            # 预缓冲阶段：快速发送，不做延迟
            pass
        else:
            # 按略快于实时的速度发送
            packets_after_prebuffer = flow_control["packet_count"] - pre_buffer_count
            expected_time = flow_control["start_time"] + (
                packets_after_prebuffer * frame_duration / 1000 / speed_multiplier
            )
            delay = expected_time - current_time
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                # 纠正误差
                flow_control["start_time"] += abs(delay)

        if conn.conn_from_mqtt_gateway:
            # 计算时间戳和序列号
            timestamp, sequence = calculate_timestamp_and_sequence(
                conn,
                flow_control["start_time"],
                flow_control["packet_count"],
                frame_duration,
            )
            # 调用通用函数发送带头部的数据包
            await _send_to_mqtt_gateway(conn, audios, timestamp, sequence)
        else:
            # 直接发送opus数据包，不添加头部
            await _send_audio_with_header(conn, audios, message_tag)

        # 更新流控状态
        flow_control["packet_count"] += 1
        flow_control["sequence"] += 1
        flow_control["last_send_time"] = time.perf_counter()
    else:
        # 文件型音频走普通播放
        start_time = time.perf_counter()
        play_position = 0

        # 执行预缓冲
        pre_buffer_frames = min(3, len(audios))
        for i in range(pre_buffer_frames):
            if conn.conn_from_mqtt_gateway:
                # 计算时间戳和序列号
                timestamp, sequence = calculate_timestamp_and_sequence(
                    conn, start_time, i, frame_duration
                )
                # 调用通用函数发送带头部的数据包
                await _send_to_mqtt_gateway(conn, audios[i], timestamp, sequence)
            else:
                # 直接发送预缓冲包，不添加头部
                await _send_audio_with_header(conn, audios[i], message_tag)
        remaining_audios = audios[pre_buffer_frames:]

        # 播放剩余音频帧
        for i, opus_packet in enumerate(remaining_audios):
            if conn.client_abort:
                break

            # 重置没有声音的状态
            conn.last_activity_time = time.time() * 1000

            if send_delay > 0:
                # 固定延迟模式
                await asyncio.sleep(send_delay)
            else:
                 # 计算预期发送时间
                expected_time = start_time + (play_position / 1000)
                current_time = time.perf_counter()
                delay = expected_time - current_time
                if delay > 0:
                    await asyncio.sleep(delay)

            if conn.conn_from_mqtt_gateway:
                # 计算时间戳和序列号（使用当前的数据包索引确保连续性）
                packet_index = pre_buffer_frames + i
                timestamp, sequence = calculate_timestamp_and_sequence(
                    conn, start_time, packet_index, frame_duration
                )
                # 调用通用函数发送带头部的数据包
                await _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence)
            else:
                # 直接发送opus数据包，不添加头部
                await _send_audio_with_header(conn, opus_packet, message_tag)

            play_position += frame_duration


async def send_tts_message(conn, state, text=None, message_tag=MessageTag.NORMAL):
    """发送 TTS 状态消息
    
    Args:
        conn: Connection object
        state: TTS state (start, sentence_start, stop)
        text: Optional text content
        message_tag: Message tag for categorization
    """
    if text is None and state == "sentence_start":
        return
    
    message = {
        "type": "tts", 
        "state": state,
        "session_id": conn.session_id,
        "message_tag": message_tag.value,
    }
    if text is not None:
        text = textUtils.check_emoji(text)
        text = strip_emotion_tags(text)
        message["text"] = text

    # TTS播放结束
    if state == "stop":
        # 播放提示音
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios = audio_to_data(stop_tts_notify_voice, is_opus=True)
            await sendAudio(conn, audios)
        # 清除服务端讲话状态
        conn.clearSpeakStatus()

    # 发送消息到客户端
    logger.bind(tag=TAG).info(f"发送TTS消息: {message}")
    await conn.websocket.send(json.dumps(message))


async def send_stt_message(conn, text):
    """发送 STT 状态消息"""
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    # 解析JSON格式，提取实际的用户说话内容
    display_text = text
    try:
        # 尝试解析JSON格式
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # 如果是包含说话人信息的JSON格式，只显示content部分
                display_text = parsed_data["content"]
                # 保存说话人信息到conn对象
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # 如果不是JSON格式，直接使用原始文本
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    conn.client_is_speaking = True
    await send_tts_message(conn, "start")
