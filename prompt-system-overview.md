# 小智 server 提示词系统梳理

> 日期:2026-07-12
> 范围:`main/xiaozhi-server`(Python)运行时构建并发送给 LLM 的全部提示词
> 目的:理清每段提示词的来源、静态/动态属性,为 speaker 注入改造提供准确的注入点依据。所有结论均附 `文件:行号`,可直接核对。

---

## 0. 一张图:LLM 实际收到的消息序列

每次 `chat()`(`connection.py:~960`)调 LLM 前,`Dialogue.get_llm_dialogue_with_memory()`(`dialogue.py:94`)构建如下消息列表(从上到下发给 LLM):

```
┌─ ① 静态 system ──────────────────────── 缓存前缀(连接期间不变) ─┐
│  渲染后的 agent-base-prompt.txt(人设 + 规则 + <context> 静态部分)│
└──────────────────────────────────────────────────────────────┘
┌─ ② few-shot(is_temporary)────────────── 缓存前缀 ──────────────┐
│  工具调用正/负样本(仅 function_call 模式)                      │
└──────────────────────────────────────────────────────────────┘
┌─ ③ 半稳定 system ─────────────────────── 当天不变 ──────────────┐
│  日期 / 位置 / 天气 + <schedule> 当天日程                       │
└──────────────────────────────────────────────────────────────┘
┌─ ④ 实时 user ─────────────────────────── 每轮变 ────────────────┐
│  当前时间 / <memory> 记忆 / <speakers_info> 全员名单            │
└──────────────────────────────────────────────────────────────┘
┌─ ⑤ 真实对话历史 ───────────────────────────────────────────────┐
│  历轮 user / assistant / tool(含 tool_calls 补全)              │
└──────────────────────────────────────────────────────────────┘
```

**设计意图**(`dialogue.py` 注释):前三段是缓存前缀(命中 LLM provider 的 prefix cache),④⑤ 是变化部分。把"当天不变"和"每轮变"拆开,是为了让缓存前缀尽可能长。

---

## 1. 静态系统提示词(①)

### 1.1 模板文件
- 文件:`main/xiaozhi-server/agent-base-prompt.txt`
- 加载:`PromptManager._load_base_template`(`prompt_manager.py:74`),按 `config["prompt_template"]` 路径,默认 `agent-base-prompt.txt`,缓存于 `CacheType.CONFIG`
- **结构(标签块)**:
  - 顶层角色定义(playful / expressive / empathetic AI)
  - `<identity>{{base_prompt}}</identity>` —— agent 人设
  - `<core_rules>` 5 条:直奔主题 / 包容 ASR 误差 / 语言统一(`{{language}}`)/ 提问克制 / 结束机制
  - `<anti_ai_smell>` 反 AI 套话
  - `<tts_format_constraints>` TTS 格式约束 + emoji 白名单 `{{emojiList}}`
  - `<tool_and_knowledge>` 工具调用规则
  - `<safety_compliance>` 安全合规
  - **`<speaker_recognition>` 说话人识别规则(详见 §5)**
  - `<context>` 动态上下文(变量,详见 §2)
  - `<memory></memory>` **空块** —— 记忆实际在 ④ 注入,这里只是占位

### 1.2 渲染过程
- `PromptManager.build_enhanced_prompt(user_prompt, device_id, client_ip)`(`prompt_manager.py:226`)
- 用 jinja2 `Template` 渲染,变量:
  - `base_prompt` = `config["prompt"]`(agent 人设,见 §1.3)
  - `current_time` = 字面量 `"{{current_time}}"` —— **故意留占位不填**,实际值由 dialogue 在 ④ 注入(时间实时变,不能固化进缓存前缀)
  - `today_date` / `today_weekday` / `lunar_date` = 当天日期
  - `local_address` / `weather_info` = 位置 / 天气(按 `client_ip` 缓存)
  - `dynamic_context` = 第三方上下文数据(见 §2.2)
  - `language` = TTS 语言(config 选的)
  - `emojiList` / `device_id` / `client_ip`
- 渲染结果缓存:`CacheType.DEVICE_PROMPT`,key = `device_prompt:{device_id}`(`prompt_manager.py:281`)

