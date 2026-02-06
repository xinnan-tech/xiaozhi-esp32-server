package xiaozhi.modules.knowledge.controller;

import java.util.List;
import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.knowledge.dto.KnowledgeBaseDTO;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.knowledge.service.KnowledgeFilesService;
import xiaozhi.modules.security.user.SecurityUser;

@AllArgsConstructor
@RestController
@RequestMapping("/datasets/{dataset_id}")
@Tag(name = "知识库文档管理")
public class KnowledgeFilesController {

    private final KnowledgeFilesService knowledgeFilesService;
    private final KnowledgeBaseService knowledgeBaseService;

    /**
     * 验证当前用户是否有权限操作指定知识库
     * 
     * @param datasetId 知识库ID
     */
    private void validateKnowledgeBasePermission(String datasetId) {
        // 获取当前登录用户ID
        Long currentUserId = SecurityUser.getUserId();

        // 获取知识库信息
        KnowledgeBaseDTO knowledgeBase = knowledgeBaseService.getByDatasetId(datasetId);

        // 检查权限：用户只能操作自己创建的知识库
        if (knowledgeBase.getCreator() == null || !knowledgeBase.getCreator().equals(currentUserId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    @GetMapping("/documents")
    @Operation(summary = "分页查询文档列表")
    @RequiresPermissions("sys:role:normal")
    public Result<PageData<KnowledgeFilesDTO>> getPageList(
            @PathVariable("dataset_id") String datasetId,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String status,
            @RequestParam(required = false, defaultValue = "1") Integer page,
            @RequestParam(required = false, defaultValue = "10") Integer page_size) {
        // 验证知识库权限
        validateKnowledgeBasePermission(datasetId);

        // 组装参数
        KnowledgeFilesDTO knowledgeFilesDTO = new KnowledgeFilesDTO();
        knowledgeFilesDTO.setDatasetId(datasetId);
        knowledgeFilesDTO.setName(name);
        knowledgeFilesDTO.setStatus(status);
        PageData<KnowledgeFilesDTO> pageData = knowledgeFilesService.getPageList(knowledgeFilesDTO, page, page_size);
        return new Result<PageData<KnowledgeFilesDTO>>().ok(pageData);
    }

    @GetMapping("/documents/status/{status}")
    @Operation(summary = "根据状态分页查询文档列表")
    @RequiresPermissions("sys:role:normal")
    public Result<PageData<KnowledgeFilesDTO>> getPageListByStatus(
            @PathVariable("dataset_id") String datasetId,
            @PathVariable("status") String status,
            @RequestParam(required = false, defaultValue = "1") Integer page,
            @RequestParam(required = false, defaultValue = "10") Integer page_size) {
        // 验证知识库权限
        validateKnowledgeBasePermission(datasetId);
        // 组装参数
        KnowledgeFilesDTO knowledgeFilesDTO = new KnowledgeFilesDTO();
        knowledgeFilesDTO.setDatasetId(datasetId);
        knowledgeFilesDTO.setStatus(status);
        PageData<KnowledgeFilesDTO> pageData = knowledgeFilesService.getPageList(knowledgeFilesDTO, page, page_size);
        return new Result<PageData<KnowledgeFilesDTO>>().ok(pageData);
    }

    @PostMapping("/documents")
    @Operation(summary = "上传文档到知识库")
    @RequiresPermissions("sys:role:normal")
    public Result<KnowledgeFilesDTO> uploadDocument(
            @PathVariable("dataset_id") String datasetId,
            @RequestParam("file") MultipartFile file,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String chunkMethod,
            @RequestParam(required = false) String metaFields,
            @RequestParam(required = false) String parserConfig) {

        // 验证知识库权限
        validateKnowledgeBasePermission(datasetId);

        KnowledgeFilesDTO resp = knowledgeFilesService.uploadDocument(datasetId, file, name,
                metaFields != null ? parseJsonMap(metaFields) : null,
                chunkMethod,
                parserConfig != null ? parseJsonMap(parserConfig) : null);
        return new Result<KnowledgeFilesDTO>().ok(resp);
    }

    @DeleteMapping("/documents/{document_id}")
    @Operation(summary = "删除单个文档")
    @Parameter(name = "document_id", description = "文档ID", required = true)
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable("dataset_id") String datasetId,
            @PathVariable("document_id") String documentId) {
        // 验证知识库权限
        validateKnowledgeBasePermission(datasetId);

        knowledgeFilesService.deleteByDocumentId(documentId, datasetId);
        return new Result<>();
    }

    @PostMapping("/chunks")
    @Operation(summary = "解析文档（切块）")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> parseDocuments(@PathVariable("dataset_id") String datasetId,
            @RequestBody Map<String, List<String>> requestBody) {
        // 验证知识库权限
        validateKnowledgeBasePermission(datasetId);

        List<String> documentIds = requestBody.get("document_ids");
        if (documentIds == null || documentIds.isEmpty()) {
            return new Result<Void>().error("document_ids参数不能为空");
        }

        boolean success = knowledgeFilesService.parseDocuments(datasetId, documentIds);
        if (success) {
            return new Result<Void>();
        } else {
            return new Result<Void>().error("文档解析失败，文档可能正在处理中");
        }
    }

    @GetMapping("/documents/{document_id}/chunks")
    @Operation(summary = "列出指定文档的切片")
    @RequiresPermissions("sys:role:normal")
    public Result<ChunkDTO.ListVO> listChunks(
            @PathVariable("dataset_id") String datasetId,
            @PathVariable("document_id") String documentId,
            @RequestParam(required = false) String keywords,
            @RequestParam(required = false, defaultValue = "1") Integer page,
            @RequestParam(required = false, defaultValue = "50") Integer page_size,
            @RequestParam(required = false) String id) {

        // 验证权限 (内部已包含知识库存在性校验与归属权校验)
        validateKnowledgeBasePermission(datasetId);

        // 调用服务层获取强类型切片列表
        ChunkDTO.ListVO result = knowledgeFilesService.listChunks(datasetId,
                documentId, keywords, page, page_size, id);
        return new Result<ChunkDTO.ListVO>().ok(result);
    }

    @PostMapping("/retrieval-test")
    @Operation(summary = "召回测试")
    @RequiresPermissions("sys:role:normal")
    public Result<RetrievalDTO.ResultVO> retrievalTest(
            @PathVariable("dataset_id") String datasetId,
            @RequestBody RetrievalDTO.TestReq req) {

        // 验证知识库权限
        validateKnowledgeBasePermission(datasetId);

        // 调用检索服务，返回强类型聚合对象
        RetrievalDTO.ResultVO result = knowledgeFilesService.retrievalTest(
                req.getQuestion(),
                req.getDatasetIds() != null && !req.getDatasetIds().isEmpty() ? req.getDatasetIds()
                        : java.util.Arrays.asList(datasetId),
                null,
                1,
                100,
                req.getSimilarityThreshold(),
                req.getVectorSimilarityWeight(),
                req.getTopK(),
                req.getRerankId(),
                req.getKeyword(),
                req.getHighlight(),
                null,
                null);

        return new Result<RetrievalDTO.ResultVO>().ok(result);
    }

    /**
     * 解析JSON字符串为Map对象
     */
    private Map<String, Object> parseJsonMap(String jsonString) {
        try {
            ObjectMapper objectMapper = new ObjectMapper();
            return objectMapper.readValue(jsonString, new TypeReference<Map<String, Object>>() {
            });
        } catch (Exception e) {
            throw new RuntimeException("解析JSON字符串失败: " + jsonString, e);
        }
    }
}