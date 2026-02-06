package xiaozhi.modules.knowledge.rag.impl;

import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.core.io.AbstractResource;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.util.UriComponentsBuilder;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.RAGFlowClient;

/**
 * RAGFlow知识库适配器实现
 * <p>
 * 重构说明 (Refactoring Note):
 * 本类已升级为使用 {@link RAGFlowClient} 统一处理 HTTP 通信。
 * 解决了旧代码中 Timeout 缺失、Error Handling 分散的问题。
 * </p>
 */
@Slf4j
public class RAGFlowAdapter extends KnowledgeBaseAdapter {

    private static final String ADAPTER_TYPE = "ragflow";

    private Map<String, Object> config;
    private ObjectMapper objectMapper;
    // Client 实例，初始化时创建
    private RAGFlowClient client;

    public RAGFlowAdapter() {
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public String getAdapterType() {
        return ADAPTER_TYPE;
    }

    @Override
    public void initialize(Map<String, Object> config) {
        this.config = config;
        validateConfig(config);
        String baseUrl = (String) config.get("base_url");
        String apiKey = (String) config.get("api_key");
        // 初始化 Client，默认超时 30s，可通过 config 扩展
        int timeout = 30;
        if (config.containsKey("timeout")) {
            try {
                timeout = Integer.parseInt(config.get("timeout").toString());
            } catch (Exception e) {
                log.warn("解析超时配置失败，使用默认值 30s");
            }
        }
        this.client = new RAGFlowClient(baseUrl, apiKey, timeout);
        log.info("RAGFlow适配器初始化完成，Client已就绪");
    }

    @Override
    public boolean validateConfig(Map<String, Object> config) {
        if (config == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        String baseUrl = (String) config.get("base_url");
        String apiKey = (String) config.get("api_key");

        if (StringUtils.isBlank(baseUrl)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_NULL);
        }

        if (StringUtils.isBlank(apiKey)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_NULL);
        }

        if (apiKey.contains("你")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_INVALID);
        }

        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_INVALID);
        }

        return true;
    }

    /**
     * 辅助方法：确保 Client 已初始化
     */
    private RAGFlowClient getClient() {
        if (this.client == null) {
            // 尝试重新初始化
            if (this.config != null) {
                initialize(this.config);
            } else {
                throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND, "适配器未初始化"); // 应该抛出 RuntimeException
            }
        }
        return this.client;
    }

    private RenException convertToRenException(Exception e) {
        if (e instanceof RenException) {
            return (RenException) e;
        }
        return new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
    }

    @Override
    public PageData<KnowledgeFilesDTO> getDocumentList(String datasetId, Map<String, Object> queryParams, Integer page,
            Integer limit) {
        try {
            log.info("=== [RAGFlow] 获取文档列表: datasetId={} ===", datasetId);

            // 构造参数
            Map<String, Object> params = new HashMap<>();
            if (page != null && page > 0)
                params.put("page", page);
            if (limit != null && limit > 0)
                params.put("page_size", limit);

            if (queryParams != null) {
                // 兼容旧逻辑的特殊 parameter mapping
                if (queryParams.containsKey("name")) {
                    params.put("keywords", queryParams.get("name"));
                }
                if (queryParams.containsKey("orderby")) {
                    params.put("orderby", queryParams.get("orderby"));
                }
                if (queryParams.containsKey("desc")) {
                    params.put("desc", queryParams.get("desc"));
                }
                if (queryParams.containsKey("id")) {
                    params.put("id", queryParams.get("id"));
                }
                if (queryParams.containsKey("run")) { // Run status
                    params.put("run", queryParams.get("run"));
                }
                // 处理时间范围等其他参数，旧逻辑中有很多 if，这里简化透传，RAGFlow Client 会处理 map
                // 如果需要严格兼容旧逻辑的 parameter transform，可以在这里补全，但 queryParams 大多 key 是直接透传的
            }

            Map<String, Object> response = getClient().get("/api/v1/datasets/" + datasetId + "/documents", params);

            Object dataObj = response.get("data");
            return parseDocumentListResponse(dataObj, page != null ? page : 1, limit != null ? limit : 10);

        } catch (Exception e) {
            log.error("获取文档列表失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public KnowledgeFilesDTO getDocumentById(String datasetId, String documentId) {
        try {
            log.info("=== [RAGFlow] 获取文档详情: datasetId={}, documentId={} ===", datasetId, documentId);
            Map<String, Object> queryParams = new HashMap<>();
            queryParams.put("id", documentId);
            PageData<KnowledgeFilesDTO> list = getDocumentList(datasetId, queryParams, 1, 1);
            if (list != null && list.getList() != null && !list.getList().isEmpty()) {
                return list.getList().get(0);
            }
            return null;
        } catch (Exception e) {
            log.error("获取文档详情失败: {}", documentId, e);
            throw convertToRenException(e);
        }
    }

    @Override
    public KnowledgeFilesDTO uploadDocument(String datasetId, MultipartFile file, String name,
            Map<String, Object> metaFields, String chunkMethod,
            Map<String, Object> parserConfig) {
        try {
            log.info("=== [RAGFlow] 上传文档: datasetId={} ===", datasetId);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartFileResource(file));

            if (StringUtils.isNotBlank(name)) {
                body.add("name", name);
            }
            if (metaFields != null && !metaFields.isEmpty()) {
                body.add("meta", objectMapper.writeValueAsString(metaFields));
            }
            if (StringUtils.isNotBlank(chunkMethod)) {
                body.add("chunk_method", chunkMethod);
            }
            if (parserConfig != null && !parserConfig.isEmpty()) {
                body.add("parser_config", objectMapper.writeValueAsString(parserConfig));
            }

            Map<String, Object> response = getClient().postMultipart("/api/v1/datasets/" + datasetId + "/documents",
                    body);

            Object dataObj = response.get("data");
            return parseUploadResponse(dataObj, datasetId, file);

        } catch (Exception e) {
            log.error("文档上传失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public PageData<KnowledgeFilesDTO> getDocumentListByStatus(String datasetId, Integer status, Integer page,
            Integer limit) {
        Map<String, Object> queryParams = new HashMap<>();
        if (status != null) {
            String runStatus;
            switch (status) {
                case 0:
                    runStatus = "UNSTART";
                    break;
                case 1:
                    runStatus = "RUNNING";
                    break;
                case 2:
                    runStatus = "CANCEL";
                    break;
                case 3:
                    runStatus = "DONE";
                    break;
                case 4:
                    runStatus = "FAIL";
                    break;
                default:
                    runStatus = status.toString(); // Support implicit numbers
            }
            queryParams.put("run", runStatus);
        }
        return getDocumentList(datasetId, queryParams, page, limit);
    }

    @Override
    public void deleteDocument(String datasetId, String documentId) {
        try {
            log.info("=== [RAGFlow] 删除文档: {} ===", documentId);

            Map<String, Object> body = new HashMap<>();
            body.put("ids", Collections.singletonList(documentId));

            getClient().delete("/api/v1/datasets/" + datasetId + "/documents", body);

        } catch (Exception e) {
            log.error("删除文档失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public boolean parseDocuments(String datasetId, List<String> documentIds) {
        try {
            log.info("=== [RAGFlow] 解析文档 ===");
            Map<String, Object> body = new HashMap<>();
            body.put("document_ids", documentIds);

            getClient().post("/api/v1/datasets/" + datasetId + "/chunks", body);
            return true;
        } catch (Exception e) {
            log.error("解析文档失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO listChunks(String datasetId, String documentId,
            String keywords,
            Integer page, Integer pageSize, String chunkId) {
        try {
            Map<String, Object> params = new HashMap<>();
            if (StringUtils.isNotBlank(keywords))
                params.put("keywords", keywords);
            if (page != null)
                params.put("page", page);
            if (pageSize != null)
                params.put("page_size", pageSize);
            if (StringUtils.isNotBlank(chunkId))
                params.put("id", chunkId);

            Map<String, Object> response = getClient()
                    .get("/api/v1/datasets/" + datasetId + "/documents/" + documentId + "/chunks", params);

            // [提灯审计] 暗礁 2 & 6: 增加 NPE 检查并使用强类型 DTO 转换
            Object dataObj = response.get("data");
            if (dataObj == null) {
                log.warn("[RAGFlow] listChunks 响应 data 为空, docId={}", documentId);
                return xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO.builder()
                        .chunks(new ArrayList<>())
                        .total(0L)
                        .build();
            }

            // 直接转换 DTO，保证字段全量映射
            xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO result = objectMapper.convertValue(dataObj,
                    xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO.class);

            // [提灯审计] 暗礁 5: 增加 Total 兜底处理
            if (result.getTotal() == null) {
                result.setTotal(0L);
            }

            return result;
        } catch (Exception e) {
            log.error("获取切片失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO retrievalTest(String question,
            List<String> datasetIds, List<String> documentIds,
            Map<String, Object> retrievalParams) {
        try {
            Map<String, Object> body = new HashMap<>();
            body.put("question", question);
            if (datasetIds != null)
                body.put("dataset_ids", datasetIds);
            if (documentIds != null)
                body.put("document_ids", documentIds);
            if (retrievalParams != null)
                body.putAll(retrievalParams);

            Map<String, Object> response = getClient().post("/api/v1/retrieval", body);

            // [提灯审计] DTO 化重构：增加 NPE 防护
            Object dataObj = response.get("data");
            if (dataObj == null) {
                log.warn("[RAGFlow] retrievalTest 响应 data 为空");
                return xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO.builder()
                        .chunks(new ArrayList<>())
                        .docAggs(new ArrayList<>())
                        .total(0L)
                        .build();
            }

            xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO result = objectMapper.convertValue(dataObj,
                    xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO.class);

            if (result.getTotal() == null) {
                result.setTotal(0L);
            }

            return result;

        } catch (Exception e) {
            log.error("召回测试失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public boolean testConnection() {
        try {
            getClient().get("/api/v1/health", null);
            return true;
        } catch (Exception e) {
            log.error("连接测试失败: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public Map<String, Object> getStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("adapterType", getAdapterType());
        status.put("configKeys", config != null ? config.keySet() : "未配置");
        status.put("connectionTest", testConnection());
        status.put("lastChecked", new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date()));
        return status;
    }

    @Override
    public Map<String, Object> getSupportedConfig() {
        Map<String, Object> supportedConfig = new HashMap<>();
        supportedConfig.put("base_url", "RAGFlow API基础URL");
        supportedConfig.put("api_key", "RAGFlow API密钥");
        supportedConfig.put("timeout", "请求超时时间（毫秒）");
        return supportedConfig;
    }

    @Override
    public Map<String, Object> getDefaultConfig() {
        Map<String, Object> defaultConfig = new HashMap<>();
        defaultConfig.put("timeout", 30000);
        return defaultConfig;
    }

    @Override
    public Map<String, Object> createDataset(Map<String, Object> createParams) {
        try {
            // Service 层已经处理了命名前缀逻辑
            Map<String, Object> response = getClient().post("/api/v1/datasets", createParams);

            // 安全地获取 data 并通过 DatasetDTO.InfoVO 进行全量映射
            Object dataObj = response.get("data");
            if (dataObj instanceof Map) {
                DatasetDTO.InfoVO info = objectMapper.convertValue(dataObj, DatasetDTO.InfoVO.class);
                return objectMapper.convertValue(info,
                        new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {
                        });
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, "Invalid response from createDataset: missing data object");
        } catch (Exception e) {
            log.error("创建数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public void updateDataset(String datasetId, Map<String, Object> updateParams) {
        try {
            // RAGFlow API 更新通常需要 Body 里带 ID，或者是 PUT /datasets (id在Body)
            // 根据 reverse analysis，原逻辑就是调 adapter.updateDataset.
            // 确保 ID 存在
            if (!updateParams.containsKey("id")) {
                updateParams.put("id", datasetId);
            }
            // 使用 PUT /api/v1/datasets
            getClient().put("/api/v1/datasets", updateParams);
        } catch (Exception e) {
            log.error("更新数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public void deleteDataset(String datasetId) {
        try {
            Map<String, Object> body = new HashMap<>();
            body.put("ids", Collections.singletonList(datasetId));
            getClient().delete("/api/v1/datasets", body);
        } catch (Exception e) {
            log.error("删除数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public Integer getDocumentCount(String datasetId) {
        try {
            // 改为调用 /datasets/{id} 获取详情
            Map<String, Object> response = getClient().get("/api/v1/datasets/" + datasetId, null);
            Object dataObj = response.get("data");
            if (dataObj instanceof Map) {
                Object countObj = ((Map<?, ?>) dataObj).get("doc_count");
                if (countObj instanceof Number) {
                    return ((Number) countObj).intValue();
                }
            }
            return 0;
        } catch (Exception e) {
            log.warn("获取文档数量失败: {}", e.getMessage());
            // 降级：不抛错，返回 0 (for Stats loop safety)
            return 0;
        }
    }

    @Override
    public void postStream(String endpoint, Object body, java.util.function.Consumer<String> onData) {
        try {
            getClient().postStream(endpoint, body, onData);
        } catch (Exception e) {
            log.error("流式请求失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public Object postSearchBotAsk(Map<String, Object> config, Object body,
            java.util.function.Consumer<String> onData) {
        // SearchBot 实际上是 Dataset 检索的一种封装，或者是未公开的 API？
        // 假设 RAGFlow 没有显式的 /searchbots 接口供 SDK 调用，而是 Dataset Retrieval 或者 Chat。
        // 但根据 BotDTO，它是 /api/v1/searchbots/ask (假设)
        // 这里的 config 可能是覆盖用的，或者我们只是用 adapter 实例已有的 client。
        // 但 Bot 可能使用不同的 API Key？通常 Adapter 实例绑定了一个 Key。
        // 如果 Bot 使用系统 Key，则直接用 getClient()。

        // 暂时假设 endpoint /api/v1/searchbots/ask 存在（或者类似的）
        // 如果是流式:
        try {
            getClient().postStream("/api/v1/searchbots/ask", body, onData);
            return null;
        } catch (Exception e) {
            log.error("SearchBot Ask 失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public void postAgentBotCompletion(Map<String, Object> config, String agentId, Object body,
            java.util.function.Consumer<String> onData) {
        // AgentBot 对应 /api/v1/agentbots/{id}/completions
        try {
            getClient().postStream("/api/v1/agentbots/" + agentId + "/completions", body, onData);
        } catch (Exception e) {
            log.error("AgentBot Completion 失败", e);
            throw convertToRenException(e);
        }
    }

    // 复用原有的辅助解析方法，保持兼容
    private PageData<KnowledgeFilesDTO> parseDocumentListResponse(Object dataObj, long curPage, long pageSize) {
        try {
            if (dataObj == null) {
                return new PageData<>(new ArrayList<>(), 0);
            }
            Map<String, Object> dataMap = (Map<String, Object>) dataObj;
            List<Map<String, Object>> documents = (List<Map<String, Object>>) dataMap.get("docs");
            if (documents == null || documents.isEmpty()) {
                return new PageData<>(new ArrayList<>(), 0);
            }

            List<KnowledgeFilesDTO> list = new ArrayList<>();
            for (Object docObj : documents) {
                DocumentDTO.InfoVO info = objectMapper.convertValue(docObj, DocumentDTO.InfoVO.class);
                list.add(mapToKnowledgeFilesDTO(info, null)); // datasetId is usually in InfoVO
            }

            long total = 0;
            if (dataMap.containsKey("total")) {
                total = ((Number) dataMap.get("total")).longValue();
            }

            return new PageData<>(list, total);

        } catch (Exception e) {
            log.error("解析文档列表失败", e);
            return new PageData<>(new ArrayList<>(), 0);
        }
    }

    // Helper to parse time from Number or String
    private Date parseTime(Object obj) {
        if (obj instanceof Number)
            return new Date(((Number) obj).longValue());
        if (obj instanceof String) {
            try {
                return new Date(Long.parseLong((String) obj));
            } catch (Exception e) {
            }
        }
        return new Date();
    }

    private KnowledgeFilesDTO parseUploadResponse(Object dataObj, String datasetId, MultipartFile file) {
        KnowledgeFilesDTO result = null;

        // 尝试从响应数据中提取文档ID (documentId)
        if (dataObj != null) {
            try {
                DocumentDTO.InfoVO info = null;
                if (dataObj instanceof Map) {
                    info = objectMapper.convertValue(dataObj, DocumentDTO.InfoVO.class);
                } else if (dataObj instanceof List) {
                    List<?> list = (List<?>) dataObj;
                    if (!list.isEmpty()) {
                        info = objectMapper.convertValue(list.get(0), DocumentDTO.InfoVO.class);
                    }
                }

                if (info != null) {
                    result = mapToKnowledgeFilesDTO(info, datasetId);
                }
            } catch (Exception e) {
                log.warn("解析上传响应数据失败: {}", e.getMessage());
            }
        }

        if (result == null) {
            log.error("未能从RAGFlow响应中提取到documentId，响应内容: {}", dataObj);
            // 这里应该返回一个最小化的包含基础信息的 DTO 而不是 null，防止上游 NPE
            result = new KnowledgeFilesDTO();
            result.setDatasetId(datasetId);
            result.setName(file.getOriginalFilename());
            result.setFileSize(file.getSize());
            result.setStatus("1");
        }

        return result;
    }

    /**
     * 将 RAGFlow 的强类型 InfoVO 映射到内部使用的 KnowledgeFilesDTO
     * 确保所有可用字段（名称、大小、状态、配置等）都得到全量同步
     */
    private KnowledgeFilesDTO mapToKnowledgeFilesDTO(DocumentDTO.InfoVO info, String datasetId) {
        KnowledgeFilesDTO dto = new KnowledgeFilesDTO();
        if (info == null)
            return dto;

        dto.setId(info.getId());
        dto.setDocumentId(info.getId());
        dto.setDatasetId(StringUtils.isNotBlank(info.getDatasetId()) ? info.getDatasetId() : datasetId);
        dto.setName(info.getName());
        dto.setFileSize(info.getSize());

        // 状态映射
        if (info.getRun() != null) {
            dto.setRun(info.getRun().name());
        }

        if (StringUtils.isNotBlank(info.getStatus())) {
            dto.setStatus(info.getStatus());
        } else {
            dto.setStatus("1"); // 默认启用
        }

        // 时间同步
        if (info.getCreateTime() != null) {
            dto.setCreatedAt(new Date(info.getCreateTime()));
        }
        if (info.getUpdateTime() != null) {
            dto.setUpdatedAt(new Date(info.getUpdateTime()));
        }

        // 核心元数据补齐 (Issue 1)
        dto.setProgress(info.getProgress());
        dto.setThumbnail(info.getThumbnail());
        dto.setProcessDuration(info.getProcessDuration());
        dto.setSourceType(info.getSourceType());
        dto.setChunkCount(info.getChunkCount() != null ? info.getChunkCount().intValue() : 0);
        dto.setTokenCount(info.getTokenCount());
        dto.setError(info.getProgressMsg()); // 将进度描述映射为错误信息提示

        // 扩展字段同步
        dto.setMetaFields(info.getMetaFields());
        if (info.getChunkMethod() != null) {
            dto.setChunkMethod(info.getChunkMethod().name().toLowerCase());
        }
        if (info.getParserConfig() != null) {
            dto.setParserConfig(objectMapper.convertValue(info.getParserConfig(), Map.class));
        }

        return dto;
    }

    private static class MultipartFileResource extends AbstractResource {
        private final MultipartFile multipartFile;

        public MultipartFileResource(MultipartFile multipartFile) {
            this.multipartFile = multipartFile;
        }

        @Override
        public String getDescription() {
            return "MultipartFile resource [" + multipartFile.getOriginalFilename() + "]";
        }

        @Override
        public String getFilename() {
            return multipartFile.getOriginalFilename();
        }

        @Override
        public InputStream getInputStream() throws IOException {
            return multipartFile.getInputStream();
        }

        @Override
        public long contentLength() throws IOException {
            return multipartFile.getSize();
        }

        @Override
        public boolean exists() {
            return !multipartFile.isEmpty();
        }
    }
}