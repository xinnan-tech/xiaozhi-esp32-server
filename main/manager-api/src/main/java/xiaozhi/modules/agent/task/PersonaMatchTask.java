package xiaozhi.modules.agent.task;

import java.util.List;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.agent.entity.UserPersonaAssignmentEntity;
import xiaozhi.modules.agent.service.PersonaMatcherService;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;

/**
 * 陪伴角色周匹配任务。
 * 仿 modules/knowledge/task/DocumentStatusSyncTask。
 * 每周一 03:30 跑一次;只处理非 manual 用户(家长手动设定过的跳过)。
 */
@Component
@AllArgsConstructor
@Slf4j
public class PersonaMatchTask {

    private final PersonaMatcherService personaMatcherService;
    private final UserPersonaAssignmentService userPersonaAssignmentService;

    /** 每周一 03:30(可按需改 cron) */
    @Scheduled(cron = "0 30 3 ? * MON")
    public void matchAll() {
        try {
            log.info("[persona-match] 开始周匹配");
            List<UserPersonaAssignmentEntity> all = userPersonaAssignmentService.list();
            int matched = 0;
            for (UserPersonaAssignmentEntity a : all) {
                if (a.getManual() != null && a.getManual() == 1) {
                    continue; // 家长手动设定,跳过
                }
                try {
                    personaMatcherService.matchForUser(a.getUserId(), 14, 50, 5);
                    matched++;
                } catch (Exception ex) {
                    log.warn("[persona-match] user={} 失败:{}", a.getUserId(), ex.getMessage());
                }
            }
            log.info("[persona-match] 周匹配完成,处理 {} 人", matched);
        } catch (Exception e) {
            log.error("[persona-match] 周匹配任务异常", e);
        }
    }
}
