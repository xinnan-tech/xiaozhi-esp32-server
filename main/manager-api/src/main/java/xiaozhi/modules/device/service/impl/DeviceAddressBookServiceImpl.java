package xiaozhi.modules.device.service.impl;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import cn.hutool.json.JSONUtil;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.device.dao.DeviceAddressBookDao;
import xiaozhi.modules.device.entity.DeviceAddressBookEntity;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceAddressBookService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.sys.service.SysParamsService;

@Service
public class DeviceAddressBookServiceImpl implements DeviceAddressBookService {

    private final DeviceAddressBookDao deviceAddressBookDao;
    private final RedisUtils redisUtils;
    private final DeviceService deviceService;
    private final SysParamsService sysParamsService;

    public DeviceAddressBookServiceImpl(DeviceAddressBookDao deviceAddressBookDao, RedisUtils redisUtils,
            @Lazy DeviceService deviceService, SysParamsService sysParamsService) {
        this.deviceAddressBookDao = deviceAddressBookDao;
        this.redisUtils = redisUtils;
        this.deviceService = deviceService;
        this.sysParamsService = sysParamsService;
    }

    @Override
    public List<DeviceAddressBookEntity> getAddressBookList(String macAddress) {
        List<DeviceAddressBookEntity> rows = assignUniqueAliases(deviceAddressBookDao.getAddressBookList(macAddress));
        // 取名按固定顺序算完了，前端要看的是最近改过的排前面，放回去
        rows.sort(Comparator
                .comparing(DeviceAddressBookEntity::getUpdateDate, Comparator.nullsLast(Comparator.reverseOrder())));
        return rows;
    }

    @Override
    @SuppressWarnings("unchecked")
    public Map<String, Map<String, String>> getAllAddressBooks() {
        Object cached = redisUtils.get(RedisKeys.getAddressBookKey());
        if (cached != null) {
            return (Map<String, Map<String, String>>) cached;
        }
        refreshCache();
        return (Map<String, Map<String, String>>) redisUtils.get(RedisKeys.getAddressBookKey());
    }

    @Override
    public Map<String, Object> callByNickname(String callerMac, String nickname, boolean isAnswer) {
        Map<String, Map<String, String>> allBooks = getAllAddressBooks();

        if (isAnswer) {
            return postToMqtt("/api/call/accept", Map.of("mac", callerMac), "接听");
        }

        // 主动呼叫模式
        Map<String, String> callerBook = allBooks.get(bookKey(callerMac));
        if (callerBook == null) {
            return errorResult("未找到备注为'" + nickname + "'的设备");
        }
        String targetMacWithPerm = callerBook.get(nickname);
        if (targetMacWithPerm == null) {
            return errorResult("未找到备注为'" + nickname + "'的设备");
        }
        String[] parts = targetMacWithPerm.split("\\|");
        String targetMac = parts[0];
        boolean hasPermission = parts.length > 1 && "1".equals(parts[1]);

        if (!hasPermission) {
            return errorResult("呼叫失败，您没有权限呼叫该设备");
        }

        // 获取目标设备如何称呼主叫方
        Map<String, String> targetBook = allBooks.get(bookKey(targetMac));
        String callerNickname = null;
        if (targetBook != null) {
            callerNickname = targetBook.get(bookKey(callerMac));
        }
        if (StringUtils.isBlank(callerNickname)) {
            DeviceEntity callerDevice = deviceService.getDeviceByMacAddress(callerMac);
            if (callerDevice != null) {
                callerNickname = callerDevice.getAlias();
            }
            if (StringUtils.isBlank(callerNickname)) {
                callerNickname = formatMacAsDeviceName(callerMac);
            }
        }

        return postToMqtt("/api/call/request",
                Map.of("caller_mac", callerMac, "target_mac", targetMac, "caller_nickname", callerNickname),
                "呼叫");
    }

    @Override
    public void refreshCache() {
        Map<String, Map<String, String>> result = new HashMap<>();
        List<DeviceAddressBookEntity> allRecords = assignUniqueAliases(deviceAddressBookDao.selectList(null));
        Map<String, String> reverseMap = new HashMap<>();

        for (DeviceAddressBookEntity entity : allRecords) {
            String macA = bookKey(entity.getMacAddress());
            String macB = bookKey(entity.getTargetMac());

            // 构建正向映射: A对B的映射 nickname -> macB|permission
            Map<String, String> book = result.computeIfAbsent(macA, k -> new HashMap<>());
            String permStr = (Boolean.TRUE.equals(entity.getHasPermission())) ? "1" : "0";
            book.put(entity.getAlias(), macB + "|" + permStr);

            // 构建反向记录用于查找B对A的称呼，用同一个去重后的名字，两边才对得上
            reverseMap.put(macB + ":" + macA, entity.getAlias());
        }

        // 构建反向映射: B对A的映射 macA -> nickname
        for (DeviceAddressBookEntity entity : allRecords) {
            String macA = bookKey(entity.getMacAddress());
            String macB = bookKey(entity.getTargetMac());
            String aliasBtoA = reverseMap.get(macA + ":" + macB);
            if (aliasBtoA != null && !aliasBtoA.isEmpty()) {
                result.computeIfAbsent(macB, k -> new HashMap<>());
                result.get(macB).put(macA, aliasBtoA);
            }
        }

        redisUtils.set(RedisKeys.getAddressBookKey(), result);
    }

