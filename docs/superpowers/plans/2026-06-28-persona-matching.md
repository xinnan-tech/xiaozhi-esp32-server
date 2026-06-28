# 周期性按聊天主题匹配陪伴角色 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让每个孩子(用户)被自动匹配到最合适的陪伴角色(系统提示词),每周重评估一次(保守切换),家长可随时手动切换(手动粘性)。xiaozhi-server(Python)零改。

**Architecture:** 全部在 manager-api。新增 `ai_user_persona_assignment` 表存「用户→当前角色」映射 + `manual` 标志;新增 `PersonaMatchTask`(`@Scheduled` 每周)用 `LLMService.generateSummary(...)` 对每个非 manual 用户做匹配(高阈值才换);`ConfigServiceImpl.getAgentModels` 解析设备→用户→映射,用匹配角色的 `system_prompt` 覆盖默认;新增 controller 让家长手动切换/恢复自动。

**Tech Stack:** Java 17 / Spring Boot / MyBatis-Plus / Shiro(`@RequiresPermissions`)/ Liquibase(sqlFile changeset)/ Vue(智控台)。LLM 调用复用 `OpenAIStyleLLMServiceImpl`(RestTemplate → `/chat/completions`)。

**Spec:** `docs/superpowers/specs/2026-06-28-multi-user-persona-design.md`

## Global Constraints

- **不改 xiaozhi-server(Python)**;不改 `ai_agent` 表(匹配直接用其 `system_prompt`)。
- 表名 `ai_user_persona_assignment`;`manual` 字段:0=自动管理,1=家长手动(自动任务跳过)。
- 匹配只在 `system_prompt` 非空的角色池内选,不生成新内容。
- 所有数据库改动走 Liquibase changeset(原子 sqlFile),并在 `db.changelog-master.yaml` 注册。
- 遵循既有命名:entity `@TableName`/`@Data`/`@Schema`;dao `@Mapper extends BaseMapper`;controller `@RequiresPermissions("sys:role:normal")`;当前用户取 `SecurityUser.getUser().getId()`。
- `@Scheduled` 任务用 cron(每周),仿 `DocumentStatusSyncTask`。
- 本仓库无 manager-api 的 JUnit 测试基建;每个任务以 **重建 manager-web/manager-api 镜像 → 重启 → 查 DB/日志** 验证(与仓库现有开发方式一致)。

---

## File Structure

**新建(manager-api):**
- `src/main/resources/db/changelog/202606281000.sql` — 建 `ai_user_persona_assignment` 表
- `modules/agent/entity/UserPersonaAssignmentEntity.java` — 映射实体
- `modules/agent/dao/UserPersonaAssignmentDao.java` — Mapper
- `modules/agent/service/UserPersonaAssignmentService.java` + `impl/UserPersonaAssignmentServiceImpl.java` — 映射读写
- `modules/agent/service/PersonaMatcherService.java` + `impl/PersonaMatcherServiceImpl.java` — 单用户匹配逻辑(取聊天+候选+调LLM+阈值)
- `modules/agent/task/PersonaMatchTask.java` — `@Scheduled` 每周遍历所有非 manual 用户
- `modules/agent/controller/UserPersonaController.java` — 家长手动切换/恢复自动

**修改(manager-api):**
- `src/main/resources/db/changelog/db.changelog-master.yaml` — 末尾注册 202606281000
- `modules/config/service/impl/ConfigServiceImpl.java` — 注入 `UserPersonaAssignmentService` + `AgentService` 已有;`getAgentModels` 解析映射覆盖 prompt

**修改(manager-web / Vue):**
- 一个设备/用户视图组件加「换角色」「恢复自动匹配」按钮(最小 UI,挂到既有用户侧视图)

---

## Task 1: 建表 ai_user_persona_assignment

**Files:**
- Create: `main/manager-api/src/main/resources/db/changelog/202606281000.sql`
- Modify: `main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml`(末尾追加 changeSet)

- [ ] **Step 1: 写建表 SQL**

