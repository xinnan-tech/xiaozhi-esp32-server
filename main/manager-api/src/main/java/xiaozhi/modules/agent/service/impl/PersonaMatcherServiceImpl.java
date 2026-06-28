package xiaozhi.modules.agent.service.impl;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.PersonaMatcherService;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.llm.service.LLMService;

@Slf4j
@Service
public class PersonaMatcherServiceImpl implements PersonaMatcherService {

    /** 仅当新角色置信度高出当前 ≥ 此值才切换 */
    private static final BigDecimal SWITCH_SCORE_DELTA = new BigDecimal("0.20");

    @Autowired private AgentDao agentDao;
    @Autowired private AgentChatHistoryService agentChatHistoryService;
    @Autowired private DeviceDao deviceDao;
    @Autowired private LLMService llmService;
    @Autowired private UserPersonaAssignmentService userPersonaAssignmentService;

    @Override
    public void matchForUser(Long userId, int days, int limit, int minHistory) {
        // 1. 取该用户所有设备的 mac
        List<DeviceEntity> devices = deviceDao.selectList(
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
        List<AgentEntity> candidates = agentDao.selectList(null).stream()
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
