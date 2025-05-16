"""
TTS上报功能已集成到ConnectionHandler类中。

上报功能包括：
1. 每个连接对象拥有自己的上报队列和处理线程
2. 上报线程的生命周期与连接对象绑定
3. 使用ConnectionHandler.enqueue_tts_report方法进行上报

具体实现请参考core/connection.py中的相关代码。
"""

import opuslib_next

from config.manage_api_client import report as manage_report

TAG = __name__


def report(conn, type, text, opus_data):
    """执行聊天记录上报操作

    Args:
        conn: 连接对象
        type: 上报类型，1为用户，2为智能体
        text: 合成文本
        opus_data: opus音频数据
    """
    try:
        if opus_data:
            audio_data = opus_to_wav(conn, opus_data)
        else:
            audio_data = None
        # 执行上报
        manage_report(
            mac_address=conn.device_id,
            session_id=conn.session_id,
            chat_type=type,
            content=text,
            audio=audio_data,
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"聊天记录上报失败: {e}")


def opus_to_wav(conn, opus_data):
    """将Opus数据转换为WAV格式的字节流

    Args:
        output_dir: 输出目录（保留参数以保持接口兼容）
        opus_data: opus音频数据

    Returns:
        bytes: WAV格式的音频数据
    """
    decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
    pcm_data = []

    for opus_packet in opus_data:
        try:
            pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
            pcm_data.append(pcm_frame)
        except opuslib_next.OpusError as e:
            conn.logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

    if not pcm_data:
        raise ValueError("没有有效的PCM数据")

    # 创建WAV文件头
    pcm_data_bytes = b"".join(pcm_data)
    num_samples = len(pcm_data_bytes) // 2  # 16-bit samples

    # WAV文件头
    wav_header = bytearray()
    wav_header.extend(b"RIFF")  # ChunkID
    wav_header.extend((36 + len(pcm_data_bytes)).to_bytes(4, "little"))  # ChunkSize
    wav_header.extend(b"WAVE")  # Format
    wav_header.extend(b"fmt ")  # Subchunk1ID
    wav_header.extend((16).to_bytes(4, "little"))  # Subchunk1Size
    wav_header.extend((1).to_bytes(2, "little"))  # AudioFormat (PCM)
    wav_header.extend((1).to_bytes(2, "little"))  # NumChannels
    wav_header.extend((16000).to_bytes(4, "little"))  # SampleRate
    wav_header.extend((32000).to_bytes(4, "little"))  # ByteRate
    wav_header.extend((2).to_bytes(2, "little"))  # BlockAlign
    wav_header.extend((16).to_bytes(2, "little"))  # BitsPerSample
    wav_header.extend(b"data")  # Subchunk2ID
    wav_header.extend(len(pcm_data_bytes).to_bytes(4, "little"))  # Subchunk2Size

    # 返回完整的WAV数据
    return bytes(wav_header) + pcm_data_bytes


def enqueue_tts_report(conn, text, opus_data):
    if not conn.read_config_from_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    """将TTS数据加入上报队列

    Args:
        conn: 连接对象
        text: 合成文本
        opus_data: opus音频数据
    """
    try:
        # 使用连接对象的队列，传入文本和二进制数据而非文件路径
        if conn.chat_history_conf == 2:
            conn.report_queue.put((2, text, opus_data))
            conn.logger.bind(tag=TAG).debug(
                f"TTS数据已加入上报队列: {conn.device_id}, 音频大小: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((2, text, None))
            conn.logger.bind(tag=TAG).debug(
                f"TTS数据已加入上报队列: {conn.device_id}, 不上报音频"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"加入TTS上报队列失败: {text}, {e}")


def enqueue_asr_report(conn, text, opus_data):
    if not conn.read_config_from_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    """将ASR数据加入上报队列

    Args:
        conn: 连接对象
        text: 合成文本
        opus_data: opus音频数据
    """
    try:
        # 使用连接对象的队列，传入文本和二进制数据而非文件路径
        if conn.chat_history_conf == 2:
            conn.report_queue.put((1, text, opus_data))
            conn.logger.bind(tag=TAG).debug(
                f"ASR数据已加入上报队列: {conn.device_id}, 音频大小: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((1, text, None))
            conn.logger.bind(tag=TAG).debug(
                f"ASR数据已加入上报队列: {conn.device_id}, 不上报音频"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"加入ASR上报队列失败: {text}, {e}")
