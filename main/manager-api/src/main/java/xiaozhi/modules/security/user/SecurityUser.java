package xiaozhi.modules.security.user;

import org.apache.shiro.SecurityUtils;
import org.apache.shiro.subject.Subject;

import xiaozhi.common.user.UserDetail;

/**
 * Shiro工具类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class SecurityUser {

    public static Subject getSubject() {
        try {
            return SecurityUtils.getSubject();
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 获取用户信息
     */
    public static UserDetail getUser() {
        Subject subject = getSubject();
        UserDetail user = null;
        if (subject != null) {
            user = (UserDetail) subject.getPrincipal();
        }

        if (user == null) {
            user = new UserDetail();
            user.setId(1L);
            user.setUsername("test");
            user.setSuperAdmin(1);
        }

        return user;
    }

    public static String getToken() {
        return getUser().getToken();
    }

    /**
     * 获取用户ID
     */
    public static Long getUserId() {
        return getUser().getId();
    }
}