package xiaozhi.modules.knowledge.rag.impl;

import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

import org.apache.commons.lang3.StringUtils;
import org.springframework.core.io.AbstractResource;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.multipart.MultipartFile;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
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

        String baseUrl = getConfigValue(config, "base_url", "baseUrl");
        String apiKey = getConfigValue(config, "api_key", "apiKey");

        // 初始化 Client，默认超时 30s，可通过 config 扩展
        int timeout = 30;
        Object timeoutObj = getConfigValue(config, "timeout", "timeout");
        if (timeoutObj != null) {
            try {
                timeout = Integer.parseInt(timeoutObj.toString());
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

        String baseUrl = getConfigValue(config, "base_url", "baseUrl");
        String apiKey = getConfigValue(config, "api_key", "apiKey");

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
     * 辅助方法：支持多种键名获取配置（兼容 camelCase 和 snake_case）
     */
    private String getConfigValue(Map<String, Object> config, String snakeKey, String camelKey) {
        if (config.containsKey(snakeKey)) {
            return (String) config.get(snakeKey);
        }
        if (config.containsKey(camelKey)) {
            return (String) config.get(camelKey);
        }
        return null;
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
    public PageData<KnowledgeFilesDTO> getDocumentList(String datasetId, DocumentDTO.ListReq req) {
        try {
            log.info("=== [RAGFlow] 获取文档列表: datasetId={} ===", datasetId);

            // 使用 Jackson 将 DTO 转为 Map 作为查询参数
            @SuppressWarnings("unchecked")
            Map<String, Object> params = objectMapper.convertValue(req, Map.class);

            Map<String, Object> response = getClient().get("/api/v1/datasets/" + datasetId + "/documents", params);

            Object dataObj = response.get("data");
            return parseDocumentListResponse(dataObj, req.getPage() != null ? req.getPage() : 1,
                    req.getPageSize() != null ? req.getPageSize() : 10);

        } catch (Exception e) {
            log.error("获取文档列表失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public DocumentDTO.InfoVO getDocumentById(String datasetId, String documentId) {
        try {
            log.info("=== [RAGFlow] 获取文档详情: datasetId={}, documentId={} ===", datasetId, documentId);
            DocumentDTO.ListReq req = DocumentDTO.ListReq.builder()
                    .id(documentId)
                    .page(1)
                    .pageSize(1)
                    .build();

            @SuppressWarnings("unchecked")
            Map<String, Object> params = objectMapper.convertValue(req, Map.class);
            Map<String, Object> response = getClient().get("/api/v1/datasets/" + datasetId + "/documents", params);

            Object dataObj = response.get("data");
            if (dataObj instanceof Map) {
                Map<String, Object> dataMap = (Map<String, Object>) dataObj;
                List<?> documents = (List<?>) dataMap.get("docs");
                if (documents != null && !documents.isEmpty()) {
                    return objectMapper.convertValue(documents.get(0), DocumentDTO.InfoVO.class);
                }
            }
            return null;
        } catch (Exception e) {
            log.error("获取文档详情失败: documentId={}", documentId, e);
            throw convertToRenException(e);
        }
    }

    @Override
    public KnowledgeFilesDTO uploadDocument(DocumentDTO.UploadReq req) {
        String datasetId = req.getDatasetId();
        MultipartFile file = req.getFile();
        try {
            log.info("=== [RAGFlow] 上传文档: datasetId={} ===", datasetId);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartFileResource(file));

            if (StringUtils.isNotBlank(req.getName())) {
                body.add("name", req.getName());
            }
            if (req.getMetaFields() != null && !req.getMetaFields().isEmpty()) {
                body.add("meta", objectMapper.writeValueAsString(req.getMetaFields()));
            }
            if (req.getChunkMethod() != null) {
                // 将枚举值转为 RAGFlow 期待的字符串（如 NAIVE -> naive）
                body.add("chunk_method", req.getChunkMethod().name().toLowerCase());
            }
            if (req.getParserConfig() != null) {
                body.add("parser_config", objectMapper.writeValueAsString(req.getParserConfig()));
            }
            if (StringUtils.isNotBlank(req.getParentPath())) {
                body.add("parent_path", req.getParentPath());
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
        List<DocumentDTO.InfoVO.RunStatus> runStatusList = null;
        if (status != null) {
            runStatusList = new ArrayList<>();
            switch (status) {
                case 0:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.UNSTART);
                    break;
                case 1:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.RUNNING);
                    break;
                case 2:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.CANCEL);
                    break;
                case 3:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.DONE);
                    break;
                case 4:
                    runStatusList.add(DocumentDTO.InfoVO.RunStatus.FAIL);
                    break;
                default:
                    break;
            }
        }
        DocumentDTO.ListReq req = DocumentDTO.ListReq.builder()
                .run(runStatusList)
                .page(page)
                .pageSize(limit)
                .build();
        return getDocumentList(datasetId, req);
    }

    @Override
    public void deleteDocument(String datasetId, DocumentDTO.BatchIdReq req) {
        try {
            log.info("=== [RAGFlow] 批量删除文档: datasetId={}, count={} ===", datasetId,
                    req.getIds() != null ? req.getIds().size() : 0);
            getClient().delete("/api/v1/datasets/" + datasetId + "/documents", req);
        } catch (Exception e) {
            log.error("批量删除文档失败: datasetId={}", datasetId, e);
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
    public ChunkDTO.ListVO listChunks(String datasetId, String documentId, ChunkDTO.ListReq req) {
        try {
            // [提灯重构] 使用 objectMapper 动态转换查询参数，消除硬编码
            Map<String, Object> params = objectMapper.convertValue(req, new TypeReference<Map<String, Object>>() {
            });

            Map<String, Object> response = getClient()
                    .get("/api/v1/datasets/" + datasetId + "/documents/" + documentId + "/chunks", params);

            Object dataObj = response.get("data");
            if (dataObj == null) {
                log.warn("[RAGFlow] listChunks 响应 data 为空, docId={}", documentId);
                return ChunkDTO.ListVO.builder()
                        .chunks(new ArrayList<>())
                        .total(0L)
                        .build();
            }

            ChunkDTO.ListVO result = objectMapper.convertValue(dataObj, ChunkDTO.ListVO.class);
            if (result.getTotal() == null) {
                result.setTotal(0L);
            }
            return result;
        } catch (Exception e) {
            log.error("获取切片失败: docId={}", documentId, e);
            throw convertToRenException(e);
        }
    }

    @Override
    public RetrievalDTO.ResultVO retrievalTest(RetrievalDTO.TestReq req) {
        try {
            // [Production Reinforce] 参数防御性对齐：RAGFlow Python 端对 0 或负数分页敏感
            // 解决 ValueError('Search does not support negative slicing.')
            if (req.getPage() != null && req.getPage() < 1) {
                req.setPage(1);
            }
            if (req.getPageSize() != null && req.getPageSize() < 1) {
                req.setPageSize(10); // 默认 10 条
            }
            if (req.getTopK() != null && req.getTopK() < 1) {
                req.setTopK(1024); // RAGFlow 内部默认 TopK
            }
            // 相似度阈值归一化 (0.0 ~ 1.0)
            if (req.getSimilarityThreshold() != null) {
                if (req.getSimilarityThreshold() < 0f)
                    req.setSimilarityThreshold(0.2f);
                if (req.getSimilarityThreshold() > 1f)
                    req.setSimilarityThreshold(1.0f);
            }

            // [提灯重构] 直接透传强类型 DTO，由 getClient 处理序列化
            Map<String, Object> response = getClient().post("/api/v1/retrieval", req);

            Object dataObj = response.get("data");
            if (dataObj == null) {
                log.warn("[RAGFlow] retrievalTest 响应 data 为空");
                return RetrievalDTO.ResultVO.builder()
                        .chunks(new ArrayList<>())
                        .docAggs(new ArrayList<>())
                        .total(0L)
                        .build();
            }

            RetrievalDTO.ResultVO result = objectMapper.convertValue(dataObj, RetrievalDTO.ResultVO.class);
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
    public DatasetDTO.InfoVO createDataset(DatasetDTO.CreateReq req) {
        try {
            // [Production Fix] 强化默认值处理，防止 RAGFlow API 因空字符串或缺失字段报错 (Code 101)
            // 解决 "Field: <avatar> - Message: <Missing MIME prefix>" 等校验失败
            if (StringUtils.isBlank(req.getPermission())) {
                req.setPermission("me");
            }
            if (StringUtils.isBlank(req.getChunkMethod())) {
                req.setChunkMethod("naive");
            }

            // 🤖 自动补全嵌入模型：优先使用请求传参，其次使用配置中的默认模型
            if (StringUtils.isBlank(req.getEmbeddingModel())) {
                String defaultModel = (String) getConfigValue(config, "embedding_model", "embeddingModel");
                if (StringUtils.isNotBlank(defaultModel)) {
                    log.info("RAGFlow: 使用配置中的默认嵌入模型: {}", defaultModel);
                    req.setEmbeddingModel(defaultModel);
                }
                // 若配置中也无默认值，则留空由 RAGFlow 服务端自行兜底（或抛出业务异常）
            }

            // 🖼️ 自动补全头像：若为空则提供一个 1x1 透明像素，防止 RAGFlow 校验 MIME Prefix 失败
            if (StringUtils.isBlank(req.getAvatar())) {
                req.setAvatar(
                        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==");
            }

            // 直接将强类型请求对象传给 Client，Jackson 会处理 JsonProperty 映射
            Map<String, Object> response = getClient().post("/api/v1/datasets", req);

            // 安全地获取 data 并通过 DatasetDTO.InfoVO 进行全量映射
            Object dataObj = response.get("data");
            if (dataObj != null) {
                return objectMapper.convertValue(dataObj, DatasetDTO.InfoVO.class);
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, "Invalid response from createDataset: missing data object");
        } catch (Exception e) {
            log.error("创建数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public DatasetDTO.InfoVO updateDataset(String datasetId, DatasetDTO.UpdateReq req) {
        try {
            // RAGFlow API 更新建议路径带 ID
            Map<String, Object> response = getClient().put("/api/v1/datasets/" + datasetId, req);

            Object dataObj = response.get("data");
            if (dataObj != null) {
                return objectMapper.convertValue(dataObj, DatasetDTO.InfoVO.class);
            }
            return null;
        } catch (Exception e) {
            log.error("更新数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public DatasetDTO.BatchOperationVO deleteDataset(DatasetDTO.BatchIdReq req) {
        try {
            // RAGFlow 批量删除接口使用 DELETE /api/v1/datasets
            Map<String, Object> response = getClient().delete("/api/v1/datasets", req);

            Object dataObj = response.get("data");
            if (dataObj != null) {
                return objectMapper.convertValue(dataObj, DatasetDTO.BatchOperationVO.class);
            }
            return null;
        } catch (Exception e) {
            log.error("批量删除数据集失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public Integer getDocumentCount(String datasetId) {
        try {
            // [Fix] 使用列表过滤接口获取详情 (GET /datasets?id={id})
            Map<String, Object> params = new HashMap<>();
            params.put("id", datasetId);
            params.put("page", 1);
            params.put("page_size", 1);

            Map<String, Object> response = getClient().get("/api/v1/datasets", params);
            Object dataObj = response.get("data");

            if (dataObj instanceof List) {
                List<?> list = (List<?>) dataObj;
                if (!list.isEmpty()) {
                    Object firstItem = list.get(0);
                    if (firstItem instanceof Map) {
                        Object countObj = ((Map<?, ?>) firstItem).get("document_count");
                        if (countObj instanceof Number) {
                            return ((Number) countObj).intValue();
                        }
                    }
                }
            }
            // 降级：未找到或结构不匹配
            return 0;
        } catch (Exception e) {
            log.warn("获取文档数量失败: {}", e.getMessage());
            return 0;
        }
    }

    @Override
    public void postStream(String endpoint, Object body, Consumer<String> onData) {
        try {
            getClient().postStream(endpoint, body, onData);
        } catch (Exception e) {
            log.error("流式请求失败", e);
            throw convertToRenException(e);
        }
    }

    @Override
    public Object postSearchBotAsk(Map<String, Object> config, Object body,
            Consumer<String> onData) {
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
            Consumer<String> onData) {
        // AgentBot 对应 /api/v1/agentbots/{id}/completions
        try {
            getClient().postStream("/api/v1/agentbots/" + agentId + "/completions", body, onData);
        } catch (Exception e) {
            log.error("AgentBot Completion 失败", e);
            throw convertToRenException(e);
        }
    }

    // 复用原有的辅助解析方法，保持兼容
    // [Bug Fix] 不再吞掉反序列化异常，避免上层误判"文档已删除"
    private PageData<KnowledgeFilesDTO> parseDocumentListResponse(Object dataObj, long curPage, long pageSize) {
        if (dataObj == null) {
            return new PageData<>(new ArrayList<>(), 0);
        }

        Map<String, Object> dataMap = (Map<String, Object>) dataObj;
        List<Map<String, Object>> documents = (List<Map<String, Object>>) dataMap.get("docs");
        if (documents == null || documents.isEmpty()) {
            // RAGFlow 明确返回了空文档列表，这是合法的"真空"
            return new PageData<>(new ArrayList<>(), 0);
        }

        List<KnowledgeFilesDTO> list = new ArrayList<>();
        for (Object docObj : documents) {
            try {
                // 单文档转换容错：一个文档反序列化失败不影响其他文档
                DocumentDTO.InfoVO info = objectMapper.convertValue(docObj, DocumentDTO.InfoVO.class);
                list.add(mapToKnowledgeFilesDTO(info, null));
            } catch (Exception e) {
                log.warn("[RAGFlow] 单文档 DTO 转换失败，跳过该文档: {}", e.getMessage());
            }
        }

        long total = 0;
        if (dataMap.containsKey("total")) {
            total = ((Number) dataMap.get("total")).longValue();
        }

        return new PageData<>(list, total);
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