### 1.3 agent 人设 `config["prompt"]` 的来源
- 运行时:`ConnectionHandler._initialize_private_config_async`(`connection.py:669`)调 `get_private_config_from_api`(`config_loader.py:96`)
- → `get_agent_models(device_id, client_id, selected_module)`(`manage_api_client.py:171`)POST manager-api `/config/agent-models`
- 返回的 `private_config["prompt"]` → `self.config["prompt"]`(`connection.py:757`)
- **即:管理后台该 agent 的"系统提示词"字段**(manager-api 数据库 `agent.systemPrompt`)
- 用于两处:`get_quick_prompt`(快速初始化,`connection.py:498`)和 `build_enhanced_prompt`(增强,`connection.py:536`)

> 注:本仓库的模板文件是"英文角色定义 + 中文规则";agent 人设(`base_prompt`)由后台填,通常中文。

---

## 2. 动态上下文(进 ①③④)

### 2.1 `update_context_info`(`prompt_manager.py:188`)
连接初始化时(`_init_prompt_enhancement`,`connection.py:531`)同步拉取:
- 位置:`_get_location_info(client_ip)` —— IP 定位城市,缓存 `CacheType.LOCATION`
- 天气:`_get_weather_info(conn, location)` —— 调 `get_weather` 插件,缓存 `CacheType.WEATHER`
- dynamic_context:见 §2.2

### 2.2 `dynamic_context` 来源(`context_provider.py`)
- `config["context_providers"]`:一个列表,每项 `{url, headers}`
- **来源**:manager-api 下发的 agent 私有配置(App 端"编辑源/上下文源"页面,对应 `AgentDetail.contextProviders`)
- `ContextDataProvider.fetch_all(device_id)`:遍历每个 URL,带 `device-id` header 发 GET,把返回数据格式化成 `- **k:** v` 或 `- item`,拼成字符串
- **用途**:接入第三方实时数据(Home Assistant 设备状态、业务系统数据等)
- **注入点**:渲染进系统提示词的 `<context>` 块(`{{dynamic_context}}`)—— 属于 ① 静态(连接期间不变,因为只在初始化时拉一次)

### 2.3 缓存与"半稳定"拆分
- 系统提示词整体缓存 `device_prompt:{device_id}`
- 但 `dialogue.py` 又把 `<context>` 里的日期/位置/天气拆出来当 ③ 半稳定 system —— 这是为了让"当天不变的日期/位置/天气"留在缓存前缀里,而把"实时变的时间/记忆/说话人"放 ④(详见 §3)

---

## 3. dialogue 消息序列详解(`get_llm_dialogue_with_memory`,`dialogue.py:94`)

### 3.1 ① 静态 system
- `system_message.content`(= 渲染后的系统提示词)
- 按 `<context>` 标签拆:`static_part` = `<context>` 之前(人设+规则),`dynamic_part` = `<context>` 起
- `dialogue.append({system, static_part})`(`dialogue.py:119`)

### 3.2 ② few-shot(`_inject_tool_call_fewshot`,`connection.py:542`)
- 仅 `intent_type == "function_call"` 时
- 正样本(direct_answer 示例)+ 负样本(handle_exit_intent 示例),`is_temporary=True`
- 放在动态 system 之前(命中缓存前缀)

### 3.3 ③ 半稳定 system(当天不变)
- `dynamic_part` 去掉"当前时间"行、去掉 `<memory>` 块(这俩移到 ④)
- 保留:日期 / 位置 / 天气
- 追加 `<schedule>` 当天日程(`schedule_str`,`memory.get_today_schedule()`)
- `dialogue.append({system, semi_stable_part})`(`dialogue.py:182`)

### 3.4 ④ 实时 user(每轮变)
`realtime_parts`(`dialogue.py:132-186`):
- `当前时间:HH:MM`
- `<memory>{memory_str}</memory>` —— 记忆摘要
- `<speakers_info>全员名单</speakers_info>` —— `config["voiceprint"]["speakers"]` 解析(`id,name,description` → `- name:description`)
- `dialogue.append({user, "\n".join(realtime_parts)})`(`dialogue.py:186`)

### 3.5 ⑤ 真实对话历史
- `self.dialogue` 里非 temporary 的 user/assistant/tool 消息
- `_ensure_tool_calls_complete`(`dialogue.py:64`)补全被打断的悬空 tool_calls(防 LLM 400)

---

## 4. 各 Provider 的内部提示词(独立 LLM 调用,非主对话)

