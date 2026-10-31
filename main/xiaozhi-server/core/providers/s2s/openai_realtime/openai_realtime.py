"""OpenAI Realtime 作为 S2S provider：WebSocket 直连平台（wss://api.openai.com/v1/realtime），平台 API key。

会话：握手时先建上游会话、等 session.created、发 session.update（指令 = 连接的系统提示词，工具 = func_handler 的清单）；
      原版把提示词增强、工具处理器建好后（after_components_ready）再同步一次。
上行：设备 16 kHz PCM → 残余回声门控（可关）→ 16 k → 24 k → input_audio_buffer.append；模型侧 server_vad 判轮次。
下行：response.output_audio.delta（24 kHz PCM）→ 60 ms Opus → 上游节拍器 → 设备；转写用 tts sentence_start / stt 消息给设备显示，
      并写进 conn.dialogue 供记忆使用。
打断：模型侧 speech_started、本地门控连续 N 帧判为人声、设备 abort 三条路都汇到 handleAbortMessage → cancel()：
      丢掉未发的帧、response.cancel（模型侧判的不用，它自己已取消）、conversation.item.truncate 截到设备实际播到的位置。
工具：response.output_item.done 里的 function_call → core/providers/s2s/tools.py → function_call_output → response.create。
结束：模型最后一次真的出声回答之后 idle_close_s 秒没有新回答就关连接（设备回待机）；上游中途断开也关连接，
      设备重连时若上游仍不可用，attach_s2s 会让它回退到原版级联。
日志只记事件、时长、字数，不记转写正文（log_text: true 才记）；api_key 不打印。
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import os
import time

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from core.handle.abortHandle import handleAbortMessage
from core.providers.s2s.audio import Resampler
from core.providers.s2s.base import DeviceSpeaker, S2SProviderBase
from core.providers.s2s.echo_gate import EchoGate, load_vad
from core.providers.s2s.tools import ToolRunner, to_realtime_tools

TAG = __name__

RT_RATE = 24000         # Realtime 的 audio/pcm 只有 24 kHz
DEVICE_RATE = 16000     # 设备上行
WAKE_TRIGGER = "嘿，你好呀"   # 上游 listenMessageHandler 把唤醒词统一换成这句再进 startToChat
RESPONSE_START_WAIT_S = 10.0  # 我们发了 response.create 之后，最多等这么久算"回答进行中"（空闲关闭不打断它）
SPEECH_GRACE_S = 3.0          # 刚说完这么久内不按空闲关闭：留给模型起回复
BENIGN_ERRORS = ("response_cancel_not_active", "conversation_already_has_active_response")


class S2SProvider(S2SProviderBase):
    def __init__(self, config: dict, conn):
        super().__init__(config, conn)
        c = self.config
        self.api_key = str(c.get("api_key") or "")
        self.url = str(c.get("url") or "wss://api.openai.com/v1/realtime")
        self.model = str(c.get("model_name") or "gpt-realtime")
        self.voice = str(c.get("voice") or "marin")
        self.transcribe_model = str(c.get("transcribe_model") or "gpt-4o-mini-transcribe")
        self.turn_detection_type = str(c.get("turn_detection") or "server_vad")
        self.vad_threshold = float(c.get("vad_threshold", 0.5))
        self.vad_silence_ms = int(c.get("vad_silence_ms", 400))
        self.vad_eagerness = str(c.get("vad_eagerness") or "auto")
        self.connect_timeout_s = float(c.get("connect_timeout_s", 4))
        self.idle_close_s = float(c.get("idle_close_s", 45))
        self.wake_greeting = c.get("wake_greeting", "用户刚叫醒你，只用两三个字回应，比如“我在”。")
        self.local_barge_frames = int(c.get("local_barge_frames", 3)) if c.get("local_barge", True) else 0
        self.log_text = bool(c.get("log_text", False))

        gate = None
        if c.get("echo_gate", True):
            gate = EchoGate(vad=load_vad(self._vad_model_path()),
                            lag_prior=float(c.get("gate_lag_prior_ms", 200)) / 1000,
                            lag_max=float(c.get("gate_lag_max_ms", 1200)) / 1000)
        self.gate = gate
        self.speaker = DeviceSpeaker(conn, getattr(conn, "sample_rate", RT_RATE), gate=gate)
        self.tools = ToolRunner(conn, conn.logger, per_minute=int(c.get("tool_calls_per_minute", 12)),
                                allow=c.get("tools_allow") or None)
        self.up_rs = Resampler(DEVICE_RATE, RT_RATE)

        self.ws = None
        self.rx_task = None
        self.closing = False
        self.resp_done = True
        self.suppress = False          # 被打断后丢掉本条回复剩下的音频，直到下一条 response.created
        self.item_id = None            # 当前助手消息（截断用）
        self.want_response = False     # 工具结果已交回、还没能发 response.create（当时有回复在进行）
        self.in_speech = False
        self.barge_run = 0
        self._pending_barge = None
        self._tool_tasks: set[asyncio.Task] = set()
        self._session_sig = None   # (指令全文, 工具名)：两者任一变了就重新 session.update
        self._idle_handle = None
        self.t_reply = time.monotonic()
        self.t_speech_stopped = None
        self.t_response_requested = None
        self.stats = {"turns": 0, "cancelled": 0, "speech_started": 0, "barge_server": 0, "barge_local": 0,
                      "barge_device": 0, "up_frames": 0, "tools": 0, "first_audio_ms": []}

    # ---------- 会话 ----------
    def _vad_model_path(self):
        try:
            selected = (self.conn.config.get("selected_module") or {}).get("VAD")
            model_dir = ((self.conn.config.get("VAD") or {}).get(selected) or {}).get("model_dir")
        except AttributeError:
            model_dir = None
        if not model_dir:
            return None
        return os.path.join(model_dir, "src", "silero_vad", "data", "silero_vad.onnx")

    def _turn_detection(self) -> dict:
        both = {"create_response": True, "interrupt_response": True}
        if self.turn_detection_type == "semantic_vad":
            return {"type": "semantic_vad", "eagerness": self.vad_eagerness, **both}
        return {"type": "server_vad", "threshold": self.vad_threshold, "prefix_padding_ms": 300,
                "silence_duration_ms": self.vad_silence_ms, **both}

    def _tool_list(self) -> list[dict]:
        fh = getattr(self.conn, "func_handler", None)
        funcs = []
        if fh is not None:
            try:
                funcs = fh.get_functions() or []
            except Exception:  # noqa: BLE001
                funcs = []
        return to_realtime_tools(funcs, self.tools.allow or None)

    def _instructions(self) -> str:
        # 建成那一刻 conn.prompt 往往还是 None（快速提示词在之后才设置）：先用配置里的原始 prompt，别让第一轮没有人设
        instructions = (getattr(self.conn, "prompt", None) or (self.conn.config.get("prompt") if isinstance(getattr(self.conn, "config", None), dict) else None)
                        or self.config.get("instructions") or "")
        return str(instructions)

    def _session(self) -> dict:
        tools = self._tool_list()
        instructions = self._instructions()
        self._session_sig = (instructions, tuple(sorted(t["name"] for t in tools)))
        return {
            "type": "realtime",
            "instructions": instructions,
            "tools": tools,
            "tool_choice": "auto",
            "output_modalities": ["audio"],
            "audio": {
                "input": {"format": {"type": "audio/pcm", "rate": RT_RATE},
                          "transcription": {"model": self.transcribe_model},
                          "turn_detection": self._turn_detection()},
                "output": {"format": {"type": "audio/pcm", "rate": RT_RATE}, "voice": self.voice},
            },
        }

    async def open(self) -> None:
        if not self.api_key or self.api_key.startswith("你的"):
            raise RuntimeError("api_key 未配置")

        async def _connect():
            ws = await connect(f"{self.url}?model={self.model}",
                               additional_headers={"Authorization": f"Bearer {self.api_key}"},
                               max_size=None, open_timeout=None, ping_interval=20, ping_timeout=20)
            try:
                ev = json.loads(await ws.recv())
                if ev.get("type") != "session.created":
                    code = (ev.get("error") or {}).get("code") if ev.get("type") == "error" else ""
                    raise RuntimeError(f"first event {ev.get('type')} {code or ''}".strip())
                await ws.send(json.dumps({"type": "session.update", "session": self._session()}, ensure_ascii=False))
                return ws
            except BaseException:
                self.spawn(ws.close())
                raise

        t0 = time.monotonic()
        self.ws = await asyncio.wait_for(_connect(), self.connect_timeout_s)
        self.rx_task = self.spawn(self._rx_loop())
        self._arm_idle()
        self.logger.bind(tag=TAG).info(
            f"Realtime 会话已建立 model={self.model} turn={self.turn_detection_type} "
            f"echo_gate={'on' if self.gate else 'off'} in {time.monotonic() - t0:.2f}s")

    def after_components_ready(self) -> None:
        asyncio.run_coroutine_threadsafe(self._after_ready(), self.conn.loop)

    async def _after_ready(self) -> None:
        await self._refresh_session()
        from core.utils.s2s import drain_pending_texts
        await drain_pending_texts(self.conn)  # provider 建成前到的文字（唤醒词 detect 等）现在补送

    async def _refresh_session(self) -> None:
        session = self._session()
        await self._send({"type": "session.update", "session": session})
        self.logger.bind(tag=TAG).info(f"会话配置已同步：指令 {len(session['instructions'])} 字、工具 {len(session['tools'])} 个")

    async def _maybe_refresh_tools(self) -> None:
        """提示词或工具清单变了就重新同步：上游的 Home Assistant 设备清单（append_devices_to_prompt）和 MCP 工具
        都是在我们第一次同步之后才异步挂上 conn.prompt / func_handler 的。"""
        tools = self._tool_list()
        sig = (self._instructions(), tuple(sorted(t["name"] for t in tools)))
        if sig != self._session_sig:
            await self._refresh_session()

    async def _send(self, obj: dict) -> None:
        if self.ws is None:
            return
        with contextlib.suppress(ConnectionClosed):
            await self.ws.send(json.dumps(obj, ensure_ascii=False))

    async def close(self) -> None:
        self.closing = True
        if self._idle_handle is not None:
            self._idle_handle.cancel()
        for t in list(self._tool_tasks):
            t.cancel()
        await super().close()
        if self.ws is not None:
            with contextlib.suppress(Exception):
                await self.ws.close()
        if self.gate is not None:
            self.stats["gate"] = dict(self.gate.stats, lag_ms=round(self.gate.lag * 1000))
        self.logger.bind(tag=TAG).info(f"Realtime 会话结束: {self.stats}")

    # ---------- 设备 → 模型 ----------
    async def on_pcm(self, pcm16k: bytes) -> None:
        if self.closing or not pcm16k:
            return
        if self.gate is not None:
            pcm16k, info = self.gate.process(pcm16k, time.monotonic(), self.speaker.speaking)
            if self.local_barge_frames:
                if self.speaker.speaking and info.startswith("pass"):
                    self.barge_run += 1
                    if self.barge_run == self.local_barge_frames:
                        await self._barge("local")
                else:
                    self.barge_run = 0
        # 设备 listen start 之前（唤醒词那几十帧）的音频不送模型：否则模型侧 VAD 把"你好小智"当一轮提问，唤醒后答两次。
        # 状态记在连接上（listenMessageHandler 维护）：provider 建成常晚于 listen start，自己记会错过它
        if not getattr(self.conn, "client_is_listening", False):
            return
        pcm24 = self.up_rs.process(pcm16k)
        await self._send({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm24).decode()})
        self.stats["up_frames"] += 1

    async def on_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        await self._maybe_refresh_tools()  # 插件 / MCP 可能刚注册完：第一轮就要看得到
        if text == WAKE_TRIGGER:
            if self.wake_greeting and self.resp_done and not self.speaker.speaking:
                await self._create_response({"instructions": self.wake_greeting})
            return
        await self.show_user_text(text)
        await self._send({"type": "conversation.item.create",
                          "item": {"type": "message", "role": "user",
                                   "content": [{"type": "input_text", "text": text}]}})
        await self._create_response()

    # ---------- 打断 ----------
    async def cancel(self, reason: str) -> None:
        """reason=device 时来自 handleAbortMessage（它已发 tts stop、置 client_abort）；
        模型侧 / 本地插话由 _barge 先调 handleAbortMessage，再经钩子到这里，真正的原因放在 _pending_barge。"""
        if reason == "device" and self._pending_barge:
            reason, self._pending_barge = self._pending_barge, None
        had_audio = self.speaker.speaking or self.speaker.frames_sent > 0
        played = self.speaker.played_ms()
        self.suppress = True
        await self.speaker.interrupt()
        if reason != "server" and not self.resp_done:
            await self._send({"type": "response.cancel"})  # 模型侧自己判的插话（interrupt_response）已经取消过
        if had_audio and self.item_id:
            await self._send({"type": "conversation.item.truncate", "item_id": self.item_id,
                              "content_index": 0, "audio_end_ms": played})
        self.stats[f"barge_{reason}"] = self.stats.get(f"barge_{reason}", 0) + 1
        self.logger.bind(tag=TAG).info(f"打断（{reason}）：截到 {played if had_audio else -1} ms")

    async def _barge(self, reason: str) -> None:
        self._pending_barge = reason
        await handleAbortMessage(self.conn)  # 发 tts stop、置 client_abort，再经 abortHandle 的钩子调到 cancel()

    # ---------- 模型 → 设备 ----------
    async def _rx_loop(self) -> None:
        try:
            async for raw in self.ws:
                try:
                    ev = json.loads(raw)
                except ValueError:
                    continue
                try:
                    await self._on_event(ev.get("type", ""), ev)
                except Exception as e:  # noqa: BLE001
                    self.logger.bind(tag=TAG).error(f"处理 Realtime 事件 {ev.get('type')} 出错: {type(e).__name__}: {e}")
        except ConnectionClosed:
            pass
        if not self.closing:
            self.closing = True
            self.logger.bind(tag=TAG).warning("Realtime 上游断开，关闭本连接（设备重连时若上游仍不可用会回退级联）")
            self.spawn(self.conn.close())

    async def _on_event(self, et: str, ev: dict) -> None:
        conn = self.conn
        if et == "input_audio_buffer.speech_started":
            self.in_speech = True
            conn.last_activity_time = time.time() * 1000
            self.stats["speech_started"] += 1
            if (self.speaker.speaking or self.speaker.frames_queued > self.speaker.frames_sent) and not self.suppress:
                await self._barge("server")
            await self._maybe_refresh_tools()  # 用户开口到模型决定调工具之间还有几百毫秒，够把新注册的工具同步上去
        elif et == "input_audio_buffer.speech_stopped":
            self.in_speech = False
            self.t_speech_stopped = time.monotonic()
            conn.last_activity_time = time.time() * 1000
        elif et == "response.created":
            self.resp_done = False
            self.suppress = False
            self.t_response_requested = None
            self.item_id = None
            await self.speaker.begin()
        elif et == "response.output_item.added":
            item = ev.get("item") or {}
            if item.get("type") == "message":
                self.item_id = item.get("id")
        elif et == "response.output_item.done":
            item = ev.get("item") or {}
            if item.get("type") == "function_call":
                t = self.spawn(self._run_tool(item))
                self._tool_tasks.add(t)
                t.add_done_callback(self._tool_tasks.discard)
        elif et in ("response.output_audio.delta", "response.audio.delta"):
            if self.suppress:
                return
            b = base64.b64decode(ev.get("delta") or "")
            if b and self.t_speech_stopped is not None and not self.speaker.speaking:
                ms = round(1000 * (time.monotonic() - self.t_speech_stopped))
                self.stats["first_audio_ms"].append(ms)
                self.t_speech_stopped = None
                self.logger.bind(tag=TAG).info(f"首个音频片段：说完后 {ms} ms")
            await self.speaker.push(b)
        elif et in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
            txt = ev.get("transcript") or ""
            if self.log_text:
                self.logger.bind(tag=TAG).info(f"assistant: {txt}")
            if txt and not self.suppress:
                await self.show_assistant_text(txt)
        elif et == "conversation.item.input_audio_transcription.completed":
            txt = ev.get("transcript") or ""
            if self.log_text:
                self.logger.bind(tag=TAG).info(f"user: {txt}")
            if txt:
                await self.show_user_text(txt)
        elif et == "response.done":
            r = ev.get("response") or {}
            self.resp_done = True
            self.stats["turns"] += 1
            if r.get("status") != "completed":
                self.stats["cancelled"] += 1
            self.t_reply = time.monotonic()
            if not self.suppress:
                self.spawn(self.speaker.end())  # 等设备播完再发 tts stop；不阻塞事件循环，插话仍能及时处理
            self.logger.bind(tag=TAG).info(
                f"回复 {r.get('status')} ({(r.get('status_details') or {}).get('reason') or '-'})")
            if self.want_response:
                await self._create_response()
            await self._maybe_refresh_tools()
        elif et == "error":
            err = ev.get("error") or {}
            code = err.get("code")
            if code == "conversation_already_has_active_response" and not self.want_response:
                self.want_response = True  # 工具结果的 response.create 撞上了刚开始的新回复：等它结束再发
            msg = f"Realtime error type={err.get('type')} code={code}"
            if code in BENIGN_ERRORS:
                self.logger.bind(tag=TAG).info(msg)
            else:
                self.logger.bind(tag=TAG).warning(msg)

    # ---------- 工具 ----------
    async def _run_tool(self, item: dict) -> None:
        self.stats["tools"] += 1
        output = await self.tools.run(item.get("name"), item.get("arguments") or "{}")
        await self._send({"type": "conversation.item.create",
                          "item": {"type": "function_call_output", "call_id": item.get("call_id"), "output": output}})
        if self.resp_done:
            await self._create_response()
        else:
            self.want_response = True  # 当前还有回复在进行（例如函数调用所在的那条还没 done）：done 时再发

    async def _create_response(self, response: dict | None = None) -> None:
        self.want_response = False
        self.t_response_requested = time.monotonic()
        await self._send({"type": "response.create", **({"response": response} if response else {})})

    # ---------- 空闲关闭（call_later，不用 sleep 循环） ----------
    def _arm_idle(self) -> None:
        if self.idle_close_s <= 0 or self.closing:
            return
        self._idle_handle = self.conn.loop.call_later(1.0, self._idle_tick)

    def _idle_due(self, now: float) -> bool:
        if self.speaker.speaking or not self.resp_done or self.want_response or self._tool_tasks:
            return False
        if self.t_response_requested is not None and now - self.t_response_requested < RESPONSE_START_WAIT_S:
            return False
        if self.in_speech:
            return False
        if self.t_speech_stopped is not None and now - self.t_speech_stopped < SPEECH_GRACE_S:
            return False
        return now - self.t_reply > self.idle_close_s

    def _idle_tick(self) -> None:
        if self.closing:
            return
        if self._idle_due(time.monotonic()):
            self.logger.bind(tag=TAG).info(f"空闲超过 {self.idle_close_s:.0f} 秒，关闭连接")
            self.closing = True
            self.spawn(self.conn.close())
            return
        self._arm_idle()
