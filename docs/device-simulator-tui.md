# 设备模拟器 TUI（交互式多轮自测）

`performance_tester/device_simulator_tui.py` 是 `performance_tester_device.py`（无头单轮）之外的**交互式**设备模拟器：Textual TUI 界面，走同一套协议 v1（`hello` → `listen` → Opus 60ms 帧），但带**本机真实音频**——麦克风 16k 采集、扬声器 48k 播放，支持多轮对话、打断、语料注入与逐轮时延面板。

引擎 `performance_tester/device_simulator.py` 与 TUI 共用，也可无头运行（见下）。

| 文件 | 作用 |
|---|---|
| `device_simulator.py` | 引擎：协议会话、Opus 编解码（PyAV libopus）、半双工互斥、数字注入、无头场景（baseline/swallowhunt/zombie/idle） |
| `device_simulator_tui.py` | Textual TUI 前端：逐轮回显 + L1-L5 时延面板 + 键位交互 |
| `phrases.txt` | 注入语料（每行一条，`#` 注释，`1-9` 映射前 9 条，`e` 键重载） |
| `prewarm_corpus.py` + `speak.ps1` | 语料预合成缓存（Windows SAPI 16k wav；装有 `edge-tts` 时优先用之） |
| `start_tui.cmd` / `start_tui.sh` | 双击/脚本启动器 |

## 快速开始

```bash
cd main/xiaozhi-server/performance_tester
pip install numpy sounddevice websockets av textual   # edge-tts 可选

# 预合成语料缓存（可选，仅 Windows；TUI 中按 1-9 也可实时合成）
python prewarm_corpus.py

# 启动 TUI（在支持 ANSI 的控制台运行）
python device_simulator_tui.py --device-id AA:BB:CC:DD:EE:FF
# Windows 双击 start_tui.cmd；Linux/macOS ./start_tui.sh
```

`--device-id` 须为服务端已登记设备；认证参数与 `performance_tester_device.py` 相同（`--token` / `--secret` / 环境变量 `DEVICE_SIM_TOKEN`）。

## 键位

| 键 | 动作 |
|---|---|
| `w` | 唤醒（建连 + `listen start`），之后直接对麦克风说话（auto 模式） |
| `space` | 打断：发 `{"type":"abort"}` + 本地立即停止播放/清队列（实证：`listen/state=abort` 服务端静默忽略，必须用 `type=abort`） |
| `m` | 麦克风开关 |
| `p` | 网络探针（WS ping RTT，10s 周期） |
| `e` | 重载 phrases.txt |
| `1-9` | 数字注入第 N 条语料（本地合成缓存 wav 直灌识别通道） |
| `+/-` | 播放音量 |
| `q` | 退出 |

## 内建行为

- **半双工互斥**：TTS 播放期间上行自动静默、播完清积压再放开——与真机半双工一致，从源头杜绝"扬声器回声被识别"（`--duplex` 可关闭，回声实验用）。
- **数字注入**：wav PCM 直灌麦克风队列（60ms 节拍、丢帧计数），绕过扬声器↔麦克风声学耦合差异，同一文件可反复注入得到确定性回归。
- **取证落盘**：`tui_*.jsonl` 全事件（含 ping RTT、1Hz RMS）；`rec/mic_*.pcm`（16k，实际发往服务端的内容）与 `rec/spk_*.pcm`（48k，扬声器实际播放内容）。
- **时延面板**：L1 唤醒→建连 / L2 说完→STT / L3 STT→首包 / L5 端到端（近 5 轮均值）。

## 引擎无头用法（回归脚本友好）

```bash
cd main/xiaozhi-server/performance_tester
# 多轮注入对话（--plays 不给时自动使用 phrases.txt 对应的预合成缓存）
python device_simulator.py --scenario baseline --device-id AA:BB:CC:DD:EE:FF \
    --plays "cache_xxxxxxxxxx.wav@1.0" --out log_baseline.jsonl
# 半开连接复现（需管理员权限，仅 Windows；从 --url 自动解析入口 IP）
python device_simulator.py --scenario zombie --device-id ... --out log_zombie.jsonl
```

场景：`baseline` 多轮注入 / `swallowhunt` 短句密集轮次 / `zombie` 半开连接与会话不收敛复现 / `idle` 静音保持观察。

## 限制

