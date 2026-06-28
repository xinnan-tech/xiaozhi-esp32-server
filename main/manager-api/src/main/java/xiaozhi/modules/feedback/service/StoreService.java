package xiaozhi.modules.feedback.service;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.feedback.dto.StoreDTO;
import xiaozhi.modules.feedback.entity.StoreEntity;
import xiaozhi.modules.feedback.vo.StoreVO;

public interface StoreService extends BaseService<StoreEntity> {
    PageData<StoreVO> page(String storeName, String page, String limit);
    void save(StoreDTO dto);
    void update(String id, StoreDTO dto);
    void delete(String[] ids);
    StoreVO getByStoreCode(String storeCode);
    void bindAgent(String storeCode, String agentId);
}
