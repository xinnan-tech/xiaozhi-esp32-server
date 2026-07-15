# 聊天时传入 Speaker 信息 — 设计文档

## 背景

le-bot 前端在缓存用户音频输入后，在前端侧识别说话人身份。需要将说话人信息通过 WebSocket 传入 xiaozhi-server，使 LLM 能够感知当前说话人身份。

## 需求

- 客户端可在任意时刻声明当前说话人身份
- 长对话中说话人可多次切换，会话不中断
- 说话人信息需流入 ASR 识别结果，最终传入 LLM prompt
- 不影响现有音频流式传输协议

## 协议

### 新增消息类型：speaker

```
客户端 → {"type": "speaker", "name": "张三", "info": "孩子的爸爸"}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 说话人名称，用于识别 |
| `info` | 否 | 说话人附加信息，用于 LLM 理解角色背景 |

该消息可在 WebSocket 连接生命周期的任意时刻发送，无副作用。

### 音频传输不变

二进制 Opus 帧流仍按现有协议传输，不受 speaker 消息影响。

## 数据流

```
客户端
  ├─ {"type": "speaker", "name": "张三"}
  └─ [Opus frame 1] [frame 2] ... [frame N]
                                  ↓
                      VAD 检测静默 → handle_voice_stop()
                                        ├─ ASR → raw_text
                                        └─ 取 conn.current_speaker 作为 speaker_name
                                              ↓
                              _build_enhanced_text(raw_text, "张三")
                                              ↓
                            {"speaker": "张三", "content": "你好"}
                                              ↓
                                  startToChat → chat() → LLM
```

## 改动清单

### 1. `core/handle/textMessageType.py`

在 `TextMessageType` 枚举中新增：

```python
SPEAKER = "speaker"
```

### 2. 新建 `core/handle/textHandler/speakerMessageHandler.py`

- 实现 `TextMessageHandler` 接口
- 从 `msg_json` 提取 `name` 和可选的 `info`
- 存入 `conn.current_speaker` 和 `conn.current_speaker_info`

### 3. `core/handle/textMessageHandlerRegistry.py`

- 新增 import：`SpeakerTextMessageHandler`
- 在 `_register_default_handlers` 中注册

### 4. `core/providers/asr/base.py`

在 `handle_voice_stop()` 方法中，voiceprint 识别结果之后增加 fallback：

```python
speaker_name = voiceprint_result
if not speaker_name and conn.current_speaker:
    speaker_name = conn.current_speaker
```

优先级：voiceprint 识别结果 > 显式传入 > 无

### 5. `core/handle/receiveAudioHandle.py`

修改 `startToChat()` 函数，移除无 speaker 时清除 `current_speaker` 的逻辑：

```python
if speaker_name:
    conn.current_speaker = speaker_name
# 不再设置 conn.current_speaker = None
```

### 6. (可选) `core/utils/dialogue.py`

如果需要在 LLM prompt 中注入当前说话人信息，可在 `get_llm_dialogue_with_memory` 的实时部分追加 `conn.current_speaker`。当前 voiceprint 已有 speakers 列表注入，此改动视 LLM 行为需求而定。

## 兼容性

- 向后兼容：旧客户端不发送 speaker 消息，行为完全不变
- speaker 消息可随时发送：无状态依赖，不要求先发什么再发 speaker
- 退出逻辑：收到新 speaker 消息即覆盖旧值，无持久化需求

## 涉及文件

- `main/xiaozhi-server/core/handle/textMessageType.py`
- `main/xiaozhi-server/core/handle/textHandler/speakerMessageHandler.py` (新建)
- `main/xiaozhi-server/core/handle/textMessageHandlerRegistry.py`
- `main/xiaozhi-server/core/providers/asr/base.py`
- `main/xiaozhi-server/core/handle/receiveAudioHandle.py`
