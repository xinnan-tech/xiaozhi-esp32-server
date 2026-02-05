package xiaozhi.modules.knowledge.service.impl;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.knowledge.dao.DocumentDao;
import xiaozhi.modules.knowledge.dao.KnowledgeBaseDao;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.entity.DocumentEntity;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;

@Service
@AllArgsConstructor
@Slf4j
public class KnowledgeFilesServiceImpl extends BaseServiceImpl<DocumentDao, DocumentEntity>
        implements KnowledgeFilesService {

    private final KnowledgeBaseService knowledgeBaseService;
    private final KnowledgeBaseDao knowledgeBaseDao;
    private final DocumentDao documentDao;
    private final ObjectMapper objectMapper;
    private final RedisUtils redisUtils;

    @Autowired
    private KnowledgeFilesService self;

    @Override
    public Map<String, Object> getRAGConfig(String ragModelId) {
        return knowledgeBaseService.getRAGConfig(ragModelId);
    }

    @Override
    public PageData<KnowledgeFilesDTO> getPageList(KnowledgeFilesDTO knowledgeFilesDTO, Integer page, Integer limit) {
        log.info("=== 开始获取知识库文档列表 (Local-First 优化版) ===");
        String datasetId = knowledgeFilesDTO.getDatasetId();
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        // 1. 获取本地影子表数据 (MyBatis-Plus 分页)
        Page<DocumentEntity> pageParams = new Page<>(page, limit);
        QueryWrapper<DocumentEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("dataset_id", datasetId);
        if (StringUtils.isNotBlank(knowledgeFilesDTO.getName())) {
            queryWrapper.like("name", knowledgeFilesDTO.getName());
        }
        if (StringUtils.isNotBlank(knowledgeFilesDTO.getRun())) {
            queryWrapper.eq("run", knowledgeFilesDTO.getRun());
        }
        if (StringUtils.isNotBlank(knowledgeFilesDTO.getStatus())) {
            queryWrapper.eq("status", knowledgeFilesDTO.getStatus());
        }
        queryWrapper.orderByDesc("created_at");

        // 2. 执行本地查询
        Page<DocumentEntity> iPage = documentDao.selectPage(pageParams, queryWrapper);

        // 3. 手动转换 DTO
        List<KnowledgeFilesDTO> dtoList = new ArrayList<>();
        for (DocumentEntity entity : iPage.getRecords()) {
            dtoList.add(convertEntityToDTO(entity));
        }
        PageData<KnowledgeFilesDTO> pageData = new PageData<>(dtoList, iPage.getTotal());

        // 4. 动态状态同步 (带限流与保护)
        if (pageData.getList() != null && !pageData.getList().isEmpty()) {
            KnowledgeBaseAdapter adapter = null;
            for (KnowledgeFilesDTO dto : pageData.getList()) {
                // 只有处于“解析中”或“待解析”状态的文档才尝试同步
                boolean needSync = "RUNNING".equals(dto.getRun()) || "UNSTART".equals(dto.getRun());
                if (needSync) {
                    // Issue 5: 限流保护，5秒内不重复向 RAGFlow 发起同一文档的状态查询
                    DocumentEntity localEntity = documentDao.selectOne(new QueryWrapper<DocumentEntity>()
                            .eq("document_id", dto.getDocumentId()));
                    if (localEntity != null && localEntity.getLastSyncAt() != null) {
                        long diff = System.currentTimeMillis() - localEntity.getLastSyncAt().getTime();
                        if (diff < 5000) {
                            continue;
                        }
                    }

                    // 延迟初始化适配器，仅在确实需要同步时创建
                    if (adapter == null) {
                        try {
                            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
                            adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig), ragConfig);
                        } catch (Exception e) {
                            log.warn("同步中断：无法初始化适配器, {}", e.getMessage());
                            break;
                        }
                    }
                    syncDocumentStatusWithRAG(dto, adapter);
                }
            }
        }

        log.info("获取文档列表成功，总数: {}", pageData.getTotal());
        return pageData;
    }

    /**
     * 将本地记录实体转换为DTO，手动对齐不一致字段 (size -> fileSize, type -> fileType)
     */
    private KnowledgeFilesDTO convertEntityToDTO(DocumentEntity entity) {
        if (entity == null) {
            return null;
        }
        KnowledgeFilesDTO dto = new KnowledgeFilesDTO();
        // 1. 基础字段拷贝
        BeanUtils.copyProperties(entity, dto);

        // Issue 2: 修正 ID 语义。前端习惯使用 id 作为操作主键。
        // 在该模块中，应始终将远程 documentId 映射为 DTO 的 id，确保前端在详情/删除等操作时 ID 一致。
        dto.setId(entity.getDocumentId());

        // 2. 将本地记录实体转换为DTO，手动对齐不一致字段 (size -> fileSize, type -> fileType)
        dto.setFileSize(entity.getSize());
        dto.setFileType(entity.getType());
        dto.setRun(entity.getRun());
        dto.setChunkCount(entity.getChunkCount());
        dto.setTokenCount(entity.getTokenCount());
        dto.setError(entity.getError());

        // 3. 自定义元数据 JSON 反序列化 (Issue 3)
        if (StringUtils.isNotBlank(entity.getMetaFields())) {
            try {
                dto.setMetaFields(objectMapper.readValue(entity.getMetaFields(),
                        new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {
                        }));
            } catch (Exception e) {
                log.warn("反序列化 MetaFields 失败, entityId: {}, error: {}", entity.getId(), e.getMessage());
            }
        }

        // 4. 解析配置 JSON 反序列化
        if (StringUtils.isNotBlank(entity.getParserConfig())) {
            try {
                dto.setParserConfig(objectMapper.readValue(entity.getParserConfig(),
                        new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {
                        }));
            } catch (Exception e) {
                log.warn("反序列化 ParserConfig 失败, entityId: {}, error: {}", entity.getId(), e.getMessage());
            }
        }
        return dto;

    }

    /**
     * 同步文档状态与RAG实际状态
     * 优化状态同步逻辑，确保解析中状态能够正常显示
     * 只有当文档有切片且解析时间超过30秒时，才更新为完成状态
     */
    /**
     * 同步文档状态与RAG实际状态 (增强型：支持外部传入适配器)
     */
    private void syncDocumentStatusWithRAG(KnowledgeFilesDTO dto, KnowledgeBaseAdapter adapter) {
        if (dto == null || StringUtils.isBlank(dto.getDocumentId()) || adapter == null) {
            return;
        }

        String documentId = dto.getDocumentId();
        String datasetId = dto.getDatasetId();

        try {
            // 使用精准的 List API 配合 ID 过滤来获取状态
            Map<String, Object> queryParams = new HashMap<>();
            queryParams.put("id", documentId);

            PageData<KnowledgeFilesDTO> remoteList = adapter.getDocumentList(datasetId, queryParams, 1, 1);

            if (remoteList != null && remoteList.getList() != null && !remoteList.getList().isEmpty()) {
                KnowledgeFilesDTO remoteDto = remoteList.getList().get(0);
                String remoteStatus = remoteDto.getStatus();

                // 核心状态对齐判别逻辑
                boolean statusChanged = remoteStatus != null && !remoteStatus.equals(dto.getStatus());
                boolean isProcessing = "RUNNING".equals(remoteDto.getRun()) || "UNSTART".equals(remoteDto.getRun());

                // 只要状态有变，或者文件仍在解析中（实时刷进度），就执行同步
                if (statusChanged || isProcessing) {
                    log.info("影子同步：状态变化={}，解析中={}，文档={}，最新状态={}，进度={}",
                            statusChanged, isProcessing, documentId, remoteStatus, remoteDto.getProgress());

                    // 1. 同步内存 DTO
                    dto.setStatus(remoteStatus);
                    dto.setRun(remoteDto.getRun());
                    dto.setProgress(remoteDto.getProgress());
                    dto.setChunkCount(remoteDto.getChunkCount());
                    dto.setTokenCount(remoteDto.getTokenCount());
                    dto.setError(remoteDto.getError());
                    dto.setProcessDuration(remoteDto.getProcessDuration());
                    dto.setThumbnail(remoteDto.getThumbnail());

                    // 2. 同步本地影子表
                    UpdateWrapper<DocumentEntity> updateWrapper = new UpdateWrapper<DocumentEntity>()
                            .set("status", remoteStatus)
                            .set("run", remoteDto.getRun())
                            .set("progress", remoteDto.getProgress())
                            .set("chunk_count", remoteDto.getChunkCount())
                            .set("token_count", remoteDto.getTokenCount())
                            .set("error", remoteDto.getError())
                            .set("process_duration", remoteDto.getProcessDuration())
                            .set("thumbnail", remoteDto.getThumbnail())
                            .eq("document_id", documentId)
                            .eq("dataset_id", datasetId);

                    // 序列化元数据同步
                    if (remoteDto.getMetaFields() != null) {
                        try {
                            updateWrapper.set("meta_fields",
                                    objectMapper.writeValueAsString(remoteDto.getMetaFields()));
                        } catch (Exception e) {
                            log.warn("同步元数据序列化失败: {}", e.getMessage());
                        }
                    }

                    // 优先同步 RAG 侧的更新时间，避免本地同步行为覆盖业务修改时间
                    Date lastUpdate = remoteDto.getUpdatedAt() != null ? remoteDto.getUpdatedAt() : new Date();
                    updateWrapper.set("updated_at", lastUpdate);
                    updateWrapper.set("last_sync_at", new Date()); // 记录影子库同步时间

                    documentDao.update(null, updateWrapper);
                }
            } else {
                // Issue 6: 远程列表为空，说明 RAGFlow 侧可能已物理删除文档。
                // 我们不应直接返回，而应同步将影子库记录标记为逻辑失效或取消，防止形成“僵尸记录”
                log.warn("远程同步感知：文档在 RAGFlow 侧已消失，准备清理影子状态, docId={}", documentId);
                dto.setRun("CANCEL");
                dto.setError("文档在远程服务中已被删除");

                documentDao.update(null, new UpdateWrapper<DocumentEntity>()
                        .set("run", "CANCEL")
                        .set("error", "文档在远程服务中已被删除")
                        .set("updated_at", new Date())
                        .eq("document_id", documentId));
            }
        } catch (Exception e) {
            log.debug("同步文档状态失败，documentId: {}, error: {}", documentId, e.getMessage());
        }
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
    public KnowledgeFilesDTO uploadDocument(String datasetId, MultipartFile file, String name,
            Map<String, Object> metaFields, String chunkMethod,
            Map<String, Object> parserConfig) {
        if (StringUtils.isBlank(datasetId) || file == null || file.isEmpty()) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        log.info("=== 开始文档上传操作 (强一致性优化) ===");

        // 1. 准备工作 (非事务性)
        String fileName = StringUtils.isNotBlank(name) ? name : file.getOriginalFilename();
        if (StringUtils.isBlank(fileName)) {
            throw new RenException(ErrorCode.RAG_FILE_NAME_NOT_NULL);
        }

        log.info("1. 发起远程上传: datasetId={}, fileName={}", datasetId, fileName);

        // 获取适配器 (非事务性)
        Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
        KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig), ragConfig);

        // 执行远程上传 (耗时 IO，在事务之外)
        KnowledgeFilesDTO result = adapter.uploadDocument(datasetId, file, fileName,
                metaFields, chunkMethod, parserConfig);

        if (result == null || StringUtils.isBlank(result.getDocumentId())) {
            throw new RenException(ErrorCode.RAG_API_ERROR, "远程上传成功但未返回有效 DocumentID");
        }

        // 2. 本地持久化 (通过 self 调用以激活 @Transactional 代理)
        log.info("2. 同步保存本地影子记录: documentId={}", result.getDocumentId());
        self.saveDocumentShadow(datasetId, result, fileName, chunkMethod, parserConfig);

        log.info("=== 文档上传与影子记录保存成功 ===");
        return result;
    }

    /**
     * 原子化保存影子记录，确保本地数据绝对一致
     */
    @Transactional(rollbackFor = Exception.class)
    public void saveDocumentShadow(String datasetId, KnowledgeFilesDTO result, String originalName, String chunkMethod,
            Map<String, Object> parserConfig) {
        DocumentEntity entity = new DocumentEntity();
        entity.setDatasetId(datasetId);
        entity.setDocumentId(result.getDocumentId());
        entity.setName(StringUtils.isNotBlank(result.getName()) ? result.getName() : originalName);
        entity.setSize(result.getFileSize());
        entity.setType(getFileType(entity.getName()));
        entity.setChunkMethod(chunkMethod);

        if (parserConfig != null) {
            try {
                entity.setParserConfig(objectMapper.writeValueAsString(parserConfig));
            } catch (Exception e) {
                log.warn("序列化解析配置失败: {}", e.getMessage());
            }
        }

        entity.setStatus(result.getStatus() != null ? result.getStatus() : "1");
        entity.setRun(result.getRun());
        entity.setProgress(result.getProgress());
        entity.setThumbnail(result.getThumbnail());
        entity.setProcessDuration(result.getProcessDuration());
        entity.setSourceType(result.getSourceType());
        entity.setError(result.getError());
        entity.setChunkCount(result.getChunkCount());
        entity.setTokenCount(result.getTokenCount());
        entity.setEnabled(1);

        // 持久化元数据
        if (result.getMetaFields() != null) {
            try {
                entity.setMetaFields(objectMapper.writeValueAsString(result.getMetaFields()));
            } catch (Exception e) {
                log.warn("持久化影子元数据失败: {}", e.getMessage());
            }
        }

        // 优先同步 RAG 侧的时间戳，若无则使用本地时间
        entity.setCreatedAt(result.getCreatedAt() != null ? result.getCreatedAt() : new Date());
        entity.setUpdatedAt(result.getUpdatedAt() != null ? result.getUpdatedAt() : new Date());

        // 插入影子表 (若失败将抛出异常，触发调用方报错，确保 Local-First 列表一致性)
        documentDao.insert(entity);

        // Issue 4: 同步递增数据集文档总数统计，保持父子表一致
        knowledgeBaseDao.updateStatsAfterUpload(datasetId);
        log.info("已同步递增数据集统计: datasetId={}", datasetId);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void deleteByDocumentId(String documentId, String datasetId) {
        if (StringUtils.isBlank(documentId) || StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        log.info("=== 开始根据documentId删除文档 (地狱级加固版) ===");

        // 1. 权限与物理归属权预审 (防止 ID 劫持漏洞)
        DocumentEntity entity = documentDao.selectOne(
                new QueryWrapper<DocumentEntity>()
                        .eq("dataset_id", datasetId)
                        .eq("document_id", documentId));

        if (entity == null) {
            log.warn("尝试删除不存在或归属权异常的文档: docId={}, datasetId={}", documentId, datasetId);
            throw new RenException(ErrorCode.NO_PERMISSION);
        }

        // 2. 状态校验 (拦截解析中文件的删除，防止 RAG 侧产生僵尸数据 - Issue 4)
        // 修正逻辑：status 是 String 类型，必须使用字符串比较或状态码转换判断
        if (entity.getStatus() != null && "1".equals(entity.getStatus())) {
            log.warn("拦截解析中文件的删除请求: docId={}, status=解析中", documentId);
            throw new RenException(ErrorCode.RAG_DOCUMENT_PARSING_DELETE_ERROR);
        }

        // 记录统计信息偏移量，用于后续影子表同步
        Long chunkDelta = entity.getChunkCount() != null ? entity.getChunkCount() : 0L;
        Long tokenDelta = entity.getTokenCount() != null ? entity.getTokenCount() : 0L;

        // 3. 获取适配器 (非事务性)
        Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
        KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig), ragConfig);

        // 4. 执行远程删除 (耗时 IO，已被 NOT_SUPPORTED 物理挂起事务)
        try {
            adapter.deleteDocument(datasetId, documentId);
            log.info("远程请求删除成功: documentId={}", documentId);
        } catch (Exception e) {
            log.warn("远程删除请求失败 (可能文件已不存在): {}", e.getMessage());
        }

        // 5. 原子化清理本地影子记录并同步统计数据 (通过 self 调用激活 @Transactional)
        log.info("5. 同步清理本地影子记录并更新统计: documentId={}", documentId);
        self.deleteDocumentShadow(documentId, datasetId, chunkDelta, tokenDelta);

        // 6. 清理缓存 (Issue 7: 缓存孤岛修复)
        try {
            String cacheKey = RedisKeys.getKnowledgeBaseCacheKey(datasetId);
            redisUtils.delete(cacheKey);
            log.info("已精准驱逐数据集缓存: {}", cacheKey);
        } catch (Exception e) {
            log.warn("驱逐 Redis 缓存失败 (非核心链路，忽略): {}", e.getMessage());
        }

        log.info("=== 文档物理清理与统计同步成功 ===");
    }

    /**
     * 原子化删除影子记录并同步父表统计，确保 Local-First 全链路一致性
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteDocumentShadow(String documentId, String datasetId, Long chunkDelta, Long tokenDelta) {
        // 1. 物理删除记录
        int deleted = documentDao.delete(
                new QueryWrapper<DocumentEntity>()
                        .eq("dataset_id", datasetId)
                        .eq("document_id", documentId));

        if (deleted > 0) {
            // 2. 同步更新数据集统计信息 (原子操作，防止并发漂移)
            knowledgeBaseDao.updateStatsAfterDelete(datasetId, chunkDelta, tokenDelta);
            log.info("已同步扣减数据集统计: datasetId={}, chunks={}, tokens={}", datasetId, chunkDelta, tokenDelta);
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
                log.info("文档解析命令发送成功，准备同步本地影子库状态，datasetId: {}, documentIds: {}", datasetId, documentIds);
                // 指令成功后立即更新本地影子状态为 RUNNING 和 解析中(1)，确保 Local-First 列表能立即反馈
                documentDao.update(null, new UpdateWrapper<DocumentEntity>()
                        .set("run", "RUNNING")
                        .set("status", "1")
                        .set("updated_at", new Date())
                        .eq("dataset_id", datasetId)
                        .in("document_id", documentIds));

                log.info("文档本地状态已更新为 RUNNING");
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
    public xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO listChunks(String datasetId, String documentId,
            String keywords,
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

            // 调用适配器列出切片 (直接返回强类型 DTO)
            xiaozhi.modules.knowledge.dto.document.ChunkDTO.ListVO result = adapter.listChunks(datasetId, documentId,
                    keywords, page, pageSize, chunkId);

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

    @Override
    public xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO retrievalTest(String question,
            List<String> datasetIds, List<String> documentIds,
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

            // 调用适配器进行检索测试 (直接返回结果 DTO)
            xiaozhi.modules.knowledge.dto.document.RetrievalDTO.ResultVO result = adapter.retrievalTest(question,
                    datasetIds, documentIds, retrievalParams);

            log.info("召回测试成功，返回数: {}", result != null ? result.getTotal() : 0);
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