`main/manager-api/src/main/resources/db/changelog/202606281000.sql`:
```sql
-- 用户-陪伴角色匹配映射(儿童陪伴:按聊天主题自动匹配角色 + 家长手动切换)
CREATE TABLE `ai_user_persona_assignment` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `agent_id` VARCHAR(32) NOT NULL COMMENT '当前匹配的陪伴角色(ai_agent.id)',
    `manual` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '0=自动匹配管理;1=家长手动设定(自动任务跳过)',
    `score` DECIMAL(4,2) DEFAULT NULL COMMENT '最近匹配置信度 0~1',
    `reason` VARCHAR(255) DEFAULT NULL COMMENT '匹配理由(LLM)',
    `matched_at` DATETIME DEFAULT NULL COMMENT '最近匹配时间',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT NULL,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户-陪伴角色匹配映射';
```

- [ ] **Step 2: 在 master yaml 末尾注册**

在 `db.changelog-master.yaml` 最后一个 changeSet(202606211000)之后追加:
```yaml
  - changeSet:
      id: 202606281000
      author: aipet
      changes:
        - sqlFile:
            encoding: utf8
            path: classpath:db/changelog/202606281000.sql
```

- [ ] **Step 3: 重建并重启 manager-api**

```bash
cd /home/aipet/coding/xiaozhi-server
docker compose -f docker-compose_all.yml build xiaozhi-esp32-server-web
docker compose -f docker-compose_all.yml up -d xiaozhi-esp32-server-web
```
Expected: 容器启动成功(日志无 Liquibase 报错)。

- [ ] **Step 4: 验证表已建**

```bash
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e "SHOW CREATE TABLE ai_user_persona_assignment; SELECT id,exectype FROM DATABASECHANGELOG WHERE id='202606281000';"
```
Expected: 表结构含 `manual`/`agent_id`/`user_id`;DATABASECHANGELOG 有 202606281000 = EXECUTED。

- [ ] **Step 5: Commit**

```bash
cd /home/aipet/coding/server-mkp/xiaozhi-esp32-server
git add main/manager-api/src/main/resources/db/changelog/202606281000.sql main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml
git commit -m "feat: 新建 ai_user_persona_assignment 表(陪伴角色匹配映射)"
```

---

## Task 2: Entity + Dao

**Files:**
- Create: `main/manager-api/src/main/java/xiaozhi/modules/agent/entity/UserPersonaAssignmentEntity.java`
- Create: `main/manager-api/src/main/java/xiaozhi/modules/agent/dao/UserPersonaAssignmentDao.java`

**Interfaces:**
- Produces: `UserPersonaAssignmentEntity`(字段见下), `UserPersonaAssignmentDao`(供 Task 3 的 Service 继承 `ServiceImpl`)

- [ ] **Step 1: 写 Entity**

`modules/agent/entity/UserPersonaAssignmentEntity.java`:
```java
package xiaozhi.modules.agent.entity;

import java.math.BigDecimal;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = false)
@TableName("ai_user_persona_assignment")
@Schema(description = "用户-陪伴角色匹配映射")
public class UserPersonaAssignmentEntity {

    @TableId(type = IdType.AUTO)
    @Schema(description = "主键ID")
    private Long id;

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "当前匹配的陪伴角色ID")
    private String agentId;

    @Schema(description = "0=自动;1=家长手动")
    private Integer manual;

    @Schema(description = "最近匹配置信度")
    private BigDecimal score;

    @Schema(description = "匹配理由")
    private String reason;

    @Schema(description = "最近匹配时间")
    private Date matchedAt;

    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}
```

- [ ] **Step 2: 写 Dao**

`modules/agent/dao/UserPersonaAssignmentDao.java`:
```java
package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;

@Mapper
public interface UserPersonaAssignmentDao extends BaseMapper<UserPersonaAssignmentEntity> {
}
```

- [ ] **Step 3: 编译验证**

