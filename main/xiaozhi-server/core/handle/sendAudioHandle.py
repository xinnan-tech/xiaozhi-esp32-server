import json
import time
import asyncio
from core.utils import textUtils
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType

TAG = __name__


async def sendAudioMessage(conn, sentenceType, audios, text):
    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).info(f"Send the first voice message: {text}")
        conn.tts.tts_audio_first_sentence = False
        await send_tts_message(conn, "start", None)

    if sentenceType == SentenceType.FIRST:
        await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios)
    # Send sentence start message
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).info(f"Send audio message: {sentenceType}, {text}")

    # Send end message (if last text)
    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None)
        conn.client_is_speaking = False
        if conn.close_after_chat:
            await conn.close()


def calculate_timestamp_and_sequence(conn, start_time, packet_index, frame_duration=60):
    """
    Calculate timestamp and sequence number of audio packets
    Args:
        conn: connection object
        start_time: start time (performance counter value)
        packet_index: packet index
        frame_duration: frame duration (milliseconds), matching Opus encoding
    Returns:
        tuple: (timestamp, sequence)
    """
    # Calculate timestamp (calculated using playback position)
    timestamp = int((start_time + packet_index * frame_duration / 1000) * 1000) % (
        2**32
    )

    # Calculate serial number
    if hasattr(conn, "audio_flow_control"):
        sequence = conn.audio_flow_control["sequence"]
    else:
        sequence = packet_index  # If there is no flow control state, use the index directly

    return timestamp, sequence


async def _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence):
    """
    Send opus packet with 16-byte header to mqtt_gateway
    Args:
        conn: connection object
        opus_packet: opus data packet
        timestamp: timestamp
        sequence: sequence number
    """
    # Add 16-byte header to opus packets
    header = bytearray(16)
    header[0] = 1  # type
    header[2:4] = len(opus_packet).to_bytes(2, "big")  # payload length
    header[4:8] = sequence.to_bytes(4, "big")  # sequence
    header[8:12] = timestamp.to_bytes(4, "big")  # Timestamp
    header[12:16] = len(opus_packet).to_bytes(4, "big")  # Opus length

    # Send complete packet including headers
    complete_packet = bytes(header) + opus_packet
    await conn.websocket.send(complete_packet)


# Play audio
async def sendAudio(conn, audios, frame_duration=60):
    """
    Send a single opus packet, support flow control
    Args:
        conn: connection object
        opus_packet: single opus data packet
        pre_buffer: Send audio quickly
        frame_duration: frame duration (milliseconds), matching Opus encoding
    """
    if audios is None or len(audios) == 0:
        return

    if isinstance(audios, bytes):
        if conn.client_abort:
            return

        conn.last_activity_time = time.time() * 1000

        # Get or initialize flow control status
        if not hasattr(conn, "audio_flow_control"):
            conn.audio_flow_control = {
                "last_send_time": 0,
                "packet_count": 0,
                "start_time": time.perf_counter(),
                "sequence": 0,  # Add serial number
            }

        flow_control = conn.audio_flow_control
        current_time = time.perf_counter()
        # Calculate expected delivery time
        expected_time = flow_control["start_time"] + (
            flow_control["packet_count"] * frame_duration / 1000
        )
        delay = expected_time - current_time
        if delay > 0:
            await asyncio.sleep(delay)
        else:
            # correct errors
            flow_control["start_time"] += abs(delay)

        if conn.conn_from_mqtt_gateway:
            # Calculate timestamps and sequence numbers
            timestamp, sequence = calculate_timestamp_and_sequence(
                conn,
                flow_control["start_time"],
                flow_control["packet_count"],
                frame_duration,
            )
            # Call a common function to send a packet with header
            await _send_to_mqtt_gateway(conn, audios, timestamp, sequence)
        else:
            # Send opus packets directly without adding headers
            await conn.websocket.send(audios)

        # Update flow control status
        flow_control["packet_count"] += 1
        flow_control["sequence"] += 1
        flow_control["last_send_time"] = time.perf_counter()
    else:
        # File-type audio is played normally
        start_time = time.perf_counter()
        play_position = 0

        # Perform prebuffering
        pre_buffer_frames = min(3, len(audios))
        for i in range(pre_buffer_frames):
            if conn.conn_from_mqtt_gateway:
                # Calculate timestamps and sequence numbers
                timestamp, sequence = calculate_timestamp_and_sequence(
                    conn, start_time, i, frame_duration
                )
                # Call a common function to send a packet with header
                await _send_to_mqtt_gateway(conn, audios[i], timestamp, sequence)
            else:
                # Send the pre-buffered packet directly without adding headers
                await conn.websocket.send(audios[i])
        remaining_audios = audios[pre_buffer_frames:]

        # Play remaining audio frames
        for i, opus_packet in enumerate(remaining_audios):
            if conn.client_abort:
                break

            # Reset no sound status
            conn.last_activity_time = time.time() * 1000

            # Calculate expected delivery time
            expected_time = start_time + (play_position / 1000)
            current_time = time.perf_counter()
            delay = expected_time - current_time
            if delay > 0:
                await asyncio.sleep(delay)

            if conn.conn_from_mqtt_gateway:
                # Calculate timestamps and sequence numbers (using current packet index to ensure continuity)
                packet_index = pre_buffer_frames + i
                timestamp, sequence = calculate_timestamp_and_sequence(
                    conn, start_time, packet_index, frame_duration
                )
                # Call a common function to send a packet with header
                await _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence)
            else:
                # Send opus packets directly without adding headers
                await conn.websocket.send(opus_packet)

            play_position += frame_duration


async def send_tts_message(conn, state, text=None):
    """Send TTS status message"""
    if text is None and state == "sentence_start":
        return
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # Tts play ends
    if state == "stop":
        # Play tone
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios = audio_to_data(stop_tts_notify_voice, is_opus=True)
            await sendAudio(conn, audios)
        # Clear server talk status
        conn.clearSpeakStatus()

    # Send message to client
    await conn.websocket.send(json.dumps(message))


async def send_stt_message(conn, text):
    """Send STT status message"""
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    # Parse the json format and extract the actual user speech content
    display_text = text
    try:
        # Try to parse json format
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # If it is in json format containing speaker information, only the content part will be displayed.
                display_text = parsed_data["content"]
                # Save speaker information to conn object
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # If it is not in json format, use the original text directly.
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    conn.client_is_speaking = True
    await send_tts_message(conn, "start")
