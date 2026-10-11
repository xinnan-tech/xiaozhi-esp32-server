"""
TTS reporting has been integrated into the ConnectionHandler class.

The reporting flow includes:
1. Each connection object owns its own report queue and worker thread.
2. The worker thread lifecycle is tied to the connection object.
3. Reporting is triggered through `ConnectionHandler.enqueue_tts_report`.

For the implementation details, see the related code in `core/connection.py`.
"""

import time
import json
import opuslib_next
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from config.manage_api_client import report as manage_report

TAG = __name__


async def report(conn: "ConnectionHandler", type, text, opus_data, report_time):
    """Send a chat-history report.

    Args:
        conn: Connection object.
        type: Report type. `1` for user, `2` for assistant, `3` for tool call.
        text: Text content.
        opus_data: Opus audio data.
        report_time: Report timestamp.
    """
    try:
        if audio_data:

            if chat_type == 1:
                wav_data = pcm_to_wav(conn, audio_data)
            elif chat_type == 2:
                wav_data = opus_to_wav(conn, audio_data)
            else:
                wav_data = None
        else:
            audio_data = None
        # Execute the async report request.
        await manage_report(
            mac_address=conn.device_id,
            session_id=conn.session_id,
            chat_type=chat_type,
            content=text,
            audio=wav_data,
            report_time=report_time,
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to report chat history: {e}")


def opus_to_wav(conn: "ConnectionHandler", opus_data):
    """Convert Opus packets into a WAV byte stream.

    Args:
        output_dir: Output directory placeholder kept for interface compatibility.
        opus_data: Opus audio data.

    Returns:
        bytes: WAV-format audio data.
    """
    try:
        decoder = opuslib_next.Decoder(16000, 1)  # 16 kHz, mono
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60 ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                conn.logger.bind(tag=TAG).error(
                    f"Opus decode error: {e}", exc_info=True
                )

        if not pcm_data:
            raise ValueError("No valid PCM data was produced")

        # Build the WAV header.
        pcm_data_bytes = b"".join(pcm_data)
        num_samples = len(pcm_data_bytes) // 2  # 16-bit samples

        # WAV header
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

        # Return the full WAV payload.
        return bytes(wav_header) + pcm_data_bytes
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"PCM转WAV失败: {e}", exc_info=True)
        raise


def opus_to_wav(conn: "ConnectionHandler", opus_data):
    """将Opus数据转换为WAV格式的字节流

    Args:
        conn: 连接对象
        opus_data: Opus音频数据（可能是列表或bytes）

    Returns:
        bytes: WAV格式的音频数据
    """
    decoder = None
    try:
        decoder = opuslib_next.Decoder(16000, 1)
        pcm_data = []

        if isinstance(opus_data, list):
            for opus_packet in opus_data:
                try:
                    pcm_frame = decoder.decode(opus_packet, 960)
                    pcm_data.append(pcm_frame)
                except opuslib_next.OpusError as e:
                    conn.logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)
        elif isinstance(opus_data, bytes):
            pcm_frame = decoder.decode(opus_data, 960)
            pcm_data.append(pcm_frame)

        if not pcm_data:
            raise ValueError("没有有效的音频数据")

        pcm_data_bytes = b"".join(pcm_data)

        wav_header = bytearray()
        wav_header.extend(b"RIFF")
        wav_header.extend((36 + len(pcm_data_bytes)).to_bytes(4, "little"))
        wav_header.extend(b"WAVE")
        wav_header.extend(b"fmt ")
        wav_header.extend((16).to_bytes(4, "little"))
        wav_header.extend((1).to_bytes(2, "little"))
        wav_header.extend((1).to_bytes(2, "little"))
        wav_header.extend((16000).to_bytes(4, "little"))
        wav_header.extend((32000).to_bytes(4, "little"))
        wav_header.extend((2).to_bytes(2, "little"))
        wav_header.extend((16).to_bytes(2, "little"))
        wav_header.extend(b"data")
        wav_header.extend(len(pcm_data_bytes).to_bytes(4, "little"))

        return bytes(wav_header) + pcm_data_bytes
    finally:
        if decoder is not None:
            try:
                del decoder
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(
                    f"Failed to release decoder resources: {e}"
                )


def enqueue_tts_report(conn: "ConnectionHandler", text, opus_data):
    if not conn.read_config_from_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    """Push TTS data into the report queue.

    Args:
        conn: Connection object.
        text: Synthesized text.
        opus_data: Opus audio data.
    """
    if not conn.read_config_from_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    try:
        # Use the connection queue and pass text plus binary data directly.
        if conn.chat_history_conf == 2:
            conn.report_queue.put((2, text, opus_data, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data queued for reporting: {conn.device_id}, audio size: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((2, text, None, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data queued for reporting: {conn.device_id}, audio upload disabled"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to queue TTS report: {text}, {e}")


def enqueue_tool_report(conn: "ConnectionHandler", tool_name: str, tool_input: dict, tool_result: str = None, report_tool_call: bool = True):
    """Push tool-call data into the report queue.

    Args:
        conn: Connection object.
        tool_name: Tool name.
        tool_input: Tool input arguments.
        tool_result: Tool execution result, if available.
        report_tool_call: Whether to report the tool call itself. Defaults to
            `True`; set to `False` to report only the result.
    """
    if not conn.read_config_from_api or conn.need_bind:
        return
    if conn.chat_history_conf == 0:
        return

    try:
        timestamp = int(time.time() * 1000)

        # Build the tool-call record.
        if report_tool_call:
            tool_text = json.dumps(
                [
                    {
                        "type": "tool",
                        "text": f"{tool_name}({json.dumps(tool_input, ensure_ascii=False)})",
                    }
                ]
            )
            conn.report_queue.put((3, tool_text, None, timestamp))

        # Build the tool-result record.
        if tool_result:
            result_display = f'{{"result":"{str(tool_result)}"}}'
            result_content = json.dumps([{"type": "tool_result", "text": result_display}], ensure_ascii=False)
            conn.report_queue.put((3, result_content, None, timestamp + 1))
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to queue tool report: {e}")


def enqueue_asr_report(conn: "ConnectionHandler", text, opus_data):
    if not conn.read_config_from_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    """Push ASR data into the report queue.

    Args:
        conn: Connection object.
        text: Recognized text.
        opus_data: Opus audio data.
    """
    if not conn.read_config_from_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    try:
        # Use the connection queue and pass text plus binary data directly.
        if conn.chat_history_conf == 2:
            conn.report_queue.put((1, text, opus_data, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data queued for reporting: {conn.device_id}, audio size: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((1, text, None, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data queued for reporting: {conn.device_id}, audio upload disabled"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).debug(f"Failed to queue ASR report: {text}, {e}")
