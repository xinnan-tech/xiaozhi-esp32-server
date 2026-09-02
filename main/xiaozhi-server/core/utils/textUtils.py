import json

TAG = __name__
EMOJI_MAP = {
    "😂": "funny",
    "😭": "crying",
    "😠": "angry",
    "😔": "sad",
    "😍": "loving",
    "😲": "surprised",
    "😱": "shocked",
    "🤔": "thinking",
    "😌": "relaxed",
    "😴": "sleepy",
    "😜": "silly",
    "🙄": "confused",
    "😶": "neutral",
    "🙂": "happy",
    "😆": "laughing",
    "😳": "embarrassed",
    "😉": "winking",
    "😎": "cool",
    "🤤": "delicious",
    "😘": "kissy",
    "😏": "confident",
}
EMOJI_RANGES = [
    (0x1F600, 0x1F64F),
    (0x1F300, 0x1F5FF),
    (0x1F680, 0x1F6FF),
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
]


def get_string_no_punctuation_or_emoji(s):
    """Remove spaces, punctuation and emoji from start/end of string"""
    chars = list(s)
    # Process starting characters
    start = 0
    while start < len(chars) and is_punctuation_or_emoji(chars[start]):
        start += 1
    # Process ending characters
    end = len(chars) - 1
    while end >= start and is_punctuation_or_emoji(chars[end]):
        end -= 1
    return "".join(chars[start : end + 1])


def is_punctuation_or_emoji(char):
    """Check if char is space, specified punctuation or emoji"""
    # Define Chinese/English punctuation to remove (including full/half width)
    punctuation_set = {
        "，",
        ",",  # Chinese comma + English comma
        "。",
        ".",  # Chinese period + English period
        "！",
        "!",  # Chinese exclamation mark + English exclamation mark
        "“",
        "”",
        '"',  # Chinese double quotes + English quotes
        "：",
        ":",  # Chinese colon + English colon
        "-",
        "－",  # English hyphen + Chinese full-width dash
        "、",  # Chinese uneven mark
        "[",
        "]",  # Brackets
        "【",
        "】",  # Chinese brackets
        "(", ")",  # English Parentheses
        "（", "）", # Chinese Parentheses
        ";", "；", # Semicolons
        "?", "？", # Question marks
        "~", "～", # Tildes
    }
    if char.isspace() or char in punctuation_set:
        return True
    return is_emoji(char)


async def get_emotion(conn, text):
    """Get emotion message/emoji within text"""
    emoji = "🙂"
    emotion = "happy"
    for char in text:
        if char in EMOJI_MAP:
            emoji = char
            emotion = EMOJI_MAP[char]
            break
    try:
        await conn.websocket.send(
            json.dumps(
                {
                    "type": "llm",
                    "text": emoji,
                    "emotion": emotion,
                    "session_id": conn.session_id,
                }
            )
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).warning(f"Failed to send emotion emoji, error: {e}")
    return


def is_emoji(char):
    """Check if char is an emoji"""
    code_point = ord(char)
    return any(start <= code_point <= end for start, end in EMOJI_RANGES)


def check_emoji(text):
    """Remove all emojis from text"""
    return ''.join(char for char in text if not is_emoji(char) and char != "\n")
