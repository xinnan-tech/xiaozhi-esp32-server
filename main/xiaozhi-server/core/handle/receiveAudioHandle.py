import time
import json
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.util import audio_to_data
from core.handle.abortHandle import handleAbortMessage
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.sendAudioHandle import send_stt_message, SentenceType

TAG = __name__


async def handleAudioMessage(conn: "ConnectionHandler", audio):
    # Ignore audio while the exit flow is already running.
    if conn.is_exiting:
        return

    # Detect whether this chunk contains speech.
    have_voice = conn.vad.is_vad(conn, audio)
    # Briefly ignore VAD immediately after wake-up.
    if hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # Resume VAD after a short delay.
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
        return
    # In manual mode, do not interrupt currently playing audio.
    if have_voice:
        if conn.client_is_speaking and conn.client_listen_mode != "manual":
            await handleAbortMessage(conn)
    # Track long idle periods to trigger a goodbye flow.
    await no_voice_close_connect(conn, have_voice)
    # Forward the audio to ASR.
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn: "ConnectionHandler"):
    # Re-enable VAD after 2 seconds.
    await asyncio.sleep(2)
    conn.just_woken_up = False


async def startToChat(conn: "ConnectionHandler", text):
    # Check whether the input is JSON with speaker metadata.
    speaker_name = None
    actual_text = text

    try:
        # Try to parse JSON-wrapped text input.
        if text.strip().startswith("{") and text.strip().endswith("}"):
            data = json.loads(text)
            if "speaker" in data and "content" in data:
                speaker_name = data["speaker"]
                actual_content = data["content"]
                conn.logger.bind(tag=TAG).info(
                    f"Parsed speaker information: {speaker_name}"
                )

                # Keep the {"speaker":...} JSON only on the speaker's first
                # appearance so the model greets them naturally once; later
                # turns degrade to plain text so the recurring name does not
                # push the model to keep addressing them every turn.
                if speaker_name not in conn.introduced_speakers:
                    conn.introduced_speakers.add(speaker_name)
                    actual_text = text
                else:
                    actual_text = actual_content
            elif "content" in data:
                # FunASR-style payloads return {"content","language","emotion"}:
                # hand only the recognized text to the LLM, otherwise the raw
                # JSON would enter the conversation history.
                actual_text = data["content"]
    except (json.JSONDecodeError, KeyError):
        # Fall back to the original text if parsing fails.
        pass

    # Persist speaker information on the connection.
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # Enforce per-device output limits when configured.
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return
    # In manual mode, do not interrupt currently playing audio.
    if conn.client_is_speaking and conn.client_listen_mode != "manual":
        await handleAbortMessage(conn)

    # Run intent handling first using the effective text content.
    intent_handled = await handle_user_intent(conn, actual_text)

    if intent_handled:
        # Stop here if intent handling already produced the response.
        return

    # Otherwise continue with the normal chat flow.
    await send_stt_message(conn, actual_text)

    # Prepare to start a new conversation.
    conn.client_abort = False

    conn.executor.submit(conn.chat, actual_text)


async def no_voice_close_connect(conn: "ConnectionHandler", have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # Only check idle timeout after the activity timestamp has been initialized.
    if conn.last_activity_time > 0.0:
        no_voice_time = time.time() * 1000 - conn.last_activity_time
        close_connection_no_voice_time = int(
            conn.config.get("close_connection_no_voice_time", 120)
        )
        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            end_prompt = conn.config.get("end_prompt", {})
            if end_prompt and end_prompt.get("enable", True) is False:
                conn.logger.bind(tag=TAG).info(
                    "Ending conversation without sending a closing prompt"
                )
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = (
                    "Please begin with ```Time really flew by``` and end this conversation "
                    "with warm, heartfelt, and slightly reluctant farewell language."
                )
            await startToChat(conn, prompt)


async def max_out_size(conn: "ConnectionHandler"):
    # Play the over-limit prompt when the daily output cap is exceeded.
    conn.client_abort = False
    text = (
        "Sorry, I need to wrap up for now. Let's talk again around this time tomorrow. "
        "It's a promise. See you tomorrow, bye for now."
    )
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets = await audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn: "ConnectionHandler"):
    if conn.bind_code:
        # Make sure the bind code is exactly 6 digits long.
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(
                f"Invalid bind code format: {conn.bind_code}"
            )
            text = "The bind code format is invalid. Please check the configuration."
            await send_stt_message(conn, text)
            return

        text = f"Please sign in to the control panel and enter {conn.bind_code} to bind the device."
        await send_stt_message(conn, text)

        # Play the bind prompt audio.
        music_path = "config/assets/bind_code.wav"
        opus_packets = await audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # Speak the digits one by one.
        for i in range(6):  # Always play exactly 6 digits.
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets = await audio_to_data(num_path)
                conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(
                    f"Failed to play bind-code digit audio: {e}"
                )
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        # Play the unbound-device prompt.
        conn.client_abort = False
        text = (
            "No version information was found for this device. Please configure the "
            "OTA address correctly and rebuild the firmware."
        )
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets = await audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
