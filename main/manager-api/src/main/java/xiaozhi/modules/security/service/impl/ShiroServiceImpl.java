package xiaozhi.modules.security.service.impl;

import org.springframework.stereotype.Service;

import lombok.AllArgsConstructor;
import xiaozhi.modules.security.dao.SysUserTokenDao;
import xiaozhi.modules.security.entity.SysUserTokenEntity;
import xiaozhi.modules.security.service.ShiroService;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.entity.SysUserEntity;

@AllArgsConstructor
@Service
public class ShiroServiceImpl implements ShiroService {
    private final SysUserDao sysUserDao;
    private final SysUserTokenDao sysUserTokenDao;

    @Override
    public SysUserTokenEntity getByToken(String token) {
        return sysUserTokenDao.getByToken(token);
    }

    @Override
    public SysUserEntity getUser(Long userId) {
        return sysUserDao.selectById(userId);
    }
}