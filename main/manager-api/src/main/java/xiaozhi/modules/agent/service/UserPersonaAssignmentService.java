package xiaozhi.modules.agent.service;

import java.math.BigDecimal;

import com.baomidou.mybatisplus.extension.service.IService;

import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;

public interface UserPersonaAssignmentService extends IService<UserPersonaAssignmentEntity> {

    UserPersonaAssignmentEntity getByUserId(Long userId);

    /** 自动匹配写入(manual=0) */
    void upsertAuto(Long userId, String agentId, BigDecimal score, String reason);

    /** 家长手动切换(manual=1,立即生效) */
    void setManual(Long userId, String agentId);

    /** 恢复自动匹配(manual=0) */
    void resetAuto(Long userId);
}
