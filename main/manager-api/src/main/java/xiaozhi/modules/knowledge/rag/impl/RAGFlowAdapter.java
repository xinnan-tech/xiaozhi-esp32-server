package xiaozhi.modules.knowledge.rag.impl;

import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.core.io.AbstractResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.util.UriComponentsBuilder;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;

/**
 * RAGFlow知识库适配器实现
 */
@Slf4j
public class RAGFlowAdapter extends KnowledgeBaseAdapter {

    private static final String ADAPTER_TYPE = "ragflow";

    private RestTemplate restTemplate;
    private ObjectMapper objectMapper;
    private Map<String, Object> config;

    public RAGFlowAdapter() {
        this.restTemplate = new RestTemplate();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public String getAdapterType() {
        return ADAPTER_TYPE;
    }

    @Override
    public void initialize(Map<String, Object> config) {
        this.config = config;
        log.info("RAGFlow适配器初始化完成，配置参数: {}", config.keySet());
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

    @Override
    public PageData<KnowledgeFilesDTO> getDocumentList(String datasetId, Map<String, Object> queryParams, Integer page,
            Integer limit) {
        try {
            log.info("=== RAGFlow适配器开始获取文档列表 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents";

            // 构建查询参数
            StringBuilder urlBuilder = new StringBuilder(url);
            List<String> params = new ArrayList<>();

            // 基本分页参数
            if (page > 0) {
                params.add("page=" + page);
            }
            if (limit > 0) {
                params.add("page_size=" + limit);
            }

            // 查询参数处理
            if (queryParams != null) {
                // 关键词搜索
                if (queryParams.containsKey("name")) {
                    params.add("keywords=" + queryParams.get("name"));
                }

                // 排序参数
                if (queryParams.containsKey("orderby")) {
                    String orderby = (String) queryParams.get("orderby");
                    if ("create_time".equals(orderby) || "update_time".equals(orderby)) {
                        params.add("orderby=" + orderby);
                    }
                }

                // 排序方向
                if (queryParams.containsKey("desc")) {
                    Boolean desc = (Boolean) queryParams.get("desc");
                    params.add("desc=" + (desc != null ? desc : true));
                }

                // 文档ID过滤
                if (queryParams.containsKey("id")) {
                    params.add("id=" + queryParams.get("id"));
                }

                // 文档名称过滤
                if (queryParams.containsKey("documentName")) {
                    params.add("name=" + queryParams.get("documentName"));
                }

                // 创建时间范围过滤
                if (queryParams.containsKey("createTimeFrom")) {
                    Long createTimeFrom = (Long) queryParams.get("createTimeFrom");
                    if (createTimeFrom != null && createTimeFrom > 0) {
                        params.add("create_time_from=" + createTimeFrom);
                    }
                }

                if (queryParams.containsKey("createTimeTo")) {
                    Long createTimeTo = (Long) queryParams.get("createTimeTo");
                    if (createTimeTo != null && createTimeTo > 0) {
                        params.add("create_time_to=" + createTimeTo);
                    }
                }

                // 文件后缀过滤
                if (queryParams.containsKey("suffix")) {
                    Object suffixObj = queryParams.get("suffix");
                    if (suffixObj instanceof String) {
                        params.add("suffix=" + suffixObj);
                    } else if (suffixObj instanceof List) {
                        @SuppressWarnings("unchecked")
                        List<String> suffixes = (List<String>) suffixObj;
                        if (!suffixes.isEmpty()) {
                            params.add("suffix=" + String.join(",", suffixes));
                        }
                    }
                }

                // 处理状态过滤
                if (queryParams.containsKey("run")) {
                    Object runObj = queryParams.get("run");
                    if (runObj instanceof String) {
                        params.add("run=" + runObj);
                    } else if (runObj instanceof Integer) {
                        params.add("run=" + runObj);
                    } else if (runObj instanceof List) {
                        @SuppressWarnings("unchecked")
                        List<Object> runStatuses = (List<Object>) runObj;
                        if (!runStatuses.isEmpty()) {
                            List<String> runParams = new ArrayList<>();
                            for (Object status : runStatuses) {
                                if (status != null) {
                                    runParams.add(status.toString());
                                }
                            }
                            params.add("run=" + String.join(",", runParams));
                        }
                    }
                }
            }

            if (!params.isEmpty()) {
                urlBuilder.append("?").append(String.join("&", params));
            }

            url = urlBuilder.toString();
            log.debug("RAGFlow API请求URL: {}", url);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<String> requestEntity = new HttpEntity<>(headers);

            // 发送GET请求
            log.info("发送GET请求到RAGFlow API获取文档列表...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            log.debug("RAGFlow API原始响应: {}", responseBody);

            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Object dataObj = responseMap.get("data");
                log.debug("RAGFlow API返回的data字段: {}", dataObj);
                return parseDocumentListResponse(dataObj, page, limit);
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, errorDetail);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器获取文档列表失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器获取文档列表操作结束 ===");
        }
    }

    @Override
    public KnowledgeFilesDTO getDocumentById(String datasetId, String documentId) {
        // 实现根据ID获取文档详情的逻辑
        // 这里需要调用RAGFlow API获取特定文档的详细信息
        throw new UnsupportedOperationException();
    }

    @Override
    public KnowledgeFilesDTO uploadDocument(String datasetId, MultipartFile file, String name,
            Map<String, Object> metaFields, String chunkMethod,
            Map<String, Object> parserConfig) {
        try {
            log.info("=== RAGFlow适配器开始文档上传操作 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents";

            // 构建多部分请求
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();

            // 添加文件
            body.add("file", new MultipartFileResource(file));

            // 添加其他参数
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

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

            // 发送POST请求
            log.info("发送POST请求到RAGFlow API上传文档...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            log.debug("RAGFlow API获取文档数量原始响应: {}", responseBody);
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            log.debug("RAGFlow API获取文档数量响应码: {}, data字段: {}", code, responseMap.get("data"));

            if (code != null && code == 0) {
                Object dataObj = responseMap.get("data");
                return parseUploadResponse(dataObj, datasetId, file);
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, errorDetail);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器文档上传失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器文档上传操作结束 ===");
        }
    }

    @Override
    public PageData<KnowledgeFilesDTO> getDocumentListByStatus(String datasetId, Integer status, Integer page,
            Integer limit) {
        try {
            log.info("=== RAGFlow适配器开始根据状态获取文档列表 ===");
            log.info("datasetId: {}, status: {}, page: {}, limit: {}", datasetId, status, page, limit);

            // 构建查询参数，包含状态过滤
            Map<String, Object> queryParams = new HashMap<>();

            // 将状态码转换为RAGFlow API支持的格式
            if (status != null) {
                // 根据KnowledgeFilesDTO中的状态常量映射
                String runStatus;
                switch (status) {
                    case 0: // STATUS_UNSTART
                        runStatus = "UNSTART";
                        break;
                    case 1: // STATUS_RUNNING
                        runStatus = "RUNNING";
                        break;
                    case 2: // STATUS_CANCEL
                        runStatus = "CANCEL";
                        break;
                    case 3: // STATUS_DONE
                        runStatus = "DONE";
                        break;
                    case 4: // STATUS_FAIL
                        runStatus = "FAIL";
                        break;
                    default:
                        runStatus = status.toString(); // 使用数字格式
                }
                queryParams.put("run", runStatus);
                log.debug("状态过滤参数: run={}", runStatus);
            }

            // 调用通用的文档列表获取方法
            return getDocumentList(datasetId, queryParams, page, limit);

        } catch (Exception e) {
            log.error("RAGFlow适配器根据状态获取文档列表失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器根据状态获取文档列表操作结束 ===");
        }
    }

    @Override
    public void deleteDocument(String datasetId, String documentId) {
        try {
            log.info("=== RAGFlow适配器开始删除文档 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents";

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            // 构建请求体 - 根据API文档，需要传递文档ID列表
            Map<String, Object> requestBody = new HashMap<>();
            List<String> documentIds = new ArrayList<>();
            documentIds.add(documentId);
            requestBody.put("ids", documentIds);

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送DELETE请求
            log.info("发送DELETE请求到RAGFlow API删除文档...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.DELETE, requestEntity,
                    String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                log.info("文档删除成功: documentId={}, datasetId={}", documentId, datasetId);
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, errorDetail);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器删除文档失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器删除文档操作结束 ===");
        }
    }

    @Override
    public boolean parseDocuments(String datasetId, List<String> documentIds) {
        try {
            log.info("=== RAGFlow适配器开始解析文档 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/chunks";

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            // 构建请求体 - 根据API文档，需要传递文档ID列表
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("document_ids", documentIds);

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送POST请求
            log.info("发送POST请求到RAGFlow API解析文档...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity,
                    String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                log.info("文档解析成功: datasetId={}, 文档数量={}", datasetId, documentIds.size());
                return true;
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, errorDetail);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器解析文档失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器解析文档操作结束 ===");
        }
    }

    @Override
    public Map<String, Object> listChunks(String datasetId, String documentId, String keywords,
            Integer page, Integer pageSize, String chunkId) {
        try {
            log.info("=== RAGFlow适配器开始列出切片 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            // 构建URL和查询参数
            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents/" + documentId + "/chunks";

            // 构建查询参数
            UriComponentsBuilder builder = UriComponentsBuilder.fromHttpUrl(url);
            if (StringUtils.isNotBlank(keywords)) {
                builder.queryParam("keywords", keywords);
            }
            if (page != null) {
                builder.queryParam("page", page);
            }
            if (pageSize != null) {
                builder.queryParam("page_size", pageSize);
            }
            if (StringUtils.isNotBlank(chunkId)) {
                builder.queryParam("id", chunkId);
            }

            String finalUrl = builder.toUriString();

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<String> requestEntity = new HttpEntity<>(headers);

            // 发送GET请求
            log.info("发送GET请求到RAGFlow API列出切片...");
            ResponseEntity<String> response = restTemplate.exchange(finalUrl, HttpMethod.GET, requestEntity,
                    String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Map<String, Object> data = (Map<String, Object>) responseMap.get("data");

                // 解析切片数据
                List<Map<String, Object>> chunks = (List<Map<String, Object>>) data.get("chunks");
                Map<String, Object> doc = (Map<String, Object>) data.get("doc");
                Integer total = (Integer) data.get("total");

                // 构建返回结果
                Map<String, Object> result = new HashMap<>();
                result.put("chunks", chunks);
                result.put("document", doc);
                result.put("total", total);

                log.info("切片列表获取成功: datasetId={}, documentId={}, 切片数量={}", datasetId, documentId, total);
                return result;
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, errorDetail);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器列出切片失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器列出切片操作结束 ===");
        }
    }

    @Override
    public Map<String, Object> retrievalTest(String question, List<String> datasetIds, List<String> documentIds,
            Map<String, Object> retrievalParams) {
        try {
            log.info("=== RAGFlow适配器开始召回测试 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/retrieval";

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();

            // 必需参数
            if (StringUtils.isBlank(question)) {
                throw new RenException(ErrorCode.RAG_API_ERROR, "问题内容不能为空");
            }
            requestBody.put("question", question);

            // 可选参数
            if (datasetIds != null && !datasetIds.isEmpty()) {
                requestBody.put("dataset_ids", datasetIds);
            }
            if (documentIds != null && !documentIds.isEmpty()) {
                requestBody.put("document_ids", documentIds);
            }

            // 处理检索参数
            if (retrievalParams != null) {
                if (retrievalParams.containsKey("page")) {
                    requestBody.put("page", retrievalParams.get("page"));
                }
                if (retrievalParams.containsKey("page_size")) {
                    requestBody.put("page_size", retrievalParams.get("page_size"));
                }
                if (retrievalParams.containsKey("similarity_threshold")) {
                    requestBody.put("similarity_threshold", retrievalParams.get("similarity_threshold"));
                }
                if (retrievalParams.containsKey("vector_similarity_weight")) {
                    requestBody.put("vector_similarity_weight", retrievalParams.get("vector_similarity_weight"));
                }
                if (retrievalParams.containsKey("top_k")) {
                    requestBody.put("top_k", retrievalParams.get("top_k"));
                }
                if (retrievalParams.containsKey("rerank_id")) {
                    requestBody.put("rerank_id", retrievalParams.get("rerank_id"));
                }
                if (retrievalParams.containsKey("keyword")) {
                    requestBody.put("keyword", retrievalParams.get("keyword"));
                }
                if (retrievalParams.containsKey("highlight")) {
                    requestBody.put("highlight", retrievalParams.get("highlight"));
                }
                if (retrievalParams.containsKey("cross_languages")) {
                    requestBody.put("cross_languages", retrievalParams.get("cross_languages"));
                }
                if (retrievalParams.containsKey("metadata_condition")) {
                    requestBody.put("metadata_condition", retrievalParams.get("metadata_condition"));
                }
            }

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送POST请求
            log.info("发送POST请求到RAGFlow API进行召回测试...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Map<String, Object> data = (Map<String, Object>) responseMap.get("data");

                // 解析召回结果
                List<Map<String, Object>> chunks = (List<Map<String, Object>>) data.get("chunks");
                List<Map<String, Object>> docAggs = (List<Map<String, Object>>) data.get("doc_aggs");
                Integer total = (Integer) data.get("total");

                // 构建返回结果
                Map<String, Object> result = new HashMap<>();
                result.put("chunks", chunks);
                result.put("doc_aggs", docAggs);
                result.put("total", total);

                log.info("召回测试成功: 问题='{}', 召回切片数量={}", question, total);
                return result;
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, errorDetail);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器召回测试失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器召回测试操作结束 ===");
        }
    }

    @Override
    public boolean testConnection() {
        try {
            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/health";

            HttpHeaders headers = new HttpHeaders();
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<String> requestEntity = new HttpEntity<>(headers);

            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, requestEntity, String.class);

            return response.getStatusCode().is2xxSuccessful();

        } catch (Exception e) {
            log.error("RAGFlow适配器连接测试失败: {}", e.getMessage());
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
    public String createDataset(Map<String, Object> createParams) {
        try {
            log.info("=== RAGFlow适配器开始创建数据集 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets";

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            if (createParams.containsKey("name")) {
                requestBody.put("name", createParams.get("name"));
            }
            if (createParams.containsKey("description")) {
                requestBody.put("description", createParams.get("description"));
            }

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送POST请求
            log.info("发送POST请求到RAGFlow API创建数据集...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Map<String, Object> data = (Map<String, Object>) responseMap.get("data");
                String datasetId = (String) data.get("id");
                log.info("数据集创建成功，datasetId: {}", datasetId);
                return datasetId;
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器创建数据集失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器创建数据集操作结束 ===");
        }
    }

    @Override
    public void updateDataset(String datasetId, Map<String, Object> updateParams) {
        try {
            log.info("=== RAGFlow适配器开始更新数据集 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets/" + datasetId;

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            if (updateParams.containsKey("name")) {
                requestBody.put("name", updateParams.get("name"));
            }
            if (updateParams.containsKey("description")) {
                requestBody.put("description", updateParams.get("description"));
            }

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送PUT请求
            log.info("发送PUT请求到RAGFlow API更新数据集...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.PUT, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                log.info("数据集更新成功，datasetId: {}", datasetId);
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器更新数据集失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器更新数据集操作结束 ===");
        }
    }

    @Override
    public void deleteDataset(String datasetId) {
        try {
            log.info("=== RAGFlow适配器开始删除数据集 ===");

            validateConfig(config);
            String baseUrl = (String) config.get("base_url");
            String apiKey = (String) config.get("api_key");

            String url = baseUrl + "/api/v1/datasets";

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            // 构建请求体 - 根据API文档，需要传递数据集ID列表
            Map<String, Object> requestBody = new HashMap<>();
            List<String> datasetIds = new ArrayList<>();
            datasetIds.add(datasetId);
            requestBody.put("ids", datasetIds);

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送DELETE请求
            log.info("发送DELETE请求到RAGFlow API删除数据集...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.DELETE, requestEntity,
                    String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, response.getStatusCode().toString());
            }

            String responseBody = response.getBody();
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                log.info("数据集删除成功，datasetId: {}", datasetId);
            } else {
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("RAGFlow适配器删除数据集失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== RAGFlow适配器删除数据集操作结束 ===");
        }
    }

    /**
     * 通过文档列表接口获取文档数量
     */
    @Override
    public Integer getDocumentCount(String datasetId) {
        try {
            log.info("尝试使用文档列表接口获取文档数量作为备用方案");

            // 构建查询参数，只获取第一页，页面大小为1，以减少网络开销
            Map<String, Object> queryParams = new HashMap<>();
            queryParams.put("page", 1);
            queryParams.put("page_size", 1);

            // 调用文档列表方法
            PageData<KnowledgeFilesDTO> pageData = getDocumentList(datasetId, queryParams, 1, 1);

            if (pageData != null) {
                log.info("通过文档列表接口获取文档数量成功，datasetId: {}, count: {}", datasetId, pageData.getTotal());
                return pageData.getTotal();
            }

            log.warn("通过文档列表接口获取文档数量失败，返回空结果");
            return 0;

        } catch (Exception e) {
            log.error("通过文档列表接口获取文档数量也失败: {}", e.getMessage());
            return 0;
        }
    }

    // 辅助方法
    private PageData<KnowledgeFilesDTO> parseDocumentListResponse(Object dataObj, long curPage, long pageSize) {
        try {
            if (dataObj == null) {
                log.warn("RAGFlow API返回的data字段为空");
                return new PageData<KnowledgeFilesDTO>(new ArrayList<>(), 0);
            }

            log.debug("parseDocumentListResponse接收到的dataObj类型: {}", dataObj.getClass().getName());
            log.debug("parseDocumentListResponse接收到的dataObj内容: {}", dataObj);

            Map<String, Object> dataMap = (Map<String, Object>) dataObj;

            // 解析文档列表 - 根据RAGFlow API文档，字段名是"docs"
            List<Map<String, Object>> documents = (List<Map<String, Object>>) dataMap.get("docs");
            if (documents == null || documents.isEmpty()) {
                log.info("RAGFlow API返回的文档列表为空");
                return new PageData<KnowledgeFilesDTO>(new ArrayList<>(), 0);
            }

            List<KnowledgeFilesDTO> knowledgeFilesList = new ArrayList<>();

            for (Map<String, Object> doc : documents) {
                KnowledgeFilesDTO knowledgeFile = new KnowledgeFilesDTO();

                // 解析文档基本信息 - 根据RAGFlow API文档调整字段名
                if (doc.containsKey("id")) {
                    knowledgeFile.setId((String) doc.get("id"));
                }
                if (doc.containsKey("name")) {
                    knowledgeFile.setName((String) doc.get("name"));
                }
                if (doc.containsKey("size")) {
                    // 文件大小字段可能是字符串或数字类型
                    Object sizeObj = doc.get("size");
                    if (sizeObj instanceof Number) {
                        knowledgeFile.setFileSize(((Number) sizeObj).longValue());
                    } else if (sizeObj instanceof String) {
                        try {
                            knowledgeFile.setFileSize(Long.parseLong((String) sizeObj));
                        } catch (NumberFormatException e) {
                            log.warn("无法解析size字符串: {}", sizeObj);
                            knowledgeFile.setFileSize(0L);
                        }
                    }
                }
                if (doc.containsKey("status")) {
                    // 状态字段可能是字符串或数字类型
                    Object statusObj = doc.get("status");
                    if (statusObj instanceof Number) {
                        knowledgeFile.setStatus(((Number) statusObj).intValue());
                    } else if (statusObj instanceof String) {
                        try {
                            knowledgeFile.setStatus(Integer.parseInt((String) statusObj));
                        } catch (NumberFormatException e) {
                            log.warn("无法解析status字符串: {}", statusObj);
                            knowledgeFile.setStatus(0);
                        }
                    }
                }
                if (doc.containsKey("create_time")) {
                    // RAGFlow API返回的时间戳可能是字符串或数字类型
                    Object createTimeObj = doc.get("create_time");
                    Long createTime = null;

                    if (createTimeObj instanceof Number) {
                        createTime = ((Number) createTimeObj).longValue();
                    } else if (createTimeObj instanceof String) {
                        try {
                            createTime = Long.parseLong((String) createTimeObj);
                        } catch (NumberFormatException e) {
                            log.warn("无法解析create_time字符串: {}", createTimeObj);
                        }
                    }

                    if (createTime != null && createTime > 0) {
                        knowledgeFile.setCreatedAt(new Date(createTime));
                    } else {
                        knowledgeFile.setCreatedAt(new Date());
                    }
                }
                if (doc.containsKey("update_time")) {
                    // RAGFlow API返回的时间戳可能是字符串或数字类型
                    Object updateTimeObj = doc.get("update_time");
                    Long updateTime = null;

                    if (updateTimeObj instanceof Number) {
                        updateTime = ((Number) updateTimeObj).longValue();
                    } else if (updateTimeObj instanceof String) {
                        try {
                            updateTime = Long.parseLong((String) updateTimeObj);
                        } catch (NumberFormatException e) {
                            log.warn("无法解析update_time字符串: {}", updateTimeObj);
                        }
                    }

                    if (updateTime != null && updateTime > 0) {
                        knowledgeFile.setUpdatedAt(new Date(updateTime));
                    } else {
                        knowledgeFile.setUpdatedAt(new Date());
                    }
                }

                // 处理文档解析状态字段 run
                if (doc.containsKey("run")) {
                    Object runObj = doc.get("run");
                    if (runObj != null) {
                        knowledgeFile.setRun(runObj.toString());
                        log.debug("设置文档解析状态: documentId={}, run={}", knowledgeFile.getId(), runObj);
                    }
                }

                knowledgeFilesList.add(knowledgeFile);
            }

            // 解析总记录数 - 根据RAGFlow API响应，字段名是"total"
            long total = 0;
            if (dataMap.containsKey("total")) {
                total = ((Number) dataMap.get("total")).longValue();
            }

            log.info("成功解析RAGFlow API响应，获取到{}个文档，总数: {}", knowledgeFilesList.size(), total);
            return new PageData<KnowledgeFilesDTO>(knowledgeFilesList, total);

        } catch (Exception e) {
            log.error("解析RAGFlow API文档列表响应失败: {}", e.getMessage(), e);
            return new PageData<KnowledgeFilesDTO>(new ArrayList<>(), 0);
        }
    }

    private KnowledgeFilesDTO parseUploadResponse(Object dataObj, String datasetId, MultipartFile file) {
        // 解析上传响应的逻辑
        // 这里需要实现从RAGFlow API响应中解析上传结果
        KnowledgeFilesDTO result = new KnowledgeFilesDTO();
        result.setDatasetId(datasetId);
        result.setName(file.getOriginalFilename());
        result.setFileSize(file.getSize());
        result.setStatus(1);
        return result;
    }

    // MultipartFile资源包装类
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