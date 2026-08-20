import json
import threading
import time
import uuid
from collections import OrderedDict

import requests

from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase


TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    """Bridge XiaoZhi text turns to the ZGC External Agent API."""

    FINAL_STATES = {"completed", "failed", "canceled"}

    def __init__(self, config):
        self.base_url = config.get(
            "base_url", "https://agents.zgci.org/api/v1/public"
        ).rstrip("/")
        self.api_key = config.get("api_key", "").strip()
        if not self.api_key:
            raise ValueError("ZGC Agent API key is required")

        self.connect_timeout = float(config.get("connect_timeout", 5))
        self.read_timeout = float(config.get("read_timeout", 180))
        self.poll_interval = float(config.get("poll_interval", 0.5))
        self.max_sessions = int(config.get("max_sessions", 512))
        self.session_title = config.get("session_title", "XiaoZhi SparkBot")

        self._sessions = OrderedDict()
        self._sessions_lock = threading.Lock()

    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request(self, method, path, **kwargs):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        timeout = kwargs.pop(
            "timeout", (self.connect_timeout, self.read_timeout)
        )
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            timeout=timeout,
            **kwargs,
        )
        if response.ok:
            return response

        try:
            payload = response.json()
            error = payload.get("error", {})
            code = error.get("code", "http_error")
            message = error.get("message", response.text)
        except (ValueError, AttributeError):
            code = "http_error"
            message = response.text
        raise ZgcApiError(response.status_code, code, message)

    def _create_remote_session(self, local_session_id):
        suffix = local_session_id[-12:] if local_session_id else "background"
        response = self._request(
            "POST",
            "/sessions",
            json={"title": f"{self.session_title} {suffix}"},
        )
        return {"session_id": response.json()["session_id"], "cursor": 0}

    def _get_session(self, local_session_id, force_new=False):
        if not local_session_id:
            return self._create_remote_session("")

        with self._sessions_lock:
            if not force_new and local_session_id in self._sessions:
                session = self._sessions.pop(local_session_id)
                self._sessions[local_session_id] = session
                return session

        session = self._create_remote_session(local_session_id)
        with self._sessions_lock:
            self._sessions[local_session_id] = session
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)
        return session

    def _set_cursor(self, local_session_id, session, cursor):
        session["cursor"] = max(int(session.get("cursor", 0)), int(cursor or 0))
        if not local_session_id:
            return
        with self._sessions_lock:
            if self._sessions.get(local_session_id) is session:
                self._sessions.move_to_end(local_session_id)

    @staticmethod
    def _last_user_text(dialogue):
        for message in reversed(dialogue):
            if message.get("role") != "user":
                continue
            content = message.get("content", "")
            if isinstance(content, str):
                if content.strip():
                    return content
                continue
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                text = "\n".join(part for part in parts if part.strip())
                if text:
                    return text
        raise ValueError("No user message found in dialogue")

    def _submit_turn(self, remote_session_id, text):
        response = self._request(
            "POST",
            f"/sessions/{remote_session_id}/messages",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={"text": text},
        )
        return response.json()["turn_id"]

    @staticmethod
    def _iter_sse(response):
        event_name = None
        event_id = None
        data_lines = []

        for raw_line in response.iter_lines(decode_unicode=True):
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if line == "":
                if data_lines:
                    yield event_name, event_id, "\n".join(data_lines)
                event_name = None
                event_id = None
                data_lines = []
                continue
            if not line or line.startswith(":"):
                continue
            field, separator, value = line.partition(":")
            if not separator:
                continue
            value = value[1:] if value.startswith(" ") else value
            if field == "event":
                event_name = value
            elif field == "id":
                event_id = value
            elif field == "data":
                data_lines.append(value)

        if data_lines:
            yield event_name, event_id, "\n".join(data_lines)

    def _stream_turn(self, local_session_id, session, turn_id):
        start_cursor = int(session.get("cursor", 0))
        response = self._request(
            "GET",
            f"/sessions/{session['session_id']}/stream",
            headers={"Last-Event-ID": str(start_cursor)},
            stream=True,
            timeout=(self.connect_timeout, self.read_timeout),
        )

        emitted = ""
        final_state = None
        stored_messages = []
        max_cursor = start_cursor

        try:
            for event_name, event_id, raw_data in self._iter_sse(response):
                if event_id:
                    try:
                        max_cursor = max(max_cursor, int(event_id))
                    except ValueError:
                        pass
                try:
                    envelope = json.loads(raw_data)
                except json.JSONDecodeError:
                    logger.bind(tag=TAG).warning("Ignored malformed ZGC SSE frame")
                    continue

                frame_turn_id = envelope.get("turn_id")
                frame_type = envelope.get("type") or event_name
                frame_data = envelope.get("data") or {}

                if frame_turn_id == turn_id and frame_type == "delta":
                    text = frame_data.get("text", "")
                    if text:
                        emitted += text
                        yield text
                elif frame_turn_id == turn_id and frame_type == "message":
                    text = frame_data.get("text", "")
                    if text:
                        stored_messages.append(text)
                elif frame_turn_id == turn_id and frame_type == "turn_state":
                    state = frame_data.get("state") or envelope.get("state")
                    if state in self.FINAL_STATES:
                        final_state = state
        finally:
            response.close()
            self._set_cursor(local_session_id, session, max_cursor)

        final_state = final_state or self._wait_for_turn(session["session_id"], turn_id)
        if final_state != "completed":
            raise RuntimeError(f"ZGC Agent turn ended with state: {final_state}")

        final_text, next_cursor = self._fetch_final_message(
            session["session_id"], turn_id, start_cursor
        )
        self._set_cursor(local_session_id, session, next_cursor)
        if not final_text and stored_messages:
            final_text = stored_messages[-1]

        if final_text.startswith(emitted):
            remainder = final_text[len(emitted) :]
            if remainder:
                yield remainder
        elif not emitted and final_text:
            yield final_text
        elif final_text and final_text != emitted:
            logger.bind(tag=TAG).warning(
                "ZGC stored message did not match the emitted delta prefix"
            )

    def _wait_for_turn(self, remote_session_id, turn_id):
        deadline = time.monotonic() + self.read_timeout
        while time.monotonic() < deadline:
            response = self._request(
                "GET", f"/sessions/{remote_session_id}/turns/{turn_id}"
            )
            state = response.json().get("state")
            if state in self.FINAL_STATES:
                return state
            time.sleep(self.poll_interval)
        raise TimeoutError("Timed out waiting for ZGC Agent turn")

    def _fetch_final_message(self, remote_session_id, turn_id, after_id):
        messages = []
        cursor = int(after_id)

        while True:
            response = self._request(
                "GET",
                f"/sessions/{remote_session_id}/events",
                params={"after_id": cursor, "limit": 500},
            )
            payload = response.json()
            for event in payload.get("events", []):
                event_id = int(event.get("event_id") or 0)
                cursor = max(cursor, event_id)
                if (
                    event.get("turn_id") == turn_id
                    and event.get("role") == "agent"
                    and event.get("type") == "message"
                ):
                    text = (event.get("data") or {}).get("text", "")
                    if text:
                        messages.append(text)
            next_cursor = payload.get("next_after_id")
            if next_cursor is not None:
                cursor = max(cursor, int(next_cursor))
            if not payload.get("has_more"):
                break

        return (messages[-1] if messages else ""), cursor

    def _cancel_turn(self, remote_session_id, turn_id):
        try:
            self._request(
                "POST", f"/sessions/{remote_session_id}/turns/{turn_id}/cancel"
            )
        except Exception as error:
            logger.bind(tag=TAG).warning(f"Failed to cancel ZGC turn: {error}")

    def response(self, session_id, dialogue, **kwargs):
        text = self._last_user_text(dialogue)
        session = self._get_session(session_id)

        try:
            turn_id = self._submit_turn(session["session_id"], text)
        except ZgcApiError as error:
            if error.status_code != 404:
                raise
            session = self._get_session(session_id, force_new=True)
            turn_id = self._submit_turn(session["session_id"], text)

        completed = False
        try:
            yield from self._stream_turn(session_id, session, turn_id)
            completed = True
        finally:
            if not completed:
                self._cancel_turn(session["session_id"], turn_id)

class ZgcApiError(RuntimeError):
    def __init__(self, status_code, code, message):
        super().__init__(f"ZGC API error {status_code} {code}: {message}")
        self.status_code = status_code
        self.code = code
