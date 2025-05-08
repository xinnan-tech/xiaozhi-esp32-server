package xiaozhi.modules.device.service;

import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.entity.OtaEntity;

/**
 * OTA固件管理
 */
public interface OtaService extends BaseService<OtaEntity> {
    PageData<OtaEntity> page(Map<String, Object> params);

    boolean save(OtaEntity entity);

    void update(OtaEntity entity);

    void delete(String[] ids);

    OtaEntity getLatestOta(String type);
}