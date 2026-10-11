import re
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

EMOTION_EMOJI_MAP = {
    "HAPPY": "🙂",
    "SAD": "😔",
    "ANGRY": "😡",
    "NEUTRAL": "😶",
    "FEARFUL": "😰",
    "DISGUSTED": "🤢",
    "SURPRISED": "😲",
    "EMO_UNKNOWN": "😶",  # Default unknown emotion to a neutral emoji.
}
# EVENT_EMOJI_MAP = {
#     "<|BGM|>": "🎼",
#     "<|Speech|>": "",
#     "<|Applause|>": "👏",
#     "<|Laughter|>": "😀",
#     "<|Cry|>": "😭",
#     "<|Sneeze|>": "🤧",
#     "<|Breath|>": "",
#     "<|Cough|>": "🤧",
# }

def lang_tag_filter(text: str) -> dict:
    """
    Parse FunASR output and extract tags plus plain-text content in order.

    Args:
        text: Raw ASR output, which may include multiple tags.

    Returns:
        dict: Structured content when tags are present.
        str: Plain text when no tags are present.

    Examples:
        FunASR format: <|language|><|emotion|><|event|><|other options|>text
        >>> lang_tag_filter("<|zh|><|SAD|><|Speech|><|withitn|>Hello there, test test.")
        {"language": "zh", "emotion": "SAD", "emoji": "😔", "content": "Hello there, test test."}
        >>> lang_tag_filter("<|en|><|HAPPY|><|Speech|><|withitn|>Hello hello.")
        {"language": "en", "emotion": "HAPPY", "emoji": "🙂", "content": "Hello hello."}
        >>> lang_tag_filter("plain text")
        {"content": "plain text"}
    """
    # Extract all tags in order.
    tag_pattern = r"<\|([^|]+)\|>"
    all_tags = re.findall(tag_pattern, text)

    # Remove all <|...|> tags to get the plain text.
    clean_text = re.sub(tag_pattern, "", text).strip()

    # Return the plain text if no tags are present.
    if not all_tags:
        return {"content": clean_text}

    # Extract tags according to FunASR's fixed ordering.
    language = all_tags[0] if len(all_tags) > 0 else "zh"
    emotion = all_tags[1] if len(all_tags) > 1 else "NEUTRAL"
    # event = all_tags[2] if len(all_tags) > 2 else "Speech"  # Event tag currently unused.

    result = {
        "content": clean_text,
        "language": language,
        "emotion": emotion,
        # "event": event,
    }

    # Replace the emotion code with its emoji mapping.
    if emotion in EMOTION_EMOJI_MAP:
        result["emotion"] = EMOTION_EMOJI_MAP[emotion]
    # The event tag is not currently used.
    # if event in EVENT_EMOJI_MAP:
    #     result["event"] = EVENT_EMOJI_MAP[event]

    return result
