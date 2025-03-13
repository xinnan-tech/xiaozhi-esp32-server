package xiaozhi.common.redis;

/**
 * Redis Key 常量类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class RedisKeys {
    /**
     * 系统参数Key
     */
    public static String getSysParamsKey() {
        return "sys:params";
    }

    /**
     * 验证码Key
     */
    public static String getCaptchaKey(String uuid) {
        return "sys:captcha:" + uuid;
    }

    /**
     * 未注册设备验证码Key
     */
    public static String getDeviceCaptchaKey(String captcha) {
        return "sys:device:captcha:" + captcha;
    }
}
