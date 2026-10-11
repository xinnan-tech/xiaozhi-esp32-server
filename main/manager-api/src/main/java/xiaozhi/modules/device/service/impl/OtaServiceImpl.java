package xiaozhi.modules.device.service.impl;

import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import io.micrometer.common.util.StringUtils;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.OtaDao;
import xiaozhi.modules.device.entity.OtaEntity;
import xiaozhi.modules.device.service.OtaService;

@Service
public class OtaServiceImpl extends BaseServiceImpl<OtaDao, OtaEntity> implements OtaService {

    @Override
    public PageData<OtaEntity> page(Map<String, Object> params) {
        IPage<OtaEntity> page = baseDao.selectPage(
                getPage(params, "update_date", true),
                getWrapper(params));

        return new PageData<>(page.getRecords(), page.getTotal());
    }

    private QueryWrapper<OtaEntity> getWrapper(Map<String, Object> params) {
        String firmwareName = (String) params.get("firmwareName");

        QueryWrapper<OtaEntity> wrapper = new QueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(firmwareName), "firmware_name", firmwareName);

        return wrapper;
    }

    @Override
    public void update(OtaEntity entity) {
        // Check if firmware with same type and version exists (excluding current record)
        QueryWrapper<OtaEntity> queryWrapper = new QueryWrapper<OtaEntity>()
                .eq("type", entity.getType())
                .eq("version", entity.getVersion())
                .ne("id", entity.getId()); // Exclude current record

        if (baseDao.selectCount(queryWrapper) > 0) {
            throw new RuntimeException("Firmware with same type and version already exists, please modify and retry");
        }

        entity.setUpdateDate(new Date());
        baseDao.updateById(entity);
    }

    @Override
    public void delete(String[] ids) {
        baseDao.deleteByIds(Arrays.asList(ids));
    }

    @Override
    public boolean save(OtaEntity entity) {
        QueryWrapper<OtaEntity> queryWrapper = new QueryWrapper<OtaEntity>()
                .eq("type", entity.getType());
        // Keep only the latest firmware of the same type
        List<OtaEntity> otaList = baseDao.selectList(queryWrapper);
        if (otaList != null && otaList.size() > 0) {
            OtaEntity otaBefore = otaList.get(0);
            entity.setId(otaBefore.getId());
            baseDao.updateById(entity);
            return true;
        }
        return baseDao.insert(entity) > 0;
    }

    @Override
    public OtaEntity getLatestOta(String type) {
        QueryWrapper<OtaEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("type", type)
                .orderByDesc("update_date")
                .last("LIMIT 1");
        return baseDao.selectOne(wrapper);
    }
}
