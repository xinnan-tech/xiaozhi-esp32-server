package xiaozhi.modules.knowledge.service;

import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;

/**
 * 知识库文档服务接口
 */
public interface KnowledgeFilesService {

        /**
         * 分页查询文档列表
         * 
         * @param knowledgeFilesDTO 查询条件
         * @param page              页码
         * @param limit             每页数量
         * @return 分页数据
         */
        PageData<KnowledgeFilesDTO> getPageList(KnowledgeFilesDTO knowledgeFilesDTO, Integer page, Integer limit);

        /**
         * 根据文档ID和知识库ID获取文档详情
         * 
         * @param documentId 文档ID
         * @param datasetId  知识库ID
         * @return 文档详情
         */
        KnowledgeFilesDTO getByDocumentId(String documentId, String datasetId);

        /**
         * 上传文档到知识库
         * 
         * @param datasetId    知识库ID
         * @param file         上传的文件
         * @param name         文档名称
         * @param metaFields   元数据字段
         * @param chunkMethod  分块方法
         * @param parserConfig 解析器配置
         * @return 上传的文档信息
         */
        KnowledgeFilesDTO uploadDocument(String datasetId, MultipartFile file, String name,
                        Map<String, Object> metaFields, String chunkMethod,
                        Map<String, Object> parserConfig);

        /**
         * 根据文档ID和知识库ID删除文档
         * 
         * @param documentId 文档ID
         * @param datasetId  知识库ID
         */
        void deleteByDocumentId(String documentId, String datasetId);

        /**
         * 获取RAG配置信息
         * 
         * @param ragModelId RAG模型配置ID
         * @return RAG配置信息
         */
        Map<String, Object> getRAGConfig(String ragModelId);

        /**
         * 解析文档（切块）
         * 
         * @param datasetId   知识库ID
         * @param documentIds 文档ID列表
         * @return 解析结果
         */
        boolean parseDocuments(String datasetId, List<String> documentIds);

        /**
         * 列出指定文档的切片
         * 
         * @param datasetId  知识库ID
         * @param documentId 文档ID
         * @param keywords   关键词过滤
         * @param page       页码
         * @param pageSize   每页数量
         * @param chunkId    切片ID
         * @return 切片列表信息
         */
        xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO listChunks(String datasetId, String documentId,
                        String keywords,
                        Integer page, Integer pageSize, String chunkId);

        /**
         * 召回测试 - 从指定数据集或文档中检索相关切片
         * 
         * @param question               用户查询或查询关键词
         * @param datasetIds             数据集ID列表
         * @param documentIds            文档ID列表
         * @param page                   页码
         * @param pageSize               每页数量
         * @param similarityThreshold    最小相似度阈值
         * @param vectorSimilarityWeight 向量相似度权重
         * @param topK                   参与向量余弦计算的切片数量
         * @param rerankId               重排模型ID
         * @param keyword                是否启用关键词匹配
         * @param highlight              是否启用高亮显示
         * @param crossLanguages         跨语言翻译列表
         * @param metadataCondition      元数据过滤条件
         * @return 召回测试结果
         */
        xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO retrievalTest(String question,
                        List<String> datasetIds, List<String> documentIds,
                        Integer page, Integer pageSize, Float similarityThreshold,
                        Float vectorSimilarityWeight, Integer topK, String rerankId,
                        Boolean keyword, Boolean highlight, List<String> crossLanguages,
                        Map<String, Object> metadataCondition);

        /**
         * 保存文档影子记录
         */
        void saveDocumentShadow(String datasetId, KnowledgeFilesDTO result, String originalName, String chunkMethod,
                        Map<String, Object> parserConfig);

        /**
         * 删除文档影子记录并更新统计信息
         * 
         * @param documentId 文档ID
         * @param datasetId  数据集ID
         * @param chunkDelta 待扣减的分块数
         * @param tokenDelta 待扣减的Token数
         */
        void deleteDocumentShadow(String documentId, String datasetId, Long chunkDelta, Long tokenDelta);
}