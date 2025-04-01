package xiaozhi.modules.device;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;

@Slf4j
@SpringBootTest
@ActiveProfiles("dev")
@DisplayName("设备测试")
public class DeviceTest {

    @Autowired
    private RedisUtils redisUtils;

    @Test
    @DisplayName("测试写入设备信息")
    public void testWriteDeviceInfo() {
        log.info("开始测试写入设备信息...");

        // 模拟设备MAC地址
        String macAddress = "00:11:22:33:44:55";
        // 模拟设备验证码
        String deviceCode = "123456";

        String redisKey = RedisKeys.getDeviceCaptchaKey(deviceCode);
        log.info("Redis Key: {}", redisKey);

        // 将设备信息写入Redis
        redisUtils.set(redisKey, macAddress, 300);
        log.info("设备信息已写入Redis");

        // 验证是否写入成功
        String savedMacAddress = (String) redisUtils.get(redisKey);
        log.info("从Redis读取的MAC地址: {}", savedMacAddress);

        // 使用断言验证
        Assertions.assertNotNull(savedMacAddress, "从Redis读取的MAC地址不应为空");
        Assertions.assertEquals(macAddress, savedMacAddress, "保存的MAC地址与原始MAC地址不匹配");

        log.info("测试完成");
    }
}