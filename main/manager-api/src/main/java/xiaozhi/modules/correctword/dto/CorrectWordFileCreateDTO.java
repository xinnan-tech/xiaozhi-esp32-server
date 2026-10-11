package xiaozhi.modules.correctword.dto;

import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

@Data
@Schema(description = "Create replacement word file DTO")
public class CorrectWordFileCreateDTO {

    @NotBlank(message = "File name cannot be empty")
    @Schema(description = "File name")
    private String fileName;

    @NotEmpty(message = "Replacement word content cannot be empty")
    @Schema(description = "Replacement word content, format per line: original|replacement")
    private List<String> content;

    @Schema(description = "File size (bytes), must not exceed 1MB")
    private Long fileSize;
}
