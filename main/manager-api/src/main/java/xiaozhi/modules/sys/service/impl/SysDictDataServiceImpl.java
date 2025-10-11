package xiaozhi.modules.sys.service.impl;

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
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.sys.dao.SysDictDataDao;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.dto.SysDictDataDTO;
import xiaozhi.modules.sys.entity.SysDictDataEntity;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysDictDataService;
import xiaozhi.modules.sys.vo.SysDictDataItem;
import xiaozhi.modules.sys.vo.SysDictDataVO;

/**
 * 字典类型
 */
@Service
@AllArgsConstructor
public class SysDictDataServiceImpl extends BaseServiceImpl<SysDictDataDao, SysDictDataEntity>
        implements SysDictDataService {
    private final SysUserDao sysUserDao;
    private final RedisUtils redisUtils;

    @Override
    public PageData<SysDictDataVO> page(Map<String, Object> params) {
        IPage<SysDictDataEntity> page = baseDao.selectPage(getPage(params, "sort", true), getWrapper(params));

        PageData<SysDictDataVO> pageData = getPageData(page, SysDictDataVO.class);

        setUserName(pageData.getList());

        return pageData;
    }

    private QueryWrapper<SysDictDataEntity> getWrapper(Map<String, Object> params) {
        String dictTypeId = (String) params.get("dictTypeId");
        String dictLabel = (String) params.get("dictLabel");
        String dictValue = (String) params.get("dictValue");

        QueryWrapper<SysDictDataEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("dict_type_id", Long.parseLong(dictTypeId));
        wrapper.like(StringUtils.isNotBlank(dictLabel), "dict_label", dictLabel);
        wrapper.like(StringUtils.isNotBlank(dictValue), "dict_value", dictValue);

        return wrapper;
    }

    @Override
    public SysDictDataVO get(Long id) {
        SysDictDataEntity entity = baseDao.selectById(id);

        return ConvertUtils.sourceToTarget(entity, SysDictDataVO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(SysDictDataDTO dto) {
        // 相同字典类型的标签不能相同
        checkDictValueUnique(dto.getDictTypeId(), dto.getDictValue(), null);

        SysDictDataEntity entity = ConvertUtils.sourceToTarget(dto, SysDictDataEntity.class);

        insert(entity);
        // 删除Redis缓存
        String dictType = baseDao.getTypeByTypeId(dto.getDictTypeId());
        redisUtils.delete(RedisKeys.getDictDataByTypeKey(dictType));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(SysDictDataDTO dto) {
        // 相同字典类型的标签不能相同
        checkDictValueUnique(dto.getDictTypeId(), dto.getDictValue(), String.valueOf(dto.getId()));

        SysDictDataEntity entity = ConvertUtils.sourceToTarget(dto, SysDictDataEntity.class);

        updateById(entity);
        // 删除Redis缓存
        String dictType = baseDao.getTypeByTypeId(dto.getDictTypeId());
        redisUtils.delete(RedisKeys.getDictDataByTypeKey(dictType));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long[] ids) {
        for (Long id : ids) {
            SysDictDataEntity entity = baseDao.selectById(id);
            // 删除Redis缓存
            String dictType = baseDao.getTypeByTypeId(entity.getDictTypeId());
            redisUtils.delete(RedisKeys.getDictDataByTypeKey(dictType));
            // 删除
            deleteById(id);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteByTypeId(Long dictTypeId) {
        LambdaQueryWrapper<SysDictDataEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(SysDictDataEntity::getDictTypeId, dictTypeId);
        baseDao.delete(wrapper);
    }

    /**
     * 设置用户名
     *
     * @param sysDictDataList 字典类型集合
     */
    private void setUserName(List<SysDictDataVO> sysDictDataList) {
        // 收集所有用户 ID
        Set<Long> userIds = sysDictDataList.stream().flatMap(vo -> Stream.of(vo.getCreator(), vo.getUpdater()))
                .filter(Objects::nonNull).collect(Collectors.toSet());

        // 设置更新者和创建者名称
        if (!userIds.isEmpty()) {
            List<SysUserEntity> sysUserEntities = sysUserDao.selectBatchIds(userIds);
            // 把List转成Map，Map<Long, String>
            Map<Long, String> userNameMap = sysUserEntities.stream().collect(Collectors.toMap(SysUserEntity::getId,
                    SysUserEntity::getUsername, (existing, replacement) -> existing));

            sysDictDataList.forEach(vo -> {
                vo.setCreatorName(userNameMap.get(vo.getCreator()));
                vo.setUpdaterName(userNameMap.get(vo.getUpdater()));
            });
        }
    }

    private void checkDictValueUnique(Long dictTypeId, String dictValue, String excludeId) {
        LambdaQueryWrapper<SysDictDataEntity> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(SysDictDataEntity::getDictTypeId, dictTypeId).eq(SysDictDataEntity::getDictLabel, dictValue);
        if (StringUtils.isNotBlank(excludeId)) {
            queryWrapper.ne(SysDictDataEntity::getId, excludeId);
        }
        boolean exists = baseDao.exists(queryWrapper);
        if (exists) {
            throw new RenException("字典标签重复");
        }
    }

    @Override
    public List<SysDictDataItem> getDictDataByType(String dictType) {
        if (StringUtils.isBlank(dictType)) {
            return null;
        }

        // 先从Redis获取缓存
        String key = RedisKeys.getDictDataByTypeKey(dictType);
        List<SysDictDataItem> cachedData = (List<SysDictDataItem>) redisUtils.get(key);
        if (cachedData != null) {
            return cachedData;
        }

        // 如果缓存中没有，则从数据库获取
        List<SysDictDataItem> data = baseDao.getDictDataByType(dictType);

        // 存入Redis缓存
        if (data != null) {
            redisUtils.set(key, data);
        }

        return data;
    }
}