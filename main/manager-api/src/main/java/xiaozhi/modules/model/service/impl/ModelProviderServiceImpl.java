package xiaozhi.modules.model.service.impl;

import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import cn.hutool.json.JSONArray;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
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
import xiaozhi.modules.security.user.SecurityUser;

@Service
@AllArgsConstructor
public class ModelProviderServiceImpl extends BaseServiceImpl<ModelProviderDao, ModelProviderEntity>
        implements ModelProviderService {

    private final ModelProviderDao modelProviderDao;
    private final KnowledgeBaseDao knowledgeBaseDao;

    @Override
    public List<ModelProviderDTO> getPluginList() {
        // 1. 获取插件列表
        LambdaQueryWrapper<ModelProviderEntity> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(ModelProviderEntity::getModelType, "Plugin");
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper);
        List<ModelProviderDTO> resultList = ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);

        // 2. 获取当前用户的知识库列表并追加到结果中
        UserDetail userDetail = SecurityUser.getUser();
        if (userDetail != null && userDetail.getId() != null) {
            // 查询当前用户的知识库
            LambdaQueryWrapper<KnowledgeBaseEntity> kbQueryWrapper = new LambdaQueryWrapper<>();
            kbQueryWrapper.eq(KnowledgeBaseEntity::getCreator, userDetail.getId());
            kbQueryWrapper.eq(KnowledgeBaseEntity::getStatus, 1); // 只获取启用状态的知识库
            List<KnowledgeBaseEntity> knowledgeBases = knowledgeBaseDao.selectList(kbQueryWrapper);

            // 将知识库转换为ModelProviderDTO格式并添加到结果列表
            for (KnowledgeBaseEntity kb : knowledgeBases) {
                ModelProviderDTO dto = new ModelProviderDTO();
                dto.setId(kb.getId());
                dto.setModelType("Rag");
                dto.setName("[知识库]" + kb.getName());
                dto.setProviderCode("ragflow"); // 假设所有RAG都使用ragflow
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
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper);
        return ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);
    }

    @Override
    public List<ModelProviderDTO> getListByModelType(String modelType) {

        QueryWrapper<ModelProviderEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("model_type", StringUtils.isBlank(modelType) ? "" : modelType);
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper);
        return ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);
    }

    @Override
    public PageData<ModelProviderDTO> getListPage(ModelProviderDTO modelProviderDTO, String page, String limit) {

        Map<String, Object> params = new HashMap<String, Object>();
        params.put(Constant.PAGE, page);
        params.put(Constant.LIMIT, limit);
        params.put(Constant.ORDER_FIELD, List.of("model_type", "sort"));
        params.put(Constant.ORDER, "asc");

        IPage<ModelProviderEntity> pageParam = getPage(params, null, true);

        QueryWrapper<ModelProviderEntity> wrapper = new QueryWrapper<ModelProviderEntity>();

        if (StringUtils.isNotBlank(modelProviderDTO.getModelType())) {
            wrapper.eq("model_type", modelProviderDTO.getModelType());
        }

        if (StringUtils.isNotBlank(modelProviderDTO.getName())) {
            wrapper.and(w -> w.like("name", modelProviderDTO.getName())
                    .or()
                    .like("provider_code", modelProviderDTO.getName()));
        }
        return getPageData(modelProviderDao.selectPage(pageParam, wrapper), ModelProviderDTO.class);
    }

    public static void main(String[] args) {
        String jsonString = "\"[]\"";
        JSONArray jsonArray = new JSONArray(jsonString);
        System.out.println("字符串转 JSONArray: " + jsonArray.toString());
    }

    @Override
    public ModelProviderDTO add(ModelProviderDTO modelProviderDTO) {
        UserDetail user = SecurityUser.getUser();
        modelProviderDTO.setCreator(user.getId());
        modelProviderDTO.setUpdater(user.getId());
        modelProviderDTO.setCreateDate(new Date());
        modelProviderDTO.setUpdateDate(new Date());
        // 去除Fields左右的双引号

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
        if (modelProviderDao.deleteBatchIds(ids) == 0) {
            throw new RenException(ErrorCode.DELETE_DATA_FAILED);
        }
    }

    @Override
    public List<ModelProviderDTO> getList(String modelType, String providerCode) {
        QueryWrapper<ModelProviderEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("model_type", StringUtils.isBlank(modelType) ? "" : modelType);
        queryWrapper.eq("provider_code", StringUtils.isBlank(providerCode) ? "" : providerCode);
        List<ModelProviderEntity> providerEntities = modelProviderDao.selectList(queryWrapper);
        return ConvertUtils.sourceToTarget(providerEntities, ModelProviderDTO.class);
    }
}
