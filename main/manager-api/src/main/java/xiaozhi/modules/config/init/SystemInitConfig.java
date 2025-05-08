package xiaozhi.modules.config.init;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.DependsOn;

import jakarta.annotation.PostConstruct;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.sys.service.SysParamsService;

@Configuration
@DependsOn("liquibase")
public class SystemInitConfig {

    @Autowired
    private SysParamsService sysParamsService;

    @Autowired
    private ConfigService configService;

    @Autowired
    private RedisUtils redisUtils;

    @PostConstruct
    public void init() {
        // 检查版本号
        String redisVersion = (String) redisUtils.get(RedisKeys.getVersionKey());
        if (!Constant.VERSION.equals(redisVersion)) {
            // 如果版本不一致，清空Redis
            redisUtils.emptyAll();
            // 存储新版本号
            redisUtils.set(RedisKeys.getVersionKey(), Constant.VERSION);
        }

        sysParamsService.initServerSecret();
        configService.getConfig(false);
    }
}