```bash
cd /home/aipet/coding/server-mkp/xiaozhi-esp32-server/main/manager-api
mvn -q compile
```
Expected: BUILD SUCCESS(无符号找不到错误)。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/entity/UserPersonaAssignmentEntity.java main/manager-api/src/main/java/xiaozhi/modules/agent/dao/UserPersonaAssignmentDao.java
git commit -m "feat: UserPersonaAssignment entity + dao"
```

---

## Task 3: 映射 Service(读写)

**Files:**
- Create: `modules/agent/service/UserPersonaAssignmentService.java`
- Create: `modules/agent/service/impl/UserPersonaAssignmentServiceImpl.java`

**Interfaces:**
- Consumes: `UserPersonaAssignmentDao`(Task 2)
- Produces:
  - `UserPersonaAssignmentEntity getByUserId(Long userId)`
  - `void upsertAuto(Long userId, String agentId, BigDecimal score, String reason)` — 写/更新自动匹配结果(`manual=0`)
  - `void setManual(Long userId, String agentId)` — 家长手动切换(`manual=1`)
  - `void resetAuto(Long userId)` — 恢复自动(`manual=0`)

- [ ] **Step 1: 写 Service 接口**

`modules/agent/service/UserPersonaAssignmentService.java`:
```java
package xiaozhi.modules.agent.service;

import java.math.BigDecimal;

import com.baomidou.mybatisplus.extension.service.IService;

import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;

public interface UserPersonaAssignmentService extends IService<UserPersonaAssignmentEntity> {

    UserPersonaAssignmentEntity getByUserId(Long userId);

    /** 自动匹配写入(manual=0) */
    void upsertAuto(Long userId, String agentId, BigDecimal score, String reason);

    /** 家长手动切换(manual=1,立即生效) */
    void setManual(Long userId, String agentId);

    /** 恢复自动匹配(manual=0) */
    void resetAuto(Long userId);
}
```

- [ ] **Step 2: 写 ServiceImpl**

`modules/agent/service/impl/UserPersonaAssignmentServiceImpl.java`:
```java
package xiaozhi.modules.agent.service.impl;

import java.math.BigDecimal;
import java.util.Date;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import xiaozhi.modules.agent.dao.UserPersonaAssignmentDao;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;

@Service
public class UserPersonaAssignmentServiceImpl
        extends ServiceImpl<UserPersonaAssignmentDao, UserPersonaAssignmentEntity>
        implements UserPersonaAssignmentService {

    @Override
    public UserPersonaAssignmentEntity getByUserId(Long userId) {
        if (userId == null) {
            return null;
        }
        return this.getOne(new LambdaQueryWrapper<UserPersonaAssignmentEntity>()
                .eq(UserPersonaAssignmentEntity::getUserId, userId));
    }

    @Override
    public void upsertAuto(Long userId, String agentId, BigDecimal score, String reason) {
        UserPersonaAssignmentEntity e = getByUserId(userId);
        if (e == null) {
            e = new UserPersonaAssignmentEntity();
            e.setUserId(userId);
        }
        e.setAgentId(agentId);
        e.setScore(score);
        e.setReason(reason);
        e.setManual(0);
        e.setMatchedAt(new Date());
        this.saveOrUpdate(e);
    }

    @Override
    public void setManual(Long userId, String agentId) {
        UserPersonaAssignmentEntity e = getByUserId(userId);
        if (e == null) {
            e = new UserPersonaAssignmentEntity();
            e.setUserId(userId);
        }
        e.setAgentId(agentId);
        e.setManual(1);
        e.setReason("manual");
        e.setMatchedAt(new Date());
        this.saveOrUpdate(e);
    }

    @Override
    public void resetAuto(Long userId) {
        UserPersonaAssignmentEntity e = getByUserId(userId);
        if (e != null) {
            e.setManual(0);
            this.updateById(e);
        }
    }
}
```

- [ ] **Step 3: 编译验证**

```bash
cd /home/aipet/coding/server-mkp/xiaozhi-esp32-server/main/manager-api && mvn -q compile
```
Expected: BUILD SUCCESS。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/service/UserPersonaAssignmentService.java main/manager-api/src/main/java/xiaozhi/modules/agent/service/impl/UserPersonaAssignmentServiceImpl.java
git commit -m "feat: UserPersonaAssignment service(upsert/manual/reset)"
```

---

## Task 4: 匹配逻辑 PersonaMatcherService

**Files:**
- Create: `modules/agent/service/PersonaMatcherService.java`
- Create: `modules/agent/service/impl/PersonaMatcherServiceImpl.java`

