import time
import json
import uuid
import random
import asyncio
from core.utils.dialogue import Message
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType
from core.utils.wakeup_word import WakeupWordsConfig
from core.handle.sendAudioHandle import sendAudioMessage, send_tts_message
from core.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes

TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 10,
    "responses": [
        "I'm here, go ahead.",
        "I'm listening, how can I help?",
        "Ready for your command.",
        "I'm right here.",
        "Yes? I'm listening.",
        "Tell me what you need.",
        "Ready when you are.",
        "How can I assist you?",
        "Awaiting your instructions.",
    ],
}

# Global wakeup words config manager
wakeup_words_config = WakeupWordsConfig()

# Lock to prevent concurrent calls to wakeupWordsResponse
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn, msg_json):
    """Protocol-compliant handshake for XiaoZhi firmware"""
    
    # 1. Update session-specific audio params
    audio_params = msg_json.get("audio_params")
    if audio_params:
        conn.audio_format = audio_params.get("format")
    
    # 2. Assign features (Setting mcp to False in the response tells the 
    # firmware not to wait for further MCP packets during the handshake)
    features = msg_json.get("features", {})
    conn.features = features

    # 3. Generate a Session ID
    session_id = str(uuid.uuid4().hex)
    conn.session_id = session_id

    # 4. Construct protocol response
    response = {
        "type": "hello",
        "version": msg_json.get("version", 1),
        "transport": msg_json.get("transport", "websocket"),
        "auth_key": conn.config["xiaozhi"]["auth_key"],
        "session_id": session_id,
        "message": "success",
        # Force MCP enabled to ensure client listeners are active
        "features": {**features, "mcp": True},
        "audio_params": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
            "frame_duration": 60
        }
    }

    # 5. Brief pause to ensure network buffers are ready
    await asyncio.sleep(0.1)

    # 6. Send and Log exactly what was sent
    resp_json = json.dumps(response)
    await conn.websocket.send(resp_json)
    conn.logger.bind(tag=TAG).info(f"Handshake mirrored: {resp_json}")


async def checkWakeupWords(conn, text):
    """Check if the transcribed text matches any wakeup words"""
    enable_wakeup_words_response_cache = conn.config.get(
        "enable_wakeup_words_response_cache", False
    )

    # Wait for TTS initialization (max 3 seconds)
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
    if filtered_text not in conn.config.get("wakeup_words", []):
        return False

    conn.just_woken_up = True
    await send_tts_message(conn, "start")

    voice = getattr(conn.tts, "voice", "default") or "default"

    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": "config/assets/wakeup_words_short.wav",
            "time": 0,
            "text": "I'm here!",
        }

    # Get audio data
    opus_packets = await audio_to_data(response.get("file_path"), use_cache=False)
    conn.client_abort = False

    # Treat wakeup as a new session
    conn.sentence_id = str(uuid.uuid4().hex)

    conn.logger.bind(tag=TAG).info(f"Playing wakeup response: {response.get('text')}")
    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    await sendAudioMessage(conn, SentenceType.LAST, [], None)

    # Append to dialogue
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))

    # Check if we need to refresh the cached response
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn):
    """Generate and cache a new random wakeup response"""
    if not conn.tts:
        return

    try:
        if not await _wakeup_response_lock.acquire():
            return

        result = random.choice(WAKEUP_CONFIG["responses"])
        if not result:
            return

        # Generate TTS audio in thread
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        voice = getattr(conn.tts, "voice", "default")
        wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=16000)
        file_path = wakeup_words_config.generate_file_path(voice)
        
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
            
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
    finally:
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()

