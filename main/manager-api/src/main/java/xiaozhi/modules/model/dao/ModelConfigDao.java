package xiaozhi.modules.model.dao;

import java.util.List;
import java.util.Map;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.model.entity.ModelConfigEntity;

@Mapper
public interface ModelConfigDao extends BaseDao<ModelConfigEntity> {

    /**
     * get model_code list
     */
    List<String> getModelCodeList(@Param("modelType") String modelType, @Param("modelName") String modelName);

    /**
     * 获取符合条件的TTS平台列表(id和modelName)
     */
    List<Map<String, Object>> getTtsPlatformList();
}
