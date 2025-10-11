package xiaozhi.modules.voiceclone.service.impl;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.RequiredArgsConstructor;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.DateUtils;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.sys.service.SysUserService;
import xiaozhi.modules.voiceclone.dao.VoiceCloneDao;
import xiaozhi.modules.voiceclone.dto.VoiceCloneDTO;
import xiaozhi.modules.voiceclone.dto.VoiceCloneResponseDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;
import xiaozhi.modules.voiceclone.service.VoiceCloneService;

@Service
@RequiredArgsConstructor
public class VoiceCloneServiceImpl extends BaseServiceImpl<VoiceCloneDao, VoiceCloneEntity>
        implements VoiceCloneService {

    private final ModelConfigService modelConfigService;
    private final SysUserService sysUserService;

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
}