### 4.1 记忆总结(mem_local_short)
- `short_term_memory_prompt`(`mem_local_short.py:12`)—— "时空记忆编织者",把对话总结成 JSON 记忆结构(身份图谱 / 记忆立方 / 关系网络 / 待响应 / 高光语录)
- 触发:连接关闭时 `_save_and_close`(`connection.py:287`)异步存
- aipet / powermem:各自有提取/总结逻辑(向量检索 + 内部 prompt)

### 4.2 聊天标题/总结
- `generate_and_save_chat_title` / `generate_and_save_chat_summary`(`manage_api_client.py:210 / 198`)—— 在 manager-api 端生成,小智 server 只触发

### 4.3 意图识别
- `_initialize_intent`(`connection.py:853`),intent provider —— **本次未深读,待补**

### 4.4 ASR 增强文本
- `_build_enhanced_text`(`asr/base.py:181`)—— 把 speaker 塞进 `{"speaker":name,"content":text}` JSON,作为 user content

---

## 5. Speaker 专题(本次改造相关)

### 5.1 模板已定义 `<speaker_recognition>` 规则(`agent-base-prompt.txt:40`)
```
针对输入格式 {"speaker":"...", "content":"..."}（speaker=说话人名, content=文本）：
1. speaker 是具体名字 → 已识别身份,首次自然称呼,参考历史特点调整风格
2. speaker 是"未知说话人" → 不能提及 speakers_info 标签数据,自行判断是主人还是朋友
```
→ 现有设计**预期 speaker 通过 enhanced_text JSON(user content)传入**,模板规则配合。

### 5.2 当前 speaker 的现状(注入 / 存储点)
| 点 | 位置 | 作用 |
|---|---|---|
| enhanced_text JSON | `asr/base.py:181` `_build_enhanced_text` | 把 speaker 塞进 user content(配合模板 `<speaker_recognition>`) |
| `<speakers_info>` 全员名单 | `dialogue.py:144` 实时 user | config voiceprint 的**静态全员列表** |
| `conn.current_speaker` | `connection.py:157` 等 | **死字段**(写 5 处、读 0 处) |
| `VoiceprintProvider.identify_speaker` | `voiceprint_provider.py:140` | 小智自己识别(调外部 `/voiceprint/identify`) |

### 5.3 记忆按 `device_id`(主人记忆)
- `init_memory(role_id=self.device_id)`(`connection.py:816`)
- 记忆 = **这个设备主人的记忆**(一份,按 device 存)
- 不管谁说话都查同一份 → **非主人说话会"串"**(把主人记忆当非主人的)

---

## 6. 来源汇总表

| 提示词/数据 | 来源 | 静态/动态 | 注入点 |
|---|---|---|---|
| 角色定义 + 规则 | `agent-base-prompt.txt` | 静态 | ① system |
| agent 人设 | manager-api `agent.systemPrompt` | 静态(连接期) | ① `<identity>` |
| 语言 / emoji 白名单 | config TTS / 配置 | 静态 | ① |
| 日期 / 农历 | `current_time.py` | 半稳定(当天) | ①/③ |
| 位置 / 天气 | IP 定位 / `get_weather` | 半稳定(缓存) | ①/③ |
| dynamic_context | `context_providers` URL 列表(manager-api) | 半稳定(连接期) | ① `<context>` |
| few-shot | 硬编码(`_inject_tool_call_fewshot`) | 静态 | ② |
| 当天日程 | `memory.get_today_schedule()` | 半稳定(当天) | ③ `<schedule>` |
| 当前时间 | `datetime.now` | 动态(每轮) | ④ user |
| 记忆 memory_str | `memory.query_memory(query)` | 动态(每轮检索) | ④ `<memory>` |
| `<speakers_info>` 全员 | `config["voiceprint"]["speakers"]` | 静态(config) | ④ |
| 当前 speaker | enhanced_text JSON / current_speaker | 动态(每轮) | ⑤ user content |
| 真实对话 | `dialogue` 历史 | 动态 | ⑤ |

---

## 7. 对 speaker 注入改造的启示

