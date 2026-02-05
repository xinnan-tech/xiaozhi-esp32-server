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
     * 删除文档后更新数据集统计信息
     * 
     * @param datasetId  数据集ID
     * @param chunkDelta 分块减少量
     * @param tokenDelta Token减少量
     */
    void updateStatsAfterDelete(@Param("datasetId") String datasetId, @Param("chunkDelta") Long chunkDelta,
            @Param("tokenDelta") Long tokenDelta);

    /**
     * 上传文档后更新数据集统计信息 (递增)
     * 
     * @param datasetId 数据集ID
     */
    void updateStatsAfterUpload(@Param("datasetId") String datasetId);

}