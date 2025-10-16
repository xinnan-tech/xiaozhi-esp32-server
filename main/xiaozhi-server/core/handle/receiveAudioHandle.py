import time
import json
import asyncio
from core.utils.util import audio_to_data
from core.handle.abortHandle import handleAbortMessage
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.sendAudioHandle import send_stt_message, SentenceType

TAG = __name__


async def handleAudioMessage(conn, audio):
    # Is anyone speaking in the current segment?
    have_voice = conn.vad.is_vad(conn, audio)
    # If the device has just been woken up, briefly ignore vad detection
    if hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # Resume vad detection after setting a short delay
        conn.asr_audio.clear()
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
        return
    # manual Do not interrupt the content being played in mode
    if have_voice:
        if conn.client_is_speaking and conn.client_listen_mode != "manual":
            await handleAbortMessage(conn)
    # Device idle detection for a long time, used for say goodbye
    await no_voice_close_connect(conn, have_voice)
    # receive audio
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn):
    # Wait 2 seconds before resuming vad detection
    await asyncio.sleep(1)
    conn.just_woken_up = False


async def startToChat(conn, text):
    # Check whether the input is in json format (contains speaker information)
    speaker_name = None
    actual_text = text

    try:
        # Try to parse input in json format
        if text.strip().startswith("{") and text.strip().endswith("}"):
            data = json.loads(text)
            if "speaker" in data and "content" in data:
                speaker_name = data["speaker"]
                actual_text = data["content"]
                conn.logger.bind(tag=TAG).info(f"Parse to speaker information: {speaker_name}")

                # Use text in json format directly without parsing
                actual_text = text
    except (json.JSONDecodeError, KeyError):
        # If parsing fails, continue using the original text
        pass

    # Save speaker information to the connection object
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # If the number of words output on that day is greater than the limited number of words,
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return
    # manual Do not interrupt the content being played in mode
    if conn.client_is_speaking and conn.client_listen_mode != "manual":
        await handleAbortMessage(conn)

    # Do intent analysis first, using actual text content
    intent_handled = await handle_user_intent(conn, actual_text)

    if intent_handled:
        # If the intent has been processed, the chat will no longer proceed
        return

    # Intent not processed, continue the regular chat flow with actual text content
    await send_stt_message(conn, actual_text)
    conn.executor.submit(conn.chat, actual_text)


async def no_voice_close_connect(conn, have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # Only perform timeout checks if the timestamp has been initialized
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
                conn.logger.bind(tag=TAG).info("End the conversation without sending an end message")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "Please end this conversation with words of 'Time flies so fast' and words that are full of emotion and reluctance. !"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    # Play prompt exceeding maximum output word count
    conn.client_abort = False
    text = "Sorry, I'm busy with something right now. We'll talk again at this time tomorrow. We've made an appointment! See you tomorrow, bye!"
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets = audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn):
    if conn.bind_code:
        # Make sure the bind code is 6 digits
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"Invalid binding code format: {conn.bind_code}")
            text = "The binding code format is incorrect, please check the configuration."
            await send_stt_message(conn, text)
            return

        text = f"Please log in to the control panel and enter {conn.bind }code to bind the device."
        await send_stt_message(conn, text)

        # Play tone
        music_path = "config/assets/bind_code.wav"
        opus_packets = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # Play numbers one by one
        for i in range(6):  # Make sure to only play 6 digits
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets = audio_to_data(num_path)
                conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        # Play unbound prompt
        conn.client_abort = False
        text = f"The version information of the device was not found. Please configure the OTA address correctly and then recompile the firmware."
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
