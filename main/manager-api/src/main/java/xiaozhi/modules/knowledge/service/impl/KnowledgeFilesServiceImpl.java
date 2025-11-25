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
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;
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

            // 获取数据集ID
            String datasetId = knowledgeFilesDTO != null ? knowledgeFilesDTO.getDatasetId() : null;
            if (StringUtils.isBlank(datasetId)) {
                throw new RenException(ErrorCode.RAG_DATASET_ID_NOT_NULL);
            }

            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建查询参数
            Map<String, Object> queryParams = new HashMap<>();
            if (knowledgeFilesDTO != null && StringUtils.isNotBlank(knowledgeFilesDTO.getName())) {
                queryParams.put("keywords", knowledgeFilesDTO.getName());
            }
            if (page > 0) {
                queryParams.put("page", page);
            }
            if (limit > 0) {
                queryParams.put("page_size", limit);
            }

            // 调用适配器获取文档列表
            PageData<KnowledgeFilesDTO> result = adapter.getDocumentList(datasetId, queryParams, page, limit);

            log.info("获取文档列表成功，共{}个文档，总数: {}", result.getList().size(), result.getTotal());
            return result;

        } catch (Exception e) {
            log.error("获取文档列表失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== 获取文档列表操作结束 ===");
        }
    }

    /**
     * 解析RAG API返回的文档列表响应
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
                                log.warn("自动检测到文档列表字段: '{}'，建议检查RAG API文档", entry.getKey());
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
                            syncDocumentStatusWithRAG(dto);
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
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        }
    }

    /**
     * 同步文档状态与RAG实际状态
     * 优化状态同步逻辑，确保解析中状态能够正常显示
     * 只有当文档有切片且解析时间超过30秒时，才更新为完成状态
     */
    private void syncDocumentStatusWithRAG(KnowledgeFilesDTO dto) {
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

                // 使用适配器获取文档切片信息
                String datasetId = dto.getDatasetId();
                Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

                // 提取适配器类型
                String adapterType = extractAdapterType(ragConfig);

                // 使用适配器工厂获取适配器实例
                KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

                // 构建查询参数
                Map<String, Object> queryParams = new HashMap<>();
                queryParams.put("document_id", documentId);

                log.debug("检查文档切片状态，documentId: {}", documentId);

                // 使用适配器获取切片列表
                Map<String, Object> chunkResult = adapter.listChunks(datasetId, documentId, null, null, null, null);
                List<Map<String, Object>> chunks = (List<Map<String, Object>>) chunkResult.get("chunks");

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
            } catch (Exception e) {
                log.debug("检查文档切片状态失败，documentId: {}, 错误: {}", documentId, e.getMessage());
                // 忽略检查失败，保持原状态
            }
        }
    }

    /**
     * 将RAG文档数据转换为KnowledgeFilesDTO
     */
    private KnowledgeFilesDTO convertRAGDocumentToDTO(Map<String, Object> docMap) {
        try {
            if (docMap == null)
                return null;

            KnowledgeFilesDTO dto = new KnowledgeFilesDTO();

            // 设置基本字段 - 支持多种可能的字段名
            dto.setId(getStringValueFromMultipleKeys(docMap, "id", "document_id", "doc_id")); // 使用RAG的文档ID作为本地ID
            dto.setDocumentId(getStringValueFromMultipleKeys(docMap, "id", "document_id", "doc_id")); // RAG文档ID
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

            // 设置文档解析状态信息 - 直接使用RAG最新状态
            String documentId = dto.getDocumentId();
            if (StringUtils.isNotBlank(documentId)) {
                // 获取RAG的最新状态
                Object runObj = getValueFromMultipleKeys(docMap, "run", "status", "parse_status");
                Integer ragFlowStatus = null;
                if (runObj != null) {
                    dto.setRun(runObj.toString());
                    ragFlowStatus = dto.getParseStatusCode();
                    log.debug("获取RAG最新状态，documentId: {}, run: {}, status: {}",
                            documentId, runObj, ragFlowStatus);
                }

            }

            return dto;

        } catch (Exception e) {
            log.error("转换RAG文档数据失败: {}", e.getMessage(), e);
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
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        log.info("=== 开始根据documentId获取文档 ===");
        log.info("documentId: {}, datasetId: {}", documentId, datasetId);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 使用适配器获取文档详情
            KnowledgeFilesDTO dto = adapter.getDocumentById(datasetId, documentId);

            if (dto != null) {
                log.info("获取文档详情成功，documentId: {}", documentId);
                return dto;
            } else {
                throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
            }

        } catch (Exception e) {
            log.error("根据documentId获取文档失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "null";
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
            throw new RenException(ErrorCode.RAG_DATASET_ID_NOT_NULL);
        }

        log.info("=== 开始根据状态查询文档列表 ===");
        log.info("datasetId: {}, status: {}, page: {}, limit: {}", datasetId, status, page, limit);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建查询参数
            Map<String, Object> queryParams = new HashMap<>();
            if (page != null && page > 0) {
                queryParams.put("page", page);
            }
            if (limit != null && limit > 0) {
                queryParams.put("page_size", limit);
            }
            if (status != null) {
                queryParams.put("status", status);
            }

            // 使用适配器获取文档列表
            PageData<KnowledgeFilesDTO> pageData = adapter.getDocumentList(datasetId, queryParams, page, limit);

            if (pageData != null) {
                log.info("根据状态查询文档列表成功，datasetId: {}, 状态: {}, 文档数量: {}",
                        datasetId, status, pageData.getList().size());
                return pageData;
            } else {
                throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
            }

        } catch (Exception e) {
            log.error("根据状态查询文档列表失败: {}", e.getMessage(), e);
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
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
                throw new RenException(ErrorCode.RAG_FILE_NAME_NOT_NULL);
            }

            if (fileSize == 0) {
                log.error("文件大小为0");
                throw new RenException(ErrorCode.RAG_FILE_CONTENT_EMPTY);
            }

            log.info("2. 开始使用适配器上传文档");

            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建上传参数
            Map<String, Object> uploadParams = new HashMap<>();
            if (StringUtils.isNotBlank(name)) {
                uploadParams.put("name", name);
            }
            if (metaFields != null && !metaFields.isEmpty()) {
                uploadParams.put("meta_fields", metaFields);
            }
            if (StringUtils.isNotBlank(chunkMethod)) {
                uploadParams.put("chunk_method", chunkMethod);
            }
            if (parserConfig != null && !parserConfig.isEmpty()) {
                uploadParams.put("parser_config", parserConfig);
            }

            // 使用适配器上传文档
            KnowledgeFilesDTO result = adapter.uploadDocument(datasetId, file,
                    (String) uploadParams.get("name"),
                    (Map<String, Object>) uploadParams.get("meta_fields"),
                    (String) uploadParams.get("chunk_method"),
                    (Map<String, Object>) uploadParams.get("parser_config"));

            log.info("文档上传成功，documentId: {}", result.getDocumentId());

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
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        log.info("=== 开始根据documentId删除文档 ===");
        log.info("删除文档documentId: {}, datasetId: {}", documentId, datasetId);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 使用适配器删除文档
            adapter.deleteDocument(datasetId, documentId);

            log.info("文档删除成功");

        } catch (Exception e) {
            log.error("删除文档失败: {}", e.getMessage(), e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        } finally {
            log.info("=== 根据documentId删除文档操作结束 ===");
        }
    }

    /**
     * 获取文件类型 - 支持RAG四种文档格式类型
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
     * 从RAG配置中提取适配器类型
     */
    private String extractAdapterType(Map<String, Object> config) {
        if (config == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        // 从配置中提取type字段
        String adapterType = (String) config.get("type");
        if (StringUtils.isBlank(adapterType)) {
            throw new RenException(ErrorCode.RAG_ADAPTER_TYPE_NOT_FOUND);
        }

        // 验证适配器类型是否已注册
        if (!KnowledgeBaseAdapterFactory.isAdapterTypeRegistered(adapterType)) {
            throw new RenException(ErrorCode.RAG_ADAPTER_TYPE_NOT_SUPPORTED, "适配器类型未注册: " + adapterType);
        }

        return adapterType;
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
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_NULL);
        }

        // 验证api_key是否存在且非空
        if (StringUtils.isBlank(apiKey)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_NULL);
        }

        // 检查api_key是否包含占位符
        if (apiKey.contains("你")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_INVALID);
        }

        // 验证base_url格式
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_INVALID);
        }
    }

    /**
     * 调用RAG API上传文档 - 流式上传版本
     */
    private String uploadDocumentToRAG(String datasetId, MultipartFile file, String name,
            Map<String, Object> metaFields, String chunkMethod,
            Map<String, Object> parserConfig) {
        try {
            log.info("开始调用知识库适配器上传文档，datasetId: {}, 文件名: {}", datasetId, file.getOriginalFilename());

            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 获取知识库适配器
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建上传参数
            Map<String, Object> uploadParams = new HashMap<>();
            uploadParams.put("file", file);
            uploadParams.put("name", StringUtils.isNotBlank(name) ? name : file.getOriginalFilename());

            if (metaFields != null && !metaFields.isEmpty()) {
                uploadParams.put("meta_fields", metaFields);
            }

            if (StringUtils.isNotBlank(chunkMethod)) {
                uploadParams.put("chunk_method", chunkMethod);
            }

            if (parserConfig != null && !parserConfig.isEmpty()) {
                uploadParams.put("parser_config", parserConfig);
            }

            log.debug("上传文档参数: {}", uploadParams.keySet());

            // 调用适配器上传文档
            KnowledgeFilesDTO result = adapter.uploadDocument(datasetId, file,
                    (String) uploadParams.get("name"),
                    (Map<String, Object>) uploadParams.get("meta_fields"),
                    (String) uploadParams.get("chunk_method"),
                    (Map<String, Object>) uploadParams.get("parser_config"));
            String documentId = result.getDocumentId();

            if (StringUtils.isBlank(documentId)) {
                log.error("无法从知识库适配器获取documentId");
                throw new RenException(ErrorCode.RAG_API_ERROR, "上传文档失败，未返回documentId");
            }

            log.info("知识库文档上传成功，documentId: {}，文档已开始自动解析切片", documentId);
            return documentId;

        } catch (Exception e) {
            log.error("知识库适配器调用失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "null";
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
     * 调用知识库适配器删除文档
     */
    private void deleteDocumentInRAG(String documentId, String datasetId) {
        try {
            log.info("开始调用知识库适配器删除文档，documentId: {}, datasetId: {}", documentId, datasetId);

            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 获取知识库适配器
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            log.debug("删除文档参数: documentId: {}", documentId);

            // 调用适配器删除文档
            adapter.deleteDocument(datasetId, documentId);

            log.info("知识库文档删除成功，documentId: {}", documentId);

        } catch (Exception e) {
            log.error("知识库适配器调用失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "null";
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
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        log.info("=== 开始解析文档（切块） ===");
        log.info("datasetId: {}, documentIds: {}", datasetId, documentIds);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 获取知识库适配器
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            log.debug("解析文档参数: documentIds: {}", documentIds);

            // 调用适配器解析文档
            boolean result = adapter.parseDocuments(datasetId, documentIds);

            if (result) {
                log.info("文档解析成功，datasetId: {}, documentIds: {}", datasetId, documentIds);
            } else {
                log.error("文档解析失败，datasetId: {}, documentIds: {}", datasetId, documentIds);
                throw new RenException(ErrorCode.RAG_API_ERROR, "文档解析失败");
            }

            return result;

        } catch (Exception e) {
            log.error("解析文档失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "null";
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
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        log.info("=== 开始列出切片 ===");
        log.info("datasetId: {}, documentId: {}, keywords: {}, page: {}, pageSize: {}, chunkId: {}",
                datasetId, documentId, keywords, page, pageSize, chunkId);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 获取知识库适配器
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            log.debug("查询参数: documentId: {}, keywords: {}, page: {}, pageSize: {}, chunkId: {}",
                    documentId, keywords, page, pageSize, chunkId);

            // 调用适配器列出切片
            Map<String, Object> result = adapter.listChunks(datasetId, documentId, keywords, page, pageSize, chunkId);

            log.info("切片列表获取成功，datasetId: {}, documentId: {}", datasetId, documentId);
            return result;

        } catch (Exception e) {
            log.error("列出切片失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "null";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 列出切片操作结束 ===");
        }
    }

    /**
     * 解析RAG API返回的切片列表响应
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
                                log.warn("自动检测到切片列表字段: '{}'，建议检查RAG API文档", entry.getKey());
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
                log.warn("RAG API响应缺少data字段，尝试直接解析响应");

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

            // 提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 获取知识库适配器
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建检索参数
            Map<String, Object> retrievalParams = new HashMap<>();
            retrievalParams.put("question", question);

            if (datasetIds != null && !datasetIds.isEmpty()) {
                retrievalParams.put("datasetIds", datasetIds);
            }

            if (documentIds != null && !documentIds.isEmpty()) {
                retrievalParams.put("documentIds", documentIds);
            }

            if (page != null && page > 0) {
                retrievalParams.put("page", page);
            }

            if (pageSize != null && pageSize > 0) {
                retrievalParams.put("pageSize", pageSize);
            }

            if (similarityThreshold != null) {
                retrievalParams.put("similarityThreshold", similarityThreshold);
            }

            if (vectorSimilarityWeight != null) {
                retrievalParams.put("vectorSimilarityWeight", vectorSimilarityWeight);
            }

            if (topK != null && topK > 0) {
                retrievalParams.put("topK", topK);
            }

            if (rerankId != null) {
                retrievalParams.put("rerankId", rerankId);
            }

            if (keyword != null) {
                retrievalParams.put("keyword", keyword);
            }

            if (highlight != null) {
                retrievalParams.put("highlight", highlight);
            }

            if (crossLanguages != null && !crossLanguages.isEmpty()) {
                retrievalParams.put("crossLanguages", crossLanguages);
            }

            if (metadataCondition != null) {
                retrievalParams.put("metadataCondition", metadataCondition);
            }

            log.debug("检索参数: {}", retrievalParams);

            // 调用适配器进行检索测试
            Map<String, Object> result = adapter.retrievalTest(question, datasetIds, documentIds, retrievalParams);

            log.info("召回测试成功，返回 {} 条切片", result.get("total"));
            return result;

        } catch (Exception e) {
            log.error("召回测试失败: {}", e.getMessage(), e);
            String errorMessage = e.getMessage() != null ? e.getMessage() : "null";
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, errorMessage);
        } finally {
            log.info("=== 召回测试操作结束 ===");
        }
    }
}