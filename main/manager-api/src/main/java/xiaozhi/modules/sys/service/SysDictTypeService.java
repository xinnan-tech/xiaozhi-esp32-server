package xiaozhi.modules.sys.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysDictTypeDTO;
import xiaozhi.modules.sys.entity.DictType;
import xiaozhi.modules.sys.entity.SysDictTypeEntity;

import java.util.List;
import java.util.Map;

/**
 * 数据字典
 */
public interface SysDictTypeService extends BaseService<SysDictTypeEntity> {

    PageData<SysDictTypeDTO> page(Map<String, Object> params);

    SysDictTypeDTO get(Long id);

    void save(SysDictTypeDTO dto);

    void update(SysDictTypeDTO dto);

    void delete(Long[] ids);
    
    /**
     * 获取所有字典类型及其数据
     */
    List<DictType> getAllList();
    
    /**
     * 获取所有字典类型
     */
    List<DictType> getDictTypeList();
}