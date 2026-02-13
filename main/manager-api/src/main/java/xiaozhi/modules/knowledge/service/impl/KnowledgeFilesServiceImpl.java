package xiaozhi.modules.knowledge.service.impl;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import org.springframework.util.CollectionUtils;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.knowledge.dao.DocumentDao;
import xiaozhi.modules.knowledge.entity.DocumentEntity;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;

@Service
@Slf4j
public class KnowledgeFilesServiceImpl extends BaseServiceImpl<DocumentDao, DocumentEntity>
        implements KnowledgeFilesService {

    private final KnowledgeBaseService knowledgeBaseService;
    private final DocumentDao documentDao;
    private final ObjectMapper objectMapper;
    private final RedisUtils redisUtils;

    public KnowledgeFilesServiceImpl(KnowledgeBaseService knowledgeBaseService,
            DocumentDao documentDao,
            ObjectMapper objectMapper,
            RedisUtils redisUtils) {
        this.knowledgeBaseService = knowledgeBaseService;
        this.documentDao = documentDao;
        this.objectMapper = objectMapper;
        this.redisUtils = redisUtils;
    }

    @Lazy
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
        // [Bug Fix] P1: 扩大同步白名单，CANCEL/FAIL 也允许低频同步以支持自愈
        if (pageData.getList() != null && !pageData.getList().isEmpty()) {
            KnowledgeBaseAdapter adapter = null;
            for (KnowledgeFilesDTO dto : pageData.getList()) {
                String runStatus = dto.getRun();
                // 高优先级同步: RUNNING/UNSTART (5秒冷却)
                boolean isActiveSync = "RUNNING".equals(runStatus) || "UNSTART".equals(runStatus);
                // 低频自愈同步: CANCEL/FAIL (60秒冷却), 防止错误状态永久锁死
                boolean isRecoverySync = "CANCEL".equals(runStatus) || "FAIL".equals(runStatus);
                boolean needSync = isActiveSync || isRecoverySync;

                if (needSync) {
                    // 限流保护：活跃状态 5 秒冷却，自愈状态 60 秒冷却
                    long cooldownMs = isActiveSync ? 5000 : 60000;
                    DocumentEntity localEntity = documentDao.selectOne(new QueryWrapper<DocumentEntity>()
                            .eq("document_id", dto.getDocumentId()));
                    if (localEntity != null && localEntity.getLastSyncAt() != null) {
                        long diff = System.currentTimeMillis() - localEntity.getLastSyncAt().getTime();
                        if (diff < cooldownMs) {
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
                    // [关键修复] 记录同步前的 Token 数，用于计算增量
                    Long oldTokenCount = dto.getTokenCount() != null ? dto.getTokenCount() : 0L;

                    syncDocumentStatusWithRAG(dto, adapter);

                    // 计算增量并更新知识库统计 (与定时任务保持一致)
                    Long newTokenCount = dto.getTokenCount() != null ? dto.getTokenCount() : 0L;
                    Long tokenDelta = newTokenCount - oldTokenCount;
                    if (tokenDelta != 0) {
                        knowledgeBaseService.updateStatistics(datasetId, 0, 0L, tokenDelta);
                        log.info("懒加载同步: 修正知识库统计, docId={}, tokenDelta={}", dto.getDocumentId(), tokenDelta);
                    }
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
                        new TypeReference<Map<String, Object>>() {
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
            // 使用强类型 ListReq 配合 ID 过滤来获取状态
            DocumentDTO.ListReq listReq = DocumentDTO.ListReq.builder()
                    .id(documentId)
                    .page(1)
                    .pageSize(1)
                    .build();

            PageData<KnowledgeFilesDTO> remoteList = adapter.getDocumentList(datasetId, listReq);

            if (remoteList != null && remoteList.getList() != null && !remoteList.getList().isEmpty()) {
                KnowledgeFilesDTO remoteDto = remoteList.getList().get(0);
                String remoteStatus = remoteDto.getStatus();

                // 核心状态对齐判别逻辑
                boolean statusChanged = remoteStatus != null && !remoteStatus.equals(dto.getStatus());
                boolean runChanged = remoteDto.getRun() != null && !remoteDto.getRun().equals(dto.getRun());
                boolean isProcessing = "RUNNING".equals(remoteDto.getRun()) || "UNSTART".equals(remoteDto.getRun());

                // 只要状态有变，或者运行状态有变，或者文件仍在解析中（实时刷进度），就执行同步
                if (statusChanged || runChanged || isProcessing) {
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
                // Issue 6: 远程列表为空，可能是文档已删除，也可能是适配器调用出了问题
                // [Bug Fix] P2: 仅当远程确实返回了合法空列表时才标记 CANCEL
                // 同时更新 last_sync_at，配合 P1 冷却机制防止高频误判
                log.warn("远程同步感知：RAGFlow 返回空文档列表, docId={}, 当前本地状态={}",
                        documentId, dto.getRun());
                dto.setRun("CANCEL");
                dto.setError("文档在远程服务中已被删除");

                documentDao.update(null, new UpdateWrapper<DocumentEntity>()
                        .set("run", "CANCEL")
                        .set("error", "文档在远程服务中已被删除")
                        .set("updated_at", new Date())
                        .set("last_sync_at", new Date())
                        .eq("document_id", documentId));
            }
        } catch (Exception e) {
            // [Bug Fix] P2: 适配器调用异常时不标记 CANCEL，避免因网络/反序列化问题导致误判
            // 仅记录日志，等下次同步周期重试
            log.warn("同步文档状态时适配器调用失败(不标记CANCEL), documentId: {}, error: {}",
                    documentId, e.getMessage());
        }
    }

    @Override
    public DocumentDTO.InfoVO getByDocumentId(String documentId, String datasetId) {
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
            DocumentDTO.InfoVO info = adapter.getDocumentById(datasetId, documentId);

            if (info != null) {
                log.info("获取文档详情成功，documentId: {}", documentId);
                return info;
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

        // 构造强类型请求 DTO
        DocumentDTO.UploadReq uploadReq = DocumentDTO.UploadReq.builder()
                .datasetId(datasetId)
                .file(file)
                .name(fileName)
                .metaFields(metaFields)
                .build();

        // 转换分块方法 (String -> Enum)
        if (StringUtils.isNotBlank(chunkMethod)) {
            try {
                uploadReq.setChunkMethod(DocumentDTO.InfoVO.ChunkMethod.valueOf(chunkMethod.toUpperCase()));
            } catch (Exception e) {
                log.warn("无效的分块方法: {}, 将使用后台默认配置", chunkMethod);
            }
        }

        // 转换解析配置 (Map -> DTO)
        if (parserConfig != null && !parserConfig.isEmpty()) {
            uploadReq.setParserConfig(objectMapper.convertValue(parserConfig, DocumentDTO.InfoVO.ParserConfig.class));
        }

        // 执行远程上传 (耗时 IO，在事务之外)
        KnowledgeFilesDTO result = adapter.uploadDocument(uploadReq);

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
        knowledgeBaseService.updateStatistics(datasetId, 1, 0L, 0L);
        log.info("已同步递增数据集统计: datasetId={}", datasetId);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void deleteDocuments(String datasetId, DocumentDTO.BatchIdReq req) {
        if (StringUtils.isBlank(datasetId) || req == null || req.getIds() == null || req.getIds().isEmpty()) {
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        List<String> documentIds = req.getIds();
        log.info("=== 开始批量删除文档: datasetId={}, count={} ===", datasetId, documentIds.size());

        // 1. 批量权限与状态预审
        List<DocumentEntity> entities = documentDao.selectList(
                new QueryWrapper<DocumentEntity>()
                        .eq("dataset_id", datasetId)
                        .in("document_id", documentIds));

        if (entities.size() != documentIds.size()) {
            log.warn("部分文档不存在或归属权异常: 预期={}, 实际={}", documentIds.size(), entities.size());
            throw new RenException(ErrorCode.NO_PERMISSION);
        }

        long totalChunkDelta = 0;
        long totalTokenDelta = 0;

        for (DocumentEntity entity : entities) {
            // 拦截正在解析中的文档的删除请求
            // [Bug Fix] 判断解析中应该用 run 字段(RUNNING), 而非 status 字段
            // status="1" 是"启用/正常"的意思, 不是"解析中"
            if ("RUNNING".equals(entity.getRun())) {
                log.warn("拦截解析中文件的删除请求: docId={}", entity.getDocumentId());
                throw new RenException(ErrorCode.RAG_DOCUMENT_PARSING_DELETE_ERROR);
            }
            totalChunkDelta += entity.getChunkCount() != null ? entity.getChunkCount() : 0L;
            totalTokenDelta += entity.getTokenCount() != null ? entity.getTokenCount() : 0L;
        }

        // 2. 获取适配器 (非事务性)
        Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
        KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig), ragConfig);

        // 3. 执行远程删除
        try {
            adapter.deleteDocument(datasetId, req);
            log.info("远程批量删除请求成功");
        } catch (Exception e) {
            log.warn("远程删除请求部分或全部失败: {}", e.getMessage());
        }

        // 4. 原子化清理本地影子记录并同步统计数据
        self.deleteDocumentShadows(documentIds, datasetId, totalChunkDelta, totalTokenDelta);

        // 5. 清理缓存
        try {
            String cacheKey = RedisKeys.getKnowledgeBaseCacheKey(datasetId);
            redisUtils.delete(cacheKey);
            log.info("已驱逐数据集缓存: {}", cacheKey);
        } catch (Exception e) {
            log.warn("驱逐 Redis 缓存失败: {}", e.getMessage());
        }

        log.info("=== 批量文档清理完成 ===");
    }

    /**
     * 批量原子化删除影子记录并同步父表统计
     */
    @Transactional(rollbackFor = Exception.class)
    public void deleteDocumentShadows(List<String> documentIds, String datasetId, Long chunkDelta, Long tokenDelta) {
        // 1. 物理删除记录
        int deleted = documentDao.delete(
                new QueryWrapper<DocumentEntity>()
                        .eq("dataset_id", datasetId)
                        .in("document_id", documentIds));

        if (deleted > 0) {
            // 2. 同步更新数据集统计信息
            knowledgeBaseService.updateStatistics(datasetId, -documentIds.size(), -chunkDelta, -tokenDelta);
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
    public ChunkDTO.ListVO listChunks(String datasetId, String documentId, ChunkDTO.ListReq req) {
        if (StringUtils.isBlank(datasetId) || StringUtils.isBlank(documentId)) {
            throw new RenException(ErrorCode.RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL);
        }

        log.info("=== 开始列出切片: datasetId={}, documentId={}, req={} ===", datasetId, documentId, req);

        try {
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig),
                    ragConfig);

            ChunkDTO.ListVO result = adapter.listChunks(datasetId, documentId, req);
            log.info("切片列表获取成功: datasetId={}, total={}", datasetId, result.getTotal());
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
    public RetrievalDTO.ResultVO retrievalTest(RetrievalDTO.TestReq req) {
        if (CollectionUtils.isEmpty(req.getDatasetIds())) {
            throw new RenException("未指定召回测试的知识库");
        }

        log.info("=== 开始召回测试: req={} ===", req);

        try {
            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(req.getDatasetIds().get(0));
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig),
                    ragConfig);

            RetrievalDTO.ResultVO result = adapter.retrievalTest(req);
            log.info("召回测试成功: total={}", result != null ? result.getTotal() : 0);
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

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteDocumentsByDatasetId(String datasetId) {
        log.info("级联清理数据集文档: datasetId={}", datasetId);
        List<DocumentEntity> list = documentDao
                .selectList(new QueryWrapper<DocumentEntity>().eq("dataset_id", datasetId));
        if (list == null || list.isEmpty())
            return;

        List<String> docIds = list.stream().map(DocumentEntity::getDocumentId).toList();

        // 封包调用现有删除逻辑 (含 RAG 物理删除)
        DocumentDTO.BatchIdReq req = DocumentDTO.BatchIdReq.builder().ids(docIds).build();
        this.deleteDocuments(datasetId, req);
    }

    @Override
    public void syncRunningDocuments() {
        // 1. 查询所有 RUNNING 状态的文档
        List<DocumentEntity> runningDocs = documentDao.selectList(
                new QueryWrapper<DocumentEntity>()
                        .eq("run", "RUNNING")
                        .eq("status", "1") // 仅同步启用的文档
        );

        if (runningDocs == null || runningDocs.isEmpty()) {
            return;
        }

        log.info("定时任务: 发现 {} 个文档正在解析中，开始同步...", runningDocs.size());

        // 2. 按 DatasetID 分组，复用 Adapter
        Map<String, List<DocumentEntity>> groupedDocs = runningDocs.stream()
                .collect(java.util.stream.Collectors.groupingBy(DocumentEntity::getDatasetId));

        groupedDocs.forEach((datasetId, docs) -> {
            KnowledgeBaseAdapter adapter = null;
            try {
                // 初始化 Adapter (每个数据集只初始化一次)
                Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfigByDatasetId(datasetId);
                adapter = KnowledgeBaseAdapterFactory.getAdapter(extractAdapterType(ragConfig), ragConfig);
            } catch (Exception e) {
                log.warn("无法为数据集 {} 初始化适配器，跳过同步: {}", datasetId, e.getMessage());
                return;
            }

            for (DocumentEntity doc : docs) {
                try {
                    // 构造临时 DTO 传给同步方法
                    KnowledgeFilesDTO dto = convertEntityToDTO(doc);
                    // 记录同步前的 Token 数
                    Long oldTokenCount = dto.getTokenCount() != null ? dto.getTokenCount() : 0L;

                    syncDocumentStatusWithRAG(dto, adapter);

                    // 3. [关键修复] 计算增量并更新知识库统计
                    Long newTokenCount = dto.getTokenCount() != null ? dto.getTokenCount() : 0L;
                    Long tokenDelta = newTokenCount - oldTokenCount;

                    // 仅当状态变为 SUCCESS 且 Token 数有变化时更新统计
                    if (tokenDelta != 0) {
                        knowledgeBaseService.updateStatistics(datasetId, 0, 0L, tokenDelta);
                        log.info("定时任务: 同步修正知识库统计, docId={}, tokenDelta={}", dto.getDocumentId(), tokenDelta);
                    }
                } catch (Exception e) {
                    log.error("同步文档 {} 失败: {}", doc.getDocumentId(), e.getMessage());
                }
            }
        });
    }
}