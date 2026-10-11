package xiaozhi.modules.voiceclone.service.impl;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.databind.ObjectMapper;

import cn.hutool.core.collection.CollUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.DateUtils;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysUserService;
import xiaozhi.modules.voiceclone.dao.VoiceCloneDao;
import xiaozhi.modules.voiceclone.dto.VoiceCloneDTO;
import xiaozhi.modules.voiceclone.dto.VoiceCloneResponseDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;
import xiaozhi.modules.voiceclone.service.VoiceCloneService;

@Slf4j
@Service
@RequiredArgsConstructor
public class VoiceCloneServiceImpl extends BaseServiceImpl<VoiceCloneDao, VoiceCloneEntity>
        implements VoiceCloneService {

    private static final Set<String> SUPPORTED_VOICE_CLONE_TYPES = Set.of();

    private final ModelConfigService modelConfigService;
    private final SysUserService sysUserService;
    private final SysUserDao sysUserDao;
    private final ObjectMapper objectMapper;

    @Override
    public PageData<VoiceCloneEntity> page(Map<String, Object> params) {
        IPage<VoiceCloneEntity> page = baseDao.selectPage(
                getPage(params, "create_date", true),
                getWrapper(params));

        return new PageData<>(page.getRecords(), page.getTotal());
    }

    private QueryWrapper<VoiceCloneEntity> getWrapper(Map<String, Object> params) {
        String name = (String) params.get("name");
        String userId = (String) params.get("userId");

        QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
        wrapper.eq(StringUtils.isNotBlank(userId), "user_id", userId);
        if (StringUtils.isNotBlank(name)) {
            wrapper.and(w -> w.like("name", name)
                    .or().eq("voice_id", name));
        }
        return wrapper;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(VoiceCloneDTO dto) {
        ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(dto.getModelId());
        if (modelConfig == null || modelConfig.getConfigJson() == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_MODEL_CONFIG_NOT_FOUND);
        }
        Map<String, Object> config = modelConfig.getConfigJson();
        String type = (String) config.get("type");
        if (StringUtils.isBlank(type)) {
            throw new RenException(ErrorCode.VOICE_CLONE_MODEL_TYPE_NOT_FOUND);
        }

        // Validate voice IDs
        for (String voiceId : dto.getVoiceIds()) {
            if (StringUtils.isBlank(voiceId)) {
                continue;
            }
            if (!SUPPORTED_VOICE_CLONE_TYPES.contains(type)) {
                throw new RenException(ErrorCode.VOICE_CLONE_MODEL_TYPE_NOT_FOUND);
            }

            QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
            wrapper.eq("voice_id", voiceId);
            wrapper.eq("model_id", dto.getModelId());
            Long count = baseDao.selectCount(wrapper);
            if (count > 0) {
                throw new RenException(ErrorCode.VOICE_ID_ALREADY_EXISTS);
            }
        }

        // Save records in batch.
        List<VoiceCloneEntity> batchInsertList = new ArrayList<>();
        // Create one record for each selected voice ID.
        int index = 0;
        String namePrefix = DateUtils.format(new Date(), "MMddHHmm");
        for (String voiceId : dto.getVoiceIds()) {
            index++;
            VoiceCloneEntity entity = new VoiceCloneEntity();
            entity.setModelId(dto.getModelId());
            entity.setVoiceId(voiceId);
            entity.setName(namePrefix + "_" + index);
            entity.setUserId(dto.getUserId());
            entity.setLanguages(dto.getLanguages());
            entity.setTrainStatus(0); // Default to training in progress.
            batchInsertList.add(entity);
        }
        if (CollUtil.isNotEmpty(batchInsertList)) {
            insertBatch(batchInsertList);
        }
    }

    @Override
    public void delete(String[] ids) {
        baseDao.deleteByIds(Arrays.asList(ids));
    }

    @Override
    public List<VoiceCloneEntity> getByUserId(Long userId) {
        QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        wrapper.orderByDesc("created_at");
        return baseDao.selectList(wrapper);
    }

    @Override
    public PageData<VoiceCloneResponseDTO> pageWithNames(Map<String, Object> params) {
        // Query paginated data first.
        IPage<VoiceCloneEntity> page = baseDao.selectPage(
                getPage(params, "create_date", true),
                getWrapper(params));

        // Convert entity records into DTOs.
        List<VoiceCloneResponseDTO> dtoList = convertToResponseDTOList(page.getRecords());

        return new PageData<>(dtoList, page.getTotal());
    }

    @Override
    public VoiceCloneResponseDTO getByIdWithNames(String id) {
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            return null;
        }

        VoiceCloneResponseDTO dto = ConvertUtils.sourceToTarget(entity, VoiceCloneResponseDTO.class);

        // Set the model name.
        if (StringUtils.isNotBlank(entity.getModelId())) {
            dto.setModelName(modelConfigService.getModelNameById(entity.getModelId()));
        }

        // Set the username.
        if (entity.getUserId() != null) {
            dto.setUserName(sysUserService.getByUserId(entity.getUserId()).getUsername());
        }
        
        // Preserve trainStatus because the frontend uses it to identify cloned audio.
        dto.setTrainStatus(entity.getTrainStatus());

        return dto;
    }

    @Override
    public List<VoiceCloneResponseDTO> getByUserIdWithNames(Long userId) {
        List<VoiceCloneEntity> entityList = getByUserId(userId);
        return convertToResponseDTOList(entityList);
    }

    /**
     * Convert VoiceCloneEntity records into VoiceCloneResponseDTO records.
     */
    private List<VoiceCloneResponseDTO> convertToResponseDTOList(List<VoiceCloneEntity> entityList) {
        if (entityList == null || entityList.isEmpty()) {
            return new ArrayList<>();
        }

        List<VoiceCloneResponseDTO> dtoList = new ArrayList<>(entityList.size());

        // Collect user IDs for username lookup.
        Set<Long> userIdList = entityList.stream().map(VoiceCloneEntity::getUserId).collect(Collectors.toSet());
        List<SysUserEntity> userList = sysUserDao.selectList(new QueryWrapper<SysUserEntity>().in("id", userIdList));
        Map<Long, String> userMap = userList.stream().collect(Collectors.toMap(SysUserEntity::getId, SysUserEntity::getUsername));

        // Convert each entity into a DTO.
        for (VoiceCloneEntity entity : entityList) {
            VoiceCloneResponseDTO dto = ConvertUtils.sourceToTarget(entity, VoiceCloneResponseDTO.class);

            // Set the model name.
            if (StringUtils.isNotBlank(entity.getModelId())) {
                dto.setModelName(modelConfigService.getModelNameById(entity.getModelId()));
            }

            // Set the username.
            if (entity.getUserId() != null) {
                dto.setUserName(userMap.get(entity.getUserId()));
            }
            
            // Preserve trainStatus because the frontend uses it to identify cloned audio.
            dto.setTrainStatus(entity.getTrainStatus());

            // Set whether audio data is present.
            dto.setHasVoice(entity.getVoice() != null);

            dtoList.add(dto);
        }

        return dtoList;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void uploadVoice(String id, MultipartFile voiceFile) throws Exception {
        // Load the voice-clone record.
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }

        // Read the uploaded audio into a byte array.
        byte[] voiceData = voiceFile.getBytes();

        // Update the voice payload.
        entity.setVoice(voiceData);
        // Reset training status to pending.
        entity.setTrainStatus(0);

        // Persist the update.
        baseDao.updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateName(String id, String name) {
        // Load the voice-clone record.
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }

        // Update the display name.
        entity.setName(name);
        baseDao.updateById(entity);
    }

    @Override
    public byte[] getVoiceData(String id) {
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            return null;
        }
        return entity.getVoice();
    }

    @Override
    // @Transactional(rollbackFor = Exception.class)
    public void cloneAudio(String cloneId) {
        VoiceCloneEntity entity = baseDao.selectById(cloneId);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }
        if (entity.getVoice() == null || entity.getVoice().length == 0) {
            throw new RenException(ErrorCode.VOICE_CLONE_AUDIO_NOT_UPLOADED);
        }

        try {

            ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(entity.getModelId());
            if (modelConfig == null || modelConfig.getConfigJson() == null) {
                throw new RenException(ErrorCode.VOICE_CLONE_MODEL_CONFIG_NOT_FOUND);
            }
            Map<String, Object> config = modelConfig.getConfigJson();
            String type = (String) config.get("type");
            if (StringUtils.isBlank(type) || !SUPPORTED_VOICE_CLONE_TYPES.contains(type)) {
                throw new RenException(ErrorCode.VOICE_CLONE_MODEL_TYPE_NOT_FOUND);
            }
        } catch (RenException re) {
            entity.setTrainStatus(3);
            entity.setTrainError(re.getMsg());
            baseDao.updateById(entity);
            throw re;
        } catch (Exception e) {
            e.printStackTrace();
            entity.setTrainStatus(3);
            entity.setTrainError(e.getMessage());
            baseDao.updateById(entity);
            throw new RenException(ErrorCode.VOICE_CLONE_TRAINING_FAILED, e.getMessage());
        }
    }

}
