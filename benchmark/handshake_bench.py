"""
xiaozhi-server 握手基准测试脚本（异步 drain 版）

模拟 digital-human 客户端最小握手路径：
  ws 连接 → 发 hello(features.mcp=true) → 收 welcome
       → 发 listen detect "嘿，你好呀" → 收 wake word TTS 音频
       → 响应 MCP initialize / tools/list

与原版差异：
- recv_data 放到后台线程持续 drain，所有 frame 入队（带时间戳）
- 主循环从队列取 frame：binary 帧丢弃，text 帧立即解析处理
- 模拟 digital-human websocket.js 异步 onmessage 行为
- binary 帧不再阻塞主循环对 text frame 的处理（虽然 FIFO 顺序不变，
  但确保 bench 不再因 settleout 等待而漏掉 tools/list 帧）

指标：
  t_hello_to_first_audio   : hello 发送 → 第一帧 TTS 音频（binary）抵达
  t_hello_to_tools_ready   : hello 发送 → server 下发 tools/list 请求抵达

用法：
  python benchmark/handshake_bench.py --runs 10 --url ws://localhost:8000/xiaozhi/v1/
"""

import argparse
import json
import queue
import statistics
import sys
import threading
import time
import uuid
from datetime import datetime

import websocket


HELLO = {
    "type": "hello",
    "device_id": "bench-device-001",
    "device_name": "bench",
    "device_mac": "00:00:00:00:00:01",
    "token": "",
    "features": {"mcp": True, "emoji": False},
}

WAKEUP_TEXT = "嘿，你好呀"
LISTEN_START = {"type": "listen", "state": "start", "mode": "auto"}


def mcp_init_response(req_id):
    return {
        "type": "mcp",
        "payload": {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bench-client", "version": "0.0.1"},
            },
        },
    }


def mcp_tools_response(req_id, n_tools=2):
    return {
        "type": "mcp",
        "payload": {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": f"self.bench_tool_{i}",
                        "description": f"bench tool {i}",
                        "inputSchema": {"type": "object", "properties": {}, "required": []},
                    }
                    for i in range(n_tools)
                ]
            },
        },
    }


def now_ms(t0):
    return (time.monotonic() - t0) * 1000.0


def stamp_ms(t0):
    return now_ms(t0)


