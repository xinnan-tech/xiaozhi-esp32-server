"""Public result types for child dialogue."""

from dataclasses import dataclass
from enum import Enum


class ReplyStatus(str, Enum):
    OK = "ok"
    EMPTY_INPUT = "empty_input"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"


@dataclass(frozen=True)
class DialogueReply:
    session_id: str
    text: str
    status: ReplyStatus
