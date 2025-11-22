package xiaozhi.modules.voiceclone.service.impl;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.DateUtils;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
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

    private final ModelConfigService modelConfigService;
    private final SysUserService sysUserService;
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

        // 检查Voice ID是否已经被使用
        for (String voiceId : dto.getVoiceIds()) {
            if (StringUtils.isBlank(voiceId)) {
                continue;
            }
            if (Constant.VOICE_CLONE_HUOSHAN_DOUBLE_STREAM.equals(type)) {
                if (voiceId.indexOf("S_") == -1) {
                    throw new RenException(ErrorCode.VOICE_CLONE_HUOSHAN_VOICE_ID_ERROR);
                }
            }

            QueryWrapper<VoiceCloneEntity> wrapper = new QueryWrapper<>();
            wrapper.eq("voice_id", voiceId);
            wrapper.eq("model_id", dto.getModelId());
            Long count = baseDao.selectCount(wrapper);
            if (count > 0) {
                throw new RenException(ErrorCode.VOICE_ID_ALREADY_EXISTS);
            }
        }

        // 遍历选择的音色ID，为每个音色ID创建一条记录
        int index = 0;
        String namePrefix = DateUtils.format(new java.util.Date(), "MMddHHmm");
        for (String voiceId : dto.getVoiceIds()) {
            index++;
            VoiceCloneEntity entity = new VoiceCloneEntity();
            entity.setModelId(dto.getModelId());
            entity.setVoiceId(voiceId);
            entity.setName(namePrefix + "_" + index);
            entity.setUserId(dto.getUserId());
            entity.setTrainStatus(0); // 默认训练中

            baseDao.insert(entity);
        }
    }

    @Override
    public void delete(String[] ids) {
        baseDao.deleteBatchIds(Arrays.asList(ids));
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
        // 先查询分页数据
        IPage<VoiceCloneEntity> page = baseDao.selectPage(
                getPage(params, "create_date", true),
                getWrapper(params));

        // 将实体列表转换为DTO列表
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

        // 设置模型名称
        if (StringUtils.isNotBlank(entity.getModelId())) {
            dto.setModelName(modelConfigService.getModelNameById(entity.getModelId()));
        }

        // 设置用户名称
        if (entity.getUserId() != null) {
            dto.setUserName(sysUserService.getByUserId(entity.getUserId()).getUsername());
        }
        
        // 确保trainStatus字段被正确设置，前端需要这个字段来判断是否为克隆音频
        dto.setTrainStatus(entity.getTrainStatus());

        return dto;
    }

    @Override
    public List<VoiceCloneResponseDTO> getByUserIdWithNames(Long userId) {
        List<VoiceCloneEntity> entityList = getByUserId(userId);
        return convertToResponseDTOList(entityList);
    }

    /**
     * 将VoiceCloneEntity列表转换为VoiceCloneResponseDTO列表
     */
    private List<VoiceCloneResponseDTO> convertToResponseDTOList(List<VoiceCloneEntity> entityList) {
        if (entityList == null || entityList.isEmpty()) {
            return new ArrayList<>();
        }

        List<VoiceCloneResponseDTO> dtoList = new ArrayList<>(entityList.size());

        // 转换每个实体为DTO
        for (VoiceCloneEntity entity : entityList) {
            VoiceCloneResponseDTO dto = ConvertUtils.sourceToTarget(entity, VoiceCloneResponseDTO.class);

            // 设置模型名称
            if (StringUtils.isNotBlank(entity.getModelId())) {
                dto.setModelName(modelConfigService.getModelNameById(entity.getModelId()));
            }

            // 设置用户名称
            if (entity.getUserId() != null) {
                dto.setUserName(sysUserService.getByUserId(entity.getUserId()).getUsername());
            }
            
            // 确保trainStatus字段被正确设置，前端需要这个字段来判断是否为克隆音频
            dto.setTrainStatus(entity.getTrainStatus());

            // 设置是否有音频数据
            dto.setHasVoice(entity.getVoice() != null);

            dtoList.add(dto);
        }

        return dtoList;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void uploadVoice(String id, MultipartFile voiceFile) throws Exception {
        // 查询声音克隆记录
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }

        // 读取音频文件并转为字节数组
        byte[] voiceData = voiceFile.getBytes();

        // 更新voice字段
        entity.setVoice(voiceData);
        // 更新训练状态为待训练
        entity.setTrainStatus(0);

        // 保存到数据库
        baseDao.updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateName(String id, String name) {
        // 查询声音克隆记录
        VoiceCloneEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.VOICE_CLONE_RECORD_NOT_EXIST);
        }

        // 更新名称
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
            if (StringUtils.isBlank(type)) {
                throw new RenException(ErrorCode.VOICE_CLONE_MODEL_TYPE_NOT_FOUND);
            }
            if (Constant.VOICE_CLONE_HUOSHAN_DOUBLE_STREAM.equals(type)) {
                huoshanClone(config, entity);
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

    /**
     * 调用火山引擎进行语音复刻训练
     * 
     * @param config 模型配置
     * @param entity 语音克隆记录实体
     * @throws Exception
     */
    private void huoshanClone(Map<String, Object> config, VoiceCloneEntity entity) throws Exception {
        String appid = (String) config.get("appid");
        String accessToken = (String) config.get("access_token");

        if (StringUtils.isAnyBlank(appid, accessToken)) {
            throw new RenException(ErrorCode.VOICE_CLONE_HUOSHAN_CONFIG_MISSING);
        }

        String audioBase64 = Base64.getEncoder().encodeToString(entity.getVoice());
        Map<String, Object> reqBody = new HashMap<>();
        reqBody.put("appid", appid);
        List<Map<String, String>> audios = new ArrayList<>();
        Map<String, String> audioMap = new HashMap<>();
        audioMap.put("audio_bytes", audioBase64);
        audioMap.put("audio_format", "wav");
        audios.add(audioMap);
        reqBody.put("audios", audios);
        reqBody.put("source", 2);
        reqBody.put("language", 0);
        reqBody.put("model_type", 1);
        reqBody.put("speaker_id", entity.getVoiceId());

        String apiUrl = "https://openspeech.bytedance.com/api/v1/mega_tts/audio/upload";

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(apiUrl))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer;" + accessToken)
                .header("Resource-Id", "seed-icl-1.0")
                .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(reqBody)))
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        System.out.println(">>> HTTP status = " + response.statusCode());
        System.out.println(">>> response body = " + response.body());

        Map<String, Object> rsp = objectMapper.readValue(response.body(),
                new TypeReference<Map<String, Object>>() {
                });

        // 获取BaseResp对象
        Map<String, Object> baseResp = objectMapper.convertValue(rsp.get("BaseResp"),
                new TypeReference<Map<String, Object>>() {
                });
        if (baseResp != null) {
            Integer statusCode = objectMapper.convertValue(baseResp.get("StatusCode"), Integer.class);
            String statusMessage = objectMapper.convertValue(baseResp.getOrDefault("StatusMessage", ""),
                    String.class);

            // 获取speaker_id
            String speakerId = objectMapper.convertValue(rsp.get("speaker_id"), String.class);

            // StatusCode == 0 表示成功
            if (statusCode != null && statusCode == 0 && StringUtils.isNotBlank(speakerId)) {
                entity.setTrainStatus(2);
                entity.setVoiceId(speakerId);
                entity.setTrainError("");
                baseDao.updateById(entity);
            } else {
                // 失败时使用StatusMessage作为错误信息
                String errorMsg = StringUtils.isNotBlank(statusMessage) ? statusMessage : "训练失败";
                throw new RenException(errorMsg);
            }
        } else {
            String errorMsg = objectMapper.convertValue(rsp.get("message"),
                    new TypeReference<String>() {
                    });
            if (StringUtils.isNotBlank(errorMsg)) {
                throw new RenException(errorMsg);
            }
            throw new RenException(ErrorCode.VOICE_CLONE_RESPONSE_FORMAT_ERROR);
        }
    }
}
