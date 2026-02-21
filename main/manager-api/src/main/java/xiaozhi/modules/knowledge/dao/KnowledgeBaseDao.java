package xiaozhi.modules.knowledge.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;

/**
 * 知识库知识库
 */
@Mapper
public interface KnowledgeBaseDao extends BaseDao<KnowledgeBaseEntity> {

    /**
     * 根据知识库ID删除相关的插件映射记录
     * 
     * @param knowledgeBaseId 知识库ID
     */
    void deletePluginMappingByKnowledgeBaseId(@Param("knowledgeBaseId") String knowledgeBaseId);

    /**
     * 通用维度原子更新知识库统计信息
     * 
     * @param datasetId  数据集ID
     * @param docDelta   文档数增量
     * @param chunkDelta 分块数增量
     * @param tokenDelta Token数增量
     */
    void updateStatsAfterChange(@Param("datasetId") String datasetId,
            @Param("docDelta") Integer docDelta,
            @Param("chunkDelta") Long chunkDelta,
            @Param("tokenDelta") Long tokenDelta);

}