**Interfaces:**
- Consumes:
  - `AgentService list()`(候选角色池) — 签名:`List<AgentEntity> list();`(MyBatis-Plus IService 已有)
  - `AgentChatHistoryService extends IService<AgentChatHistoryEntity>`(字段:`macAddress`, `chatType`, `content`, `createdAt`)— `list(LambdaQueryWrapper)`
  - `DeviceService extends IService<DeviceEntity>`(字段:`userId`, `macAddress`)— `list(LambdaQueryWrapper)`
  - `LLMService.generateSummary(String conversation, String promptTemplate, String modelId) → String`(modelId=null 用默认)
  - `UserPersonaAssignmentService.getByUserId(Long)`(Task 3)
- Produces:
  - `void matchForUser(Long userId, int days, int limit, int minHistory)` — 拉聊天+候选→调 LLM→高阈值才写自动匹配;冷启动/不足不动
  - 常量:`SWITCH_SCORE_DELTA = 0.20`(切换阈值,差值需 ≥ 此值才换)

- [ ] **Step 1: 写 Service 接口**

`modules/agent/service/PersonaMatcherService.java`:
```java
package xiaozhi.modules.agent.service;

public interface PersonaMatcherService {

    /**
     * 为单个用户做一次匹配(保守:仅当另一角色置信度高出当前 Δ 才切换)。
     * 跳过 manual=1(由调用方保证)。
     *
     * @param userId     用户
     * @param days       取最近多少天聊天
     * @param limit      最多取多少条
     * @param minHistory 历史不足此数则不匹配(冷启动)
     */
    void matchForUser(Long userId, int days, int limit, int minHistory);
}
```

- [ ] **Step 2: 写 ServiceImpl**

