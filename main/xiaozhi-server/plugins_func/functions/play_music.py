import os
import re
import time
import random
import difflib
import traceback
from pathlib import Path
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__

MUSIC_CACHE = {}

play_music_function_desc = {
    "type": "function",
    "function": {
        "name": "play_music",
        "description": "Method for singing, listening to songs, and playing music.",
        "parameters": {
            "type": "object",
            "properties": {
                "song_name": {
                    "type": "string",
                    "description": "Song name, if user doesn't specify a specific song name then 'random', when explicitly specified returns the music name Example: ```User: play Two Tigers\nParameter: Two Tigers``` ```User: play music\nParameter: random```",
                }
            },
            "required": ["song_name"],
        },
    },
}


@register_function("play_music", play_music_function_desc, ToolType.SYSTEM_CTL)
async def play_music(conn: "ConnectionHandler", song_name: str):
    try:
        music_intent = (
            f"play music {song_name}" if song_name != "random" else "play random music"
        )

        # Check event loop status
        if not conn.loop.is_running():
            conn.logger.bind(tag=TAG).error("Event loop not running, cannot submit task")
            return ActionResponse(
                action=Action.RESPONSE, result="System busy", response="Please try again later"
            )

        # Submit async task
        task = conn.loop.create_task(
            handle_music_command(conn, music_intent)  # Encapsulate async logic
        )

        # Non-blocking callback handling
        def handle_done(f):
            try:
                f.result()  # Can handle success logic here
                conn.logger.bind(tag=TAG).info("Playback completed")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"Playback failed: {e}")

        task.add_done_callback(handle_done)

        # RECORD: write the tool-call chain into dialogue history (so the
        # model remembers it played a song) without TTS'ing this line —
        # handle_music_command speaks the play prompt itself.
        return ActionResponse(
            action=Action.RECORD, result="Command received", response="Playing music for you"
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Error handling music intent: {e}")
        return ActionResponse(
            action=Action.RESPONSE, result=str(e), response="Error occurred while playing music"
        )


def _extract_song_name(text):
    """Extract song name from user input"""
    for keyword in ["play music"]:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip()
    return None


def _find_best_match(potential_song, music_files):
    """Find the best matching song"""
    best_match = None
    highest_ratio = 0

    for music_file in music_files:
        song_name = os.path.splitext(music_file)[0]
        ratio = difflib.SequenceMatcher(None, potential_song, song_name).ratio()
        if ratio > highest_ratio and ratio > 0.4:
            highest_ratio = ratio
            best_match = music_file
    return best_match


def get_music_files(music_dir, music_ext):
    music_dir = Path(music_dir)
    music_files = []
    music_file_names = []
    for file in music_dir.rglob("*"):
        # Check if it's a file
        if file.is_file():
            # Get file extension
            ext = file.suffix.lower()
            # Check if extension is in the list
            if ext in music_ext:
                # Add relative path
                music_files.append(str(file.relative_to(music_dir)))
                music_file_names.append(
                    os.path.splitext(str(file.relative_to(music_dir)))[0]
                )
    return music_files, music_file_names


def initialize_music_handler(conn: "ConnectionHandler"):
    global MUSIC_CACHE
    if MUSIC_CACHE == {}:
        plugins_config = conn.config.get("plugins", {})
        if "play_music" in plugins_config:
            MUSIC_CACHE["music_config"] = plugins_config["play_music"]
            MUSIC_CACHE["music_dir"] = os.path.abspath(
                MUSIC_CACHE["music_config"].get("music_dir", "./music")  # Default path modification
            )
            MUSIC_CACHE["music_ext"] = MUSIC_CACHE["music_config"].get(
                "music_ext", (".mp3", ".wav", ".p3")
            )
            MUSIC_CACHE["refresh_time"] = MUSIC_CACHE["music_config"].get(
                "refresh_time", 60
            )
        else:
            MUSIC_CACHE["music_dir"] = os.path.abspath("./music")
            MUSIC_CACHE["music_ext"] = (".mp3", ".wav", ".p3")
            MUSIC_CACHE["refresh_time"] = 60
        # Get music file list
        MUSIC_CACHE["music_files"], MUSIC_CACHE["music_file_names"] = get_music_files(
            MUSIC_CACHE["music_dir"], MUSIC_CACHE["music_ext"]
        )
        MUSIC_CACHE["scan_time"] = time.time()
    return MUSIC_CACHE


async def handle_music_command(conn: "ConnectionHandler", text):
    initialize_music_handler(conn)
    global MUSIC_CACHE

    """Handle music playback command"""
    clean_text = re.sub(r"[^\w\s]", "", text).strip()
    conn.logger.bind(tag=TAG).debug(f"Check if it's a music command: {clean_text}")

    # Try to match specific song name
    if os.path.exists(MUSIC_CACHE["music_dir"]):
        if time.time() - MUSIC_CACHE["scan_time"] > MUSIC_CACHE["refresh_time"]:
            # Refresh music file list
            MUSIC_CACHE["music_files"], MUSIC_CACHE["music_file_names"] = (
                get_music_files(MUSIC_CACHE["music_dir"], MUSIC_CACHE["music_ext"])
            )
            MUSIC_CACHE["scan_time"] = time.time()

        potential_song = _extract_song_name(clean_text)
        if potential_song:
            best_match = _find_best_match(potential_song, MUSIC_CACHE["music_files"])
            if best_match:
                conn.logger.bind(tag=TAG).info(f"Found best matching song: {best_match}")
                await play_local_music(conn, specific_file=best_match)
                return True
    # Check if it's a general play music command
    await play_local_music(conn)
    return True


def _get_random_play_prompt(song_name):
    """Generate random playback prompt"""
    # Remove file extension
    clean_name = os.path.splitext(song_name)[0]
    # No decorative brackets around the title: TTS would read them aloud.
    prompts = [
        f"Playing for you, {clean_name}",
        f"Please enjoy the song, {clean_name}",
        f"About to play for you, {clean_name}",
        f"Now bringing you, {clean_name}",
        f"Let's listen together, {clean_name}",
        f"Next please enjoy, {clean_name}",
        f"Now presenting to you, {clean_name}",
    ]
    # Use random.choice directly, don't set seed
    return random.choice(prompts)


async def play_local_music(conn: "ConnectionHandler", specific_file=None):
    global MUSIC_CACHE
    """Play local music file"""
    try:
        if not os.path.exists(MUSIC_CACHE["music_dir"]):
            conn.logger.bind(tag=TAG).error(
                f"Music directory does not exist: " + MUSIC_CACHE["music_dir"]
            )
            return

        # Ensure path correctness
        if specific_file:
            selected_music = specific_file
            music_path = os.path.join(MUSIC_CACHE["music_dir"], specific_file)
        else:
            if not MUSIC_CACHE["music_files"]:
                conn.logger.bind(tag=TAG).error("No MP3 music files found")
                return
            selected_music = random.choice(MUSIC_CACHE["music_files"])
            music_path = os.path.join(MUSIC_CACHE["music_dir"], selected_music)

        if not os.path.exists(music_path):
            conn.logger.bind(tag=TAG).error(f"Selected music file does not exist: {music_path}")
            return
        text = _get_random_play_prompt(selected_music)
        conn.dialogue.put(Message(role="assistant", content=text))

        if conn.intent_type == "intent_llm":
            conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=conn.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.TEXT,
                content_detail=text,
            )
        )
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.FILE,
                content_file=music_path,
            )
        )
        if conn.intent_type == "intent_llm":
            conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=conn.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )

    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Music playback failed: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")
