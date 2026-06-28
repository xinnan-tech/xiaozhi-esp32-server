package xiaozhi.modules.agent.service.impl;

import java.math.BigDecimal;
import java.util.Date;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import xiaozhi.modules.agent.dao.UserPersonaAssignmentDao;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;

@Service
public class UserPersonaAssignmentServiceImpl
        extends ServiceImpl<UserPersonaAssignmentDao, UserPersonaAssignmentEntity>
        implements UserPersonaAssignmentService {

    @Override
    public UserPersonaAssignmentEntity getByUserId(Long userId) {
        if (userId == null) {
            return null;
        }
        return this.getOne(new LambdaQueryWrapper<UserPersonaAssignmentEntity>()
                .eq(UserPersonaAssignmentEntity::getUserId, userId));
    }

    @Override
    public void upsertAuto(Long userId, String agentId, BigDecimal score, String reason) {
        UserPersonaAssignmentEntity e = getByUserId(userId);
        if (e == null) {
            e = new UserPersonaAssignmentEntity();
            e.setUserId(userId);
        }
        e.setAgentId(agentId);
        e.setScore(score);
        e.setReason(reason);
        e.setManual(0);
        e.setMatchedAt(new Date());
        this.saveOrUpdate(e);
    }

    @Override
    public void setManual(Long userId, String agentId) {
        UserPersonaAssignmentEntity e = getByUserId(userId);
        if (e == null) {
            e = new UserPersonaAssignmentEntity();
            e.setUserId(userId);
        }
        e.setAgentId(agentId);
        e.setManual(1);
        e.setReason("manual");
        e.setMatchedAt(new Date());
        this.saveOrUpdate(e);
    }

    @Override
    public void resetAuto(Long userId) {
        UserPersonaAssignmentEntity e = getByUserId(userId);
        if (e != null) {
            e.setManual(0);
            this.updateById(e);
        }
    }
}
