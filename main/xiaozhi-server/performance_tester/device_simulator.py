# -*- coding: utf-8 -*-
"""device_simulator.py — xiaozhi 设备协议 v1 音频 E2E 模拟器引擎（无头场景；device_simulator_tui.py 复用本引擎）

本机采集/回放真实音频：麦克风 16k 采集 → Opus 60ms 帧实时上行；下行解码 48k 播放。
支持「数字注入」（wav PCM 直灌识别通道，绕过扬声器↔麦克风声学耦合差异，确定性回归）
与「半双工互斥」（TTS 播放期自动静默上行，防回声，与真机行为一致）。
逐事件 JSONL 日志；上行（实发 16k）/ 下行（实播 48k）PCM 落盘 rec/ 供取证。

用法（在 performance_tester 目录下）:
  python device_simulator.py --scenario baseline --device-id AA:BB:CC:DD:EE:FF \
      --plays "cache_xxx.wav@1.0,cache_yyy.wav@1.5" --out log_baseline.jsonl
  python device_simulator.py --scenario idle --device-id ... --out log_idle.jsonl   # 静音观察
认证: --token <设备token>（或环境变量 DEVICE_SIM_TOKEN）；或 --secret <auth_key> 现签
场景: baseline=多轮注入对话; swallowhunt=短句密集轮次; zombie=半开连接(需管理员netsh); idle=静音保持
"""
import os
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "WSS_PROXY", "WS_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_k, None)  # 强制直连（与设备一致），禁止 env 代理劫持

import argparse
import asyncio
import json
import queue
import socket
import sys
import threading
import time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import urllib.parse
import wave as wavemod
import numpy as np
import sounddevice as sd
import websockets

SAMPLE_RATE = 16000
FRAME_SAMPLES = 960                        # 60ms @16k
FW_IS_TIMEOUT_S = 120                      # 固件 protocol.cc IsTimeout 看门狗

LOG = None
T0 = time.monotonic()


def ev(kind, **kw):
    rec = {"t_wall": time.strftime("%H:%M:%S") + f".{int(time.time()*1000)%1000:03d}",
           "t_mono": round(time.monotonic() - T0, 3), "ev": kind}
    rec.update(kw)
    if LOG:
        LOG.write(json.dumps(rec, ensure_ascii=False) + "\n")
        LOG.flush()
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def resolve_token(args) -> str:
    """认证三选一: --token / 环境变量 DEVICE_SIM_TOKEN / --secret 现签（需能导入服务端 core.auth）"""
    if getattr(args, "token", None):
        return args.token
    if os.environ.get("DEVICE_SIM_TOKEN"):
        return os.environ["DEVICE_SIM_TOKEN"]
    secret = getattr(args, "secret", None)
    if secret:
        _SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _SERVER_ROOT not in sys.path:
            sys.path.insert(0, _SERVER_ROOT)
        from core.auth import AuthManager
        return AuthManager(secret).generate_token(args.client_id, args.device_id)
    return ""


