package xiaozhi.modules.feedback.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.feedback.entity.FeedbackRecordEntity;
import xiaozhi.modules.feedback.vo.FeedbackRecordVO;

public interface FeedbackRecordService extends BaseService<FeedbackRecordEntity> {
    PageData<FeedbackRecordVO> page(String storeId, String page, String limit);
    void saveRecord(FeedbackRecordEntity entity);
}