    /**
     * 给每行算出一个不重名的称呼，返回排好序、alias 已写好的新列表
     *
     * 昵称在同一个人的通讯录里是索引，同名后写的会盖掉先写的，按昵称呼会呼错设备。
     * 库里本来就有重名：空别名补出来的尾号称呼只有 256 种取值，一本通讯录十几条
     * 没起名就撞上了。所以显示和呼叫都得走这一份，
     * 不然前端看到的字和呼叫时用的名字对不上，用户照着点的名字呼不到人。
     * 不改传入的那个列表：它是 DAO 刚查出来的，调用方还要按自己的顺序用
     */
    private List<DeviceAddressBookEntity> assignUniqueAliases(List<DeviceAddressBookEntity> rows) {
        // 取名要靠先后定谁拿原名，而 selectList 不带 order by，返回顺序不保证。
        // 排一次，同样的数据每次算出来的结果一样，缓存不会来回变。
        // 按归一后的地址排：同一个人不管库里是哪种写法都排到一起，
        // 后面两级比较器再分先后。同一本里 target_mac 不会重复（主键摆着），
        // 所以顺序还是由这三个键定死的，不会掉回"跟着数据库返回顺序走"
        List<DeviceAddressBookEntity> ordered = new ArrayList<>(rows);
        ordered.sort(Comparator
                .comparing((DeviceAddressBookEntity row) -> bookKey(row.getMacAddress()),
                        Comparator.nullsFirst(Comparator.naturalOrder()))
                // 权限排在地址前面：撞名时让对方准许呼我的那台先拿原名。
                // 排在后面等于不起作用，两条地址不同时谁先谁后是地址定的，
                // 没权限那条照样占住原名，用户照前端看到的名字呼叫命中的就是它，
                // 界面上只会说没权限，怎么点都不通
                .thenComparing(DeviceAddressBookEntity::getHasPermission,
                        Comparator.nullsLast(Comparator.reverseOrder()))
                .thenComparing(DeviceAddressBookEntity::getTargetMac, Comparator.nullsFirst(Comparator.naturalOrder())));

        Map<String, Set<String>> takenByOwner = new HashMap<>();
        for (DeviceAddressBookEntity row : ordered) {
            // 建表时 alias 默认是空的，用户没起名就是空的，这是默认状态不是异常。
            // 补个尾号称呼顶上，整条跳过的话接口照样返回成功，对方却再也呼不过来
            String alias = StringUtils.isBlank(row.getAlias())
                    ? formatMacAsDeviceName(row.getTargetMac())
                    : row.getAlias();

            // 加后缀的写法跟 generateUniqueAlias 保持一致，不搞两套命名规则
            Set<String> taken = takenByOwner.computeIfAbsent(bookKey(row.getMacAddress()), k -> new HashSet<>());
            String uniqueAlias = alias;
            int suffix = 1;
            while (taken.contains(uniqueAlias)) {
                uniqueAlias = alias + suffix++;
            }
            taken.add(uniqueAlias);
            row.setAlias(uniqueAlias);
        }
        return ordered;
    }

    @Override
    public void updateAlias(String macAddress, String targetMac, String alias) {
        String finalAlias = generateUniqueAlias(macAddress, targetMac, alias);
        deviceAddressBookDao.updateAlias(macAddress, targetMac, finalAlias);
        refreshCache();
    }

    @Override
    public void updatePermission(String macAddress, String targetMac, Boolean hasPermission) {
        deviceAddressBookDao.updatePermission(macAddress, targetMac, hasPermission);
        refreshCache();
    }

