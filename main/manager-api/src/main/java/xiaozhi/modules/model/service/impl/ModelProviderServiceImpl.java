package xiaozhi.modules.model.service.impl;

import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import cn.hutool.json.JSONArray;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.ConvertUtils;
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
            throw new RenException("新增数据失败");
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
            throw new RenException("修改数据失败");
        }
        return ConvertUtils.sourceToTarget(modelProviderDTO, ModelProviderDTO.class);
    }

    @Override
    public void delete(String id) {
        if (modelProviderDao.deleteById(id) == 0) {
            throw new RenException("删除数据失败");
        }
    }

    @Override
    public void delete(List<String> ids) {
        if (modelProviderDao.deleteBatchIds(ids) == 0) {
            throw new RenException("删除数据失败");
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
