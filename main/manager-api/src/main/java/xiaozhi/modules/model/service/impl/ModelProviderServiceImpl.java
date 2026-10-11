package xiaozhi.modules.model.service.impl;

import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.knowledge.dao.KnowledgeBaseDao;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;
import xiaozhi.modules.model.dao.ModelProviderDao;
import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.entity.ModelProviderEntity;
import xiaozhi.modules.model.service.ModelProviderService;
import xiaozhi.modules.model.support.ProviderPolicy;
import xiaozhi.modules.security.user.SecurityUser;

@Service
@AllArgsConstructor
public class ModelProviderServiceImpl extends BaseServiceImpl<ModelProviderDao, ModelProviderEntity>
        implements ModelProviderService {

    private final ModelProviderDao modelProviderDao;
    private final KnowledgeBaseDao knowledgeBaseDao;

    @Override
    public List<ModelProviderDTO> getPluginList() {
        // 1. Fetch plugin list
        LambdaQueryWrapper<ModelProviderEntity> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(ModelProviderEntity::getModelType, "Plugin");
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper)
                .stream()
                .filter(ProviderPolicy::isAllowedProvider)
                .collect(Collectors.toList());
        List<ModelProviderDTO> resultList = ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);

        // 2. Append knowledge bases owned by the current user
        UserDetail userDetail = SecurityUser.getUser();
        if (userDetail != null && userDetail.getId() != null) {
            // Query knowledge bases for the current user
            LambdaQueryWrapper<KnowledgeBaseEntity> kbQueryWrapper = new LambdaQueryWrapper<>();
            kbQueryWrapper.eq(KnowledgeBaseEntity::getCreator, userDetail.getId());
            kbQueryWrapper.eq(KnowledgeBaseEntity::getStatus, 1); // Only enabled knowledge bases
            List<KnowledgeBaseEntity> knowledgeBases = knowledgeBaseDao.selectList(kbQueryWrapper);

            // Convert knowledge bases to ModelProviderDTO and append to the list
            for (KnowledgeBaseEntity kb : knowledgeBases) {
                ModelProviderDTO dto = new ModelProviderDTO();
                dto.setId(kb.getId());
                dto.setModelType("Rag");
                dto.setName("[Knowledge Base] " + kb.getName());
                dto.setProviderCode("ragflow"); // Assume all RAG uses ragflow
                dto.setFields("[]");
                dto.setSort(0);
                dto.setCreateDate(kb.getCreatedAt());
                dto.setUpdateDate(kb.getUpdatedAt());
                dto.setCreator(0L);
                dto.setUpdater(0L);
                resultList.add(dto);
            }
        }

        return resultList;
    }

    @Override
    public ModelProviderDTO getById(String id) {
        ModelProviderEntity entity = modelProviderDao.selectById(id);
        return ConvertUtils.sourceToTarget(entity, ModelProviderDTO.class);
    }

    @Override
    public List<ModelProviderDTO> getPluginListByIds(Collection<String> ids) {
        LambdaQueryWrapper<ModelProviderEntity> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.in(ModelProviderEntity::getId, ids);
        queryWrapper.eq(ModelProviderEntity::getModelType, "Plugin");
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper)
                .stream()
                .filter(ProviderPolicy::isAllowedProvider)
                .collect(Collectors.toList());
        return ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);
    }

    @Override
    public List<ModelProviderDTO> getListByModelType(String modelType) {

        QueryWrapper<ModelProviderEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("model_type", StringUtils.isBlank(modelType) ? "" : modelType);
        queryWrapper.orderByAsc("sort");
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper)
                .stream()
                .filter(ProviderPolicy::isAllowedProvider)
                .collect(Collectors.toList());
        return ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);
    }

    @Override
    public PageData<ModelProviderDTO> getListPage(ModelProviderDTO modelProviderDTO, String page, String limit) {
        QueryWrapper<ModelProviderEntity> wrapper = new QueryWrapper<ModelProviderEntity>();

        if (StringUtils.isNotBlank(modelProviderDTO.getModelType())) {
            wrapper.eq("model_type", modelProviderDTO.getModelType());
        }

        if (StringUtils.isNotBlank(modelProviderDTO.getName())) {
            wrapper.and(w -> w.like("name", modelProviderDTO.getName())
                    .or()
                    .like("provider_code", modelProviderDTO.getName()));
        }
        wrapper.orderByAsc("model_type", "sort");

        List<ModelProviderEntity> allRecords = modelProviderDao.selectList(wrapper);
        List<ModelProviderEntity> filteredRecords = allRecords.stream()
                .filter(ProviderPolicy::isAllowedProvider)
                .collect(Collectors.toList());

        long currentPage = Long.parseLong(page);
        long pageSize = Long.parseLong(limit);
        int total = filteredRecords.size();
        int fromIndex = (int) Math.min((currentPage - 1) * pageSize, total);
        int toIndex = (int) Math.min(fromIndex + pageSize, total);

        List<ModelProviderEntity> pageRecords = filteredRecords.subList(fromIndex, toIndex);
        return new PageData<>(ConvertUtils.sourceToTarget(pageRecords, ModelProviderDTO.class), total);
    }

    @Override
    public ModelProviderDTO add(ModelProviderDTO modelProviderDTO) {
        UserDetail user = SecurityUser.getUser();
        modelProviderDTO.setCreator(user.getId());
        modelProviderDTO.setUpdater(user.getId());
        modelProviderDTO.setCreateDate(new Date());
        modelProviderDTO.setUpdateDate(new Date());
        // Remove double quotes around Fields.

        modelProviderDTO.setFields(modelProviderDTO.getFields());
        ModelProviderEntity entity = ConvertUtils.sourceToTarget(modelProviderDTO, ModelProviderEntity.class);
        if (modelProviderDao.insert(entity) == 0) {
            throw new RenException(ErrorCode.ADD_DATA_FAILED);
        }

        return ConvertUtils.sourceToTarget(modelProviderDTO, ModelProviderDTO.class);
    }

    @Override
    public ModelProviderDTO edit(ModelProviderDTO modelProviderDTO) {
        UserDetail user = SecurityUser.getUser();
        modelProviderDTO.setUpdater(user.getId());
        modelProviderDTO.setUpdateDate(new Date());
        if (modelProviderDao
                .updateById(ConvertUtils.sourceToTarget(modelProviderDTO, ModelProviderEntity.class)) == 0) {
            throw new RenException(ErrorCode.UPDATE_DATA_FAILED);
        }
        return ConvertUtils.sourceToTarget(modelProviderDTO, ModelProviderDTO.class);
    }

    @Override
    public void delete(String id) {
        if (modelProviderDao.deleteById(id) == 0) {
            throw new RenException(ErrorCode.DELETE_DATA_FAILED);
        }
    }

    @Override
    public void delete(List<String> ids) {
        if (modelProviderDao.deleteByIds(ids) == 0) {
            throw new RenException(ErrorCode.DELETE_DATA_FAILED);
        }
    }

    @Override
    public List<ModelProviderDTO> getList(String modelType, String providerCode) {
        QueryWrapper<ModelProviderEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("model_type", StringUtils.isBlank(modelType) ? "" : modelType);
        queryWrapper.eq("provider_code", StringUtils.isBlank(providerCode) ? "" : providerCode);
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper)
                .stream()
                .filter(ProviderPolicy::isAllowedProvider)
                .collect(Collectors.toList());
        return ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);
    }
}
