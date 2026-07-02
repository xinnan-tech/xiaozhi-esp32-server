# agent 扩展字段(键值对 → system_prompt 模板变量)实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 agent 加灵活的扩展字段(键值对),作为 `system_prompt` 的模板变量 `{{ext.字段名}}`,运行时替换;不改 `ai_agent` 表(远端合入零冲突),xiaozhi-server(Python)零改。

**Architecture:** 新表 `ai_agent_ext`(agent_id PK + ext_json TEXT,一个 agent 一行 JSON 对象)。新 `AgentExtController` 整体读写 ext。`ConfigServiceImpl.getAgentModels` 解析「生效 agent」(matcher 覆盖时=匹配角色,否则=设备 agent),在其 `system_prompt` 上把 `{{ext.key}}` 替换成 ext 值,再走现有 `buildModuleConfig`(它做 `{{assistant_name}}`)。智控台 `roleConfig.vue` 加键值对编辑器。

**Tech Stack:** Spring Boot / MyBatis-Plus / Liquibase / Shiro(manager-api,Java);Vue2 + element-ui(manager-web);hutool JSON。无 JUnit 测试基建 → 每任务以 **mvn compile / npm build + 重启查日志** 验证(与仓库现有一致)。

**Spec:** `docs/superpowers/specs/2026-07-01-agent-ext-fields-design.md`

## Global Constraints

- **不改 `ai_agent` 表**(零列变更 → 远端 upstream 合入零冲突)。**不改 xiaozhi-server(Python)。**
- `ext_json` 用 **TEXT** 存(跟 `ai_model_config.config_json` 一致),Java 侧 hutool 解析。
- 变量语法 **`{{ext.字段名}}`**(`ext.` 前缀,避免与 `{{assistant_name}}`/`{{dynamic_context}}` 撞)。
- 所有 DB 改动走 **新建** Liquibase changeset(绝不改已有 → checksum 会挂),并在 `db.changelog-master.yaml` 注册。
- 列名/字段名:用非保留字(`agent_id`/`ext_json`,无 `manual` 那种雷)。
- **CRITICAL git**:工作树有 1000+ CRLF-modified 文件(预存噪声)。`git add` 只加**本任务新建/修改的文件**,绝不 `git add -A`/`.`。新建 SQL 文件用 **LF** 行尾。
- `@AllArgsConstructor` 注入:新 `final` 字段自动进构造器。
- 验证:`mvn -q compile`(maven 容器)+ `npm run build`(node 容器)。Web 镜像重建已修(`eclipse-temurin:21-jre-alpine`),但本计划各任务以编译/构建为门。

---

## File Structure

**新建(manager-api):**
- `src/main/resources/db/changelog/202607011000.sql` — 建 `ai_agent_ext`
- `modules/agent/entity/AgentExtEntity.java` — 实体
- `modules/agent/dao/AgentExtDao.java` — Mapper
- `modules/agent/service/AgentExtService.java` + `impl/AgentExtServiceImpl.java` — 读写
- `modules/agent/controller/AgentExtController.java` — GET/PUT ext

**修改(manager-api):**
- `src/main/resources/db/changelog/db.changelog-master.yaml` — 注册 202607011000
- `modules/config/service/impl/ConfigServiceImpl.java` — 注入 `AgentExtService`;`resolveUserPersonaPrompt`→`resolveEffectiveAgent`(返回 agent);新 `applyExtToPrompt`;改 getAgentModels 调用点

**修改(manager-web / Vue2):**
- `src/views/roleConfig.vue` — 加扩展字段键值对编辑器(挂 form.systemPrompt 同级)
- `src/apis/module/agent.js`(或现有 agent api 模块)— 加 `getExt`/`saveExt`

---

## Task 1: 建 ai_agent_ext 表

**Files:**
- Create: `main/manager-api/src/main/resources/db/changelog/202607011000.sql`
- Modify: `main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml`(末尾追加)

- [ ] **Step 1: 写建表 SQL(LF 行尾)**

