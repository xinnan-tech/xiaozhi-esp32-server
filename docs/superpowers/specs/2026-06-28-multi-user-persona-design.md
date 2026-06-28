# 周期性按聊天主题匹配陪伴角色 — 设计文档

- 日期: 2026-06-28
- 状态: draft(待用户审阅)
- 范围: manager-api(Java,含定时任务 + LLM 调用);xiaozhi-server(Python)零改

## 1. 背景与目标

**产品**:儿童陪伴产品(B2C,面向大量家庭,每家一台孩子的小智设备)。
**需求**:有一个可扩充的**陪伴角色池**;根据每个孩子的**近期聊天主题**,为其匹配最合适的陪伴角色。不同孩子可能匹配到同一个角色(共享)。匹配周期性进行(默认每周一次),周期内角色固定;但**儿童场景下匹配要保守**(孩子依恋固定角色,频繁切换不利)。

**不加「适用场景」字段**:匹配直接用角色自己的 `system_prompt`(它本身即描述「这是个什么角色」),不新增字段、不改 `ai_agent` 表。

外部《动态匹配系统提示词技术方案报告》对原生能力的描述有多处失实(虚构 `UserContext`/`user_id` 透传/插件前置钩子/`ContextDataProvider` 写入式注入),本设计基于真实代码重做。

**本期规模**:几十 → 几百家庭/用户。

## 2. 真实代码基线(已逐一核实)

- **角色池 = `ai_agent`**:每个 agent 一段 `system_prompt`(角色设定);管理员可在智控台扩充。本期不新增字段。
- **设备归属用户**:`ai_device.user_id` 绑定时由当前登录用户填入(`DeviceServiceImpl:131/143`);设备查询/所有权校验均按 `user_id`(`:294/302/694/800`)。儿童设备通常由家长账号注册绑定;聊天内容是孩子的。
- **聊天内容可取**:`ai_agent_chat_history.content VARCHAR(1024)`,`chat_type`(1=用户/2=智能体),按 `mac_address`+`agent_id`+`session_id`+`created_at` 索引。经 `user → ai_device(mac_address) → chat_history` 聚合某孩子的聊天。
- **system prompt 解析**:`ConfigServiceImpl.getAgentModels(macAddress)` → `device → device.agent_id → agent → agent.getSystemPrompt()` → `result["prompt"]`;已有 `{{assistant_name}}` 替换先例。
- **manager-api 可直接调 LLM**:`OpenAIStyleLLMServiceImpl` 用 `RestTemplate` POST `/chat/completions`;`RestTemplateConfig` 提供 bean。
- **定时任务先例**:`modules/knowledge/task/DocumentStatusSyncTask.java`(`@Scheduled`),照此模式新增匹配任务。
- **Python 端**:`config["prompt"] = private_config["prompt"]`(`connection.py:758`)→ `build_enhanced_prompt`(`:535`)。**本期零改**。
- **记忆**:aipet 按 `role_id=device_id` 存;1 用户 1 设备 → 天然按用户隔离,本期零改。

## 3. 范围

**本期 IN**
- 可扩充陪伴角色池(复用 `ai_agent`,不加字段)。
- 周期性(默认每周)定时任务:按孩子近期聊天主题,用 LLM 匹配最合适角色,写入「用户→当前角色」映射。
- **儿童保守策略**:已匹配后倾向稳定,仅当另一角色「显著更合适」才切换(高阈值)。
- **家长手动切换**:家长可随时给孩子换角色(切换后标为「手动」,每周自动匹配让位、不再覆盖,直到家长点「恢复自动匹配」)。
- `getAgentModels` 使用该映射下发角色 system_prompt。
- 冷启动(新用户/历史不足)→ 默认角色(设备绑定 agent)。

**本期 OUT(v2+)**
- 每句话实时匹配(不做,避免人设突变)。
- 孩子画像采集(年龄/兴趣等,目前无;本期只用聊天主题)。
- 按用户知识库(RAG)、1 用户多设备记忆 rekey、按用户模型/TTS、计费。