class OpusEncoder:
    def __init__(self):
        import av
        # 关键: PyAV libopus 实际运行于 48k(声明 16k 被忽略, 实测音频 3× 变调)。
        # 显式按 48k 编码: 麦克风 16k 先 ×3 重采样再喂包, 服务端解码即得正确音高/时长。
        self.c = av.CodecContext.create("libopus", "w")
        self.c.sample_rate = 48000
        self.c.layout = "mono"
        self.c.format = av.AudioFormat("s16")
        self.c.options = {"application": "voip"}
        self.c.open()
        ev("enc_open", frame_size=self.c.frame_size, note="48k native")

    def encode(self, pcm_int16_16k: np.ndarray):
        """输入 16k int16(60ms=960 样本) → ×3 重采样 → 48k 编码"""
        import av
        n = len(pcm_int16_16k)
        up = np.interp(
            np.linspace(0, n - 1, n * 3), np.arange(n), pcm_int16_16k.astype(np.float32)
        ).astype(np.int16)
        frame = av.AudioFrame.from_ndarray(up.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = 48000
        frame.pts = None
        return [bytes(p) for p in self.c.encode(frame)]


class OpusDecoder:
    def __init__(self, sr: int):
        import av
        self.c = av.CodecContext.create("libopus", "r")
        self.c.sample_rate = 48000  # libopus 解码输出固定 48k（仅本地播放用；服务端自行解码不受影响）
        self.c.layout = "mono"
        self.c.open()
        self.out_sr = 48000

    def decode(self, packet: bytes) -> np.ndarray:
        import av
        pkt = av.Packet(packet)
        frames = self.c.decode(pkt)
        out = []
        for f in frames:
            arr = f.to_ndarray()
            if arr.dtype != np.int16:
                arr = (np.clip(arr, -1, 1) * 32767).astype(np.int16)
            out.append(arr.reshape(-1))
        return np.concatenate(out) if out else np.zeros(0, dtype=np.int16)


def rms(i16: np.ndarray) -> int:
    if len(i16) == 0:
        return 0
    return int(np.sqrt(np.mean(i16.astype(np.int64) ** 2)))


class Sim:
    def __init__(self, scenario: str, plays, out_path: str, dur: float,
                 url: str, device_id: str, client_id: str, token: str = ""):
        self.scenario = scenario
        self.plays = plays
        self.dur = dur
        self.url = url
        self.device_id = device_id
        self.client_id = client_id
        self.token = token
        self.session_id = None
        self.downlink_sr = 16000
        self.seq = 0
        self.mic_on = True
        self.mic_q = asyncio.Queue(maxsize=200)
        self.loop = None
        self.enc = None
        self.dec = None
        self.playback_active = False
        self.inject = True   # 数字注入(默认开; TUI 人工模式可关, 走真实麦克风)
        self.last_incoming = time.monotonic()
        self.turn_marker = {"speak_end": None}
        self.stt_waiters = []
        self.first_audio_ts = None
        self.tts_done = asyncio.Event()
        self.stt_event = asyncio.Event()
        # TUI/复用安全: 通道属性先置空(open_channel 时创建)
        self.asr_ws = None
        self.ws = None
        self.mic_stream = None
        self.spk_stream = None
        self.pump_task = None
        self.probe_task = None
        # 播放与半双工(F批): 接收/播放解耦 + 播放期上行静默(互斥防回声, 与真机半双工一致)
        self.play_q = queue.Queue(maxsize=2000)
        self._player_thread = None
        self._spk_gen = 0              # 播放代次: abort 后旧队列项作废
        self.tts_playing = False
        self.half_duplex = True        # --duplex 可关(回声实验用); 默认互斥
        self.last_voice_mono = None    # 真麦克风时延锚: 最近一块实音(rms>=600)时刻
        self.last_stt_mono = None
        self.rec_mic = None            # 上行 PCM 落盘(发往服务端的帧, 16k s16le)
        self.rec_spk = None            # 下行 PCM 落盘(解码后播放帧, 48k s16le)

    def _set_mic_state(self, on: bool, reason: str):
        """上行静默开关; 放开时清空积压帧, 防播放期回声/静音块灌入下一轮识别"""
        if self.mic_on == on:
            return
        self.mic_on = on
        if on:
            dropped = 0
            while True:
                try:
                    self.mic_q.get_nowait()
                    dropped += 1
                except Exception:
                    break
            ev("mic_unmute", reason=reason, dropped_backlog=dropped)
        else:
            ev("mic_mute", reason=reason)

    # ---------- 音频 ----------
    def mic_callback(self, indata, frames, t, status):
        if status:
            ev("mic_status", status=str(status))
        if self.mic_on:
            if int(np.sqrt(np.mean(indata.astype(np.int64) ** 2))) >= 600:
                self.last_voice_mono = time.monotonic()   # 采集侧锚(免受 pump 滞后污染)
            try:
                self.mic_q.put_nowait(indata.copy())
            except asyncio.QueueFull:
                self._drops = getattr(self, "_drops", 0) + 1
                if self._drops == 1 or self._drops % 100 == 0:
                    ev("mic_drop", total=self._drops)

    def play_wav(self, path):
        with wavemod.open(path, "rb") as w:
            sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
            raw = w.readframes(n)
        data = np.frombuffer(raw, dtype=np.int16)
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1).astype(np.int16)
        ev("speak_start", file=os.path.basename(path), sr=sr, dur_ms=int(n / sr * 1000), rms=rms(data))
        # 数字注入: wav PCM 直灌麦克风队列(绕过扬声器↔麦克风声学耦合差异, 确定性回归)
        if self.inject:
            import threading
            def _feed():
                self.mic_on = False   # 注入期间静默真实麦克风(单源, 防交叠稀释)
                while not self.mic_q.empty():   # 清空积压的真实麦克风静音块, 防语音块排队迟到
                    try:
                        self.mic_q.get_nowait()
                    except Exception:
                        break
                step = 960
                drops = 0
                for i in range(0, len(data), step):
                    try:
                        self.mic_q.put_nowait(data[i:i + step].reshape(-1, 1).copy())
                    except Exception:
                        drops += 1   # 丢帧可审计(不再静默)
                        if drops % 100 == 1:
                            ev("inject_drop", total=drops)
                    time.sleep(0.06)
                time.sleep(0.3)
                if not self.tts_playing:   # 回复已在播则保持静默(半双工), 由 tts stop 统一放开
                    self.mic_on = True
            threading.Thread(target=_feed, daemon=True).start()
        else:
            sd.play(data, samplerate=sr)
        sd.wait()
        self.turn_marker["speak_end"] = time.monotonic()
        ev("speak_end", file=os.path.basename(path))

    async def mic_pump(self):
        # 节拍在消费侧 —— 第 k 块应发时刻对齐单调钟(60ms/块), 落后>1s 追平
        ev("pump_start")
        try:
            await self._mic_pump_inner()
        except asyncio.CancelledError:
            ev("pump_cancelled")
            raise
        except Exception as e:
            import traceback as _tb
            ev("pump_fatal", err=repr(e), tb=_tb.format_exc()[-500:])

    async def _mic_pump_inner(self):
        t_origin = time.monotonic()
        block_idx = 0
        last_consume = time.monotonic()
        while True:
            block = await self.mic_q.get()
            now = time.monotonic()
            if now - last_consume > 0.5:
                # 产量断档(半双工静音/注入间隙)后重锚节拍, 防把静音时长误判为滞后而突发连发
                t_origin = now - block_idx * 0.06
                ev("pump_reanchor", gap_s=round(now - last_consume, 2), qsize=self.mic_q.qsize())
            last_consume = now
            n = len(block)
            for i in range(0, n, FRAME_SAMPLES):
                chunk = block[i:i + FRAME_SAMPLES].reshape(-1)
                if len(chunk) < FRAME_SAMPLES:
                    continue
                block_idx += 1
                due = t_origin + block_idx * 0.06
                lag = time.monotonic() - due
                if lag > 1.0:
                    ev("pump_catchup", lag_s=round(lag, 2), qsize=self.mic_q.qsize())
                    t_origin = time.monotonic() - block_idx * 0.06   # 重锚, 放弃历史滞后
                elif lag < -0.005:
                    await asyncio.sleep(-lag)   # 超前则睡到点
                r = rms(chunk)
                if self.rec_mic:
                    self.rec_mic.write(chunk.astype(np.int16).tobytes())
                try:
                    pkts = self.enc.encode(chunk)
                    for pkt in pkts:
                        self.seq += 1
                        await self.ws.send(pkt)
                    if block_idx % 17 == 1:
                        ev("frame_tx", seq=block_idx, rms=r, qsize=self.mic_q.qsize())
                except websockets.ConnectionClosed:
                    ev("pump_exit_closed", seq=block_idx)
                    return

    async def audio_rx(self, data: bytes):
        if not self.tts_playing:
            self.tts_playing = True
            if self.half_duplex:
                self._set_mic_state(False, reason="tts_playback")   # 半双工: 播放即静默上行
        if self.first_audio_ts is None:
            self.first_audio_ts = time.monotonic()
            lat_stt = (round(self.first_audio_ts - self.last_stt_mono, 3)
                       if self.last_stt_mono else None)
            ev("tts_first_audio", latency_from_speak_end=(
                round(self.first_audio_ts - self.turn_marker["speak_end"], 3)
                if self.turn_marker["speak_end"] else None),
               latency_from_stt=lat_stt)
        pcm = self.dec.decode(data)
        if self.rec_spk:
            self.rec_spk.write(pcm.tobytes())
        try:
            self.play_q.put_nowait((self._spk_gen, pcm))
        except queue.Full:
            ev("play_q_full", dropped=True)

    def _player_loop(self):
        """单线程顺序写扬声器: 接收循环不再被阻塞写背压(曾实测文本消息延迟 8s)"""
        while True:
            item = self.play_q.get()
            if item is None:
                return
            gen, pcm = item
            if gen != self._spk_gen or len(pcm) == 0:
                continue
            if getattr(self, "_spk_started", False) is False:
                self._spk_started = True
                ev("tts_play_start", latency_from_speak_end=(
                    round(time.monotonic() - self.turn_marker["speak_end"], 3)
                    if self.turn_marker["speak_end"] else None))
            g = getattr(self, "playback_gain", 1.0)
            if g != 1.0:
                a = np.frombuffer(pcm, dtype=np.int16).astype(np.int32)
                pcm = np.clip(a * g, -32768, 32767).astype(np.int16).tobytes()
            try:
                self.spk_stream.write(pcm)
            except Exception as e:
                if getattr(self, "_spk_err_last", "") != str(e):   # 连续同错去重(停流期间刷屏)
                    ev("spk_err", err=str(e))
                self._spk_err_last = str(e)
            else:
                self._spk_err_last = ""

    # ---------- 协议 ----------
    def hello_msg(self):
        return json.dumps({"type": "hello", "version": 1, "features": {"mcp": True},
                           "transport": "websocket",
                           "audio_params": {"format": "opus", "sample_rate": SAMPLE_RATE,
                                            "channels": 1, "frame_duration": 60}}, ensure_ascii=False)

    async def handle_text(self, raw: str):
        try:
            msg = json.loads(raw)
        except Exception:
            ev("text_rx_unparsed", raw=raw[:200])
            return
        t = msg.get("type")
        if t == "hello":
            self.session_id = msg.get("session_id")
            ap = msg.get("audio_params") or {}
            self.downlink_sr = int(ap.get("sample_rate", 16000))
            self.dec = OpusDecoder(self.downlink_sr)
            ev("hello_rx", session_id=self.session_id, downlink_sr=self.downlink_sr)
        elif t == "mcp":
            await self.reply_mcp(msg)
        elif t == "tts":
            st = msg.get("state")
            if st == "stop":
                self.tts_playing = False
                if self.half_duplex:
                    self._set_mic_state(True, reason="tts_stop")
                self.tts_done.set()
            ev("tts_state", state=st, **{k: v for k, v in msg.items() if k in ("session_id", "text")})
        elif t == "stt":
            lat = None
            now = time.monotonic()
            if self.last_voice_mono and 0 <= now - self.last_voice_mono < 60:
                lat = round(now - self.last_voice_mono, 3)   # 真麦克风: 最近实音→识别到达
            elif self.turn_marker["speak_end"]:
                lat = round(now - self.turn_marker["speak_end"], 3)
            self.last_stt_mono = now
            ev("stt_rx", text=msg.get("text"), stt_latency_from_speak_end=lat)
            self.stt_event.set()
        else:
            ev("text_rx", msg=json.dumps(msg, ensure_ascii=False)[:300])

    async def reply_mcp(self, msg):
        payload = msg.get("payload") or {}
        rid = payload.get("id")
        method = payload.get("method", "")
        if rid is None:
            return
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "esp32-s3", "version": "2.5.2"}}
        elif method == "tools/list":
            result = {"tools": []}
        else:
            result = {}
        out = json.dumps({"session_id": self.session_id, "type": "mcp",
                          "payload": {"jsonrpc": "2.0", "id": rid, "result": result}},
                         ensure_ascii=False)
        await self.ws.send(out)
        ev("mcp_reply", method=method, id=rid)

    async def listen(self, state, mode="auto"):
        await self.ws.send(json.dumps({"session_id": self.session_id, "type": "listen",
                                       "state": state, "mode": mode}, ensure_ascii=False))
        ev("listen_tx", state=state, mode=mode)

    # ---------- 场景 ----------
    def _entry_ip(self) -> str:
        """从 --url 解析服务端入口 IPv4(zombie 场景防火墙阻断用)"""
        host = urllib.parse.urlparse(self.url).hostname or ""
        return socket.gethostbyname(host)

    async def open_channel(self):
        old_pump = getattr(self, "pump_task", None)
        if old_pump:
            old_pump.cancel()
        old_probe = getattr(self, "probe_task", None)
        if old_probe:
            old_probe.cancel()
        for attr in ("mic_stream", "spk_stream"):
            s = getattr(self, attr, None)
            if s:
                try:
                    s.stop(); s.close()
                except Exception:
                    pass
        ev("connect_start", url=self.url)
        headers = {"Device-Id": self.device_id, "Client-Id": self.client_id,
                   "Protocol-Version": "1"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        use_ping = self.scenario != "zombie"  # zombie 场景忠实固件：无任何 ping
        self.ws = await websockets.connect(
            self.url, additional_headers=headers,
            max_size=None,
            ping_interval=20 if use_ping else None,
            ping_timeout=15 if use_ping else None,
            close_timeout=5)
        ev("connect_ok", client_ping=use_ping)
        await self.ws.send(self.hello_msg())
        ev("hello_tx")
        self.enc = OpusEncoder()
        self.mic_stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                         blocksize=FRAME_SAMPLES, callback=self.mic_callback)
        self.spk_stream = sd.OutputStream(samplerate=48000, channels=1, dtype="int16")
        self.spk_stream.start()
        self.mic_stream.start()
        ev("audio_devices", mic=sd.query_devices(kind="input")["name"],
           spk=sd.query_devices(kind="output")["name"])
        # 端侧取证落盘: 上行(实际发往服务端, 16k) + 下行(解码后播放帧, 48k)
        for f in (self.rec_mic, self.rec_spk):   # 先关旧句柄(重开频道场景)
            if f:
                try:
                    f.close()
                except Exception:
                    pass
        try:
            os.makedirs("rec", exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            self.rec_mic = open(f"rec/mic_{ts}.pcm", "wb")
            self.rec_spk = open(f"rec/spk_{ts}.pcm", "wb")
            ev("rec_start", mic_dump=f"rec/mic_{ts}.pcm", spk_dump=f"rec/spk_{ts}.pcm",
               mic_sr=16000, spk_sr=48000)
        except Exception as e:
            ev("rec_start_err", err=str(e))
        old_player = self._player_thread
        if old_player is not None:
            self.play_q.put(None)   # 让旧播放线程退出, 防双线程竞争队列
        self._player_thread = threading.Thread(target=self._player_loop, daemon=True)
        self._player_thread.start()
        self.pump_task = asyncio.create_task(self.mic_pump())
        if self.scenario != "zombie":
            self.probe_task = asyncio.create_task(self.ping_probe())

    async def ping_probe(self):
        """每 10s 主动 ping 一次测路径 RTT；pong 停 = 路径死，pong 活但无数据 = 服务端楔死"""
        while True:
            await asyncio.sleep(10)
            try:
                t0 = time.monotonic()
                await asyncio.wait_for(self.ws.ping(), timeout=8)
                ev("ping_rtt_ms", ms=round((time.monotonic() - t0) * 1000))
            except Exception as e:
                ev("ping_fail", err=repr(e))

    async def recv_loop(self):
        try:
            async for raw in self.ws:
                self.last_incoming = time.monotonic()
                if isinstance(raw, str):
                    await self.handle_text(raw)
                else:
                    await self.audio_rx(raw)
                    self.seq_rx = getattr(self, "seq_rx", 0) + 1
                    if self.seq_rx % 50 == 1:
                        ev("frame_rx", seq=self.seq_rx, bytes=len(raw))
        except websockets.ConnectionClosed as e:
            ev("ws_closed", code=getattr(e, "code", None), reason=str(getattr(e, "reason", "")))
        except Exception as e:
            ev("ws_error", err=repr(e))

    async def abort(self, reason="user"):
        """打断: 发 abort(type=abort, 服务端 AbortTextMessageHandler 才会路由) + 本地即停 + 释放上行静默
        (实证: type=listen/state=abort 服务端静默忽略, 抓包验证)"""
        if self.ws:
            try:
                await self.ws.send(json.dumps(
                    {"session_id": self.session_id, "type": "abort"}))
            except Exception as e:
                ev("abort_send_err", err=str(e))
        self._spk_gen += 1
        dropped = 0
        while True:
            try:
                self.play_q.get_nowait()
                dropped += 1
            except Exception:
                break
        try:
            self.spk_stream.stop()   # 丢弃设备缓冲中在发声帧, 立即静音
            self.spk_stream.start()
        except Exception as e:
            ev("spk_flush_err", err=str(e))
        self.tts_playing = False
        self._spk_started = False
        if self.half_duplex:
            self._set_mic_state(True, reason="abort")
        ev("abort_tx", reason=reason, dropped_playq=dropped)

    async def do_turn(self, wav_path, settle=0.8):
        """一轮对话：静置→播放语音(麦克风采集回灌)→等 stt→等 tts 播完"""
        self.turn_marker["speak_end"] = None
        self.first_audio_ts = None
        self.tts_done.clear()
        self.stt_event.clear()
        await asyncio.sleep(settle)
        await asyncio.get_event_loop().run_in_executor(None, self.play_wav, wav_path)
        try:
            await asyncio.wait_for(self.stt_event.wait(), timeout=15)
        except asyncio.TimeoutError:
            ev("stt_wait_timeout")
        try:
            await asyncio.wait_for(self.tts_done.wait(), timeout=60)
        except asyncio.TimeoutError:
            ev("tts_wait_timeout")
        await asyncio.sleep(0.5)

    async def run_idle(self, seconds: float = 150.0):
        """静音观察: 建连+listen 后保持静音 N 秒(验证静音空识别不触发兜底)"""
        await self.open_channel()
        recv = asyncio.create_task(self.recv_loop())
        await asyncio.sleep(0.5)
        await self.listen("start")
        t0 = time.monotonic()
        while time.monotonic() - t0 < seconds:
            await asyncio.sleep(10)
            ev("idle_tick", since_start_s=round(time.monotonic() - t0, 1))
        await self.listen("stop")
        await asyncio.sleep(1)
        await self.ws.close()
        ev("close_tx")
        recv.cancel()

    async def run_baseline(self):
        await self.open_channel()
        recv = asyncio.create_task(self.recv_loop())
        await asyncio.sleep(0.5)
        await self.listen("start")
        for p in self.plays:
            wav, delay = (p.split("@") + ["1.0"])[:2]
            await asyncio.sleep(float(delay))
            await self.do_turn(wav)
        ev("baseline_done", turns=len(self.plays))
        await self.listen("stop")
        await asyncio.sleep(1)
        await self.ws.close()
        ev("close_tx")
        recv.cancel()

    async def run_swallowhunt(self):
        # 与 baseline 同构，但轮次多、句子短，逐轮标记编号便于与服务端"重放 N 帧"对照
        await self.run_baseline()

    async def run_zombie(self):
        """半开连接模拟: 防火墙吞 FIN 后关旧连接→服务端无感知→新连接并存(复现会话不收敛)。
        需要管理员权限执行 netsh; 仅 Windows。"""
        import subprocess
        await self.open_channel()
        recv = asyncio.create_task(self.recv_loop())
        await asyncio.sleep(0.5)
        await self.listen("start")
        await self.do_turn(self.plays[0].split("@")[0])
        ev("zombie_phase", phase="turn_done_going_idle")
        # 进入"设备空闲"：停发音频（真机空闲不推流），保持 WS 打开
        self.mic_on = False
        block_rule = 'xiaozhi-sim-block'
        block_ip = self._entry_ip()
        subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", "name=" + block_rule],
                       capture_output=True)
        r = subprocess.run(["netsh", "advfirewall", "firewall", "add", "rule", "name=" + block_rule,
                            "dir=out", "action=block", f"remoteip={block_ip}",
                            "protocol=tcp", "remoteport=443"], capture_output=True, text=True)
        ev("firewall_block_on", rc=r.returncode, remoteip=block_ip)
        t_block = time.monotonic()
        for m in (30, 60, 90, 120):
            await asyncio.sleep(m - (time.monotonic() - t_block) if time.monotonic() - t_block < m else 0)
            ev("zombie_tick", since_block_s=round(time.monotonic() - t_block, 1),
               since_incoming_s=round(time.monotonic() - self.last_incoming, 1))
        ev("fw_is_timeout_fires", note=f"固件 IsTimeout({FW_IS_TIMEOUT_S}s) 等效点：频道判死")
        # 固件语义：websocket_.reset() —— 关旧 socket（FIN 走被阻断路径=丢失），随后新开连接
        try:
            await self.ws.close()
            ev("old_socket_close_tx", note="FIN 被防火墙吞掉，服务端将无感知")
        except Exception as e:
            ev("old_socket_close_err", err=repr(e))
        await asyncio.sleep(3)
        ev("zombie_phase", phase="reopen_channel")
        self.mic_on = True
        await self.open_channel()   # 新连接（新 hello/新 session）
        recv.cancel()
        recv = asyncio.create_task(self.recv_loop())
        await asyncio.sleep(0.5)
        await self.listen("start")
        await self.do_turn(self.plays[-1].split("@")[0])
        ev("zombie_phase", phase="post_reopen_turn_done")
        r = subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", "name=" + block_rule],
                           capture_output=True)
        ev("firewall_block_off", rc=r.returncode)
        # 保留 20s 观测旧僵尸是否被服务端回收
        await asyncio.sleep(20)
        ev("zombie_done")
        try:
            await self.ws.close()
        except Exception:
            pass
        recv.cancel()