`main/manager-api/src/main/resources/db/changelog/202607011000.sql`:
```sql
-- agent 扩展字段(键值对 JSON,作为 system_prompt 模板变量 {{ext.key}} 的来源)
CREATE TABLE `ai_agent_ext` (
    `agent_id` VARCHAR(32) NOT NULL COMMENT '关联 agent(一对一)',
    `ext_json` TEXT COMMENT '扩展字段 JSON 对象 {key:value}',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT NULL,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT NULL,
    PRIMARY KEY (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='agent 扩展字段';
```

- [ ] **Step 2: 在 master yaml 末尾注册**

在 `db.changelog-master.yaml` 最后一个 changeSet 后追加:
```yaml
  - changeSet:
      id: 202607011000
      author: aipet
      changes:
        - sqlFile:
            encoding: utf8
            path: classpath:db/changelog/202607011000.sql
```

- [ ] **Step 3: 重建 manager-api + 重启,验证表建出**

```bash
cd /home/aipet/coding/server-mkp/xiaozhi-esp32-server
docker run --rm -v "$PWD/main/manager-api":/app -w /app maven:3.9-eclipse-temurin-21 mvn -q package -DskipTests
docker cp main/manager-api/target/xiaozhi-esp32-api.jar xiaozhi-esp32-server-web:/app/xiaozhi-esp32-api.jar
docker exec xiaozhi-esp32-server-web chown 1003:1003 /app/xiaozhi-esp32-api.jar
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml restart xiaozhi-esp32-server-web
sleep 25
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e "SHOW CREATE TABLE ai_agent_ext; SELECT id FROM DATABASECHANGELOG WHERE id='202607011000';"
```
Expected: 表含 `agent_id`(PK)/`ext_json`;DATABASECHANGELOG 有 202607011000 = EXECUTED;容器日志有 `Started AdminApplication`。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/resources/db/changelog/202607011000.sql main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml
git commit -m "feat: 新建 ai_agent_ext 表(agent 扩展字段 JSON)"
```

---

## Task 2: AgentExtEntity + Dao

**Files:**
- Create: `main/manager-api/src/main/java/xiaozhi/modules/agent/entity/AgentExtEntity.java`
- Create: `main/manager-api/src/main/java/xiaozhi/modules/agent/dao/AgentExtDao.java`

**Interfaces:**
- Produces: `AgentExtEntity`(字段 `agentId:String`、`extJson:String`),`AgentExtDao`(供 Task 3 的 ServiceImpl 继承)

- [ ] **Step 1: Entity**

`modules/agent/entity/AgentExtEntity.java`:
```java
package xiaozhi.modules.agent.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = false)
@TableName("ai_agent_ext")
@Schema(description = "agent 扩展字段")
public class AgentExtEntity {

    @TableId(type = IdType.INPUT)
    @Schema(description = "关联 agent(主键)")
    private String agentId;

    @Schema(description = "扩展字段 JSON 对象 {key:value}")
    private String extJson;

    @TableField(fill = com.baomidou.mybatisplus.annotation.FieldFill.INSERT)
    private Long creator;

    @TableField(fill = com.baomidou.mybatisplus.annotation.FieldFill.INSERT)
    private java.util.Date createDate;

    @TableField(fill = com.baomidou.mybatisplus.annotation.FieldFill.UPDATE)
    private Long updater;

    @TableField(fill = com.baomidou.mybatisplus.annotation.FieldFill.UPDATE)
    private java.util.Date updateDate;
}
```
> `agentId` 是 String 且就是主键 → `IdType.INPUT`(应用层提供,即 agent 的 id),无自增。

- [ ] **Step 2: Dao**

`modules/agent/dao/AgentExtDao.java`:
```java
package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.agent.entity.AgentExtEntity;

@Mapper
public interface AgentExtDao extends BaseMapper<AgentExtEntity> {
}
```

- [ ] **Step 3: 编译**

```bash
docker run --rm -v "$PWD/main/manager-api":/app -w /app maven:3.9-eclipse-temurin-21 mvn -q compile
```
Expected: BUILD SUCCESS。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/entity/AgentExtEntity.java main/manager-api/src/main/java/xiaozhi/modules/agent/dao/AgentExtDao.java
git commit -m "feat: AgentExt entity + dao"
```

---