1. **模板 `<speaker_recognition>` 已存在**,配合 enhanced_text JSON —— 现有注入路径是 work 的(JSON 进 user content,模板规则解析)
2. **改造选项 A(最小,顺应现有结构)**:沿用 enhanced_text,只改 `speaker_name` 来源(`external_vpr` 时取 `conn.proxy_speaker`)—— 模板规则不动
3. **改造选项 B(更结构化)**:在 ④ 实时 user 加 `<current_speaker>` 块(和 `<memory>`/`<speakers_info>` 并列),同时更新模板 `<speaker_recognition>` 规则 —— 更干净,但要动模板
4. **记忆串问题**:非主人不该用主人记忆 —— 需在 `chat()` 按 speaker 决定是否注入 `<memory>`(或标注"他人记忆")

---

## 8. 待深挖(本次未细读,标注诚实)
- intent provider 的 prompt(意图识别内部逻辑)
- `memory.get_today_schedule()` 的具体实现(日程来源)
- aipet / powermem 的提取/总结内部 prompt
- `correct_words`(替换词)注入点
- manager-api 端 `agent.systemPrompt` / `voiceprint` / `context_providers` 的数据库结构与下发格式
- `private_config` 里 `voiceprint` / `context_providers` 字段映射进 `self.config` 的具体行(本次 grep 只确认了 `prompt` 在 `connection.py:757`)

---

## 附录 A:完整提示词实例(多轮)

> 用一个家庭场景,把 §0 的 5 段消息序列填上真实内容,看 LLM 实际收到什么。**这是某一次 `chat()` 调用时,发给 LLM 的完整消息列表。**

### A.1 场景设定
| 项 | 值 |
|---|---|
| 设备 | 客厅音箱 `AA:BB:CC:DD:EE:FF`,agent = "小智家庭助手" |
| agent 人设 `config["prompt"]` | "你是小智,一个温暖幽默的家庭语音助手,服务于张三一家(爸爸张三、妈妈李四、儿子张小宝)。" |
| 位置 / 时间 | 北京 / 2026-07-12 星期日(农历六月十八)19:03 |
| 天气 | 晴 32°C |
| context_provider(Home Assistant) | 返回:客厅灯=开启、客厅温度=26°C |
| voiceprint 全员名单 `config["voiceprint"]["speakers"]` | `张三,爸爸,喜欢摇滚和吉他` / `李四,妈妈,在减肥` / `张小宝,儿子,6岁怕黑` |
| 主人记忆(按 `device_id`,张三的) | 喜欢摇滚 / 在学吉他 / 小宝怕黑 / 李四减肥 |
| 当天日程 | 19:00 全家看电影 |
| intent 模式 | function_call(带工具) |

### A.2 多轮用户输入(每轮的 `enhanced_text` = user content)
| 轮 | speaker | content | 小智回复(简) |
|---|---|---|---|
| 1 | 张三(主人) | 今天外面热吗? | ☀️热呢,北京今天32度,出门戴帽子。 |
| 2 | 李四(妈妈) | 把客厅灯关了 | [调 hass 工具] 💡好的李姐,客厅灯关好了~ |
| 3 | 张三 | 晚上几点看电影? | 🎬今晚7点全家看电影,我还记着呢~ |
| **4** | **张小宝(儿子)** | **给我讲个故事** | **(下面完整展示这一轮 LLM 收到的 prompt)** |
| 5 | 未知说话人(客人) | 你好 | 你好呀,我是小智,欢迎欢迎~ |

### A.3 第 4 轮(张小宝讲故事)LLM 收到的完整消息列表

> 下面 ①②③④⑤ 按顺序拼成 `messages` 数组发给 LLM。①②③ 是缓存前缀(几轮间不变),④⑤ 是本轮变化部分。

**① 静态 system**(`agent-base-prompt.txt` 渲染后):
```
You are a playful, expressive, empathetic, and highly emotionally intelligent
conversational AI assistant interacting through a smart voice device. ...

<identity>
你是小智,一个温暖幽默的家庭语音助手,服务于张三一家(爸爸张三、妈妈李四、儿子张小宝)。
</identity>

<core_rules>
1. 【直奔主题】... 2. 【包容ASR误差】... 3. 【语言统一】...中文...
4. 【提问克制】... 5. 【结束机制】...
</core_rules>

<anti_ai_smell>...</anti_ai_smell>

<tts_format_constraints>
... emoji 白名单:[😊 🤗 🎵 🎬 ☀️ 💡 🦊 🌙 🎸 👋] ...
</tts_format_constraints>

<tool_and_knowledge>
必须调工具:播放音乐→play_music | 控制设备→hass | 告别→handle_exit_intent
</tool_and_knowledge>

<safety_compliance>...</safety_compliance>

<speaker_recognition>
针对输入格式 {"speaker":"...", "content":"..."}:
1. speaker 是具体名字 → 已识别,首次自然称呼,参考其历史特点调整风格
2. speaker 是"未知说话人" → 不能提及 speakers_info,自行判断是主人还是朋友
</speaker_recognition>

<context>
【重要提示:以下信息已实时提供,无需调用工具查询】
- 当前时间:{{current_time}}          ← 故意留占位,实际值在 ④
- 今天日期:2026-07-12(星期日)
- 今天农历:六月十八
- 设备所在地:北京
- 本地未来天气:晴,32°C,东南风3级
- **客厅灯:** 开启                      ← dynamic_context(Home Assistant)
- **客厅温度:** 26°C                     ← dynamic_context
</context>

<memory>
</memory>                              ← 空块,真实记忆在 ④
```

