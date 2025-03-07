package xiaozhi.modules.sys.service.impl;


import com.wf.captcha.SpecCaptcha;
import com.wf.captcha.base.Captcha;
import jakarta.servlet.http.HttpServletResponse;
import lombok.AllArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.sys.service.CaptchaService;

import java.io.IOException;

/**
 * @author zjy
 * @since 2025-3-7
 */
@AllArgsConstructor
@Service("captchaService")
public class CaptchaServiceImpl implements CaptchaService {
    private final RedisUtils redisUtils;

    @Value("${captcha.expire}")
    private Integer captchaExpireTime;


    @Override
    public void create(HttpServletResponse response, String uuid) {
        response.setContentType("image/png");
        response.setHeader("Pragma", "No-cache");
        response.setHeader("Cache-Control", "no-cache");
        response.setDateHeader("Expires", 0);

        // 创建验证码对象 宽度、高度、字符长度
        SpecCaptcha captcha = new SpecCaptcha(130, 48, 5);
        // 默认字符类型
        captcha.setCharType(Captcha.TYPE_DEFAULT);
        // 缓存验证码
        redisUtils.set(uuid,captcha.text(),captchaExpireTime);

        // 输出验证码图片
        try {
            captcha.out(response.getOutputStream());
        } catch (IOException e) {
            throw new RenException(ErrorCode.VERIFICATION_CODE,"验证码生成错误");
        }
    }

    @Override
    public void validate(String uuid, String code) {
        // 从缓存中获取验证码
        Object storedCode = redisUtils.get(uuid);
        //对验证码进行验证过程
        if(storedCode == null){
            throw new RenException(ErrorCode.VERIFICATION_CODE,"验证码过期，请从新获取");
        }else if(code.equalsIgnoreCase(storedCode.toString())){
            throw new RenException(ErrorCode.VERIFICATION_CODE,"验证码错误");
        }
        // 从缓存删除验证码
        redisUtils.delete(uuid);
    }
}
