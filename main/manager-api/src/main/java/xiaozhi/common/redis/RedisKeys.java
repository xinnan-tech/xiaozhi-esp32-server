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
     * 登录用户Key
     */
    public static String getSecurityUserKey(Long id) {
        return "sys:security:user:" + id;
    }

    /**
     * 系统日志Key
     */
    public static String getSysLogKey() {
        return "sys:log";
    }

    /**
     * 系统资源Key
     */
    public static String getSysResourceKey() {
        return "sys:resource";
    }

    /**
     * 用户菜单导航Key
     */
    public static String getUserMenuNavKey(Long userId) {
        return "sys:user:nav:" + userId;
    }

    /**
     * 用户权限标识Key
     */
    public static String getUserPermissionsKey(Long userId) {
        return "sys:user:permissions:" + userId;
    }

    /**
     * 用户登陆错误次数
     *
     * @param username
     * @return
     */
    public static String getUserLoginErrorCountKey(String username) {
        return "sys:user:login:error:" + username;
    }

    public static String getUserInfoKey(Long userId) {
        return "sys:user:" + userId;
    }

    public static String getDataScopeListKey(Long userId) {
        return "sys:user:data:scope:" + userId;
    }

    public static String getSysUserName(Long id) {
        return "sys:user:name" + id;
    }

}
