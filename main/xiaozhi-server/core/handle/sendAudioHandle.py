# import json
# import asyncio
# import time
# from core.providers.tts.dto.dto import SentenceType
# from core.utils import textUtils

# TAG = __name__


# async def sendAudioMessage(conn, sentenceType, audios, text):
#     # Send sentence start message
#     conn.logger.bind(tag=TAG).info(
#         f"Send audio message: {sentenceType}, {text}")

#     pre_buffer = False
#     if conn.tts.tts_audio_first_sentence:
#         conn.logger.bind(tag=TAG).info(f"Send first audio segment: {text}")
#         conn.tts.tts_audio_first_sentence = False
#         pre_buffer = True

#     await send_tts_message(conn, "sentence_start", text)

#     await sendAudio(conn, audios, pre_buffer)

#     # Send end message (if it's the last text)
#     if conn.llm_finish_task and sentenceType == SentenceType.LAST:
#         await send_tts_message(conn, "stop", None)
#         conn.client_is_speaking = False
#         if conn.close_after_chat:
#             await conn.close()


# # Play audio
# async def sendAudio(conn, audios, pre_buffer=True):
#     if audios is None or len(audios) == 0:
#         return
#     # Flow control parameter optimization
#     # Frame duration (milliseconds), matching Opus encoding
#     frame_duration = 60
#     start_time = time.perf_counter()
#     play_position = 0

#     # Execute pre-buffering only for the first sentence
#     if pre_buffer:
#         pre_buffer_frames = min(3, len(audios))
#         for i in range(pre_buffer_frames):
#             await conn.websocket.send(audios[i])
#         remaining_audios = audios[pre_buffer_frames:]
#     else:
#         remaining_audios = audios

#     # Play remaining audio frames
#     for opus_packet in remaining_audios:
#         if conn.client_abort:
#             break

#         # Reset no-voice state
#         conn.last_activity_time = time.time() * 1000

#         # Calculate expected send time
#         expected_time = start_time + (play_position / 1000)
#         current_time = time.perf_counter()
#         delay = expected_time - current_time
#         if delay > 0:
#             await asyncio.sleep(delay)

#         await conn.websocket.send(opus_packet)

#         play_position += frame_duration


# async def send_tts_message(conn, state, text=None):
#     """Send TTS status message"""
#     message = {"type": "tts", "state": state, "session_id": conn.session_id}
#     if text is not None:
#         message["text"] = textUtils.check_emoji(text)

#     # TTS playback ended
#     if state == "stop":
#         # Play notification sound
#         tts_notify = conn.config.get("enable_stop_tts_notify", False)
#         if tts_notify:
#             stop_tts_notify_voice = conn.config.get(
#                 "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
#             )
#             audios, _ = conn.tts.audio_to_opus_data(stop_tts_notify_voice)
#             await sendAudio(conn, audios)
#         # Clear server speaking status and resume listening
#         conn.clearSpeakStatus()
#         conn.logger.bind(tag=TAG).info("TTS finished - resuming audio listening")

#     # Send message to client
#     await conn.websocket.send(json.dumps(message))


# async def send_stt_message(conn, text):
#     end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
#     if end_prompt_str and end_prompt_str == text:
#         await send_tts_message(conn, "start")
#         return

#     """Send STT status message"""

#     # Parse JSON format, extract actual user speech content
#     display_text = text
#     try:
#         # Try to parse JSON format
#         if text.strip().startswith('{') and text.strip().endswith('}'):
#             parsed_data = json.loads(text)
#             if isinstance(parsed_data, dict) and "content" in parsed_data:
#                 # If it's JSON format containing speaker information, only display the content part
#                 display_text = parsed_data["content"]
#                 # Save speaker information to conn object
#                 if "speaker" in parsed_data:
#                     conn.current_speaker = parsed_data["speaker"]
#     except (json.JSONDecodeError, TypeError):
#         # If it's not JSON format, use original text directly
#         display_text = text
#     stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
#     await conn.websocket.send(
#         json.dumps({"type": "stt", "text": stt_text,
#                    "session_id": conn.session_id})
#     )
#     conn.client_is_speaking = True
#     conn.logger.bind(tag=TAG).info("TTS started - pausing audio listening to prevent interruption")
#     await send_tts_message(conn, "start")

import json
import asyncio
import time
from core.providers.tts.dto.dto import SentenceType
from core.utils import textUtils

TAG = __name__


async def sendAudioMessage(conn, sentenceType, audios, text):
    # Send sentence start message
    conn.logger.bind(tag=TAG).info(
        f"Send audio message: {sentenceType}, {text}")

    pre_buffer = False
    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).info(f"Send first audio segment: {text}")
        conn.tts.tts_audio_first_sentence = False
        pre_buffer = True

    await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios, pre_buffer)

    # Send end message (if it's the last text)
    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None)
        conn.client_is_speaking = False
        if conn.close_after_chat:
            await conn.close()


# Play audio
async def sendAudio(conn, audios, pre_buffer=True):
    if audios is None or len(audios) == 0:
        return
    # Flow control parameter optimization
    # Frame duration (milliseconds), matching Opus encoding
    frame_duration = 60
    start_time = time.perf_counter()
    play_position = 0

    # Execute pre-buffering only for the first sentence
    if pre_buffer:
        pre_buffer_frames = min(3, len(audios))
        for i in range(pre_buffer_frames):
            await conn.websocket.send(audios[i])
        remaining_audios = audios[pre_buffer_frames:]
    else:
        remaining_audios = audios

    # Play remaining audio frames
    for opus_packet in remaining_audios:
        if conn.client_abort:
            break

        # Reset no-voice state
        conn.last_activity_time = time.time() * 1000

        # Calculate expected send time
        expected_time = start_time + (play_position / 1000)
        current_time = time.perf_counter()
        delay = expected_time - current_time
        if delay > 0:
            await asyncio.sleep(delay)

        await conn.websocket.send(opus_packet)

        play_position += frame_duration


async def send_tts_message(conn, state, text=None):
    """Send TTS status message"""
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # TTS playback ended
    if state == "stop":
        # Play notification sound
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios, _ = conn.tts.audio_to_opus_data(stop_tts_notify_voice)
            await sendAudio(conn, audios)
        # Clear server speaking status and resume listening
        conn.clearSpeakStatus()
        conn.logger.bind(tag=TAG).info("TTS finished - resuming audio listening")

    # Send message to client
    await conn.websocket.send(json.dumps(message))
    # await conn.websocket.send(json.dumps({
    #     "type": "tts",
    #     "state": "stop",
    #     "session_id": conn.session_id
    # }))



async def send_stt_message(conn, text):
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    """Send STT status message"""

    # Parse JSON format, extract actual user speech content
    display_text = text
    try:
        # Try to parse JSON format
        if text.strip().startswith('{') and text.strip().endswith('}'):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # If it's JSON format containing speaker information, only display the content part
                display_text = parsed_data["content"]
                # Save speaker information to conn object
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # If it's not JSON format, use original text directly
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text,
                   "session_id": conn.session_id})
    )
    conn.client_is_speaking = True
    conn.logger.bind(tag=TAG).info("TTS started - pausing audio listening to prevent interruption")
    await send_tts_message(conn, "start")
