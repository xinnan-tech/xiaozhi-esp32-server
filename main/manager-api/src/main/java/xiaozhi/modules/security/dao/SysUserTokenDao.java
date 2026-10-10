package xiaozhi.modules.security.dao;

import java.util.Date;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.security.entity.SysUserTokenEntity;

/**
 * 系统用户Token
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Mapper
public interface SysUserTokenDao extends BaseDao<SysUserTokenEntity> {

    SysUserTokenEntity getByToken(String token);

    SysUserTokenEntity getByUserId(Long userId);

    void logout(@Param("userId") Long userId, @Param("expireDate") Date expireDate);

    /**
     * 用旧 token 换新 token 的 CAS 更新：仅当旧 token 未过期且属于指定 user 时才覆盖。
     * 返回受影响行数（0 表示条件不满足 = token 已被并发刷新或过期）。
     */
    int refreshTokenCAS(@Param("userId") Long userId,
            @Param("oldToken") String oldToken,
            @Param("newToken") String newToken,
            @Param("newExpire") Date newExpire,
            @Param("updateDate") Date updateDate);
}
