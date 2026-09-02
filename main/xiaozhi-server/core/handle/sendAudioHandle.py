import json
import time
import asyncio
from core.utils import textUtils
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType
from core.utils.audioRateController import AudioRateController

TAG = __name__
# Audio frame duration (ms)
AUDIO_FRAME_DURATION = 60
# Pre-buffer count, send directly to reduce latency
PRE_BUFFER_COUNT = 5


async def sendAudioMessage(conn, sentenceType, audios, text):
    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).info(f"Sending first audio segment: {text}")
        conn.tts.tts_audio_first_sentence = False
        await send_tts_message(conn, "start", None)

    if sentenceType == SentenceType.FIRST:
        # Subsequent messages for the same sentence join the flow control queue, others send immediately
        if (
            hasattr(conn, "audio_rate_controller")
            and conn.audio_rate_controller
            and getattr(conn, "audio_flow_control", {}).get("sentence_id")
            == conn.sentence_id
        ):
            conn.audio_rate_controller.add_message(
                lambda: send_tts_message(conn, "sentence_start", text)
            )
        else:
            # New sentence or rate controller not initialized, send immediately
            await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios)
    # Send sentence start message
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).info(f"Sending audio message: {sentenceType}, {text}")

    # Send end message (if it is the last text)
    if sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None)
        conn.client_is_speaking = False
        if conn.close_after_chat:
            await conn.close()


async def _wait_for_audio_completion(conn):
    """
    Wait for audio queue to empty and wait for pre-buffer packets to finish playing

    Args:
        conn: connection object
    """
    if hasattr(conn, "audio_rate_controller") and conn.audio_rate_controller:
        rate_controller = conn.audio_rate_controller
        conn.logger.bind(tag=TAG).debug(
            f"Waiting for audio completion, {len(rate_controller.queue)} packets remaining"
        )
        await rate_controller.queue_empty_event.wait()

        # Wait for pre-buffer packets to finish playing
        # First N packets sent directly, adding 2 network jitter packets, need extra wait for them to finish playing on client
        frame_duration_ms = rate_controller.frame_duration
        pre_buffer_playback_time = (PRE_BUFFER_COUNT + 2) * frame_duration_ms / 1000.0
        await asyncio.sleep(pre_buffer_playback_time)

        conn.logger.bind(tag=TAG).debug("Audio sending completed")


async def _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence):
    """
    Send opus packet with 16-byte header to mqtt_gateway
    Args:
        conn: connection object
        opus_packet: opus data packet
        timestamp: timestamp
        sequence: sequence number
    """
    # Add 16-byte header to opus packet
    header = bytearray(16)
    header[0] = 1  # type
    header[2:4] = len(opus_packet).to_bytes(2, "big")  # payload length
    header[4:8] = sequence.to_bytes(4, "big")  # sequence
    header[8:12] = timestamp.to_bytes(4, "big")  # timestamp
    header[12:16] = len(opus_packet).to_bytes(4, "big")  # opus length

    # Send complete packet containing header
    complete_packet = bytes(header) + opus_packet
    await conn.websocket.send(complete_packet)


async def sendAudio(conn, audios, frame_duration=AUDIO_FRAME_DURATION):
    """
    Send audio packets, use AudioRateController for precise flow control

    Args:
        conn: connection object
        audios: single opus packet (bytes) or list of opus packets
        frame_duration: frame duration (ms), default uses global constant AUDIO_FRAME_DURATION
    """
    if audios is None or len(audios) == 0:
        return

    send_delay = conn.config.get("tts_audio_send_delay", -1) / 1000.0
    is_single_packet = isinstance(audios, bytes)

    # Initialize or get RateController
    rate_controller, flow_control = _get_or_create_rate_controller(
        conn, frame_duration, is_single_packet
    )

    # Unified conversion to list processing
    audio_list = [audios] if is_single_packet else audios

    # Send audio packets
    await _send_audio_with_rate_control(
        conn, audio_list, rate_controller, flow_control, send_delay
    )