`modules/agent/service/impl/PersonaMatcherServiceImpl.java`:
```java
package xiaozhi.modules.agent.service.impl;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.PersonaMatcherService;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.llm.service.LLMService;

@Slf4j
@Service
public class PersonaMatcherServiceImpl implements PersonaMatcherService {

    /** 仅当新角色置信度高出当前 ≥ 此值才切换 */
    private static final BigDecimal SWITCH_SCORE_DELTA = new BigDecimal("0.20");

    @Autowired private AgentService agentService;
    @Autowired private AgentChatHistoryService agentChatHistoryService;
    @Autowired private DeviceService deviceService;
    @Autowired private LLMService llmService;
    @Autowired private UserPersonaAssignmentService userPersonaAssignmentService;

    @Override
    public void matchForUser(Long userId, int days, int limit, int minHistory) {
        // 1. 取该用户所有设备的 mac
        List<DeviceEntity> devices = deviceService.list(
                new LambdaQueryWrapper<DeviceEntity>().eq(DeviceEntity::getUserId, userId));
        if (devices.isEmpty()) {
            return;
        }
        List<String> macs = devices.stream().map(DeviceEntity::getMacAddress).collect(Collectors.toList());

        // 2. 取近期孩子消息(chat_type=1)
        Date cutoff = Date.from(LocalDateTime.now().minusDays(days)
                .atZone(ZoneId.systemDefault()).toInstant());
        List<AgentChatHistoryEntity> msgs = agentChatHistoryService.list(
                new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .in(AgentChatHistoryEntity::getMacAddress, macs)
                        .eq(AgentChatHistoryEntity::getChatType, 1)
                        .gt(AgentChatHistoryEntity::getCreatedAt, cutoff)
                        .orderByDesc(AgentChatHistoryEntity::getCreatedAt)
                        .last("LIMIT " + limit));
        if (msgs.size() < minHistory) {
            log.info("[persona-match] user={} 历史不足({}<{})跳过", userId, msgs.size(), minHistory);
            return;
        }

        // 3. 候选角色(system_prompt 非空)
        List<AgentEntity> candidates = agentService.list().stream()
                .filter(a -> a.getSystemPrompt() != null && !a.getSystemPrompt().isBlank())
                .collect(Collectors.toList());
        if (candidates.isEmpty()) {
            return;
        }

        // 4. 拼主题 + 候选,调 LLM
        String topics = msgs.stream().map(AgentChatHistoryEntity::getContent)
                .filter(s -> s != null && !s.isBlank())
                .collect(Collectors.joining("\n"));
        UserPersonaAssignmentEntity cur = userPersonaAssignmentService.getByUserId(userId);
        String conversation = buildConversation(topics, candidates, cur);
        String promptTemplate = buildInstruction();
        String resp;
        try {
            resp = llmService.generateSummary(conversation, promptTemplate, null);
        } catch (Exception e) {
            log.warn("[persona-match] user={} LLM 调用失败:{}", userId, e.getMessage());
            return;
        }

        // 5. 解析 + 高阈值才写
        MatchResult mr = parse(resp);
        if (mr == null) {
            log.warn("[persona-match] user={} LLM 返回无法解析:{}", userId, resp);
            return;
        }
        boolean shouldSwitch = cur == null
                || cur.getManual() != null && cur.getManual() == 1   // 不该进来(manual 被跳过),保险
                || !mr.agentId.equals(cur.getAgentId())
                && (cur.getScore() == null || mr.score.subtract(cur.getScore()).compareTo(SWITCH_SCORE_DELTA) >= 0);
        if (!shouldSwitch) {
            log.info("[persona-match] user={} 保留当前 agent={}(new={},cur={})", userId,
                    cur == null ? null : cur.getAgentId(), mr.agentId, mr.score);
            return;
        }
        userPersonaAssignmentService.upsertAuto(userId, mr.agentId, mr.score, mr.reason);
        log.info("[persona-match] user={} 切换到 agent={} score={} reason={}", userId, mr.agentId, mr.score, mr.reason);
    }

    private String buildConversation(String topics, List<AgentEntity> candidates, UserPersonaAssignmentEntity cur) {
        StringBuilder sb = new StringBuilder();
        sb.append("【孩子近期聊天】\n").append(topics).append("\n\n【候选陪伴角色】\n");
        for (AgentEntity a : candidates) {
            String desc = a.getSystemPrompt();
            if (desc.length() > 120) desc = desc.substring(0, 120);
            sb.append("- ").append(a.getAgentName()).append("(id=").append(a.getId()).append("): ")
              .append(desc).append("\n");
        }
        if (cur != null) {
            sb.append("\n【当前角色id】").append(cur.getAgentId());
        }
        return sb.toString();
    }

    private String buildInstruction() {
        return "你是儿童陪伴角色匹配器。根据【孩子近期聊天】从【候选陪伴角色】里选最贴合的一个。"
                + "若【当前角色】已足够合适,务必保留当前(孩子需要稳定陪伴)。"
                + "仅当另一角色明显更贴合时才换。只返回JSON,不要多余文字:"
                + "{\"agent_id\":\"候选id\",\"score\":0到1的小数,\"reason\":\"一句话\"}";
    }

    private MatchResult parse(String resp) {
        if (resp == null) return null;
        int s = resp.indexOf('{'), e = resp.lastIndexOf('}');
        if (s < 0 || e <= s) return null;
        try {
            JSONObject j = JSONUtil.parseObj(resp.substring(s, e + 1));
            MatchResult mr = new MatchResult();
            mr.agentId = j.getStr("agent_id");
            mr.score = new BigDecimal(j.getStr("score", "0"));
            mr.reason = j.getStr("reason");
            return (mr.agentId == null || mr.agentId.isBlank()) ? null : mr;
        } catch (Exception ex) {
            return null;
        }
    }

    private static class MatchResult {
        String agentId;
        BigDecimal score;
        String reason;
    }
}
```

> 注:`AgentChatHistoryEntity`/`AgentEntity`/`DeviceEntity` 的 getter 名以仓库实际为准(`getMacAddress`/`getChatType`/`getCreatedAt`/`getContent`/`getSystemPrompt`/`getAgentName`/`getUserId`);`cn.hutool.json` 仓库已用(见 OpenAIStyleLLMServiceImpl 的 JSONObject)。

- [ ] **Step 3: 编译验证**

```bash
cd /home/aipet/coding/server-mkp/xiaozhi-esp32-server/main/manager-api && mvn -q compile
```
Expected: BUILD SUCCESS。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/service/PersonaMatcherService.java main/manager-api/src/main/java/xiaozhi/modules/agent/service/impl/PersonaMatcherServiceImpl.java
git commit -m "feat: PersonaMatcher 主题匹配(高阈值保守切换)"
```

---

## Task 5: 定时任务 PersonaMatchTask

**Files:**
- Create: `modules/agent/task/PersonaMatchTask.java`

**Interfaces:**
- Consumes: `PersonaMatcherService.matchForUser(...)`(Task 4), `UserPersonaAssignmentService`(判断 manual)
- Produces: 每周一凌晨遍历所有非 manual 用户调用 matchForUser

- [ ] **Step 1: 写 Task**

`modules/agent/task/PersonaMatchTask.java`:
```java
package xiaozhi.modules.agent.task;

