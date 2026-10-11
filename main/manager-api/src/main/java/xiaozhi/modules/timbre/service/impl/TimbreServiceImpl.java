package xiaozhi.modules.timbre.service.impl;

import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import cn.hutool.core.collection.CollectionUtil;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.modules.model.dto.VoiceDTO;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.timbre.dao.TimbreDao;
import xiaozhi.modules.timbre.dto.TimbreDataDTO;
import xiaozhi.modules.timbre.dto.TimbrePageDTO;
import xiaozhi.modules.timbre.entity.TimbreEntity;
import xiaozhi.modules.timbre.service.TimbreService;
import xiaozhi.modules.timbre.vo.TimbreDetailsVO;
import xiaozhi.modules.voiceclone.dao.VoiceCloneDao;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

/**
 * Timbre business layer implementation
 *
 * @author zjy
 * @since 2025-3-21
 */
@AllArgsConstructor
@Service
public class TimbreServiceImpl extends BaseServiceImpl<TimbreDao, TimbreEntity> implements TimbreService {

    private static final Pattern LANGUAGE_SEPARATOR = Pattern.compile("[、；;,，]");

    private final TimbreDao timbreDao;
    private final VoiceCloneDao voiceCloneDao;
    private final RedisUtils redisUtils;

    @Override
    public PageData<TimbreDetailsVO> page(TimbrePageDTO dto) {
        Map<String, Object> params = new HashMap<String, Object>();
        params.put(Constant.PAGE, dto.getPage());
        params.put(Constant.LIMIT, dto.getLimit());
        IPage<TimbreEntity> page = baseDao.selectPage(
                getPage(params, null, true),
                // Define query conditions.
                new QueryWrapper<TimbreEntity>()
                        // Always filter by TTS model ID.
                        .eq("tts_model_id", dto.getTtsModelId())
                        // Apply fuzzy search when a timbre name is provided.
                        .like(StringUtils.isNotBlank(dto.getName()), "name", dto.getName()));

        return getPageData(page, TimbreDetailsVO.class);
    }

