package xiaozhi.modules.sys.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysDictDataDTO;
import xiaozhi.modules.sys.entity.SysDictDataEntity;
import xiaozhi.modules.sys.vo.SysDictDataItem;
import xiaozhi.modules.sys.vo.SysDictDataVO;

/**
 * 数据字典
 */
public interface SysDictDataService extends BaseService<SysDictDataEntity> {

    /**
     * 分页查询数据字典信息
     *
     * @param params 查询参数，包含分页信息和查询条件
     * @return 返回数据字典的分页查询结果
     */
    PageData<SysDictDataVO> page(Map<String, Object> params);

    /**
     * 根据ID获取数据字典实体
     *
     * @param id 数据字典实体的唯一标识
     * @return 返回数据字典实体的详细信息
     */
    SysDictDataVO get(Long id);

    /**
     * 保存新的数据字典项
     *
     * @param dto 数据字典项的保存数据传输对象
     */
    void save(SysDictDataDTO dto);

    /**
     * 更新数据字典项
     *
     * @param dto 数据字典项的更新数据传输对象
     */
    void update(SysDictDataDTO dto);

    /**
     * 删除数据字典项
     *
     * @param ids 要删除的数据字典项的ID数组
     */
    void delete(Long[] ids);

    /**
     * 根据字典类型ID删除对应的字典数据
     *
     * @param dictTypeId 字典类型ID
     */
    void deleteByTypeId(Long dictTypeId);

    /**
     * 根据字典类型获取字典数据列表
     *
     * @param dictType 字典类型
     * @return 返回字典数据列表
     */
    List<SysDictDataItem> getDictDataByType(String dictType);

}