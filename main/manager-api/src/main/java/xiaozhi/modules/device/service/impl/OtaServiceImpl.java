package xiaozhi.modules.device.service.impl;

import java.util.Arrays;
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
        // 检查是否存在相同名称、类型和版本的固件（排除当前记录）
        QueryWrapper<OtaEntity> queryWrapper = new QueryWrapper<OtaEntity>()
                .eq("firmware_name", entity.getFirmwareName())
                .eq("type", entity.getType())
                .eq("version", entity.getVersion())
                .ne("id", entity.getId()); // 排除当前记录

        if (baseDao.selectCount(queryWrapper) > 0) {
            throw new RuntimeException("已存在相同名称、类型和版本的固件，请修改后重试");
        }

        baseDao.updateById(entity);
    }

    @Override
    public void delete(String[] ids) {
        baseDao.deleteBatchIds(Arrays.asList(ids));
    }

    @Override
    public boolean save(OtaEntity entity) {
        // 检查是否存在相同名称、类型和版本的固件
        QueryWrapper<OtaEntity> queryWrapper = new QueryWrapper<OtaEntity>()
                .eq("firmware_name", entity.getFirmwareName())
                .eq("type", entity.getType())
                .eq("version", entity.getVersion());

        if (baseDao.selectCount(queryWrapper) > 0) {
            throw new RuntimeException("已存在相同名称、类型和版本的固件，请勿重复添加");
        }

        return baseDao.insert(entity) > 0;
    }
}