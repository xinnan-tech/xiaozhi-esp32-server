package xiaozhi.modules.feedback.controller;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.apache.commons.lang3.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.feedback.entity.FeedbackRecordEntity;
import xiaozhi.modules.feedback.entity.StoreEntity;
import xiaozhi.modules.feedback.dao.StoreDao;
import xiaozhi.modules.feedback.service.EmployeeService;
import xiaozhi.modules.feedback.service.FeedbackRecordService;
import xiaozhi.modules.feedback.service.StoreService;
import xiaozhi.modules.feedback.vo.EmployeeVO;
import xiaozhi.modules.feedback.vo.StoreVO;

@AllArgsConstructor
@RestController
@RequestMapping("/feedback/public")
@Tag(name = "反馈H5公开接口")
public class FeedbackPublicController {

    private final StoreService storeService;
    private final EmployeeService employeeService;
    private final StoreDao storeDao;
    private final DeviceDao deviceDao;
    private final FeedbackRecordService feedbackRecordService;

    @GetMapping("/store/{storeCode}")
    @Operation(summary = "扫码查门店信息")
    public Result<StoreVO> getStoreByCode(@PathVariable String storeCode) {
        StoreVO store = storeService.getByStoreCode(storeCode);
        if (store == null) {
            return new Result<StoreVO>().error(1001, "门店不存在");
        }
        return new Result<StoreVO>().ok(store);
    }

    @GetMapping("/employees/{storeId}")
    @Operation(summary = "获取门店下的员工列表")
    public Result<List<EmployeeVO>> listEmployees(@PathVariable String storeId) {
        List<EmployeeVO> list = employeeService.listByStoreId(storeId);
        return new Result<List<EmployeeVO>>().ok(list);
    }

    @PostMapping("/device-init")
    @Operation(summary = "初始化设备绑定")
    public Result<Map<String, String>> deviceInit(@RequestBody Map<String, String> params) {
        String storeId = params.get("storeId");
        String employeeId = params.get("employeeId");

        if (StringUtils.isBlank(storeId)) {
            return new Result<Map<String, String>>().error(1002, "门店ID不能为空");
        }

        StoreEntity store = storeDao.selectById(storeId);
        if (store == null) {
            return new Result<Map<String, String>>().error(1001, "门店不存在");
        }
        if (StringUtils.isBlank(store.getAgentId())) {
            return new Result<Map<String, String>>().error(1003, "门店尚未绑定智能体");
        }

        // 生成随机MAC地址
        String mac = generateFeedbackMac();

        // 在ai_device表中注册此设备，绑定到门店对应的智能体
        DeviceEntity device = new DeviceEntity();
        device.setMacAddress(mac);
        device.setAgentId(store.getAgentId());
        device.setBoard("feedback-h5");
        deviceDao.insert(device);

        Map<String, String> result = new HashMap<>();
        result.put("deviceMac", mac);
        result.put("otaUrl", "http://127.0.0.1:8002/xiaozhi/ota/");
        result.put("clientId", "feedback_client");
        return new Result<Map<String, String>>().ok(result);
    }

    @PostMapping("/record")
    @Operation(summary = "保存反馈记录")
    public Result<Void> saveRecord(@RequestBody Map<String, String> params) {
        FeedbackRecordEntity record = new FeedbackRecordEntity();
        record.setStoreId(params.get("storeId"));
        record.setEmployeeId(params.get("employeeId"));
        record.setSessionId(params.get("sessionId"));
        record.setDeviceMac(params.get("deviceMac"));
        record.setRawAsrText(params.get("rawAsrText"));
        record.setCleanedText(params.get("cleanedText"));
        record.setQaJson(params.get("qaJson"));
        record.setReviewLong(params.get("reviewLong"));
        record.setReviewShort(params.get("reviewShort"));
        record.setStatus(1);
        feedbackRecordService.saveRecord(record);
        return new Result<>();
    }

    /**
     * 生成反馈设备MAC地址（以FB开头）
     */
    private String generateFeedbackMac() {
        Random random = new Random();
        StringBuilder mac = new StringBuilder("FB");
        for (int i = 0; i < 5; i++) {
            mac.append(":");
            mac.append(String.format("%02X", random.nextInt(256)));
        }
        return mac.toString();
    }
}
