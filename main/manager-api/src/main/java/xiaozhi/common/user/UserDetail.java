package xiaozhi.common.user;

import java.io.Serializable;

import lombok.Data;

/**
 * 登录用户信息
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Data
public class UserDetail implements Serializable {
    private Long id;
    private String username;
    private Integer superAdmin;
    private String token;
    private Integer status;
}