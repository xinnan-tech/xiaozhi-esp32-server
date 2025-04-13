package xiaozhi.modules.device.controller;

import java.nio.charset.StandardCharsets;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.SneakyThrows;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.device.utils.NetworkUtil;

@Tag(name = "设备管理", description = "OTA 相关接口")
@RestController
@RequiredArgsConstructor
@RequestMapping("/ota/")
public class OTAController {
    private final DeviceService deviceService;

    @Operation(summary = "检查 OTA 版本和设备激活状态")
    @PostMapping
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
    @GetMapping
    public ResponseEntity<String> getOTAPrompt() {
        return createResponse(DeviceReportRespDTO.createError("请提交正确的ota参数"));
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