def _get_or_create_rate_controller(conn, frame_duration, is_single_packet):
    """
    Get or create RateController and flow_control

    Args:
        conn: connection object
        frame_duration: frame duration
        is_single_packet: Whether single packet mode (True: TTS streaming single packet, False: batch packet)

    Returns:
        (rate_controller, flow_control)
    """
    # Check if controller needs reset
    need_reset = False

    if not hasattr(conn, "audio_rate_controller"):
        # Controller does not exist, need to create
        need_reset = True
    else:
        rate_controller = conn.audio_rate_controller

        # Background send task stopped, need to reset
        if (
            not rate_controller.pending_send_task
            or rate_controller.pending_send_task.done()
        ):
            need_reset = True
        # When sentence_id changes, need to reset
        elif (
            getattr(conn, "audio_flow_control", {}).get("sentence_id")
            != conn.sentence_id
        ):
            need_reset = True

    if need_reset:
        # Create or get rate_controller
        if not hasattr(conn, "audio_rate_controller"):
            conn.audio_rate_controller = AudioRateController(frame_duration)
        else:
            conn.audio_rate_controller.reset()

        # Initialize flow_control
        conn.audio_flow_control = {
            "packet_count": 0,
            "sequence": 0,
            "sentence_id": conn.sentence_id,
        }

        # Start background send loop
        _start_background_sender(
            conn, conn.audio_rate_controller, conn.audio_flow_control
        )

    return conn.audio_rate_controller, conn.audio_flow_control


def _start_background_sender(conn, rate_controller, flow_control):
    """
    Start background send loop task

    Args:
        conn: connection object
        rate_controller: rate controller
        flow_control: flow control status
    """

    async def send_callback(packet):
        # Check if should abort
        if conn.client_abort:
            raise asyncio.CancelledError("Client aborted")

        conn.last_activity_time = time.time() * 1000
        await _do_send_audio(conn, packet, flow_control)
        conn.client_is_speaking = True

    # Use start_sending to start background loop
    rate_controller.start_sending(send_callback)


async def _send_audio_with_rate_control(
    conn, audio_list, rate_controller, flow_control, send_delay
):
    """
    Use rate_controller to send audio packets

    Args:
        conn: connection object
        audio_list: list of audio packets
        rate_controller: rate controller
        flow_control: flow control status
        send_delay: fixed delay (seconds), -1 means use dynamic flow control
    """
    for packet in audio_list:
        if conn.client_abort:
            return

        conn.last_activity_time = time.time() * 1000

        # Pre-buffer: first N packets send directly
        if flow_control["packet_count"] < PRE_BUFFER_COUNT:
            await _do_send_audio(conn, packet, flow_control)
            conn.client_is_speaking = True
        elif send_delay > 0:
            # Fixed delay mode
            await asyncio.sleep(send_delay)
            await _do_send_audio(conn, packet, flow_control)
            conn.client_is_speaking = True
        else:
            # Dynamic flow control mode: only add to queue, background loop responsible for sending
            rate_controller.add_audio(packet)


async def _do_send_audio(conn, opus_packet, flow_control):
    """
    Execute actual audio sending
    """
    packet_index = flow_control.get("packet_count", 0)
    sequence = flow_control.get("sequence", 0)

    if conn.conn_from_mqtt_gateway:
        # Calculate timestamp (based on playback position)
        start_time = time.time()
        timestamp = int(start_time * 1000) % (2**32)
        await _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence)
    else:
        # Send opus data packet directly
        await conn.websocket.send(opus_packet)

    # Update flow control status
    flow_control["packet_count"] = packet_index + 1
    flow_control["sequence"] = sequence + 1


async def send_tts_message(conn, state, text=None):
    """Send TTS state message"""
    if text is None and state == "sentence_start":
        return
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # TTS playback finished
    if state == "stop":
        # Play notification sound
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios = await audio_to_data(stop_tts_notify_voice, is_opus=True)
            await sendAudio(conn, audios)
        # Wait for all audio packets to finish sending
        await _wait_for_audio_completion(conn)
        # Clear server speaking status
        conn.clearSpeakStatus()

    # Send message to client
    await conn.websocket.send(json.dumps(message))


async def send_stt_message(conn, text):
    """Send STT state message"""
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    # Parse JSON format, extract actual user spoken content
    display_text = text
    try:
        # Try to parse JSON format
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # If JSON format containing speaker info, only display content part
                display_text = parsed_data["content"]
                # Save speaker info to conn object
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # If not JSON format, use original text directly
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    await send_tts_message(conn, "start")
