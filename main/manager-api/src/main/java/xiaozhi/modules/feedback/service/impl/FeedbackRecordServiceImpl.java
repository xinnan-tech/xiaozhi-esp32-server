package xiaozhi.modules.feedback.service.impl;

import java.util.HashMap;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.feedback.dao.FeedbackRecordDao;
import xiaozhi.modules.feedback.entity.FeedbackRecordEntity;
import xiaozhi.modules.feedback.service.FeedbackRecordService;
import xiaozhi.modules.feedback.vo.FeedbackRecordVO;

@AllArgsConstructor
@Service
public class FeedbackRecordServiceImpl extends BaseServiceImpl<FeedbackRecordDao, FeedbackRecordEntity> implements FeedbackRecordService {

    @Override
    public PageData<FeedbackRecordVO> page(String storeId, String page, String limit) {
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, page);
        params.put(Constant.LIMIT, limit);
        IPage<FeedbackRecordEntity> result = baseDao.selectPage(
                getPage(params, "create_date", false),
                new QueryWrapper<FeedbackRecordEntity>()
                        .eq(StringUtils.isNotBlank(storeId), "store_id", storeId)
                        .orderByDesc("create_date"));
        return getPageData(result, FeedbackRecordVO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveRecord(FeedbackRecordEntity entity) {
        baseDao.insert(entity);
    }
}
