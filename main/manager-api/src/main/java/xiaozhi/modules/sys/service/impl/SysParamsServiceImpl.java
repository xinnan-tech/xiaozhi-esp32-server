package xiaozhi.modules.sys.service.impl;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.sys.dao.SysParamsDao;
import xiaozhi.modules.sys.dto.SysParamsDTO;
import xiaozhi.modules.sys.entity.SysParamsEntity;
import xiaozhi.modules.sys.redis.SysParamsRedis;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * 参数管理
 */
@AllArgsConstructor
@Service
public class SysParamsServiceImpl extends BaseServiceImpl<SysParamsDao, SysParamsEntity> implements SysParamsService {
    private final SysParamsRedis sysParamsRedis;

    @Override
    public PageData<SysParamsDTO> page(Map<String, Object> params) {
        IPage<SysParamsEntity> page = baseDao.selectPage(
                getPage(params, Constant.CREATE_DATE, false),
                getWrapper(params));

        return getPageData(page, SysParamsDTO.class);
    }

    @Override
    public List<SysParamsDTO> list(Map<String, Object> params) {
        List<SysParamsEntity> entityList = baseDao.selectList(getWrapper(params));

        return ConvertUtils.sourceToTarget(entityList, SysParamsDTO.class);
    }

    private QueryWrapper<SysParamsEntity> getWrapper(Map<String, Object> params) {
        String paramCode = (String) params.get("paramCode");

        QueryWrapper<SysParamsEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("param_type", 1);
        wrapper.like(StringUtils.isNotBlank(paramCode), "param_code", paramCode);

        return wrapper;
    }

    @Override
    public SysParamsDTO get(Long id) {
        SysParamsEntity entity = baseDao.selectById(id);

        return ConvertUtils.sourceToTarget(entity, SysParamsDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(SysParamsDTO dto) {
        validateParamValue(dto);

        SysParamsEntity entity = ConvertUtils.sourceToTarget(dto, SysParamsEntity.class);
        insert(entity);

        sysParamsRedis.set(entity.getParamCode(), entity.getParamValue());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(SysParamsDTO dto) {
        validateParamValue(dto);

        SysParamsEntity entity = ConvertUtils.sourceToTarget(dto, SysParamsEntity.class);
        updateById(entity);

        sysParamsRedis.set(entity.getParamCode(), entity.getParamValue());
    }

    /**
     * 校验参数值类型
     */
    private void validateParamValue(SysParamsDTO dto) {
        if (dto == null) {
            throw new RenException(ErrorCode.PARAM_VALUE_NULL);
        }

        if (StringUtils.isBlank(dto.getParamValue())) {
            throw new RenException(ErrorCode.PARAM_VALUE_NULL);
        }

        if (StringUtils.isBlank(dto.getValueType())) {
            throw new RenException(ErrorCode.PARAM_TYPE_NULL);
        }

        String valueType = dto.getValueType().toLowerCase();
        String paramValue = dto.getParamValue();

        switch (valueType) {
            case "string":
                break;
            case "array":
                break;
            case "number":
                try {
                    Double.parseDouble(paramValue);
                } catch (NumberFormatException e) {
                    throw new RenException(ErrorCode.PARAM_NUMBER_INVALID);
                }
                break;
            case "boolean":
                if (!"true".equalsIgnoreCase(paramValue) && !"false".equalsIgnoreCase(paramValue)) {
                    throw new RenException(ErrorCode.PARAM_BOOLEAN_INVALID);
                }
                break;
            case "json":
                try {
                    JsonUtils.parseObject(paramValue, Object.class);
                } catch (Exception e) {
                    throw new RenException(ErrorCode.PARAM_JSON_INVALID);
                }
                break;
            default:
                throw new RenException(ErrorCode.PARAM_TYPE_INVALID);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long[] ids) {
        // 删除Redis数据
        List<String> paramCodeList = baseDao.getParamCodeList(ids);
        String[] paramCodes = paramCodeList.toArray(new String[paramCodeList.size()]);
        sysParamsRedis.delete(paramCodes);

        // 删除
        deleteBatchIds(Arrays.asList(ids));
    }

    @Override
    public String getValue(String paramCode, Boolean fromCache) {
        String paramValue = null;
        if (fromCache) {
            paramValue = sysParamsRedis.get(paramCode);
            if (paramValue == null) {
                paramValue = baseDao.getValueByCode(paramCode);

                sysParamsRedis.set(paramCode, paramValue);
            }
        } else {
            paramValue = baseDao.getValueByCode(paramCode);
        }
        return paramValue;
    }

    @Override
    public <T> T getValueObject(String paramCode, Class<T> clazz) {
        String paramValue = getValue(paramCode, true);
        if (StringUtils.isNotBlank(paramValue)) {
            return JsonUtils.parseObject(paramValue, clazz);
        }

        try {
            return clazz.getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int updateValueByCode(String paramCode, String paramValue) {
        int count = baseDao.updateValueByCode(paramCode, paramValue);
        sysParamsRedis.set(paramCode, paramValue);
        return count;
    }

    @Override
    public void initServerSecret() {
        // 获取服务器密钥
        String secretParam = getValue(Constant.SERVER_SECRET, false);
        if (StringUtils.isBlank(secretParam) || "null".equals(secretParam)) {
            String newSecret = UUID.randomUUID().toString();
            updateValueByCode(Constant.SERVER_SECRET, newSecret);
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public Object getConfig() {
        // 查询所有系统参数
        QueryWrapper<SysParamsEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("param_type", 1);
        List<SysParamsEntity> paramsList = baseDao.selectList(wrapper);

        // 构建配置信息
        Map<String, Object> config = new HashMap<>();

        for (SysParamsEntity param : paramsList) {
            String[] keys = param.getParamCode().split("\\.");
            Map<String, Object> current = config;

            // 遍历除最后一个key之外的所有key
            for (int i = 0; i < keys.length - 1; i++) {
                String key = keys[i];
                if (!current.containsKey(key)) {
                    current.put(key, new HashMap<String, Object>());
                }
                current = (Map<String, Object>) current.get(key);
            }

            // 处理最后一个key
            String lastKey = keys[keys.length - 1];
            String value = param.getParamValue();

            // 根据valueType转换值
            switch (param.getValueType().toLowerCase()) {
                case "number":
                    try {
                        current.put(lastKey, Double.parseDouble(value));
                    } catch (NumberFormatException e) {
                        current.put(lastKey, value);
                    }
                    break;
                case "boolean":
                    current.put(lastKey, Boolean.parseBoolean(value));
                    break;
                case "array":
                    // 将分号分隔的字符串转换为数字数组
                    List<String> list = new ArrayList<>();
                    for (String num : value.split(";")) {
                        if (StringUtils.isNotBlank(num)) {
                            list.add(num.trim());
                        }
                    }
                    current.put(lastKey, list);
                    break;
                case "json":
                    try {
                        current.put(lastKey, JsonUtils.parseObject(value, Object.class));
                    } catch (Exception e) {
                        current.put(lastKey, value);
                    }
                    break;
                default:
                    current.put(lastKey, value);
            }
        }

        return config;
    }
}