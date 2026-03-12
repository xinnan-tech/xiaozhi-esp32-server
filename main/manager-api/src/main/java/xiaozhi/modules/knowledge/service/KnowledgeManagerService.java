package xiaozhi.modules.knowledge.service;

import java.util.List;

/**
 * 知识库模块领域编排服务
 * 用于处理跨 KnowledgeBase 和 KnowledgeFiles 的复杂业务流程，彻底解决 Service 间的循环依赖问题。
 */
public interface KnowledgeManagerService {

    /**
     * 级联删除知识库及其下属所有文档 (包括本地 DB 和 RAGFlow 远程数据)
     * 
     * @param datasetId 知识库 ID
     */
    void deleteDatasetWithFiles(String datasetId);

    /**
     * 批量级联删除知识库
     * 
     * @param datasetIds 知识库 ID 列表
     */
    void batchDeleteDatasetsWithFiles(List<String> datasetIds);
}
