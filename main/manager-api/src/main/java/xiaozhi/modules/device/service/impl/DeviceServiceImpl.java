package xiaozhi.modules.device.service.impl;

import java.time.Instant;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;

import cn.hutool.core.util.RandomUtil;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.dto.DeviceBindDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;

@Service
public class DeviceServiceImpl extends BaseServiceImpl<DeviceDao, DeviceEntity> implements DeviceService {

    private final DeviceDao deviceDao;

    private final String frontedUrl;

    private final RedisTemplate<String, Object> redisTemplate;

    // 添加构造函数来初始化 deviceMapper
    public DeviceServiceImpl(DeviceDao deviceDao,
            @Value("${app.fronted-url:http://localhost:8001}") String frontedUrl,
            RedisTemplate<String, Object> redisTemplate) {
        this.deviceDao = deviceDao;
        this.frontedUrl = frontedUrl;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public DeviceEntity getDeviceById(String deviceId) {
        LambdaQueryWrapper<DeviceEntity> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(DeviceEntity::getId, deviceId);
        return deviceDao.selectOne(queryWrapper);
    }

    @Override
    public Boolean deviceActivation(String activationCode) {
        if (StringUtils.isBlank(activationCode)) {
            throw new RenException("激活码不能为空");
        }
        String deviceKey = "ota:activation:code:" + activationCode;
        Object cacheDeviceId = redisTemplate.opsForValue().get(deviceKey);
        if (cacheDeviceId == null) {
            throw new RenException("激活码错误");
        }
        String deviceId = (String) cacheDeviceId;
        String safeDeviceId = deviceId.replace(":", "_").toLowerCase();
        String cacheDeviceKey = String.format("ota:activation:data:%s", safeDeviceId);
        Map<Object, Object> cacheMap = redisTemplate.opsForHash().entries(cacheDeviceKey);
        if (cacheMap == null) {
            throw new RenException("激活码错误");
        }
        String cachedCode = (String) cacheMap.get("activation_code");
        if (!activationCode.equals(cachedCode)) {
            throw new RenException("激活码错误");
        }
        // 检查设备有没有被激活
        if (selectById(deviceId) != null) {
            throw new RenException("设备已激活");
        }

        String macAddress = (String) cacheMap.get("mac_address");
        String board = (String) cacheMap.get("board");
        String appVersion = (String) cacheMap.get("app_version");
        UserDetail user = SecurityUser.getUser();
        if (user.getId() == null) {
            throw new RenException("用户未登录");
        }

        Date currentTime = new Date();
        DeviceEntity deviceEntity = new DeviceEntity();
        deviceEntity.setId(deviceId);
        deviceEntity.setBoard(board);
        deviceEntity.setAppVersion(appVersion);
        deviceEntity.setMacAddress(macAddress);
        deviceEntity.setUserId(user.getId());
        deviceEntity.setCreator(user.getId());
        deviceEntity.setCreateDate(currentTime);
        deviceEntity.setUpdater(user.getId());
        deviceEntity.setUpdateDate(currentTime);
        deviceEntity.setLastConnectedAt(currentTime);
        deviceDao.insert(deviceEntity);

        // 清理redis缓存
        redisTemplate.delete(cacheDeviceKey);
        redisTemplate.delete(deviceKey);
        return true;
    }

    @Override
    public DeviceReportRespDTO checkDeviceActive(String macAddress, String deviceId, String clientId,
            DeviceReportReqDTO deviceReport) {
        DeviceReportRespDTO response = new DeviceReportRespDTO();
        response.setServerTime(buildServerTime());
        // todo: 此处是固件信息，目前是针对固件上传上来的版本号再返回回去
        // 在未来开发了固件更新功能，需要更换此处代码，
        // 或写定时任务定期请求虾哥的OTA，获取最新的版本讯息保存到服务内
        DeviceReportRespDTO.Firmware firmware = new DeviceReportRespDTO.Firmware();
        firmware.setVersion(deviceReport.getApplication().getVersion());
        firmware.setUrl("http://localhost:8002/xiaozhi-esp32-api/api/v1/ota/download");
        response.setFirmware(firmware);

        DeviceEntity deviceById = getDeviceById(deviceId);
        if (deviceById != null) { // 如果设备存在，则更新上次连接时间
            deviceById.setLastConnectedAt(new Date());
            deviceDao.updateById(deviceById);
        } else { // 如果设备不存在，则生成激活码
            String safeDeviceId = deviceId.replace(":", "_").toLowerCase();
            String dataKey = String.format("ota:activation:data:%s", safeDeviceId);

            Map<Object, Object> cacheMap = redisTemplate.opsForHash().entries(dataKey);
            DeviceReportRespDTO.Activation code = new DeviceReportRespDTO.Activation();

            if (cacheMap != null && cacheMap.containsKey("activation_code")) {
                String cachedCode = (String) cacheMap.get("activation_code");
                code.setCode(cachedCode);
                code.setMessage(frontedUrl + "\n" + cachedCode);
            } else {
                String newCode = RandomUtil.randomNumbers(6);
                code.setCode(newCode);
                code.setMessage(frontedUrl + "\n" + newCode);

                Map<String, Object> dataMap = new HashMap<>();
                dataMap.put("id", deviceId);
                dataMap.put("mac_address", macAddress);
                dataMap.put("board", (deviceReport.getChipModelName() != null) ? deviceReport.getChipModelName()
                        : (deviceReport.getBoard() != null ? deviceReport.getBoard().getType() : "unknown"));
                dataMap.put("app_version", (deviceReport.getApplication() != null)
                        ? deviceReport.getApplication().getVersion()
                        : null);
                dataMap.put("deviceId", deviceId);
                dataMap.put("activation_code", newCode);

                // 写入主数据 key
                redisTemplate.opsForHash().putAll(dataKey, dataMap);
                redisTemplate.expire(dataKey, 24, TimeUnit.HOURS);

                // 写入反查激活码 key
                String codeKey = "ota:activation:code:" + newCode;
                redisTemplate.opsForValue().set(codeKey, deviceId, 24, TimeUnit.HOURS);
            }

            response.setActivation(code);
        }

        return response;
    }

    @Override
    public DeviceEntity bindDevice(DeviceBindDTO dto) {
        // 查看是否已经被绑定
        DeviceEntity deviceEntity = baseDao
                .selectOne(new LambdaQueryWrapper<DeviceEntity>().eq(DeviceEntity::getMacAddress, dto.getMacAddress()));
        if (deviceEntity != null) {
            throw new RenException("设备已绑定");
        }
        deviceEntity = ConvertUtils.sourceToTarget(dto, DeviceEntity.class);
        baseDao.insert(deviceEntity);
        return deviceEntity;
    }

    @Override
    public List<DeviceEntity> getUserDevices(Long userId, String agentId) {
        QueryWrapper<DeviceEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        wrapper.eq("agent_id", agentId);
        return baseDao.selectList(wrapper);
    }

    @Override
    public void unbindDevice(Long userId, String deviceId) {
        UpdateWrapper<DeviceEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("user_id", userId);
        wrapper.eq("id", deviceId);
        baseDao.delete(wrapper);
    }

    private DeviceReportRespDTO.ServerTime buildServerTime() {
        DeviceReportRespDTO.ServerTime serverTime = new DeviceReportRespDTO.ServerTime();
        TimeZone tz = TimeZone.getDefault();
        serverTime.setTimestamp(Instant.now().toEpochMilli());
        serverTime.setTimeZone(tz.getID());
        serverTime.setTimezoneOffset(tz.getOffset(System.currentTimeMillis()) / (60 * 1000));
        return serverTime;
    }
}