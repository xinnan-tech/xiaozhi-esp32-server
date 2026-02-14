package xiaozhi.modules.knowledge.dto.file;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;
import org.springframework.web.multipart.MultipartFile;

/**
 * 文件管理聚合 DTO
 * <p>
 * 容器类，内含文件模块所有请求/响应对象的静态内部类定义。
 * </p>
 */
@Schema(description = "文件管理聚合 DTO")
public class FileDTO {

    // ========== 请求类 ==========

    /**
     * 文件上传请求 (对应接口 1: upload)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "文件上传请求")
    public static class UploadReq implements Serializable {

        @NotNull(message = "文件不能为空")
        @Schema(description = "上传的文件", requiredMode = Schema.RequiredMode.REQUIRED)
        private MultipartFile file;

        @Schema(description = "父文件夹 ID (为空则上传到根目录)", example = "folder_001")
        @JsonProperty("parent_id")
        private String parentId;
    }

    /**
     * 新建文件夹请求 (对应接口 2: create)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "新建文件夹请求")
    public static class CreateReq implements Serializable {

        @NotBlank(message = "文件夹名称不能为空")
        @Schema(description = "文件夹名称", requiredMode = Schema.RequiredMode.REQUIRED, example = "新建文件夹")
        private String name;

        @Schema(description = "父文件夹 ID (为空则创建在根目录)", example = "folder_001")
        @JsonProperty("parent_id")
        private String parentId;

        @NotBlank(message = "类型不能为空")
        @Schema(description = "类型: FOLDER", requiredMode = Schema.RequiredMode.REQUIRED, example = "FOLDER")
        @Builder.Default
        private String type = "FOLDER";
    }

    /**
     * 重命名请求 (对应接口 6: rename)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "重命名请求")
    public static class RenameReq implements Serializable {

        @NotBlank(message = "文件 ID 不能为空")
        @Schema(description = "文件/文件夹 ID", requiredMode = Schema.RequiredMode.REQUIRED, example = "file_001")
        @JsonProperty("file_id")
        private String fileId;

        @NotBlank(message = "新名称不能为空")
        @Schema(description = "新名称", requiredMode = Schema.RequiredMode.REQUIRED, example = "重命名后的文件")
        private String name;
    }

    /**
     * 移动请求 (对应接口 7: move)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "移动请求")
    public static class MoveReq implements Serializable {

        @NotEmpty(message = "源文件 ID 列表不能为空")
        @Schema(description = "源文件/文件夹 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED, example = "[\"file_001\", \"file_002\"]")
        @JsonProperty("src_file_ids")
        private List<String> srcFileIds;

        @NotBlank(message = "目标文件夹 ID 不能为空")
        @Schema(description = "目标文件夹 ID", requiredMode = Schema.RequiredMode.REQUIRED, example = "folder_002")
        @JsonProperty("dest_file_id")
        private String destFileId;
    }

    /**
     * 批量删除请求 (对应接口 8: rm)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "批量删除请求")
    public static class RemoveReq implements Serializable {

        @NotEmpty(message = "文件 ID 列表不能为空")
        @Schema(description = "文件/文件夹 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED, example = "[\"file_001\", \"file_002\"]")
        @JsonProperty("file_ids")
        private List<String> fileIds;
    }

    /**
     * 导入知识库请求 (对应接口 9: convert)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "导入知识库请求")
    public static class ConvertReq implements Serializable {

        @NotEmpty(message = "文件 ID 列表不能为空")
        @Schema(description = "文件 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED, example = "[\"file_001\", \"file_002\"]")
        @JsonProperty("file_ids")
        private List<String> fileIds;

        @NotEmpty(message = "知识库 ID 列表不能为空")
        @Schema(description = "目标知识库 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED, example = "[\"kb_001\"]")
        @JsonProperty("kb_ids")
        private List<String> kbIds;
    }

    /**
     * 列表查询请求 (对应接口 3: list_files)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "列表查询请求")
    public static class ListReq implements Serializable {

        @Schema(description = "父文件夹 ID (为空则查询根目录)", example = "folder_001")
        @JsonProperty("parent_id")
        private String parentId;

        @Schema(description = "关键词搜索", example = "文档")
        private String keywords;

        @Schema(description = "页码 (从 1 开始)", example = "1")
        private Integer page;

        @Schema(description = "每页数量", example = "30")
        @JsonProperty("page_size")
        private Integer pageSize;

        @Schema(description = "排序字段: create_time / update_time / name / size", example = "create_time")
        private String orderby;

        @Schema(description = "是否降序", example = "true")
        private Boolean desc;
    }

    // ========== 响应类 ==========

    /**
     * 文件/文件夹基础信息 VO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "文件/文件夹基础信息")
    public static class InfoVO implements Serializable {

        @Schema(description = "文件/文件夹 ID", example = "file_001")
        private String id;

        @Schema(description = "父文件夹 ID", example = "folder_001")
        @JsonProperty("parent_id")
        private String parentId;

        @Schema(description = "租户 ID", example = "tenant_001")
        @JsonProperty("tenant_id")
        private String tenantId;

        @Schema(description = "创建者 ID", example = "user_001")
        @JsonProperty("created_by")
        private String createdBy;

        @Schema(description = "类型: FOLDER / FILE", example = "FOLDER")
        private String type;

        @Schema(description = "名称", example = "我的文件夹")
        private String name;

        @Schema(description = "路径位置", example = "/root/folder")
        private String location;

        @Schema(description = "文件大小 (字节)", example = "1024")
        private Long size;

        @Schema(description = "来源类型", example = "local")
        @JsonProperty("source_type")
        private String sourceType;

        @Schema(description = "创建时间 (时间戳)", example = "1700000000000")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "创建日期 (格式化)", example = "2024-01-15 10:30:00")
        @JsonProperty("create_date")
        private String createDate;

        @Schema(description = "更新时间 (时间戳)", example = "1700000001000")
        @JsonProperty("update_time")
        private Long updateTime;

        @Schema(description = "更新日期 (格式化)", example = "2024-01-15 11:00:00")
        @JsonProperty("update_date")
        private String updateDate;

        @Schema(description = "文件扩展名", example = "pdf")
        private String extension;
    }

    /**
     * 列表响应 VO (对应接口 3: list_files)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "文件列表响应")
    public static class ListVO implements Serializable {

        @Schema(description = "总记录数", example = "100")
        private Long total;

        @Schema(description = "当前父文件夹信息")
        @JsonProperty("parent_folder")
        private InfoVO parentFolder;

        @Schema(description = "文件/文件夹列表")
        private List<InfoVO> files;

        @Schema(description = "面包屑导航路径")
        private List<InfoVO> breadcrumb;
    }

    /**
     * 转换结果项 VO (对应接口 9: convert)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "文件转换结果项")
    public static class ConvertVO implements Serializable {

        @Schema(description = "转换记录 ID", example = "convert_001")
        private String id;

        @Schema(description = "源文件 ID", example = "file_001")
        @JsonProperty("file_id")
        private String fileId;

        @Schema(description = "目标文档 ID", example = "doc_001")
        @JsonProperty("document_id")
        private String documentId;

        @Schema(description = "创建时间 (时间戳)", example = "1700000000000")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "创建日期 (格式化)", example = "2024-01-15 10:30:00")
        @JsonProperty("create_date")
        private String createDate;

        @Schema(description = "更新时间 (时间戳)", example = "1700000001000")
        @JsonProperty("update_time")
        private Long updateTime;

        @Schema(description = "更新日期 (格式化)", example = "2024-01-15 11:00:00")
        @JsonProperty("update_date")
        private String updateDate;
    }

    /**
     * 转换状态 VO (对应接口 10: get_convert_status)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "文件转换状态")
    public static class ConvertStatusVO implements Serializable {

        @Schema(description = "转换状态: pending / processing / completed / failed", example = "completed")
        private String status;

        @Schema(description = "转换进度 (0.0 - 1.0)", example = "1.0")
        private Float progress;

        @Schema(description = "状态消息", example = "转换完成")
        private String message;
    }

    /**
     * 面包屑 VO (对应接口 12: all_parent_folder)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "面包屑导航 (所有父文件夹)")
    public static class BreadcrumbVO implements Serializable {

        @Schema(description = "父文件夹列表 (从根到当前的路径)")
        @JsonProperty("parent_folders")
        private List<InfoVO> parentFolders;
    }

    /**
     * 根目录信息 VO (对应接口 10: get_root_folder)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "根目录信息")
    public static class RootFolderVO implements Serializable {

        @Schema(description = "根文件夹信息")
        @JsonProperty("root_folder")
        private InfoVO rootFolder;
    }

    /**
     * 父目录信息 VO (对应接口 11: get_parent_folder)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "父目录信息")
    public static class ParentFolderVO implements Serializable {

        @Schema(description = "父文件夹信息")
        @JsonProperty("parent_folder")
        private InfoVO parentFolder;
    }
}
