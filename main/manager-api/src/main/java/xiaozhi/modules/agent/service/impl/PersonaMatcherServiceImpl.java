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
import xiaozhi.modules.agent.vo.PersonaCandidateVO;
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
    public List<PersonaCandidateVO> listCandidatePersonas() {
        return agentDao.selectList(null).stream()
                .filter(a -> a.getSystemPrompt() != null && !a.getSystemPrompt().isBlank())
                .map(a -> {
                    PersonaCandidateVO vo = new PersonaCandidateVO();
                    vo.setId(a.getId());
                    vo.setAgentName(a.getAgentName());
                    return vo;
                })
                .collect(Collectors.toList());
    }

    @Override
    public void matchAllNonManualUsers() {
        // 遍历「有设备的用户」(而非已有 assignment —— 否则空表永远 seed 不了新用户)
        java.util.Set<Long> userIds = deviceDao.selectList(null).stream()
                .map(DeviceEntity::getUserId)
                .filter(java.util.Objects::nonNull)
                .collect(Collectors.toSet());
        log.info("[persona-match] 开始匹配,候选用户 {} 人", userIds.size());
        int matched = 0;
        for (Long userId : userIds) {
            UserPersonaAssignmentEntity a = userPersonaAssignmentService.getByUserId(userId);
            if (a != null && a.getManual() != null && a.getManual() == 1) {
                continue; // 家长手动设定,跳过
            }
            try {
                matchForUser(userId, 14, 50, 5);
                matched++;
            } catch (Exception ex) {
                log.warn("[persona-match] user={} 失败:{}", userId, ex.getMessage());
            }
        }
        log.info("[persona-match] 匹配完成,处理 {} 人", matched);
    }

    @Override
    public void matchForUser(Long userId, int days, int limit, int minHistory) {
        // 0. 取当前角色,manual=1 的用户跳过(保护手动设定,不覆盖)
        UserPersonaAssignmentEntity cur = userPersonaAssignmentService.getByUserId(userId);
        if (cur != null && cur.getManual() != null && cur.getManual() == 1) {
            log.info("[persona-match] user={} manual=1, skip", userId);
            return;
        }

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
        String conversation = buildConversation(topics, candidates, cur);
        String promptTemplate = buildInstruction();
        String resp;
        try {
            resp = llmService.generateSummary(conversation, promptTemplate, null);
        } catch (Exception e) {
            log.warn("[persona-match] user={} LLM 调用失败:{}", userId, e.getMessage());
            return;
        }

        // 5. 解析 + 校验编号 + 高阈值才写
        MatchResult mr = parse(resp);
        if (mr == null) {
            log.warn("[persona-match] user={} LLM 返回无法解析:{}", userId, resp);
            return;
        }
        // 校验编号在候选范围内(防 LLM 编造;不让 LLM 抄 id,只返回编号)
        if (mr.choice < 1 || mr.choice > candidates.size()) {
            log.warn("[persona-match] user={} LLM 返回 choice={} 超出范围(1~{}),跳过", userId, mr.choice, candidates.size());
            return;
        }
        String chosenAgentId = candidates.get(mr.choice - 1).getId();
        boolean shouldSwitch = cur == null
                || !chosenAgentId.equals(cur.getAgentId())
                && (cur.getScore() == null || mr.score.subtract(cur.getScore()).compareTo(SWITCH_SCORE_DELTA) >= 0);
        if (!shouldSwitch) {
            log.info("[persona-match] user={} 保留当前 agent={}(new={},score={})", userId,
                    cur == null ? null : cur.getAgentId(), chosenAgentId, mr.score);
            return;
        }
        userPersonaAssignmentService.upsertAuto(userId, chosenAgentId, mr.score, mr.reason);
        log.info("[persona-match] user={} 切换到 agent={} score={} reason={}", userId, chosenAgentId, mr.score, mr.reason);
    }

    private String buildConversation(String topics, List<AgentEntity> candidates, UserPersonaAssignmentEntity cur) {
        StringBuilder sb = new StringBuilder();
        sb.append("【孩子近期聊天】\n").append(topics).append("\n\n【候选陪伴角色】\n");
        int idx = 1;
        for (AgentEntity a : candidates) {
            String desc = a.getSystemPrompt();
            if (desc.length() > 120) desc = desc.substring(0, 120);
            sb.append(idx++).append(". ").append(a.getAgentName()).append(": ").append(desc).append("\n");
        }
        if (cur != null) {
            sb.append("\n【当前角色id】").append(cur.getAgentId());
        }
        return sb.toString();
    }

    private String buildInstruction() {
        return "你是儿童陪伴角色匹配器。根据【孩子近期聊天】从【候选陪伴角色】的编号列表里选最贴合的一个。"
                + "若【当前角色】已足够合适,务必保留当前(孩子需要稳定陪伴)。仅当另一角色明显更贴合时才换。"
                + "只返回JSON,不要多余文字:{\"choice\":选中角色的编号(整数),\"score\":0.0到1.0,\"reason\":\"一句话\"}";
    }

    private MatchResult parse(String resp) {
        if (resp == null) return null;
        int s = resp.indexOf('{'), e = resp.lastIndexOf('}');
        if (s < 0 || e <= s) return null;
        try {
            JSONObject j = JSONUtil.parseObj(resp.substring(s, e + 1));
            MatchResult mr = new MatchResult();
            mr.choice = j.getInt("choice", 0);
            mr.score = new BigDecimal(j.getStr("score", "0"));
            // score 越界(DB 列 DECIMAL(4,2) 上限 9.99,且语义上仅 [0,1] 有意义)视为不可解析,跳过写入
            if (mr.score.signum() < 0 || mr.score.compareTo(BigDecimal.ONE) > 0) {
                return null;
            }
            mr.reason = j.getStr("reason");
            return mr;
        } catch (Exception ex) {
            return null;
        }
    }

    private static class MatchResult {
        int choice;
        BigDecimal score;
        String reason;
    }
}