import java.util.List;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
import xiaozhi.modules.agent.service.PersonaMatcherService;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;

/**
 * 陪伴角色周匹配任务。
 * 仿 modules/knowledge/task/DocumentStatusSyncTask。
 * 每周一 03:30 跑一次;只处理非 manual 用户(家长手动设定过的跳过)。
 */
@Component
@AllArgsConstructor
@Slf4j
public class PersonaMatchTask {

    private final PersonaMatcherService personaMatcherService;
    private final UserPersonaAssignmentService userPersonaAssignmentService;

    /** 每周一 03:30(可按需改 cron) */
    @Scheduled(cron = "0 30 3 ? * MON")
    public void matchAll() {
        try {
            log.info("[persona-match] 开始周匹配");
            List<UserPersonaAssignmentEntity> all = userPersonaAssignmentService.list();
            int matched = 0;
            for (UserPersonaAssignmentEntity a : all) {
                if (a.getManual() != null && a.getManual() == 1) {
                    continue; // 家长手动设定,跳过
                }
                try {
                    personaMatcherService.matchForUser(a.getUserId(), 14, 50, 5);
                    matched++;
                } catch (Exception ex) {
                    log.warn("[persona-match] user={} 失败:{}", a.getUserId(), ex.getMessage());
                }
            }
            log.info("[persona-match] 周匹配完成,处理 {} 人", matched);
        } catch (Exception e) {
            log.error("[persona-match] 周匹配任务异常", e);
        }
    }
}
```

- [ ] **Step 2: 确认 @EnableScheduling 已开**

```bash
grep -rn "EnableScheduling" main/manager-api/src/main/java/xiaozhi/
```
Expected: 命中 `AdminApplication.java` 或某 `@Configuration`(DocumentStatusSyncTask 能跑说明已开)。若**未命中**,在 `AdminApplication.java` 类上加 `@EnableScheduling`(`import org.springframework.scheduling.annotation.EnableScheduling;`)。

- [ ] **Step 3: 重建重启 + 手动触发验证(临时改 cron 为近时,或直接调接口)**

为便于验证,临时把 cron 改成 `0 */2 * * * ?`(每 2 分钟)跑一次,重建重启后:
```bash
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml build xiaozhi-esp32-server-web
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml up -d xiaozhi-esp32-server-web
sleep 130
docker logs --since 3m xiaozhi-esp32-server-web 2>&1 | grep persona-match | tail -20
```
Expected: 日志出现 `[persona-match] 开始周匹配` / `user=... 切换到 agent=...` 或 `历史不足...跳过`(无数据用户)。验证后**把 cron 改回 `0 30 3 ? * MON`** 再提交。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/task/PersonaMatchTask.java
git commit -m "feat: PersonaMatchTask 每周自动匹配角色"
```

---

## Task 6: getAgentModels 接入映射

**Files:**
- Modify: `modules/config/service/impl/ConfigServiceImpl.java`(注入新 Service + 改 `getAgentModels` 的 prompt)

**Interfaces:**
- Consumes: `UserPersonaAssignmentService.getByUserId(Long)`(Task 3), `AgentService.getAgentById(String)`(已有)
- Produces: 设备所属用户的匹配角色 `system_prompt` 作为 `result["prompt"]`(无则回退设备绑定 agent)

- [ ] **Step 1: 注入 UserPersonaAssignmentService**

在 `ConfigServiceImpl` 的依赖字段区(与已有 `private final AgentService agentService;` 同级)加:
```java
private final UserPersonaAssignmentService userPersonaAssignmentService;
```
并加 import:
```java
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
```
(若该类用 `@RequiredArgsConstructor`/`@AllArgsConstructor`,final 字段会自动进构造器。)

- [ ] **Step 2: 改 getAgentModels 的 prompt 参数**

定位 `buildModuleConfig(` 调用(约 line 222,第二个实参是 `agent.getSystemPrompt()`)。在它**之前**插入解析,并把第二个实参换成 `prompt`:

