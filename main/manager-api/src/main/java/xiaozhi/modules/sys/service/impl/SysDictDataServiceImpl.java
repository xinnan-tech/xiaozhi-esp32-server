package xiaozhi.modules.sys.service.impl;

import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import cn.hutool.core.collection.CollUtil;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.sys.dao.SysDictDataDao;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.dto.SysDictDataDTO;
import xiaozhi.modules.sys.entity.SysDictDataEntity;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysDictDataService;
import xiaozhi.modules.sys.vo.SysDictDataItem;
import xiaozhi.modules.sys.vo.SysDictDataVO;

/**
 * Dictionary-data service implementation.
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
        // Labels must be unique within the same dictionary type.
        checkDictValueUnique(dto.getDictTypeId(), dto.getDictValue(), null);

        SysDictDataEntity entity = ConvertUtils.sourceToTarget(dto, SysDictDataEntity.class);

        insert(entity);
        // Invalidate the Redis cache.
        String dictType = baseDao.getTypeByTypeId(dto.getDictTypeId());
        redisUtils.delete(RedisKeys.getDictDataByTypeKey(dictType));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(SysDictDataDTO dto) {
        // Labels must be unique within the same dictionary type.
        checkDictValueUnique(dto.getDictTypeId(), dto.getDictValue(), String.valueOf(dto.getId()));

        SysDictDataEntity entity = ConvertUtils.sourceToTarget(dto, SysDictDataEntity.class);

        updateById(entity);
        // Invalidate the Redis cache.
        String dictType = baseDao.getTypeByTypeId(dto.getDictTypeId());
        redisUtils.delete(RedisKeys.getDictDataByTypeKey(dictType));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long[] ids) {
        List<Long> idList = Arrays.asList(ids);
        if (ToolUtil.isNotEmpty(idList)) {
            // Delete cached dictionary entries in batch.
            List<String> redisKeyList = new ArrayList<>();
            // Load dictionary types in batch.
            List<String> dictTypeList = Optional.ofNullable(baseDao.getDictTypesByIdList(idList)).orElseGet(ArrayList::new);
            dictTypeList.forEach(dictType -> redisKeyList.add(RedisKeys.getDictDataByTypeKey(dictType)));
            if (ToolUtil.isNotEmpty(redisKeyList)) {
                // Clear cache entries.
                redisUtils.delete(redisKeyList);
            }
            // Delete dictionary rows in batch.
            deleteBatchIds(Arrays.asList(ids));
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
     * Populate creator and updater names.
     *
     * @param sysDictDataList dictionary-data list
     */
    private void setUserName(List<SysDictDataVO> sysDictDataList) {
        // Collect all user IDs.
        Set<Long> userIds = sysDictDataList.stream().flatMap(vo -> Stream.of(vo.getCreator(), vo.getUpdater()))
                .filter(Objects::nonNull).collect(Collectors.toSet());

        // Populate creator and updater names.
        if (!userIds.isEmpty()) {
            List<SysUserEntity> sysUserEntities = sysUserDao.selectBatchIds(userIds);
            // Convert the list to a Map<Long, String>.
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
            throw new RenException(ErrorCode.DICT_LABEL_DUPLICATE);
        }
    }

    @Override
    public List<SysDictDataItem> getDictDataByType(String dictType) {
        if (StringUtils.isBlank(dictType)) {
            return null;
        }

        // Read from Redis cache first.
        String key = RedisKeys.getDictDataByTypeKey(dictType);
        List<SysDictDataItem> cachedData = JsonUtils.toList(redisUtils.get(key), SysDictDataItem.class);
        if (cachedData != null) {
            return cachedData;
        }

        // Load from the database when the cache misses.
        List<SysDictDataItem> data = baseDao.getDictDataByType(dictType);

        // Store in Redis.
        if (data != null) {
            redisUtils.set(key, data);
        }

        return data;
    }
}
