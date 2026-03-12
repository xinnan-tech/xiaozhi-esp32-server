package xiaozhi.modules.knowledge.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.knowledge.dto.KnowledgeBaseDTO;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;
import xiaozhi.modules.model.entity.ModelConfigEntity;

/**
 * 知识库知识库服务接口
 */
public interface KnowledgeBaseService extends BaseService<KnowledgeBaseEntity> {

    /**
     * 分页查询知识库列表
     * 
     * @param knowledgeBaseDTO 查询条件
     * @param page             页码
     * @param limit            每页数量
     * @return 分页数据
     */
    PageData<KnowledgeBaseDTO> getPageList(KnowledgeBaseDTO knowledgeBaseDTO, Integer page, Integer limit);

    /**
     * 根据ID获取知识库详情
     * 
     * @param id 知识库ID
     * @return 知识库详情
     */
    KnowledgeBaseDTO getById(String id);

    /**
     * 新增知识库
     * 
     * @param knowledgeBaseDTO 知识库信息
     * @return 新增的知识库
     */
    KnowledgeBaseDTO save(KnowledgeBaseDTO knowledgeBaseDTO);

    /**
     * 更新知识库
     * 
     * @param knowledgeBaseDTO 知识库信息
     * @return 更新的知识库
     */
    KnowledgeBaseDTO update(KnowledgeBaseDTO knowledgeBaseDTO);

    /**
     * 根据知识库ID查询知识库
     * 
     * @param datasetId 知识库ID
     * @return 知识库详情
     */
    KnowledgeBaseDTO getByDatasetId(String datasetId);

    /**
     * 根据知识库ID集合查询知识库
     *
     * @param datasetIdList 知识库ID集合
     * @return 知识库详情
     */
    List<KnowledgeBaseDTO> getByDatasetIdList(List<String> datasetIdList);

    /**
     * 根据知识库ID删除知识库
     * 
     * @param datasetId 知识库ID
     */
    void deleteByDatasetId(String datasetId);

    /**
     * 获取RAG配置信息
     * 
     * @param ragModelId RAG模型配置ID
     * @return RAG配置信息
     */
    Map<String, Object> getRAGConfig(String ragModelId);

    /**
     * 根据知识库ID获取对应的RAG配置
     * 
     * @param datasetId 知识库ID
     * @return RAG配置
     */
    Map<String, Object> getRAGConfigByDatasetId(String datasetId);

    /**
     * 获取RAG模型列表
     * 
     * @return RAG模型列表
     */
    List<ModelConfigEntity> getRAGModels();

    /**
     * 更新知识库统计信息 (用于被文件服务回调)
     * 
     * @param datasetId  知识库ID
     * @param docDelta   文档数增量
     * @param chunkDelta 分块数增量
     * @param tokenDelta Token数增量
     */
    void updateStatistics(String datasetId, Integer docDelta, Long chunkDelta, Long tokenDelta);
}