把这段:
```java
        // 构建模块配置
        buildModuleConfig(
                agent.getAgentName(),
                agent.getSystemPrompt(),
```
改为:
```java
        // 解析该用户的匹配角色(有则覆盖 prompt,无则回退设备绑定 agent)
        String prompt = resolveUserPersonaPrompt(device, agent);

        // 构建模块配置
        buildModuleConfig(
                agent.getAgentName(),
                prompt,
```

- [ ] **Step 3: 加私有方法 resolveUserPersonaPrompt**

在 `ConfigServiceImpl` 内(`getAgentModels` 方法所在的类)加:
```java
    /**
     * 取该用户当前匹配角色的 system_prompt;无映射或映射角色无效则回退设备绑定 agent。
     */
    private String resolveUserPersonaPrompt(DeviceEntity device, AgentEntity fallbackAgent) {
        String fallback = fallbackAgent.getSystemPrompt();
        if (device == null || device.getUserId() == null) {
            return fallback;
        }
        UserPersonaAssignmentEntity a = userPersonaAssignmentService.getByUserId(device.getUserId());
        if (a == null || a.getAgentId() == null) {
            return fallback;
        }
        AgentEntity matched = agentService.getAgentById(a.getAgentId());
        if (matched != null && matched.getSystemPrompt() != null && !matched.getSystemPrompt().isBlank()) {
            return matched.getSystemPrompt();
        }
        return fallback;
    }
```

- [ ] **Step 4: 重建重启 + 验证**

```bash
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml build xiaozhi-esp32-server-web
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml up -d xiaozhi-esp32-server-web
# 手动给某测试用户写一条映射,再用该用户的设备 mac 查 config:
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e \
  "INSERT INTO ai_user_persona_assignment(user_id,agent_id,manual,matched_at) VALUES(<某userId>,'<某agentId>',0,NOW()) ON DUPLICATE KEY UPDATE agent_id=VALUES(agent_id);"
```
然后该设备对话,看 xiaozhi-server 日志 `build_enhanced_prompt` / `config["prompt"]` 是否为该 agent 的 system_prompt;清掉该映射行后回退为设备绑定 agent。
Expected: 有映射→用映射角色;无映射→回退。

- [ ] **Step 5: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/config/service/impl/ConfigServiceImpl.java
git commit -m "feat: getAgentModels 按用户匹配角色覆盖 system_prompt"
```

---

## Task 7: 家长手动切换接口

**Files:**
- Create: `modules/agent/controller/UserPersonaController.java`

**Interfaces:**
- Consumes: `UserPersonaAssignmentService.setManual(Long,String)` / `resetAuto(Long)`(Task 3),当前用户 `SecurityUser.getUser().getId()`
- Produces: `POST /persona/switch {agentId}`、`POST /persona/auto`

- [ ] **Step 1: 写 Controller**

`modules/agent/controller/UserPersonaController.java`:
```java
package xiaozhi.modules.agent.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;
import xiaozhi.modules.security.user.SecurityUser;

@RestController
@RequestMapping("/persona")
@AllArgsConstructor
public class UserPersonaController {

    private final UserPersonaAssignmentService userPersonaAssignmentService;

    /** 家长手动切换角色(立即生效,标 manual=1,自动任务不再覆盖) */
    @PostMapping("/switch")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> switchPersona(@RequestBody Map<String, String> body) {
        String agentId = body.get("agentId");
        if (agentId == null || agentId.isBlank()) {
            return Result.error("agentId 不能为空");
        }
        Long userId = SecurityUser.getUser().getId();
        userPersonaAssignmentService.setManual(userId, agentId);
        return new Result<Void>();
    }

    /** 恢复自动匹配(manual=0) */
    @PostMapping("/auto")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> resetAuto() {
        Long userId = SecurityUser.getUser().getId();
        userPersonaAssignmentService.resetAuto(userId);
        return new Result<Void>();
    }
}
```

> 注:`Result`/`Result.error(...)` 的包名与构造以仓库实际通用返回类为准(参考既有 controller,如 `DeviceController` 的 import);若 `new Result<Void>()` 不成立,改用既有 controller 的返回写法。

- [ ] **Step 2: 编译验证**

```bash
cd /home/aipet/coding/server-mkp/xiaozhi-esp32-server/main/manager-api && mvn -q compile
```
Expected: BUILD SUCCESS(`Result` 包名不对则按 DeviceController 修正 import)。

- [ ] **Step 3: 重建重启 + 调用验证**

```bash
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml build xiaozhi-esp32-server-web
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml up -d xiaozhi-esp32-server-web
# 带登录 token 调(用智控台登录后拿到的 token):
curl -X POST 'http://localhost:8002/persona/switch' \
  -H 'Authorization: <token>' -H 'Content-Type: application/json' \
  -d '{"agentId":"<某agentId>"}'
