# 语音进语音出（S2S）provider 使用教程

## 概述

原版链路是 VAD → ASR → 文字 LLM → TTS 的级联：一问一答，模型说话时不能插嘴。S2S（speech-to-speech）provider 把中间那一格换成一个
自己判轮次、自己出声、能被打断的实时语音模型，比如 OpenAI Realtime。设备固件和协议完全不变，服务器的工具、记忆、OTA、
白名单也照用。

目前自带的 provider：

| 名称 | type | 传输 | 说明 |
|---|---|---|---|
| OpenAIRealtime | `openai_realtime` | WebSocket 直连 `wss://api.openai.com/v1/realtime` | 平台 API key；模型侧 server_vad / semantic_vad 判轮次；真机说完约 0.5～1.2 秒出声，可以开口打断 |

## 工作原理

```
设备 Opus ──▶ connection._route_message 解成 PCM ──▶ provider.on_pcm ──▶（残余回声门控）──▶ 16 k → 24 k ──▶ 模型
模型音频  ──▶ provider ──▶ 24 kHz 60 ms Opus ──▶ 上游节拍器 sendAudio ──▶ 设备（tts start / sentence_start / stop 照发）
模型转写  ──▶ stt / tts sentence_start 给设备显示；写进 conn.dialogue，连接关闭时由记忆模块照常保存
工具      ──▶ Intent=function_call 的统一工具处理器（服务端插件 / server_mcp / 设备 MCP / MCP 接入点）
打断      ──▶ 设备 abort、模型侧 VAD 检到用户开口、本地门控连续几帧判为人声 → handleAbortMessage → provider.cancel
            （丢掉未发的帧、取消模型回复、把模型上下文截到设备实际播到的位置）
```

选中 S2S 的连接不再初始化 TTS 和 ASR；上游会话在握手时建立（限时 `connect_timeout_s`），建不成就自动回退到原版级联，
同一条连接、设备无感。模型最后一次出声回答之后 `idle_close_s` 秒没有新回答，连接关闭，设备回待机。

改动的上游文件只有 4 个、五处小钩子：`core/connection.py`（`self.s2s`、`_route_message` 入队前分流、`_initialize_components` 跳过 TTS / ASR、
`close()` 关上游会话）、`core/handle/abortHandle.py`、`core/handle/receiveAudioHandle.py` 的 `startToChat`、
`core/handle/textHandler/listenMessageHandler.py`（维护 `conn.client_is_listening`：`listen start` 之前的唤醒词音频不送模型）。
其余都在 `core/providers/s2s/` 和 `core/utils/s2s.py`。

## 接口规范（写一个新 provider）

目录与 LLM / TTS 相同：`core/providers/s2s/<type>/<type>.py`，类名 `S2SProvider`，继承 `core/providers/s2s/base.py` 的 `S2SProviderBase`：

| 方法 | 何时被调 | 要做什么 |
|---|---|---|
| `open()` | 连接初始化（执行器线程经 `attach_s2s` 调度到事件循环，限时） | 建上游会话；抛异常 = 失败，连接回退级联 |
| `after_components_ready()` | 原版把提示词增强、工具处理器建好之后（执行器线程） | 把 `conn.prompt` 与 `conn.func_handler.get_functions()` 同步给上游 |
| `on_pcm(pcm16k)` | 每收到一帧设备音频（16 kHz 单声道 PCM，60 ms） | 送给模型 |
| `on_text(text)` | 唤醒词 detect、文字消息、结束语 | 作为用户输入交给模型；唤醒词是固定的 `嘿，你好呀` |
| （读）`conn.client_is_listening` | 上游 listen 处理器在 start / stop 时维护 | `on_pcm` 据此决定送不送模型；provider 建成常晚于 listen start，所以状态记在连接上 |
| `cancel(reason)` | 打断（`device` 来自设备按键；模型侧 / 本地由 provider 自己发起） | 丢帧、取消、截断 |
| `close()` | 连接关闭 | 收尾 |

下行请用基类里的 `DeviceSpeaker`：`begin()`（一条新回复）、`push(pcm)`（模型音频）、`end()`（回复结束，等设备播完再发 stop）、
`interrupt()`、`played_ms()`（设备大约播到了哪，截断用）。它走上游现成的 `AudioRateController`，前 5 帧直接发当缓冲，之后 60 ms 一帧。

工具接线请用 `core/providers/s2s/tools.py`：`to_realtime_tools()` 把工具清单拍平，`ToolRunner.run(name, arguments)` 执行并翻成文字，
白名单、限频、request_id 日志都在里面。

## 配置指南

### 方式 1：配置文件（单模块部署）

`data/.config.yaml`：

```yaml
selected_module:
  S2S: OpenAIRealtime        # 不填或留空 = 原版级联
  Intent: function_call      # 工具要走统一工具处理器
  # VAD / LLM / TTS / ASR 照常配置：S2S 握手失败会回退到它们

S2S:
  OpenAIRealtime:
    type: openai_realtime
    api_key: 你的OpenAI平台密钥
    model_name: gpt-realtime
    voice: marin
    turn_detection: server_vad   # 或 semantic_vad
    vad_silence_ms: 400
    idle_close_s: 45
    echo_gate: true
    local_barge: true
```

所有项的说明见 `config.yaml` 的 `S2S:` 块。

### 方式 2：智控台（全模块部署）

暂不支持，智控台没有 S2S 这一类模块；全模块部署请在 `data/.config.yaml` 里按方式 1 配置，`selected_module.S2S` 会生效。

### 残余回声门控

设备端 AEC 之后，播放期间上行仍会漏一点与播放内容相关的回声；模型侧 VAD 会把它当成用户开口，模型播到半秒就被自己打断、
再接着回答自己的回声。`echo_gate: true` 时 provider 用自己发出的音频当参考，按滞后与回传比把回声帧换成舒适噪声，人声放行。
它复用 `selected_module.VAD` 的 silero onnx 模型；模型不在时只用能量判据。实测只有设备 AEC、不开门控的场景能不能稳，
建议先开着，再按日志里的 `gate` 统计决定。

## 附录：Mock 测试

`tests/core/providers/s2s/` 里有一个假的 Realtime WebSocket 服务端（`test_openai_realtime.py`），按脚本发事件、断言 provider
对上游和对设备分别发了什么；`tests/core/handle/test_s2s_slot.py` 用假 provider 验证四处钩子。都不出网、不用真 key：

```bash
cd main/xiaozhi-server
pytest tests/core/providers/s2s tests/core/handle/test_s2s_slot.py -q
```

真机验收四项：唤醒后握手、语音控制工具（如 `hass_state` 开灯）、模型说话时插话、把 `api_key` 改错后设备无感回退到级联。
