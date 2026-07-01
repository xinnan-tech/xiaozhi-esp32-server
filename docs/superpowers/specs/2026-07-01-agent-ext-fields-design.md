# agent 扩展字段(键值对 → system_prompt 模板变量)— 设计

- 日期: 2026-07-01
- 状态: draft(待用户审阅)
- 范围: manager-api(Java)+ 智控台(Vue);xiaozhi-server(Python)零改

## 1. 目标

给 agent 加**灵活的扩展字段**(键值对),作为 system_prompt 的**模板变量**(`{{ext.字段名}}`),运行时替换成值。

- 不固定列、不改 `ai_agent` 表 → **远端(upstream)合入零冲突**(关键诉求)。
- 管理员可随时加字段(零改表/零改代码)。
- 字段名即模板变量名,在 system_prompt 里用 `{{ext.字段名}}` 引用。

## 2. 真实代码基线(已核实)

- system_prompt 来自 `agent.system_prompt`,`ConfigServiceImpl.getAgentModels` 经 `result["prompt"]` 下发 → xiaozhi-server `build_enhanced_prompt`。
- 已有模板变量先例:`{{assistant_name}}` 在 `ConfigServiceImpl` 里 `prompt.replace(...)`(manager-api 侧字符串替换)。
- agent 编辑:`PUT /agent/{id}`(`AgentController.update`,`AgentUpdateDTO`)。
- schema 走 Liquibase(`sqlFile` changeset + `db.changelog-master.yaml` 注册);`ai_model_config.config_json` 用 **TEXT 存 JSON**,Java 侧 hutool 解析 → 本设计沿用。

## 3. 数据模型

新表 `ai_agent_ext`(**零改 `ai_agent`**):
| 字段 | 类型 | 说明 |
|---|---|---|
| `agent_id` | VARCHAR(32) PK | 关联 agent(一对一) |
| `ext_json` | TEXT | 扩展字段 JSON 对象 `{key:value}` |
| `creator/create_date/updater/update_date` | — | 审计 |

- 一个 agent **一行**,`ext_json` 装任意多个键值对。
- key 推荐英文(`age_group`/`trait`),value 可中文;`{{ext.key}}` 是字符串替换,key 用什么都行。

## 4. 注入(核心)

`ConfigServiceImpl`,在现有 `{{assistant_name}}` 替换那段**旁边**加:
```java
prompt = prompt.replace("{{assistant_name}}", assistantName);   // 现有
// 新增:生效 agent 的 ext 字段逐个替换
AgentExtEntity ext = agentExtService.getByAgentId(effectiveAgentId);
if (ext != null && StringUtils.isNotBlank(ext.getExtJson())) {
    try {
        JSONObject m = JSONUtil.parseObj(ext.getExtJson());
        for (String k : m.keySet()) {
            prompt = prompt.replace("{{ext." + k + "}}", m.getStr(k));
        }
    } catch (Exception e) { log.warn("agent {} ext_json 解析失败", effectiveAgentId); }
}
// 清掉没值的 {{ext.*}},避免原始占位符漏给 LLM
prompt = prompt.replaceAll("\\{\\{ext\\.[^}]*\\}\\}", "");
```
- `effectiveAgentId` = 话术是谁的就用谁(见 §6)。

## 5. 接口(新 `AgentExtController`,不碰 `AgentController` → 合入干净)

| 接口 | 作用 |
|---|---|
| `GET /agent/{id}/ext` | 返回该 agent 的 ext JSON 对象 |
| `PUT /agent/{id}/ext` | body=整个 JSON 对象,**整体覆盖** ext_json |

- `@RequiresPermissions("sys:role:normal")`(与 `PUT /agent/{id}` 一致)。
- 配套:`AgentExtEntity`(`agentId` PK + `extJson` String)、`AgentExtDao`、`AgentExtService`(`getByAgentId` / `saveOrUpdate`)。
- **整体读写**(非逐 key):UI 一次编辑一组、整体存,最简单,避免并发改同一 JSON 互覆盖。

## 6. 与 matcher(persona 匹配)的衔接

matcher 会把 prompt 覆盖成匹配角色的。ext 必须「**话术是谁的就用谁的 ext**」:
- 用了匹配角色 prompt → 用**匹配角色**的 ext;
- 回退到设备 agent prompt → 用**设备 agent**的 ext。

→ 把 `resolveUserPersonaPrompt` 小改:**返回「生效 agent」(不只是 prompt 字符串)**,prompt + ext 都从生效 agent 取,不串味。

## 7. 智控台(Vue)

agent 编辑页加一块「扩展字段」:
- **键值对列表编辑器**:每行 `[字段名] [值] [删]`,底部 `+ 添加`。
- 打开:`GET /agent/{id}/ext` → JSON 填成行;保存:序列化成 JSON → `PUT /agent/{id}/ext`。
- 提示:「在 system_prompt 里用 `{{ext.字段名}}` 引用」并回显当前字段名。

## 8. 建表 changeset

`main/manager-api/src/main/resources/db/changelog/202607011000.sql`(新建,不改已有 → checksum 不挂):
```sql
CREATE TABLE `ai_agent_ext` (
    `agent_id` VARCHAR(32) NOT NULL COMMENT '关联 agent(一对一)',
    `ext_json` TEXT COMMENT '扩展字段 JSON 对象 {key:value}',
    `creator` BIGINT DEFAULT NULL, `create_date` DATETIME DEFAULT NULL,
    `updater` BIGINT DEFAULT NULL, `update_date` DATETIME DEFAULT NULL,
    PRIMARY KEY (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='agent 扩展字段';
```
+ `db.changelog-master.yaml` 末尾注册(id `202607011000`)。

## 9. 边界 / 注意

- agent 无 ext 行 → 不替换。
- `{{ext.缺失字段}}` → 清空(§4 末尾正则)。
- ext_json 解析失败 → catch,当无 ext(log warn)。
- **CRLF**:新 SQL 文件 LF 行尾。
- **保留字**:`agent_id`/`ext_json` 非保留,无雷。

## 10. 验证

1. 给 agent A 设 ext(`age_group=5岁`、`trait=勇敢`)+ A 的 system_prompt 含 `{{ext.age_group}}`/`{{ext.trait}}`。
2. A 的设备拉 config → prompt 里已替换成 `5岁`/`勇敢`(看 server 日志 / config 响应)。
3. matcher 覆盖时(设备被匹配到角色 B)→ prompt 用 B 的 prompt + **B 的 ext**。

## 11. 范围外(v2+)

- user / device 的 ext(本期只 agent)。
- 按 key 跨 agent 查询(如「所有 age_group=5岁的 agent」)——JSON 不好查,需要时换长表或加索引。
- matcher 用 ext 字段辅助选角。

## 12. 实现顺序(供 writing-plans)

1. changelog 建表 `ai_agent_ext` + 注册。
2. `AgentExtEntity`/`Dao`/`Service`。
3. `AgentExtController`(GET/PUT ext)。
4. `ConfigServiceImpl` 加 ext 替换 + `resolveUserPersonaPrompt` 改返回生效 agent。
5. 智控台 agent 编辑页加扩展字段编辑器。
6. 验证(§10)。