- 依赖本机音频设备与显示终端（TUI 需支持 ANSI）；服务器/容器内请用无头的 `performance_tester_device.py`。
- `zombie` 场景需要 Windows 管理员权限（netsh 防火墙）。
- 语料合成的 SAPI 兜底仅 Windows；`edge-tts` 受网络影响时用 `prewarm_corpus.py` 预合成。

---

# Device Simulator TUI (English)

`performance_tester/device_simulator_tui.py` is the **interactive** counterpart of `performance_tester_device.py` (headless, single turn): a Textual TUI speaking the same protocol v1 (`hello` → `listen` → Opus 60 ms frames) with **real local audio** — 16 k microphone capture, 48 k speaker playback, multi-turn conversation, interrupt, corpus injection and a per-turn latency panel.

The engine `performance_tester/device_simulator.py` is shared with the TUI and can also run headless (see below).

| File | Purpose |
|---|---|
| `device_simulator.py` | Engine: protocol session, Opus codec (PyAV libopus), half-duplex mutex, digital injection, headless scenarios (baseline/swallowhunt/zombie/idle) |
| `device_simulator_tui.py` | Textual TUI front-end: full per-turn transcript + L1-L5 latency panel + key bindings |
| `phrases.txt` | Injection corpus (one phrase per line, `#` comments; keys `1-9` map to the first 9, `e` reloads) |
| `prewarm_corpus.py` + `speak.ps1` | Pre-synthesize corpus cache (Windows SAPI 16 kHz wav; uses `edge-tts` when available) |
| `start_tui.cmd` / `start_tui.sh` | Launchers (double-click / shell script) |

## Quick start

```bash
cd main/xiaozhi-server/performance_tester
pip install numpy sounddevice websockets av textual   # edge-tts optional

python prewarm_corpus.py      # optional, Windows only

python device_simulator_tui.py --device-id AA:BB:CC:DD:EE:FF
# Windows: double-click start_tui.cmd; Linux/macOS: ./start_tui.sh
```

`--device-id` must be registered on the server; auth options are the same as `performance_tester_device.py` (`--token` / `--secret` / `DEVICE_SIM_TOKEN`).

## Key bindings

| Key | Action |
|---|---|
| `w` | Wake (connect + `listen start`); then just speak to the microphone (auto mode) |
| `space` | Interrupt: sends `{"type":"abort"}` and stops local playback immediately (verified: `listen/state=abort` is silently ignored by the server — `type=abort` is required) |
| `m` | Microphone on/off |
| `p` | Network probe (WS ping RTT every 10 s) |
| `e` | Reload phrases.txt |
| `1-9` | Digitally inject corpus phrase N (locally synthesized cache wav fed straight into the recognition channel) |
| `+/-` | Playback volume |
| `q` | Quit |

## Built-in behavior

- **Half-duplex mutex**: uplink is muted automatically while TTS plays and un-muted with a backlog flush after it ends — mirrors real-device half duplex and prevents "speaker echo being recognized" (`--duplex` disables it for echo experiments).
- **Digital injection**: wav PCM is fed straight into the microphone queue (60 ms pacing, audited drop counter), bypassing speaker↔microphone acoustic coupling differences; the same file can be re-injected for deterministic regression.
- **Forensics**: `tui_*.jsonl` full event log (ping RTT, 1 Hz RMS); `rec/mic_*.pcm` (16 k, what was actually sent) and `rec/spk_*.pcm` (48 k, what was actually played).
- **Latency panel**: L1 wake→connect / L2 speech-end→STT / L3 STT→first packet / L5 end-to-end (mean of last 5 turns).

## Headless engine usage (regression-friendly)

```bash
cd main/xiaozhi-server/performance_tester
python device_simulator.py --scenario baseline --device-id AA:BB:CC:DD:EE:FF \
    --plays "cache_xxxxxxxxxx.wav@1.0" --out log_baseline.jsonl
python device_simulator.py --scenario zombie --device-id ... --out log_zombie.jsonl   # admin required
```

Scenarios: `baseline` multi-turn injection / `swallowhunt` dense short utterances / `zombie` half-open connection & session non-convergence / `idle` silence holding.

## Limitations

- Needs a local audio device and an ANSI-capable terminal; inside servers/containers use the headless `performance_tester_device.py` instead.
- The `zombie` scenario requires Windows admin rights (netsh firewall).
- The SAPI corpus-synthesis fallback is Windows-only; pre-synthesize with `prewarm_corpus.py` when `edge-tts` is unreachable.
