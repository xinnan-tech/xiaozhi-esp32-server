package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;

import com.baomidou.mybatisplus.core.conditions.AbstractWrapper;
import com.baomidou.mybatisplus.core.conditions.Wrapper;

import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.security.user.SecurityUser;

/**
 * #3448 设备标识归一化回归测试
 *
 * <p>
 * 同一台设备换个分隔符或大小写上报，入库、查重、查询三处必须算成同一个值，
 * 否则表现为静默不发凭证、不下发固件，没有任何报错可查。
 */
@DisplayName("设备标识归一化回归测试")
class DeviceMacAddressNormalizeTest {

    private static final String CANONICAL = "aa:bb:cc:dd:ee:ff";

    @Test
    @DisplayName("冒号、连字符、下划线、无分隔符、大小写写法归一到同一个值")
    void everySpellingCollapsesToCanonical() {
        for (String spelling : new String[] {
                "aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF", "aa-bb-cc-dd-ee-ff",
                "aa_bb_cc_dd_ee_ff", "aabbccddeeff", "Aa:Bb:Cc:Dd:Ee:Ff" }) {
            assertEquals(CANONICAL, DeviceServiceImpl.normalizeDeviceId(spelling), spelling);
        }
    }

    @Test
    @DisplayName("不是 MAC 的标识原样返回，交给后续校验拒绝")
    void nonMacValuePassesThrough() {
        for (String value : new String[] { null, "", "   ", "abc", "zz:zz:zz:zz:zz:zz", "00112233445566" }) {
            assertEquals(value, DeviceServiceImpl.normalizeDeviceId(value), String.valueOf(value));
        }
    }

    @Test
    @DisplayName("按任意写法上报都能查到归一后入库的那台设备")
    void lookupFindsRowStoredInCanonicalForm() {
        DeviceEntity stored = storedDevice(CANONICAL);
        DeviceServiceImpl service = service(daoMatchingOnly(CANONICAL, stored));

        for (String spelling : new String[] {
                "aa:bb:cc:dd:ee:ff", "aabbccddeeff", "AA-BB-CC-DD-EE-FF", "aa_bb_cc_dd_ee_ff" }) {
            assertSame(stored, service.getDeviceByMacAddress(spelling), spelling);
        }
    }

    @Test
    @DisplayName("迁移前按原文入库的存量设备仍能查到，不被归一化挡掉")
    void lookupFallsBackToLegacyRow() {
        DeviceEntity legacy = storedDevice("AA-BB-CC-DD-EE-FF");
        DeviceServiceImpl service = service(daoMatchingOnly("AA-BB-CC-DD-EE-FF", legacy));

        assertSame(legacy, service.getDeviceByMacAddress("AA-BB-CC-DD-EE-FF"),
                "归一后没查到，该退回原文再查一次，否则迁移前的设备直接失联");
    }

    @Test
    @DisplayName("两种写法都查不到时返回 null")
    void lookupMissReturnsNull() {
        DeviceServiceImpl service = service(daoMatchingOnly(CANONICAL, storedDevice(CANONICAL)));

        assertNull(service.getDeviceByMacAddress("11:22:33:44:55:66"));
        assertNull(service.getDeviceByMacAddress("  "));
    }

    @Test
    @DisplayName("手工添加按归一值查重、按归一值入库")
    void manualAddStoresNormalizedMac() {
        DeviceDao dao = mock(DeviceDao.class);
        when(dao.selectOne(any())).thenReturn(null);
        DeviceServiceImpl service = service(dao);

        DeviceManualAddDTO dto = new DeviceManualAddDTO();
        dto.setMacAddress("AABBCCDDEEFF");
        dto.setAgentId("1");
        service.manualAddDevice(9L, dto);

        ArgumentCaptor<Wrapper<DeviceEntity>> queried = wrapperCaptor();
        verify(dao).selectOne(queried.capture());
        assertEquals(CANONICAL, queriedMac(queried.getValue()),
                "查重用的不是归一值，同一台设备换个写法就能被重复添加");

        ArgumentCaptor<DeviceEntity> inserted = ArgumentCaptor.forClass(DeviceEntity.class);
        verify(dao).insert(inserted.capture());
        assertEquals(CANONICAL, inserted.getValue().getMacAddress());
        assertEquals(CANONICAL, inserted.getValue().getId(), "主键跟着一起归一，否则同一台设备能插进两条");
    }

    @Test
    @DisplayName("设备激活入库的是归一后的 MAC")
    void activationStoresNormalizedMac() {
        DeviceDao dao = mock(DeviceDao.class);
        when(dao.selectById(any())).thenReturn(null);
        RedisUtils redisUtils = mock(RedisUtils.class);
        Map<String, Object> activation = new HashMap<>();
        activation.put("mac_address", "AA-BB-CC-DD-EE-FF");
        activation.put("activation_code", "CODE1");
        when(redisUtils.get(any())).thenAnswer(invocation -> {
            String key = invocation.getArgument(0);
            return key.endsWith("CODE1") ? CANONICAL : activation;
        });
        DeviceServiceImpl service = service(dao, redisUtils);

        UserDetail user = new UserDetail();
        user.setId(9L);
        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user);
            assertTrue(service.deviceActivation("1", "CODE1"));
        }

        ArgumentCaptor<DeviceEntity> inserted = ArgumentCaptor.forClass(DeviceEntity.class);
        verify(dao).insert(inserted.capture());
        assertEquals(CANONICAL, inserted.getValue().getMacAddress());
    }

    private DeviceServiceImpl service(DeviceDao dao) {
        return service(dao, mock(RedisUtils.class));
    }

    /** baseDao 由父类持有，子类内部赋给 this，测试类自己碰不到它 */
    private DeviceServiceImpl service(DeviceDao dao, RedisUtils redisUtils) {
        return new DeviceServiceImpl(dao, null, null, redisUtils, null, null) {
            {
                this.baseDao = dao;
            }
        };
    }

    /** 只在查询值等于 storedMac 时才命中，用来验证查的是哪个值 */
    private DeviceDao daoMatchingOnly(String storedMac, DeviceEntity row) {
        DeviceDao dao = mock(DeviceDao.class);
        when(dao.selectOne(any())).thenAnswer(invocation -> {
            Wrapper<DeviceEntity> wrapper = invocation.getArgument(0);
            return storedMac.equals(queriedMac(wrapper)) ? row : null;
        });
        return dao;
    }

    private DeviceEntity storedDevice(String mac) {
        DeviceEntity device = new DeviceEntity();
        device.setId(mac);
        device.setMacAddress(mac);
        return device;
    }

    @SuppressWarnings("unchecked")
    private ArgumentCaptor<Wrapper<DeviceEntity>> wrapperCaptor() {
        return ArgumentCaptor.forClass(Wrapper.class);
    }

    /** eq() 绑定的值只在 AbstractWrapper 上，Wrapper 接口看不到 */
    private Map<String, Object> boundValues(Wrapper<DeviceEntity> wrapper) {
        return ((AbstractWrapper<?, ?, ?>) wrapper).getParamNameValuePairs();
    }

    /**
     * 取出这次查询实际拿去比对的 MAC
     *
     * <p>
     * 绑定值是拼 SQL 时才写进去的，getSqlSegment() 先调一次才读得到
     */
    private Object queriedMac(Wrapper<DeviceEntity> wrapper) {
        wrapper.getSqlSegment();
        return boundValues(wrapper).values().iterator().next();
    }
}