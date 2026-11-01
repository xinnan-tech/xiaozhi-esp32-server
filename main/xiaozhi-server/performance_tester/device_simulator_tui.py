# -*- coding: utf-8 -*-
"""device_simulator_tui.py — xiaozhi 设备模拟器交互前端（Textual TUI）

复用 device_simulator.py 的引擎（Sim/Opus/日志），逐轮全量回显输入输出
+ L1-L5 时延面板 + 网络质量探针（WS ping RTT）+ 键位交互（唤醒/打断/音量/语料注入）。

用法（在 performance_tester 目录下）:
  python device_simulator_tui.py --device-id AA:BB:CC:DD:EE:FF [--url ...] [--token ...|--secret ...]
键位: w 唤醒 · space 打断 · m 麦克风 · p 探针 · e 重载语料 · 1-9 注入语料 · +/- 音量 · q 退出
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
import time
import wave as wavemod
import numpy as np

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Header, Footer, RichLog, Static

import device_simulator as core
from device_simulator import Sim, FRAME_SAMPLES, add_common_args, resolve_token

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHRASES_FILE = os.path.join(_BASE_DIR, "phrases.txt")   # 每行一条, # 注释


class SimTuiApp(App):
    TITLE = "xiaozhi device simulator"
    SUB_TITLE = "device protocol v1 · E2E"

    CSS = """
    Screen { layout: vertical; }
    #conv { height: 40%; border: round $accent; }
    #lat  { height: auto; border: round $success; padding: 0 1; }
    #meter{ height: auto; border: round $warning; padding: 0 1; }
    #evt  { height: 1fr; border: round $primary; }
    """
    BINDINGS = [
        ("w", "wake", "唤醒"),
        ("space", "abort", "打断"),
        ("m", "mic", "麦克风"),
        ("p", "probe", "探针"),
        ("e", "reload", "重载语料"),
        ("q", "quit", "退出"),
    ]

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.sim = None
        self.phrases = []
        self.gain = 1.0
        self.probe_on = False
        self.probe_task = None
        self.state = "idle"
        self.turn_lat = []          # [(L2, L3, L5)] 近 5 轮
        self.cur = {}               # 本轮时延锚点
        self._evt_poll = None
        self._evq = []
        self._evq_lock = __import__("threading").Lock()

    # ---------- 布局 ----------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="conv", markup=True, highlight=False, wrap=True)
        yield Static("时延 本轮/近5轮均值 — 尚无数据", id="lat")
        yield Static("麦克风 ▁▁▁  扬声器 ▁", id="meter")
        yield RichLog(id="evt", markup=False, wrap=True)
        yield Footer()

    # ---------- 事件路由 ----------
    def _route_ev(self, rec: dict):
        """线程安全事件入口: 入队, UI 定时器排空(规避跨线程/同线程差异)"""
        with self._evq_lock:
            self._evq.append(rec)

    def _handle_ev(self, rec: dict):
        kind = rec.get("ev", "")
        t = rec.get("t_wall", "")
        evt_log = self.query_one("#evt", RichLog)
        conv = self.query_one("#conv", RichLog)
        # 对话回显
        if kind == "stt_rx":
            conv.write(f"[b cyan]{t} 我[/] {rec.get('text','')}")
            self.cur["stt"] = rec.get("t_mono")
            l2_real = rec.get("stt_latency_from_speak_end")
            if l2_real is not None:
                self.cur["l2_real"] = l2_real   # 真麦克风: 引擎按最近实音锚计算
            self.state = "listening"
        elif kind == "mic_mute":
            self._mic_muted = rec.get("reason", "tts")
        elif kind == "mic_unmute":
            self._mic_muted = None
        elif kind == "tts_state" and rec.get("state") == "sentence_start":
            conv.write(f"[b green]{t} 小智[/] {rec.get('text','')}")
            self.state = "speaking"
        elif kind == "tts_state" and rec.get("state") == "stop":
            self.state = "listening"
        elif kind == "speak_start":
            conv.write(f"[b yellow]{t} 我(注入)[/] {rec.get('file','')} ({rec.get('dur_ms',0)}ms)")
            self.cur["speak_start"] = rec.get("t_mono")
            self.cur["speak_end"] = None
        elif kind == "speak_end":
            self.cur["speak_end"] = rec.get("t_mono")
        # 状态机
        elif kind == "connect_ok":
            self.state = "connecting"
        elif kind == "hello_rx":
            self.state = "listening"
            self.cur["l1_done"] = rec.get("t_mono")
        elif kind == "listen_tx" and rec.get("state") == "start":
            if self.state == "idle":
                self.state = "connecting"
        elif kind == "ws_closed":
            self.state = "idle"
        elif kind in ("tts_first_audio", "tts_play_start"):
            self.cur.setdefault(kind, rec.get("t_mono"))
        # 时延计算
        if kind in ("stt_rx", "tts_first_audio", "tts_play_start", "hello_rx", "speak_end"):
            self._update_latency()
        # 探针
        if kind == "ping_rtt_ms":
            self._last_rtt = rec.get("ms")
        # 事件尾栏(全量)
        evt_log.write(f"{t} {json.dumps(rec, ensure_ascii=False)[:180]}")
        self._refresh_meter(rec)

    def _update_latency(self):
        cur = self.cur
        l2 = l3 = l5 = None
        se, stt, fa, ps = cur.get("speak_end"), cur.get("stt"), cur.get("tts_first_audio"), cur.get("tts_play_start")
        l2 = cur.get("l2_real")            # 引擎锚(真麦克风/注入均有效)
        if stt and fa and fa > stt:
            l3 = round(fa - stt, 2)
        if se and ps and ps > se:
            l5 = round(ps - se, 2)
        if l2 is not None and fa:
            row = (l2, l3, l5)
            if not self.turn_lat or self.turn_lat[-1] != row:
                self.turn_lat.append(row)
                self.turn_lat = self.turn_lat[-5:]
        lat = self.query_one("#lat", Static)
        if self.turn_lat:
            n = len(self.turn_lat)
            m2 = round(sum(r[0] or 0 for r in self.turn_lat) / n, 2)
            m3 = round(sum(r[1] or 0 for r in self.turn_lat) / n, 2)
            m5 = round(sum(r[2] or 0 for r in self.turn_lat) / n, 2)
            last = self.turn_lat[-1]
            lat.update(
                f"L1 唤醒→建连 {self._l1}s   L2 说完→STT {last[0]}/{m2}s   "
                f"L3 STT→首包 {last[1]}/{m3}s   L5 端到端 {last[2]}/{m5}s   "
                f"(近{n}轮均值)")
        self.sub_title = f"device · 状态 {self.state} · 会话 {(self.sim.session_id or '-')[:8]} · 音量 {int(self.gain*70)}"

    _l1 = 0.0

    def _refresh_meter(self, rec):
        meter = self.query_one("#meter", Static)
        mic_bar = "▇" * min(10, (rec.get("rms", 0) or 0) // 400) if rec.get("ev") == "frame_tx" else None
        if mic_bar is not None:
            self._mic_level = mic_bar
        playing = "▶ 播放中" if rec.get("ev") == "tts_first_audio" else self._spk_state
        mic_label = "🔇静默(播放中)" if getattr(self, "_mic_muted", None) else getattr(self, "_mic_level", "▁▁▁")
        meter.update(f"麦克风 {mic_label}   扬声器 {playing}   "
                     f"RTT {getattr(self,'_last_rtt','-')}ms   探针 {'开' if self.probe_on else '关'}")

    _mic_level = "▁▁▁"
    _spk_state = "▁"
    _mic_muted = None

    # ---------- 动作 ----------
    def on_key(self, event):
        if event.character.isdigit() and event.character != "0":
            self.run_worker(self._phrase_n(int(event.character)), exclusive=False)
        elif event.character == "+":
            self.run_worker(self.action_vol_up(), exclusive=False)
        elif event.character == "-":
            self.run_worker(self.action_vol_dn(), exclusive=False)

    async def action_wake(self):
        if self.sim is None:
            self.sim = Sim("tui", [], "", 86400,
                           url=self.args.url, device_id=self.args.device_id,
                           client_id=self.args.client_id, token=self.token)
            if self.args.noinject:
                self.sim.inject = False
            if self.args.duplex:
                self.sim.half_duplex = False
        if self.sim.asr_ws is None:
            self._l1 = 0.0
            t0 = time.monotonic()
            await self.sim.open_channel()
            self._l1 = round(time.monotonic() - t0, 2)
            # 引擎 recv_loop 是独立任务(headless 场景里手动创建), TUI 侧同样必须启动
            self.sim.recv_task = asyncio.create_task(self.sim.recv_loop())
            await self.sim.listen("start")
        else:
            self.notify("频道已打开")

    def _route_ev_bridge(self, rec):
        # 引擎 ev() 被替换为本桥: 写 JSONL + 路由 UI
        if core.LOG:
            core.LOG.write(json.dumps(rec, ensure_ascii=False) + "\n")
            core.LOG.flush()
        self._route_ev(rec)

    async def action_abort(self):
        if self.sim and self.sim.asr_ws and self.sim.session_id:
            await self.sim.abort(reason="tui_space")
            self.state = "listening"
        else:
            self.notify("频道未打开")

    async def action_mic(self):
        if self.sim:
            self.sim.mic_on = not self.sim.mic_on
            self.notify(f"麦克风 {'开' if self.sim.mic_on else '关'}")

    async def action_probe(self):
        self.probe_on = not self.probe_on
        if self.probe_on and self.sim and self.sim.asr_ws:
            self.sim.probe_task = asyncio.create_task(self.sim.ping_probe())
            self.notify("探针 P1 开(WS ping RTT)")
        elif not self.probe_on and getattr(self.sim, "probe_task", None):
            self.sim.probe_task.cancel()
            self.sim.probe_task = None
            self.notify("探针关")

    async def action_reload(self):
        self._load_phrases()
        self.notify(f"语料重载: {len(self.phrases)} 条")

    def _load_phrases(self):
        try:
            with open(PHRASES_FILE, encoding="utf-8") as f:
                self.phrases = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        except FileNotFoundError:
            self.phrases = []
            self.notify("phrases.txt 不存在")

    async def _inject_phrase(self, text: str):
        """语料文本 → 本地合成(缓存) → 数字注入; 合成链: edge-tts → PowerShell SAPI → 报错"""
        import hashlib, subprocess
        cache = os.path.join(_BASE_DIR, f"cache_{hashlib.md5(text.encode()).hexdigest()[:10]}.wav")
        if not os.path.exists(cache):
            ok = False
            try:
                import edge_tts
                await edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural").save(cache)
                ok = os.path.getsize(cache) > 1000
            except Exception:
                ok = False
            if not ok:
                try:
                    r = subprocess.run(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-File",
                         os.path.join(_BASE_DIR, "speak.ps1"), text, os.path.abspath(cache)],
                        capture_output=True, timeout=30)
                    ok = os.path.exists(cache) and os.path.getsize(cache) > 1000
                except Exception as e:
                    self.notify(f"合成失败: {e}")
                    return
            if not ok:
                self.notify("合成失败(edge-tts+SAPI 均不可用)")
                return
        self.cur = {"speak_start": time.monotonic()}
        await self.sim.do_turn(cache)

    async def _phrase_n(self, n: int):
        if not self.phrases:
            self._load_phrases()
        if 1 <= n <= len(self.phrases):
            await self._inject_phrase(self.phrases[n - 1])

    async def action_vol_up(self):
        self.gain = min(2.0, self.gain + 0.2)
        if self.sim:
            self.sim.playback_gain = self.gain
        self.notify(f"播放增益 {int(self.gain*50)}%")

    async def action_vol_dn(self):
        self.gain = max(0.2, self.gain - 0.2)
        if self.sim:
            self.sim.playback_gain = self.gain
        self.notify(f"播放增益 {int(self.gain*50)}%")

    # ---------- 生命周期 ----------
    def on_mount(self):
        self._load_phrases()
        conv = self.query_one("#conv", RichLog)
        conv.write("[b]键位[/] w唤醒 · space打断(本地即停+清队列) · m麦克风 · p探针 · e重载语料 · q退出 · 1-9注入语料 · +/- 音量")
        conv.write("[b]半双工[/] 播放期间上行自动静默(互斥防回声, 与真机一致); 上下行 PCM 落盘 rec/ 供取证")
        conv.write(f"[b]语料[/] {len(self.phrases)} 条(phrases.txt); 人工对话直接对麦克风说话(auto 模式)")
        self._evt_poll = self.set_interval(0.2, self._poll_events)

    def _poll_events(self):
        while True:
            with self._evq_lock:
                if not self._evq:
                    return
                rec = self._evq.pop(0)
            self._handle_ev(rec)

    async def action_quit(self):
        try:
            if self.sim and self.sim.asr_ws:
                await self.sim.ws.close()
        except Exception:
            pass
        self.exit()


def install_bridge(app):
    """引擎 ev() 桥接到 TUI(签名与引擎一致: (kind, **kw) → 记录构建+JSONL+UI 路由)"""
    log_path = os.path.join(
        _BASE_DIR, "tui_" + time.strftime("%Y%m%d_%H%M%S") + ".jsonl")
    log_fh = open(log_path, "a", encoding="utf-8")

    def bridge(kind, **kw):
        rec = {"t_wall": time.strftime("%H:%M:%S") + f".{int(time.time()*1000)%1000:03d}",
               "t_mono": round(time.monotonic() - core.T0, 3), "ev": kind}
        rec.update(kw)
        try:
            log_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log_fh.flush()
        except Exception:
            pass
        app._route_ev(rec)

    core.ev = bridge


def main():
    import argparse
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    args = ap.parse_args()
    if not args.device_id:
        ap.error("缺少 --device-id（或环境变量 DEVICE_SIM_ID）")
    args.client_id = args.client_id or __import__("uuid").uuid4().__str__()
    args.token = resolve_token(args)

    app = SimTuiApp(args)
    install_bridge(app)
    try:
        app.run()
    except Exception:
        # 启动/运行异常落盘, 留证据通道
        import traceback as _tb
        p = os.path.join(_BASE_DIR, f"tui_error_{time.strftime('%Y%m%d_%H%M%S')}.log")
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(_tb.format_exc())
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
