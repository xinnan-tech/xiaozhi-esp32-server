package xiaozhi.modules.correctword.controller;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.correctword.dto.CorrectWordFileCreateDTO;
import xiaozhi.modules.correctword.service.CorrectWordFileService;
import xiaozhi.modules.correctword.vo.CorrectWordFileVO;

@RestController
@RequestMapping("/correct-word")
@Tag(name = "替换词管理")
@AllArgsConstructor
public class CorrectWordController {

    private final CorrectWordFileService correctWordFileService;

    @PostMapping("/file")
    @Operation(summary = "创建替换词文件")
    @RequiresPermissions("sys:role:normal")
    public Result<CorrectWordFileVO> createFile(@Valid @RequestBody CorrectWordFileCreateDTO dto) {
        CorrectWordFileVO vo = correctWordFileService.createFile(dto);
        return new Result<CorrectWordFileVO>().ok(vo);
    }

    @PutMapping("/file/{fileId}")
    @Operation(summary = "修改替换词文件")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> updateFile(@PathVariable String fileId, @Valid @RequestBody CorrectWordFileCreateDTO dto) {
        correctWordFileService.updateFile(fileId, dto);
        return new Result<>();
    }

    @GetMapping("/file/list")
    @Operation(summary = "分页获取当前用户替换词文件列表")
    @RequiresPermissions("sys:role:normal")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true),
    })
    public Result<PageData<CorrectWordFileVO>> listFiles(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        PageData<CorrectWordFileVO> page = correctWordFileService.listFiles(params);
        return new Result<PageData<CorrectWordFileVO>>().ok(page);
    }

    @GetMapping("/file/select")
    @Operation(summary = "智能体获取当前用户替换词文件列表")
    @RequiresPermissions("sys:role:normal")
    public Result<List<CorrectWordFileVO>> listAllFiles() {
        List<CorrectWordFileVO> list = correctWordFileService.listAllFiles();
        return new Result<List<CorrectWordFileVO>>().ok(list);
    }

    @GetMapping("/file/download/{fileId}")
    @Operation(summary = "下载替换词文件")
    @RequiresPermissions("sys:role:normal")
    public ResponseEntity<byte[]> downloadFile(@PathVariable String fileId) {
        CorrectWordFileVO vo = correctWordFileService.getFileContent(fileId);
        if (vo == null || vo.getContent() == null || vo.getContent().isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        byte[] bytes = String.join("\n", vo.getContent()).getBytes(StandardCharsets.UTF_8);
        String encodedFileName = URLEncoder.encode(vo.getFileName(), StandardCharsets.UTF_8).replace("+", "%20");
        String asciiFileName = vo.getFileName().replaceAll("[^\\x00-\\x7F]", "_");
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + asciiFileName + "\"; filename*=UTF-8''" + encodedFileName)
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(bytes);
    }

    @DeleteMapping("/file/{fileId}")
    @Operation(summary = "删除替换词文件")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> deleteFile(@PathVariable String fileId) {
        correctWordFileService.deleteFile(fileId);
        return new Result<>();
    }

    @PostMapping("/file/batch-delete")
    @Operation(summary = "批量删除替换词文件")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> batchDeleteFiles(@RequestBody List<String> fileIds) {
        if (fileIds == null || fileIds.isEmpty()) {
            return new Result<>();
        }
        correctWordFileService.batchDeleteFiles(fileIds);
        return new Result<>();
    }
}
