package xiaozhi.modules.feedback.service.impl;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

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
import xiaozhi.modules.feedback.dao.StoreDao;
import xiaozhi.modules.feedback.dto.StoreDTO;
import xiaozhi.modules.feedback.entity.StoreEntity;
import xiaozhi.modules.feedback.service.StoreService;
import xiaozhi.modules.feedback.vo.StoreVO;

@AllArgsConstructor
@Service
public class StoreServiceImpl extends BaseServiceImpl<StoreDao, StoreEntity> implements StoreService {

    private final StoreDao storeDao;

    @Override
    public PageData<StoreVO> page(String storeName, String page, String limit) {
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, page);
        params.put(Constant.LIMIT, limit);
        IPage<StoreEntity> result = baseDao.selectPage(
                getPage(params, "create_date", false),
                new QueryWrapper<StoreEntity>()
                        .like(StringUtils.isNotBlank(storeName), "store_name", storeName)
                        .orderByDesc("create_date"));
        return getPageData(result, StoreVO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(StoreDTO dto) {
        StoreEntity entity = ConvertUtils.sourceToTarget(dto, StoreEntity.class);
        entity.setStoreCode(generateStoreCode());
        entity.setStatus(1);
        baseDao.insert(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(String id, StoreDTO dto) {
        StoreEntity entity = ConvertUtils.sourceToTarget(dto, StoreEntity.class);
        entity.setId(id);
        baseDao.updateById(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(String[] ids) {
        baseDao.deleteBatchIds(Arrays.asList(ids));
    }

    @Override
    public StoreVO getByStoreCode(String storeCode) {
        StoreEntity entity = storeDao.selectOne(
                new QueryWrapper<StoreEntity>().eq("store_code", storeCode));
        if (entity == null) {
            return null;
        }
        return ConvertUtils.sourceToTarget(entity, StoreVO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void bindAgent(String storeCode, String agentId) {
        StoreEntity entity = storeDao.selectOne(
                new QueryWrapper<StoreEntity>().eq("store_code", storeCode));
        if (entity != null) {
            entity.setAgentId(agentId);
            baseDao.updateById(entity);
        }
    }

    private String generateStoreCode() {
        Random random = new Random();
        String code;
        do {
            code = String.format("%06d", random.nextInt(1000000));
        } while (storeDao.selectOne(
                new QueryWrapper<StoreEntity>().eq("store_code", code)) != null);
        return code;
    }
}
