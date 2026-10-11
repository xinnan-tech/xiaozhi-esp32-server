package xiaozhi.modules.correctword.service.impl;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.agent.dao.AgentCorrectWordMappingDao;
import xiaozhi.modules.correctword.dao.CorrectWordFileDao;
import xiaozhi.modules.correctword.dao.CorrectWordItemDao;
import xiaozhi.modules.correctword.dto.CorrectWordFileCreateDTO;
import xiaozhi.modules.agent.entity.AgentCorrectWordMappingEntity;
import xiaozhi.modules.correctword.entity.CorrectWordFileEntity;
import xiaozhi.modules.correctword.entity.CorrectWordItemEntity;
import xiaozhi.modules.correctword.service.CorrectWordFileService;
import xiaozhi.modules.correctword.vo.CorrectWordFileVO;
import xiaozhi.modules.correctword.vo.CorrectWordSimpleVO;
import xiaozhi.modules.security.user.SecurityUser;

@Service
@AllArgsConstructor
public class CorrectWordFileServiceImpl extends BaseServiceImpl<CorrectWordFileDao, CorrectWordFileEntity>
        implements CorrectWordFileService {

    private final CorrectWordFileDao correctWordFileDao;
    private final CorrectWordItemDao correctWordItemDao;
    private final AgentCorrectWordMappingDao agentCorrectWordMappingDao;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CorrectWordFileVO createFile(CorrectWordFileCreateDTO dto) {
        // Validate that file size does not exceed 1MB
        if (dto.getFileSize() != null && dto.getFileSize() > 1024 * 1024) {
            throw new RenException(ErrorCode.FILE_SIZE_OVER_LIMIT);
        }

        // Validate if filename is duplicate
        Long userId = SecurityUser.getUserId();
        LambdaQueryWrapper<CorrectWordFileEntity> nameWrapper = new LambdaQueryWrapper<>();
        nameWrapper.eq(CorrectWordFileEntity::getCreator, userId)
                .eq(CorrectWordFileEntity::getFileName, dto.getFileName());
        if (correctWordFileDao.selectCount(nameWrapper) > 0) {
            throw new RenException(ErrorCode.CORRECT_WORD_FILE_NAME_EXISTS);
        }

        List<CorrectWordItemEntity> items = parseContent(dto.getContent());

        // Save file records
        CorrectWordFileEntity fileEntity = new CorrectWordFileEntity();
        fileEntity.setFileName(dto.getFileName());
        fileEntity.setWordCount(items.size());
        fileEntity.setContent(String.join("\n", dto.getContent()));
        fileEntity.setCreator(SecurityUser.getUserId());
        fileEntity.setCreatedAt(new Date());
        correctWordFileDao.insert(fileEntity);

        // Set fileId and batch save entries
        String fileId = fileEntity.getId();
        for (CorrectWordItemEntity item : items) {
            item.setFileId(fileId);
        }
        if (!items.isEmpty()) {
            correctWordItemDao.batchInsert(items);
        }

        return toVO(fileEntity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateFile(String fileId, CorrectWordFileCreateDTO dto) {
        CorrectWordFileEntity fileEntity = correctWordFileDao.selectById(fileId);
        if (fileEntity == null) {
            return;
        }

        // Check for duplicate filenames (excluding self).
        Long userId = SecurityUser.getUserId();
        LambdaQueryWrapper<CorrectWordFileEntity> nameWrapper = new LambdaQueryWrapper<>();
        nameWrapper.eq(CorrectWordFileEntity::getCreator, userId)
                .eq(CorrectWordFileEntity::getFileName, dto.getFileName())
                .ne(CorrectWordFileEntity::getId, fileId);
        if (correctWordFileDao.selectCount(nameWrapper) > 0) {
            throw new RenException("File name already exists:" + dto.getFileName());
        }

        // Delete old entries first
        LambdaQueryWrapper<CorrectWordItemEntity> deleteWrapper = new LambdaQueryWrapper<>();
        deleteWrapper.eq(CorrectWordItemEntity::getFileId, fileId);
        correctWordItemDao.delete(deleteWrapper);

        // Parse new entries and batch save
        List<CorrectWordItemEntity> items = parseContent(dto.getContent());
        if (!items.isEmpty()) {
            for (CorrectWordItemEntity item : items) {
                item.setFileId(fileId);
            }
            correctWordItemDao.batchInsert(items);
        }

        // Update file record
        fileEntity.setFileName(dto.getFileName());
        fileEntity.setWordCount(items.size());
        fileEntity.setContent(String.join("\n", dto.getContent()));
        fileEntity.setUpdater(SecurityUser.getUserId());
        fileEntity.setUpdatedAt(new Date());
        correctWordFileDao.updateById(fileEntity);
    }

    @Override
    public PageData<CorrectWordFileVO> listFiles(Map<String, Object> params) {
        Long userId = SecurityUser.getUserId();
        IPage<CorrectWordFileEntity> page = getPage(params, "created_at", false);
        LambdaQueryWrapper<CorrectWordFileEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(CorrectWordFileEntity::getCreator, userId)
                .orderByDesc(CorrectWordFileEntity::getCreatedAt);
        correctWordFileDao.selectPage(page, wrapper);
        List<CorrectWordFileVO> voList = toVOList(page.getRecords());
        return new PageData<>(voList, page.getTotal());
    }

    @Override
    public List<CorrectWordFileVO> listAllFiles() {
        Long userId = SecurityUser.getUserId();
        LambdaQueryWrapper<CorrectWordFileEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(CorrectWordFileEntity::getCreator, userId)
                .orderByDesc(CorrectWordFileEntity::getCreatedAt);
        List<CorrectWordFileEntity> entities = correctWordFileDao.selectList(wrapper);
        return toVOList(entities);
    }

    @Override
    public CorrectWordFileVO getFileContent(String fileId) {
        CorrectWordFileEntity entity = correctWordFileDao.selectById(fileId);
        return toVO(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteFile(String fileId) {
        if (fileId == null || fileId.trim().isEmpty()) {
            return;
        }
        // Delete associated table records first
        agentCorrectWordMappingDao.deleteByFileId(fileId);
        // Delete entry
        LambdaQueryWrapper<CorrectWordItemEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(CorrectWordItemEntity::getFileId, fileId);
        correctWordItemDao.delete(wrapper);
        // Delete File
        correctWordFileDao.deleteById(fileId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteMappingsByAgentId(String agentId) {
        agentCorrectWordMappingDao.deleteByAgentId(agentId);
    }

    @Override
    public List<CorrectWordSimpleVO> getAllItemsByAgentId(String agentId) {
        // Get file ID list via association table
        List<AgentCorrectWordMappingEntity> mappings = agentCorrectWordMappingDao.selectByAgentId(agentId);
        if (mappings == null || mappings.isEmpty()) {
            return new ArrayList<>();
        }
        List<String> fileIds = mappings.stream()
                .map(AgentCorrectWordMappingEntity::getFileId)
                .collect(Collectors.toList());

        // Query entries by file ID list
        LambdaQueryWrapper<CorrectWordItemEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(CorrectWordItemEntity::getFileId, fileIds);
        List<CorrectWordItemEntity> entities = correctWordItemDao.selectList(wrapper);
        return ConvertUtils.sourceToTarget(entities, CorrectWordSimpleVO.class);
    }

    @Override
    public List<String> getAgentCorrectWordFileIds(String agentId) {
        List<AgentCorrectWordMappingEntity> mappings = agentCorrectWordMappingDao.selectByAgentId(agentId);
        if (mappings == null || mappings.isEmpty()) {
            return new ArrayList<>();
        }
        return mappings.stream()
                .map(AgentCorrectWordMappingEntity::getFileId)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveAgentCorrectWords(String agentId, List<String> fileIds) {
        // Delete old association records first
        agentCorrectWordMappingDao.deleteByAgentId(agentId);

        if (fileIds == null || fileIds.isEmpty()) {
            return;
        }

        // Batch insert new association records
        Long userId = SecurityUser.getUserId();
        Date now = new Date();
        List<AgentCorrectWordMappingEntity> mappings = new ArrayList<>();
        for (String fileId : fileIds) {
            AgentCorrectWordMappingEntity mapping = new AgentCorrectWordMappingEntity();
            mapping.setAgentId(agentId);
            mapping.setFileId(fileId);
            mapping.setCreator(userId);
            mapping.setCreatedAt(now);
            mapping.setUpdater(userId);
            mapping.setUpdatedAt(now);
            mappings.add(mapping);
        }
        agentCorrectWordMappingDao.batchInsertMapping(mappings);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void batchDeleteFiles(List<String> fileIds) {
        if (fileIds == null || fileIds.isEmpty()) {
            return;
        }
        for (String fileId : fileIds) {
            if (fileId == null || fileId.trim().isEmpty()) {
                continue;
            }
            deleteFile(fileId.trim());
        }
    }

    /**
     * Parse replacement words, each line format: original|replacement
     */
    private List<CorrectWordItemEntity> parseContent(List<String> lines) {
        List<CorrectWordItemEntity> items = new ArrayList<>();
        if (lines == null || lines.isEmpty()) {
            return items;
        }
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) {
                continue;
            }
            int idx = line.indexOf('|');
            if (idx <= 0 || idx >= line.length() - 1) {
                continue;
            }
            String sourceWord = line.substring(0, idx).trim();
            String targetWord = line.substring(idx + 1).trim();
            if (sourceWord.isEmpty() || targetWord.isEmpty()) {
                continue;
            }
            CorrectWordItemEntity item = new CorrectWordItemEntity();
            item.setSourceWord(sourceWord);
            item.setTargetWord(targetWord);
            items.add(item);
        }
        return items;
    }

    private CorrectWordFileVO toVO(CorrectWordFileEntity entity) {
        if (entity == null) {
            return null;
        }
        CorrectWordFileVO vo = new CorrectWordFileVO();
        vo.setId(entity.getId());
        vo.setFileName(entity.getFileName());
        vo.setWordCount(entity.getWordCount());
        vo.setContent(entity.getContent() != null
                ? Arrays.asList(entity.getContent().split("\n"))
                : new ArrayList<>());
        vo.setCreatedAt(entity.getCreatedAt());
        vo.setUpdatedAt(entity.getUpdatedAt());
        return vo;
    }

    private List<CorrectWordFileVO> toVOList(List<CorrectWordFileEntity> entities) {
        if (entities == null || entities.isEmpty()) {
            return new ArrayList<>();
        }
        return entities.stream().map(this::toVO).collect(Collectors.toList());
    }
}
