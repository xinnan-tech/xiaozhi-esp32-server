package xiaozhi.modules.device.controller;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.SneakyThrows;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.OtaEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.device.service.OtaService;
import xiaozhi.modules.device.utils.NetworkUtil;
import xiaozhi.common.constant.Constant;
import io.swagger.v3.oas.annotations.Parameters;
import xiaozhi.common.validator.ValidatorUtils;

@Tag(name = "固件管理", description = "OTA固件管理接口")
@RestController
@RequiredArgsConstructor
@RequestMapping("/ota")
public class OTAController {
    private static final Logger logger = LoggerFactory.getLogger(OTAController.class);
    private final DeviceService deviceService;
    private final OtaService otaService;

    @GetMapping("/otas")
    @Operation(summary = "分页查询 OTA 固件信息")
    @Parameters({
        @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
        @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true)
    })
    public Result<PageData<OtaEntity>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        ValidatorUtils.validateEntity(params);
        PageData<OtaEntity> page = otaService.page(params);
        return new Result<PageData<OtaEntity>>().ok(page);
    }

    @GetMapping("{id}")
    @Operation(summary = "信息 OTA 固件信息")
    public Result<OtaEntity> get(@PathVariable("id") String id) {
        OtaEntity data = otaService.getById(id);
        return new Result<OtaEntity>().ok(data);
    }

    @PostMapping
    @Operation(summary = "保存 OTA 固件信息")
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

    @PutMapping("/{id}")    
    @Operation(summary = "修改 OTA 固件信息")
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

    @DeleteMapping("/{id}")
    @Operation(summary = "OTA 删除")
    public Result<Void> delete(@PathVariable("id") String[] ids) {
        if (ids == null || ids.length == 0) {
            return new Result<Void>().error("删除的固件ID不能为空");
        }
        otaService.delete(ids);
        return new Result<Void>();
    }

    @Operation(summary = "检查 OTA 版本和设备激活状态")
    @PostMapping("check")
    public ResponseEntity<String> checkOTAVersion(
            @RequestBody DeviceReportReqDTO deviceReportReqDTO,
            @Parameter(name = "Device-Id", description = "设备唯一标识", required = true, in = ParameterIn.HEADER) @RequestHeader("Device-Id") String deviceId,
            @Parameter(name = "Client-Id", description = "客户端标识", required = true, in = ParameterIn.HEADER) @RequestHeader("Client-Id") String clientId) {
        if (StringUtils.isAnyBlank(deviceId, clientId)) {
            return createResponse(DeviceReportRespDTO.createError("Device ID is required"));
        }
        String macAddress = deviceReportReqDTO.getMacAddress();
        boolean macAddressValid = NetworkUtil.isMacAddressValid(macAddress);
        // 设备Id和Mac地址应是一致的, 并且必须需要application字段
        if (!deviceId.equals(macAddress) || !macAddressValid || deviceReportReqDTO.getApplication() == null) {
            return createResponse(DeviceReportRespDTO.createError("Invalid OTA request"));
        }
        return createResponse(deviceService.checkDeviceActive(macAddress, deviceId, clientId, deviceReportReqDTO));
    }

    @Operation(summary = "获取 OTA 提示信息")
    @GetMapping("prompt")
    public ResponseEntity<String> getOTAPrompt() {
        return createResponse(DeviceReportRespDTO.createError("请提交正确的ota参数"));
    }

    @GetMapping("/download/{id}")
    @Operation(summary = "下载固件文件")
    public ResponseEntity<byte[]> downloadFirmware(@PathVariable("id") String id) {
        try {
            // 获取固件信息
            OtaEntity otaEntity = otaService.getById(id);
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
            String originalFilename = otaEntity.getFirmwareName() + "_" + otaEntity.getVersion();
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
    public Result<String> uploadFirmware(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return new Result<String>().error("上传文件不能为空");
        }

        try {
            // 获取文件名
            String originalFilename = file.getOriginalFilename();
            // 生成唯一的文件名
            String uniqueFileName = UUID.randomUUID().toString() + "_" + originalFilename;
            // 设置存储路径
            String uploadDir = "firmware";
            Path uploadPath = Paths.get(uploadDir);
            System.out.println(uploadPath);
            
            // 如果目录不存在，创建目录
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }
            
            // 完整的文件路径
            Path filePath = uploadPath.resolve(uniqueFileName);
            
            // 保存文件
            Files.copy(file.getInputStream(), filePath);
            
            // 返回文件路径
            return new Result<String>().ok(filePath.toString());
        } catch (IOException e) {
            return new Result<String>().error("文件上传失败：" + e.getMessage());
        }
    }

    @SneakyThrows
    private ResponseEntity<String> createResponse(DeviceReportRespDTO deviceReportRespDTO) {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        String json = objectMapper.writeValueAsString(deviceReportRespDTO);
        byte[] jsonBytes = json.getBytes(StandardCharsets.UTF_8);
        return ResponseEntity
                .ok()
                .contentType(MediaType.APPLICATION_JSON)
                .contentLength(jsonBytes.length)
                .body(json);
    }
}
