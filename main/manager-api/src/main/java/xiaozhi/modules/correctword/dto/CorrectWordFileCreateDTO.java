package xiaozhi.modules.correctword.dto;

import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

@Data
@Schema(description = "创建替换词文件DTO")
public class CorrectWordFileCreateDTO {

    @NotBlank(message = "文件名不能为空")
    @Schema(description = "文件名")
    private String fileName;

    @NotEmpty(message = "替换词内容不能为空")
    @Schema(description = "替换词内容，每条格式：原词|替换词")
    private List<String> content;

    @Schema(description = "文件大小（字节），不能超过1MB")
    private Long fileSize;
}
