package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.time.ZoneId;
import java.util.Date;
import java.util.List;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;
import xiaozhi.modules.security.config.WebMvcConfig;

@DisplayName("设备时间序列化回归测试")
class DeviceTimeSerializationTest {

    @ParameterizedTest(name = "浏览器时区 {0}")
    @ValueSource(strings = { "Asia/Shanghai", "America/Sao_Paulo" })
    @DisplayName("#3280 绑定时间和最后连接时间在任意浏览器时区都表示同一时刻")
    void serializedDeviceTimesDescribeTheSameInstantAcrossBrowserTimeZones(String browserTimeZone) {
        Instant connectedAt = Instant.parse("2026-07-10T13:21:42Z");
        DeviceEntity entity = new DeviceEntity();
        entity.setCreateDate(Date.from(connectedAt));
        entity.setLastConnectedAt(Date.from(connectedAt));

        DeviceServiceImpl deviceService = serviceReturning(entity);
        UserShowDeviceListVO device = deviceService.getUserDeviceList(1L, "agent-id").getFirst();

        ObjectMapper objectMapper = new WebMvcConfig().jackson2HttpMessageConverter().getObjectMapper();
        JsonNode payload = objectMapper.valueToTree(device);
        Instant createDate = Instant.ofEpochMilli(
                Long.parseLong(payload.path("createDateTimestamp").asText()));
        Instant lastConnectedAt = Instant.ofEpochMilli(
                Long.parseLong(payload.path("lastConnectedAtTimestamp").asText()));
        ZoneId browserZone = ZoneId.of(browserTimeZone);

        assertAll(
                () -> assertTrue(payload.path("createDateTimestamp").isTextual(),
                        "Long 时间戳必须遵循现有 JSON 契约序列化为字符串"),
                () -> assertTrue(payload.path("lastConnectedAtTimestamp").isTextual(),
                        "Long 时间戳必须遵循现有 JSON 契约序列化为字符串"),
                () -> assertEquals(connectedAt, createDate,
                        "createDateTimestamp 必须保留源时间点"),
                () -> assertEquals(connectedAt, lastConnectedAt,
                        "lastConnectedAtTimestamp 必须保留源时间点"),
                () -> assertEquals(lastConnectedAt.atZone(browserZone).toLocalDateTime(),
                        createDate.atZone(browserZone).toLocalDateTime(),
                        "绑定时间和最后连接时间在同一浏览器中必须显示为相同的本地时间"),
                () -> assertTrue(payload.path("createDate").isTextual(),
                        "兼容字段 createDate 必须继续保留"));
    }

    @Test
    @DisplayName("时间为空时新旧字段均保持 null")
    void nullDeviceTimesRemainNull() {
        DeviceEntity entity = new DeviceEntity();
        DeviceServiceImpl deviceService = serviceReturning(entity);

        UserShowDeviceListVO device = deviceService.getUserDeviceList(1L, "agent-id").getFirst();
        ObjectMapper objectMapper = new WebMvcConfig().jackson2HttpMessageConverter().getObjectMapper();
        JsonNode payload = objectMapper.valueToTree(device);

        assertAll(
                () -> assertTrue(payload.path("createDateTimestamp").isNull()),
                () -> assertTrue(payload.path("lastConnectedAtTimestamp").isNull()),
                () -> assertTrue(payload.path("createDate").isNull()));
    }

    private DeviceServiceImpl serviceReturning(DeviceEntity entity) {
        return new DeviceServiceImpl(null, null, null, null, null, null) {
            @Override
            public List<DeviceEntity> getUserDevices(Long userId, String agentId) {
                return List.of(entity);
            }
        };
    }
}
