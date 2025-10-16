import time
import json
import random
import asyncio
from core.utils.dialogue import Message
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType
from core.utils.wakeup_word import WakeupWordsConfig
from core.handle.sendAudioHandle import sendAudioMessage, send_stt_message
from core.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)

TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 5,
    "words": ["Hello", "Hello", "Hey, hello", "Hi"],
}

# Create a global wake-up word configuration manager
wakeup_words_config = WakeupWordsConfig()

# Lock used to prevent concurrent calls to wakeupWordsResponse
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn, msg_json):
    """Process hello message"""
    audio_params = msg_json.get("audio_params")
    if audio_params:
        format = audio_params.get("format")
        conn.logger.bind(tag=TAG).info(f"Client audio format: {format}")
        conn.audio_format = format
        conn.welcome_msg["audio_params"] = audio_params
    features = msg_json.get("features")
    if features:
        conn.logger.bind(tag=TAG).info(f"Client features: {features}")
        conn.features = features
        if features.get("mcp"):
            conn.logger.bind(tag=TAG).info("Client supports MCP")
            conn.mcp_client = MCPClient()
            # Send initialization
            asyncio.create_task(send_mcp_initialize_message(conn))
            # Send mcp message to get tools list
            asyncio.create_task(send_mcp_tools_list_request(conn))

    await conn.websocket.send(json.dumps(conn.welcome_msg))


async def checkWakeupWords(conn, text):
    enable_wakeup_words_response_cache = conn.config[
        "enable_wakeup_words_response_cache"
    ]

    # Wait for tts to initialize, wait up to 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3:
        if conn.tts:
            break
        await asyncio.sleep(0.1)
    else:
        return False

    if not enable_wakeup_words_response_cache:
        return False

    _, filtered_text = remove_punctuation_and_length(text)
    if filtered_text not in conn.config.get("wakeup_words"):
        return False

    conn.just_woken_up = True
    await send_stt_message(conn, text)

    # Get the current timbre
    voice = getattr(conn.tts, "voice", "default")
    if not voice:
        voice = "default"

    # Get the wake-up word reply configuration
    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": "config/assets/wakeup_words.wav",
            "time": 0,
            "text": "Hello, I'm Xiaozhi, a Taiwanese girl with a nice voice. I'm so happy to meet you. What are you busy with recently? Don't forget to give me some interesting information. I love to hear gossip."
        }

    # Get audio data
    opus_packets = audio_to_data(response.get("file_path"))
    # Play wake-up word reply
    conn.client_abort = False

    conn.logger.bind(tag=TAG).info(f"Play wake-up word reply: {response.get('text')}")
    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    await sendAudioMessage(conn, SentenceType.LAST, [], None)

    # Additional dialogue
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))

    # Check if the wakeup word reply needs to be updated
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn):
    if not conn.tts or not conn.llm or not conn.llm.response_no_stream:
        return

    try:
        # Try to acquire the lock, and return if it cannot be acquired
        if not await _wakeup_response_lock.acquire():
            return

        # Generate wake-up word response
        wakeup_word = random.choice(WAKEUP_CONFIG["words"])
        question = (
            "The user is talking to you at this moment"
            + wakeup_word
            + "```.\nPlease write a 20-30 word reply based on the above user's content. Please be consistent with the character's emotions and attitude set by the system, and do not speak like a robot.\n"
            + "Please do not provide any explanation or response to this content. Do not return emoticons. Only return replies to the user's content."
        )

        result = conn.llm.response_no_stream(conn.config["prompt"], question)
        if not result or len(result) == 0:
            return

        # Generate TTS audio
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        # Get the current timbre
        voice = getattr(conn.tts, "voice", "default")

        wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=16000)
        file_path = wakeup_words_config.generate_file_path(voice)
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
        # Update configuration
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
    finally:
        # Make sure the lock is released in any case
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()