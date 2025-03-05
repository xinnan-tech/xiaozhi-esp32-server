package xiaozhi.modules.sys.dao;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.dto.SysDictDataDTO;
import xiaozhi.modules.sys.entity.DictData;
import xiaozhi.modules.sys.entity.SysDictDataEntity;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

/**
 * 字典数据
 */
@Mapper
public interface SysDictDataDao extends BaseDao<SysDictDataEntity> {

    /**
     * 字典数据列表
     */
    List<DictData> getDictDataList();

    List<SysDictDataDTO> getDataByTypeCode(String dictType);
}
