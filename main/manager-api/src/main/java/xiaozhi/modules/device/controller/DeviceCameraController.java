package xiaozhi.modules.device.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.CameraStreamStartDTO;
import xiaozhi.modules.device.service.CameraStreamService;

import java.io.IOException;

@Tag(name = "设备摄像头")
@RestController
@RequiredArgsConstructor
@RequestMapping("/device/camera")
public class DeviceCameraController {

    private final CameraStreamService cameraStreamService;

    @Operation(summary = "启动设备摄像头推流")
    @PostMapping("/{deviceId}/start")
    public Result<Boolean> start(@PathVariable String deviceId, 
                                 @RequestBody(required = false) CameraStreamStartDTO body,
                                 HttpServletRequest request) {
        Integer fps = body != null ? body.getFps() : null;
        Integer quality = body != null ? body.getQuality() : null;
        cameraStreamService.startStream(deviceId, fps, quality);
        return new Result<Boolean>().ok(true);
    }

    @Operation(summary = "停止设备摄像头推流")
    @PostMapping("/{deviceId}/stop")
    public Result<Boolean> stop(@PathVariable String deviceId,
                                HttpServletRequest request) {
        cameraStreamService.stopStream(deviceId);
        return new Result<Boolean>().ok(true);
    }

    @Operation(summary = "获取设备摄像头MJPEG流")
    @GetMapping(value = "/{deviceId}/stream", produces = MediaType.MULTIPART_MIXED_VALUE)
    public void stream(@PathVariable String deviceId, 
                       HttpServletRequest request,
                       HttpServletResponse resp) throws IOException {
        // 调试日志
        System.out.println("=== DeviceCamera stream method called ===");
        System.out.println("Device ID: " + deviceId);
        System.out.println("Request URL: " + request.getRequestURL());
        System.out.println("Request URI: " + request.getRequestURI());
        System.out.println("Authorization header: " + request.getHeader("Authorization"));

        resp.setStatus(200);
        resp.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
        resp.setHeader("Pragma", "no-cache");
        resp.setHeader("Connection", "close");
        resp.setContentType("multipart/x-mixed-replace; boundary=frame");
        cameraStreamService.openMjpegStream(deviceId, resp.getOutputStream());
        // 注意：保持连接直到客户端关闭，由下层写入帧
    }
}


