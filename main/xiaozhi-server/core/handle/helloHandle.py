import time
import json
import random
import asyncio
from core.utils.dialogue import Message
from core.utils.util import audio_to_data
from core.handle.sendAudioHandle import sendAudioMessage, send_stt_message
from core.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tts.dto.dto import ContentType, SentenceType
from core.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)
from core.utils.wakeup_word import WakeupWordsConfig

TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 5,
    "words": ["你好", "你好啊", "嘿，你好", "嗨"],
}

# Create global wakeup words configuration manager
wakeup_words_config = WakeupWordsConfig()

# Lock to prevent concurrent calls to wakeupWordsResponse
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn, msg_json):
    """Handle hello message"""
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

        # Handle both list and dictionary formats for features
        has_mcp = False
        if isinstance(features, list):
            has_mcp = "mcp" in features
        elif isinstance(features, dict):
            has_mcp = features.get("mcp", False)

        if has_mcp:
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

    if not enable_wakeup_words_response_cache or not conn.tts:
        return False

    _, filtered_text = remove_punctuation_and_length(text)
    if filtered_text not in conn.config.get("wakeup_words"):
        return False

    conn.just_woken_up = True
    await send_stt_message(conn, text)

    # Get current voice
    voice = getattr(conn.tts, "voice", "default")
    if not voice:
        voice = "default"

    # Get wakeup words reply configuration
    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": "config/assets/wakeup_words.wav",
            "time": 0,
            "text": "哈啰啊，我是小智啦，声音好听的台湾女孩一枚，超开心认识你耶，最近在忙啥，别忘了给我来点有趣的料哦，我超爱听八卦的啦",
        }

    # Play wakeup words reply
    conn.client_abort = False
    opus_packets, _ = audio_to_data(response.get("file_path"))

    conn.logger.bind(tag=TAG).info(
        f"Playing wakeup words reply: {response.get('text')}")
    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    await sendAudioMessage(conn, SentenceType.LAST, [], None)

    # Add to dialogue
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))

    # Check if wakeup words reply needs to be updated
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn):
    if not conn.tts or not conn.llm or not conn.llm.response_no_stream:
        return

    try:
        # Try to acquire lock, return if cannot acquire
        if not await _wakeup_response_lock.acquire():
            return

        # Generate wakeup words reply
        wakeup_word = random.choice(WAKEUP_CONFIG["words"])
        question = (
            "The user is currently saying ```"
            + wakeup_word
            + "``` to you.\nPlease reply to the user's content above in 20-30 words. It should match the role's emotions and attitude set in the system, don't talk like a robot.\n"
            + "Please do not explain or respond to this content itself, do not return emojis, only return a reply to the user's content."
        )

        result = conn.llm.response_no_stream(conn.config["prompt"], question)
        if not result or len(result) == 0:
            return

        # Generate TTS audio
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        # Get current voice
        voice = getattr(conn.tts, "voice", "default")

        wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=16000)
        file_path = wakeup_words_config.generate_file_path(voice)
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
        # Update configuration
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
    finally:
        # Ensure lock is released in any case
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()
