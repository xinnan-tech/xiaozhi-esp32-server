"""真设备 WS 交互模拟(在 server 容器内跑,连本地真 server)

模拟 lebot/设备:WS 连真 server(xiaozhi-esp32-server 容器),带 X-External-Speaker header,
发 hello / listen start / {type:speaker} / opus 音频帧 / listen stop,看 server 真实跑通
ASR(讯飞)→ handle_voice_stop(external 分支用 proxy_speaker)→ LLM → 回复。

opus 音频:用容器内 ffmpeg + opuslib 把一段 wav 编码成 opus 帧。

运行(容器内):docker exec xiaozhi-esp32-server python3 /tmp/test_ws_device_simulation.py
"""
import asyncio
import json
import subprocess

import opuslib_next
import websockets

WAV = "/opt/xiaozhi-esp32-server/config/assets/wakeup_words_short.wav"
WS_URL = "ws://localhost:8000/xiaozhi/v1/"
DEVICE_ID = "02:1e:b0:26:e2:63"  # 活跃真设备(回访医生 agent)
CLIENT_ID = "019ec960-0000-7000-8000-000000000001"
SPEAKER_FRAME = {"type": "speaker", "name": "张三", "relationship": "患者"}


def wav_to_opus_frames(wav_path):
    """wav → 16k mono pcm → opus 帧(每帧 60ms / 960 samples)"""
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-ar", "16000", "-ac", "1",
         "-f", "s16le", "/tmp/_in.pcm"],
        check=True, capture_output=True,
    )
    pcm = open("/tmp/_in.pcm", "rb").read()
    enc = opuslib_next.Encoder(16000, 1, opuslib_next.APPLICATION_VOIP)
    frame_size = 960
    frames = []
    for i in range(0, len(pcm), frame_size * 2):
        chunk = pcm[i:i + frame_size * 2]
        if len(chunk) < frame_size * 2:
            chunk += b"\x00" * (frame_size * 2 - len(chunk))
        frames.append(enc.encode(chunk, frame_size))
    return frames


async def main():
    opus_frames = wav_to_opus_frames(WAV)
    print(f"[client] 编码 {len(opus_frames)} 个 opus 帧(~{len(opus_frames)*60}ms)")

    headers = {"device-id": DEVICE_ID, "client-id": CLIENT_ID, "X-External-Speaker": "1"}
    async with websockets.connect(WS_URL, additional_headers=headers) as ws:
        # hello
        await ws.send(json.dumps({
            "type": "hello",
            "audio_params": {"format": "opus", "sample_rate": 16000,
                             "channels": 1, "frame_duration": 60},
        }))
        try:
            print("[client] hello ack:", (await asyncio.wait_for(ws.recv(), 5))[:200])
        except asyncio.TimeoutError:
            print("[client] 无 hello ack")

        # listen start + speaker 帧
        await ws.send(json.dumps({"type": "listen", "state": "start"}))
        await ws.send(json.dumps(SPEAKER_FRAME))
        print(f"[client] 发送 speaker 帧: {SPEAKER_FRAME}")

        # 发 opus 音频帧(模拟说话,60ms/帧,接近实时)
        for f in opus_frames:
            await ws.send(f)
            await asyncio.sleep(0.06)
        print(f"[client] 发完 {len(opus_frames)} 个音频帧")

        # listen stop
        await ws.send(json.dumps({"type": "listen", "state": "stop"}))
        print("[client] 发 listen stop,等 server 回复...")

        # 收 server 回复(JSON 控制帧;二进制是 TTS 音频)
        for _ in range(60):
            try:
                msg = await asyncio.wait_for(ws.recv(), 10)
                if isinstance(msg, str):
                    data = json.loads(msg)
                    t = data.get("type")
                    if t == "stt":
                        print(f"[server] STT 识别: {data.get('text','')}")
                    elif t == "tts":
                        print(f"[server] TTS state={data.get('state')}")
                    elif t == "llm":
                        print(f"[server] LLM: {str(data)[:300]}")
                    else:
                        print(f"[server] {t}: {str(data)[:200]}")
            except asyncio.TimeoutError:
                print("[client] recv 超时,结束")
                break
            except websockets.exceptions.ConnectionClosed:
                print("[client] 连接关闭")
                break


if __name__ == "__main__":
    asyncio.run(main())
