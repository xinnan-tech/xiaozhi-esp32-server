package xiaozhi.modules.agent.task;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.agent.service.PersonaMatcherService;

/**
 * 陪伴角色周匹配任务。
 * 仿 modules/knowledge/task/DocumentStatusSyncTask。
 * 每周一 03:30 跑一次;遍历有设备的非 manual 用户(seed + 重评估)。
 */
@Component
@AllArgsConstructor
@Slf4j
public class PersonaMatchTask {

    private final PersonaMatcherService personaMatcherService;

    /** 每周一 03:30(可按需改 cron) */
    @Scheduled(cron = "0 30 3 ? * MON")
    public void matchAll() {
        try {
            personaMatcherService.matchAllNonManualUsers();
        } catch (Exception e) {
            log.error("[persona-match] 周匹配任务异常", e);
        }
    }
}
