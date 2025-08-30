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

# S3 Streaming imports
import boto3
from botocore.exceptions import ClientError
import logging

# CDN Download imports
from core.utils.cdn_manager import download_cdn_file

TAG = __name__

MUSIC_CACHE = {}
MULTILINGUAL_MATCHER = None

# S3 Configuration
S3_CLIENT = None
S3_BUCKET_NAME = "cheeko-audio-files"

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
                "requested_language": {
                    "type": ["string", "null"],
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
def play_music(conn, user_request: str, song_type: str = "random", requested_language: str = None):
    try:
        # Check if music is already playing to prevent multiple simultaneous requests
        # if hasattr(conn, 'client_is_speaking') and conn.client_is_speaking:
        #     conn.logger.bind(tag=TAG).info(f"Music already playing, ignoring duplicate request: '{user_request}'")
        #     return ActionResponse(
        #         action=Action.RESPONSE, 
        #         result="Music already playing", 
        #         response="I'm already playing music for you!"
        #     )
        
        # Initialize multilingual matcher
        initialize_multilingual_music_system(conn)
        
        # Log the request for debugging
        conn.logger.bind(tag=TAG).info(f"Music request: '{user_request}', type: {song_type}, language: {requested_language}")

        # Check event loop status
        if not conn.loop.is_running():
            conn.logger.bind(tag=TAG).error("Event loop is not running, unable to submit task")
            return ActionResponse(
                action=Action.RESPONSE, result="System busy", response="Please try again later"
            )

        # Submit async task with enhanced parameters
        task = conn.loop.create_task(
            handle_multilingual_music_command(conn, user_request, song_type, requested_language)
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
            action=Action.RESPONSE, 
            result="Song not available", 
            response="The song you requested is not available right now, but it will be available soon. Please try again later."
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
    """Get all music files - S3 MODE: Read from metadata.json"""
    import json
    
    music_dir = Path(music_dir)
    music_files = []
    music_file_names = []
    
    # Iterate through language folders
    for language_folder in music_dir.iterdir():
        if language_folder.is_dir():
            language_name = language_folder.name
            
            # Check for metadata.json file first (S3 mode)
            metadata_file = language_folder / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Add music from metadata
                    for song_title, song_info in metadata.items():
                        filename = song_info.get('filename', f"{song_title}.mp3")
                        relative_path = f"{language_name}/{filename}"
                        music_files.append(relative_path)
                        music_file_names.append(os.path.splitext(relative_path)[0])
                    
                    logging.info(f"Loaded {len(metadata)} songs from {language_name} metadata")
                    continue
                    
                except Exception as e:
                    logging.error(f"Error reading metadata from {metadata_file}: {e}")
            
            # Fallback: scan for actual audio files (legacy mode)
            for file in language_folder.rglob("*"):
                if file.is_file():
                    ext = file.suffix.lower()
                    if ext in music_ext:
                        relative_path = str(file.relative_to(music_dir))
                        music_files.append(relative_path)
                        music_file_names.append(os.path.splitext(relative_path)[0])
    
    return music_files, music_file_names


def initialize_s3_client():
    """Initialize S3 client for streaming with SigV4"""
    global S3_CLIENT
    if S3_CLIENT is None:
        try:
            from botocore.config import Config
            
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            
            if aws_access_key and aws_secret_key:
                S3_CLIENT = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=aws_region,
                    config=Config(signature_version="s3v4")
                )
                logging.info(f"S3 client initialized for music streaming (region: {aws_region})")
            else:
                logging.warning("AWS credentials not found, S3 streaming disabled")
        except Exception as e:
            logging.error(f"Failed to initialize S3 client: {e}")
            S3_CLIENT = None

def generate_cdn_music_url(language, filename):
    """Generate CDN streaming URL for music file"""
    try:
        # Import CDN helper
        from utils.cdn_helper import get_audio_url
        
        # Ensure proper capitalization for S3 key (S3 folders are capitalized)
        language_capitalized = language.capitalize()
        audio_path = f"music/{language_capitalized}/{filename}"
        
        # Use CDN helper to generate URL with automatic encoding
        cdn_url = get_audio_url(audio_path)
        logging.info(f"Generated CDN URL for music: {audio_path} -> {cdn_url}")
        return cdn_url
        
    except Exception as e:
        logging.error(f"Error generating CDN URL for music: {e}")
        # Fallback to S3 presigned URL if CDN fails
        return generate_s3_music_url_fallback(language, filename)

def generate_s3_music_url_fallback(language, filename):
    """Fallback S3 streaming URL for music file"""
    global S3_CLIENT, S3_BUCKET_NAME
    
    if not S3_CLIENT:
        return None
    
    try:
        # Ensure proper capitalization for S3 key (S3 folders are capitalized)
        language_capitalized = language.capitalize()
        s3_key = f"music/{language_capitalized}/{filename}"
        url = S3_CLIENT.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=7200  # 2 hours for streaming
        )
        logging.info(f"Generated fallback S3 URL for music: {s3_key}")
        return url
    except ClientError as e:
        logging.error(f"Error generating fallback S3 URL for music: {e}")
        return None

