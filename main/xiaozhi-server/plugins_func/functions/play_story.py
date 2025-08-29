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

STORY_CACHE = {}
STORY_MULTILINGUAL_MATCHER = None

# Story categories mapping for better recognition
STORY_CATEGORIES = {
    "bedtime": ["Bedtime", "bedtime story", "sleep story", "night story"],
    "fantasy": ["Fantasy", "fantasy story", "magical story", "magic story"],
    "fairy tales": ["Fairy Tales", "fairy tale", "fairytale"],
    "educational": ["Educational", "educational story", "learning story", "education"],
    "adventure": ["Adventure", "adventure story", "exciting story"]
}

play_story_function_desc = {
    "type": "function",
    "function": {
        "name": "play_story",
        "description": (
            "CRITICAL: This function ONLY plays pre-recorded story audio files from the stories folder. "
            "NEVER generate, create, or tell stories using text. ALWAYS call this function for ANY story request. "
            "This plays actual audio story files, not generated text stories. "
            "MANDATORY: Use this function for ALL story requests including: 'tell me a story', 'story please', "
            "'I want to hear a story', 'play a bedtime story', 'tell me The Boy Who Cried Wolf', etc. "
            "DO NOT create stories with text - only play pre-recorded audio story files. "
            "Examples: 'tell me a story' → play random story file, 'bedtime story' → play bedtime category file, "
            "'कहानी सुनाओ' (Hindi) → play story file, 'ಕಥೆ ಹೇಳಿ' (Kannada) → play story file"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Complete user request for story. Examples: 'tell me a story', 'tell me The Boy Who Cried Wolf story', 'play a bedtime story', 'I want to hear a fantasy story', 'story please', 'कहानी सुनाओ', 'ಕಥೆ ಹೇಳಿ'",
                },
                "story_type": {
                    "type": "string",
                    "enum": ["specific", "category", "random"],
                    "description": "ALWAYS use 'random' for general requests like 'tell me a story'. Use 'specific' only for named stories like 'The Boy Who Cried Wolf'. Use 'category' for requests like 'bedtime story', 'fantasy story'."
                },
                "category_preference": {
                    "type": "string",
                    "description": "Story category if mentioned: 'bedtime', 'fantasy', 'fairy tales', 'educational', 'adventure'. Only set if explicitly mentioned.",
                },
                "requested_language": {
                    "type": "string",
                    "description": "Language user requested the story in (e.g., 'hindi', 'english', 'kannada'). Note: Stories may be available in multiple languages depending on metadata.",
                }
            },
            "required": ["user_request", "story_type"],
        },
    },
}