def run_one(url, run_idx, args, headers_extra=None):
    session_id = str(uuid.uuid4())
    headers = [
        f"device-id: bench-device-001",
        f"client-id: bench-client-{run_idx}",
    ]
    if headers_extra:
        headers += headers_extra

    ws = websocket.create_connection(
        url,
        header=headers,
        timeout=10,
    )
    events = []

    t0 = time.monotonic()

    def log(label, **extra):
        ms = stamp_ms(t0)
        ev = {"t_ms": round(ms, 1), "label": label}
        ev.update(extra)
        events.append(ev)

    log("ws_open", url=url)

    frame_queue: "queue.Queue" = queue.Queue()
    stop_drain = threading.Event()

    def drain_loop():
        ws.settimeout(0.05)
        while not stop_drain.is_set():
            try:
                opcode, data = ws.recv_data()
                frame_queue.put((time.monotonic() - t0, opcode, data))
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break

    drain_thread = threading.Thread(target=drain_loop, daemon=True)
    drain_thread.start()

    ws.send(json.dumps(HELLO))
    log("hello_sent")

    welcome = None
    first_audio_at = None
    tts_started_at = None
    tts_stopped_at = None
    mcp_init_seen = None
    mcp_tools_list_recv_at = None
    tools_ready_at = None

    try:
        end_deadline = t0 + args.per_run_timeout
        while True:
            if time.monotonic() > end_deadline:
                log("timeout")
                break

            try:
                t_recv, opcode, data = frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if opcode == 0x2:  # binary
                if first_audio_at is None:
                    first_audio_at = t_recv
                    log("first_audio_frame", bytes=len(data))
                continue

            try:
                msg = json.loads(data)
            except Exception:
                continue
            mtype = msg.get("type")

            if mtype == "hello" and welcome is None:
                welcome = msg
                ws.send(
                    json.dumps(
                        {
                            "session_id": welcome.get("session_id", session_id),
                            "type": "listen",
                            "state": "detect",
                            "text": WAKEUP_TEXT,
                        }
                    )
                )
                ws.send(json.dumps({"type": "listen", "state": "start", "mode": "auto"}))
                log("welcome_recv", session_id=welcome.get("session_id"))

            elif mtype == "tts":
                state = msg.get("state")
                if state == "start" and tts_started_at is None:
                    tts_started_at = t_recv
                    log("tts_start", text=msg.get("text"))
                if state == "stop":
                    tts_stopped_at = t_recv
                    log("tts_stop")

            elif mtype == "stt":
                log("stt", text=msg.get("text", "")[:40])

            elif mtype == "mcp":
                payload = msg.get("payload") or {}
                method = payload.get("method")
                req_id = payload.get("id")
                if method == "initialize":
                    mcp_init_seen = t_recv
                    log("mcp_init_recv", id=req_id)
                    ws.send(json.dumps(mcp_init_response(req_id)))
                    log("mcp_init_resp_sent")
                elif method == "tools/list":
                    mcp_tools_list_recv_at = t_recv
                    log("mcp_tools_list_recv", id=req_id)
                    ws.send(json.dumps(mcp_tools_response(req_id)))
                    log("mcp_tools_list_resp_sent")
                    tools_ready_at = t_recv
            elif mtype == "llm":
                log("llm", text=(msg.get("text", "") or "")[:40])

            if (
                first_audio_at is not None
                and mcp_init_seen is not None
                and mcp_tools_list_recv_at is not None
                and tools_ready_at is not None
                and (time.monotonic() - t0) > 0.6
            ):
                log("grace_period_enter")
                break

    finally:
        stop_drain.set()
        try:
            ws.close()
        except Exception:
            pass

    t_hello_to_first_audio = first_audio_at
    t_hello_to_tools_ready = tools_ready_at
    return {
        "run": run_idx,
        "ok": first_audio_at is not None and tools_ready_at is not None,
        "t_hello_to_first_audio_ms": round(t_hello_to_first_audio * 1000, 1)
        if t_hello_to_first_audio is not None
        else None,
        "t_hello_to_tools_ready_ms": round(t_hello_to_tools_ready * 1000, 1)
        if t_hello_to_tools_ready is not None
        else None,
        "events": events,
    }


def _percentile(vals, q):
    """线性插值百分位（与 numpy 默认 method 一致）。"""
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    if n == 1:
        return s[0]
    k = (n - 1) * q
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return s[f]
    return s[f] + (k - f) * (s[c] - s[f])


def summarize(name, vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        print(f"  {name}: no samples")
        return
    p50 = _percentile(vals, 0.5)
    p95 = _percentile(vals, 0.95)
    print(
        f"  {name}: n={len(vals)} min={min(vals):.0f} "
        f"p50={p50:.0f} p95={p95:.0f} max={max(vals):.0f} ms"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--url", type=str, default="ws://localhost:8000/xiaozhi/v1/")
    ap.add_argument("--per-run-timeout", type=float, default=15.0)
    ap.add_argument("--save-events", type=str, default=None)
    args = ap.parse_args()

    print(f"# Handshake bench (async drain) — {args.runs} runs against {args.url}")
    results = []
    audio_samples = []
    tools_samples = []
    for i in range(args.runs):
        print(f"\n--- run {i + 1}/{args.runs} ---")
        r = run_one(args.url, i, args)
        results.append(r)
        if r["ok"]:
            audio_samples.append(r["t_hello_to_first_audio_ms"])
            tools_samples.append(r["t_hello_to_tools_ready_ms"])
            print(
                f"  hello→first_audio: {r['t_hello_to_first_audio_ms']:.0f} ms | "
                f"hello→tools_ready: {r['t_hello_to_tools_ready_ms']:.0f} ms"
            )
        else:
            print(f"  FAILED — first_audio={r['t_hello_to_first_audio_ms']}, "
                  f"tools_ready={r['t_hello_to_tools_ready_ms']}")

    print("\n## Summary")
    summarize("t_hello_to_first_audio_ms", audio_samples)
    summarize("t_hello_to_tools_ready_ms", tools_samples)

    if args.save_events:
        with open(args.save_events, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nEvents saved to {args.save_events}")


if __name__ == "__main__":
    main()
