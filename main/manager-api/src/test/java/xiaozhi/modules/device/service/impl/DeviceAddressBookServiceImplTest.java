package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Date;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;

import xiaozhi.common.constant.Constant;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.device.dao.DeviceAddressBookDao;
import xiaozhi.modules.device.entity.DeviceAddressBookEntity;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.sys.service.SysParamsService;

class DeviceAddressBookServiceImplTest {

    private static final String MAC = "00:11:22:33:44:55";
    private static final String OTHER_MAC = "00:11:22:33:44:66";
    private static final String THIRD_MAC = "00:11:22:33:44:77";
    // 纯数字的 MAC 大小写化后跟原来一模一样，拿它造不出"只差大小写"的两行
    private static final String HEX_MAC = "00:11:22:33:44:ab";

    @Test
    void newEntryUsesTheDedicatedAddressBookInsertMapping() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());

        service.saveOrUpdate(MAC, OTHER_MAC, "living-room", true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        DeviceAddressBookEntity entity = entityCaptor.getValue();
        assertEquals(MAC, entity.getMacAddress());
        assertEquals(OTHER_MAC, entity.getTargetMac());
        assertEquals("living-room", entity.getAlias());
        assertTrue(entity.getHasPermission());
        verify(addressBookDao, never()).insert(any(DeviceAddressBookEntity.class));
    }

    @Test
    void blankAliasOnUnregisteredTargetFallsBackToMacSuffix() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());
        when(deviceService.getDeviceByMacAddress(OTHER_MAC)).thenReturn(null);

        service.saveOrUpdate(MAC, OTHER_MAC, null, true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        DeviceAddressBookEntity entity = entityCaptor.getValue();
        assertNotNull(entity.getAlias());
        assertEquals("尾号为66的设备", entity.getAlias());
        assertTrue(entity.getHasPermission());
    }

    @Test
    void blankAliasOnRegisteredTargetWithoutNicknameFallsBackToMacSuffix() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());
        DeviceEntity registered = new DeviceEntity();
        registered.setMacAddress(OTHER_MAC);
        registered.setAlias(null);
        when(deviceService.getDeviceByMacAddress(OTHER_MAC)).thenReturn(registered);

        service.saveOrUpdate(MAC, OTHER_MAC, null, true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        assertEquals("尾号为66的设备", entityCaptor.getValue().getAlias(),
                "登记了但没起名的设备落个空名，缓存刷新会跳过这条，对方永远呼不过来");
    }

    @Test
    void refreshCacheKeepsEntriesWhoseAliasWasNeverFilledIn() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        when(addressBookDao.selectList(null)).thenReturn(List.of(row(MAC, OTHER_MAC, null)));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        service.refreshCache();

        Map<String, String> book = cachedBook(service, redisUtils).get(MAC);
        assertNotNull(book, "空别名整条被跳过，这条设备就再也呼不过来了");
        assertEquals(OTHER_MAC + "|1", book.get("尾号为66的设备"));
    }

    @Test
    void refreshCacheDisambiguatesTwoEntriesSharingAnAlias() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        when(addressBookDao.selectList(null)).thenReturn(List.of(
                row(MAC, OTHER_MAC, "客厅"),
                row(MAC, THIRD_MAC, "客厅")));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        service.refreshCache();

        Map<String, String> book = cachedBook(service, redisUtils).get(MAC);
        assertEquals(2, book.size(), "撞名的两台设备只留得下一台：" + book);
        assertEquals(OTHER_MAC + "|1", book.get("客厅"));
        assertEquals(THIRD_MAC + "|1", book.get("客厅1"));
    }

    @Test
    void refreshCacheGivesTheSameResultWhateverOrderRowsComeBackIn() {
        DeviceAddressBookEntity first = row(MAC, OTHER_MAC, "客厅");
        DeviceAddressBookEntity second = row(MAC, THIRD_MAC, "客厅");

        Map<String, String> inOrder = refreshAndRead(List.of(first, second));
        Map<String, String> reversed = refreshAndRead(List.of(second, first));

        assertEquals(inOrder, reversed, "同样的数据两次刷新结果不一样，缓存里的称呼会来回变");
    }

    /**
     * 库里能同时存在两条 owner 只差大小写的行：表是 utf8mb4_0900_ai_ci，
     * 主键 (mac_address, target_mac) 大小写不敏感，target 不同就不会撞。
     * 这是同一个人，算称呼和写缓存都得按小写归成一本
     */
    @Test
    void ownersDifferingOnlyInCaseShareOneBook() {
        String upper = HEX_MAC.toUpperCase();
        assertNotEquals(HEX_MAC, upper, "这个用例得真的造出大小写差异才有效");

        Map<String, Map<String, String>> books = refreshAndReadAll(List.of(
                row(upper, OTHER_MAC, "客厅"),
                row(HEX_MAC, THIRD_MAC, "客厅")));

        Map<String, String> book = books.get(HEX_MAC);
        assertNotNull(book, "同一个人被算成了两个人：" + books.keySet());
        assertEquals(2, book.size(), "两台设备只剩一台，另一台从缓存里消失了：" + book);
        assertEquals(OTHER_MAC + "|1", book.get("客厅"));
        assertEquals(THIRD_MAC + "|1", book.get("客厅1"));
        assertEquals(1, books.size(), "两种写法的地址被拆成了两本：" + books.keySet());
    }

    @Test
    void listAndCacheAgreeWhenOwnersDifferOnlyInCase() {
        String upper = HEX_MAC.toUpperCase();
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        when(addressBookDao.getAddressBookList(upper)).thenReturn(new ArrayList<>(List.of(
                row(upper, OTHER_MAC, "客厅"), row(HEX_MAC, THIRD_MAC, "客厅"))));
        when(addressBookDao.selectList(null)).thenReturn(List.of(
                row(upper, OTHER_MAC, "客厅"), row(HEX_MAC, THIRD_MAC, "客厅")));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        Map<String, String> shownToConsole = namesByTargetMac(service.getAddressBookList(upper));
        assertEquals(2, shownToConsole.size(),
                "接口按原值分组，同一个人的两台设备被算成一个，前端只能看到一台：" + shownToConsole);

        service.refreshCache();
        Map<String, String> callableNames = new HashMap<>();
        cachedBook(service, redisUtils).get(HEX_MAC)
                .forEach((name, macAndPerm) -> callableNames.put(name, macAndPerm.split("\\|")[0]));

        assertEquals(shownToConsole, callableNames,
                "接口按原值分组、缓存按小写分组，用户照前端看到的名字呼，命中的不是同一台设备");
    }

    @Test
    void nameAssignmentDoesNotDependOnWhichSpellingOfTheOwnerCameBack() {
        String upper = HEX_MAC.toUpperCase();
        Map<String, String> expected = Map.of("客厅", OTHER_MAC + "|1", "客厅1", THIRD_MAC + "|1");

        Map<String, String> lowerFirst = refreshAndRead(HEX_MAC, List.of(
                row(HEX_MAC, OTHER_MAC, "客厅"), row(upper, THIRD_MAC, "客厅")));
        Map<String, String> upperFirst = refreshAndRead(HEX_MAC, List.of(
                row(upper, THIRD_MAC, "客厅"), row(HEX_MAC, OTHER_MAC, "客厅")));

        assertEquals(expected, lowerFirst,
                "同一个人的称呼取决于库里哪种写法先返回，刷新一次就换一次名字");
        assertEquals(expected, upperFirst, "顺序反过来结果就该不一样：" + upperFirst);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Map<String, String>> refreshAndReadAll(List<DeviceAddressBookEntity> rows) {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        when(addressBookDao.selectList(null)).thenReturn(rows);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        service.refreshCache();

        return cachedBook(service, redisUtils);
    }

    private Map<String, String> refreshAndRead(List<DeviceAddressBookEntity> rows) {
        return refreshAndRead(MAC, rows);
    }

    private Map<String, String> refreshAndRead(String owner, List<DeviceAddressBookEntity> rows) {
        return refreshAndReadAll(rows).get(owner);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Map<String, String>> cachedBook(DeviceAddressBookServiceImpl service, RedisUtils redisUtils) {
        ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
        verify(redisUtils).set(eq(RedisKeys.getAddressBookKey()), captor.capture());
        return (Map<String, Map<String, String>>) captor.getValue();
    }

    private DeviceAddressBookEntity row(String macAddress, String targetMac, String alias) {
        return row(macAddress, targetMac, alias, Boolean.TRUE);
    }

    private DeviceAddressBookEntity row(String macAddress, String targetMac, String alias, Boolean hasPermission) {
        DeviceAddressBookEntity entity = new DeviceAddressBookEntity();
        entity.setMacAddress(macAddress);
        entity.setTargetMac(targetMac);
        entity.setAlias(alias);
        entity.setHasPermission(hasPermission);
        return entity;
    }

    @Test
    void listAndCacheHandOutTheSameNameForCollidingEntries() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        // 两次 DAO 调用各给一份新行：取名会写回实体，共用同一份的话第二遍读到的是算过的名字
        // 用可变列表，跟 MyBatis 实际返回的一致，免得排序那步先炸掉、断言根本没跑到
        when(addressBookDao.getAddressBookList(MAC)).thenReturn(
                new ArrayList<>(List.of(row(MAC, OTHER_MAC, "客厅"), row(MAC, THIRD_MAC, "客厅"))));
        when(addressBookDao.selectList(null)).thenReturn(List.of(
                row(MAC, OTHER_MAC, "客厅"), row(MAC, THIRD_MAC, "客厅")));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        Map<String, String> shownToConsole = namesByTargetMac(service.getAddressBookList(MAC));
        service.refreshCache();
        Map<String, String> callableNames = new HashMap<>();
        cachedBook(service, redisUtils).get(MAC)
                .forEach((name, macAndPerm) -> callableNames.put(name, macAndPerm.split("\\|")[0]));

        assertEquals(callableNames, shownToConsole,
                "接口和缓存给的是两个名字，用户照前端看到的那个名字呼叫，命中的不是同一台设备");
    }

    @Test
    void theCallableEntryKeepsThePlainNameWhenTwoCollide() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        // OTHER_MAC 的 target_mac 排在前面，没权限的那条会先占住原名
        when(addressBookDao.selectList(null)).thenReturn(List.of(
                row(MAC, OTHER_MAC, "客厅", Boolean.FALSE),
                row(MAC, THIRD_MAC, "客厅", Boolean.TRUE)));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        service.refreshCache();

        Map<String, String> book = cachedBook(service, redisUtils).get(MAC);
        assertEquals(THIRD_MAC + "|1", book.get("客厅"),
                "能呼的那台被挤到后缀名上了，用户照前端看到的名字点，界面只会说没权限");
        assertEquals(OTHER_MAC + "|0", book.get("客厅1"));
    }

    @Test
    void listFillsInBlankAliasesSoTheConsoleShowsWhatCanBeCalled() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        when(addressBookDao.getAddressBookList(MAC)).thenReturn(new ArrayList<>(List.of(row(MAC, OTHER_MAC, null))));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        List<DeviceAddressBookEntity> rows = service.getAddressBookList(MAC);

        assertEquals("尾号为66的设备", rows.get(0).getAlias(),
                "空别名原样返回的话前端回落显示设备名，用户照着那个名字呼叫却只会说找不到备注");
    }

    @Test
    void anUppercaseMacGetsTheSameNameWhicheverPathAddsItToTheBook() {
        // 兜底称呼只有这一处算法：存进去的时候算一次，之后接口和缓存里显示的
        // 都是同一个字符串。不跟着小写化的话同一个地址在两条路径上算出两个称呼，
        // 用户照着看到的名字呼过去，命中的不是自己刚存的那台
        //
        // 运行期这一侧：saveOrUpdate 传的是 DTO 原样过来的地址，大小写没归一
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());
        when(deviceService.getDeviceByMacAddress(anyString())).thenReturn(null);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, mock(SysParamsService.class));

        service.saveOrUpdate(MAC, "ff:ee:dd:cc:bb:AB", null, true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        assertEquals("尾号为ab的设备", entityCaptor.getValue().getAlias(),
                "MAC 大小写不区分，末尾两位要跟着小写化，否则接口和呼叫那边算出来的称呼对不上");
    }

    /**
     * 接口按最近改过的排前面
     *
     * <p>
     * 智控台那条 Vue 是按 targetMac 把 alias 合进 allDevices 的，接口顺序被丢掉了，
     * 这条现在对 console 没有效果。用例留着是把这个契约钉住：哪天当无用代码删了，
     * 会有用例报出来，而不是静悄悄换掉接口的返回顺序
     */
    @Test
    void listPutsTheMostRecentlyTouchedEntryFirst() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceAddressBookEntity older = row(MAC, OTHER_MAC, "客厅");
        older.setUpdateDate(new Date(1767321840000L));
        DeviceAddressBookEntity newer = row(MAC, THIRD_MAC, "书房");
        newer.setUpdateDate(new Date(1778000000000L));
        DeviceAddressBookEntity neverTouched = row(MAC, "00:11:22:33:44:88", "阳台");
        when(addressBookDao.getAddressBookList(MAC)).thenReturn(
                new ArrayList<>(List.of(older, neverTouched, newer)));
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, mock(DeviceService.class), mock(SysParamsService.class));

        List<DeviceAddressBookEntity> rows = service.getAddressBookList(MAC);

        assertEquals(List.of("书房", "客厅", "阳台"), rows.stream().map(DeviceAddressBookEntity::getAlias).toList(),
                "最近改过的应该排前面，没改过的排最后");
    }


    private Map<String, String> namesByTargetMac(List<DeviceAddressBookEntity> rows) {
        Map<String, String> byAlias = new HashMap<>();
        for (DeviceAddressBookEntity row : rows) {
            byAlias.put(row.getAlias(), row.getTargetMac());
        }
        return byAlias;
    }

    @Test
    void callByNicknameFallsBackToMacSuffixWhenCallerHasNoAlias() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);

        Map<String, Map<String, String>> books = new HashMap<>();
        Map<String, String> callerBook = new HashMap<>();
        callerBook.put("office", OTHER_MAC + "|1");
        books.put(MAC, callerBook);
        when(redisUtils.get(RedisKeys.getAddressBookKey())).thenReturn(books);
        when(deviceService.getDeviceByMacAddress(MAC)).thenReturn(null);
        when(sysParamsService.getValue("server.mqtt_manager_api", true)).thenReturn("127.0.0.1:1883");
        when(sysParamsService.getValue(Constant.SERVER_MQTT_SECRET, true)).thenReturn("gateway-key");

        // 网关是真的 http 调用，桩掉它，否则测试会往 127.0.0.1:1883 真发请求
        AtomicReference<String> sentUrl = new AtomicReference<>();
        AtomicReference<String> sentBody = new AtomicReference<>();
        Map<String, Object> result;
        try (MockedStatic<MqttGatewayAuthorization> gateway = mockStatic(MqttGatewayAuthorization.class)) {
            gateway.when(() -> MqttGatewayAuthorization.postJson(
                            anyString(), anyString(), anyString(), any(), anyInt()))
                    .thenAnswer(invocation -> {
                        sentUrl.set(invocation.getArgument(0));
                        sentBody.set(invocation.getArgument(1));
                        return "{\"status\":\"success\",\"message\":\"ok\"}";
                    });
            result = service.callByNickname(MAC, "office", false);
        }

        assertEquals("success", result.get("status"));
        assertEquals("http://127.0.0.1:1883/api/call/request", sentUrl.get());
        assertTrue(sentBody.get().contains("尾号为55的设备"),
                "主叫方没登记也没起名时该退回尾号称呼：" + sentBody.get());
    }
}
