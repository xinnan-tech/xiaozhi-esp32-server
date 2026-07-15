# 外部 Speaker 注入(lebot 代理)— 设计文档

- **日期**:2026-07-12
- **范围**:仅 `main/xiaozhi-server` 侧
- **方案**:A —— 沿用 `enhanced_text` JSON 注入,只换 speaker 来源
- **状态**:待用户审阅

> 配套文档:`prompt-system-overview.md`(现有提示词系统梳理)、`speaker-injection-flow.html`(端到端时序图)

---

## 1. 背景

lebot backend 作为设备(ESP32/App)与小智 server 之间的 WS 代理(`XiaozhiProxy`,`lebot/packages/backend/src/modules/xiaozhi/proxy.ts`),已用 VPR 在音频流式过程中识别说话人(person_id + 查 persons 表补全 name/relationship)。但识别结果**仅用于 lebot 本地的"打断门控"**(`_runVprInterruptCheck`),**从不传给小智 server**。

小智 server 因此不知道"当前这句话是谁说的":
- 若配了 `VoiceprintProvider`,会自己再识别一遍 —— 重复、可能打架、且 lebot 已有更准结果
- 若没配,完全不知道是谁

**目标**:让小智接收 lebot 已识别的 speaker,直接用,跳过自己的 `VoiceprintProvider`。

## 2. 目标 / 非目标

**目标**
- lebot 代理连接下,小智接收外部识别的 speaker,注入 LLM(走现有 `enhanced_text` 路径)
- 跳过小智自己的 `VoiceprintProvider`(避免双重识别)
- 直连设备路径零改动

**非目标(YAGNI,不做)**
- 不改 lebot 侧实现(由对方按 §10 协议对接)
- 不动 ASR / 下游注入链 / 系统提示词模板 / LLM 调用
- 不做 `confidence` 阈值过滤(字段保留备用)
- 不解决"短语音认人"(客户端 VPR 固有限制)
- **暂不碰记忆注入 / 主人非主人分流**(见 §9,作为后续可选扩展)

## 3. 现状(关键事实,均已核对代码)

### 3.1 speaker 消费的唯一时机
`handle_voice_stop`(`asr/base.py:84`),发生在 listen stop 或 server Silero VAD 静默≥1s 之后。
**所有 ASR 类型都汇聚到这一处**:
- 非流式:`base.py:76` `client_voice_stop=True` 且音频>15 帧 → handle_voice_stop
- doubao 流式自动模式:`doubao_stream.py:194/205/225/231` 调继承的 handle_voice_stop(识别到 definite 片段就触发,**早于 listen stop**)
- aliyun / aliyunbl / xunfei 流式:经 `super()` 回到 base.py:84

### 3.2 speaker 注入路径(现有,work 的)
```
handle_voice_stop
  → _build_enhanced_text(asr/base.py:181) → {"speaker":name,"content":text} JSON 字符串
  → startToChat(asr/base.py:174) → actual_text = 整段 JSON(receiveAudioHandle.py:56,不解析)
  → conn.chat(connection.py:907) → dialogue.put(user, content=JSON字符串)(connection.py:918)
  → get_llm_dialogue_with_memory → append({role:user, content:JSON字符串})(dialogue.py:48)
  → 发给 LLM
```
模型按模板 `<speaker_recognition>` 规则(`agent-base-prompt.txt:40`)理解这个 JSON 文本 —— **这是文本约定,不是 API 结构化 JSON**。

### 3.3 标记 / 字段
- `conn.current_speaker`:**死字段**(写 5 处、读 0 处),不影响,本 spec 不用它
- 现有 `VoiceprintProvider.identify_speaker`(`voiceprint_provider.py:140`):在 `handle_voice_stop` 里并发跑,结果作 speaker_name —— 本 spec 在 external 模式下跳过它

### 3.4 时序约束
- lebot VPR 需累积 ~900ms(15 帧)才出结果,识别完成即发 speaker 帧(通常早于 listen stop)
- doubao 自动模式 handle_voice_stop 来得更早(说话中途),speaker 帧时序更紧

## 4. 设计

### 4.1 协议契约(新)