docker exec xiaozhi-esp32-server-db mysql -uroot -p123456 xiaozhi_esp32_server -e \
  "SELECT user_id,agent_id,manual FROM ai_user_persona_assignment WHERE user_id=<某userId>;"
```
Expected: HTTP 200;DB 中该用户 `manual=1`、`agent_id` 为所传;下次对话立即用该角色。

- [ ] **Step 4: Commit**

```bash
git add main/manager-api/src/main/java/xiaozhi/modules/agent/controller/UserPersonaController.java
git commit -m "feat: 家长手动切换/恢复自动匹配角色接口"
```

---

## Task 8: 智控台按钮(最小 UI)

**Files:**
- Modify: `main/manager-web/src/` 下既有用户设备视图组件(挂「换角色」「恢复自动匹配」按钮)

> 定位:在用户侧看自己设备的页面(与 `UserShowDeviceListVO` 对应的前端组件)。若没有合适的现成位置,先在任一用户已登录可见的设备详情组件上加。

- [ ] **Step 1: 定位组件**

```bash
grep -rln "UserShowDeviceList\|我的设备\|/device/bind" main/manager-web/src --include=*.vue | head
```
选其中一个用户可见的 `.vue`,在其设备项操作区加按钮。

- [ ] **Step 2: 加按钮 + 调接口**

在选中组件的模板操作区加:
```vue
<el-dropdown @command="onSwitchPersona">
  <el-button size="small">换角色</el-button>
  <template #dropdown>
    <el-dropdown-item v-for="a in personaOptions" :key="a.id" :command="a.id">{{ a.agentName }}</el-dropdown-item>
  </template>
</el-dropdown>
<el-button size="small" @click="onResetAuto">恢复自动匹配</el-button>
```
脚本里(用项目既有 http 封装,通常是 `request`/`useRequest`,按组件现有写法):
```js
import request from '@/utils/request' // 以组件现有 import 为准

async function onSwitchPersona(agentId) {
  await request.post('/persona/switch', { agentId })
  // 既有消息提示组件,如 ElMessage.success('已切换')
}
async function onResetAuto() {
  await request.post('/persona/auto')
}
// personaOptions:从既有「角色列表」接口取(智控台已有 agent 列表接口),onMounted 拉
```

- [ ] **Step 3: 重建 web 镜像 + 验证**

```bash
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml build xiaozhi-esp32-server-web
docker compose -f /home/aipet/coding/xiaozhi-server/docker-compose_all.yml up -d xiaozhi-esp32-server-web
```
浏览器登录智控台 → 用户侧设备页 → 点「换角色」选一个 → 看 DB `manual=1` 且对话人设变化。
Expected: 按钮可点、切换生效。

- [ ] **Step 4: Commit**

```bash
git add main/manager-web/src/<选中组件路径>
git commit -m "feat: 智控台加「换角色/恢复自动匹配」按钮"
```

---

## 端到端验证(全部完成后)

1. **自动匹配**:某用户聊几天某主题 → 临时短 cron 跑一次 → `ai_user_persona_assignment` 出现该用户行,`manual=0`,角色贴合主题。
2. **保守不跳**:主题未明显变化,再跑一次 → `agent_id` 不变。
3. **手动粘性**:家长点「换角色」→ `manual=1`;再跑周任务 → 该用户被跳过,角色不被覆盖。
4. **回退**:删某用户映射行 → 对话用设备绑定 agent(行为同改造前)。
5. **共享**:两用户聊相似主题 → 匹配到同一 `agent_id`。
6. **隔离**:A 的匹配不影响 B。
7. 把 Task 5 的 cron 改回正式值 `0 30 3 ? * MON`,提交。
