package xiaozhi.modules.knowledge.service;

import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;

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
         * @return 文档详情 (强类型 InfoVO)
         */
        DocumentDTO.InfoVO getByDocumentId(String documentId, String datasetId);

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
         * 批量删除文档
         * 
         * @param datasetId 知识库ID
         * @param req       删除请求参数 (含文档ID列表)
         */
        void deleteDocuments(String datasetId, DocumentDTO.BatchIdReq req);

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
         * @param req        切片列表请求参数
         * @return 切片列表信息
         */
        ChunkDTO.ListVO listChunks(String datasetId, String documentId, ChunkDTO.ListReq req);

        /**
         * 召回测试
         * 
         * @param req 检索测试请求参数
         * @return 召回测试结果
         */
        RetrievalDTO.ResultVO retrievalTest(RetrievalDTO.TestReq req);

        /**
         * 保存文档影子记录
         */
        void saveDocumentShadow(String datasetId, KnowledgeFilesDTO result, String originalName, String chunkMethod,
                        Map<String, Object> parserConfig);

        /**
         * 批量删除文档影子记录并同步统计数据
         * 
         * @param documentIds 文档ID列表
         * @param datasetId   数据集ID
         * @param chunkDelta  待扣减的总分块数
         * @param tokenDelta  待扣减的总Token数
         */
        void deleteDocumentShadows(List<String> documentIds, String datasetId, Long chunkDelta, Long tokenDelta);

        /**
         * 根据数据集ID清理所有关联文档 (级联删除专用)
         * 
         * @param datasetId 数据集ID
         */
        void deleteDocumentsByDatasetId(String datasetId);

        /**
         * 同步所有处于 RUNNING 状态的文档 (供定时任务调用)
         */
        void syncRunningDocuments();
}