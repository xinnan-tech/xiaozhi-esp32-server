package xiaozhi.modules.sys.service.impl;

import lombok.AllArgsConstructor;
import org.springframework.stereotype.Service;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysUserUtilService;

import java.util.function.Consumer;

@Service
@AllArgsConstructor
public class SysUserUtilServiceImpl extends BaseServiceImpl<SysUserDao, SysUserEntity> implements SysUserUtilService {

    private RedisUtils redisUtils;

    @Override
    public void assignUsername(Long userId, Consumer<String> setter) {
        String userIdKey = RedisKeys.getUserIdKey(userId);
        String username = redisUtils.get(userIdKey).toString();
        if(username != null){
            setter.accept(username);
        }else {
            SysUserEntity entity = baseDao.selectById(userId);
            if (entity != null) {
                username = entity.getUsername();
                redisUtils.set(userIdKey,username,10);
                setter.accept(username);
            }
        }
    }
}
