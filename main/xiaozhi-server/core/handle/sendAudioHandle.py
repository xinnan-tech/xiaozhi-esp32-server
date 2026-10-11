import json
import time
import asyncio
import opuslib_next
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils import textUtils
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType
from core.utils.audioRateController import AudioRateController

TAG = __name__
# Audio frame duration (ms)
AUDIO_FRAME_DURATION = 60
# Pre-buffer packet count, send directly to reduce latency
PRE_BUFFER_COUNT = 5


async def sendAudioMessage(conn: "ConnectionHandler", sentenceType, audios, text, sentence_id=None):
    # Skipping residual audio from old sentence
    if sentence_id is not None and sentence_id != conn.sentence_id:
        return

    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).info(f"Send first audio segment: {text}")
        conn.tts.tts_audio_first_sentence = False

    if sentenceType == SentenceType.FIRST:
        # Add subsequent messages for the same sentence to the flow control queue; send others immediately
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
            # New sentence or stream controller not initialized, send immediately
            await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios)
    # Send sentence start message
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).info(f"Send audio message: {sentenceType}, {text}")

    # Send end message (if it is the last text)
    # Call must maintain speaking state
    if not conn.calling and sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None)
        if conn.close_after_chat:
            await conn.close()


async def _wait_for_audio_completion(conn: "ConnectionHandler"):
    """
    Wait for audio queue to clear and pre-buffered packets to finish playing

    Args:
        conn: Connection object
    """
    if hasattr(conn, "audio_rate_controller") and conn.audio_rate_controller:
        rate_controller = conn.audio_rate_controller
        send_delay_ms = conn.config.get("tts_audio_send_delay", 0)
        conn.logger.bind(tag=TAG).debug(
            f"Waiting for audio transmission to complete; {len(rate_controller.queue)} packets remaining in queue"
        )
        await rate_controller.queue_empty_event.wait()

        if send_delay_ms > 0:
            # Custom rhythm: wait for the last frame to finish playing on the client
            playback_time = 2 * rate_controller.interval_ms / 1000.0
        else:
            # Default pacing: First N frames pre-buffered and sent directly, wait for playback to complete
            playback_time = (PRE_BUFFER_COUNT + 2) * rate_controller.interval_ms / 1000.0
        await asyncio.sleep(playback_time)

        conn.logger.bind(tag=TAG).debug("Audio send complete")


async def _send_to_mqtt_gateway(
    conn: "ConnectionHandler", opus_packet, timestamp, sequence
):
    """
    Send opus packet with 16-byte header to mqtt_gateway, and cache audio for AEC processing
    Args:
        conn: Connection object
        opus_packet: opus packet
        timestamp: Timestamp
        sequence: Sequence number
    """
    # If server-side AEC is enabled, cache PCM data for subsequent AEC processing
    if conn.client_aec and timestamp > 0:
        if not hasattr(conn, "aec_audio_cache"):
            conn.aec_audio_cache = {}
            conn.aec_audio_cache_time = {}
            conn._send_opus_decoder = opuslib_next.Decoder(16000, 1)
        # Decode Opus to PCM and cache
        pcm_data = conn._send_opus_decoder.decode(bytes(opus_packet), 960)
        conn.aec_audio_cache[timestamp] = bytes(pcm_data)
        conn.aec_audio_cache_time[timestamp] = time.time()

    # Add 16-byte header to Opus packet
    header = bytearray(16)
    header[0] = 1  # type
    header[2:4] = len(opus_packet).to_bytes(2, "big")  # payload length
    header[4:8] = sequence.to_bytes(4, "big")  # sequence
    header[8:12] = timestamp.to_bytes(4, "big")  # Timestamp
    header[12:16] = len(opus_packet).to_bytes(4, "big")  # Opus length

    # Send complete data packet including headers
    complete_packet = bytes(header) + opus_packet
    await conn.websocket.send(complete_packet)


async def sendAudio(
    conn: "ConnectionHandler", audios, frame_duration=AUDIO_FRAME_DURATION
):
    """
    Send audio packets with precise flow control via AudioRateController

    Args:
        conn: Connection object
        audios: Single opus packet (bytes) or list of opus packets
        frame_duration: frame duration (ms), defaults to global constant AUDIO_FRAME_DURATION
    """
    if audios is None or len(audios) == 0:
        return

    send_delay_ms = conn.config.get("tts_audio_send_delay", 0)
    is_single_packet = isinstance(audios, bytes)

    # Initialize or get RateController
    rate_controller, flow_control = _get_or_create_rate_controller(
        conn, frame_duration, is_single_packet, send_delay_ms
    )

    # Convert to list for unified processing
    audio_list = [audios] if is_single_packet else audios

    # Send audio packet
    await _send_audio_with_rate_control(
        conn, audio_list, rate_controller, flow_control, send_delay_ms
    )


