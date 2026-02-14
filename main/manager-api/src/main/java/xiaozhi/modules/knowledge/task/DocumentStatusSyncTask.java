package xiaozhi.modules.knowledge.task;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;

/**
 * 知识库文档状态同步定时任务
 * 
 * 作用：
 * 1. 自动扫描处于 "RUNNING" (解析中) 状态的文档
 * 2. 调用 RAGFlow 接口获取最新状态
 * 3. 状态翻转 (RUNNING -> SUCCESS/FAIL) 时，同步更新数据库
 * 4. [关键] 解析成功时，补偿更新知识库的统计信息 (TokenCount)
 */
@Component
@AllArgsConstructor
@Slf4j
public class DocumentStatusSyncTask {

    private final KnowledgeFilesService knowledgeFilesService;

    /**
     * 每 30 秒执行一次同步
     * 采用 fixedDelay，确保上一次执行完 30 秒后才开始下一次，防止积压
     */
    @Scheduled(fixedDelay = 30000)
    public void syncRunningDocuments() {
        try {
            // log.debug("开始执行文档状态同步任务...");
            knowledgeFilesService.syncRunningDocuments();
        } catch (Exception e) {
            log.error("文档状态同步任务异常", e);
        }
    }
}
