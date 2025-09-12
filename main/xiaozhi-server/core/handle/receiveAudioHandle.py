# from core.handle.sendAudioHandle import send_stt_message
# from core.handle.intentHandler import handle_user_intent
# from core.utils.output_counter import check_device_output_limit
# from core.handle.abortHandle import handleAbortMessage
# import time
# import asyncio
# import json
# from core.handle.sendAudioHandle import SentenceType
# from core.utils.util import audio_to_data

# TAG = __name__


# async def handleAudioMessage(conn, audio):
#     # Log that we received audio (only log periodically to avoid spam)
#     if not hasattr(conn, '_audio_log_counter'):
#         conn._audio_log_counter = 0
#     conn._audio_log_counter += 1

#     if conn._audio_log_counter % 200 == 0:  # Log every 200th packet (reduced from 50)
#         conn.logger.bind(tag=TAG).debug(f"Received audio packet #{conn._audio_log_counter}, size: {len(audio)} bytes")

#     # Skip VAD/ASR processing when server is speaking (streaming audio to client)
#     # This prevents interruptions during TTS playback
#     if conn.client_is_speaking:
#         # conn.logger.bind(tag=TAG).debug("Server is speaking - skipping audio processing to prevent interruption")
#         return

#     # Whether the current segment has someone speaking
#     have_voice = conn.vad.is_vad(conn, audio)
    
#     # Track when voice recording starts in auto VAD mode (for 10-second timeout)
#     if have_voice and not hasattr(conn, 'vad_recording_start_time'):
#         conn.vad_recording_start_time = time.time()
#         conn.logger.bind(tag=TAG).debug(f"VAD recording started at: {conn.vad_recording_start_time}")
#     elif have_voice and hasattr(conn, 'vad_recording_start_time'):
#         conn.logger.bind(tag=TAG).debug(f"VAD recording continues, started at: {conn.vad_recording_start_time}")

#     # Check if this is the initial connection period (ignore first 1 second of audio)
#     if have_voice and hasattr(conn, "initial_connection_handled") and not conn.initial_connection_handled:
#         current_time = asyncio.get_event_loop().time()
#         if current_time - conn.initial_connection_time < 1.0:  # Ignore first 1 second
#             have_voice = False
#             conn.asr_audio.clear()  # Clear any accumulated audio
#             return
#         else:
#             conn.initial_connection_handled = True

#     # If the device was just woken up, briefly ignore VAD detection
#     if have_voice and hasattr(conn, "just_woken_up") and conn.just_woken_up:
#         have_voice = False
#         # Set a brief delay before resuming VAD detection
#         conn.asr_audio.clear()
#         if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
#             conn.vad_resume_task = asyncio.create_task(
#                 resume_vad_detection(conn))
#         return

#     if have_voice:
#         if conn.client_is_speaking:
#             await handleAbortMessage(conn)
#     # Device long-term idle detection, used for say goodbye
#     await no_voice_close_connect(conn, have_voice)
#     # Receive audio
#     await conn.asr.receive_audio(conn, audio, have_voice)


# async def resume_vad_detection(conn):
#     # Wait 2 seconds before resuming VAD detection
#     await asyncio.sleep(1)
#     conn.just_woken_up = False


# async def startToChat(conn, text):
#     # Check if input is in JSON format (containing speaker information)
#     speaker_name = None
#     actual_text = text

#     try:
#         # Try to parse JSON format input
#         if text.strip().startswith('{') and text.strip().endswith('}'):
#             data = json.loads(text)
#             if 'speaker' in data and 'content' in data:
#                 speaker_name = data['speaker']
#                 actual_text = data['content']
#                 conn.logger.bind(tag=TAG).info(
#                     f"Parsed speaker information: {speaker_name}")

#                 # Use JSON format text directly, do not parse
#                 actual_text = text
#     except (json.JSONDecodeError, KeyError):
#         # If parsing fails, continue using original text
#         pass

#     # Save speaker information to connection object
#     if speaker_name:
#         conn.current_speaker = speaker_name
#     else:
#         conn.current_speaker = None

#     if conn.need_bind:
#         await check_bind_device(conn)
#         return

