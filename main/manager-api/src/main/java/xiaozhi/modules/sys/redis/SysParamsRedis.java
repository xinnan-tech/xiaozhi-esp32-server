package xiaozhi.modules.sys.redis;

import org.springframework.stereotype.Component;

import lombok.AllArgsConstructor;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;

/**
 * 参数管理
 */
@AllArgsConstructor
@Component
public class SysParamsRedis {
    private final RedisUtils redisUtils;

    public void delete(Object[] paramCodes) {
        String key = RedisKeys.getSysParamsKey();
        redisUtils.hDel(key, paramCodes);
    }

    public void set(String paramCode, String paramValue) {
        if (paramValue == null) {
            return;
        }
        String key = RedisKeys.getSysParamsKey();
        redisUtils.hSet(key, paramCode, paramValue);
    }

    public String get(String paramCode) {
        String key = RedisKeys.getSysParamsKey();
        return (String) redisUtils.hGet(key, paramCode);
    }

}
