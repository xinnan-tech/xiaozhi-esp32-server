package xiaozhi.modules.sys.dao;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.entity.DictType;
import xiaozhi.modules.sys.entity.SysDictTypeEntity;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

/**
 * 字典类型
 */
@Mapper
public interface SysDictTypeDao extends BaseDao<SysDictTypeEntity> {

    /**
     * 字典类型列表
     */
    List<DictType> getDictTypeList();

}
