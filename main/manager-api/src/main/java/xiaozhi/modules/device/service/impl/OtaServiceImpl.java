package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.springframework.stereotype.Service;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Query;
import xiaozhi.modules.device.dao.OtaDao;
import xiaozhi.modules.device.entity.OtaEntity;
import xiaozhi.modules.device.service.OtaService;

import java.util.Arrays;
import java.util.Map;

@Service
public class OtaServiceImpl extends ServiceImpl<OtaDao, OtaEntity> implements OtaService {

    @Override
    public PageData<OtaEntity> page(Map<String, Object> params) {
        IPage<OtaEntity> page = baseMapper.selectPage(
            new Query<OtaEntity>().getPage(params),
            new QueryWrapper<OtaEntity>()
                .orderByDesc("create_date")
        );

        return new PageData<>(page.getRecords(), page.getTotal());
    }

    @Override
    public void update(OtaEntity entity) {
        // 检查是否存在相同名称、类型和版本的固件（排除当前记录）
        QueryWrapper<OtaEntity> queryWrapper = new QueryWrapper<OtaEntity>()
            .eq("firmware_name", entity.getFirmwareName())
            .eq("type", entity.getType())
            .eq("version", entity.getVersion())
            .ne("id", entity.getId());  // 排除当前记录
        
        if (baseMapper.selectCount(queryWrapper) > 0) {
            throw new RuntimeException("已存在相同名称、类型和版本的固件，请修改后重试");
        }
        
        baseMapper.updateById(entity);
    }

    @Override
    public void delete(String[] ids) {
        baseMapper.deleteBatchIds(Arrays.asList(ids));
    }

    @Override
    public boolean save(OtaEntity entity) {
        // 检查是否存在相同名称、类型和版本的固件
        QueryWrapper<OtaEntity> queryWrapper = new QueryWrapper<OtaEntity>()
            .eq("firmware_name", entity.getFirmwareName())
            .eq("type", entity.getType())
            .eq("version", entity.getVersion());
        
        if (baseMapper.selectCount(queryWrapper) > 0) {
            throw new RuntimeException("已存在相同名称、类型和版本的固件，请勿重复添加");
        }
        
        return baseMapper.insert(entity) > 0;
    }
}