@register_function("play_story", play_story_function_desc, ToolType.SYSTEM_CTL)
def play_story(conn, user_request: str, story_type: str = "random", category_preference: str = None, requested_language: str = None):
    try:
        # Initialize multilingual story system
        initialize_multilingual_story_system(conn)
        
        # Log the request for debugging
        conn.logger.bind(tag=TAG).info(f"Story request: '{user_request}', type: {story_type}, category: {category_preference}, language: {requested_language}")

        # Check event loop status
        if not conn.loop.is_running():
            conn.logger.bind(tag=TAG).error("Event loop not running, cannot submit task")
            return ActionResponse(
                action=Action.RESPONSE, result="System busy", response="Please try again later"
            )

        # Submit async task with enhanced parameters
        task = conn.loop.create_task(
            handle_multilingual_story_command(conn, user_request, story_type, category_preference, requested_language)
        )

        # Non-blocking callback handling
        def handle_done(f):
            try:
                f.result()
                conn.logger.bind(tag=TAG).info("Multilingual story playback completed")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"Multilingual story playback failed: {e}")

        task.add_done_callback(handle_done)

        return ActionResponse(
            action=Action.NONE, 
            result="Multilingual story command received", 
            response="Let me find a wonderful story for you!"
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Error handling multilingual story request: {e}")
        return ActionResponse(
            action=Action.RESPONSE, result=str(e), response="Error occurred while processing your story request"
        )


def normalize_category_name(category_input):
    """Normalize story category name to match folder names"""
    if not category_input:
        return None
    
    category_lower = category_input.lower().strip()
    
    # Direct mapping for exact matches from LLM
    direct_mappings = {
        "bedtime": "Bedtime",
        "fantasy": "Fantasy", 
        "fairy tales": "Fairy Tales",
        "educational": "Educational",
        "adventure": "Adventure",
        "random": None  # None means select random category
    }
    
    # Check direct mappings first
    if category_lower in direct_mappings:
        return direct_mappings[category_lower]
    
    # Check against category variations
    for key, variations in STORY_CATEGORIES.items():
        for variation in variations:
            if variation.lower() in category_lower or category_lower in variation.lower():
                # Return the actual folder name
                if key == "bedtime":
                    return "Bedtime"
                elif key == "fantasy":
                    return "Fantasy"
                elif key == "fairy tales":
                    return "Fairy Tales"
                elif key == "educational":
                    return "Educational"
                elif key == "adventure":
                    return "Adventure"
    
    # If no match, return None to trigger random selection
    return None


def get_story_files(story_dir, story_ext):
    """Get all story files organized by category"""
    story_dir = Path(story_dir)
    story_files_by_category = {}
    all_story_files = []
    
    # Check if stories directory exists
    if not story_dir.exists():
        return {}, []
    
    # Iterate through category folders
    for category_folder in story_dir.iterdir():
        if category_folder.is_dir():
            category_name = category_folder.name
            story_files_by_category[category_name] = []
            
            # Get all story files in this category
            for file in category_folder.rglob("*"):
                if file.is_file():
                    ext = file.suffix.lower()
                    if ext in story_ext:
                        relative_path = str(file.relative_to(story_dir))
                        story_files_by_category[category_name].append(relative_path)
                        all_story_files.append(relative_path)
    
    return story_files_by_category, all_story_files


def initialize_story_handler(conn):
    """Initialize story handler with configuration"""
    global STORY_CACHE
    if STORY_CACHE == {}:
        if "play_story" in conn.config["plugins"]:
            STORY_CACHE["story_config"] = conn.config["plugins"]["play_story"]
            STORY_CACHE["story_dir"] = os.path.abspath(
                STORY_CACHE["story_config"].get("story_dir", "./stories")
            )
            STORY_CACHE["story_ext"] = STORY_CACHE["story_config"].get(
                "story_ext", (".mp3", ".wav", ".p3")
            )
            STORY_CACHE["refresh_time"] = STORY_CACHE["story_config"].get(
                "refresh_time", 300  # Refresh every 5 minutes
            )
        else:
            STORY_CACHE["story_dir"] = os.path.abspath("./stories")
            STORY_CACHE["story_ext"] = (".mp3", ".wav", ".p3")
            STORY_CACHE["refresh_time"] = 300
        
        # Get story files organized by category
        STORY_CACHE["story_files_by_category"], STORY_CACHE["all_story_files"] = get_story_files(
            STORY_CACHE["story_dir"], STORY_CACHE["story_ext"]
        )
        STORY_CACHE["scan_time"] = time.time()
        
        # Log available categories
        if STORY_CACHE["story_files_by_category"]:
            conn.logger.bind(tag=TAG).info(
                f"Found story categories: {list(STORY_CACHE['story_files_by_category'].keys())}"
            )
            for category, files in STORY_CACHE["story_files_by_category"].items():
                conn.logger.bind(tag=TAG).info(f"  {category}: {len(files)} stories")
    
    return STORY_CACHE

def initialize_multilingual_story_system(conn):
    """Initialize the multilingual story matching system"""
    global STORY_MULTILINGUAL_MATCHER, STORY_CACHE
    
    # Initialize basic story cache first
    initialize_story_handler(conn)
    
    # Initialize multilingual matcher if not already done
    if STORY_MULTILINGUAL_MATCHER is None:
        try:
            STORY_MULTILINGUAL_MATCHER = MultilingualMatcher(
                STORY_CACHE["story_dir"], 
                STORY_CACHE["story_ext"]
            )
            if STORY_MULTILINGUAL_MATCHER.language_folders:
                conn.logger.bind(tag=TAG).info(f"Multilingual story matcher initialized with languages: {STORY_MULTILINGUAL_MATCHER.language_folders}")
            else:
                conn.logger.bind(tag=TAG).info("Multilingual story matcher initialized (no metadata.json found, using filesystem fallback)")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Failed to initialize multilingual story matcher: {e}")
            STORY_MULTILINGUAL_MATCHER = None

async def handle_multilingual_story_command(conn, user_request: str, story_type: str, category_preference: str = None, requested_language: str = None):
    """Enhanced story command handler with multilingual AI matching"""
    global STORY_MULTILINGUAL_MATCHER, STORY_CACHE
    
    conn.logger.bind(tag=TAG).debug(f"Processing multilingual story request: '{user_request}'")
    
    # Check if stories directory exists
    if not os.path.exists(STORY_CACHE["story_dir"]):
        conn.logger.bind(tag=TAG).error(f"Story directory does not exist: {STORY_CACHE['story_dir']}")
        await send_stt_message(conn, "Sorry, I couldn't find the story collection.")
        return
    
    # Refresh cache if needed
    if time.time() - STORY_CACHE["scan_time"] > STORY_CACHE["refresh_time"]:
        STORY_CACHE["story_files_by_category"], STORY_CACHE["all_story_files"] = get_story_files(
            STORY_CACHE["story_dir"], STORY_CACHE["story_ext"]
        )
        STORY_CACHE["scan_time"] = time.time()
    
    selected_story = None
    match_info = None
    
    # Try multilingual AI matching for specific stories
    if STORY_MULTILINGUAL_MATCHER and story_type == "specific":
        try:
            match_result = STORY_MULTILINGUAL_MATCHER.find_content_match(user_request, requested_language)
            if match_result:
                selected_story, detected_language, metadata_entry = match_result
                match_info = {
                    'method': 'ai_multilingual',
                    'language': detected_language,
                    'title': metadata_entry.get('romanized', 'Unknown'),
                    'original_title': list(STORY_MULTILINGUAL_MATCHER.metadata_cache[detected_language]['metadata'].keys())[
                        list(STORY_MULTILINGUAL_MATCHER.metadata_cache[detected_language]['metadata'].values()).index(metadata_entry)
                    ] if detected_language in STORY_MULTILINGUAL_MATCHER.metadata_cache else 'Unknown',
                    'category': 'unknown'
                }
                conn.logger.bind(tag=TAG).info(f"AI story match found: {selected_story} ({detected_language})")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error in AI story matching: {e}")
    
    # Try language-specific selection if no AI match and language is specified
    if not selected_story and requested_language and STORY_MULTILINGUAL_MATCHER:
        try:
            language_content = STORY_MULTILINGUAL_MATCHER.get_language_specific_content(requested_language)
            if language_content:
                selected_path, metadata_entry = random.choice(language_content)
                selected_story = selected_path
                match_info = {
                    'method': 'language_random',
                    'language': requested_language,
                    'title': metadata_entry.get('romanized', 'Unknown'),
                    'category': 'unknown'
                }
                conn.logger.bind(tag=TAG).info(f"Language-specific story selection: {selected_story}")
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error in language-specific story selection: {e}")
    
    # Fallback to legacy category-based selection
    if not selected_story and category_preference:
        normalized_category = normalize_category_name(category_preference)
        if normalized_category and normalized_category in STORY_CACHE["story_files_by_category"]:
            if STORY_CACHE["story_files_by_category"][normalized_category]:
                selected_story = random.choice(STORY_CACHE["story_files_by_category"][normalized_category])
                match_info = {
                    'method': 'category_selection',
                    'language': 'english',  # Default assumption
                    'title': os.path.splitext(os.path.basename(selected_story))[0],
                    'category': normalized_category
                }
                conn.logger.bind(tag=TAG).info(f"Category-based story selection: {selected_story}")
    
    # Try legacy specific story matching
    if not selected_story and story_type == "specific":
        # Extract story name and try fuzzy matching
        story_name_match = find_best_story_match(user_request, STORY_CACHE["all_story_files"])
        if story_name_match:
            selected_story = story_name_match
            match_info = {
                'method': 'legacy_fuzzy',
                'language': 'english',
                'title': os.path.splitext(os.path.basename(selected_story))[0],
                'category': selected_story.split(os.sep)[0] if os.sep in selected_story else 'unknown'
            }
            conn.logger.bind(tag=TAG).info(f"Legacy fuzzy story match: {selected_story}")
    
    # Final fallback to random selection
    if not selected_story and STORY_CACHE["all_story_files"]:
        selected_story = random.choice(STORY_CACHE["all_story_files"])
        match_info = {
            'method': 'random_fallback',
            'language': 'english',
            'title': os.path.splitext(os.path.basename(selected_story))[0],
            'category': selected_story.split(os.sep)[0] if os.sep in selected_story else 'unknown'
        }
        conn.logger.bind(tag=TAG).info(f"Random story fallback: {selected_story}")
    
    # Play the selected story
    if selected_story:
        await play_multilingual_story(conn, selected_story, match_info, user_request)
    else:
        conn.logger.bind(tag=TAG).error("No stories found to play")
        await send_stt_message(conn, "Sorry, I couldn't find any stories to play.")

async def play_multilingual_story(conn, selected_story: str, match_info: dict, original_request: str):
    """Play selected story with contextual introduction"""
    global STORY_CACHE
    
    try:
        # Ensure path correctness
        if not os.path.isabs(selected_story):
            story_path = os.path.join(STORY_CACHE["story_dir"], selected_story)
        else:
            story_path = selected_story
        
        if not os.path.exists(story_path):
            conn.logger.bind(tag=TAG).error(f"Selected story file does not exist: {story_path}")
            return
        
        # Generate contextual introduction based on match info
        intro_text = generate_multilingual_story_intro(match_info, original_request)
        
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
                content_file=story_path,
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
        
        conn.logger.bind(tag=TAG).info(f"Playing multilingual story: {story_path}")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to play multilingual story: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")

def generate_multilingual_story_intro(match_info: dict, original_request: str) -> str:
    """Generate contextual introduction based on matching method and info"""
    method = match_info.get('method', 'unknown')
    language = match_info.get('language', 'english')
    title = match_info.get('title', 'Unknown Story')
    category = match_info.get('category', 'story')
    original_title = match_info.get('original_title', title)
    
    # Clean up the title (remove underscores, etc.)
    clean_title = title.replace("_", " ").replace("-", " ")
    
    if method == 'ai_multilingual':
        if language != 'english':
            intros = [
                f"Perfect! I found '{clean_title}' for you!",
                f"Great choice! Here's the story '{clean_title}'!",
                f"I found exactly what you wanted: '{clean_title}'!",
                f"Let me tell you '{clean_title}' - this should be perfect!"
            ]
        else:
            intros = [
                f"I found '{clean_title}' which matches your request perfectly!",
                f"Here's '{clean_title}' - I think you'll love this story!",
                f"Playing '{clean_title}' based on your request!"
            ]
    elif method == 'language_random':
        intros = [
            f"Here's a wonderful story for you: '{clean_title}'!",
            f"Let me tell you '{clean_title}' - a beautiful story!",
            f"I picked '{clean_title}' from our collection!"
        ]
    elif method == 'category_selection':
        if category != 'unknown':
            intros = [
                f"Here's a lovely {category.lower()} story: '{clean_title}'!",
                f"Perfect! I have a {category.lower()} story for you: '{clean_title}'!",
                f"Let me tell you this {category.lower()} story called '{clean_title}'!"
            ]
        else:
            intros = [
                f"Here's a wonderful story: '{clean_title}'!",
                f"Let me tell you '{clean_title}'!",
                f"I have a great story for you: '{clean_title}'!"
            ]
    elif method == 'legacy_fuzzy':
        intros = [
            f"I think you'll love '{clean_title}'!",
            f"Here's '{clean_title}' - hope this is what you wanted!",
            f"Let me tell you the story of '{clean_title}'!"
        ]
    else:  # random_fallback
        intros = [
            f"Let me tell you a wonderful story: '{clean_title}'!",
            f"Here's a great story for you: '{clean_title}'!",
            f"I have a special story called '{clean_title}'!"
        ]
    
    return random.choice(intros)


def find_best_story_match(story_name, story_files):
    """Find the best matching story from available files"""
    best_match = None
    highest_ratio = 0
    
    for story_file in story_files:
        # Extract just the filename without path and extension
        file_name = os.path.splitext(os.path.basename(story_file))[0]
        ratio = difflib.SequenceMatcher(None, story_name.lower(), file_name.lower()).ratio()
        if ratio > highest_ratio and ratio > 0.5:  # Higher threshold for stories
            highest_ratio = ratio
            best_match = story_file
    
    return best_match


async def handle_story_command(conn, category, specific_story=None, requested_language=None):
    """Handle story playback command"""
    initialize_story_handler(conn)
    global STORY_CACHE
    
    conn.logger.bind(tag=TAG).debug(f"Handling story command - Category: {category}, Story: {specific_story}, Language: {requested_language}")
    
    # Check if stories directory exists
    if not os.path.exists(STORY_CACHE["story_dir"]):
        conn.logger.bind(tag=TAG).error(f"Story directory does not exist: {STORY_CACHE['story_dir']}")
        await send_stt_message(conn, "Sorry, I couldn't find the story collection.")
        return
    
    # Refresh cache if needed
    if time.time() - STORY_CACHE["scan_time"] > STORY_CACHE["refresh_time"]:
        STORY_CACHE["story_files_by_category"], STORY_CACHE["all_story_files"] = get_story_files(
            STORY_CACHE["story_dir"], STORY_CACHE["story_ext"]
        )
        STORY_CACHE["scan_time"] = time.time()
    
    selected_story = None
    
    # If specific story name is provided, try to find it
    if specific_story:
        selected_story = find_best_story_match(specific_story, STORY_CACHE["all_story_files"])
        if selected_story:
            conn.logger.bind(tag=TAG).info(f"Found matching story: {selected_story}")
    
    # If no specific story found, select based on category
    if not selected_story:
        if category and category.lower() != "random":
            # Normalize category name
            normalized_category = normalize_category_name(category)
            
            # Try to find the category
            matching_category = None
            for cat_name in STORY_CACHE["story_files_by_category"].keys():
                if cat_name.lower() == normalized_category.lower():
                    matching_category = cat_name
                    break
            
            if matching_category and STORY_CACHE["story_files_by_category"][matching_category]:
                selected_story = random.choice(STORY_CACHE["story_files_by_category"][matching_category])
                conn.logger.bind(tag=TAG).info(f"Selected {matching_category} story: {selected_story}")
            else:
                conn.logger.bind(tag=TAG).warning(f"Category '{category}' not found or empty, selecting random story")
                if STORY_CACHE["all_story_files"]:
                    selected_story = random.choice(STORY_CACHE["all_story_files"])
        else:
            # Select random story from all available
            if STORY_CACHE["all_story_files"]:
                selected_story = random.choice(STORY_CACHE["all_story_files"])
                conn.logger.bind(tag=TAG).info(f"Selected random story: {selected_story}")
    
    if selected_story:
        await play_story_file(conn, selected_story, requested_language)
    else:
        conn.logger.bind(tag=TAG).error("No stories found in the collection")
        await send_stt_message(conn, "I'm sorry, I couldn't find any stories to play.")


def get_story_intro(story_file, requested_language=None):
    """Generate an introduction for the story"""
    # Extract story name and category
    parts = story_file.split(os.sep)
    if len(parts) > 1:
        category = parts[0]
        story_name = os.path.splitext(parts[-1])[0]
    else:
        category = "story"
        story_name = os.path.splitext(story_file)[0]
    
    # Clean up the story name (remove underscores, etc.)
    story_name = story_name.replace("_", " ").replace("-", " ")
    
    # Always use English intros since stories are in English
    intros = [
        f"Let me tell you a wonderful {category.lower()} story called '{story_name}'",
        f"Here's a {category.lower()} story for you: '{story_name}'",
        f"Get comfortable and enjoy this {category.lower()} story: '{story_name}'",
        f"I have a special {category.lower()} story for you called '{story_name}'",
        f"Listen carefully to this amazing story: '{story_name}'",
        f" Let's begin '{story_name}'",
    ]
    
    intro = random.choice(intros)
    
    # Add note if requested in another language
    if requested_language and requested_language != "english":
        intro = f"Playing English story. {intro}"
    
    return intro


async def play_story_file(conn, story_file, requested_language=None):
    """Play the selected story file"""
    try:
        story_path = os.path.join(STORY_CACHE["story_dir"], story_file)
        
        if not os.path.exists(story_path):
            conn.logger.bind(tag=TAG).error(f"Story file does not exist: {story_path}")
            return
        
        # Generate and send introduction (always in English)
        intro_text = get_story_intro(story_file, requested_language)
        await send_stt_message(conn, intro_text)
        conn.dialogue.put(Message(role="assistant", content=intro_text))
        
        # Send TTS messages to play the story
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
                content_file=story_path,
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
        
        conn.logger.bind(tag=TAG).info(f"Playing story: {story_path}")
        
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to play story: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"Detailed error: {traceback.format_exc()}")