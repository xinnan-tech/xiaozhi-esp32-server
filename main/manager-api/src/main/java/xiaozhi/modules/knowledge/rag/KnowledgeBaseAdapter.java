package xiaozhi.modules.knowledge.rag;

import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;

/**
 * 知识库API适配器抽象基类
 * 定义通用的知识库操作接口，支持多种后端API实现
 */
public abstract class KnowledgeBaseAdapter {

        /**
         * 获取适配器类型标识
         * 
         * @return 适配器类型（如：ragflow, milvus, pinecone等）
         */
        public abstract String getAdapterType();

        /**
         * 初始化适配器配置
         * 
         * @param config 配置参数
         */
        public abstract void initialize(Map<String, Object> config);

        /**
         * 验证配置是否有效
         * 
         * @param config 配置参数
         * @return 验证结果
         */
        public abstract boolean validateConfig(Map<String, Object> config);

        /**
         * 分页查询文档列表
         * 
         * @param datasetId   知识库ID
         * @param queryParams 查询参数
         * @param page        页码
         * @param limit       每页数量
         * @return 分页数据
         */
        public abstract PageData<KnowledgeFilesDTO> getDocumentList(String datasetId,
                        Map<String, Object> queryParams,
                        Integer page,
                        Integer limit);

        /**
         * 根据文档ID获取文档详情
         * 
         * @param datasetId 知识库ID
         * @return 文档详情
         */
        public abstract KnowledgeFilesDTO getDocumentById(String datasetId, String documentId);

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
        public abstract KnowledgeFilesDTO uploadDocument(String datasetId,
                        MultipartFile file,
                        String name,
                        Map<String, Object> metaFields,
                        String chunkMethod,
                        Map<String, Object> parserConfig);

        /**
         * 根据状态分页查询文档列表
         * 
         * @param datasetId 知识库ID
         * @param status    文档解析状态
         * @param page      页码
         * @param limit     每页数量
         * @return 分页数据
         */
        public abstract PageData<KnowledgeFilesDTO> getDocumentListByStatus(String datasetId,
                        Integer status,
                        Integer page,
                        Integer limit);

        /**
         * 删除文档
         * 
         * @param datasetId  知识库ID
         * @param documentId 文档ID
         */
        public abstract void deleteDocument(String datasetId, String documentId);

        /**
         * 解析文档（切块）
         * 
         * @param datasetId   知识库ID
         * @param documentIds 文档ID列表
         * @return 解析结果
         */
        public abstract boolean parseDocuments(String datasetId, List<String> documentIds);

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
        public abstract Map<String, Object> listChunks(String datasetId,
                        String documentId,
                        String keywords,
                        Integer page,
                        Integer pageSize,
                        String chunkId);

        /**
         * 召回测试 - 从知识库中检索相关切片
         * 
         * @param question        用户查询
         * @param datasetIds      数据集ID列表
         * @param documentIds     文档ID列表
         * @param retrievalParams 检索参数
         * @return 召回测试结果
         */
        public abstract Map<String, Object> retrievalTest(String question,
                        List<String> datasetIds,
                        List<String> documentIds,
                        Map<String, Object> retrievalParams);

        /**
         * 测试连接
         * 
         * @return 连接测试结果
         */
        public abstract boolean testConnection();

        /**
         * 获取适配器状态信息
         * 
         * @return 状态信息
         */
        public abstract Map<String, Object> getStatus();

        /**
         * 获取支持的配置参数
         * 
         * @return 配置参数说明
         */
        public abstract Map<String, Object> getSupportedConfig();

        /**
         * 获取默认配置
         * 
         * @return 默认配置
         */
        public abstract Map<String, Object> getDefaultConfig();

        /**
         * 创建数据集
         * 
         * @param createParams 创建参数
         * @return 数据集ID
         */
        public abstract String createDataset(Map<String, Object> createParams);

        /**
         * 更新数据集
         * 
         * @param datasetId    数据集ID
         * @param updateParams 更新参数
         */
        public abstract void updateDataset(String datasetId, Map<String, Object> updateParams);

        /**
         * 删除数据集
         * 
         * @param datasetId 数据集ID
         */
        public abstract void deleteDataset(String datasetId);

        /**
         * 获取数据集的文档数量
         * 
         * @param datasetId 数据集ID
         * @return 文档数量
         */
        public abstract Integer getDocumentCount(String datasetId);
}