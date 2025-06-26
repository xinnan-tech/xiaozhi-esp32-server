package xiaozhi.modules.sms.service.imp;

import com.aliyun.dysmsapi20170525.Client;
import com.aliyun.dysmsapi20170525.models.SendSmsRequest;
import com.aliyun.dysmsapi20170525.models.SendSmsResponse;
import com.aliyun.teaopenapi.models.Config;
import com.aliyun.teautil.models.RuntimeOptions;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.sms.service.SmsService;
import xiaozhi.modules.sys.service.SysParamsService;

@Service
@AllArgsConstructor
@Slf4j
public class ALiYunSmsService implements SmsService {
    private final SysParamsService  sysParamsService;
    private final RedisUtils redisUtils;

    @Override
    public void sendVerificationCodeSms(String phone, String VerificationCode) {
        Client client = createClient();
        String SignName = sysParamsService.getValue(Constant.SysMSMParam
                .ALIYUN_SMS_SIGN_NAME.getValue(),true);
        String TemplateCode = sysParamsService.getValue(Constant.SysMSMParam
                .ALIYUN_SMS_SMS_CODE_TEMPLATE_CODE.getValue(),true);
        try {
            SendSmsRequest sendSmsRequest = new SendSmsRequest()
                    .setSignName(SignName)
                    .setTemplateCode(TemplateCode)
                    .setPhoneNumbers(phone)
                    .setTemplateParam(String.format("{\"code\":\"%s\"}", VerificationCode));
            RuntimeOptions runtime = new RuntimeOptions();
            // 复制代码运行请自行打印 API 的返回值
            SendSmsResponse sendSmsResponse = client.sendSmsWithOptions(sendSmsRequest, runtime);
            log.info("发送短信响应的requestID: {}", sendSmsResponse.getBody().getRequestId());
        } catch (Exception e) {
            // 如果发送失败了退还这次发送数
            String todayCountKey = RedisKeys.getSMSTodayCountKey(phone);
            redisUtils.delete(todayCountKey);
            // 错误 message
            log.error(e.getMessage());
            throw new RenException("短信发送失败");
        }

    }


    /**
     * 创建阿里云连接
     * @return 返回连接对象
     */
    private Client createClient(){
        String ACCESS_KEY_ID = sysParamsService.getValue(Constant.SysMSMParam
                .ALIYUN_SMS_ACCESS_KEY_ID.getValue(),true);
        String ACCESS_KEY_SECRET = sysParamsService.getValue(Constant.SysMSMParam
                .ALIYUN_SMS_ACCESS_KEY_SECRET.getValue(),true);
        try {
            Config config = new Config()
                    .setAccessKeyId(ACCESS_KEY_ID)
                    .setAccessKeySecret(ACCESS_KEY_SECRET);
            // 配置 Endpoint。中国站请使用dysmsapi.aliyuncs.com
            config.endpoint = "dysmsapi.aliyuncs.com";
            return new Client(config);
        }catch (Exception e){
            // 错误 message
            log.error(e.getMessage());
            throw new RenException("短信连接建立失败");
        }
    }
}