def phrase_cache_names(limit: int = 4) -> list:
    """从 phrases.txt 读语料, 返回前 limit 条对应的预合成缓存文件名(存在才返回)"""
    import hashlib
    pf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phrases.txt")
    try:
        phrases = [ln.strip() for ln in open(pf, encoding="utf-8")
                   if ln.strip() and not ln.strip().startswith("#")]
    except OSError:
        return []
    names = []
    for text in phrases:
        cache = f"cache_{hashlib.md5(text.encode()).hexdigest()[:10]}.wav"
        if os.path.exists(cache):
            names.append(cache)
        if len(names) >= limit:
            break
    return names


def add_common_args(ap: argparse.ArgumentParser):
    ap.add_argument("--url", default=os.environ.get("DEVICE_SIM_URL", "ws://127.0.0.1:8000/xiaozhi/v1/"))
    ap.add_argument("--device-id", default=os.environ.get("DEVICE_SIM_ID", ""),
                    help="设备 Device-Id（如 AA:BB:CC:DD:EE:FF）")
    ap.add_argument("--client-id", default=os.environ.get("DEVICE_SIM_CLIENT_ID") or None)
    ap.add_argument("--token", default="", help="设备 token（服务端开启认证时）")
    ap.add_argument("--secret", default="", help="服务端 auth_key，现签 token（服务端本机调试方便）")
    ap.add_argument("--noinject", action="store_true", help="禁用数字注入(走真实声学路径)")
    ap.add_argument("--duplex", action="store_true", help="关闭半双工互斥(播放期不静默上行, 回声实验用)")


