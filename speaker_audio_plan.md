# Speaker 信息传入音频链路的方案

## 背景

le-bot 的 VirtualDeviceProxy 需要将说话人身份传入 xiaozhi-server 的 WebSocket 聊天接口（`ws://.../xiaozhi/v1/`）。目前二进制音频帧（Opus）只携带音频数据，不带任何元信息。

## 现有链路

```
二进制音频 → asr_audio_queue → VAD → handle_voice_stop()
                                            ├─ ASR → raw_text
                                            └─ Voiceprint → speaker_name
                                                    ↓
                                  _build_enhanced_text(raw_text, speaker_name)
                                               ↓
                        {"speaker": "张三", "content": "你好"}
                                               ↓
                                  startToChat(conn, enhanced_text)
                                    ↓ 解析 JSON，提取 speaker
                               conn.current_speaker = "张三"
                                    ↓
                                  chat() → dialogue.put()
                                               ↓
                               LLM prompt 中可见说话人
```

## 关键发现

1. `current_speaker` 在 `connection.py:157` 定义，初始为 `None`
2. voiceprint **不启用时**，`handle_voice_stop()` 的 `speaker_name` 为 `None`，speaker 丢失
3. `startToChat` 第 63-65 行：无 speaker 时主动设 `conn.current_speaker = None`，会覆盖外部值
4. listen 消息目前不处理 `speaker` 字段

## 改动方案（3 处修改）

### ① `listenMessageHandler.py`

在 `handle()` 开头（`mode` 处理之后）添加 speaker 接收：

```python
if "speaker" in msg_json:
    conn.current_speaker = msg_json["speaker"]
```

覆盖 `start` / `stop` / `detect` 所有分支。

### ② `asr/base.py` `handle_voice_stop()`

voiceprint 识别后，增加 fallback 到显式 speaker：

```python
speaker_name = voiceprint_result
if not speaker_name and conn.current_speaker:
    speaker_name = conn.current_speaker
```

### ③ `receiveAudioHandle.py` `startToChat()`

移除无 speaker 时清除 `current_speaker` 的逻辑：

```python
if speaker_name:
    conn.current_speaker = speaker_name
# 移除 else: conn.current_speaker = None
```

## le-bot 用法

```python
# 发音频前先发一条 JSON
await ws.send(json.dumps({
    "type": "listen",
    "state": "start",
    "speaker": "张三"
}))
# 然后发二进制音频帧
await ws.send(audio_frame)
```

## 优先级

| 场景 | speaker_name 结果 |
|------|-------------------|
| 有声纹且识别成功 | 声纹结果（最高优先级） |
| 声纹失败/未启用，但有显式 speaker | 显式传入的 speaker |
| 两者都没有 | `None`（纯文本，原行为） |

## 涉及文件

- `main/xiaozhi-server/core/handle/textHandler/listenMessageHandler.py`
- `main/xiaozhi-server/core/providers/asr/base.py`
- `main/xiaozhi-server/core/handle/receiveAudioHandle.py`