## Task 3: AgentExtService

**Files:**
- Create: `modules/agent/service/AgentExtService.java`
- Create: `modules/agent/service/impl/AgentExtServiceImpl.java`

**Interfaces:**
- Consumes: `AgentExtDao`(Task 2)
- Produces:
  - `AgentExtEntity getByAgentId(String agentId)` — 取一个 agent 的 ext(无则 null)
  - `void saveOrUpdate(String agentId, String extJson)` — 整体覆盖

- [ ] **Step 1: Service 接口**

`modules/agent/service/AgentExtService.java`:
```java
package xiaozhi.modules.agent.service;

import xiaozhi.modules.agent.entity.AgentExtEntity;

public interface AgentExtService {
    AgentExtEntity getByAgentId(String agentId);
    void saveOrUpdate(String agentId, String extJson);
}
```

- [ ] **Step 2: ServiceImpl**

`modules/agent/service/impl/AgentExtServiceImpl.java`:
```java
package xiaozhi.modules.agent.service.impl;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import xiaozhi.modules.agent.dao.AgentExtDao;
import xiaozhi.modules.agent.entity.AgentExtEntity;
import xiaozhi.modules.agent.service.AgentExtService;

@Service
public class AgentExtServiceImpl
        extends ServiceImpl<AgentExtDao, AgentExtEntity>
        implements AgentExtService {

    @Override
    public AgentExtEntity getByAgentId(String agentId) {
        if (agentId == null || agentId.isBlank()) {
            return null;
        }
        return this.getById(agentId);   // agentId 即主键
    }

    @Override
    public void saveOrUpdate(String agentId, String extJson) {
        AgentExtEntity e = getByAgentId(agentId);
        if (e == null) {
            e = new AgentExtEntity();
            e.setAgentId(agentId);
        }
        e.setExtJson(extJson);
        this.saveOrUpdate(e);
    }
}
```

- [ ] **Step 3: 编译**

```bash
docker run --rm -v "$PWD/main/manager-api":/app -w /app maven:3.9-eclipse-temurin-21 mvn -q compile
```
Expected: BUILD SUCCESS。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/service/AgentExtService.java main/manager-api/src/main/java/xiaozhi/modules/agent/service/impl/AgentExtServiceImpl.java
git commit -m "feat: AgentExt service(getByAgentId / saveOrUpdate)"
```

---

## Task 4: AgentExtController(整体读写)

**Files:**
- Create: `modules/agent/controller/AgentExtController.java`

**Interfaces:**
- Consumes: `AgentExtService`(Task 3);当前用户 `SecurityUser.getUser()`(权限校验,与 `AgentController` 一致)
- Produces: `GET /agent/{id}/ext`、`PUT /agent/{id}/ext`

- [ ] **Step 1: Controller**

`modules/agent/controller/AgentExtController.java`:
```java
package xiaozhi.modules.agent.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import cn.hutool.json.JSONUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.entity.AgentExtEntity;
import xiaozhi.modules.agent.service.AgentExtService;

@Tag(name = "agent 扩展字段")
@RestController
@RequestMapping("/agent")
@AllArgsConstructor
public class AgentExtController {

    private final AgentExtService agentExtService;

    @GetMapping("/{id}/ext")
    @Operation(summary = "取 agent 扩展字段(JSON 对象)")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> getExt(@PathVariable String id) {
        AgentExtEntity e = agentExtService.getByAgentId(id);
        Object obj = (e != null && e.getExtJson() != null && !e.getExtJson().isBlank())
                ? JSONUtil.parseObj(e.getExtJson())
                : JSONUtil.parseObj("{}");
        return new Result<>().ok(obj);
    }

