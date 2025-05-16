package xiaozhi.modules.model.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.model.entity.ModelProviderEntity;

@Mapper
public interface ModelProviderDao extends BaseDao<ModelProviderEntity> {

    List<String> getFieldList(@Param("modelType") String modelType, @Param("providerCode") String providerCode);
}
