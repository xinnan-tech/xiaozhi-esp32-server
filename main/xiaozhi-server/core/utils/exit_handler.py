"""
Centralized exit/goodbye detection and handling.

Consolidates exit command matching and graceful shutdown logic
that was previously duplicated across connection.py and intentHandler.py.

Pre-caches TTS audio for exit replies so goodbye messages play instantly
without waiting for TTS generation.
"""
import uuid
import random
import threading
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# Module-level cache: maps goodbye text -> list of opus packets
_exit_audio_cache = {}
_cache_lock = threading.Lock()
_cache_initialized = False


def is_exit_command(text: str, exit_commands: list) -> bool:
    """
    Check if text matches any configured exit command.

    Args:
        text: User input text (will be stripped of punctuation and lowercased)
        exit_commands: List of exit command strings from config

    Returns:
        True if text matches an exit command
    """
    if not exit_commands or not text:
        return False
    clean = text.strip(" .,!?").lower()
    return clean in exit_commands


def pre_cache_exit_audio(tts_provider, exit_replies: list):
    """
    Pre-generate TTS audio for all exit replies in a background thread.
    Call once after TTS provider is ready (e.g., after open_audio_channels).

    Args:
        tts_provider: The TTS provider instance (has to_tts method)
        exit_replies: List of goodbye phrases to pre-generate
    """
    global _cache_initialized
    if _cache_initialized or not exit_replies:
        return

    def _generate():
        global _cache_initialized
        for reply in exit_replies:
            try:
                result = tts_provider.to_tts(reply)
                if result is not None:
                    # to_tts returns either a file path or a list of opus packets
                    if isinstance(result, list):
                        with _cache_lock:
                            _exit_audio_cache[reply] = result
                    else:
                        # It's a file path — convert to opus packets
                        from core.utils.util import audio_to_data
                        import asyncio
                        loop = asyncio.new_event_loop()
                        try:
                            packets = loop.run_until_complete(audio_to_data(result))
                            with _cache_lock:
                                _exit_audio_cache[reply] = packets
                        finally:
                            loop.close()
                    logger.bind(tag=TAG).debug(f"Pre-cached exit audio: '{reply}'")
                else:
                    logger.bind(tag=TAG).warning(f"Failed to pre-cache exit audio: '{reply}'")
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Error pre-caching exit audio for '{reply}': {e}")
        _cache_initialized = True
        logger.bind(tag=TAG).info(f"Exit audio cache ready: {len(_exit_audio_cache)}/{len(exit_replies)} phrases cached")

    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()


def handle_exit(conn, exit_replies: list = None):
    """
    Initiate a graceful exit with a random goodbye message.

    If pre-cached audio is available, bypasses TTS generation entirely by
    putting opus packets directly into the audio queue (~instant playback).
    Otherwise falls back to the TTS text queue.

    Args:
        conn: ConnectionHandler instance
        exit_replies: List of goodbye phrases. If None, reads from conn.config.
    """
    if exit_replies is None:
        exit_replies = getattr(conn, "config", {}).get("exit_replies", [])

    goodbye_text = random.choice(exit_replies) if exit_replies else "Goodbye!"

    conn.close_after_chat = True
    conn.sentence_id = str(uuid.uuid4().hex)

    # Try to use pre-cached audio (bypasses TTS generation entirely)
    with _cache_lock:
        cached_audio = _exit_audio_cache.get(goodbye_text)

    if cached_audio:
        # Put audio directly into the audio queue — skips TTS generation
        conn.tts.tts_audio_first_sentence = True
        conn.tts.tts_audio_queue.put((SentenceType.LAST, cached_audio, goodbye_text))
        logger.bind(tag=TAG).info(f"Exit initiated (cached): '{goodbye_text}'")
    else:
        # Fall back to normal TTS text queue
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.LAST,
                content_type=ContentType.TEXT,
                content_detail=goodbye_text,
            )
        )
        logger.bind(tag=TAG).info(f"Exit initiated (TTS): '{goodbye_text}'")
