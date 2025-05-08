package xiaozhi.modules.sys.service.impl;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.sys.dao.SysDictTypeDao;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.dto.SysDictTypeDTO;
import xiaozhi.modules.sys.entity.SysDictTypeEntity;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysDictDataService;
import xiaozhi.modules.sys.service.SysDictTypeService;
import xiaozhi.modules.sys.vo.SysDictTypeVO;

/**
 * 字典类型
 */
@Service
@AllArgsConstructor
public class SysDictTypeServiceImpl extends BaseServiceImpl<SysDictTypeDao, SysDictTypeEntity>
        implements SysDictTypeService {
    private final SysUserDao sysUserDao;
    private final SysDictDataService sysDictDataService;

    @Override
    public PageData<SysDictTypeVO> page(Map<String, Object> params) {
        IPage<SysDictTypeEntity> page = baseDao.selectPage(getPage(params, "sort", true), getWrapper(params));

        PageData<SysDictTypeVO> pageData = getPageData(page, SysDictTypeVO.class);

        setUserName(pageData.getList());

        return pageData;
    }

    private QueryWrapper<SysDictTypeEntity> getWrapper(Map<String, Object> params) {
        String dictType = (String) params.get("dictType");
        String dictName = (String) params.get("dictName");

        QueryWrapper<SysDictTypeEntity> wrapper = new QueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(dictType), "dict_type", dictType);
        wrapper.like(StringUtils.isNotBlank(dictName), "dict_name", dictName);

        return wrapper;
    }

    @Override
    public SysDictTypeVO get(Long id) {
        SysDictTypeEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException("字典类型不存在");
        }

        return ConvertUtils.sourceToTarget(entity, SysDictTypeVO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(SysDictTypeDTO dto) {
        // 字典类型编码不能重复
        checkDictTypeUnique(dto.getDictType(), null);

        SysDictTypeEntity entity = ConvertUtils.sourceToTarget(dto, SysDictTypeEntity.class);

        insert(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(SysDictTypeDTO dto) {
        // 字典类型编码不能重复
        checkDictTypeUnique(dto.getDictType(), String.valueOf(dto.getId()));

        SysDictTypeEntity entity = ConvertUtils.sourceToTarget(dto, SysDictTypeEntity.class);

        updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long[] ids) {
        // 先删除对应的字典数据
        for (Long id : ids) {
            sysDictDataService.deleteByTypeId(id);
        }
        // 再删除字典类型
        deleteBatchIds(Arrays.asList(ids));
    }

    @Override
    public List<SysDictTypeVO> list(Map<String, Object> params) {
        List<SysDictTypeEntity> entityList = baseDao.selectList(getWrapper(params));
        List<SysDictTypeVO> sysDictTypeVOList = ConvertUtils.sourceToTarget(entityList, SysDictTypeVO.class);
        // 设置用户名
        setUserName(sysDictTypeVOList);

        return sysDictTypeVOList;
    }

    /**
     * 设置用户名
     *
     * @param sysDictTypeList 字典类型集合
     */
    private void setUserName(List<SysDictTypeVO> sysDictTypeList) {
        // 收集所有用户 ID
        Set<Long> userIds = sysDictTypeList.stream().flatMap(vo -> Stream.of(vo.getCreator(), vo.getUpdater()))
                .filter(Objects::nonNull).collect(Collectors.toSet());

        // 设置更新者和创建者名称
        if (!userIds.isEmpty()) {
            List<SysUserEntity> sysUserEntities = sysUserDao.selectBatchIds(userIds);
            // 把List转成Map，Map<Long, String>
            Map<Long, String> userNameMap = sysUserEntities.stream().collect(Collectors.toMap(SysUserEntity::getId,
                    SysUserEntity::getUsername, (existing, replacement) -> existing));

            sysDictTypeList.forEach(vo -> {
                vo.setCreatorName(userNameMap.get(vo.getCreator()));
                vo.setUpdaterName(userNameMap.get(vo.getUpdater()));
            });
        }
    }

    private void checkDictTypeUnique(String dictType, String excludeId) {
        LambdaQueryWrapper<SysDictTypeEntity> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(SysDictTypeEntity::getDictType, dictType);
        if (StringUtils.isNotBlank(excludeId)) {
            queryWrapper.ne(SysDictTypeEntity::getId, excludeId);
        }
        boolean exists = baseDao.exists(queryWrapper);
        if (exists) {
            throw new RenException("字典类型编码重复");
        }
    }
}