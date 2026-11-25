# 设备协议 E2E 模拟器（Device Protocol Simulator）

`performance_tester/performance_tester_device.py` 用真实设备协议（`hello` → `listen` → `opus` 音频帧 → `listen stop`）连接 xiaozhi-server，用于回归验证「设备说话后无反应」这类端到端问题：服务端到底有没有完成 ASR、有没有触发工具/大模型、有没有下发 TTS。

它不替代固件测试：不涉及麦克风/扬声器声学链路，也不验证固件看门狗与重连逻辑。需要真实麦克风/扬声器交互式多轮自测时，用同族的交互式模拟器 `performance_tester/device_simulator_tui.py`（见 `docs/device-simulator-tui.md`）。

## 快速开始

```bash
cd main/xiaozhi-server
pip install -r requirements.txt

# 1) 准备一段 16kHz / 单声道 / 16bit 的语音
ffmpeg -i question.mp3 -f s16le -ac 1 -ar 16000 /tmp/question.pcm
#    或直接使用 wav：--wav question.wav

# 2) 直接运行
python performance_tester/performance_tester_device.py \
  --url ws://127.0.0.1:8000/xiaozhi/v1/ \
  --device-id AA:BB:CC:DD:EE:FF \
  --pcm /tmp/question.pcm

# 或从菜单进入
python performance_tester.py
```

`--device-id` 必须是服务端已登记的设备（否则会进入绑定流程或拿不到智能体配置）。

## 认证

服务端 `server.auth.enabled=true` 时，必须携带 token，二选一：

| 方式 | 说明 |
|---|---|
| `--token <token>` | 直接使用设备 token（固件 NVS 里的值） |
| `--secret <auth_key>` | 用服务端 `auth_key` 现签 token，适合在服务器本机调试 |

也支持环境变量 `DEVICE_SIM_TOKEN` / `DEVICE_SIM_SECRET`。
注意：运行态配置可能来自管理端（`server:config` 缓存），与本地 `config.yaml` 不一致；以服务端实际返回的认证要求为准。

## 常用参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--url` | `ws://127.0.0.1:8000/xiaozhi/v1/` | 服务端 WebSocket 地址 |
| `--device-id` | 无（必填） | 设备 ID |
| `--client-id` | 随机 UUID | 客户端 ID（与 token 签名绑定） |
| `--pcm` / `--wav` | 无 | 输入音频（16k/mono/16bit） |
| `--tail-silence` | `1.0` | 语音结束后的静音秒数，用于触发服务端断句 |
| `--timeout` | `40` | 等待 TTS 结束的最长秒数 |
| `--json-out` | 无 | 结果写入 JSON 文件 |
| `--verbose` | 关 | 打印服务端其余消息 |

## 输出与退出码

运行结束打印一行汇总：

```json
{"stt": ["今天深圳的天气怎么样？"], "llm_msgs": 1, "tts_states": ["start", "sentence_start", "stop"], "tts_audio_frames": 395, "session": "..."}
```

- 退出码 `0`：收到非空识别结果，且收到 TTS 音频（PASS）
- 退出码 `2`：超时/认证失败/无识别或无音频（FAIL）

## 限制

- 只验证服务端链路；TTS 音频不解码、不校验音质。
- MCP 工具列表返回空（设备侧工具不可用），服务端插件（天气等）不受影响。
- 不是压测工具：单连接、单轮对话，帧按 60ms 实时发送。

---

# Device Protocol Simulator (English)

`performance_tester/performance_tester_device.py` connects to xiaozhi-server using the real device protocol (`hello` → `listen` → Opus frames → `listen stop`) to reproduce and verify end-to-end "device says something, server never responds" issues: did ASR produce text, did the tool/LLM run, did TTS audio come back?

It is **not** a firmware or acoustic test: microphone/speaker paths, watchdog and reconnect behavior are out of scope. For interactive multi-turn self-testing with a real microphone/speaker, use the TUI sibling `performance_tester/device_simulator_tui.py` (see `docs/device-simulator-tui.md`).

## Quick start

```bash
cd main/xiaozhi-server
pip install -r requirements.txt

# 16 kHz / mono / 16-bit audio
ffmpeg -i question.mp3 -f s16le -ac 1 -ar 16000 /tmp/question.pcm

python performance_tester/performance_tester_device.py \
  --url ws://127.0.0.1:8000/xiaozhi/v1/ \
  --device-id AA:BB:CC:DD:EE:FF \
  --pcm /tmp/question.pcm
```

`--device-id` must be a device already registered on the server.

## Authentication

When `server.auth.enabled=true`, supply a token with either `--token <token>` (the device token from firmware NVS) or `--secret <auth_key>` (sign a token locally, handy on the server host). Environment variables `DEVICE_SIM_TOKEN` / `DEVICE_SIM_SECRET` are also supported.

Note: the effective server config may come from the manager API (`server:config` cache) and differ from the local `config.yaml`; always follow what the running server enforces.

## Options

`--url`, `--device-id`, `--client-id`, `--pcm`/`--wav`, `--tail-silence` (default 1.0 s), `--timeout` (default 40 s), `--json-out`, `--verbose`.

## Result

A single JSON summary line is printed, e.g.:

```json
{"stt": ["What's the weather in Shenzhen today?"], "llm_msgs": 1, "tts_states": ["start", "sentence_start", "stop"], "tts_audio_frames": 395}
```

Exit code `0` = non-empty STT plus TTS audio; `2` = timeout/auth failure/no STT or no audio.

## Limitations

- Server-side path only; TTS audio is counted, not decoded or quality-checked.
- MCP device tools are reported as empty; server-side plugins (weather, etc.) still work.
- Single connection, single turn, 60 ms real-time pacing — not a load generator.
