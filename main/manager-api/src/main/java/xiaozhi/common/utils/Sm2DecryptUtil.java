package xiaozhi.common.utils;

import org.apache.commons.lang3.StringUtils;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.security.service.CaptchaService;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * SM2解密和验证码验证工具类
 * 封装了重复的SM2解密、验证码提取和验证逻辑
 */
public class Sm2DecryptUtil {
    
    /**
     * 验证码长度
     */
    private static final int CAPTCHA_LENGTH = 5;
    
    /**
     * 解密SM2加密内容，提取验证码并验证
     * @param encryptedPassword SM2加密的密码字符串
     * @param captchaId 验证码ID
     * @param captchaService 验证码服务
     * @param sysParamsService 系统参数服务
     * @return 解密后的实际密码
     */
    public static String decryptAndValidateCaptcha(String encryptedPassword, String captchaId, 
                                                 CaptchaService captchaService, SysParamsService sysParamsService) {
        // 获取SM2私钥
        String privateKeyStr = sysParamsService.getValue(Constant.SM2_PRIVATE_KEY, true);
        if (StringUtils.isBlank(privateKeyStr)) {
            throw new RenException(ErrorCode.SM2_KEY_NOT_CONFIGURED);
        }
        
        // 使用SM2私钥解密密码
        String decryptedContent;
        try {
            decryptedContent = SM2Utils.decrypt(privateKeyStr, encryptedPassword);
        } catch (Exception e) {
            throw new RenException(ErrorCode.SM2_DECRYPT_ERROR);
        }
        
        // 分离验证码和密码：前5位是验证码，后面是密码
        if (decryptedContent.length() > CAPTCHA_LENGTH) {
            String embeddedCaptcha = decryptedContent.substring(0, CAPTCHA_LENGTH);
            String actualPassword = decryptedContent.substring(CAPTCHA_LENGTH);
            
            // 验证嵌入的验证码是否正确
            boolean embeddedCaptchaValid = captchaService.validate(captchaId, embeddedCaptcha, true);
            if (!embeddedCaptchaValid) {
                throw new RenException(ErrorCode.SMS_CAPTCHA_ERROR);
            }
            
            return actualPassword;
        } else {
            throw new RenException(ErrorCode.SM2_DECRYPT_ERROR);
        }
    }
}