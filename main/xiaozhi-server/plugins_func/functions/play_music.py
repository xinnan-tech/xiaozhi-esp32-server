import os
import re
import time
import random
import difflib
import traceback
from pathlib import Path
from core.handle.sendAudioHandle import send_stt_message
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.dialogue import Message
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
from plugins_func.utils.multilingual_matcher import MultilingualMatcher

TAG = __name__

MUSIC_CACHE = {}
MULTILINGUAL_MATCHER = None

play_music_function_desc = {
    "type": "function",
    "function": {
        "name": "play_music",
        "description": "Advanced multilingual music player that understands natural language requests in any language. Supports specific song requests, language preferences, mood-based selection, and educational content. Handles requests like 'play Baa Baa Black Sheep', 'sing a Hindi song', 'play phonics', 'I want energetic music', 'play something in Telugu', etc. Uses AI-powered matching to find songs even with different spellings or scripts.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Complete user request for music. Include the full original request to enable intelligent matching. Examples: 'play Baa Baa Black Sheep', 'sing Hanuman Chalisa', 'play any Hindi song', 'I want Telugu music', 'play phonics songs', 'something energetic', 'play music for kids'",
                },
                "language_preference": {
                    "type": "string",
                    "description": "Detected or requested language preference. Options: 'english', 'hindi', 'telugu', 'kannada', 'tamil', 'phonics', or 'any'. Only set if explicitly mentioned or clearly implied.",
                },
                "song_type": {
                    "type": "string",
                    "enum": ["specific", "random", "language_specific", "educational"],
                    "description": "Type of request: 'specific' for named songs (e.g., 'play Hanuman Chalisa', 'bandar mama song'), 'random' for any song, 'language_specific' for language-only requests (e.g., 'play Hindi song'), 'educational' for phonics/learning content"
                }
            },
            "required": ["user_request", "song_type"],
        },
    },
}