async def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    ap.add_argument("--scenario", required=True, choices=["baseline", "swallowhunt", "zombie", "idle"])
    ap.add_argument("--plays", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dur", type=float, default=600)
    args = ap.parse_args()
    if not args.device_id:
        ap.error("缺少 --device-id（或环境变量 DEVICE_SIM_ID）")
    args.client_id = args.client_id or __import__("uuid").uuid4().__str__()
    token = resolve_token(args)

    global LOG
    LOG = open(args.out, "a", encoding="utf-8")
    plays = [p for p in args.plays.split(",") if p]
    if not plays and args.scenario in ("baseline", "swallowhunt", "zombie"):
        plays = phrase_cache_names(limit=6 if args.scenario == "swallowhunt" else 1)
        if not plays:
            ap.error("未提供 --plays，且 phrases.txt 对应的预合成缓存不存在（先运行 prewarm_corpus.py）")
    sim = Sim(args.scenario, plays, args.out, args.dur,
              url=args.url, device_id=args.device_id, client_id=args.client_id, token=token)
    if args.noinject:
        sim.inject = False
    if args.duplex:
        sim.half_duplex = False
    fn = {"baseline": sim.run_baseline, "swallowhunt": sim.run_swallowhunt,
          "zombie": sim.run_zombie, "idle": sim.run_idle}[args.scenario]
    try:
        await asyncio.wait_for(fn(), timeout=args.dur)
    except asyncio.TimeoutError:
        ev("sim_timeout", dur=args.dur)
    except Exception as e:
        ev("sim_fatal", err=repr(e))
    finally:
        try:
            sim.mic_stream.stop(); sim.mic_stream.close()
            sim.spk_stream.stop(); sim.spk_stream.close()
        except Exception:
            pass
        ev("sim_exit")


if __name__ == "__main__":
    asyncio.run(main())
