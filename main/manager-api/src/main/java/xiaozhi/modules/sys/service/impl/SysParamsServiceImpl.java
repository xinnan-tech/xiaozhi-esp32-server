package xiaozhi.modules.sys.service.impl;

import java.util.ArrayList;
import java.util.Arrays;
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
import xiaozhi.common.utils.SM2Utils;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.sys.dao.SysParamsDao;
import xiaozhi.modules.sys.dto.SysParamsDTO;
import xiaozhi.modules.sys.entity.SysParamsEntity;
import xiaozhi.modules.sys.redis.SysParamsRedis;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * Parameter management
 */
@AllArgsConstructor
@Service
public class SysParamsServiceImpl extends BaseServiceImpl<SysParamsDao, SysParamsEntity> implements SysParamsService {
    private final SysParamsRedis sysParamsRedis;
    private final AgentPluginMappingService agentPluginMappingService;

    @Override
    public PageData<SysParamsDTO> page(Map<String, Object> params) {
        IPage<SysParamsEntity> page = baseDao.selectPage(
                getPage(params, null, false),
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
        wrapper.nested(StringUtils.isNotBlank(paramCode), i -> i.like("param_code", paramCode)
                .or()
                .like("remark", paramCode));

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
        detectingSMSParameters(dto.getParamCode(), dto.getParamValue());
        SysParamsEntity entity = ConvertUtils.sourceToTarget(dto, SysParamsEntity.class);
        updateById(entity);

        sysParamsRedis.set(entity.getParamCode(), entity.getParamValue());
    }

    /**
     * Validate parameter value type
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
                    // First check if it starts with { and ends with }
                    String trimmedValue = paramValue.trim();
                    if (!trimmedValue.startsWith("{") || !trimmedValue.endsWith("}")) {
                        throw new RenException(ErrorCode.PARAM_JSON_INVALID);
                    }
                    // Then attempt to parse JSON
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
    public void delete(String[] ids) {
        // Delete Redis data
        List<String> paramCodeList = baseDao.getParamCodeList(ids);
        String[] paramCodes = paramCodeList.toArray(new String[paramCodeList.size()]);
        if (paramCodes.length > 0) {
            sysParamsRedis.delete(paramCodes);
        }

        // Delete
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
        // Get server key
        String secretParam = getValue(Constant.SERVER_SECRET, false);
        if (StringUtils.isBlank(secretParam) || "null".equals(secretParam)) {
            String newSecret = UUID.randomUUID().toString();
            updateValueByCode(Constant.SERVER_SECRET, newSecret);
        }

        // Initialize SM2 key pair
        initSM2KeyPair();
    }

    /**
     * Initialize SM2 key pair
     */
    private void initSM2KeyPair() {
        // Get SM2 public key
        String publicKey = getValue(Constant.SM2_PUBLIC_KEY, false);
        // Get SM2 private key
        String privateKey = getValue(Constant.SM2_PRIVATE_KEY, false);

        // If the public or private key is empty, generate a new key pair
        if (StringUtils.isBlank(publicKey) || StringUtils.isBlank(privateKey) || 
            "null".equals(publicKey) || "null".equals(privateKey)) {
            Map<String, String> keyPair = SM2Utils.createKey();
            String newPublicKey = keyPair.get(SM2Utils.KEY_PUBLIC_KEY);
            String newPrivateKey = keyPair.get(SM2Utils.KEY_PRIVATE_KEY);

            // Update key pair in database
            updateValueByCode(Constant.SM2_PUBLIC_KEY, newPublicKey);
            updateValueByCode(Constant.SM2_PRIVATE_KEY, newPrivateKey);
        }
    }

    /**
     * Validate SMS parameters
     * 
     * @param paramCode Parameter code
     * @param paramValue Parameter value
     * @return Whether passed
     */
    private boolean detectingSMSParameters(String paramCode, String paramValue) {
        // Check if the parameter code enables mobile registration; if not, skip other SMS parameter checks and return true directly.
        if (!Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue().equals(paramCode)) {
            return true;
        }
        // Check if it is a close SMS registration; if so, skip other SMS parameter checks and return true directly.
        if ("false".equalsIgnoreCase(paramValue)) {
            return true;
        }
        // Check if SMS association parameters are empty
        ArrayList<String> list = new ArrayList<String>();
        list.add(Constant.SysMSMParam.SERVER_SMS_MAX_SEND_COUNT.getValue());
        list.add(Constant.SysMSMParam.TWILIO_SMS_ACCOUNT_SID.getValue());
        list.add(Constant.SysMSMParam.TWILIO_SMS_AUTH_TOKEN.getValue());
        list.add(Constant.SysMSMParam.TWILIO_SMS_PHONE_NUMBER.getValue());
        list.add(Constant.SysMSMParam.TWILIO_SMS_TEMPLATE_MESSAGE.getValue());
        StringBuilder str = new StringBuilder();
        list.forEach(item -> {
            if (!StringUtils.isNoneBlank(item)) {
                str.append(",").append(item);
            }
        });
        if (!str.isEmpty()) {
            String promptStr = "%sthese parameters cannot be empty";
            String substring = str.substring(1, str.length());
            throw new RenException(promptStr.formatted(substring));
        }
        return true;
    }
    @Override
    public String getSystemWebMenu(boolean fromCache) {
        return getValue(Constant.SYSTEM_WEB_MENU, fromCache);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateSystemWebMenu(String configJson) {
        // Get current config
        String currentConfig = getSystemWebMenu(false);
        Map<String, Object> currentMap = null;
        Map<String, Object> newMap = null;

        try {
            if (StringUtils.isNotBlank(currentConfig)) {
                currentMap = JsonUtils.parseMap(currentConfig);
            }
            if (StringUtils.isNotBlank(configJson)) {
                newMap = JsonUtils.parseMap(configJson);
            }
        } catch (Exception e) {
            throw new RenException(ErrorCode.PARAM_JSON_INVALID);
        }

        // Check if addressBook feature is disabled
        if (currentMap != null && newMap != null) {
            Map<?, ?> currentFeatures = Map.class.cast(currentMap.get("features"));
            Map<?, ?> newFeatures = Map.class.cast(newMap.get("features"));

            if (currentFeatures != null && newFeatures != null) {
                Object currentAddressBookObj = currentFeatures.get("addressBook");
                Object newAddressBookObj = newFeatures.get("addressBook");

                Boolean currentEnabled = false;
                Boolean newEnabled = false;

                if (currentAddressBookObj instanceof Map<?, ?> currentAddressBook) {
                    Object enabled = currentAddressBook.get("enabled");
                    currentEnabled = enabled != null ? Boolean.class.cast(enabled) : false;
                }

                if (newAddressBookObj instanceof Map<?, ?> newAddressBook) {
                    Object enabled = newAddressBook.get("enabled");
                    newEnabled = enabled != null ? Boolean.class.cast(enabled) : false;
                }

                // If previously enabled but now disabled, remove all call_device plugins
                if (Boolean.TRUE.equals(currentEnabled) && !Boolean.TRUE.equals(newEnabled)) {
                    agentPluginMappingService.deleteByPluginId("SYSTEM_PLUGIN_CALL_DEVICE");
                }
            }
        }

        // Update config
        updateValueByCode(Constant.SYSTEM_WEB_MENU, configJson);
    }
}