    @PutMapping("/{id}/ext")
    @Operation(summary = "整体覆盖 agent 扩展字段(body=JSON 对象)")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> saveExt(@PathVariable String id, @RequestBody Map<String, Object> body) {
        agentExtService.saveOrUpdate(id, JSONUtil.toJsonStr(body));
        return new Result<>();
    }
}
```
> `Result` 用仓库实例形式(`new Result<>().ok(...)` / `new Result<>()` 成功),与 `DeviceController` 一致(已核实)。`@RequiresPermissions("sys:role:normal")` 与 `PUT /agent/{id}` 同级。

- [ ] **Step 2: 编译**

```bash
docker run --rm -v "$PWD/main/manager-api":/app -w /app maven:3.9-eclipse-temurin-21 mvn -q compile
```
Expected: BUILD SUCCESS。

- [ ] **Step 3: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/controller/AgentExtController.java
git commit -m "feat: AgentExtController GET/PUT /agent/{id}/ext"
```

---

## Task 5: ConfigServiceImpl 接入 ext 替换 + 生效 agent 重构

**Files:**
- Modify: `modules/config/service/impl/ConfigServiceImpl.java`
  - 加 `private final AgentExtService agentExtService;`(line 59 附近,与其它 final 字段同级)
  - 加 import:`AgentExtEntity`、`AgentExtService`、`cn.hutool.json.JSONObject`、`cn.hutool.json.JSONUtil`
  - `resolveUserPersonaPrompt`(line 271)→ 改名 `resolveEffectiveAgent`,**返回 `AgentEntity`**(不再返回 prompt 字符串)
  - 新增 `applyExtToPrompt(String prompt, String agentId)`
  - 改 getAgentModels 调用点(line 227)

**Interfaces:**
- Consumes: `AgentExtService`(Task 3)、`AgentService.getAgentById`(已有)、`UserPersonaAssignmentService`(已有)
- Produces: 设备 config 的 `prompt` 已把 `{{ext.key}}` 替换成生效 agent 的 ext 值

- [ ] **Step 1: 注入 AgentExtService + import**

在 `ConfigServiceImpl` 字段区(line 59 `userPersonaAssignmentService` 后)加:
```java
    private final AgentExtService agentExtService;
```
顶部 import 区加:
```java
import xiaozhi.modules.agent.entity.AgentExtEntity;
import xiaozhi.modules.agent.service.AgentExtService;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
```

- [ ] **Step 2: 把 resolveUserPersonaPrompt 改成 resolveEffectiveAgent(返回 agent)**

把 line 271 起的整个方法(`private String resolveUserPersonaPrompt...`)替换为:
```java
    /**
     * 解析「生效 agent」:匹配角色(有且有效)则用它,否则回退设备绑定 agent。
     * prompt 与 ext 都从生效 agent 取,保证话术与其扩展字段同源。
     */
    private AgentEntity resolveEffectiveAgent(DeviceEntity device, AgentEntity fallbackAgent) {
        if (device == null || device.getUserId() == null) {
            return fallbackAgent;
        }
        UserPersonaAssignmentEntity a = userPersonaAssignmentService.getByUserId(device.getUserId());
        if (a == null || a.getAgentId() == null) {
            return fallbackAgent;
        }
        // getAgentById 在 agent 不存在(被删除/LLM 返回非法 id)时会抛 RenException,
        // 此处必须回退设备 agent,绝不能让异常冒泡导致设备连不上。
        AgentEntity matched;
        try {
            matched = agentService.getAgentById(a.getAgentId());
        } catch (RenException e) {
            matched = null;
        }
        if (matched != null && matched.getSystemPrompt() != null && !matched.getSystemPrompt().isBlank()) {
            return matched;
        }
        return fallbackAgent;
    }

    /**
     * 把 system_prompt 里的 {{ext.key}} 替换成该 agent 的 ext 值;没值的占位符清空。
     */
    private String applyExtToPrompt(String prompt, String agentId) {
        if (prompt == null || agentId == null) {
            return prompt;
        }
        AgentExtEntity ext = agentExtService.getByAgentId(agentId);
        if (ext != null && ext.getExtJson() != null && !ext.getExtJson().isBlank()) {
            try {
                JSONObject m = JSONUtil.parseObj(ext.getExtJson());
                for (String k : m.keySet()) {
                    prompt = prompt.replace("{{ext." + k + "}}", m.getStr(k));
                }
            } catch (Exception ignore) {
                // ext_json 解析失败:当无 ext 处理,不影响主流程
            }
        }
        // 清掉没值的 {{ext.*}},避免原始占位符漏给 LLM
        return prompt.replaceAll("\\{\\{ext\\.[^}]*\\}\\}", "");
    }
```

