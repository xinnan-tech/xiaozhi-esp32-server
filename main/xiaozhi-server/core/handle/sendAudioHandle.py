import json
import time
import asyncio
from core.utils import textUtils
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType

TAG = __name__


async def sendAudioMessage(conn, sentenceType, audios, text):
    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts.tts_audio_first_sentence = False
        await send_tts_message(conn, "start", None)

    if sentenceType == SentenceType.FIRST:
        await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios)
    # 发送句子开始消息
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).info(f"发送音频消息: {sentenceType}, {text}")

    # 发送结束消息（如果是最后一个文本）
    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        if hasattr(conn, "audio_flow_control"):
            flow_control = conn.audio_flow_control
            delay = (flow_control["start_time"] + flow_control["packet_count"] * 60 / 1000) - flow_control["last_send_time"]
            conn.logger.bind(tag=TAG).info(f"等待误差后发送stop指令 : {delay}")
            if delay > 0:
                await asyncio.sleep(delay * 20 + 0.06)
            delattr(conn, "audio_flow_control")
        await send_tts_message(conn, "stop", None)
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


# 播放音频
async def sendAudio(conn, audios, frame_duration=60):
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

    if isinstance(audios, bytes):
        if conn.client_abort:
            return

        conn.last_activity_time = time.time() * 1000

        # 获取或初始化流控状态
        if not hasattr(conn, "audio_flow_control"):
            start_time = time.perf_counter()
            conn.audio_flow_control = {
                "last_send_time": 0,
                "packet_count": 0,
                "start_time": start_time,
                "sequence": 0,  # 添加序列号
            }

        flow_control = conn.audio_flow_control
        current_time = time.perf_counter()
        # 计算预期发送时间
        expected_time = flow_control["start_time"] + (
            flow_control["packet_count"] * frame_duration / 1000
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
            await conn.websocket.send(audios)

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
                await conn.websocket.send(audios[i])
        remaining_audios = audios[pre_buffer_frames:]

        # 播放剩余音频帧
        for i, opus_packet in enumerate(remaining_audios):
            if conn.client_abort:
                break

            # 重置没有声音的状态
            conn.last_activity_time = time.time() * 1000

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
                await conn.websocket.send(opus_packet)

            play_position += frame_duration


async def send_tts_message(conn, state, text=None):
    """发送 TTS 状态消息"""
    if text is None and state == "sentence_start":
        return
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

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
