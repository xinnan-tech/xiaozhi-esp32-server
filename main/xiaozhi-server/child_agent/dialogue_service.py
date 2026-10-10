"""Bounded session history around the server's existing streaming LLM adapter."""

import logging
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any

from .prompt_builder import build_dialogue, load_system_prompt
from .schemas import DialogueReply, ReplyStatus

logger = logging.getLogger(__name__)


class DialogueService:
    def __init__(
        self, llm: Any, *, max_turns: int = 4, timeout_seconds: float = 10,
        max_sessions: int = 128, system_prompt: str | None = None,
    ) -> None:
        if max_turns < 1 or max_sessions < 1 or timeout_seconds <= 0:
            raise ValueError("max_turns, max_sessions and timeout_seconds must be positive")
        self._llm = llm
        self.max_turns = max_turns
        self.timeout_seconds = timeout_seconds
        self.max_sessions = max_sessions
        self.system_prompt = system_prompt or load_system_prompt()
        self._history: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._lock = threading.RLock()
        # Timed-out synchronous provider calls cannot be forcibly stopped.
        # Bound the number of calls that can remain in the background.
        self._slots = threading.BoundedSemaphore(4)

    @classmethod
    def from_config(cls, config: dict, **kwargs: Any) -> "DialogueService":
        """Select an existing provider using the server's normal LLM factory."""
        from core.utils.llm import create_instance

        name = config["selected_module"]["LLM"]
        provider_config = dict(config["LLM"][name])
        if provider_config["type"] == "openai":
            provider_config.setdefault("timeout", kwargs.get("timeout_seconds", 10))
        return cls(create_instance(provider_config["type"], provider_config), **kwargs)

    def chat(self, session_id: str, user_text: str) -> DialogueReply:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(user_text, str) or not user_text.strip():
            return DialogueReply(session_id, "我没听清楚，可以再说一次吗？", ReplyStatus.EMPTY_INPUT)

        user_text = user_text.strip()
        with self._lock:
            history = list(self._history.get(session_id, []))
        messages = build_dialogue(user_text, history, self.system_prompt)

        if not self._slots.acquire(blocking=False):
            return DialogueReply(session_id, "我现在有点忙，请稍后再试。", ReplyStatus.API_ERROR)

        # Existing adapters are synchronous generators. A worker enforces the
        # caller's deadline; the provider's own network timeout should also be set.
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._collect, session_id, messages)
        except Exception:
            self._slots.release()
            executor.shutdown(wait=False)
            raise
        future.add_done_callback(lambda _future: self._slots.release())
        try:
            answer = future.result(timeout=self.timeout_seconds)
        except FutureTimeout:
            logger.warning("Child dialogue timed out for session %s", session_id)
            return DialogueReply(session_id, "我想一想，请稍后再试一次。", ReplyStatus.TIMEOUT)
        except Exception:
            logger.exception("Child dialogue provider failed for session %s", session_id)
            return DialogueReply(session_id, "现在没法回答，我们稍后再试。", ReplyStatus.API_ERROR)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        if not answer:
            return DialogueReply(session_id, "现在没法回答，我们稍后再试。", ReplyStatus.API_ERROR)

        with self._lock:
            turns = self._history.setdefault(session_id, [])
            turns.extend(({"role": "user", "content": user_text},
                          {"role": "assistant", "content": answer}))
            del turns[:-2 * self.max_turns]
            self._history.move_to_end(session_id)
            while len(self._history) > self.max_sessions:
                self._history.popitem(last=False)
        return DialogueReply(session_id, answer, ReplyStatus.OK)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._history.pop(session_id, None)

    def _collect(self, session_id: str, messages: list[dict[str, str]]) -> str:
        chunks = self._llm.response(session_id, messages)
        return "".join(part for part in chunks if isinstance(part, str)).strip()
