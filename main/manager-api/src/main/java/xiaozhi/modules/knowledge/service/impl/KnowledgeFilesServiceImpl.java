package xiaozhi.modules.knowledge.service.impl;

import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.core.io.AbstractResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;

@Service
@AllArgsConstructor
@Slf4j
public class KnowledgeFilesServiceImpl implements KnowledgeFilesService {

    private final KnowledgeBaseService knowledgeBaseService;
    private RestTemplate restTemplate = new RestTemplate();
    private ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public Map<String, Object> getRAGConfig(String ragModelId) {
        return knowledgeBaseService.getRAGConfig(ragModelId);
    }

    @Override
    public PageData<KnowledgeFilesDTO> getPageList(KnowledgeFilesDTO knowledgeFilesDTO, Integer page, Integer limit) {
        try {

            log.info("=== 开始获取文档列表 ===");
            log.info("查询条件: datasetId={}, name={}, status={}, page={}, limit={}",
                    knowledgeFilesDTO != null ? knowledgeFilesDTO.getDatasetId() : null,
                    knowledgeFilesDTO != null ? knowledgeFilesDTO.getName() : null,
                    knowledgeFilesDTO != null ? knowledgeFilesDTO.getStatus() : null,
                    page, limit);

            // 构建请求URL - 根据RAGFlow API文档，获取文档列表的接口
            String datasetId = knowledgeFilesDTO != null ? knowledgeFilesDTO.getDatasetId() : null;
            if (StringUtils.isBlank(datasetId)) {
                throw new RenException(ErrorCode.PARAMS_GET_ERROR, "datasetId不能为空");
            }

            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents";

            // 添加查询参数
            StringBuilder urlBuilder = new StringBuilder(url);
            List<String> params = new ArrayList<>();

            if (knowledgeFilesDTO != null && StringUtils.isNotBlank(knowledgeFilesDTO.getName())) {
                params.add("keywords=" + knowledgeFilesDTO.getName());
            }
            if (page > 0) {
                params.add("page=" + page);
            }
            if (limit > 0) {
                params.add("page_size=" + limit);
            }

            if (!params.isEmpty()) {
                urlBuilder.append("?").append(String.join("&", params));
            }

            url = urlBuilder.toString();
            log.debug("请求URL: {}", url);

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
                throw new RenException(ErrorCode.RAG_API_ERROR, "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode());
            }

            String responseBody = response.getBody();
            log.debug("RAGFlow API响应内容: {}", responseBody);

            // 解析响应
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Object dataObj = responseMap.get("data");
                return parseDocumentListResponse(dataObj, page, limit);
            } else {
                log.error("RAGFlow API调用失败，响应码: {}", code);
                // 获取错误消息，如果存在的话
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误详情: {}", errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("获取文档列表失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }

            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 获取文档列表操作结束 ===");
        }
    }

    /**
     * 解析RAGFlow API返回的文档列表响应
     */
    private PageData<KnowledgeFilesDTO> parseDocumentListResponse(Object dataObj, long curPage, long pageSize) {
        try {
            List<KnowledgeFilesDTO> documents = new ArrayList<>();
            long totalCount = 0;

            if (dataObj instanceof Map) {
                Map<String, Object> dataMap = (Map<String, Object>) dataObj;

                // 获取文档列表 - 支持多种可能的字段名
                Object documentsObj = null;

                // 支持多种可能的文档列表字段名
                String[] possibleDocumentFields = { "docs", "documents", "items", "list", "data" };

                for (String fieldName : possibleDocumentFields) {
                    if (dataMap.containsKey(fieldName) && dataMap.get(fieldName) instanceof List) {
                        documentsObj = dataMap.get(fieldName);
                        log.debug("使用字段名'{}'获取文档列表", fieldName);
                        break;
                    }
                }

                // 如果标准字段不存在，尝试自动检测
                if (documentsObj == null) {
                    for (Map.Entry<String, Object> entry : dataMap.entrySet()) {
                        if (entry.getValue() instanceof List) {
                            List<?> list = (List<?>) entry.getValue();
                            if (!list.isEmpty() && list.get(0) instanceof Map) {
                                documentsObj = entry.getValue();
                                log.warn("自动检测到文档列表字段: '{}'，建议检查RAGFlow API文档", entry.getKey());
                                break;
                            }
                        }
                    }
                }

                if (documentsObj instanceof List) {
                    List<Map<String, Object>> documentList = (List<Map<String, Object>>) documentsObj;

                    for (Map<String, Object> docMap : documentList) {
                        KnowledgeFilesDTO dto = convertRAGDocumentToDTO(docMap);
                        if (dto != null) {
                            // 在文档列表获取时也进行状态同步检查
                            syncDocumentStatusWithRAGFlow(dto);
                            documents.add(dto);
                        }
                    }
                }

                // 解析总数 - 支持多种可能的字段名
                Object totalObj = null;
                String[] possibleTotalFields = { "total", "totalCount", "total_count", "count" };

                for (String fieldName : possibleTotalFields) {
                    if (dataMap.containsKey(fieldName)) {
                        totalObj = dataMap.get(fieldName);
                        log.debug("使用字段名'{}'获取总数", fieldName);
                        break;
                    }
                }

                if (totalObj instanceof Integer) {
                    totalCount = ((Integer) totalObj).longValue();
                } else if (totalObj instanceof Long) {
                    totalCount = (Long) totalObj;
                } else if (totalObj instanceof String) {
                    try {
                        totalCount = Long.parseLong((String) totalObj);
                    } catch (NumberFormatException e) {
                        log.warn("无法解析总数字段: {}", totalObj);
                    }
                }
            }

            // 创建分页数据
            PageData<KnowledgeFilesDTO> pageData = new PageData<>(documents, totalCount);

            log.info("获取文档列表成功，共{}个文档，总数: {}", documents.size(), totalCount);
            return pageData;

        } catch (Exception e) {
            log.error("获取文档列表响应失败: {}", e.getMessage(), e);
            throw new RenException(ErrorCode.RAG_API_ERROR, "获取文档列表响应失败: " + e.getMessage());
        }
    }

    /**
     * 同步文档状态与RAGFlow实际状态
     * 优化状态同步逻辑，确保解析中状态能够正常显示
     * 只有当文档有切片且解析时间超过30秒时，才更新为完成状态
     */
    private void syncDocumentStatusWithRAGFlow(KnowledgeFilesDTO dto) {
        if (dto == null || StringUtils.isBlank(dto.getDocumentId())) {
            return;
        }

        String documentId = dto.getDocumentId();
        Integer currentStatus = dto.getStatus();

        // 只有当状态明确为处理中(1)时，才进行状态同步检查
        // 避免在状态不确定或已完成的文档上重复检查
        if (currentStatus != null && currentStatus == 1) {
            try {
                long currentTime = System.currentTimeMillis();

                // 调用RAGFlow API获取文档切片信息
                String datasetId = dto.getDatasetId();
                Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
                String baseUrl = (String) ragConfig.get("base_url");
                String apiKey = (String) ragConfig.get("api_key");

                String url = baseUrl + "/api/v1/documents/" + documentId + "/chunks";

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                headers.set("Authorization", "Bearer " + apiKey);

                HttpEntity<String> requestEntity = new HttpEntity<>(headers);

                log.debug("检查文档切片状态，documentId: {}", documentId);
                ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, requestEntity,
                        String.class);

                if (response.getStatusCode().is2xxSuccessful()) {
                    String responseBody = response.getBody();
                    Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);

                    Integer code = (Integer) responseMap.get("code");
                    if (code != null && code == 0) {
                        Object dataObj = responseMap.get("data");
                        if (dataObj instanceof Map) {
                            Map<String, Object> dataMap = (Map<String, Object>) dataObj;

                            // 检查是否有切片数据
                            Object chunksObj = getValueFromMultipleKeys(dataMap, "chunks", "items", "list", "data");
                            if (chunksObj instanceof List) {
                                List<?> chunks = (List<?>) chunksObj;

                                // 如果有切片且数量大于0，说明解析已完成
                                if (!chunks.isEmpty()) {
                                    // 检查文档创建时间，确保解析过程有足够的时间显示
                                    Date createdAt = dto.getCreatedAt();
                                    long parseDuration = currentTime
                                            - (createdAt != null ? createdAt.getTime() : currentTime);

                                    // 只有当解析时间超过30秒时，才更新为完成状态
                                    // 这样可以确保解析中状态有足够的时间显示
                                    if (parseDuration > 30000) {
                                        log.info("状态同步：文档已有切片且解析时间超过30秒，更新为完成状态，documentId: {}, 切片数量: {}, 解析时长: {}ms",
                                                documentId, chunks.size(), parseDuration);

                                        // 更新状态为完成(3)
                                        dto.setStatus(3);
                                    } else {
                                        log.debug("文档已有切片但解析时间不足30秒，保持解析中状态，documentId: {}, 解析时长: {}ms",
                                                documentId, parseDuration);
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (Exception e) {
                log.debug("检查文档切片状态失败，documentId: {}, 错误: {}", documentId, e.getMessage());
                // 忽略检查失败，保持原状态
            }
        }
    }

    /**
     * 将RAGFlow文档数据转换为KnowledgeFilesDTO
     */
    private KnowledgeFilesDTO convertRAGDocumentToDTO(Map<String, Object> docMap) {
        try {
            if (docMap == null)
                return null;

            KnowledgeFilesDTO dto = new KnowledgeFilesDTO();

            // 设置基本字段 - 支持多种可能的字段名
            dto.setId(getStringValueFromMultipleKeys(docMap, "id", "document_id", "doc_id")); // 使用RAGFlow的文档ID作为本地ID
            dto.setDocumentId(getStringValueFromMultipleKeys(docMap, "id", "document_id", "doc_id")); // RAGFlow文档ID
            dto.setName(getStringValueFromMultipleKeys(docMap, "name", "filename", "file_name", "title"));
            dto.setDatasetId(getStringValueFromMultipleKeys(docMap, "dataset_id", "dataset", "knowledge_base_id"));

            // 设置文件信息 - 支持多种可能的字段名
            dto.setFileType(getStringValueFromMultipleKeys(docMap, "file_type", "type", "format", "extension"));

            // 文件大小 - 支持多种可能的字段名
            Object sizeObj = getValueFromMultipleKeys(docMap, "size", "file_size", "size_bytes");
            if (sizeObj instanceof Integer) {
                dto.setFileSize(((Integer) sizeObj).longValue());
            } else if (sizeObj instanceof Long) {
                dto.setFileSize((Long) sizeObj);
            } else if (sizeObj instanceof String) {
                try {
                    dto.setFileSize(Long.parseLong((String) sizeObj));
                } catch (NumberFormatException e) {
                    log.warn("无法解析文件大小: {}", sizeObj);
                }
            }

            // 设置元数据和配置 - 支持多种可能的字段名
            Object metaFieldsObj = getValueFromMultipleKeys(docMap, "meta_fields", "metadata", "meta", "properties");
            if (metaFieldsObj instanceof Map) {
                dto.setMetaFields((Map<String, Object>) metaFieldsObj);
            }

            Object parserConfigObj = getValueFromMultipleKeys(docMap, "parser_config", "parser", "parse_config",
                    "config");
            if (parserConfigObj instanceof Map) {
                dto.setParserConfig((Map<String, Object>) parserConfigObj);
            }

            dto.setChunkMethod(getStringValueFromMultipleKeys(docMap, "chunk_method", "chunking", "chunk_strategy"));

            // 设置时间信息 - 支持多种可能的字段名
            Object createTimeObj = getValueFromMultipleKeys(docMap, "create_time", "created_at", "creation_time",
                    "created");
            if (createTimeObj instanceof Long) {
                dto.setCreatedAt(new Date((Long) createTimeObj));
            } else if (createTimeObj instanceof String) {
                // 尝试解析时间字符串
                try {
                    // 这里可以根据实际的时间格式进行调整
                    dto.setCreatedAt(new Date(Long.parseLong((String) createTimeObj)));
                } catch (NumberFormatException e) {
                    log.warn("无法解析创建时间: {}", createTimeObj);
                }
            }

            Object updateTimeObj = getValueFromMultipleKeys(docMap, "update_time", "updated_at", "modified_time",
                    "modified");
            if (updateTimeObj instanceof Long) {
                dto.setUpdatedAt(new Date((Long) updateTimeObj));
            } else if (updateTimeObj instanceof String) {
                try {
                    dto.setUpdatedAt(new Date(Long.parseLong((String) updateTimeObj)));
                } catch (NumberFormatException e) {
                    log.warn("无法解析更新时间: {}", updateTimeObj);
                }
            }

            // 设置文档解析状态信息 - 直接使用RAGFlow最新状态
            String documentId = dto.getDocumentId();
            if (StringUtils.isNotBlank(documentId)) {
                // 获取RAGFlow的最新状态
                Object runObj = getValueFromMultipleKeys(docMap, "run", "status", "parse_status");
                Integer ragFlowStatus = null;
                if (runObj != null) {
                    dto.setRun(runObj.toString());
                    ragFlowStatus = dto.getParseStatusCode();
                    log.debug("获取RAGFlow最新状态，documentId: {}, run: {}, status: {}",
                            documentId, runObj, ragFlowStatus);
                }

            }

            return dto;

        } catch (Exception e) {
            log.error("转换RAGFlow文档数据失败: {}", e.getMessage(), e);
            return null;
        }
    }

    /**
     * 从多个可能的字段名中获取字符串值
     */
    private String getStringValueFromMultipleKeys(Map<String, Object> map, String... keys) {
        for (String key : keys) {
            Object value = map.get(key);
            if (value != null) {
                return value.toString();
            }
        }
        return null;
    }

    /**
     * 从多个可能的字段名中获取值
     */
    private Object getValueFromMultipleKeys(Map<String, Object> map, String... keys) {
        for (String key : keys) {
            Object value = map.get(key);
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    @Override
    public KnowledgeFilesDTO getByDocumentId(String documentId, String datasetId) {
        if (StringUtils.isBlank(documentId) || StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR, "documentId和datasetId不能为空");
        }

        log.info("=== 开始根据documentId获取文档 ===");
        log.info("documentId: {}, datasetId: {}", documentId, datasetId);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            // 修正API路径 - 根据RAGFlow API规范，获取单个文档需要datasetId
            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents/" + documentId;
            log.debug("请求URL: {}", url);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<String> requestEntity = new HttpEntity<>(headers);

            // 发送GET请求
            log.info("发送GET请求到RAGFlow API获取文档详情...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                String responseBody = response.getBody();
                throw new RenException(ErrorCode.RAG_API_ERROR,
                        "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode() +
                                ", 响应内容: " + (responseBody != null ? responseBody : "无响应内容"));
            }

            String responseBody = response.getBody();
            log.debug("RAGFlow API响应内容: {}", responseBody);

            // 解析响应
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Object dataObj = responseMap.get("data");
                if (dataObj instanceof Map) {
                    KnowledgeFilesDTO dto = convertRAGDocumentToDTO((Map<String, Object>) dataObj);
                    if (dto != null) {
                        log.info("获取文档详情成功，documentId: {}", documentId);
                        return dto;
                    }
                }
                throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
            } else {
                log.error("RAGFlow API调用失败，响应码: {}", code);
                // 获取错误消息，如果存在的话
                String apiMessage = (String) responseMap.get("message");
                String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                log.error("RAGFlow API调用失败详情: {}", errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("根据documentId获取文档失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 根据documentId获取文档操作结束 ===");
        }
    }

    @Override
    public PageData<KnowledgeFilesDTO> getPageListByStatus(String datasetId, Integer status, Integer page,
            Integer limit) {
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR, "datasetId不能为空");
        }

        log.info("=== 开始根据状态查询文档列表 ===");
        log.info("datasetId: {}, status: {}, page: {}, limit: {}", datasetId, status, page, limit);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            // 构建请求URL - 获取文档列表
            StringBuilder urlBuilder = new StringBuilder();
            urlBuilder.append(baseUrl).append("/api/v1/datasets/").append(datasetId).append("/documents");

            // 构建查询参数
            List<String> params = new ArrayList<>();
            if (page != null && page > 0) {
                params.add("page=" + page);
            }
            if (limit != null && limit > 0) {
                params.add("page_size=" + limit);
            }

            if (!params.isEmpty()) {
                urlBuilder.append("?").append(String.join("&", params));
            }

            String url = urlBuilder.toString();
            log.debug("请求URL: {}", url);

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
                throw new RenException(ErrorCode.RAG_API_ERROR, "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode());
            }

            String responseBody = response.getBody();
            log.debug("RAGFlow API响应内容: {}", responseBody);

            // 解析响应
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Object dataObj = responseMap.get("data");

                // 解析文档列表并过滤状态
                PageData<KnowledgeFilesDTO> pageData = parseDocumentListResponse(dataObj, page, limit);

                if (status != null) {
                    // 根据状态过滤文档列表
                    List<KnowledgeFilesDTO> filteredDocuments = pageData.getList().stream()
                            .filter(doc -> status.equals(doc.getStatus()))
                            .collect(Collectors.toList());

                    // 更新分页数据
                    pageData.setList(filteredDocuments);
                    pageData.setTotal(filteredDocuments.size());
                }

                log.info("根据状态查询文档列表成功，datasetId: {}, 状态: {}, 文档数量: {}",
                        datasetId, status, pageData.getList().size());
                return pageData;
            } else {
                log.error("RAGFlow API调用失败，响应码: {}", code);
                throw new RenException(ErrorCode.RAG_API_ERROR, "RAGFlow API调用失败，响应码: " + code);
            }

        } catch (Exception e) {
            log.error("根据状态查询文档列表失败: {}", e.getMessage(), e);
            throw new RenException(ErrorCode.RAG_API_ERROR, "查询文档列表失败: " + e.getMessage());
        } finally {
            log.info("=== 根据状态查询文档列表操作结束 ===");
        }
    }

    @Override
    public KnowledgeFilesDTO uploadDocument(String datasetId, MultipartFile file, String name,
            Map<String, Object> metaFields, String chunkMethod,
            Map<String, Object> parserConfig) {
        if (StringUtils.isBlank(datasetId) || file == null || file.isEmpty()) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        log.info("=== 开始文档上传操作 ===");
        log.info("上传文档到数据集: {}, 文件名: {}", datasetId, file.getOriginalFilename());

        try {
            // 在文件上传前添加详细日志
            log.info("1. 开始处理文件信息");
            String fileName = file.getOriginalFilename();
            String fileType = getFileType(fileName);
            long fileSize = file.getSize();

            log.info("文件信息 - 文件名: {}, 文件类型: {}, 文件大小: {} bytes",
                    fileName, fileType, fileSize);

            // 检查文件基本信息
            if (StringUtils.isBlank(fileName)) {
                log.error("文件名为空");
                throw new RenException(ErrorCode.PARAMS_GET_ERROR, "文件名不能为空");
            }

            if (fileSize == 0) {
                log.error("文件大小为0");
                throw new RenException(ErrorCode.PARAMS_GET_ERROR, "文件内容为空");
            }

            log.info("2. 开始流式上传到RAGFlow");
            // 直接调用RAGFlow API上传文档 - 使用流式上传
            String documentId = uploadDocumentToRAGFlow(datasetId, file, name, metaFields, chunkMethod, parserConfig);

            log.info("文档上传成功，documentId: {}", documentId);

            // 返回上传的文档信息
            KnowledgeFilesDTO result = new KnowledgeFilesDTO();
            result.setId(documentId); // 使用documentId作为ID
            result.setDocumentId(documentId);
            result.setDatasetId(datasetId);
            result.setName(StringUtils.isNotBlank(name) ? name : fileName);
            result.setFileType(fileType);
            result.setFileSize(fileSize);
            result.setStatus(1); // 上传成功，设置为处理中状态

            return result;

        } catch (Exception e) {
            log.error("文档上传失败: {}", e.getMessage());
            log.error("文档上传失败详细异常: ", e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.INTERNAL_SERVER_ERROR);
        } finally {
            log.info("=== 文档上传操作结束 ===");
        }
    }

    @Override
    public void deleteByDocumentId(String documentId, String datasetId) {
        if (StringUtils.isBlank(documentId) || StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR, "documentId和datasetId不能为空");
        }

        log.info("=== 开始根据documentId删除文档 ===");
        log.info("删除文档documentId: {}, datasetId: {}", documentId, datasetId);

        try {
            // 直接调用RAGFlow API删除文档，不进行前置验证
            // 因为即使文档不存在，RAGFlow API也会返回相应的错误信息
            log.info("开始调用RAGFlow API删除文档");
            deleteDocumentInRAGFlow(documentId, datasetId);
            log.info("RAGFlow API删除调用完成");

        } catch (Exception e) {
            log.error("删除文档失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 根据documentId删除文档操作结束 ===");
        }
    }

    /**
     * 获取文件类型 - 支持RAGFlow四种文档格式类型
     */
    private String getFileType(String fileName) {
        if (StringUtils.isBlank(fileName)) {
            log.warn("文件名为空，返回unknown类型");
            return "unknown";
        }

        try {
            int lastDotIndex = fileName.lastIndexOf('.');
            if (lastDotIndex > 0 && lastDotIndex < fileName.length() - 1) {
                String extension = fileName.substring(lastDotIndex + 1).toLowerCase();

                // 文档格式类型
                String[] documentTypes = { "pdf", "doc", "docx", "txt", "md", "mdx" };
                String[] spreadsheetTypes = { "csv", "xls", "xlsx" };
                String[] presentationTypes = { "ppt", "pptx" };

                // 检查文档类型
                for (String type : documentTypes) {
                    if (type.equals(extension)) {
                        return "document";
                    }
                }

                // 检查表格类型
                for (String type : spreadsheetTypes) {
                    if (type.equals(extension)) {
                        return "spreadsheet";
                    }
                }
                // 检查幻灯片类型
                for (String type : presentationTypes) {
                    if (type.equals(extension)) {
                        return "presentation";
                    }
                }
                // 返回原始扩展名作为文件类型
                return extension;
            }
            return "unknown";
        } catch (Exception e) {
            log.error("获取文件类型失败: ", e);
            return "unknown";
        }
    }

    /**
     * 验证RAG配置中是否包含必要的参数
     */
    private void validateRagConfig(Map<String, Object> config) {
        if (config == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        // 从配置中提取必要的参数
        String baseUrl = (String) config.get("base_url");
        String apiKey = (String) config.get("api_key");

        // 验证base_url是否存在且非空
        if (StringUtils.isBlank(baseUrl)) {
            throw new RenException(ErrorCode.RAG_API_ERROR, "RAG配置缺少必要参数: base_url");
        }
    }

    /**
     * 调用RAGFlow API上传文档 - 流式上传版本
     */
    private String uploadDocumentToRAGFlow(String datasetId, MultipartFile file, String name,
            Map<String, Object> metaFields, String chunkMethod,
            Map<String, Object> parserConfig) {
        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            log.info("开始调用RAGFlow API流式上传文档，datasetId: {}, 文件名: {}", datasetId, file.getOriginalFilename());
            log.debug("RAGFlow配置 - baseUrl: {}, apiKey: {}", baseUrl, StringUtils.isBlank(apiKey) ? "未配置" : "已配置");

            // 构建请求URL
            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents";
            log.debug("请求URL: {}", url);

            // 构建multipart/form-data请求
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            headers.set("Authorization", "Bearer " + apiKey);

            // 创建多部分请求体 - 使用MultipartFileResource进行流式上传
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartFileResource(file, file.getOriginalFilename()));

            // 添加其他参数
            if (StringUtils.isNotBlank(name)) {
                body.add("name", name);
            } else {
                body.add("name", file.getOriginalFilename());
            }

            if (metaFields != null && !metaFields.isEmpty()) {
                try {
                    body.add("meta_fields", objectMapper.writeValueAsString(metaFields));
                } catch (Exception e) {
                    log.warn("序列化meta_fields失败: {}", e.getMessage());
                }
            }

            if (StringUtils.isNotBlank(chunkMethod)) {
                body.add("chunk_method", chunkMethod);
            }

            if (parserConfig != null && !parserConfig.isEmpty()) {
                try {
                    body.add("parser_config", objectMapper.writeValueAsString(parserConfig));
                } catch (Exception e) {
                    log.warn("序列化parser_config失败: {}", e.getMessage());
                }
            }

            log.debug("multipart请求体参数数量: {}", body.size());
            log.debug("multipart请求体参数: {}", body.keySet());

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

            // 发送POST请求
            log.info("发送multipart/form-data POST请求到RAGFlow API...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());
            log.debug("RAGFlow API响应内容: {}", response.getBody());

            String responseBody = response.getBody();
            String documentId = null;

            if (response.getStatusCode().is2xxSuccessful()) {
                try {
                    Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);

                    log.debug("RAGFlow API响应解析结果: {}", responseMap);

                    // 首先检查响应码
                    Integer code = (Integer) responseMap.get("code");
                    if (code != null && code == 0) {
                        // 响应码为0表示成功，从data字段中获取documentId
                        Object dataObj = responseMap.get("data");

                        // 增强的documentId提取逻辑
                        documentId = extractDocumentIdFromResponse(dataObj);

                        // 如果从data字段无法提取，尝试从根级别提取
                        if (StringUtils.isBlank(documentId)) {
                            documentId = extractDocumentIdFromRoot(responseMap);
                        }

                        log.info("文档上传成功，documentId: {}", documentId);
                    } else {
                        // 如果响应码不为0，说明API调用失败
                        log.error("RAGFlow API调用失败，响应码: {}", code);
                        // 获取错误消息，如果存在的话
                        String apiMessage = (String) responseMap.get("message");
                        String errorDetail = apiMessage != null ? apiMessage : "无详细错误信息";
                        log.error("RAGFlow API调用失败详情: {}", errorDetail);
                        throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
                    }

                    log.info("从RAGFlow API响应中解析出documentId: {}", documentId);
                    log.debug("完整响应内容: {}", responseBody);
                } catch (Exception e) {
                    log.error("解析RAGFlow API响应失败: {}", e.getMessage());
                    throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
                }
            } else {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR,
                        "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode() +
                                ", 响应内容: " + (responseBody != null ? responseBody : "无响应内容"));
            }

            if (StringUtils.isBlank(documentId)) {
                log.error("无法从RAGFlow API响应中获取documentId");
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }
            log.info("RAGFlow文档上传成功，documentId: {}，文档已开始自动解析切片", documentId);
            return documentId;

        } catch (Exception e) {
            log.error("RAGFlow API调用失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        }
    }

    /**
     * 从响应数据中提取documentId
     */
    private String extractDocumentIdFromResponse(Object dataObj) {
        String documentId = null;

        if (dataObj instanceof List) {
            // data是一个数组，取第一个元素的id字段
            List<Map<String, Object>> dataList = (List<Map<String, Object>>) dataObj;
            if (!dataList.isEmpty()) {
                Map<String, Object> firstItem = dataList.get(0);
                documentId = extractDocumentIdFromMap(firstItem);
            }
        } else if (dataObj instanceof Map) {
            // data是一个对象
            Map<String, Object> dataMap = (Map<String, Object>) dataObj;
            documentId = extractDocumentIdFromMap(dataMap);
        }

        return documentId;
    }

    /**
     * 从Map中提取documentId，支持多种可能的字段名
     */
    private String extractDocumentIdFromMap(Map<String, Object> map) {
        if (map == null)
            return null;

        // 尝试多种可能的字段名
        String[] possibleFieldNames = { "id", "document_id", "documentId", "doc_id", "documentId" };

        for (String fieldName : possibleFieldNames) {
            Object value = map.get(fieldName);
            if (value != null && value instanceof String && StringUtils.isNotBlank((String) value)) {
                return (String) value;
            }
        }

        return null;
    }

    /**
     * 从根级别响应中提取documentId
     */
    private String extractDocumentIdFromRoot(Map<String, Object> responseMap) {
        if (responseMap == null)
            return null;

        // 尝试从根级别提取
        String[] possibleFieldNames = { "id", "document_id", "documentId", "doc_id", "documentId" };

        for (String fieldName : possibleFieldNames) {
            Object value = responseMap.get(fieldName);
            if (value != null && value instanceof String && StringUtils.isNotBlank((String) value)) {
                return (String) value;
            }
        }

        return null;
    }

    /**
     * 调用RAGFlow API删除文档
     */
    private void deleteDocumentInRAGFlow(String documentId, String datasetId) {
        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            log.info("开始调用RAGFlow API删除文档，documentId: {}, datasetId: {}", documentId, datasetId);
            log.debug("RAGFlow配置 - baseUrl: {}, apiKey: {}", baseUrl, StringUtils.isBlank(apiKey) ? "未配置" : "已配置");

            // 构建请求URL - 根据RAGFlow API文档，使用正确的路径参数名称
            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/documents";
            log.debug("请求URL: {}", url);

            // 构建请求体 - 严格按照API文档格式
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("ids", Arrays.asList(documentId)); // 使用Arrays.asList确保序列化正确
            log.debug("请求体: {}", requestBody);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送DELETE请求
            log.info("发送DELETE请求到RAGFlow API...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.DELETE, requestEntity,
                    String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());
            log.debug("RAGFlow API响应内容: {}", response.getBody());

            String responseBody = response.getBody();

            if (response.getStatusCode().is2xxSuccessful()) {
                // 验证响应格式
                if (responseBody != null) {
                    try {
                        Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
                        Integer code = (Integer) responseMap.get("code");

                        if (code != null && code == 0) {
                            log.info("RAGFlow文档删除成功，documentId: {}", documentId);
                            return;
                        } else {
                            String message = (String) responseMap.get("message");
                            log.error("RAGFlow API调用失败，响应码: {}", code);
                            String errorDetail = message != null ? message : "无详细错误信息";
                            throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
                        }
                    } catch (Exception e) {
                        log.warn("解析RAGFlow响应失败，但HTTP状态码成功，视为删除成功: {}", e.getMessage());
                        log.info("RAGFlow文档删除成功，documentId: {}", documentId);
                        return;
                    }
                } else {
                    log.info("RAGFlow文档删除成功（无响应体），documentId: {}", documentId);
                    return;
                }
            } else {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR,
                        "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode() +
                                ", 响应内容: " + (responseBody != null ? responseBody : "无响应内容"));
            }

        } catch (Exception e) {
            log.error("RAGFlow API调用失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        }
    }

    /**
     * 辅助类：将MultipartFile转换为Resource用于流式上传
     */
    private static class MultipartFileResource extends AbstractResource {
        private final MultipartFile multipartFile;
        private final String filename;

        public MultipartFileResource(MultipartFile multipartFile, String filename) {
            this.multipartFile = multipartFile;
            this.filename = filename;
        }

        @Override
        public String getFilename() {
            return this.filename;
        }

        @Override
        public InputStream getInputStream() throws IOException {
            return this.multipartFile.getInputStream();
        }

        @Override
        public long contentLength() throws IOException {
            return this.multipartFile.getSize();
        }

        @Override
        public boolean exists() {
            return true;
        }

        @Override
        public String getDescription() {
            return "MultipartFile resource for " + this.filename;
        }
    }

    @Override
    public boolean parseDocuments(String datasetId, List<String> documentIds) {
        if (StringUtils.isBlank(datasetId) || documentIds == null || documentIds.isEmpty()) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR, "datasetId和documentIds不能为空");
        }

        log.info("=== 开始解析文档（切块） ===");
        log.info("datasetId: {}, documentIds: {}", datasetId, documentIds);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            // 构建请求URL - 根据RAGFlow API文档，解析文档的接口
            String url = baseUrl + "/api/v1/datasets/" + datasetId + "/chunks";
            log.debug("请求URL: {}", url);

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("document_ids", documentIds);
            log.debug("请求体: {}", requestBody);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送POST请求
            log.info("发送POST请求到RAGFlow API解析文档...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            String responseBody = response.getBody();
            log.debug("RAGFlow API响应内容: {}", responseBody);

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                String errorDetail = responseBody != null ? responseBody : "无响应内容";
                throw new RenException(ErrorCode.RAG_API_ERROR,
                        "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode() + ", 响应内容: " + errorDetail);
            }

            // 解析响应
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                log.info("文档解析成功，datasetId: {}, documentIds: {}", datasetId, documentIds);
                return true;
            } else {
                // 获取错误消息，如果存在的话
                String message = (String) responseMap.get("message");
                String errorDetail = message != null ? message : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误信息: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("解析文档失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 解析文档操作结束 ===");
        }
    }

    @Override
    public Map<String, Object> listChunks(String datasetId, String documentId, String keywords,
            Integer page, Integer pageSize, String chunkId) {
        if (StringUtils.isBlank(datasetId) || StringUtils.isBlank(documentId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR, "datasetId和documentId不能为空");
        }

        log.info("=== 开始列出切片 ===");
        log.info("datasetId: {}, documentId: {}, keywords: {}, page: {}, pageSize: {}, chunkId: {}",
                datasetId, documentId, keywords, page, pageSize, chunkId);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            // 构建请求URL - 根据RAGFlow API文档，列出切片的接口
            StringBuilder urlBuilder = new StringBuilder();
            urlBuilder.append(baseUrl).append("/api/v1/datasets/").append(datasetId)
                    .append("/documents/").append(documentId).append("/chunks");

            // 添加查询参数
            List<String> params = new ArrayList<>();

            if (StringUtils.isNotBlank(keywords)) {
                params.add("keywords=" + keywords);
            }

            if (page != null && page > 0) {
                params.add("page=" + page);
            }

            if (pageSize != null && pageSize > 0) {
                params.add("page_size=" + pageSize);
            }

            if (StringUtils.isNotBlank(chunkId)) {
                params.add("id=" + chunkId);
            }

            if (!params.isEmpty()) {
                urlBuilder.append("?").append(String.join("&", params));
            }

            String url = urlBuilder.toString();
            log.debug("请求URL: {}", url);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<String> requestEntity = new HttpEntity<>(headers);

            // 发送GET请求
            log.info("发送GET请求到RAGFlow API列出切片...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            String responseBody = response.getBody();
            log.debug("RAGFlow API响应内容: {}", responseBody);

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                String errorDetail = responseBody != null ? responseBody : "无响应内容";
                throw new RenException(ErrorCode.RAG_API_ERROR,
                        "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode() + ", 响应内容: " + errorDetail);
            }

            // 解析响应
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                log.info("切片列表获取成功，datasetId: {}, documentId: {}", datasetId, documentId);

                // 解析切片数据并格式化返回
                return parseChunkListResponse(responseMap);
            } else {
                // 获取错误消息，如果存在的话
                String message = (String) responseMap.get("message");
                String errorDetail = message != null ? message : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误信息: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (IOException e) {
            log.error("解析RAGFlow API响应失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } catch (Exception e) {
            log.error("列出切片失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 列出切片操作结束 ===");
        }
    }

    /**
     * 解析RAGFlow API返回的切片列表响应
     */
    private Map<String, Object> parseChunkListResponse(Map<String, Object> responseMap) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> chunkList = new ArrayList<>();
        long totalCount = 0;

        try {
            // 首先检查是否有data字段
            Object dataObj = responseMap.get("data");
            if (dataObj instanceof Map) {
                Map<String, Object> dataMap = (Map<String, Object>) dataObj;

                // 解析切片列表 - 支持多种可能的字段名
                Object chunksObj = null;

                // 支持多种可能的切片列表字段名
                String[] possibleChunkFields = { "chunks", "items", "list", "data", "docs" };

                for (String fieldName : possibleChunkFields) {
                    if (dataMap.containsKey(fieldName) && dataMap.get(fieldName) instanceof List) {
                        chunksObj = dataMap.get(fieldName);
                        log.debug("使用字段名'{}'获取切片列表", fieldName);
                        break;
                    }
                }

                // 如果标准字段不存在，尝试自动检测
                if (chunksObj == null) {
                    for (Map.Entry<String, Object> entry : dataMap.entrySet()) {
                        if (entry.getValue() instanceof List) {
                            List<?> list = (List<?>) entry.getValue();
                            if (!list.isEmpty() && list.get(0) instanceof Map) {
                                chunksObj = entry.getValue();
                                log.warn("自动检测到切片列表字段: '{}'，建议检查RAGFlow API文档", entry.getKey());
                                break;
                            }
                        }
                    }
                }

                if (chunksObj instanceof List) {
                    List<Map<String, Object>> rawChunkList = (List<Map<String, Object>>) chunksObj;

                    for (Map<String, Object> chunkMap : rawChunkList) {
                        Map<String, Object> formattedChunk = formatChunkData(chunkMap);
                        if (formattedChunk != null) {
                            chunkList.add(formattedChunk);
                        }
                    }
                }

                // 解析总数 - 支持多种可能的字段名
                Object totalObj = null;
                String[] possibleTotalFields = { "total", "totalCount", "total_count", "count" };

                for (String fieldName : possibleTotalFields) {
                    if (dataMap.containsKey(fieldName)) {
                        totalObj = dataMap.get(fieldName);
                        log.debug("使用字段名'{}'获取总数", fieldName);
                        break;
                    }
                }

                if (totalObj instanceof Integer) {
                    totalCount = ((Integer) totalObj).longValue();
                } else if (totalObj instanceof Long) {
                    totalCount = (Long) totalObj;
                } else if (totalObj instanceof String) {
                    try {
                        totalCount = Long.parseLong((String) totalObj);
                    } catch (NumberFormatException e) {
                        log.warn("无法解析总数字段: {}", totalObj);
                    }
                }

                // 如果没有找到总数，使用切片列表的大小
                if (totalCount == 0 && !chunkList.isEmpty()) {
                    totalCount = chunkList.size();
                }
            } else {
                log.warn("RAGFlow API响应缺少data字段，尝试直接解析响应");

                // 如果没有data字段，尝试直接解析响应
                Object chunksObj = null;
                String[] possibleChunkFields = { "chunks", "items", "list", "data", "docs" };

                for (String fieldName : possibleChunkFields) {
                    if (responseMap.containsKey(fieldName) && responseMap.get(fieldName) instanceof List) {
                        chunksObj = responseMap.get(fieldName);
                        log.debug("使用字段名'{}'获取切片列表", fieldName);
                        break;
                    }
                }

                if (chunksObj instanceof List) {
                    List<Map<String, Object>> rawChunkList = (List<Map<String, Object>>) chunksObj;

                    for (Map<String, Object> chunkMap : rawChunkList) {
                        Map<String, Object> formattedChunk = formatChunkData(chunkMap);
                        if (formattedChunk != null) {
                            chunkList.add(formattedChunk);
                        }
                    }
                }

                // 解析总数
                Object totalObj = responseMap.get("total");
                if (totalObj instanceof Integer) {
                    totalCount = ((Integer) totalObj).longValue();
                } else if (totalObj instanceof Long) {
                    totalCount = (Long) totalObj;
                }

                if (totalCount == 0 && !chunkList.isEmpty()) {
                    totalCount = chunkList.size();
                }
            }

        } catch (Exception e) {
            log.error("解析切片列表响应失败: {}", e.getMessage(), e);
        }

        result.put("list", chunkList);
        result.put("total", totalCount);

        log.debug("解析后的切片列表: {} 条记录", chunkList.size());
        return result;
    }

    /**
     * 格式化切片数据
     */
    private Map<String, Object> formatChunkData(Map<String, Object> chunkMap) {
        if (chunkMap == null || chunkMap.isEmpty()) {
            return null;
        }

        Map<String, Object> formattedChunk = new HashMap<>();

        try {
            // 提取切片ID - 支持多种可能的字段名
            String chunkId = extractChunkId(chunkMap);
            if (StringUtils.isBlank(chunkId)) {
                log.warn("切片数据缺少ID字段，跳过处理: {}", chunkMap);
                return null;
            }
            formattedChunk.put("id", chunkId);

            // 提取切片内容 - 支持多种可能的字段名
            String content = extractChunkContent(chunkMap);
            formattedChunk.put("content", content != null ? content : "");

            // 提取重要关键词 - 支持多种可能的字段名
            List<String> importantKeywords = extractImportantKeywords(chunkMap);
            formattedChunk.put("important_keywords", importantKeywords);

            // 提取问题列表 - 支持多种可能的字段名
            List<String> questions = extractQuestions(chunkMap);
            formattedChunk.put("questions", questions);

            // 提取创建时间 - 支持多种可能的字段名
            String createTime = extractCreateTime(chunkMap);
            formattedChunk.put("create_time", createTime != null ? createTime : "");

        } catch (Exception e) {
            log.error("格式化切片数据失败: {}", e.getMessage(), e);
            return null;
        }

        return formattedChunk;
    }

    /**
     * 提取切片ID
     */
    private String extractChunkId(Map<String, Object> chunkMap) {
        String[] possibleIdFields = { "id", "chunk_id", "chunkId", "chunkId" };

        for (String fieldName : possibleIdFields) {
            Object value = chunkMap.get(fieldName);
            if (value != null && value instanceof String && StringUtils.isNotBlank((String) value)) {
                return (String) value;
            }
        }

        return null;
    }

    /**
     * 提取切片内容
     */
    private String extractChunkContent(Map<String, Object> chunkMap) {
        String[] possibleContentFields = { "content", "text", "chunk_content", "chunkContent" };

        for (String fieldName : possibleContentFields) {
            Object value = chunkMap.get(fieldName);
            if (value != null && value instanceof String && StringUtils.isNotBlank((String) value)) {
                return (String) value;
            }
        }

        return null;
    }

    /**
     * 提取重要关键词
     */
    private List<String> extractImportantKeywords(Map<String, Object> chunkMap) {
        String[] possibleKeywordFields = { "important_keywords", "keywords", "importantKeywords", "key_words" };

        for (String fieldName : possibleKeywordFields) {
            Object value = chunkMap.get(fieldName);
            if (value instanceof List) {
                List<?> list = (List<?>) value;
                List<String> keywords = new ArrayList<>();
                for (Object item : list) {
                    if (item instanceof String && StringUtils.isNotBlank((String) item)) {
                        keywords.add((String) item);
                    }
                }
                return keywords;
            } else if (value instanceof String && StringUtils.isNotBlank((String) value)) {
                // 如果是逗号分隔的字符串，分割成列表
                String[] parts = ((String) value).split(",");
                List<String> keywords = new ArrayList<>();
                for (String part : parts) {
                    String trimmed = part.trim();
                    if (StringUtils.isNotBlank(trimmed)) {
                        keywords.add(trimmed);
                    }
                }
                return keywords;
            }
        }

        return new ArrayList<>();
    }

    /**
     * 提取问题列表
     */
    private List<String> extractQuestions(Map<String, Object> chunkMap) {
        String[] possibleQuestionFields = { "questions", "question_list", "questionList", "qas" };

        for (String fieldName : possibleQuestionFields) {
            Object value = chunkMap.get(fieldName);
            if (value instanceof List) {
                List<?> list = (List<?>) value;
                List<String> questions = new ArrayList<>();
                for (Object item : list) {
                    if (item instanceof String && StringUtils.isNotBlank((String) item)) {
                        questions.add((String) item);
                    }
                }
                return questions;
            } else if (value instanceof String && StringUtils.isNotBlank((String) value)) {
                // 如果是逗号分隔的字符串，分割成列表
                String[] parts = ((String) value).split(",");
                List<String> questions = new ArrayList<>();
                for (String part : parts) {
                    String trimmed = part.trim();
                    if (StringUtils.isNotBlank(trimmed)) {
                        questions.add(trimmed);
                    }
                }
                return questions;
            }
        }

        return new ArrayList<>();
    }

    /**
     * 提取创建时间
     */
    private String extractCreateTime(Map<String, Object> chunkMap) {
        String[] possibleTimeFields = { "create_time", "created_at", "createTime", "timestamp" };

        for (String fieldName : possibleTimeFields) {
            Object value = chunkMap.get(fieldName);
            if (value != null) {
                if (value instanceof String && StringUtils.isNotBlank((String) value)) {
                    return (String) value;
                } else if (value instanceof Long) {
                    // 如果是时间戳，转换为字符串
                    return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date((Long) value));
                }
            }
        }

        return null;
    }

    @Override
    public Map<String, Object> retrievalTest(String question, List<String> datasetIds, List<String> documentIds,
            Integer page, Integer pageSize, Float similarityThreshold,
            Float vectorSimilarityWeight, Integer topK, String rerankId,
            Boolean keyword, Boolean highlight, List<String> crossLanguages,
            Map<String, Object> metadataCondition) {

        log.info("=== 开始召回测试 ===");
        log.info("问题: {}, 数据集ID: {}, 文档ID: {}, 页码: {}, 每页数量: {}",
                question, datasetIds, documentIds, page, pageSize);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetIds.get(0));
            String baseUrl = (String) ragConfig.get("base_url");
            String apiKey = (String) ragConfig.get("api_key");

            // 构建请求URL
            String url = baseUrl + "/api/v1/retrieval";
            log.debug("请求URL: {}", url);

            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("question", question);

            if (datasetIds != null && !datasetIds.isEmpty()) {
                requestBody.put("dataset_ids", datasetIds);
            }

            if (documentIds != null && !documentIds.isEmpty()) {
                requestBody.put("document_ids", documentIds);
            }

            if (page != null && page > 0) {
                requestBody.put("page", page);
            }

            if (pageSize != null && pageSize > 0) {
                requestBody.put("page_size", pageSize);
            }

            if (similarityThreshold != null) {
                requestBody.put("similarity_threshold", similarityThreshold);
            }

            if (vectorSimilarityWeight != null) {
                requestBody.put("vector_similarity_weight", vectorSimilarityWeight);
            }

            if (topK != null && topK > 0) {
                requestBody.put("top_k", topK);
            }

            if (rerankId != null) {
                requestBody.put("rerank_id", rerankId);
            }

            if (keyword != null) {
                requestBody.put("keyword", keyword);
            }

            if (highlight != null) {
                requestBody.put("highlight", highlight);
            }

            if (crossLanguages != null && !crossLanguages.isEmpty()) {
                requestBody.put("cross_languages", crossLanguages);
            }

            if (metadataCondition != null) {
                requestBody.put("metadata_condition", metadataCondition);
            }

            log.debug("请求体: {}", requestBody);

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<Map<String, Object>> requestEntity = new HttpEntity<>(requestBody, headers);

            // 发送POST请求
            log.info("发送POST请求到RAGFlow API进行召回测试...");
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            log.info("RAGFlow API响应状态码: {}", response.getStatusCode());

            String responseBody = response.getBody();
            log.debug("RAGFlow API响应内容: {}", responseBody);

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API调用失败，状态码: {}", response.getStatusCode());
                String errorDetail = responseBody != null ? responseBody : "无响应内容";
                throw new RenException(ErrorCode.RAG_API_ERROR,
                        "RAGFlow API调用失败，HTTP状态码: " + response.getStatusCode() + ", 响应内容: " + errorDetail);
            }

            // 解析响应
            Map<String, Object> responseMap = objectMapper.readValue(responseBody, Map.class);
            Integer code = (Integer) responseMap.get("code");

            if (code != null && code == 0) {
                Object dataObj = responseMap.get("data");
                if (dataObj instanceof Map) {
                    Map<String, Object> result = (Map<String, Object>) dataObj;
                    log.info("召回测试成功，返回 {} 条切片", result.get("total"));
                    return result;
                } else {
                    log.error("RAGFlow API响应格式错误，data字段不是Map类型");
                    throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
                }
            } else {
                // 获取错误消息，如果存在的话
                String message = (String) responseMap.get("message");
                String errorDetail = message != null ? message : "无详细错误信息";
                log.error("RAGFlow API调用失败，响应码: {}, 错误信息: {}", code, errorDetail);
                throw new RenException(ErrorCode.RAG_API_ERROR, responseBody);
            }

        } catch (Exception e) {
            log.error("召回测试失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "未知错误";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 召回测试操作结束 ===");
        }
    }
}