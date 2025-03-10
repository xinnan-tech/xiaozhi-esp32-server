package xiaozhi;

import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.sys.entity.SysUserEntity;
import jakarta.annotation.Resource;
import org.apache.commons.lang3.builder.ToStringBuilder;
// 若使用 JUnit 5，应导入以下包
import org.junit.jupiter.api.Test;
// 由于代码中使用了 JUnit 5 的 @Test 注解，应移除 JUnit 4 的 @RunWith 相关导入
// import org.junit.runner.RunWith;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit4.SpringRunner;

// 由于代码中使用了 JUnit 5 的 @Test 注解，应移除 JUnit 4 的 @RunWith 相关代码
// @RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class RedisTest {
    @Resource
    private RedisUtils redisUtils;

    @Test
    public void contextLoads() {
        SysUserEntity user = new SysUserEntity();
        user.setEmail("123456@qq.com");
        redisUtils.set("user", user);

        System.out.println(ToStringBuilder.reflectionToString(redisUtils.get("user")));
    }

}