package xiaozhi.modules.device.controller;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.UUID;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
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
import org.springframework.web.multipart.MultipartFile;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.device.entity.OtaEntity;
import xiaozhi.modules.device.service.OtaService;

@Tag(name = "设备管理", description = "OTA 相关接口")
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/otaMag")
public class OTAMagController {
    private static final Logger logger = LoggerFactory.getLogger(OTAController.class);
    private final OtaService otaService;
    private final RedisUtils redisUtils;

    @GetMapping
    @Operation(summary = "分页查询 OTA 固件信息")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true)
    })
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<OtaEntity>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        ValidatorUtils.validateEntity(params);
        PageData<OtaEntity> page = otaService.page(params);
        return new Result<PageData<OtaEntity>>().ok(page);
    }

    @GetMapping("{id}")
    @Operation(summary = "信息 OTA 固件信息")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<OtaEntity> get(@PathVariable("id") String id) {
        OtaEntity data = otaService.selectById(id);
        return new Result<OtaEntity>().ok(data);
    }

    @PostMapping
    @Operation(summary = "保存 OTA 固件信息")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> save(@RequestBody OtaEntity entity) {
        if (entity == null) {
            return new Result<Void>().error("固件信息不能为空");
        }
        if (StringUtils.isBlank(entity.getFirmwareName())) {
            return new Result<Void>().error("固件名称不能为空");
        }
        if (StringUtils.isBlank(entity.getType())) {
            return new Result<Void>().error("固件类型不能为空");
        }
        if (StringUtils.isBlank(entity.getVersion())) {
            return new Result<Void>().error("版本号不能为空");
        }
        try {
            otaService.save(entity);
            return new Result<Void>();
        } catch (RuntimeException e) {
            return new Result<Void>().error(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "OTA 删除")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> delete(@PathVariable("id") String[] ids) {
        if (ids == null || ids.length == 0) {
            return new Result<Void>().error("删除的固件ID不能为空");
        }
        otaService.delete(ids);
        return new Result<Void>();
    }

    @PutMapping("/{id}")
    @Operation(summary = "修改 OTA 固件信息")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<?> update(@PathVariable("id") String id, @RequestBody OtaEntity entity) {
        if (entity == null) {
            return new Result<>().error("固件信息不能为空");
        }
        entity.setId(id);
        try {
            otaService.update(entity);
            return new Result<>();
        } catch (RuntimeException e) {
            return new Result<>().error(e.getMessage());
        }
    }

    @GetMapping("/getDownloadUrl/{id}")
    @Operation(summary = "获取 OTA 固件下载链接")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<String> getDownloadUrl(@PathVariable("id") String id) {
        String uuid = UUID.randomUUID().toString();
        redisUtils.set(RedisKeys.getOtaIdKey(uuid), id);
        return new Result<String>().ok(uuid);
    }

    @GetMapping("/download/{uuid}")
    @Operation(summary = "下载固件文件")
    public ResponseEntity<byte[]> downloadFirmware(@PathVariable("uuid") String uuid) {
        String id = (String) redisUtils.get(RedisKeys.getOtaIdKey(uuid));
        if (StringUtils.isBlank(id)) {
            return ResponseEntity.notFound().build();
        }

        // 检查下载次数
        String downloadCountKey = RedisKeys.getOtaDownloadCountKey(uuid);
        Integer downloadCount = (Integer) redisUtils.get(downloadCountKey);
        if (downloadCount == null) {
            downloadCount = 0;
        }

        // 如果下载次数超过3次，返回404
        if (downloadCount >= 3) {
            redisUtils.delete(downloadCountKey);
            redisUtils.delete(RedisKeys.getOtaIdKey(uuid));
            logger.warn("Download limit exceeded for UUID: {}", uuid);
            return ResponseEntity.notFound().build();
        }

        redisUtils.set(downloadCountKey, downloadCount + 1);

        try {
            // 获取固件信息
            OtaEntity otaEntity = otaService.selectById(id);
            if (otaEntity == null || StringUtils.isBlank(otaEntity.getFirmwarePath())) {
                logger.warn("Firmware not found or path is empty for ID: {}", id);
                return ResponseEntity.notFound().build();
            }

            // 获取文件路径 - 确保路径是绝对路径或正确的相对路径
            String firmwarePath = otaEntity.getFirmwarePath();
            Path path;

            // 检查是否是绝对路径
            if (Paths.get(firmwarePath).isAbsolute()) {
                path = Paths.get(firmwarePath);
            } else {
                // 如果是相对路径，则从当前工作目录解析
                path = Paths.get(System.getProperty("user.dir"), firmwarePath);
            }

            logger.info("Attempting to download firmware for ID: {}, DB path: {}, resolved path: {}",
                    id, firmwarePath, path.toAbsolutePath());

            if (!Files.exists(path) || !Files.isRegularFile(path)) {
                // 尝试直接从firmware目录下查找文件名
                String fileName = new File(firmwarePath).getName();
                Path altPath = Paths.get(System.getProperty("user.dir"), "firmware", fileName);

                logger.info("File not found at primary path, trying alternative path: {}", altPath.toAbsolutePath());

                if (Files.exists(altPath) && Files.isRegularFile(altPath)) {
                    path = altPath;
                } else {
                    logger.error("Firmware file not found at either path: {} or {}",
                            path.toAbsolutePath(), altPath.toAbsolutePath());
                    return ResponseEntity.notFound().build();
                }
            }

            // 读取文件内容
            byte[] fileContent = Files.readAllBytes(path);

            // 设置响应头
            String originalFilename = otaEntity.getType() + "_" + otaEntity.getVersion();
            if (firmwarePath.contains(".")) {
                String extension = firmwarePath.substring(firmwarePath.lastIndexOf("."));
                originalFilename += extension;
            }

            // 清理文件名，移除不安全字符
            String safeFilename = originalFilename.replaceAll("[^a-zA-Z0-9._-]", "_");

            logger.info("Providing download for firmware ID: {}, filename: {}, size: {} bytes",
                    id, safeFilename, fileContent.length);

            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + safeFilename + "\"")
                    .body(fileContent);
        } catch (IOException e) {
            logger.error("Error reading firmware file for ID: {}", id, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        } catch (Exception e) {
            logger.error("Unexpected error during firmware download for ID: {}", id, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @PostMapping("/upload")
    @Operation(summary = "上传固件文件")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<String> uploadFirmware(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return new Result<String>().error("上传文件不能为空");
        }

        // 检查文件扩展名
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null) {
            return new Result<String>().error("文件名不能为空");
        }

        String extension = originalFilename.substring(originalFilename.lastIndexOf(".")).toLowerCase();
        if (!extension.equals(".bin") && !extension.equals(".apk")) {
            return new Result<String>().error("只允许上传.bin和.apk格式的文件");
        }

        try {
            // 计算文件的MD5值
            String md5 = calculateMD5(file);

            // 设置存储路径
            String uploadDir = "uploadfile";
            Path uploadPath = Paths.get(uploadDir);

            // 如果目录不存在，创建目录
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }

            // 使用MD5作为文件名，固定使用.bin扩展名
            String uniqueFileName = md5 + extension;
            Path filePath = uploadPath.resolve(uniqueFileName);

            // 检查文件是否已存在
            if (Files.exists(filePath)) {
                return new Result<String>().ok(filePath.toString());
            }

            // 保存文件
            Files.copy(file.getInputStream(), filePath);

            // 返回文件路径
            return new Result<String>().ok(filePath.toString());
        } catch (IOException | NoSuchAlgorithmException e) {
            return new Result<String>().error("文件上传失败：" + e.getMessage());
        }
    }

    private String calculateMD5(MultipartFile file) throws IOException, NoSuchAlgorithmException {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] digest = md.digest(file.getBytes());
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
