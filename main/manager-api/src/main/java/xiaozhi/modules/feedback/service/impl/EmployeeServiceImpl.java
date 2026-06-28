package xiaozhi.modules.feedback.service.impl;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.feedback.dao.EmployeeDao;
import xiaozhi.modules.feedback.dto.EmployeeDTO;
import xiaozhi.modules.feedback.entity.EmployeeEntity;
import xiaozhi.modules.feedback.service.EmployeeService;
import xiaozhi.modules.feedback.vo.EmployeeVO;

@AllArgsConstructor
@Service
public class EmployeeServiceImpl extends BaseServiceImpl<EmployeeDao, EmployeeEntity> implements EmployeeService {

    private final EmployeeDao employeeDao;

    @Override
    public PageData<EmployeeVO> page(String storeId, String name, String page, String limit) {
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, page);
        params.put(Constant.LIMIT, limit);
        IPage<EmployeeEntity> result = baseDao.selectPage(
                getPage(params, "number", true),
                new QueryWrapper<EmployeeEntity>()
                        .eq(StringUtils.isNotBlank(storeId), "store_id", storeId)
                        .like(StringUtils.isNotBlank(name), "name", name)
                        .orderByAsc("number"));
        return getPageData(result, EmployeeVO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(EmployeeDTO dto) {
        EmployeeEntity entity = ConvertUtils.sourceToTarget(dto, EmployeeEntity.class);
        entity.setStatus(1);
        baseDao.insert(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(String id, EmployeeDTO dto) {
        EmployeeEntity entity = ConvertUtils.sourceToTarget(dto, EmployeeEntity.class);
        entity.setId(id);
        baseDao.updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(String[] ids) {
        baseDao.deleteBatchIds(Arrays.asList(ids));
    }

    @Override
    public List<EmployeeVO> listByStoreId(String storeId) {
        List<EmployeeEntity> list = employeeDao.selectList(
                new QueryWrapper<EmployeeEntity>()
                        .eq("store_id", storeId)
                        .eq("status", 1)
                        .orderByAsc("number"));
        return list.stream()
                .map(e -> ConvertUtils.sourceToTarget(e, EmployeeVO.class))
                .collect(Collectors.toList());
    }
}
