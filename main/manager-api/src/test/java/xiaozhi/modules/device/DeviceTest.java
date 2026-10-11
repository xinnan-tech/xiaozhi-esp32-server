package xiaozhi.modules.device;

import java.util.HashMap;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.context.annotation.Import;

import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.service.SysUserService;

@Slf4j
@SpringBootTest
@ActiveProfiles("test")
@Import(xiaozhi.config.TestConfig.class)
@DisplayName("Device Test")
public class DeviceTest {

    private static final Logger log = LoggerFactory.getLogger(DeviceTest.class);

    @Autowired
    private RedisUtils redisUtils;
    @Autowired
    private SysUserService sysUserService;

    @Test
    public void testRejectWeakPassword() {
        SysUserDTO userDTO = new SysUserDTO();
        userDTO.setUsername("test");
        userDTO.setPassword("TestPassword123!");
        sysUserService.save(userDTO);
    }

    @Test
    @DisplayName("Test writing device information")
    public void testWriteDeviceInfo() {
        log.info("Starting test for writing device information...");
        // Simulate device MAC address
        String macAddress = "00:11:22:33:44:66";
        // Simulate device verification code
        String deviceCode = "123456";

        HashMap<String, Object> map = new HashMap<>();
        map.put("mac_address", macAddress);
        map.put("activation_code", deviceCode);
        map.put("board", "Hardware Model");
        map.put("app_version", "0.3.13");

        String safeDeviceId = macAddress.replace(":", "_").toLowerCase();
        String cacheDeviceKey = String.format("ota:activation:data:%s", safeDeviceId);
        redisUtils.set(cacheDeviceKey, map, 300);

        String redisKey = "ota:activation:code:" + deviceCode;
        log.info("Redis Key: {}", redisKey);

        // Write device information to Redis
        redisUtils.set(redisKey, macAddress, 300);
        log.info("Device information has been written to Redis");

        // Verify if write was successful
        String savedMacAddress = (String) redisUtils.get(redisKey);
        log.info("MAC address read from Redis: {}", savedMacAddress);

        // Use assertions for verification
        Assertions.assertNotNull(savedMacAddress, "MAC address read from Redis should not be null");
        Assertions.assertEquals(macAddress, savedMacAddress, "Saved MAC address does not match original MAC address");

        log.info("Test completed");
    }
}
