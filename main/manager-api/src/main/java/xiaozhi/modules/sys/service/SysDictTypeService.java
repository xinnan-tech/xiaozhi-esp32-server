package xiaozhi.modules.sys.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysDictTypeDTO;
import xiaozhi.modules.sys.entity.SysDictTypeEntity;
import xiaozhi.modules.sys.vo.SysDictTypeVO;

/**
 * 数据字典
 */
public interface SysDictTypeService extends BaseService<SysDictTypeEntity> {

    /**
     * 分页查询字典类型信息
     *
     * @param params 查询参数，包含分页信息和查询条件
     * @return 返回分页的字典类型数据
     */
    PageData<SysDictTypeVO> page(Map<String, Object> params);

    /**
     * 根据ID获取字典类型信息
     *
     * @param id 字典类型ID
     * @return 返回字典类型对象
     */
    SysDictTypeVO get(Long id);

    /**
     * 保存字典类型信息
     *
     * @param dto 字典类型数据传输对象
     */
    void save(SysDictTypeDTO dto);

    /**
     * 更新字典类型信息
     *
     * @param dto 字典类型数据传输对象
     */
    void update(SysDictTypeDTO dto);

    /**
     * 删除字典类型信息
     *
     * @param ids 要删除的字典类型ID数组
     */
    void delete(Long[] ids);

    /**
     * 列出所有字典类型信息
     *
     * @return 返回字典类型列表
     */
    List<SysDictTypeVO> list(Map<String, Object> params);
}