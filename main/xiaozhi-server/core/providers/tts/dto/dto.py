from enum import Enum
from typing import Union, Optional


class SentenceType(Enum):
    # Speaking stage
    FIRST = "FIRST"  # First sentence
    MIDDLE = "MIDDLE"  # Speaking in progress
    LAST = "LAST"  # Last sentence


class ContentType(Enum):
    # Content type
    TEXT = "TEXT"  # Text content
    FILE = "FILE"  # File content
    ACTION = "ACTION"  # Action content


class InterfaceType(Enum):
    # Interface type
    DUAL_STREAM = "DUAL_STREAM"  # Dual streaming
    SINGLE_STREAM = "SINGLE_STREAM"  # Single streaming
    NON_STREAM = "NON_STREAM"  # Non-streaming


class TTSMessageDTO:
    def __init__(
        self,
        sentence_id: str,
        # Speaking stage
        sentence_type: SentenceType,
        # Content type
        content_type: ContentType,
        # Content details, usually text to be converted or lyrics of audio
        content_detail: Optional[str] = None,
        # If content type is file, need to pass file path
        content_file: Optional[str] = None,
    ):
        self.sentence_id = sentence_id
        self.sentence_type = sentence_type
        self.content_type = content_type
        self.content_detail = content_detail
        self.content_file = content_file