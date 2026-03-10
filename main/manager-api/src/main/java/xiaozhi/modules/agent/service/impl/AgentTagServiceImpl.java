package xiaozhi.modules.agent.service.impl;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.agent.dao.AgentTagDao;
import xiaozhi.modules.agent.dao.AgentTagRelationDao;
import xiaozhi.modules.agent.dto.AgentTagDTO;
import xiaozhi.modules.agent.entity.AgentTagEntity;
import xiaozhi.modules.agent.entity.AgentTagRelationEntity;
import xiaozhi.modules.agent.service.AgentTagService;

@Service
@AllArgsConstructor
public class AgentTagServiceImpl extends BaseServiceImpl<AgentTagDao, AgentTagEntity> implements AgentTagService {

    private final AgentTagRelationDao agentTagRelationDao;

    @Override
    public AgentTagEntity saveTag(String tagName) {
        if (tagName == null || tagName.trim().isEmpty()) {
            throw new RenException(ErrorCode.AGENT_TAG_NAME_EMPTY);
        }

        QueryWrapper<AgentTagEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("tag_name", tagName);
        wrapper.eq("deleted", 0);
        AgentTagEntity existTag = baseDao.selectOne(wrapper);
        if (existTag != null) {
            return existTag;
        }

        AgentTagEntity tag = new AgentTagEntity();
        tag.setId(UUID.randomUUID().toString().replace("-", ""));
        tag.setTagName(tagName);
        tag.setSort(0);
        tag.setCreatedAt(new Date());
        tag.setUpdatedAt(new Date());
        tag.setDeleted(0);
        baseDao.insert(tag);
        return tag;
    }

    @Override
    public void deleteTag(String tagId) {
        AgentTagEntity tag = baseDao.selectById(tagId);
        if (tag != null) {
            tag.setDeleted(1);
            tag.setUpdatedAt(new Date());
            baseDao.updateById(tag);
        }
    }

    @Override
    public List<AgentTagDTO> getTagsByAgentId(String agentId) {
        List<AgentTagEntity> tags = baseDao.selectByAgentId(agentId);
        return tags.stream().map(this::convertToDTO).collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveAgentTags(String agentId, List<String> tagIds, List<String> tagNames) {
        agentTagRelationDao.deleteByAgentId(agentId);

        List<AgentTagEntity> currentTags = baseDao.selectByAgentId(agentId);
        List<String> currentTagNames = currentTags.stream()
                .map(AgentTagEntity::getTagName)
                .collect(Collectors.toList());

        List<String> allTagIds = new ArrayList<>();
        List<String> newTagNames = new ArrayList<>();

        if (tagNames != null && !tagNames.isEmpty()) {
            Set<String> addedTagNames = new HashSet<>();
            for (String tagName : tagNames) {
                if (tagName == null || tagName.trim().isEmpty()) {
                    throw new RenException(ErrorCode.AGENT_TAG_NAME_EMPTY);
                }

                if (currentTagNames.contains(tagName) || addedTagNames.contains(tagName)) {
                    throw new RenException(ErrorCode.AGENT_TAG_NAME_DUPLICATE);
                }
                addedTagNames.add(tagName);
                newTagNames.add(tagName);
            }
        }

        List<AgentTagEntity> existTags = new ArrayList<>();
        if (!newTagNames.isEmpty()) {
            existTags = baseDao.selectByTagNames(newTagNames);
        }

        Map<String, AgentTagEntity> existTagMap = existTags.stream()
                .collect(Collectors.toMap(AgentTagEntity::getTagName, t -> t, (a, b) -> a));

        List<AgentTagEntity> tagsToInsert = new ArrayList<>();
        for (String tagName : newTagNames) {
            AgentTagEntity existTag = existTagMap.get(tagName);
            if (existTag != null) {
                allTagIds.add(existTag.getId());
            } else {
                AgentTagEntity tag = new AgentTagEntity();
                tag.setId(UUID.randomUUID().toString().replace("-", ""));
                tag.setTagName(tagName);
                tag.setSort(0);
                tag.setDeleted(0);
                tag.setCreatedAt(new Date());
                tag.setUpdatedAt(new Date());
                tagsToInsert.add(tag);
            }
        }

        if (!tagsToInsert.isEmpty()) {
            baseDao.batchInsert(tagsToInsert);
            for (AgentTagEntity tag : tagsToInsert) {
                allTagIds.add(tag.getId());
            }
        }

        if (tagIds != null && !tagIds.isEmpty()) {
            List<AgentTagEntity> tagIdEntities = baseDao.selectBatchIds(tagIds);
            for (AgentTagEntity tag : tagIdEntities) {
                if (tag != null && (currentTagNames.contains(tag.getTagName()) ||
                        newTagNames.contains(tag.getTagName()))) {
                    throw new RenException(ErrorCode.AGENT_TAG_NAME_DUPLICATE);
                }
            }
            allTagIds.addAll(tagIds);
        }

        if (allTagIds.isEmpty()) {
            return;
        }

        List<AgentTagRelationEntity> relations = new ArrayList<>();
        Date now = new Date();
        int sort = 0;
        for (String tagId : allTagIds) {
            AgentTagRelationEntity relation = new AgentTagRelationEntity();
            relation.setId(UUID.randomUUID().toString().replace("-", ""));
            relation.setAgentId(agentId);
            relation.setTagId(tagId);
            relation.setSort(sort++);
            relation.setCreatedAt(now);
            relation.setUpdatedAt(now);
            relations.add(relation);
        }
        agentTagRelationDao.batchInsertRelation(relations);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAgentTags(String agentId) {
        agentTagRelationDao.deleteByAgentId(agentId);
    }

    @Override
    public List<AgentTagDTO> getTagsByAgentIds(List<String> agentIds) {
        if (agentIds == null || agentIds.isEmpty()) {
            return List.of();
        }
        List<AgentTagEntity> tags = baseDao.selectByAgentIds(agentIds);
        return tags.stream().map(this::convertToDTO).collect(Collectors.toList());
    }

    @Override
    public List<AgentTagDTO> getAllTags() {
        List<AgentTagEntity> tags = baseDao.selectAll();
        return tags.stream().map(this::convertToDTO).collect(Collectors.toList());
    }

    @Override
    public List<String> getAgentIdsByTagName(String tagName) {
        return baseDao.selectAgentIdsByTagName(tagName);
    }

    private AgentTagDTO convertToDTO(AgentTagEntity entity) {
        AgentTagDTO dto = new AgentTagDTO();
        dto.setId(entity.getId());
        dto.setTagName(entity.getTagName());
        return dto;
    }
}