lebot → 小智,新增**普通 JSON 文本帧**(`ws.send`,与现有 `abort` 帧同款):
```json
{ "type": "speaker", "person_id": "abc123", "name": "张三", "relationship": "爸爸", "confidence": 0.92 }
```
- **时机**:VPR 识别完成(`proxy.ts` `_runTurnOwnerRecognition` 拿到 person_id + 查库补 name/relationship)立即发,通常早于 listen stop
- **频率**:一轮最多一次
- **识别不出**(短语音 <15 帧)→ **不发**,小智侧超时 fallback
- `confidence`:带上但小智**暂不**做阈值过滤
- 路由:`_route_message`(`connection.py:351`)`isinstance(str)` → `handleTextMessage` → registry 按 `type` 分发

### 4.2 标记 lebot 代理连接
- WS 握手 header:**`X-External-Speaker: 1`**(lebot 握手已带 `Device-ID`/`Client-ID`/`Authorization`,加一个一致)
- 小智 `handle_connection`(`connection.py:198` 解析 headers,210 device_id 旁)加:
  ```python
  self.external_vpr_enabled = self.headers.get("x-external-speaker") == "1"
  ```
- 不用 URL 参数(留给现有 `?from=mqtt_gateway` 那套,不混)

### 4.3 新增 handler 接收
- `textMessageType.py`:加 `SPEAKER = "speaker"`
- 新建 `textHandler/speakerMessageHandler.py`(~10 行):
  ```python
  class SpeakerTextMessageHandler(TextMessageHandler):
      @property
      def message_type(self) -> TextMessageType:
          return TextMessageType.SPEAKER

      async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
          conn.proxy_speaker = msg_json
          conn.proxy_speaker_ready.set()
  ```
- `textMessageHandlerRegistry.py:24` `_register_default_handlers` 列表加 `SpeakerTextMessageHandler()`

### 4.4 `connection.py` 改动
- `__init__` 加 3 个字段:
  ```python
  self.external_vpr_enabled = False
  self.proxy_speaker = None
  self.proxy_speaker_ready = asyncio.Event()
  ```
- `handle_connection`:解析 header(见 4.2)
- `reset_audio_states`(`connection.py:1499`)加两行,确保每轮独立:
  ```python
  self.proxy_speaker = None
  self.proxy_speaker_ready.clear()
  ```

### 4.5 `handle_voice_stop` 改动(`asr/base.py:84`,核心,~8 行)
**只改 `speaker_name` 的来源分支**,下游 `_build_enhanced_text → startToChat → chat` 一行不动:
```python
if conn.external_vpr_enabled:
    # 信任外部 speaker,跳过自己的 VoiceprintProvider
    try:
        await asyncio.wait_for(conn.proxy_speaker_ready.wait(), timeout=0.3)
    except asyncio.TimeoutError:
        pass
    speaker_name = conn.proxy_speaker.get("name") if conn.proxy_speaker else "未知说话人"
else:
    # 现状不变:自己的 VoiceprintProvider 识别(若有)
    ...  # 现有 identify_speaker 并发逻辑保持
```
覆盖所有 ASR 类型(都汇聚 base.py:84)。

### 4.6 fallback

| 场景 | speaker 帧到达时机 | 小智处理 |
|---|---|---|
| 正常(说话 ≥900ms) | 说话中途,早于 handle_voice_stop | `wait` 立即返回,**零等待** |
| 帧数够、VPR/网络慢 | 晚于 handle_voice_stop 几百 ms | `wait_for(0.3s)` 窗口接住 |
| 短语音(<900ms) | 永不到(lebot 不发) | 超时 → **"未知说话人"** |
| doubao 自动模式(handle_voice_stop 早) | 时序紧 | `wait 0.3s`;0.3s 是调参点 |

**不** fallback 到小智自己的 `VoiceprintProvider`(双重识别、慢、短语音也不靠谱)。

## 5. 数据流(端到端,详见 `speaker-injection-flow.html`)

```
设备 ──opus 实时流──> lebot(透传 + 旁路攒 VPR)
                        │攒满 15 帧 → VPR → person_id + 查库
                        │ ws.send({type:"speaker",...})   ← 说话中途
设备 ──listen stop──> lebot ──透传──> 小智
                                         handle_voice_stop
                                           external_vpr_enabled? → wait proxy_speaker
                                           speaker_name = name(或"未知")
                                           → _build_enhanced_text → startToChat → LLM
```

