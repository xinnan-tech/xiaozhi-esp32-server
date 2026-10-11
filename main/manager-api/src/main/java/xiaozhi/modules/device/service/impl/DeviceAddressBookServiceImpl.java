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
            return postToMqtt("/api/call/accept", Map.of("mac", callerMac), "Answer");
        }

        // Active call mode
        Map<String, String> callerBook = allBooks.get(callerMac.toLowerCase());
        if (callerBook == null) {
            return errorResult("Device with nickname '" + nickname + "' not found");
        }
        String targetMacWithPerm = callerBook.get(nickname);
        if (targetMacWithPerm == null) {
            return errorResult("Device with nickname '" + nickname + "' not found");
        }
        String[] parts = targetMacWithPerm.split("\\|");
        String targetMac = parts[0];
        boolean hasPermission = parts.length > 1 && "1".equals(parts[1]);

        if (!hasPermission) {
            return errorResult("Call failed: you do not have permission to call this device");
        }

        // Get how the target device addresses the caller
        Map<String, String> targetBook = allBooks.get(targetMac.toLowerCase());
        String callerNickname = null;
        if (targetBook != null) {
            callerNickname = targetBook.get(callerMac.toLowerCase());
        }
        if (StringUtils.isBlank(callerNickname)) {
            callerNickname = deviceService.getDeviceByMacAddress(callerMac).getAlias();
            if (StringUtils.isBlank(callerNickname)) {
                callerNickname = formatMacAsDeviceName(callerMac);
            }
        }

        return postToMqtt("/api/call/request",
                Map.of("caller_mac", callerMac, "target_mac", targetMac, "caller_nickname", callerNickname),
                "Call");
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

            // Build forward mapping: A-to-B mapping nickname -> macB|permission
            if (alias != null && !alias.isEmpty()) {
                result.computeIfAbsent(macA, k -> new HashMap<>());
                String permStr = (hasPermission != null && hasPermission) ? "1" : "0";
                result.get(macA).put(alias, macB + "|" + permStr);
            }

            // Build reverse records to look up how B refers to A
            if (alias != null && !alias.isEmpty()) {
                reverseMap.put(macB + ":" + macA, alias);
            }
        }

        // Build reverse mapping: B-to-A mapping macA -> nickname
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
            // If alias is empty, default to device name
            if (StringUtils.isBlank(alias)) {
                alias = deviceService.getDeviceByMacAddress(targetMac).getAlias();
            }
            // Check for duplicates
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
            result.put("message", action + "Failed, gateway config missing");
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
            result.put("message", action + "Failed, please try again later");
            return result;
        }
    }

    private String formatMacAsDeviceName(String mac) {
        if (StringUtils.isBlank(mac) || mac.length() < 2) {
            return mac;
        }
        String lastTwo = mac.substring(mac.length() - 2);
        return "Device ending in " + lastTwo;
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
