import json
import os
import queue
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


def _ts() -> str:
    """ISO timestamp with timezone, milliseconds."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _send(proc: subprocess.Popen, obj: Dict) -> None:
    proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
    proc.stdin.flush()


def _is_server_request(msg: Dict) -> bool:
    return (
        "id" in msg
        and "method" in msg
        and "result" not in msg
        and "error" not in msg
    )


def _accept_server_request(proc: subprocess.Popen, msg: Dict, auto_approve: bool) -> None:
    decision = "accept" if auto_approve else "reject"
    _send(proc, {"id": msg["id"], "result": {"decision": decision}})


class _StdoutReader(threading.Thread):
    def __init__(self, proc: subprocess.Popen, out_queue: queue.Queue) -> None:
        super().__init__(daemon=True)
        self.proc = proc
        self.q = out_queue

    def run(self) -> None:
        while True:
            line = self.proc.stdout.readline()
            if not line:
                self.q.put({"__eof__": True})
                return
            line = line.strip()
            if not line:
                continue
            try:
                self.q.put(json.loads(line))
            except json.JSONDecodeError:
                self.q.put({"__non_json__": line})


def _read_one(q: queue.Queue, timeout: Optional[float] = None) -> Dict:
    while True:
        msg = q.get(timeout=timeout)
        if isinstance(msg, dict) and msg.get("__eof__"):
            raise RuntimeError("codex app-server exited (stdout closed)")
        if isinstance(msg, dict) and "__non_json__" in msg:
            logger.bind(tag=TAG).debug(f"codex non-json stdout: {msg['__non_json__']}")
            continue
        return msg


def _wait_result(
    proc: subprocess.Popen,
    q: queue.Queue,
    req_id: int,
    auto_approve: bool,
) -> Dict:
    while True:
        msg = _read_one(q, timeout=None)
        if _is_server_request(msg):
            _accept_server_request(proc, msg, auto_approve)
            continue
        if msg.get("id") == req_id and ("result" in msg or "error" in msg):
            if "error" in msg:
                raise RuntimeError(msg["error"])
            return msg["result"]


def _matches_thread_turn(msg: Dict, thread_id: str, turn_id: str) -> bool:
    method = msg.get("method")
    params = msg.get("params", {}) or {}

    if method == "turn/completed":
        return params.get("threadId") == thread_id and str(
            (params.get("turn") or {}).get("id")
        ) == str(turn_id)

    if "threadId" in params and params["threadId"] != thread_id:
        return False
    if "turnId" in params and str(params["turnId"]) != str(turn_id):
        return False
    if "threadId" not in params and "turnId" not in params:
        return False
    return True


def _split_dialogue(dialogue: List[Dict]) -> Tuple[List[Dict], str, List[Dict]]:
    last_user_index = None
    for idx in range(len(dialogue) - 1, -1, -1):
        if dialogue[idx].get("role") == "user":
            last_user_index = idx
            break
    if last_user_index is None:
        return dialogue, "", []
    history = dialogue[:last_user_index]
    last_user = dialogue[last_user_index].get("content") or ""
    tail = dialogue[last_user_index + 1 :]
    return history, last_user, tail


def _extract_system_prompt(dialogue: List[Dict]) -> str:
    for msg in dialogue:
        if msg.get("role") == "system":
            return msg.get("content") or ""
    return ""


def _build_transcript(history: List[Dict]) -> str:
    lines: List[str] = []
    for msg in history:
        role = (msg.get("role") or "").lower()
        if role == "system":
            continue
        if role == "user":
            prefix = "User"
        elif role == "assistant":
            prefix = "Assistant"
        elif role == "tool":
            prefix = "Tool"
        else:
            prefix = role or "Message"
        content = msg.get("content")
        if content is None and "tool_calls" in msg:
            content = json.dumps(msg["tool_calls"], ensure_ascii=False)
        if content:
            lines.append(f"{prefix}: {content}")
    return "\n".join(lines)


def _build_tool_context(messages: List[Dict]) -> str:
    lines: List[str] = []
    for msg in messages:
        role = (msg.get("role") or "").lower()
        if role == "tool":
            content = msg.get("content") or ""
            if content:
                lines.append(f"Tool result: {content}")
        elif role == "assistant" and msg.get("tool_calls"):
            payload = json.dumps(msg.get("tool_calls"), ensure_ascii=False)
            lines.append(f"Tool call: {payload}")
    return "\n".join(lines)


def _short(text: Optional[str], limit: int = 240) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n")
    return text if len(text) <= limit else text[:limit] + " ..."


def _format_action_desc(item: Dict) -> str:
    desc = item.get("type") or "item"
    if "command" in item:
        desc += f" cmd={_short(str(item['command']))}"
    if "path" in item:
        desc += f" path={_short(str(item['path']))}"
    if "tool" in item:
        desc += f" tool={_short(str(item['tool']))}"
    if "name" in item:
        desc += f" name={_short(str(item['name']))}"
    return desc


def _safe_filename(s: str) -> str:
    s = str(s or "session")
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return s[:120] if len(s) > 120 else s


class _CodexSession:
    def __init__(self, config: Dict, session_key: str) -> None:
        self.session_key = session_key
        self.codex_bin = config.get("codex_bin", "codex.cmd")
        self.model = config.get("model_name") or config.get("model") or "gpt-5.2"
        self.workspace = str(Path(config.get("workspace", os.getcwd())).resolve())
        self.auto_approve = bool(config.get("auto_approve", True))
        self.approval_policy = config.get("approval_policy")
        self.network_access = bool(config.get("network_access", True))
        self.thread_sandbox = config.get("sandbox", "workspace-write")
        self.sandbox_policy = config.get("sandbox_policy")
        self.effort = config.get("effort")
        self.summary = config.get("summary")
        self.system_prompt_mode = (config.get("system_prompt_mode") or "first_turn").lower()
        self.bootstrap_mode = (config.get("bootstrap_mode") or "none").lower()
        self.api_key = config.get("api_key")
        self.export_api_key = bool(config.get("export_api_key", False))
        self.env_overrides = config.get("env", {}) or {}
        self.runtime_config = config.get("runtime_config", {}) or {}
        self.emit_events = bool(config.get("emit_events", False))
        self.thinking_mode = (config.get("thinking_mode") or "off").lower()
        self.show_actions = bool(config.get("show_actions", False))
        self.thinking_debug = bool(config.get("thinking_debug", False))

        # ---- Stream logging toggles ----
        # log_stream: enables writing stream output to file + end-of-turn info log
        self.log_stream = bool(config.get("log_stream", True))
        # stream_debug: enables per-token debug logs (config-only gate)
        self.stream_debug = bool(config.get("stream_debug", False))
        # log_events: also write emitted event dicts (thinking/action) into SAME log file
        self.log_events = bool(config.get("log_events", True))
        # raw_stream_log: write raw app-server messages to a separate file
        self.raw_stream_log = bool(config.get("raw_stream_log", False))
        # event_max_chars: truncate long event JSON payloads (0 = no truncation)
        self.event_max_chars = int(config.get("event_max_chars", 8000))

        default_stream_log_path = str(
            Path(self.workspace) / f"/log/codex_stream_{_safe_filename(session_key)}.log"
        )
        self.stream_log_path = config.get("stream_log_path", default_stream_log_path)
        self._stream_flush_bytes = int(config.get("stream_flush_bytes", 4096))
        default_raw_log_path = str(
            Path(self.workspace) / f"/log/codex_stream_raw_{_safe_filename(session_key)}.log"
        )
        self.raw_stream_log_path = config.get("raw_stream_log_path", default_raw_log_path)
        self._raw_stream_flush_bytes = int(config.get("raw_stream_flush_bytes", 8192))

        self.proc: Optional[subprocess.Popen] = None
        self.q: Optional[queue.Queue] = None
        self.thread_id: Optional[str] = None
        self._req_id = 0
        self._last_system_prompt: Optional[str] = None
        self._system_prompt_sent = False
        self._bootstrap_history = True
        self._active_turn_id: Optional[str] = None
        self._lock = threading.Lock()

    def _next_id(self) -> int:
        rid = self._req_id
        self._req_id += 1
        return rid

    def _append_stream_log(self, text: str) -> None:
        """Append to per-session stream log file (best-effort)."""
        if not self.log_stream or not self.stream_log_path or not text:
            return
        try:
            Path(self.stream_log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.stream_log_path, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception as exc:
            logger.bind(tag=TAG).warning(f"codex stream log write failed: {exc}")

    def _append_raw_log(self, text: str) -> None:
        """Append to per-session raw log file (best-effort)."""
        if not self.raw_stream_log or not self.raw_stream_log_path or not text:
            return
        try:
            Path(self.raw_stream_log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.raw_stream_log_path, "a", encoding="utf-8") as f:
                f.write(text)
        except Exception as exc:
            logger.bind(tag=TAG).warning(f"codex raw log write failed: {exc}")

    def _pump_stderr(self) -> None:
        if not self.proc or not self.proc.stderr:
            return
        for line in self.proc.stderr:
            logger.bind(tag=TAG).warning(f"codex stderr: {line.rstrip()}")

    def _write_config(self, key: str, value) -> None:
        _send(
            self.proc,
            {
                "method": "config/value/write",
                "id": self._next_id(),
                "params": {"keyPath": key, "mergeStrategy": "replace", "value": value},
            },
        )
        _wait_result(self.proc, self.q, self._req_id - 1, self.auto_approve)

    def _start_process(self) -> None:
        env = os.environ.copy()
        if self.api_key and self.export_api_key and "OPENAI_API_KEY" not in env:
            env["OPENAI_API_KEY"] = self.api_key
        env.update(self.env_overrides)

        self.proc = subprocess.Popen(
            [self.codex_bin, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=self.workspace,
            env=env,
        )

        threading.Thread(target=self._pump_stderr, daemon=True).start()
        self.q = queue.Queue()
        _StdoutReader(self.proc, self.q).start()

        _send(
            self.proc,
            {
                "method": "initialize",
                "id": self._next_id(),
                "params": {
                    "clientInfo": {
                        "name": "xiaozhi_codex_provider",
                        "title": "Xiaozhi Codex Provider",
                        "version": "0.0.1",
                    }
                },
            },
        )
        _wait_result(self.proc, self.q, self._req_id - 1, self.auto_approve)
        _send(self.proc, {"method": "initialized", "params": {}})

        _send(
            self.proc,
            {"method": "account/read", "id": self._next_id(), "params": {"refreshToken": False}},
        )
        auth = _wait_result(self.proc, self.q, self._req_id - 1, self.auto_approve)
        if auth.get("requiresOpenaiAuth") and auth.get("account") is None:
            if not self.api_key:
                raise RuntimeError("Codex app-server requires auth; set api_key in config.")
            _send(
                self.proc,
                {
                    "method": "account/login/start",
                    "id": self._next_id(),
                    "params": {"type": "apiKey", "apiKey": self.api_key},
                },
            )
            _wait_result(self.proc, self.q, self._req_id - 1, self.auto_approve)

        for key, value in self.runtime_config.items():
            try:
                self._write_config(key, value)
            except Exception as exc:
                logger.bind(tag=TAG).warning(f"codex config write failed: {key} ({exc})")

        if self.emit_events and self.thinking_mode != "off" and "hide_agent_reasoning" not in self.runtime_config:
            try:
                self._write_config("hide_agent_reasoning", False)
            except Exception as exc:
                logger.bind(tag=TAG).warning(
                    f"codex config write failed: hide_agent_reasoning ({exc})"
                )

        thread_params = {"model": self.model, "cwd": self.workspace, "sandbox": self.thread_sandbox}
        if self.approval_policy:
            thread_params["approvalPolicy"] = self.approval_policy
        _send(self.proc, {"method": "thread/start", "id": self._next_id(), "params": thread_params})
        thread_result = _wait_result(self.proc, self.q, self._req_id - 1, self.auto_approve)
        self.thread_id = str(thread_result["thread"]["id"])

        self._system_prompt_sent = False
        self._bootstrap_history = True

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        self._start_process()

    def close(self) -> None:
        if not self.proc:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None
        self.q = None
        self.thread_id = None

    def _restart(self) -> None:
        self.close()
        self.start()

    def _compose_prompt(self, dialogue: List[Dict]) -> str:
        history, last_user, tail = _split_dialogue(dialogue)
        tool_context = _build_tool_context(tail)
        if tool_context:
            if last_user:
                last_user = f"{last_user}\n\nTool results:\n{tool_context}"
            else:
                last_user = f"Tool results:\n{tool_context}"
        if not last_user:
            return ""

        system_prompt = _extract_system_prompt(history)
        if self._last_system_prompt is not None and system_prompt != self._last_system_prompt:
            self._restart()
        self._last_system_prompt = system_prompt

        include_system = (
            system_prompt
            and self.system_prompt_mode in ("always", "first_turn")
            and (self.system_prompt_mode == "always" or not self._system_prompt_sent)
        )

        if self._bootstrap_history and self.bootstrap_mode != "none":
            transcript = _build_transcript(history)
            parts: List[str] = []
            if include_system:
                parts.append(system_prompt)
            if transcript:
                parts.append("Conversation so far:\n" + transcript)
            parts.append(last_user)
            prompt = "\n\n".join(parts)
            if include_system:
                self._system_prompt_sent = True
            self._bootstrap_history = False
            return prompt

        if include_system:
            self._system_prompt_sent = True
            return f"{system_prompt}\n\n{last_user}"

        return last_user

    def _stream_turn(self, prompt_text: str, emit_events: bool, **kwargs):
        self.start()

        turn_params = {
            "threadId": self.thread_id,
            "input": [{"type": "text", "text": prompt_text}],
            "model": self.model,
            "cwd": self.workspace,
        }

        effort = kwargs.get("effort", self.effort)
        summary = kwargs.get("summary", self.summary)
        if effort:
            turn_params["effort"] = effort
        if summary:
            turn_params["summary"] = summary

        if self.sandbox_policy:
            turn_params["sandboxPolicy"] = self.sandbox_policy
        else:
            turn_params["sandboxPolicy"] = {
                "type": "workspaceWrite",
                "writableRoots": [self.workspace],
                "networkAccess": self.network_access,
            }

        _send(self.proc, {"method": "turn/start", "id": self._next_id(), "params": turn_params})
        result = _wait_result(self.proc, self.q, self._req_id - 1, self.auto_approve)
        turn_id = str(result["turn"]["id"])
        self._active_turn_id = turn_id

        # Turn logger
        tlog = logger.bind(
            tag=TAG,
            session_key=self.session_key,
            thread_id=self.thread_id,
            turn_id=turn_id,
        )

        # ---- file buffering (assistant text + event lines) ----
        file_buf = ""
        raw_buf = ""

        def file_append(s: str) -> None:
            nonlocal file_buf
            if not self.log_stream or not s:
                return
            file_buf += s
            if len(file_buf.encode("utf-8", errors="ignore")) >= self._stream_flush_bytes:
                self._append_stream_log(file_buf)
                file_buf = ""

        def file_flush() -> None:
            nonlocal file_buf
            if file_buf:
                self._append_stream_log(file_buf)
                file_buf = ""

        def raw_append(s: str) -> None:
            nonlocal raw_buf
            if not self.raw_stream_log or not s:
                return
            raw_buf += s
            if len(raw_buf.encode("utf-8", errors="ignore")) >= self._raw_stream_flush_bytes:
                self._append_raw_log(raw_buf)
                raw_buf = ""

        def raw_flush() -> None:
            nonlocal raw_buf
            if raw_buf:
                self._append_raw_log(raw_buf)
                raw_buf = ""

        def file_event(event_obj: Dict) -> None:
            """
            Write an event line into the SAME log file, with timestamp.
            We log the *emitted* event dicts (thinking/action), not every raw app-server message.
            """
            if not (self.log_stream and self.log_events):
                return

            try:
                payload = json.dumps(event_obj, ensure_ascii=False)
            except Exception:
                payload = str(event_obj)

            if self.event_max_chars and len(payload) > self.event_max_chars:
                payload = payload[: self.event_max_chars] + " ..."

            # Ensure event starts on a new line and ends with newline.
            file_append(f"\n[{_ts()}] [EVENT] {payload}\n")

        def file_thinking_debug(method: str, delta: str) -> None:
            if not (self.log_stream and self.thinking_debug):
                return
            safe_delta = delta.replace("\r", "\\r").replace("\n", "\\n")
            file_append(f"\n[{_ts()}] [THINKING_DEBUG] {method}: {safe_delta}\n")

        # Log turn start
        if self.log_stream:
            file_append(f"[{_ts()}] [TURN_START] session={self.session_key} thread={self.thread_id} turn={turn_id}\n")

        saw_tokens = False
        final_text = None
        thinking_buffer = ""
        out_buffer = ""

        try:
            while True:
                msg = _read_one(self.q, timeout=None)
                if self.raw_stream_log:
                    try:
                        raw_payload = json.dumps(msg, ensure_ascii=False)
                    except Exception:
                        raw_payload = str(msg)
                    raw_append(f"[{_ts()}] raw_{raw_payload}\n")
                if _is_server_request(msg):
                    _accept_server_request(self.proc, msg, self.auto_approve)
                    continue

                if not _matches_thread_turn(msg, self.thread_id, turn_id):
                    continue

                method = msg.get("method")
                params = msg.get("params", {}) or {}
                
                # --- assistant text stream ---
                if method == "item/agentMessage/delta":
                    delta = params.get("delta", "")
                    if delta:
                        saw_tokens = True
                        out_buffer += delta

                        # write assistant text as-is to the log file (streaming)
                        if self.log_stream:
                            file_append(delta)

                        # per-token debug (config-only gate)
                        if self.log_stream and self.stream_debug:
                            tlog.debug("codex_stream_delta", delta=_short(delta, 400))

                        yield delta

                # --- emitted events (thinking/action) ---
                if emit_events and self.thinking_mode != "off":
                    if self.thinking_mode == "summary" and method == "item/reasoning/summaryTextDelta":
                        delta = params.get("delta", "")
                        if delta:
                            thinking_buffer += delta
                            evt = {"kind": "thinking", "mode": "summary", "delta": delta, "turn_id": turn_id}
                            file_event(evt)
                            file_thinking_debug(method, delta)
                            if self.log_stream and self.stream_debug:
                                tlog.debug("codex_thinking_summary_delta", delta=_short(delta, 400))
                            yield {"kind": "thinking", "text": thinking_buffer}

                    if self.thinking_mode == "raw" and method == "item/reasoning/textDelta":
                        delta = params.get("delta", "")
                        if delta:
                            thinking_buffer += delta
                            evt = {"kind": "thinking", "mode": "raw", "delta": delta, "turn_id": turn_id}
                            file_event(evt)
                            file_thinking_debug(method, delta)
                            if self.log_stream and self.stream_debug:
                                tlog.debug("codex_thinking_raw_delta", delta=_short(delta, 400))
                            yield {"kind": "thinking", "text": thinking_buffer}
                else:
                    if method in ("item/reasoning/summaryTextDelta", "item/reasoning/textDelta"):
                        delta = params.get("delta", "")
                        if delta:
                            file_thinking_debug(method, delta)

                if emit_events and self.show_actions and method in ("item/started", "item/completed"):
                    item = params.get("item", {}) or {}
                    item_type = item.get("type")
                    if item_type not in ("userMessage", "reasoning", "agentMessage"):
                        phase = "start" if method == "item/started" else "done"
                        desc = _format_action_desc(item)
                        evt = {"kind": "action", "phase": phase, "text": desc, "turn_id": turn_id}
                        file_event(evt)

                        if self.log_stream:
                            tlog.info("codex_action", phase=phase, action=desc)

                        yield {"kind": "action", "text": desc, "phase": phase}

                # --- final text fallback ---
                if method == "item/completed":
                    item = params.get("item", {}) or {}
                    if item.get("type") == "agentMessage":
                        final_text = item.get("text") or item.get("content") or ""

                if method == "turn/completed":
                    break

            # fallback if the server didn't stream deltas but gave final text
            if not saw_tokens and final_text:
                out_buffer += final_text
                if self.log_stream:
                    file_append(final_text)
                yield final_text

        finally:
            self._active_turn_id = None

            # Log turn end
            if self.log_stream:
                file_append(f"\n[{_ts()}] [TURN_END] chars={len(out_buffer)}\n\n--- turn_end ---\n\n")

            file_flush()
            raw_flush()

            if self.log_stream:
                tlog.info(
                    "codex_stream_turn_completed",
                    chars=len(out_buffer),
                    preview=_short(out_buffer, 2000),
                    stream_log_path=self.stream_log_path,
                )

    def stream_response(self, dialogue: List[Dict], **kwargs):
        with self._lock:
            prompt_text = self._compose_prompt(dialogue)
            if not prompt_text:
                return
            emit_events = kwargs.pop("emit_events", self.emit_events)
            for token in self._stream_turn(prompt_text, emit_events=emit_events, **kwargs):
                if isinstance(token, dict) and not emit_events:
                    continue
                yield token


class LLMProvider(LLMProviderBase):
    def __init__(self, config: Dict):
        self.config = config
        self._sessions: Dict[str, _CodexSession] = {}
        self._reuse_utility_session = bool(config.get("reuse_utility_session", False))
        self._utility_session_key = "__utility__"

    def _get_session(self, session_id: str) -> _CodexSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = _CodexSession(self.config, session_id)
        return self._sessions[session_id]

    def response(self, session_id, dialogue, **kwargs):
        try:
            if not session_id:
                if self._reuse_utility_session:
                    session = self._get_session(self._utility_session_key)
                    for token in session.stream_response(dialogue, **kwargs):
                        yield token
                else:
                    temp_session = _CodexSession(self.config, "utility")
                    try:
                        for token in temp_session.stream_response(dialogue, **kwargs):
                            yield token
                    finally:
                        temp_session.close()
                return

            session = self._get_session(session_id)
            for token in session.stream_response(dialogue, **kwargs):
                yield token
        except Exception as exc:
            if session_id:
                session = self._sessions.get(session_id)
                if session:
                    session.close()
            elif self._reuse_utility_session:
                session = self._sessions.get(self._utility_session_key)
                if session:
                    session.close()
            logger.bind(tag=TAG).error(f"Codex response error: {exc}")
            yield "[Codex response error]"

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        for token in self.response(session_id, dialogue, **kwargs):
            if isinstance(token, dict):
                yield token
            else:
                yield token, None
