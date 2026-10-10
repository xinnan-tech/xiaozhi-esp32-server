"""Build the message format accepted by existing LLM providers."""

from pathlib import Path
from typing import Mapping, Sequence

_PROMPT_FILE = Path(__file__).parent / "prompts" / "base_system.md"


def load_system_prompt() -> str:
    return _PROMPT_FILE.read_text(encoding="utf-8").strip()


def build_dialogue(
    user_text: str, history: Sequence[Mapping[str, str]], system_prompt: str
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in history)
    messages.append({"role": "user", "content": user_text})
    return messages
