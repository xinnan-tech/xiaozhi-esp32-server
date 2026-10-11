package xiaozhi.modules.sys.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysParamsDTO;
import xiaozhi.modules.sys.entity.SysParamsEntity;

/**
 * Parameter management
 */
public interface SysParamsService extends BaseService<SysParamsEntity> {

    PageData<SysParamsDTO> page(Map<String, Object> params);

    List<SysParamsDTO> list(Map<String, Object> params);

    SysParamsDTO get(Long id);

    void save(SysParamsDTO dto);

    void update(SysParamsDTO dto);

    void delete(String[] ids);

    /**
     * Get parameter value based on parameter code
     *
     * @param paramCode Parameter code
     * @param fromCache Whether to get from cache
     */
    String getValue(String paramCode, Boolean fromCache);

    /**
     * Get Object object of value based on parameter code
     *
     * @param paramCode Parameter code
     * @param clazz     Object class
     */
    <T> T getValueObject(String paramCode, Class<T> clazz);

    /**
     * Update value based on parameter code
     *
     * @param paramCode  Parameter code
     * @param paramValue Parameter value
     */
    int updateValueByCode(String paramCode, String paramValue);

    /**
     * Initialize server secret key
     */
    void initServerSecret();

    /**
     * Get system function menu configuration
     *
     * @param fromCache Whether retrieved from cache
     * @return System function menu config JSON string
     */
    String getSystemWebMenu(boolean fromCache);

    /**
     * Update system feature menu config (automatically handles cleanup of feature-related plugins)
     *
     * @param configJson New system feature menu config JSON
     */
    void updateSystemWebMenu(String configJson);
}