## 4. 总体架构

```
【离线:每周一次的匹配任务】(manager-api @Scheduled)
  对每个未锁定、且有足够历史的孩子:
    user → 设备(mac) → ai_agent_chat_history(近 N 天,chat_type=1)
    → 拼「近期主题」+ 各候选角色的 system_prompt(角色描述)
    → LLM 选最合适角色(仅「显著更优」才换,否则保留当前)
    → 写 user_persona_assignment

【在线:对话路径】(零额外延迟)
  ESP32(MAC) → getAgentModels(mac)
    → device.user_id → user_persona_assignment.agent_id(无则回退 device.agent_id)
    → 该 agent.system_prompt → result["prompt"]
    → Python build_enhanced_prompt → LLM
```

对话路径不跑匹配,只用预先匹配好的结果 → 无延迟、不突变。

## 5. 组件

### 5.1 角色池(不加字段)
复用 `ai_agent`;每个陪伴角色的 `system_prompt` 本身即匹配依据(描述角色是谁、擅长什么)。候选集 = 所有 `system_prompt` 非空的角色。

### 5.2 信号采集
主信号:`ai_agent_chat_history.content`(孩子消息,近 N 天,N 默认 14,因儿童周期放宽)。
取数 SQL 思路:
```sql
SELECT h.content FROM ai_agent_chat_history h
JOIN ai_device d ON h.mac_address = d.mac_address
WHERE d.user_id = ? AND h.chat_type = 1
  AND h.created_at > [now - N days]
ORDER BY h.created_at DESC LIMIT [M];
```
增强信号(可选):复用 aipet 已抽取的孩子话题/事实;本期先用原始聊天内容。

### 5.3 定时匹配任务
- 新建 `PersonaMatchTask`(`@Scheduled`,默认每周一次),仿 `DocumentStatusSyncTask`。
- 跳过 `manual=1` 的用户(家长已手动设定,尊重其选择)。
- 对每个历史充足的用户:
  1. 取近期聊天内容 → 汇总「近期主题」。
  2. 候选角色 = system_prompt 非空的 agent。
  3. 调 LLM(走 `OpenAIStyleLLMServiceImpl`/RestTemplate):给定孩子主题 + 各候选角色 system_prompt + 当前角色,返回最合适角色 id + 置信度。
  4. **儿童高阈值切换**:仅当新角色置信度 ≥ 当前 + Δ(如 0.2),或当前角色明显不匹配时才换;否则保留。
  5. 写 `user_persona_assignment`。
- 冷启动:历史条数 < 阈值 → 不匹配,沿用默认角色。

### 5.4 用户→角色映射存储
新建表 `ai_user_persona_assignment`:
| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | — |
| user_id | BIGINT UNIQUE | 关联用户(家庭账号) |
| agent_id | VARCHAR(32) | 当前匹配角色 |
| manual | TINYINT DEFAULT 0 | 0=自动匹配管理;1=家长手动设定(自动匹配跳过,直到恢复自动) |
| score | DECIMAL | 最近匹配置信度 |
| reason | VARCHAR(255) | LLM 简短理由(可观测) |
| matched_at | DATETIME | 最近匹配时间 |
| creator/create_date/updater/update_date | — | 审计 |

### 5.5 `getAgentModels` 使用映射
`ConfigServiceImpl` 解析出 `device` 后:
```java
String prompt = agent.getSystemPrompt();                 // 默认:设备绑定 agent
UserPersonaAssignmentEntity a = userPersonaAssignmentService.getByUserId(device.getUserId());
if (a != null) {
    AgentEntity matched = agentService.getById(a.getAgentId());
    if (matched != null && StringUtils.isNotBlank(matched.getSystemPrompt())) {
        prompt = matched.getSystemPrompt();              // 匹配角色覆盖
    }
}
buildModuleConfig(..., prompt, ..., result, true);
```