def initialize_music_handler(conn):
    global MUSIC_CACHE
    # Initialize S3 client
    initialize_s3_client()
    
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

async def handle_multilingual_music_command(conn, user_request: str, song_type: str, requested_language: str = None):
    """Enhanced music command handler with multilingual AI matching"""
    global MULTILINGUAL_MATCHER, MUSIC_CACHE
    
    conn.logger.bind(tag=TAG).debug(f"Processing multilingual music request: '{user_request}'")
    
    # Check if music directory exists
    if not os.path.exists(MUSIC_CACHE["music_dir"]):
        conn.logger.bind(tag=TAG).error(f"Music directory does not exist: {MUSIC_CACHE['music_dir']}")
        await send_stt_message(conn, "The music collection is being set up. Songs will be available soon. Please try again later.")
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
    if not requested_language and MULTILINGUAL_MATCHER:
        requested_language = MULTILINGUAL_MATCHER.detect_language_from_request(user_request)
    
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
                conn.logger.bind(tag=TAG).info(f"AI match found: {selected_music} ({detected_language}) - overriding LLM language hint: {requested_language}")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error in AI matching: {e}")
    
    # Try language-specific selection for language requests or when language is detected
    if not selected_music and requested_language and MULTILINGUAL_MATCHER:
        try:
            language_content = MULTILINGUAL_MATCHER.get_language_specific_content(requested_language)
            if language_content:
                selected_path, metadata_entry = random.choice(language_content)
                selected_music = selected_path
                match_info = {
                    'method': 'language_random',
                    'language': requested_language,
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
        # Provide a user-friendly message when song is not available
        conn.logger.bind(tag=TAG).info(f"Song not found for request: {user_request}")
        not_available_message = "The song you requested is not available right now, but it will be available soon. Please try again later or ask for a different song."
        await send_stt_message(conn, not_available_message)

async def play_multilingual_music(conn, selected_music: str, match_info: dict, original_request: str):
    """Play selected music with contextual introduction - CDN STREAMING VERSION"""
    global MUSIC_CACHE
    
    try:
        # Extract language and filename from selected_music path
        # selected_music format: "Hindi/song.mp3" or "English/song.mp3"
        path_parts = selected_music.split('/')
        if len(path_parts) >= 2:
            language = path_parts[0]
            filename = path_parts[1]
        else:
            # Fallback: try to get from match_info
            language = match_info.get('language', 'English')
            filename = os.path.basename(selected_music)
        
        # Generate CDN streaming URL
        cdn_url = generate_cdn_music_url(language, filename)
        
        if not cdn_url:
            conn.logger.bind(tag=TAG).error(f"Failed to generate CDN URL for: {language}/{filename}")
            await send_stt_message(conn, "The song is not available right now, but it will be available soon. Please try again later.")
            return
        
        # CRITICAL CHANGE: Download from CDN to local file first
        # Try CDN download, fallback to presigned URL if needed
        local_file_path = await download_cdn_file(cdn_url, conn)
        if not local_file_path:
            conn.logger.bind(tag=TAG).warning(f"CDN download failed for: {cdn_url}")
            # Try direct presigned URL as fallback
            try:
                presigned_url = generate_s3_music_url_fallback(language, filename)
                if presigned_url:
                    conn.logger.bind(tag=TAG).info(f"Using presigned URL fallback: {presigned_url[:50]}...")
                    local_file_path = await download_cdn_file(presigned_url, conn)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"Presigned URL fallback failed: {e}")
        
        if not local_file_path:
            conn.logger.bind(tag=TAG).error(f"All download methods failed for: {language}/{filename}")
            await send_stt_message(conn, "The song is not available right now, but it will be available soon. Please try again later.")
            return
        
        # Generate contextual introduction based on match info
        intro_text = generate_multilingual_intro(match_info, original_request)
        
        # Set client_is_speaking flag to prevent VAD during music playback
        conn.client_is_speaking = True
        # Set llm_finish_task to ensure "stop" message is sent when music finishes
        conn.llm_finish_task = True
        conn.logger.bind(tag=TAG).info("Music playback started - pausing audio listening to prevent interruption")
        
        await send_stt_message(conn, intro_text)
        conn.dialogue.put(Message(role="assistant", content=intro_text))
        
        # Queue TTS messages with S3 URL
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
        
        # Use CDN URL instead of local file path
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.FILE,
                content_file=local_file_path,  # LOCAL FILE, NOT CDN URL!
            )
        )
        
        # Always send LAST message to ensure proper TTS stop signal
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.LAST,
                content_type=ContentType.ACTION,
            )
        )
        
        conn.logger.bind(tag=TAG).info(f"Streaming music from local cache: {local_file_path}")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to stream music from CDN: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")
        await send_stt_message(conn, "The song is not available right now, but it will be available soon. Please try again later.")

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
    """Play music from S3 - UPDATED FOR S3 STREAMING"""
    try:
        # Ensure path correctness
        if specific_file:
            selected_music = specific_file
        else:
            if not MUSIC_CACHE["music_files"]:
                conn.logger.bind(tag=TAG).error("No music files found in metadata")
                return
            selected_music = random.choice(MUSIC_CACHE["music_files"])

        # Extract language and filename from path
        path_parts = selected_music.split('/')
        if len(path_parts) >= 2:
            language = path_parts[0]
            filename = path_parts[1]
        else:
            # Fallback
            language = "English"
            filename = os.path.basename(selected_music)

        # Generate CDN streaming URL (CloudFront)
        cdn_url = generate_cdn_music_url(language, filename)
        
        if not cdn_url:
            conn.logger.bind(tag=TAG).error(f"Failed to generate CDN URL for: {language}/{filename}")
            await send_stt_message(conn, "The song is not available right now, but it will be available soon. Please try again later.")
            return

        # Download from CDN to local file first (same as multilingual function)
        local_file_path = await download_cdn_file(cdn_url, conn)
        if not local_file_path:
            conn.logger.bind(tag=TAG).warning(f"CDN download failed for: {cdn_url}")
            # Try presigned URL fallback
            try:
                presigned_url = generate_s3_music_url_fallback(language, filename)
                if presigned_url:
                    conn.logger.bind(tag=TAG).info(f"Using presigned URL fallback: {presigned_url[:50]}...")
                    local_file_path = await download_cdn_file(presigned_url, conn)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"Presigned URL fallback failed: {e}")
        
        if not local_file_path:
            conn.logger.bind(tag=TAG).error(f"All download methods failed for: {language}/{filename}")
            await send_stt_message(conn, "The song is not available right now, but it will be available soon. Please try again later.")
            return

        # Set client_is_speaking flag to prevent VAD during music playback
        conn.client_is_speaking = True
        # Set llm_finish_task to ensure "stop" message is sent when music finishes
        conn.llm_finish_task = True
        conn.logger.bind(tag=TAG).info("Music playback started - pausing audio listening to prevent interruption")
        
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
        # Use local downloaded file instead of streaming URL
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.FILE,
                content_file=local_file_path,  # LOCAL FILE, NOT STREAMING URL!
            )
        )
        
        # Always send LAST message to ensure proper TTS stop signal
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.LAST,
                content_type=ContentType.ACTION,
            )
        )

        conn.logger.bind(tag=TAG).info(f"Streaming music from local cache: {local_file_path}")

    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to stream music from CDN: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")
        await send_stt_message(conn, "The song is not available right now, but it will be available soon. Please try again later.")