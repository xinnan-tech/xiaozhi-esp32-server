package xiaozhi.modules.device.service;

import com.baomidou.mybatisplus.extension.service.IService;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.device.entity.OtaEntity;

import java.util.Map;

/**
 * OTA固件管理
 */
public interface OtaService extends IService<OtaEntity> {
    PageData<OtaEntity> page(Map<String, Object> params);

    boolean save(OtaEntity entity);

    void update(OtaEntity entity);

    void delete(String[] ids);
}