### 5.6 家长手动切换(接口)
- `POST` 设置某用户角色:`{agent_id}`,写 `manual=1` → 立即生效;每周自动任务跳过。
- `POST` 恢复自动匹配:`manual=0` → 下个周期重新纳入自动匹配。
- 权限:仅该用户(家长)本人或管理员可操作(走既有 user_id 所有权校验)。

## 6. 匹配算法(LLM 调用)

Prompt 结构:
```
你是儿童陪伴角色匹配器。孩子近期聊天主题如下:
<近期孩子消息摘要/片段>

候选陪伴角色(每个含其 system_prompt 摘要):
- 角色A (id=...): <system_prompt 摘要>
- 角色B (id=...): <system_prompt 摘要>
...

当前角色:id=<cur>,描述=<cur 摘要>
请判断:哪个角色最贴合这个孩子近期的主题与需要?
- 若当前角色已足够合适,务必保留当前(孩子需要稳定的陪伴)。
- 仅当另一角色明显更贴合时才换。
返回 JSON:{"agent_id":"...","score":0~1,"reason":"..."}
```
- 复用一个已配置 LLM(建议复用主 agent 的 LLM,或单独配轻量模型)。
- system_prompt 过长时取摘要/截断喂给 LLM。
- `score` 用于切换阈值;`reason` 仅观测。

## 7. 验证

1. **匹配生效**:孩子聊了段时间某主题 → 跑任务 → 映射更新为更合适角色 → 下次对话人设变化(看 server 日志 `config["prompt"]`/`build_enhanced_prompt`)。
2. **保守不横跳**:主题未显著变化时,连续两周跑任务,角色不变。
3. **家长手动切换**:家长换角色 → 立即生效;`manual=1` 后每周自动任务跳过该用户;点「恢复自动匹配」后重新纳入。
4. **回退**:无映射/历史不足 → 用设备绑定 agent,行为同现状。
5. **共享**:两孩子聊相似主题 → 匹配到同一角色。
6. **隔离**:A 的匹配不影响 B。

## 8. 风险与取舍(儿童专项)

- **陪伴稳定性(核心)**:孩子依恋固定角色 → 已用「高阈值切换 + 手动设定优先 + 周期放宽到每周」三重保守:每周只做保守再评估;家长一旦手动切换即固定(自动让位)。
- **内容安全**:角色池由管理员把控,均为儿童适宜;匹配只在池内选,不生成新内容 → 无新增内容风险。
- **儿童隐私**:聊天数据已按 user/device 隔离;离线任务内部处理,不外传(除调 LLM 匹配外不传原文敏感信息——实现时可只传主题摘要)。
- **匹配质量依赖 LLM**:误匹配给孩子不合适角色 → 靠高阈值 + 家长锁定兜底。
- **LLM 成本**:每周每用户一次,几十~几百量级成本可忽略。

## 9. 后续(v2+)

- 孩子画像(年龄/兴趣)作为匹配信号(年龄对儿童陪伴很关键)。
- aipet 抽取话题替代原始聊天内容做信号。
- 家长在控制台手动挑/换角色(本期已支持 locked,UI 可后加)。
- 1 用户多设备:记忆 rekey 到 user_id。

## 10. 实现顺序(供 writing-plans 参考)

1. changelog:新建 `ai_user_persona_assignment`(含 `locked`)。**不改 ai_agent**。
2. entity/dao/service:UserPersonaAssignment。
3. `PersonaMatchTask`(@Scheduled):取数 + 调 LLM + 高阈值切换 + 跳过 locked + 写映射。
4. `getAgentModels` 接映射(5.5)。
5. 智控台:家长「换角色」(手动切换,写 `manual=1`)+「恢复自动匹配」(`manual=0`)按钮(最小 UI)。
6. 验证(§7)。
