# 音频流处理流程

```
设备 Opus 帧 → ws.send(binary) → asr_queue → VAD 逐帧检测
                                              ├─ 正在说 → 缓存到 asr_audio[]
                                              └─ 静默 1s → 批量 ASR 转文字
                                                            ↓
                                                  startToChat → chat() → LLM → TTS → 客户端
```
