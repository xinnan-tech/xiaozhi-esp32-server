package xiaozhi.modules.device.service.impl;

import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;


import xiaozhi.common.utils.JsonRpcTwo;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.device.service.CameraStreamService;

import java.io.IOException;
import java.io.OutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.util.Base64;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Slf4j
@Service
@RequiredArgsConstructor
public class CameraStreamServiceImpl implements CameraStreamService {

    // 设备 -> 订阅者列表
    private final Map<String, CopyOnWriteArrayList<OutputStream>> subscribers = new ConcurrentHashMap<>();
    private final AtomicInteger rpcId = new AtomicInteger(1);
    private final StringRedisTemplate stringRedisTemplate;
    private final RedisMessageListenerContainer redisMessageListenerContainer;
    
    // 帧数据队列和定时器
    private final Map<String, BlockingQueue<byte[]>> frameQueues = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);

    // 采样保存：每个设备计数器（每帧保存一张，便于调试）
    private final Map<String, AtomicInteger> deviceFrameCounters = new ConcurrentHashMap<>();
    private static final int SAVE_EVERY_N_FRAMES = 1; // 改为每帧保存，便于调试
    private static final DateTimeFormatter TS_FMT = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS");

    @Override
    public void startStream(String deviceId, Integer fps, Integer quality) {
        // 通过已存在的 MCP 通道向设备下发 tools/call
        // 这里使用已有的 JsonRpcTwo 工具组装请求，实际发送应走你们的设备消息通道
        try {
            log.info("Starting camera stream for device: {}, fps: {}, quality: {}", deviceId, fps, quality);
            
            Map<String, Object> args = new HashMap<>();
            if (fps != null) args.put("fps", fps);
            if (quality != null) args.put("quality", quality);
            Map<String, Object> params = new HashMap<>();
            params.put("name", "self.camera.stream.start");
            params.put("arguments", args);
            var req = new JsonRpcTwo("tools/call", params, rpcId.getAndIncrement());
            JsonUtils.toJsonString(req); // 保留构造示例但不直接发送
            
            // 发布到 Redis，xiaozhi-server 订阅 camera:cmd:{deviceId}
            String redisChannel = "camera:cmd:" + deviceId;
            String message = JsonUtils.toJsonString(new HashMap<String, Object>() {{
                put("action", "start");
                if (fps != null) put("fps", fps);
                if (quality != null) put("quality", quality);
            }});
            
            log.info("Publishing to Redis channel: {}, message: {}", redisChannel, message);
            stringRedisTemplate.convertAndSend(redisChannel, message);
            log.info("Redis message published successfully");
            
        } catch (Exception e) {
            log.error("startStream failed", e);
        }
    }

    @Override
    public void stopStream(String deviceId) {
        try {
            log.info("Stopping camera stream for device: {}", deviceId);
            
            String redisChannel = "camera:cmd:" + deviceId;
            String message = JsonUtils.toJsonString(new HashMap<String, Object>() {{
                put("action", "stop");
            }});
            
            log.info("Publishing to Redis channel: {}, message: {}", redisChannel, message);
            stringRedisTemplate.convertAndSend(redisChannel, message);
            log.info("Redis stop message published successfully");
            
        } catch (Exception e) {
            log.error("stopStream failed", e);
        }
    }

    @Override
    public void openMjpegStream(String deviceId, OutputStream os) throws IOException {
        var list = subscribers.computeIfAbsent(deviceId, k -> new CopyOnWriteArrayList<>());
        list.add(os);
        
        // 为设备创建帧队列和定时器（如果还没有的话）
        frameQueues.computeIfAbsent(deviceId, k -> {
            var queue = new LinkedBlockingQueue<byte[]>(10); // 最多缓存10帧
            // 启动定时器，每100ms处理一次队列中的帧
            scheduler.scheduleAtFixedRate(() -> processFrameQueue(deviceId, queue), 0, 100, TimeUnit.MILLISECONDS);
            return queue;
        });
        
        // 懒订阅：首次有人看时，启动一个后台线程订阅 Redis 帧频道
        ensureFramesSubscription(deviceId);
    }

    @PreDestroy
    public void onShutdown() {
        subscribers.clear();
        scheduler.shutdown();
    }
    
    // 处理帧队列中的数据，写入到所有订阅者的 OutputStream
    private void processFrameQueue(String deviceId, BlockingQueue<byte[]> queue) {
        try {
            // 处理队列中的所有帧
            while (!queue.isEmpty()) {
                byte[] frameData = queue.poll();
                if (frameData != null) {
                    var list = subscribers.get(deviceId);
                    if (list != null && !list.isEmpty()) {
                        // 写入到所有订阅者
                        for (var os : list) {
                            try {
                                os.write(frameData);
                                os.flush();
                            } catch (IOException e) {
                                log.debug("OutputStream write failed for device: {}, removing subscriber", deviceId);
                                list.remove(os);
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.error("Error processing frame queue for device: {}", deviceId, e);
        }
    }

    // 供设备消息通道回调：当收到 {type:camera,event:frame,mime,image/jpeg,data:base64} 时调用
    public void onIncomingCameraFrame(String deviceId, String base64, OutputStream optionalSingleTarget) {
        byte[] jpeg;
        try {
            jpeg = Base64.getDecoder().decode(base64);
        } catch (IllegalArgumentException e) {
            log.warn("invalid base64 from {}", deviceId);
            return;
        }

        byte[] header = ("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + jpeg.length + "\r\n\r\n").getBytes();
        byte[] tail = "\r\n".getBytes();

        // 采样保存到本地，便于验证服务端是否收到帧
        try {
            var counter = deviceFrameCounters.computeIfAbsent(deviceId, k -> new AtomicInteger(0));
            int c = counter.incrementAndGet();
            if (c % SAVE_EVERY_N_FRAMES == 0) {
                // Windows 不允许文件名包含冒号，替换为下划线
                String safeDeviceId = deviceId.replace(":", "_");
                String dirPath = "camera_frames" + File.separator + safeDeviceId;
                File dir = new File(dirPath);
                if (!dir.exists()) {
                    // 尝试创建目录
                    if (!dir.mkdirs() && !dir.exists()) {
                        log.warn("failed to create directory for frames: {}", dirPath);
                    }
                }
                String ts = LocalDateTime.now().format(TS_FMT);
                File out = new File(dir, ts + ".jpg");
                try (FileOutputStream fos = new FileOutputStream(out)) {
                    fos.write(jpeg);
                }
                log.info("saved camera frame: device={}, path={}, bytes={}, count={}", 
                        deviceId, out.getAbsolutePath(), jpeg.length, c);
            }
        } catch (Exception saveEx) {
            log.warn("save frame failed for {}: {}", deviceId, saveEx.toString());
        }

        if (optionalSingleTarget != null) {
            try {
                optionalSingleTarget.write(header);
                optionalSingleTarget.write(jpeg);
                optionalSingleTarget.write(tail);
                optionalSingleTarget.flush();
            } catch (IOException ignored) {}
            return;
        }

        // 将帧数据放入队列，由定时器处理写入
        var queue = frameQueues.get(deviceId);
        if (queue != null) {
            // 创建完整的 MJPEG 帧数据
            byte[] frameData = new byte[header.length + jpeg.length + tail.length];
            System.arraycopy(header, 0, frameData, 0, header.length);
            System.arraycopy(jpeg, 0, frameData, header.length, jpeg.length);
            System.arraycopy(tail, 0, frameData, header.length + jpeg.length, tail.length);
            
            // 非阻塞方式添加到队列，如果队列满了就丢弃旧帧
            if (!queue.offer(frameData)) {
                // 队列满了，移除一个旧帧，然后添加新帧
                queue.poll();
                queue.offer(frameData);
            }
        }
    }

    // 使用 Spring Redis 的 MessageListenerContainer 进行更稳定的订阅
    private final Map<String, Boolean> framesSubStarted = new ConcurrentHashMap<>();
    private void ensureFramesSubscription(String deviceId) {
        if (framesSubStarted.putIfAbsent(deviceId, true) != null) return;
        
        try {
            // 使用 Spring Redis 的 MessageListenerContainer 进行订阅
            String channel = "camera:frames:" + deviceId;
            ChannelTopic topic = new ChannelTopic(channel);
            
            // 创建简单的消息监听器，避免 MessageListenerAdapter 的复杂配置
            var listener = new org.springframework.data.redis.listener.adapter.MessageListenerAdapter() {
                @Override
                public void onMessage(org.springframework.data.redis.connection.Message message, byte[] pattern) {
                    try {
                        String messageBody = new String(message.getBody());
                        String channelName = new String(message.getChannel());
                        log.debug("Received frame from Redis channel: {}, message length: {}", channelName, messageBody.length());
                        
                        // 从 channel 中提取设备 ID
                        String deviceIdFromChannel = channelName.replace("camera:frames:", "");
                        onIncomingCameraFrame(deviceIdFromChannel, messageBody, null);
                    } catch (Exception e) {
                        log.error("Error processing Redis message for device: {}", deviceId, e);
                    }
                }
            };
            
            redisMessageListenerContainer.addMessageListener(listener, topic);
            log.info("Started Redis subscription for device: {} on channel: {}", deviceId, channel);
            
        } catch (Exception e) {
            log.error("Failed to start Redis subscription for device: {}", deviceId, e);
            framesSubStarted.remove(deviceId);
        }
    }
    
    // 移除这个方法，因为不再需要
    // public void handleRedisMessage(String message, String channel) { ... }
}