def _get_or_create_rate_controller(
    conn: "ConnectionHandler", frame_duration, is_single_packet, send_delay_ms=0
):
    """
    Get or create RateController and flow_control

    Args:
        conn: Connection object
        frame_duration: Frame duration
        is_single_packet: Whether single-packet mode is enabled (True: TTS streaming single packet, False: batch packets)
        send_delay_ms: Custom send interval (ms).

    Returns:
        (rate_controller, flow_control)
    """
    # Check if controller reset is required
    need_reset = False

    if not hasattr(conn, "audio_rate_controller"):
        # Controller does not exist, needs to be created
        need_reset = True
    else:
        rate_controller = conn.audio_rate_controller

        # Background send task stopped, reset required
        if (
            not rate_controller.pending_send_task
            or rate_controller.pending_send_task.done()
        ):
            need_reset = True
        # Reset when sentence_id changes
        elif (
            getattr(conn, "audio_flow_control", {}).get("sentence_id")
            != conn.sentence_id
        ):
            need_reset = True

    if need_reset:
        # Create or get rate_controller
        if not hasattr(conn, "audio_rate_controller"):
            conn.audio_rate_controller = AudioRateController(
                frame_duration, send_delay=send_delay_ms
            )
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


def _start_background_sender(conn: "ConnectionHandler", rate_controller, flow_control):
    """
    Start background send loop task

    Args:
        conn: Connection object
        rate_controller: Rate controller
        flow_control: Flow control status
    """

    async def send_callback(packet):
        # Check if should abort
        if conn.client_abort:
            raise asyncio.CancelledError("Client aborted")

        conn.last_activity_time = time.time() * 1000
        await _do_send_audio(conn, packet, flow_control)

    # Use start_sending to start the background loop
    rate_controller.start_sending(send_callback)


async def _send_audio_with_rate_control(
    conn: "ConnectionHandler", audio_list, rate_controller, flow_control, send_delay_ms
):
    """
    Send audio packets using rate_controller

    Args:
        conn: Connection object
        audio_list: List of audio packets
        rate_controller: Rate controller
        flow_control: Flow control status
        send_delay_ms: Custom send interval (ms).
    """
    for packet in audio_list:
        if conn.client_abort:
            return

        conn.last_activity_time = time.time() * 1000

        if send_delay_ms > 0:
            # Custom pacing mode: enqueue all packets and send with send_delay (disable pre-buffering)
            rate_controller.add_audio(packet)
        else:
            # Default pacing mode (60ms/packet): send first N packets directly from pre-buffer, enqueue subsequent packets for background task to send at interval_ms
            if flow_control["packet_count"] < PRE_BUFFER_COUNT:
                await _do_send_audio(conn, packet, flow_control)
            else:
                rate_controller.add_audio(packet)


async def _do_send_audio(conn: "ConnectionHandler", opus_packet, flow_control):
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
        # Send Opus data packet directly
        await conn.websocket.send(opus_packet)

    # Update flow control state
    flow_control["packet_count"] = packet_index + 1
    flow_control["sequence"] = sequence + 1


async def send_tts_message(conn: "ConnectionHandler", state, text=None):
    """Send TTS status message"""
    if text is None and state == "sentence_start":
        return
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # TTS playback ended
    if state == "stop":
        # Save the current sentence_id for later round validation
        current_sentence_id = conn.sentence_id
        # Play notification sound
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios = await audio_to_data(stop_tts_notify_voice, is_opus=True)
            await sendAudio(conn, audios)
        # Wait for all audio packets to be sent
        await _wait_for_audio_completion(conn)

        # Check if current turn
        if current_sentence_id != conn.sentence_id:
            return

        # Stop the audio sending loop (call only if the flow controller is initialized)
        if hasattr(conn, "audio_rate_controller") and conn.audio_rate_controller:
            conn.audio_rate_controller.stop_sending()
        conn.clearSpeakStatus()

    # Send message to client
    await conn.websocket.send(json.dumps(message))


async def send_stt_message(conn: "ConnectionHandler", text):
    """Send STT status message"""
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    # Parse JSON format and extract the actual user speech content
    display_text = text
    try:
        # Attempt to parse JSON format
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # If the JSON format includes speaker information, display only the content field
                display_text = parsed_data["content"]
                # Save speaker info to conn object
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # If not in JSON format, use the raw text directly
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    await send_tts_message(conn, "start")
    # After sending the start message, the client enters speaking state; sync with server state
    conn.client_is_speaking = True


async def send_display_message(conn: "ConnectionHandler", text):
    """Send display-only message"""
    message = {
        "type": "stt",
        "text": text,
        "session_id": conn.session_id
    }
    await conn.websocket.send(json.dumps(message))
