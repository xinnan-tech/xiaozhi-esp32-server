package xiaozhi.modules.feedback.service;

import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.feedback.dto.EmployeeDTO;
import xiaozhi.modules.feedback.entity.EmployeeEntity;
import xiaozhi.modules.feedback.vo.EmployeeVO;

public interface EmployeeService extends BaseService<EmployeeEntity> {
    PageData<EmployeeVO> page(String storeId, String name, String page, String limit);
    void save(EmployeeDTO dto);
    void update(String id, EmployeeDTO dto);
    void delete(String[] ids);
    List<EmployeeVO> listByStoreId(String storeId);
}
