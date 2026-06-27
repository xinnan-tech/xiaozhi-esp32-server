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
        if (subject == null) {
            return null;
        }

        UserDetail user = (UserDetail) subject.getPrincipal();
        if (user == null) {
            return null;
        }

        return user;
    }

    public static String getToken() {
        UserDetail user = getUser();
        return user != null ? user.getToken() : null;
    }

    /**
     * 获取用户ID
     */
    public static Long getUserId() {
        UserDetail user = getUser();
        return user != null ? user.getId() : null;
    }
}