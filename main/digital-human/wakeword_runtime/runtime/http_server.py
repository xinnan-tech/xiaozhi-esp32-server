import base64
import hashlib
import json
import queue
import socket
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from ..bridge import WakewordEventBridge
from ..config.config_loader import load_config


class TestRuntimeHttpServer:
    def __init__(self, test_root: Path, host: str = "0.0.0.0", port: int = 8006) -> None:
        self.test_root = test_root
        self.host = host
        self.port = port
        self.event_bridge = WakewordEventBridge()
        self._restart_handler: Callable[[], None] | None = None
        self._restart_lock = threading.Lock()
        self._server = self._build_server()

    @property
    def page_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/index.html"

    @property
    def bridge_url(self) -> str:
        return f"ws://127.0.0.1:{self.port}/wakeword-ws"

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self.event_bridge.close()
        self._server.server_close()

    def set_restart_handler(self, handler: Callable[[], None]) -> None:
        self._restart_handler = handler

    def request_runtime_restart(self) -> None:
        with self._restart_lock:
            handler = self._restart_handler

        if handler is None:
            raise RuntimeError("restart handler is not configured")

        threading.Thread(
            target=self._run_restart_handler,
            name="test-runtime-restart",
            daemon=True,
        ).start()

    def _run_restart_handler(self) -> None:
        handler = self._restart_handler
        if handler is None:
            return
        handler()

    def _build_server(self) -> ThreadingHTTPServer:
        test_root = self.test_root
        event_bridge = self.event_bridge
        schedule_restart = self.request_runtime_restart

        class TestRuntimeHandler(SimpleHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(test_root), **kwargs)

            def handle(self) -> None:
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            def do_GET(self) -> None:
                if self.path == "/wakeword-ws":
                    self._handle_websocket(event_bridge)
                    return

                if self.path == "/health":
                    body = json.dumps({"status": "ok"}).encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                super().do_GET()

            def log_message(self, format: str, *args) -> None:
                return

            def _handle_websocket(self, bridge: WakewordEventBridge) -> None:
                if self.headers.get("Upgrade", "").lower() != "websocket":
                    self.send_error(HTTPStatus.BAD_REQUEST, "expected websocket upgrade")
                    return

                websocket_key = self.headers.get("Sec-WebSocket-Key")
                if not websocket_key:
                    self.send_error(HTTPStatus.BAD_REQUEST, "missing Sec-WebSocket-Key")
                    return

                accept_source = websocket_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                accept_value = base64.b64encode(
                    hashlib.sha1(accept_source.encode("utf-8")).digest()
                ).decode("ascii")

                client_queue = bridge.add_client()
                self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
                self.send_header("Upgrade", "websocket")
                self.send_header("Connection", "Upgrade")
                self.send_header("Sec-WebSocket-Accept", accept_value)
                self.end_headers()

                try:
                    self.connection.settimeout(0.2)
                    self._send_websocket_text(bridge.build_ready_message())
                    self._send_websocket_text(self._build_wakeword_config_message(bridge))

                    while bridge.is_running:
                        inbound_message = self._receive_websocket_message()
                        if inbound_message is not None:
                            response_message = self._handle_bridge_request(bridge, inbound_message)
                            if response_message:
                                self._send_websocket_text(response_message)

                        try:
                            message = client_queue.get(timeout=0.2)
                            if message == "__bridge_closed__":
                                break
                            self._send_websocket_text(message)
                        except queue.Empty:
                            if not bridge.is_running:
                                break
                            continue
                except socket.timeout:
                    pass
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                finally:
                    bridge.remove_client(client_queue)

            def _build_wakeword_config_message(self, bridge: WakewordEventBridge) -> str:
                try:
                    runtime_root = test_root / "wakeword_runtime"
                    config = load_config(runtime_root)
                    payload = {
                        "enabled": config.wakeword_enabled,
                        "wakeWords": config.wake_words,
                    }
                    return bridge.build_message("wakeword_config", payload)
                except Exception as exc:
                    return bridge.build_message(
                        "wakeword_config",
                        {},
                        success=False,
                        error=f"读取唤醒词配置失败: {exc}",
                    )

            def _handle_bridge_request(self, bridge: WakewordEventBridge, raw_message: str) -> str | None:
                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    return None

                message_type = str(message.get("type", "")).strip()
                request_id = message.get("requestId")
                payload = message.get("payload") or {}
                result_type = f"{message_type}_result" if message_type else "bridge_request_result"

                if message_type == "set_wakeword_config":
                    try:
                        result_payload = self._save_wakeword_config(payload)
                        bridge.publish("wakeword_config", result_payload)
                        return bridge.build_message(
                            "set_wakeword_config_result",
                            result_payload,
                            request_id=request_id,
                        )
                    except Exception as exc:
                        return bridge.build_message(
                            "set_wakeword_config_result",
                            {},
                            request_id=request_id,
                            success=False,
                            error=f"保存唤醒词配置失败: {exc}",
                        )

                if message_type == "restart_wakeword_service":
                    schedule_restart()
                    return bridge.build_message(
                        "restart_wakeword_service_result",
                        {"restarting": True},
                        request_id=request_id,
                    )

                return bridge.build_message(
                    result_type,
                    {},
                    request_id=request_id,
                    success=False,
                    error=f"unsupported message type: {message_type}",
                )

            def _save_wakeword_config(self, payload: dict) -> dict:
                runtime_root = test_root / "wakeword_runtime"
                config_path = runtime_root / "config.json"
                model_root = runtime_root / "models"
                keywords_path = model_root / "keywords.txt"

                enabled = bool(payload.get("enabled", True))
                wake_words = payload.get("wakeWords") or []
                normalized_wake_words = []
                for item in wake_words:
                    if not isinstance(item, str):
                        continue
                    text = item.strip()
                    if text and text not in normalized_wake_words:
                        normalized_wake_words.append(text)

                if enabled and not normalized_wake_words:
                    raise ValueError("wakeWords cannot be empty when wakeword is enabled")

                raw_config = json.loads(config_path.read_text(encoding="utf-8"))
                raw_config.setdefault("wakeword", {})["enabled"] = enabled
                config_path.write_text(
                    json.dumps(raw_config, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

                keywords_lines = [self._build_keyword_line(item) for item in normalized_wake_words]
                keywords_path.write_text(
                    ("\n".join(keywords_lines) + "\n") if keywords_lines else "",
                    encoding="utf-8",
                )

                return {
                    "enabled": enabled,
                    "wakeWords": normalized_wake_words,
                }

            def _build_keyword_line(self, keyword_text: str) -> str:
                from pypinyin import Style, pinyin

                initials = pinyin(keyword_text, style=Style.INITIALS, strict=False)
                finals = pinyin(
                    keyword_text,
                    style=Style.FINALS_TONE,
                    strict=False,
                    neutral_tone_with_five=True,
                )

                tokens: list[str] = []
                for initial_parts, final_parts in zip(initials, finals):
                    initial = initial_parts[0].strip()
                    final = final_parts[0].strip()
                    if initial:
                        tokens.append(initial)
                    if final:
                        tokens.append(final)

                if not tokens:
                    raise ValueError(f"failed to generate pinyin tokens for wake word: {keyword_text}")

                return f"{' '.join(tokens)} @{keyword_text}"

            def _receive_websocket_message(self) -> str | None:
                try:
                    header = self._read_exact(2)
                except socket.timeout:
                    return None

                if not header:
                    return None

                first_byte, second_byte = header[0], header[1]
                opcode = first_byte & 0x0F
                masked = (second_byte & 0x80) != 0
                payload_length = second_byte & 0x7F

                if payload_length == 126:
                    payload_length = int.from_bytes(self._read_exact(2), "big")
                elif payload_length == 127:
                    payload_length = int.from_bytes(self._read_exact(8), "big")

                masking_key = self._read_exact(4) if masked else b""
                payload = self._read_exact(payload_length) if payload_length else b""

                if masked and payload:
                    payload = bytes(
                        byte ^ masking_key[index % 4]
                        for index, byte in enumerate(payload)
                    )

                if opcode == 0x8:
                    raise ConnectionAbortedError("websocket closed by client")

                if opcode == 0x9:
                    self._send_websocket_frame(0xA, payload)
                    return None

                if opcode == 0xA:
                    return None

                if opcode != 0x1:
                    return None

                return payload.decode("utf-8")

            def _read_exact(self, size: int) -> bytes:
                if size <= 0:
                    return b""

                chunks = bytearray()
                while len(chunks) < size:
                    chunk = self.connection.recv(size - len(chunks))
                    if not chunk:
                        raise ConnectionResetError("websocket connection closed")
                    chunks.extend(chunk)
                return bytes(chunks)

            def _send_websocket_text(self, message: str) -> None:
                self._send_websocket_frame(0x1, message.encode("utf-8"))

            def _send_websocket_frame(self, opcode: int, payload: bytes) -> None:
                header = bytearray()
                header.append(0x80 | opcode)

                payload_length = len(payload)
                if payload_length < 126:
                    header.append(payload_length)
                elif payload_length < 65536:
                    header.append(126)
                    header.extend(payload_length.to_bytes(2, "big"))
                else:
                    header.append(127)
                    header.extend(payload_length.to_bytes(8, "big"))

                self.wfile.write(bytes(header) + payload)
                self.wfile.flush()

        server = ThreadingHTTPServer((self.host, self.port), TestRuntimeHandler)
        server.daemon_threads = True
        return server
