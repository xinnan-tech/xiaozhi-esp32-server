package xiaozhi.modules.device.service.impl;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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
        return deviceAddressBookDao.getAddressBookList(macAddress);
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
            DeviceEntity callerDevice =
                    deviceService.getDeviceByMacAddress(callerMac);
            if (callerDevice == null) {
                return errorResult("接听失败，设备信息不存在");
            }
            return postCallAccept(
                    buildMqttClientId(callerDevice),
                    Map.of("mac", callerMac));
        }

        // 主动呼叫模式
        Map<String, String> callerBook = allBooks.get(callerMac.toLowerCase());
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

        DeviceEntity callerDevice =
                deviceService.getDeviceByMacAddress(callerMac);
        DeviceEntity targetDevice =
                deviceService.getDeviceByMacAddress(targetMac);
        if (callerDevice == null || targetDevice == null) {
            return errorResult("呼叫失败，设备信息不存在");
        }

        // 获取目标设备如何称呼主叫方
        Map<String, String> targetBook = allBooks.get(targetMac.toLowerCase());
        String callerNickname = null;
        if (targetBook != null) {
            callerNickname = targetBook.get(callerMac.toLowerCase());
        }
        if (StringUtils.isBlank(callerNickname)) {
            callerNickname = callerDevice.getAlias();
            if (StringUtils.isBlank(callerNickname)) {
                callerNickname = formatMacAsDeviceName(callerMac);
            }
        }

        return postCallRequest(
                buildMqttClientId(callerDevice),
                buildMqttClientId(targetDevice),
                Map.of(
                        "caller_mac", callerMac,
                        "target_mac", targetMac,
                        "caller_nickname", callerNickname));
    }

    @Override
    public void refreshCache() {
        Map<String, Map<String, String>> result = new HashMap<>();
        List<DeviceAddressBookEntity> allRecords = deviceAddressBookDao.selectList(null);
        Map<String, String> reverseMap = new HashMap<>();

        for (DeviceAddressBookEntity entity : allRecords) {
            String macA = entity.getMacAddress().toLowerCase();
            String macB = entity.getTargetMac().toLowerCase();
            String alias = entity.getAlias();
            Boolean hasPermission = entity.getHasPermission();

            // 构建正向映射: A对B的映射 nickname -> macB|permission
            if (alias != null && !alias.isEmpty()) {
                result.computeIfAbsent(macA, k -> new HashMap<>());
                String permStr = (hasPermission != null && hasPermission) ? "1" : "0";
                result.get(macA).put(alias, macB + "|" + permStr);
            }

            // 构建反向记录用于查找B对A的称呼
            if (alias != null && !alias.isEmpty()) {
                reverseMap.put(macB + ":" + macA, alias);
            }
        }

        // 构建反向映射: B对A的映射 macA -> nickname
        for (DeviceAddressBookEntity entity : allRecords) {
            String macA = entity.getMacAddress().toLowerCase();
            String macB = entity.getTargetMac().toLowerCase();
            String aliasBtoA = reverseMap.get(macA + ":" + macB);
            if (aliasBtoA != null && !aliasBtoA.isEmpty()) {
                result.computeIfAbsent(macB, k -> new HashMap<>());
                result.get(macB).put(macA, aliasBtoA);
            }
        }

        redisUtils.set(RedisKeys.getAddressBookKey(), result);
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
        System.out.println("saveOrUpdate - mac=" + macAddress + ", targetMac=" + targetMac + ", alias=" + alias + ", record=" + (record == null ? "null" : "not null"));
        if (record == null) {
            DeviceAddressBookEntity entity = new DeviceAddressBookEntity();
            entity.setMacAddress(macAddress);
            entity.setTargetMac(targetMac);
            // 如果 alias 为空，就默认使用设备名称
            if (StringUtils.isBlank(alias)) {
                alias = deviceService.getDeviceByMacAddress(targetMac).getAlias();
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

    private Map<String, Object> postCallRequest(
            String callerClientId,
            String targetClientId,
            Map<String, Object> body) {
        try {
            MqttManagementHttpClient.Response response =
                    createMqttManagementRouter().sendCallRequest(
                            callerClientId, targetClientId, body);
            return parseCallResponse(response, "呼叫");
        } catch (Exception e) {
            return errorResult("呼叫失败，请稍后再试");
        }
    }

    private Map<String, Object> postCallAccept(
            String clientId,
            Map<String, Object> body) {
        try {
            MqttManagementHttpClient.Response response =
                    createMqttManagementRouter().sendCallAccept(
                            clientId, body);
            return parseCallResponse(response, "接听");
        } catch (Exception e) {
            return errorResult("接听失败，请稍后再试");
        }
    }

    private Map<String, Object> parseCallResponse(
            MqttManagementHttpClient.Response response,
            String action) {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "error");
        if (response == null || StringUtils.isBlank(response.body())) {
            result.put("message", action + "失败，MQTT管理配置缺失");
            return result;
        }

        try {
            Map<String, Object> backendResult =
                    JSONUtil.parseObj(response.body());
            result.put("status", backendResult.get("status"));
            result.put("message", backendResult.get("message"));
            if (backendResult.containsKey("code")) {
                result.put("code", backendResult.get("code"));
            }
            return result;
        } catch (Exception e) {
            result.put("message", action + "失败，请稍后再试");
            return result;
        }
    }

    MqttManagementRouter createMqttManagementRouter() {
        return new MqttManagementRouter(
                new MqttManagementEndpointResolver(sysParamsService),
                new MqttManagementHttpClient());
    }

    private String buildMqttClientId(DeviceEntity device) {
        return MqttClientId.build(
                device.getBoard(), device.getMacAddress());
    }

    private String formatMacAsDeviceName(String mac) {
        if (StringUtils.isBlank(mac) || mac.length() < 2) {
            return mac;
        }
        String lastTwo = mac.substring(mac.length() - 2);
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