    @Override
    public void saveOrUpdate(String macAddress, String targetMac, String alias, Boolean hasPermission) {
        QueryWrapper<DeviceAddressBookEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("mac_address", macAddress).eq("target_mac", targetMac);
        DeviceAddressBookEntity record = deviceAddressBookDao.selectOne(wrapper);
        if (record == null) {
            DeviceAddressBookEntity entity = new DeviceAddressBookEntity();
            entity.setMacAddress(macAddress);
            entity.setTargetMac(targetMac);
            // 如果 alias 为空，就默认使用设备名称；对方设备尚未登记时退回尾号称呼
            if (StringUtils.isBlank(alias)) {
                DeviceEntity targetDevice = deviceService.getDeviceByMacAddress(targetMac);
                if (targetDevice != null) {
                    alias = targetDevice.getAlias();
                }
                // 设备登记了但用户没起过名，alias 建表就是 null，这是默认状态
                // 不是异常。这时候落个 null 进去，缓存刷新会把整条跳过，
                // 接口照样返回成功，对方却永远呼不过来
                if (StringUtils.isBlank(alias)) {
                    alias = formatMacAsDeviceName(targetMac);
                }
            }
            // 检查重名
            alias = generateUniqueAlias(macAddress, targetMac, alias);
            entity.setAlias(alias);
            entity.setHasPermission(hasPermission);
            deviceAddressBookDao.insertAddressBook(entity);
        } else {
            if (alias != null) {
                updateAlias(macAddress, targetMac, alias);
            }
            if (hasPermission != null) {
                deviceAddressBookDao.updatePermission(macAddress, targetMac, hasPermission);
            }
        }
        refreshCache();
    }

    @Override
    public void deleteByMacAddresses(List<String> macAddresses) {
        if (macAddresses == null || macAddresses.isEmpty()) {
            return;
        }
        deviceAddressBookDao.deleteByMacAddresses(macAddresses);
        refreshCache();
    }

    private Map<String, Object> errorResult(String message) {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "error");
        result.put("message", message);
        return result;
    }

    private Map<String, Object> postToMqtt(String path, Map<String, Object> body, String action) {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "error");

        String mqttGatewayUrl = sysParamsService.getValue("server.mqtt_manager_api", true);
        String mqttSignatureKey = sysParamsService.getValue(Constant.SERVER_MQTT_SECRET, true);

        if (StringUtils.isBlank(mqttGatewayUrl) || "null".equals(mqttGatewayUrl)
                || MqttGatewayAuthorization.isMissingSignatureKey(mqttSignatureKey)) {
            result.put("message", action + "失败，网关配置缺失");
            return result;
        }

        try {
            String url = "http://" + mqttGatewayUrl + path;
            String response = MqttGatewayAuthorization.postJson(
                    url,
                    JSONUtil.toJsonStr(body),
                    mqttSignatureKey,
                    Instant.now(),
                    5000);

            if (StringUtils.isNotBlank(response)) {
                Map<String, Object> gwResult = JSONUtil.parseObj(response);
                result.put("status", gwResult.get("status"));
                result.put("message", gwResult.get("message"));
            }
            return result;
        } catch (Exception e) {
            result.put("message", action + "失败，请稍后再试");
            return result;
        }
    }

    /**
     * 通讯录里当主人用的地址键
     *
     * <p>
     * 写缓存、查缓存、算称呼都靠它分组，三处必须是同一个值。少归一一次，同一个人的两行
     * 会被当成两个人：各自拿到同名，写进同一本时后者盖掉前者，一台设备直接从缓存里消失。
     * 库里确实能出现这种数据——表是 utf8mb4_0900_ai_ci，主键 (mac_address, target_mac)
     * 大小写不敏感，owner 只差大小写而 target 不同的话两行不撞
     */
    private static String bookKey(String macAddress) {
        return macAddress == null ? null : macAddress.toLowerCase();
    }

    private String formatMacAsDeviceName(String mac) {
        if (StringUtils.isBlank(mac) || mac.length() < 2) {
            return mac;
        }
        // MAC 本身不区分大小写，落库、查库走的都是小写化的值。
        // 这里跟着小写化，不跟着的话同一个地址在两条路径上会算出两个称呼，
        // 数据搬到智控台上看到的名字就叫不到人了
        String lastTwo = mac.substring(mac.length() - 2).toLowerCase();
        return "尾号为" + lastTwo + "的设备";
    }

    private String generateUniqueAlias(String macAddress, String targetMac, String alias) {
        QueryWrapper<DeviceAddressBookEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("mac_address", macAddress);
        List<DeviceAddressBookEntity> existing = deviceAddressBookDao.selectList(wrapper);
        List<String> existNames = existing.stream()
                .map(DeviceAddressBookEntity::getAlias)
                .filter(a -> a != null && !a.isEmpty())
                .collect(Collectors.toList());
        if (!existNames.contains(alias)) {
            return alias;
        }
        int suffix = 1;
        String newAlias;
        while (existNames.contains(newAlias = alias + suffix)) {
            suffix++;
        }
        return newAlias;
    }
}