- [ ] **Step 3: 改 getAgentModels 调用点(line 227)**

把:
```java
        // 解析该用户的匹配角色(有则覆盖 prompt,无则回退设备绑定 agent)
        String prompt = resolveUserPersonaPrompt(device, agent);
```
改成:
```java
        // 解析生效 agent(匹配角色有则覆盖,无则回退设备绑定 agent);prompt + ext 都从生效 agent 取
        AgentEntity effectiveAgent = resolveEffectiveAgent(device, agent);
        String prompt = effectiveAgent.getSystemPrompt();
        prompt = applyExtToPrompt(prompt, effectiveAgent.getId());
```
> 紧接其后的 `buildModuleConfig(agent.getAgentName(), prompt, ...)` **不动** —— `{{assistant_name}}` 仍用设备 agent 的名字(只换 prompt + ext,名字/音色/模型不动,符合「只换 prompt」决策)。

- [ ] **Step 4: 编译**

```bash
docker run --rm -v "$PWD/main/manager-api":/app -w /app maven:3.9-eclipse-temurin-21 mvn -q compile
```
Expected: BUILD SUCCESS(若 `RenException` 未 import,按 `xiaozhi.common.exception.RenException` 加 import —— 应已存在,Task 6 fix 时加过)。

- [ ] **Step 5: 验证替换逻辑(打 JAR 重启 + 设 ext + 看日志)**

```bash
docker run --rm -v "$PWD/main/manager-api":/app -w /app maven:3.9-eclipse-temurin-21 mvn -q package -DskipTests
docker cp main/manager-api/target/xiaozhi-esp32-api.jar xiaozhi-esp32-server-web:/app/xiaozhi-esp32-api.jar
docker exec xiaozhi-esp32-server-web chown 1003:1003 /app/xiaozhi-esp32-api.jar
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml restart xiaozhi-esp32-server-web
sleep 25
# 挑一个 agent,设 ext(age_group=5岁)并改其 system_prompt 含 {{ext.age_group}}
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e \
  "INSERT INTO ai_agent_ext(agent_id,ext_json) VALUES('<某agentId>','{\"age_group\":\"5岁\"}') ON DUPLICATE KEY UPDATE ext_json=VALUES(ext_json);"
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e \
  "UPDATE ai_agent SET system_prompt=CONCAT(system_prompt,' 孩子年龄段是 {{ext.age_group}}。') WHERE id='<某agentId>';"
```
然后该 agent 的设备对话,看 server 日志 `config["prompt"]` / `build_enhanced_prompt` 里 `{{ext.age_group}}` 是否变成 `5岁`。验证后可回滚该测试 UPDATE。
Expected: prompt 中占位符被替换成值;无残留 `{{ext.*}}`。

