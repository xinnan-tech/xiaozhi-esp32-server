package xiaozhi.modules.agent.service.impl;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.collection.ListUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.Enums.AgentChatHistoryType;
import xiaozhi.modules.agent.dao.AiAgentChatHistoryDao;
import xiaozhi.modules.agent.dto.AgentChatHistoryDTO;
import xiaozhi.modules.agent.dto.AgentChatSessionDTO;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentChatTitleService;
import xiaozhi.modules.agent.vo.AgentChatHistoryUserVO;

/**
 * Chat-history service implementation for agents.
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
@Service
@RequiredArgsConstructor
public class AgentChatHistoryServiceImpl extends CrudRepository<AiAgentChatHistoryDao, AgentChatHistoryEntity>
        implements AgentChatHistoryService {

    private final AgentChatTitleService agentChatTitleService;

    @Override
    public PageData<AgentChatSessionDTO> getSessionListByAgentId(Map<String, Object> params) {
        String agentId = (String) params.get("agentId");
        int page = Integer.parseInt(params.get(Constant.PAGE).toString());
        int limit = Integer.parseInt(params.get(Constant.LIMIT).toString());

        // Build query conditions.
        QueryWrapper<AgentChatHistoryEntity> wrapper = new QueryWrapper<>();
        wrapper.select("session_id", "MAX(created_at) as created_at", "COUNT(*) as chat_count")
                .eq("agent_id", agentId)
                .groupBy("session_id")
                .orderByDesc("created_at");

        // Run the paginated query.
        Page<Map<String, Object>> pageParam = new Page<>(page, limit);
        IPage<Map<String, Object>> result = this.baseMapper.selectMapsPage(pageParam, wrapper);

        List<AgentChatSessionDTO> records = result.getRecords().stream().map(map -> {
            AgentChatSessionDTO dto = new AgentChatSessionDTO();
            dto.setSessionId((String) map.get("session_id"));
            dto.setCreatedAt((LocalDateTime) map.get("created_at"));
            dto.setChatCount(((Number) map.get("chat_count")).intValue());
            dto.setTitle(agentChatTitleService.getTitleBySessionId(dto.getSessionId()));
            return dto;
        }).collect(Collectors.toList());

        return new PageData<>(records, result.getTotal());
    }

    @Override
    public List<AgentChatHistoryDTO> getChatHistoryBySessionId(String agentId, String sessionId) {
        // Build query conditions.
        QueryWrapper<AgentChatHistoryEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("agent_id", agentId)
                .eq("session_id", sessionId)
                .orderByAsc("created_at");

        // Query chat history.
        List<AgentChatHistoryEntity> historyList = list(wrapper);

        // Convert to DTOs.
        return ConvertUtils.sourceToTarget(historyList, AgentChatHistoryDTO.class);
    }

    @Override
    public String getAgentIdBySessionId(String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            return null;
        }
        AgentChatHistoryEntity entity = baseMapper.selectOne(
                new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .select(AgentChatHistoryEntity::getAgentId)
                        .eq(AgentChatHistoryEntity::getSessionId, sessionId)
                        .last("LIMIT 1"));
        return entity == null ? null : entity.getAgentId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteByAgentId(String agentId, Boolean deleteAudio, Boolean deleteText) {
        if (deleteAudio) {
            // Delete audio in batches to avoid timeouts.
            List<String> audioIds = baseMapper.getAudioIdsByAgentId(agentId);
            if (ToolUtil.isNotEmpty(audioIds)) {
                // Delete 1000 rows per batch.
                List<List<String>> batch = ListUtil.split(audioIds, 1000);
                batch.forEach(dataList -> {
                    baseMapper.deleteAudioByIds(dataList);
                });
            }
        }
        if (deleteAudio && !deleteText) {
            baseMapper.deleteAudioIdByAgentId(agentId);
        }
        if (deleteText) {
            baseMapper.deleteHistoryByAgentId(agentId);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteBySessionId(String agentId, String sessionId) {
        LambdaQueryWrapper<AgentChatHistoryEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AgentChatHistoryEntity::getAgentId, agentId)
                .eq(AgentChatHistoryEntity::getSessionId, sessionId);
        baseMapper.delete(wrapper);
    }

    @Override
    public List<AgentChatHistoryUserVO> getRecentlyFiftyByAgentId(String agentId) {
        // Build query conditions without sorting by created_at.
        // In practice a larger primary key means a later creation time, which is cheaper to paginate.
        LambdaQueryWrapper<AgentChatHistoryEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.select(AgentChatHistoryEntity::getContent, AgentChatHistoryEntity::getAudioId)
                .eq(AgentChatHistoryEntity::getAgentId, agentId)
                .eq(AgentChatHistoryEntity::getChatType, AgentChatHistoryType.USER.getValue())
                .isNotNull(AgentChatHistoryEntity::getAudioId)
                // Use descending ID order because it aligns with creation time and is index-friendly.
                .orderByDesc(AgentChatHistoryEntity::getId);

        // Query the most recent 50 records.
        Page<AgentChatHistoryEntity> pageParam = new Page<>(0, 50);
        IPage<AgentChatHistoryEntity> result = this.baseMapper.selectPage(pageParam, wrapper);
        return result.getRecords().stream().map(item -> {
            AgentChatHistoryUserVO vo = ConvertUtils.sourceToTarget(item, AgentChatHistoryUserVO.class);
            // Normalize content so only the chat text is returned.
            if (vo != null && vo.getContent() != null) {
                vo.setContent(extractContentFromString(vo.getContent()));
            }
            return vo;
        }).toList();
    }

    /**
     * Extract chat text from the content field.
     * If content is JSON such as {"speaker": "...", "content": "..."}, the inner content field is returned.
     * Otherwise the original string is returned unchanged.
     *
     * @param content raw content
     * @return extracted chat content
     */
    private String extractContentFromString(String content) {
        if (content == null || content.trim().isEmpty()) {
            return content;
        }

        // Try to parse the content as JSON.
        try {
            Map<String, Object> jsonMap = JsonUtils.parseMap(content);
            if (jsonMap != null && jsonMap.containsKey("content")) {
                Object contentObj = jsonMap.get("content");
                return contentObj != null ? contentObj.toString() : content;
            }
        } catch (Exception e) {
            // If parsing fails, fall back to the original content.
        }

        // Return the original content if no nested content field is present.
        return content;
    }

    @Override
    public String getContentByAudioId(String audioId) {
        AgentChatHistoryEntity agentChatHistoryEntity = baseMapper
                .selectOne(new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .select(AgentChatHistoryEntity::getContent)
                        .eq(AgentChatHistoryEntity::getAudioId, audioId));
        return agentChatHistoryEntity == null ? null : agentChatHistoryEntity.getContent();
    }

    @Override
    public String getAgentIdByAudioId(String audioId) {
        if (audioId == null || audioId.isBlank()) {
            return null;
        }
        AgentChatHistoryEntity entity = baseMapper.selectOne(
                new LambdaQueryWrapper<AgentChatHistoryEntity>()
                        .select(AgentChatHistoryEntity::getAgentId)
                        .eq(AgentChatHistoryEntity::getAudioId, audioId)
                        .last("LIMIT 1"));
        return entity == null ? null : entity.getAgentId();
    }

    @Override
    public boolean isAudioOwnedByAgent(String audioId, String agentId) {
        // Check whether exactly one record exists for the given audio ID and agent ID.
        Long row = baseMapper.selectCount(new LambdaQueryWrapper<AgentChatHistoryEntity>()
                .eq(AgentChatHistoryEntity::getAudioId, audioId)
                .eq(AgentChatHistoryEntity::getAgentId, agentId));
        return row == 1;
    }
}
