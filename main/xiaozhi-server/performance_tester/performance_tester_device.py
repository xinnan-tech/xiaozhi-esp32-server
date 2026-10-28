"""设备协议 E2E 测试（hello / listen / opus 音频注入）

模拟 ESP32 设备走完整 WebSocket 协议链路：
    hello 握手 -> listen start -> opus 音频帧 -> listen stop
    -> 等待 stt / llm / tts 消息，输出端到端结果

用于回归验证「设备说话后无反应」类问题：可直接确认服务端是否完成
ASR 识别、是否调用工具/大模型、是否下发 TTS 音频。

用法（在 main/xiaozhi-server 目录下）：
    python performance_tester.py            # 按菜单选择
    python performance_tester/performance_tester_device.py \
        --url ws://127.0.0.1:8000/xiaozhi/v1/ \
        --device-id AA:BB:CC:DD:EE:FF \
        --pcm /tmp/question.pcm

认证（server.auth.enabled=true 时二选一）：
    --token <token>      直接使用设备 token（固件 NVS 中的值）
    --secret <auth_key>  用服务端 auth_key 现签 token（服务端本机调试方便）
    也可用环境变量 DEVICE_SIM_TOKEN / DEVICE_SIM_SECRET

音频准备（16kHz / 单声道 / 16bit）：
    ffmpeg -i question.mp3 -f s16le -ac 1 -ar 16000 question.pcm
    或直接传 16k 单声道 wav：--wav question.wav
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
import wave

import numpy as np
import opuslib_next
import websockets

# 直接运行本文件时（python performance_tester/performance_tester_device.py），
# 把 main/xiaozhi-server 加入 sys.path，保证 core.auth / config 可导入
_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

description = "设备协议 E2E 测试（hello/listen/opus 注入，验证 ASR->LLM->TTS）"

SAMPLE_RATE = 16000
FRAME_SAMPLES = 960          # 60ms @16k
DEFAULT_URL = "ws://127.0.0.1:8000/xiaozhi/v1/"


def _load_pcm(args) -> np.ndarray:
    if args.pcm:
        data = np.fromfile(args.pcm, dtype=np.int16)
        source = args.pcm
    elif args.wav:
        with wave.open(args.wav, "rb") as w:
            if w.getframerate() != SAMPLE_RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
                raise SystemExit(
                    f"{args.wav}: 需要 16kHz / 单声道 / 16bit wav，"
                    f"实际 {w.getframerate()}Hz/{w.getnchannels()}ch/{w.getsampwidth()*8}bit；"
                    "可先用 ffmpeg 转换"
                )
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        source = args.wav
    elif os.environ.get("DEVICE_SIM_PCM"):
        data = np.fromfile(os.environ["DEVICE_SIM_PCM"], dtype=np.int16)
        source = os.environ["DEVICE_SIM_PCM"]
    else:
        data = np.array([], dtype=np.int16)
        source = ""
    if data.size < FRAME_SAMPLES:
        raise SystemExit(f"音频不足一帧（{data.size} samples）：{source or '未提供 --pcm/--wav'}")
    return data


def _resolve_token(args) -> str:
    if args.token:
        return args.token
    if os.environ.get("DEVICE_SIM_TOKEN"):
        return os.environ["DEVICE_SIM_TOKEN"]
    secret = args.secret or os.environ.get("DEVICE_SIM_SECRET")
    if secret:
        from core.auth import AuthManager

        token = AuthManager(secret).generate_token(args.client_id, args.device_id)
        print("[device-sim] token=generated from auth_key")
        return token
    return ""


async def run(args) -> int:
    pcm = _load_pcm(args)
    token = _resolve_token(args)
    enc = opuslib_next.Encoder(SAMPLE_RATE, 1, "audio")
    dec = opuslib_next.Decoder(SAMPLE_RATE, 1)
    probe = enc.encode(pcm[:FRAME_SAMPLES].tobytes(), FRAME_SAMPLES)
    if len(np.frombuffer(dec.decode(probe, FRAME_SAMPLES), dtype=np.int16)) != FRAME_SAMPLES:
        raise SystemExit("opus 编解码自检失败（检查 opuslib_next 安装）")
    print(
        f"[device-sim] pcm={len(pcm)} samples / {len(pcm)/SAMPLE_RATE:.2f}s / "
        f"rms={int(np.sqrt(np.mean(pcm.astype(np.int64) ** 2)))}"
    )

    state = {"session": None, "stt": [], "llm": 0, "tts": [], "audio": 0, "closed": None}
    t0 = time.monotonic()

    def log(kind, **kw):
        detail = f" {json.dumps(kw, ensure_ascii=False)}" if kw else ""
        print(f"[device-sim] {time.monotonic()-t0:6.2f}s {kind}{detail}", flush=True)

    headers = {
        "Device-Id": args.device_id,
        "Client-Id": args.client_id,
        "Protocol-Version": "1",
    }
    if token:
        headers["Authorization"] = "Bearer " + token

    try:
        async with websockets.connect(args.url, additional_headers=headers, max_size=None) as ws:
            async def rx():
                async for raw in ws:
                    if isinstance(raw, bytes):
                        state["audio"] += 1
                        continue
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        if str(raw).strip():
                            print(f"[device-sim] server says: {str(raw)[:120]}")
                        continue
                    t = msg.get("type")
                    if t == "hello":
                        state["session"] = msg.get("session_id")
                        log("hello", session=state["session"])
                    elif t == "mcp":
                        payload = msg.get("payload") or {}
                        rid = payload.get("id")
                        if rid is not None:
                            if payload.get("method") == "initialize":
                                result = {
                                    "protocolVersion": "2024-11-05",
                                    "capabilities": {"tools": {}},
                                    "serverInfo": {"name": "device-simulator", "version": "1.0"},
                                }
                            else:
                                result = {"tools": []}
                            await ws.send(
                                json.dumps(
                                    {
                                        "session_id": state["session"],
                                        "type": "mcp",
                                        "payload": {"jsonrpc": "2.0", "id": rid, "result": result},
                                    },
                                    ensure_ascii=False,
                                )
                            )
                    elif t == "stt":
                        state["stt"].append(msg.get("text") or "")
                        log("stt", text=msg.get("text"))
                    elif t == "llm":
                        state["llm"] += 1
                        log("llm", emotion=msg.get("emotion"), text=(msg.get("text") or "")[:80])
                    elif t == "tts":
                        state["tts"].append(msg.get("state"))
                        log("tts", state=msg.get("state"), text=(msg.get("text") or "")[:60])
                    elif args.verbose:
                        log("msg", type=t, raw=json.dumps(msg, ensure_ascii=False)[:160])

            rx_task = asyncio.create_task(rx())
            await ws.send(
                json.dumps(
                    {
                        "type": "hello",
                        "version": 1,
                        "features": {"mcp": True},
                        "transport": "websocket",
                        "audio_params": {
                            "format": "opus",
                            "sample_rate": SAMPLE_RATE,
                            "channels": 1,
                            "frame_duration": 60,
                        },
                    },
                    ensure_ascii=False,
                )
            )
            log("hello_sent")
            await asyncio.sleep(0.6)
            await ws.send(
                json.dumps(
                    {"session_id": state["session"], "type": "listen", "state": "start", "mode": "auto"},
                    ensure_ascii=False,
                )
            )
            log("listen_start")

            next_at = time.monotonic()
            sent = 0
            for i in range(0, len(pcm) - FRAME_SAMPLES + 1, FRAME_SAMPLES):
                await ws.send(enc.encode(pcm[i:i + FRAME_SAMPLES].tobytes(), FRAME_SAMPLES))
                sent += 1
                next_at += 0.06
                delay = next_at - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
            log("frames_sent", n=sent)

            await asyncio.sleep(args.tail_silence)
            await ws.send(
                json.dumps(
                    {"session_id": state["session"], "type": "listen", "state": "stop", "mode": "auto"},
                    ensure_ascii=False,
                )
            )
            log("listen_stop")

            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                if state["tts"] and state["tts"][-1] == "stop":
                    break
                await asyncio.sleep(0.25)
            rx_task.cancel()
    except websockets.exceptions.InvalidStatus as e:
        print(f"[device-sim] 握手失败：{e}（检查 url / 反向代理）")
        return 2
    except websockets.exceptions.ConnectionClosed as e:
        print(f"[device-sim] 连接被关闭：{e}（若服务端开启认证，请用 --token/--secret）")
        if not state["stt"]:
            return 2

    summary = {
        "stt": state["stt"],
        "llm_msgs": state["llm"],
        "tts_states": state["tts"],
        "tts_audio_frames": state["audio"],
        "session": state["session"],
    }
    print("[device-sim] SUMMARY " + json.dumps(summary, ensure_ascii=False))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    ok = bool(state["stt"]) and state["audio"] > 0
    print("[device-sim] " + ("PASS" if ok else "FAIL: 未收到识别结果或 TTS 音频"))
    return 0 if ok else 2


def _interactive_defaults(args):
    if not args.device_id:
        args.device_id = os.environ.get("DEVICE_SIM_ID", "")
    if not args.device_id and sys.stdin.isatty():
        args.device_id = input("设备 Device-Id（如 AA:BB:CC:DD:EE:FF）：").strip()
    if not args.device_id:
        raise SystemExit("缺少 --device-id（或环境变量 DEVICE_SIM_ID）")
    if not args.pcm and not args.wav and sys.stdin.isatty() and not os.environ.get("DEVICE_SIM_PCM"):
        path = input("PCM 文件路径（16k/mono/s16le，留空则退出）：").strip()
        if not path:
            raise SystemExit("未提供音频文件")
        args.pcm = path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--url", default=os.environ.get("DEVICE_SIM_URL", DEFAULT_URL))
    p.add_argument("--device-id", default="")
    p.add_argument("--client-id", default=os.environ.get("DEVICE_SIM_CLIENT_ID") or str(uuid.uuid4()))
    p.add_argument("--pcm", help="16kHz/mono/s16le 裸 PCM 文件")
    p.add_argument("--wav", help="16kHz/mono/16bit wav 文件")
    p.add_argument("--token", default="", help="设备 token（auth.enabled=true 时）")
    p.add_argument("--secret", default="", help="服务端 auth_key，用于现签 token")
    p.add_argument("--tail-silence", type=float, default=1.0, help="语音后静音秒数（默认 1.0）")
    p.add_argument("--timeout", type=float, default=40.0, help="等待 TTS 结束的秒数（默认 40）")
    p.add_argument("--json-out", default="", help="把结果写入 JSON 文件")
    p.add_argument("--verbose", action="store_true")
    return p


async def main():
    args = build_arg_parser().parse_args()
    _interactive_defaults(args)
    return await run(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