- [ ] **Step 6: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/config/service/impl/ConfigServiceImpl.java
# CRLF 自查:diff --stat 应只有少量行;若整文件翻转,sed -i 's/\r$//' 后重新 add
git commit -m "feat: ConfigServiceImpl 接入 ext 替换 + 生效 agent 重构"
```

---

## Task 6: 智控台扩展字段编辑器(roleConfig.vue)

**Files:**
- Modify: `main/manager-web/src/views/roleConfig.vue`(system_prompt 输入在 line 123 `v-model="form.systemPrompt"`;加同级的扩展字段编辑器)
- Modify: `main/manager-web/src/apis/module/agent.js`(加 getExt/saveExt;若 agent api 在别的文件,按 `Api.agent.*` 现有写法定位)

> 仓库是 Vue2 + element-ui(非 Vue3);用 `slot="dropdown"` 等 Vue2 写法。先 `grep -n "Api.agent" main/manager-web/src/apis/module/agent.js` 确认现有封装(用 `RequestService.sendRequest()...send()`,与 `persona.js` 同模式)。

- [ ] **Step 1: api 加 getExt/saveExt**

在 agent api 模块(若 `apis/module/agent.js`)按现有模式加两个方法(参考 `persona.js` 的 `switchPersona`):
```javascript
getExt(agentId, success, reAjaxFun) {
  RequestService.sendRequest()
    .url('/agent/' + agentId + '/ext').method('GET')
    .success(success).networkFail(reAjaxFun || clearRequestTime).send()
}
saveExt(agentId, extObj, success, reAjaxFun) {
  RequestService.sendRequest()
    .url('/agent/' + agentId + '/ext').method('PUT').data(extObj)
    .success(success).networkFail(reAjaxFun || clearRequestTime).send()
}
```
> 实际写法以 `persona.js` / `agent.js` 现有封装为准(import、`RequestService`、`clearRequestTime` 等照抄)。

- [ ] **Step 2: roleConfig.vue 加编辑器(模板)**

在 `v-model="form.systemPrompt"`(line 123)那个输入框**下方**加一块:
```vue
<el-form-item label="扩展字段">
  <div style="margin-bottom:8px;color:#888;font-size:12px;">
    作为 system_prompt 的模板变量,在提示词里用 {{ '{{ext.字段名}}' }} 引用。
  </div>
  <div v-for="(item, idx) in form.extFields" :key="idx" style="margin-bottom:6px;">
    <el-input v-model="item.key" placeholder="字段名(如 age_group)" style="width:35%;" />
    <el-input v-model="item.value" placeholder="值(如 5岁)" style="width:45%; margin-left:4px;" />
    <el-button type="danger" size="small" @click="form.extFields.splice(idx,1)" style="margin-left:4px;">删</el-button>
  </div>
  <el-button size="small" @click="form.extFields.push({key:'',value:''})">+ 添加字段</el-button>
</el-form-item>
```

- [ ] **Step 3: roleConfig.vue 加数据 + 加载 + 保存**

data 里(`systemPrompt` 旁边)加:
```javascript
extFields: [],   // [{key,value}]
```
取 agent 详情时(getAgent 成功回调,加载 form 那段)加:
```javascript
this.form.extFields = []
Api.agent.getExt(this.form.id, (res) => {
  const obj = (res && res.data) || {}
  this.form.extFields = Object.keys(obj).map(k => ({ key: k, value: obj[k] }))
})
```
保存 agent 时(submit,把 form 发出去那段)**之后**加一段(把 extFields 序列化成 JSON 存):
```javascript
const extObj = {}
this.form.extFields.forEach(f => { if (f.key) extObj[f.key] = f.value })
Api.agent.saveExt(this.form.id, extObj, () => { /* 成功提示,复用现有 message */ })
```
> 具体钩子位置:打开 `roleConfig.vue`,定位 `getAgent`/`submit` 两个方法名(以实际为准),把上述片段插到对应回调里。

- [ ] **Step 4: 构建 web 验证**

```bash
docker run --rm -v "$PWD/main/manager-web":/app -w /app node:20-alpine sh -c "npm run build" 2>&1 | tail -5
```
Expected: `Build complete` / 0 errors。

- [ ] **Step 5: Commit**

```bash
git add main/manager-web/src/views/roleConfig.vue main/manager-web/src/apis/module/agent.js
# CRLF 自查两个文件;翻转了就 sed -i 's/\r$//' 后重新 add
git commit -m "feat: 智控台 roleConfig 加扩展字段编辑器"
```

---

## 端到端验证(全部完成后)

1. 智控台编辑某 agent:在「扩展字段」加 `age_group=5岁`、`trait=勇敢`;在 system_prompt 里写 `你是{{assistant_name}}。设定:{{ext.age_group}}的孩子,性格{{ext.trait}}。`
2. 重建镜像 + 重启(`docker compose build` 已可用,eclipse-temurin base)。
3. 该 agent 的设备对话 → server 日志里 prompt 已是 `你是<昵称>。设定:5岁的孩子,性格勇敢。`(占位符全替换,无 `{{ext.*}}` 残留)。
4. **matcher 衔接**:把某用户 matcher 匹配到角色 B(角色 B 有 ext + prompt 用 `{{ext.*}}`)→ 该用户设备的 prompt 用 B 的 prompt + **B 的 ext**(不串 A 的)。
5. **未匹配用户**:设备用自己绑定 agent 的 ext。