#     # If the daily output word count exceeds the limit
#     if conn.max_output_size > 0:
#         if check_device_output_limit(
#             conn.headers.get("device-id"), conn.max_output_size
#         ):
#             await max_out_size(conn)
#             return
#     if conn.client_is_speaking:
#         await handleAbortMessage(conn)

#     # First perform intent analysis, using actual text content
#     intent_handled = await handle_user_intent(conn, actual_text)

#     if intent_handled:
#         # If intent has been handled, no longer proceed with chat
#         return

#     # Intent not handled, continue with regular chat flow, using actual text content
#     await send_stt_message(conn, actual_text)
#     conn.executor.submit(conn.chat, actual_text)


# async def no_voice_close_connect(conn, have_voice):
#     if have_voice:
#         conn.last_activity_time = time.time() * 1000
#         return
#     # Only perform timeout check when timestamp has been initialized
#     if conn.last_activity_time > 0.0:
#         no_voice_time = time.time() * 1000 - conn.last_activity_time
#         close_connection_no_voice_time = int(
#             conn.config.get("close_connection_no_voice_time", 120)
#         )
#         if (
#             not conn.close_after_chat
#             and no_voice_time > 1000 * close_connection_no_voice_time
#         ):
#             conn.close_after_chat = True
#             conn.client_abort = False
#             end_prompt = conn.config.get("end_prompt", {})
#             if end_prompt and end_prompt.get("enable", True) is False:
#                 conn.logger.bind(tag=TAG).info(
#                     "End conversation, no need to send ending prompt")
#                 await conn.close()
#                 return
#             prompt = end_prompt.get("prompt")
#             if not prompt:
#                 prompt = "Please use ```time flies so fast``` as the opening, and use emotionally rich, reluctant words to end this conversation!"
#             await startToChat(conn, prompt)


# async def max_out_size(conn):
#     text = "Sorry, I have some things to deal with now. Let's chat again at this time tomorrow. It's a promise! See you tomorrow, goodbye!"
#     await send_stt_message(conn, text)
#     file_path = "config/assets/max_output_size.wav"
#     opus_packets, _ = audio_to_data(file_path)
#     conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
#     conn.close_after_chat = True


# async def check_bind_device(conn):
#     if conn.bind_code:
#         # Ensure bind_code is a 6-digit number
#         if len(conn.bind_code) != 6:
#             conn.logger.bind(tag=TAG).error(
#                 f"Invalid binding code format: {conn.bind_code}")
#             text = "Binding code format error, please check configuration."
#             await send_stt_message(conn, text)
#             return

#         text = f"Please log into the control panel and enter {conn.bind_code} to bind the device."
#         await send_stt_message(conn, text)

#         # Play notification sound
#         music_path = "config/assets/bind_code.wav"
#         opus_packets, _ = audio_to_data(music_path)
#         conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

#         # Play digits one by one
#         for i in range(6):  # Ensure only 6 digits are played
#             try:
#                 digit = conn.bind_code[i]
#                 num_path = f"config/assets/bind_code/{digit}.wav"
#                 num_packets, _ = audio_to_data(num_path)
#                 conn.tts.tts_audio_queue.put(
#                     (SentenceType.MIDDLE, num_packets, None))
#             except Exception as e:
#                 conn.logger.bind(tag=TAG).error(
#                     f"Failed to play digit audio: {e}")
#                 continue
#         conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
#     else:
#         text = f"Version information for this device was not found. Please configure the OTA address correctly and then recompile the firmware."
#         await send_stt_message(conn, text)
#         music_path = "config/assets/bind_not_found.wav"
#         opus_packets, _ = audio_to_data(music_path)
#         conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))

from core.handle.sendAudioHandle import send_stt_message
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.abortHandle import handleAbortMessage
import time
import asyncio
import json
from core.handle.sendAudioHandle import SentenceType
from core.utils.util import audio_to_data

TAG = __name__