**② few-shot**(`is_temporary`,仅 function_call 模式):
```
user: 给我讲个故事吧
assistant: [tool_call → direct_answer(response="好呀,你想听什么类型的?")]
tool: 已直接回复

user: 拜拜
assistant: [tool_call → handle_exit_intent(say_goodbye="再见,下次再聊~")]
tool: 退出意图已处理
assistant: 再见,下次再聊~
```

**③ 半稳定 system**(当天不变):
```
[system]
2026-07-12(星期日) / 农历六月十八 / 北京 / 晴 32°C
<schedule>
以下是用户近期的安排:
- 今晚 19:00 全家看电影《千与千寻》
</schedule>
```

**④ 实时 user**(每轮变,本轮):
```
[user]
当前时间:19:03
<memory>
- [2026-07-10] 张三喜欢摇滚乐,最近在学吉他
- [2026-07-08] 张小宝怕黑,睡觉要开小夜灯
- [2026-07-05] 李四在减肥,晚上不吃主食
</memory>
<speakers_info>
- 张三:爸爸,喜欢摇滚和吉他
- 李四:妈妈,在减肥
- 张小宝:儿子,6岁,怕黑
</speakers_info>
```

**⑤ 真实对话历史 + 当前轮**:
```
[user]      {"speaker":"张三","content":"今天外面热吗?"}          ← 轮1
[assistant] ☀️热呢,北京今天32度大晴天,出门记得戴帽子。
[user]      {"speaker":"李四","content":"把客厅灯关了"}            ← 轮2
[assistant] [tool_call → hass(turn_off, living_room_light)]
[tool]      已关闭
[assistant] 💡好的李姐,客厅灯关好了~
[user]      {"speaker":"张三","content":"晚上几点看电影?"}         ← 轮3
[assistant] 🎬今晚7点全家看电影,我还记着呢~
[user]      {"speaker":"张小宝","content":"给我讲个故事"}          ← 轮4(当前,等 LLM 回复)
```

**LLM 据此生成的回复(轮4)**:
```
🦊好呀小宝,给你讲个小狐狸找朋友的故事。从前有只小狐狸,它特别想交朋友,
就跑到森林里去找小兔子……要继续听吗?
```

### A.4 这个实例能看出的几件事

1. **speaker 是名字 → 个性化**:轮4 `speaker=张小宝`,LLM 按孩子风格讲故事(简短、随叫随停);还能用 `<speakers_info>` 里"6岁怕黑"调整内容。
2. **speaker 是"未知说话人" → 不泄露名单**:轮5 LLM 不喊名字、不念名单,自然招呼(模板 `<speaker_recognition>` 规则2 生效)。
3. **记忆"串"问题**:轮2 是李四说话,但 ④ `<memory>` 仍是**张三**的记忆(按 `device_id`)—— 这就是非主人会串的隐患,也是"主人走记忆、非主人加名字"要修的点。
4. **工具调用**:轮2 调 `hass` 关灯;轮1/3/4 不调工具(`<context>`/`<schedule>` 已有信息,模板规则"无需调用工具查询")。
5. **缓存前缀**:①②③ 在这 5 轮里几乎不变(只有 ④ 的"当前时间"和 ⑤ 的历史每轮变)—— 命中 LLM provider 的 prefix cache,省 token、降延迟。
6. **`current_time` 占位**:模板 `<context>` 里 `{{current_time}}` 是占位,真值"19:03"在 ④ 注入 —— 这样系统提示词能进缓存,不被每分钟变化的时间破坏。