## 6. 改动文件清单(仅小智 server)

| 文件 | 改动 | 行数 |
|---|---|---|
| `core/connection.py` | 3 字段 + header 解析 + `reset_audio_states` 清理 | ~8 |
| `core/handle/textMessageType.py` | `SPEAKER` 枚举 | 1 |
| `core/handle/textMessageHandlerRegistry.py` | 注册 handler | 1 |
| `core/handle/textHandler/speakerMessageHandler.py` | **新增** | ~10 |
| `core/providers/asr/base.py` `handle_voice_stop` | `speaker_name` 来源分支 | ~8 |
| 下游:`_build_enhanced_text` / `startToChat` / `chat` / 模板 | **不动** | 0 |
| 直连设备路径(`external_vpr_enabled=False`) | **不动** | 0 |

## 7. 已知限制
- **短语音(<~1s)认不出人** → "未知说话人"。这是客户端 VPR 固有限制(样本太少),要解决得改 lebot 的 `VPR_MIN_FRAMES`,不是小智侧能救的。
- **doubao 自动模式**下 handle_voice_stop 来得早,speaker 帧命中率可能偏低;`0.3s` 超时是实现调参点(可按线上 ASR 类型调整)。
- **记忆仍按 `device_id` 注入**(主人记忆);非主人说话会用主人记忆(串)—— **本 spec 不修**,见 §9。

## 8. 测试策略
- **单元**
  - `SpeakerTextMessageHandler.handle`:正确写 `conn.proxy_speaker` + set event
  - `handle_voice_stop` 分支矩阵:`external_vpr_enabled` {True,False} × `proxy_speaker` {有值,无值,超时}
- **集成**:mock lebot(带 `X-External-Speaker` header + 发 speaker 帧 + 发音频)→ 验证 LLM 收到的 user content 含 `"speaker":"张三"`
- **回归**:直连设备(无 header)→ 行为完全不变(走现有 identify_speaker)
- **边界**:短语音(不发 speaker 帧)→ content 含 `"speaker":"未知说话人"`

## 9. 待定 / 可选扩展(本 spec 不含)

讨论中提及但**暂不做**(YAGNI,待后续按实际需求决定):
1. **记忆串修复**:非主人说话时不注入主人记忆(需改 `chat()` 的 memory 注入,按 speaker 决定)
2. **主人/非主人分流**:主人走记忆 + 非主人加名字(需"判断是不是主人"的映射:lebot `person_id` ↔ agent 主人)
3. **per-person 记忆**:`role_id` 从 `device_id` 换成 `person_id`(记忆系统重构)
4. **`confidence` 阈值过滤**:低于阈值当"未知"

> 这些若做,会扩大范围(碰 `chat()` 记忆注入、系统提示词模板),建议本 spec 先落地最小版,验证后再决定。

## 10. 对 lebot 侧的协议要求(对接清单,lebot 由对方实现)

- WS 握手加 header:`X-External-Speaker: 1`
- VPR 识别完成(`_runTurnOwnerRecognition` 拿到 person_id + 查 persons 表补 name/relationship 后)→ 立即:
  ```
  this._upstreamWs.send(JSON.stringify({
    type: "speaker", person_id, name, relationship, confidence
  }))
  ```
- 短语音(不足 15 帧、识别不出)→ **不发**(小智侧超时 fallback "未知说话人")
- 一轮最多发一次

---

## 附:设计决策记录
- **为何方案 A(不是 B/C)**:模板 `<speaker_recognition>`(`agent-base-prompt.txt:40`)已配合 `enhanced_text` JSON 约定 —— 沿用它零改动;方案 B(加 `<current_speaker>` 块)要改模板、方案 C(结构化注入)要改 dialogue 缓存分段,YAGNI。
- **为何 header 标记(不是 URL/配置)**:lebot 握手已带多个 header,加一个一致;URL 参数留给 mqtt_gateway;配置开关粒度不对。
- **为何不 fallback 到自识别**:external 模式的设计意图就是信任 lebot 的结果;短语音自识别也不准还慢;双重识别可能打架。
- **为何 `proxy_speaker` 用 `asyncio.Event` + 0.3s**:正常路径零等待(event 已 set),慢网络给窗口,短语音超时退化 —— 不阻塞 LLM 首字。