async def handleAudioMessage(conn, audio):
    # Log that we received audio (only log periodically to avoid spam)
    if not hasattr(conn, '_audio_log_counter'):
        conn._audio_log_counter = 0
    conn._audio_log_counter += 1

    if conn._audio_log_counter % 200 == 0:  # Log every 200th packet (reduced from 50)
        conn.logger.bind(tag=TAG).debug(f"Received audio packet #{conn._audio_log_counter}, size: {len(audio)} bytes")

    # Skip VAD/ASR processing when server is speaking (streaming audio to client)
    # This prevents interruptions during TTS playback
    if conn.client_is_speaking:
        # conn.logger.bind(tag=TAG).debug("Server is speaking - skipping audio processing to prevent interruption")
        return

    # Whether the current segment has someone speaking
    have_voice = conn.vad.is_vad(conn, audio)
    
    # Track when voice recording starts in auto VAD mode (for 10-second timeout)
    # Only set the timer once per recording session when transitioning from no-voice to voice
    if have_voice:
        if not hasattr(conn, 'vad_recording_start_time'):
            # First voice detection in this session - set the timer
            conn.vad_recording_start_time = time.time()
            conn.logger.bind(tag=TAG).debug(f"VAD recording started at: {conn.vad_recording_start_time}")
        # Don't overwrite existing timer during continuous voice detection

    # Initial connection handling removed - no longer ignoring initial audio

    # If the device was just woken up, briefly ignore VAD detection
    if have_voice and hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # Set a brief delay before resuming VAD detection
        conn.asr_audio.clear()
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(
                resume_vad_detection(conn))
        return

    if have_voice:
        if conn.client_is_speaking:
            await handleAbortMessage(conn)
    # Device long-term idle detection, used for say goodbye
    await no_voice_close_connect(conn, have_voice)
    # Receive audio
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn):
    # Wait 2 seconds before resuming VAD detection
    await asyncio.sleep(1)
    conn.just_woken_up = False


async def startToChat(conn, text):
    # Check if input is in JSON format (containing speaker information)
    speaker_name = None
    actual_text = text

    try:
        # Try to parse JSON format input
        if text.strip().startswith('{') and text.strip().endswith('}'):
            data = json.loads(text)
            if 'speaker' in data and 'content' in data:
                speaker_name = data['speaker']
                actual_text = data['content']
                conn.logger.bind(tag=TAG).info(
                    f"Parsed speaker information: {speaker_name}")

                # Use JSON format text directly, do not parse
                actual_text = text
    except (json.JSONDecodeError, KeyError):
        # If parsing fails, continue using original text
        pass

    # Save speaker information to connection object
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # If the daily output word count exceeds the limit
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return
    if conn.client_is_speaking:
        await handleAbortMessage(conn)

    # First perform intent analysis, using actual text content
    intent_handled = await handle_user_intent(conn, actual_text)

    if intent_handled:
        # If intent has been handled, no longer proceed with chat
        return

    # Intent not handled, continue with regular chat flow, using actual text content
    await send_stt_message(conn, actual_text)
    conn.executor.submit(conn.chat, actual_text)


async def no_voice_close_connect(conn, have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # Only perform timeout check when timestamp has been initialized
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
                    "End conversation, no need to send ending prompt")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "Please use ```time flies so fast``` as the opening, and use emotionally rich, reluctant words to end this conversation!"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    text = "Sorry, I have some things to deal with now. Let's chat again at this time tomorrow. It's a promise! See you tomorrow, goodbye!"
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets, _ = audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn):
    if conn.bind_code:
        # Ensure bind_code is a 6-digit number
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(
                f"Invalid binding code format: {conn.bind_code}")
            text = "Binding code format error, please check configuration."
            await send_stt_message(conn, text)
            return

        text = f"Please log into the control panel and enter {conn.bind_code} to bind the device."
        await send_stt_message(conn, text)

        # Play notification sound
        music_path = "config/assets/bind_code.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # Play digits one by one
        for i in range(6):  # Ensure only 6 digits are played
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets, _ = audio_to_data(num_path)
                conn.tts.tts_audio_queue.put(
                    (SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(
                    f"Failed to play digit audio: {e}")
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        text = f"Version information for this device was not found. Please configure the OTA address correctly and then recompile the firmware."
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
