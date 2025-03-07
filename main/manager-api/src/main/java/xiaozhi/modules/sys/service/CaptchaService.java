package xiaozhi.modules.sys.service;

import jakarta.servlet.http.HttpServletResponse;

/**
 * @author zjy
 * @since 2025-3-7
 */
public interface CaptchaService {
    /**
     * 生成验证码
     * @param response 响应对象
     * @param uuid 验证码唯一id
     */
    void create(HttpServletResponse response, String uuid);

    /**
     * 验证码验证
     * @param uuid 验证码唯一id
     * @param code 验证码内容
     * @return
     */
    void validate(String uuid, String code);
}
