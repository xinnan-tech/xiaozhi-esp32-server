package xiaozhi.modules.sys.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.entity.SysParamsEntity;

/**
 * 参数管理
 */
@Mapper
public interface SysParamsDao extends BaseDao<SysParamsEntity> {
    /**
     * 根据参数编码，查询value
     *
     * @param paramCode 参数编码
     * @return 参数值
     */
    String getValueByCode(String paramCode);

    /**
     * 获取参数编码列表
     *
     * @param ids ids
     * @return 返回参数编码列表
     */
    List<String> getParamCodeList(String[] ids);

    /**
     * 根据参数编码，更新value
     *
     * @param paramCode  参数编码
     * @param paramValue 参数值
     */
    int updateValueByCode(@Param("paramCode") String paramCode, @Param("paramValue") String paramValue);
}