@register_function("play_music", play_music_function_desc, ToolType.SYSTEM_CTL)
def play_music(conn, user_request: str, song_type: str = "random", language_preference: str = None):
    try:
        # Initialize multilingual matcher
        initialize_multilingual_music_system(conn)
        
        # Log the request for debugging
        conn.logger.bind(tag=TAG).info(f"Music request: '{user_request}', type: {song_type}, language: {language_preference}")

        # Check event loop status
        if not conn.loop.is_running():
            conn.logger.bind(tag=TAG).error("Event loop is not running, unable to submit task")
            return ActionResponse(
                action=Action.RESPONSE, result="System busy", response="Please try again later"
            )

        # Submit async task with enhanced parameters
        task = conn.loop.create_task(
            handle_multilingual_music_command(conn, user_request, song_type, language_preference)
        )

        # Non-blocking callback handling
        def handle_done(f):
            try:
                f.result()
                conn.logger.bind(tag=TAG).info("Multilingual music playback completed")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"Multilingual music playback failed: {e}")

        task.add_done_callback(handle_done)

        return ActionResponse(
            action=Action.NONE, 
            result="Multilingual music command received", 
            response="Let me find the perfect song for you!"
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Error handling multilingual music request: {e}")
        return ActionResponse(
            action=Action.RESPONSE, result=str(e), response="Error occurred while processing your music request"
        )


def _extract_song_name(text):
    """Extract song name from user input with multiple trigger patterns"""
    # Define various music-related keywords and patterns
    music_keywords = [
        "play music",
        "play",
        "sing",
        "sing a song",
        "sing me",
        "can you sing",
        "put on some music",
        "put on",
        "I want to hear",
        "listen to",
        "play some music",
        "music"
    ]
    
    text_lower = text.lower()
    
    # Try to extract song name after various patterns
    for keyword in music_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in text_lower:
            # Find the position of the keyword
            keyword_pos = text_lower.find(keyword_lower)
            
            # Extract everything after the keyword
            after_keyword = text[keyword_pos + len(keyword):].strip()
            
            # Remove common words that might follow
            common_words = ["for me", "please", "now", "some", "a song", "the song"]
            for word in common_words:
                after_keyword = after_keyword.replace(word, "").strip()
            
            # If we found something meaningful after the keyword, return it
            if after_keyword and len(after_keyword) > 1:
                return after_keyword
    
    return None


def _detect_language_request(text):
    """Detect if user is requesting music from a specific language/folder"""
    text_lower = text.lower()
    
    # Define language mappings (you can add more languages as needed)
    language_mappings = {
        # Phonics variations (Educational content)
        "phonics": "phonics",
        "phonics song": "phonics",
        "phonics music": "phonics",
        "play phonics": "phonics",
        "sing phonics": "phonics",
        "learn phonics": "phonics",
        "phonics sounds": "phonics",
        "alphabet sounds": "phonics",
        "letter sounds": "phonics",
        
        # English variations
        "english": "English",
        "english song": "English", 
        "english music": "English",
        "any english": "English",
        
        # Telugu variations
        "telugu": "Telugu",
        "telugu song": "Telugu",
        "telugu music": "Telugu",
        "any telugu": "Telugu",
        
        # Hindi variations
        "hindi": "Hindi",
        "hindi song": "Hindi",
        "hindi music": "Hindi",
        "any hindi": "Hindi",
        
        # Tamil variations
        "tamil": "Tamil",
        "tamil song": "Tamil",
        "tamil music": "Tamil",
        "any tamil": "Tamil",
        
        # Add more languages as needed
        "kannada": "Kannada",
        "malayalam": "Malayalam",
        "bengali": "Bengali",
        "punjabi": "Punjabi",
        "marathi": "Marathi",
        "gujarati": "Gujarati",
    }
    
    # Check for language requests
    for key, folder_name in language_mappings.items():
        if key in text_lower:
            return folder_name
    
    return None


def _get_language_specific_files(music_dir, music_ext, language_folder):
    """Get music files from a specific language folder"""
    language_path = Path(music_dir) / language_folder
    
    if not language_path.exists():
        return [], []
    
    music_files = []
    music_file_names = []
    
    for file in language_path.rglob("*"):
        if file.is_file():
            ext = file.suffix.lower()
            if ext in music_ext:
                # Get relative path from the main music directory
                relative_path = str(file.relative_to(Path(music_dir)))
                music_files.append(relative_path)
                music_file_names.append(os.path.splitext(relative_path)[0])
    
    return music_files, music_file_names


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


def initialize_music_handler(conn):
    global MUSIC_CACHE
    if MUSIC_CACHE == {}:
        if "play_music" in conn.config["plugins"]:
            MUSIC_CACHE["music_config"] = conn.config["plugins"]["play_music"]
            MUSIC_CACHE["music_dir"] = os.path.abspath(
                MUSIC_CACHE["music_config"].get("music_dir", "./music")  # Default path modified
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

def initialize_multilingual_music_system(conn):
    """Initialize the multilingual music matching system"""
    global MULTILINGUAL_MATCHER, MUSIC_CACHE
    
    # Initialize basic music cache first
    initialize_music_handler(conn)
    
    # Initialize multilingual matcher if not already done
    if MULTILINGUAL_MATCHER is None:
        try:
            MULTILINGUAL_MATCHER = MultilingualMatcher(
                MUSIC_CACHE["music_dir"], 
                MUSIC_CACHE["music_ext"]
            )
            conn.logger.bind(tag=TAG).info(f"Multilingual music matcher initialized with languages: {MULTILINGUAL_MATCHER.language_folders}")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Failed to initialize multilingual matcher: {e}")
            MULTILINGUAL_MATCHER = None

async def handle_multilingual_music_command(conn, user_request: str, song_type: str, language_preference: str = None):
    """Enhanced music command handler with multilingual AI matching"""
    global MULTILINGUAL_MATCHER, MUSIC_CACHE
    
    conn.logger.bind(tag=TAG).debug(f"Processing multilingual music request: '{user_request}'")
    
    # Check if music directory exists
    if not os.path.exists(MUSIC_CACHE["music_dir"]):
        conn.logger.bind(tag=TAG).error(f"Music directory does not exist: {MUSIC_CACHE['music_dir']}")
        await send_stt_message(conn, "Sorry, I couldn't find the music collection.")
        return
    
    # Refresh cache if needed
    if time.time() - MUSIC_CACHE["scan_time"] > MUSIC_CACHE["refresh_time"]:
        MUSIC_CACHE["music_files"], MUSIC_CACHE["music_file_names"] = get_music_files(
            MUSIC_CACHE["music_dir"], MUSIC_CACHE["music_ext"]
        )
        MUSIC_CACHE["scan_time"] = time.time()
    
    selected_music = None
    match_info = None
    
    # Detect language from request if not provided
    if not language_preference and MULTILINGUAL_MATCHER:
        language_preference = MULTILINGUAL_MATCHER.detect_language_from_request(user_request)
    
    # Check if this is a language-only request
    is_language_only = MULTILINGUAL_MATCHER and MULTILINGUAL_MATCHER.is_language_only_request(user_request)
    
    # Try multilingual AI matching for specific songs (ignore LLM language hint for better accuracy)
    if MULTILINGUAL_MATCHER and song_type in ["specific", "random"] and not is_language_only:
        try:
            # First try without language hint to find best match across all languages
            match_result = MULTILINGUAL_MATCHER.find_content_match(user_request, None)
            if match_result:
                selected_music, detected_language, metadata_entry = match_result
                match_info = {
                    'method': 'ai_multilingual',
                    'language': detected_language,
                    'title': metadata_entry.get('romanized', 'Unknown'),
                    'original_title': list(MULTILINGUAL_MATCHER.metadata_cache[detected_language]['metadata'].keys())[
                        list(MULTILINGUAL_MATCHER.metadata_cache[detected_language]['metadata'].values()).index(metadata_entry)
                    ] if detected_language in MULTILINGUAL_MATCHER.metadata_cache else 'Unknown'
                }
                conn.logger.bind(tag=TAG).info(f"AI match found: {selected_music} ({detected_language}) - overriding LLM language hint: {language_preference}")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error in AI matching: {e}")
    
    # Try language-specific selection for language requests or when language is detected
    if not selected_music and language_preference and MULTILINGUAL_MATCHER:
        try:
            language_content = MULTILINGUAL_MATCHER.get_language_specific_content(language_preference)
            if language_content:
                selected_path, metadata_entry = random.choice(language_content)
                selected_music = selected_path
                match_info = {
                    'method': 'language_random',
                    'language': language_preference,
                    'title': metadata_entry.get('romanized', 'Unknown')
                }
                conn.logger.bind(tag=TAG).info(f"Language-specific random selection: {selected_music}")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error in language-specific selection: {e}")
    
    # Fallback to legacy matching methods
    if not selected_music:
        # Try legacy language detection and matching
        requested_language = _detect_language_request(user_request)
        if requested_language:
            language_files, language_file_names = _get_language_specific_files(
                MUSIC_CACHE["music_dir"], MUSIC_CACHE["music_ext"], requested_language
            )
            if language_files:
                selected_music = random.choice(language_files)
                match_info = {
                    'method': 'legacy_language',
                    'language': requested_language,
                    'title': os.path.splitext(os.path.basename(selected_music))[0]
                }
                conn.logger.bind(tag=TAG).info(f"Legacy language match: {selected_music}")
        
        # Try legacy song name matching
        if not selected_music:
            potential_song = _extract_song_name(user_request)
            if potential_song:
                best_match = _find_best_match(potential_song, MUSIC_CACHE["music_files"])
                if best_match:
                    selected_music = best_match
                    match_info = {
                        'method': 'legacy_fuzzy',
                        'language': 'unknown',
                        'title': os.path.splitext(os.path.basename(selected_music))[0]
                    }
                    conn.logger.bind(tag=TAG).info(f"Legacy fuzzy match: {selected_music}")
    
    # Final fallback to random selection
    if not selected_music and MUSIC_CACHE["music_files"]:
        selected_music = random.choice(MUSIC_CACHE["music_files"])
        match_info = {
            'method': 'random_fallback',
            'language': 'unknown',
            'title': os.path.splitext(os.path.basename(selected_music))[0]
        }
        conn.logger.bind(tag=TAG).info(f"Random fallback: {selected_music}")
    
    # Play the selected music
    if selected_music:
        await play_multilingual_music(conn, selected_music, match_info, user_request)
    else:
        conn.logger.bind(tag=TAG).error("No music found to play")
        await send_stt_message(conn, "Sorry, I couldn't find any music to play.")

async def play_multilingual_music(conn, selected_music: str, match_info: dict, original_request: str):
    """Play selected music with contextual introduction"""
    global MUSIC_CACHE
    
    try:
        # Ensure path correctness
        if not os.path.isabs(selected_music):
            music_path = os.path.join(MUSIC_CACHE["music_dir"], selected_music)
        else:
            music_path = selected_music
        
        if not os.path.exists(music_path):
            conn.logger.bind(tag=TAG).error(f"Selected music file does not exist: {music_path}")
            return
        
        # Generate contextual introduction based on match info
        intro_text = generate_multilingual_intro(match_info, original_request)
        
        await send_stt_message(conn, intro_text)
        conn.dialogue.put(Message(role="assistant", content=intro_text))
        
        # Queue TTS messages
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
                content_detail=intro_text,
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
        
        conn.logger.bind(tag=TAG).info(f"Playing multilingual music: {music_path}")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to play multilingual music: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")

def generate_multilingual_intro(match_info: dict, original_request: str) -> str:
    """Generate contextual introduction based on matching method and info"""
    method = match_info.get('method', 'unknown')
    language = match_info.get('language', 'unknown')
    title = match_info.get('title', 'Unknown Song')
    original_title = match_info.get('original_title', title)
    
    # Ensure language is a string and handle None case
    if not language or not isinstance(language, str):
        language = 'unknown'
    
    try:
        if method == 'ai_multilingual':
            if language != 'unknown':
                intros = [
                    f"Perfect! I found '{title}' in {language.title()} for you!",
                    f"Great choice! Here's '{title}' - a beautiful {language.title()} song!",
                    f"I found exactly what you wanted: '{title}' in {language.title()}!",
                    f"Playing '{title}' - this {language.title()} song should be perfect!"
                ]
            else:
                intros = [
                    f"I found '{title}' which matches your request perfectly!",
                    f"Here's '{title}' - I think you'll love it!",
                    f"Playing '{title}' based on your request!"
                ]
        elif method == 'language_random':
            intros = [
                f"Here's a lovely {language.title()} song for you: '{title}'!",
                f"Playing '{title}' - a beautiful {language.title()} selection!",
                f"I picked '{title}' from our {language.title()} collection!"
            ]
        elif method == 'legacy_language':
            intros = [
                f"Playing a {language.title()} song: '{title}'!",
                f"Here's '{title}' in {language.title()} for you!",
                f"Enjoy this {language.title()} music: '{title}'!"
            ]
        elif method == 'legacy_fuzzy':
            intros = [
                f"I think you'll like '{title}'!",
                f"Playing '{title}' - hope this is what you wanted!",
                f"Here's '{title}' for you!"
            ]
        else:  # random_fallback
            intros = [
                f"Let me play '{title}' for you!",
                f"Here's a nice song: '{title}'!",
                f"Playing '{title}' - enjoy the music!"
            ]
        
        return random.choice(intros)
    
    except Exception as e:
        # Fallback intro if there's any error
        return f"Playing '{title}' for you!"


async def handle_music_command(conn, text):
    initialize_music_handler(conn)
    global MUSIC_CACHE

    """Handle music playback commands"""
    clean_text = re.sub(r"[^\w\s]", "", text).strip()
    conn.logger.bind(tag=TAG).debug(f"Check if it's a music command: {clean_text}")

    # Check if user is requesting a specific language
    requested_language = _detect_language_request(clean_text)
    
    if os.path.exists(MUSIC_CACHE["music_dir"]):
        if time.time() - MUSIC_CACHE["scan_time"] > MUSIC_CACHE["refresh_time"]:
            # Refresh music file list
            MUSIC_CACHE["music_files"], MUSIC_CACHE["music_file_names"] = (
                get_music_files(MUSIC_CACHE["music_dir"], MUSIC_CACHE["music_ext"])
            )
            MUSIC_CACHE["scan_time"] = time.time()

        # If language is specified, get files from that language folder
        if requested_language:
            conn.logger.bind(tag=TAG).info(f"Language request detected: {requested_language}")
            language_files, language_file_names = _get_language_specific_files(
                MUSIC_CACHE["music_dir"], MUSIC_CACHE["music_ext"], requested_language
            )
            
            if language_files:
                # Play random song from the requested language folder
                selected_music = random.choice(language_files)
                conn.logger.bind(tag=TAG).info(f"Playing {requested_language} song: {selected_music}")
                await play_local_music(conn, specific_file=selected_music)
                return True
            else:
                conn.logger.bind(tag=TAG).warning(f"No {requested_language} songs found")
                # Fall back to general music if no songs found in requested language
        
        # Try to match specific song name
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
    """Generate random play prompt"""
    # Remove file extension and extract just the filename (not the folder path)
    clean_name = os.path.splitext(os.path.basename(song_name))[0]
    prompts = [
        f"Now playing for you, '{clean_name}'",
        f"Please enjoy the song, '{clean_name}'",
        f"About to play for you, '{clean_name}'",
        f"Now bringing you, '{clean_name}'",
        f"Let's listen together to, '{clean_name}'",
        f"Next, please enjoy, '{clean_name}'",
        f"At this moment, presenting to you, '{clean_name}'",
    ]
     # Use random.choice directly, don't set seed
    return random.choice(prompts)


async def play_local_music(conn, specific_file=None):
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
        await send_stt_message(conn, text)
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
        conn.logger.bind(tag=TAG).error(f"Failed to play music: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")