    @Override
    public TimbreDetailsVO get(String timbreId) {
        if (StringUtils.isBlank(timbreId)) {
            return null;
        }

        // Read from Redis cache first.
        String key = RedisKeys.getTimbreDetailsKey(timbreId);
        TimbreDetailsVO cachedDetails = (TimbreDetailsVO) redisUtils.get(key);
        if (cachedDetails != null) {
            return cachedDetails;
        }

        // Load from the database when the cache misses.
        TimbreEntity entity = baseDao.selectById(timbreId);
        if (entity == null) {
            return null;
        }

        // Convert to the response VO.
        TimbreDetailsVO details = ConvertUtils.sourceToTarget(entity, TimbreDetailsVO.class);

        // Store the result in Redis.
        if (details != null) {
            redisUtils.set(key, details);
        }

        return details;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(TimbreDataDTO dto) {
        isTtsModelId(dto.getTtsModelId());
        if (dto.getSort() == null) {
            dto.setSort(0L);
        }
        TimbreEntity timbreEntity = ConvertUtils.sourceToTarget(dto, TimbreEntity.class);
        baseDao.insert(timbreEntity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(String timbreId, TimbreDataDTO dto) {
        isTtsModelId(dto.getTtsModelId());
        TimbreEntity timbreEntity = ConvertUtils.sourceToTarget(dto, TimbreEntity.class);
        timbreEntity.setId(timbreId);
        baseDao.updateById(timbreEntity);
        // Invalidate cache.
        redisUtils.delete(RedisKeys.getTimbreDetailsKey(timbreId));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(String[] ids) {
        baseDao.deleteByIds(Arrays.asList(ids));
    }

    @Override
    public List<VoiceDTO> getVoiceNames(String ttsModelId, String voiceName) {
        QueryWrapper<TimbreEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("tts_model_id", StringUtils.isBlank(ttsModelId) ? "" : ttsModelId);
        if (StringUtils.isNotBlank(voiceName)) {
            queryWrapper.like("name", voiceName);
        }
        List<TimbreEntity> timbreEntities = Optional.ofNullable(timbreDao.selectList(queryWrapper)).orElseGet(ArrayList::new);
        List<VoiceDTO> voiceDTOs = timbreEntities.stream()
                .map(entity -> {
                    VoiceDTO dto = new VoiceDTO(entity.getId(), entity.getName());
                    dto.setVoiceDemo(entity.getVoiceDemo());
                    dto.setLanguages(entity.getLanguages()); // Preserve language metadata.
                    dto.setIsClone(false); // Mark as a standard timbre.
                    return dto;
                })
                .collect(Collectors.toList());

        // Resolve the current logged-in user.
        Long currentUserId = SecurityUser.getUser().getId();
        if (currentUserId != null) {
            // Load all trained clone-timbre records for the user.
            List<VoiceDTO> cloneEntities = voiceCloneDao.getTrainSuccess(ttsModelId, currentUserId);
            for (VoiceDTO entity : cloneEntities) {
                // Only include successfully trained clone timbres that match the model.
                VoiceDTO voiceDTO = new VoiceDTO();
                voiceDTO.setId(entity.getId());
                voiceDTO.setName(MessageUtils.getMessage(ErrorCode.VOICE_CLONE_PREFIX) + entity.getName());
                // Preserve the voiceDemo value returned from the database.
                voiceDTO.setVoiceDemo(entity.getVoiceDemo());
                voiceDTO.setLanguages(entity.getLanguages());
                voiceDTO.setIsClone(true); // Mark as a clone timbre.
                redisUtils.set(RedisKeys.getTimbreNameById(voiceDTO.getId()), voiceDTO.getName(),
                        RedisUtils.NOT_EXPIRE);
                voiceDTOs.add(0, voiceDTO);
            }
        }

        return CollectionUtil.isEmpty(voiceDTOs) ? null : voiceDTOs;
    }

    @Override
    public String getDefaultLanguageById(String id) {
        if (StringUtils.isBlank(id)) {
            return null;
        }

        TimbreEntity timbre = timbreDao.selectById(id);
        if (timbre != null) {
            return firstNonBlankLanguage(timbre.getLanguages());
        }

        VoiceCloneEntity voiceClone = voiceCloneDao.selectById(id);
        return voiceClone == null ? null : firstNonBlankLanguage(voiceClone.getLanguages());
    }

    private String firstNonBlankLanguage(String languages) {
        if (StringUtils.isBlank(languages)) {
            return null;
        }
        return LANGUAGE_SEPARATOR.splitAsStream(languages)
                .map(StringUtils::trimToNull)
                .filter(Objects::nonNull)
                .findFirst()
                .orElse(null);
    }

    /**
     * Process whether it is TTS model ID
     */
    private void isTtsModelId(String ttsModelId) {
        // Reserved for future validation against model configuration.
    }

    @Override
    public String getTimbreNameById(String id) {
        if (StringUtils.isBlank(id)) {
            return null;
        }

        String cachedName = (String) redisUtils.get(RedisKeys.getTimbreNameById(id));

        if (StringUtils.isNotBlank(cachedName)) {
            return cachedName;
        }

        TimbreEntity entity = timbreDao.selectById(id);
        if (entity != null) {
            String name = entity.getName();
            if (StringUtils.isNotBlank(name)) {
                redisUtils.set(RedisKeys.getTimbreNameById(id), name);
            }
            return name;
        } else {
            VoiceCloneEntity cloneEntity = voiceCloneDao.selectById(id);
            if (cloneEntity != null) {
                String name = MessageUtils.getMessage(ErrorCode.VOICE_CLONE_PREFIX) + cloneEntity.getName();
                redisUtils.set(RedisKeys.getTimbreNameById(id), name);
                return name;
            }
        }

        return null;
    }

    @Override
    public VoiceDTO getByVoiceCode(String ttsModelId, String voiceCode) {
        if (StringUtils.isBlank(voiceCode)) {
            return null;
        }
        QueryWrapper<TimbreEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("tts_model_id", ttsModelId);
        queryWrapper.eq("tts_voice", voiceCode);
        List<TimbreEntity> list = timbreDao.selectList(queryWrapper);
        if (list.isEmpty()) {
            return null;
        }
        TimbreEntity entity = list.get(0);
        VoiceDTO dto = new VoiceDTO(entity.getId(), entity.getName());
        dto.setVoiceDemo(entity.getVoiceDemo());
        dto.setIsClone(false); // Mark as a standard timbre.
        return dto;
    }
}
