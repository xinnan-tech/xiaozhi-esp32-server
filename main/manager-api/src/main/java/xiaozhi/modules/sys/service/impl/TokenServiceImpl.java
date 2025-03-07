package xiaozhi.modules.sys.service.impl;

import lombok.AllArgsConstructor;
import org.springframework.stereotype.Service;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.security.oauth2.TokenGenerator;
import xiaozhi.modules.sys.service.TokenService;

import java.util.Date;

@AllArgsConstructor
@Service
public class TokenServiceImpl implements TokenService {
    private final RedisUtils redisUtils;
    /**
     * 3小时无操作过期
     */
    private final static int EXPIRE = 60 * 60 * 3;

    @Override
    public String createToken(long userId) {
        //生成一个token
        String token = TokenGenerator.generateValue();

        //当前时间
        Date now = new Date();
        //过期时间
        Date expireTime = new Date(now.getTime() + EXPIRE * 1000);
        return token;
    }
}
