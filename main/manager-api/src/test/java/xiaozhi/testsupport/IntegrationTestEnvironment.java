package xiaozhi.testsupport;

import java.io.IOException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.time.Duration;

import org.junit.jupiter.api.Assumptions;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.PropertySource;
import org.springframework.core.env.PropertySourcesPropertyResolver;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;

import io.lettuce.core.RedisClient;
import io.lettuce.core.RedisURI;
import io.lettuce.core.api.StatefulRedisConnection;
import lombok.extern.slf4j.Slf4j;

/**
 * 几个 @SpringBootTest 要真连 MySQL 和 Redis。本地没起这两个依赖时，
 * 整类测试跳过，别让 Spring 上下文起不来变成一堆看不懂的报错；
 * CI 里依赖必须真的在，探不通就直接让构建红。
 */
@Slf4j
public final class IntegrationTestEnvironment {

    /** 集成测试用的配置文件，跟应用本身读的是同一套 */
    private static final String[] CONFIG_FILES = {"application.yml", "application-dev.yml"};

    private static Boolean available;
    private static String problem;

    private IntegrationTestEnvironment() {
    }

    /**
     * 放在要连库的测试类的 @BeforeAll 里。
     * 本地依赖不齐就整类跳过，CI 里依赖不齐就直接失败。
     */
    public static void requireDatabaseAndRedis() {
        String issue = probe();
        if (issue == null) {
            return;
        }
        if (isCi()) {
            throw new IllegalStateException(
                    "CI 环境里" + issue + "，这几个集成测试必须真的跑起来，不能跳过");
        }
        log.warn("跳过依赖 MySQL 和 Redis 的集成测试：{}", issue);
        Assumptions.assumeTrue(false, issue);
    }

    /** GitHub Actions 上会带 CI=true */
    public static boolean isCi() {
        String value = System.getenv("CI");
        if (value == null) {
            return false;
        }
        String trimmed = value.trim();
        return !trimmed.isEmpty() && !"false".equalsIgnoreCase(trimmed);
    }

    /** 依赖都齐返回 null，不齐返回缺什么 */
    static synchronized String probe() {
        if (available != null) {
            return problem;
        }
        PropertySourcesPropertyResolver resolver = resolver();
        StringBuilder issues = new StringBuilder();

        String url = firstNonBlank(resolver.getProperty("spring.datasource.druid.url", ""),
                resolver.getProperty("spring.datasource.url", ""));
        String username = firstNonBlank(resolver.getProperty("spring.datasource.druid.username", ""),
                resolver.getProperty("spring.datasource.username", ""));
        String password = firstNonBlank(resolver.getProperty("spring.datasource.druid.password", ""),
                resolver.getProperty("spring.datasource.password", ""));
        if (url.isBlank()) {
            issues.append("配置里找不到数据源地址；");
        } else {
            try {
                DriverManager.setLoginTimeout(5);
                try (Connection connection = DriverManager.getConnection(url, username, password)) {
                    connection.isValid(3);
                }
            } catch (Exception e) {
                issues.append("连不上 MySQL（").append(e.getMessage()).append("）；");
            }
        }

        String redisHost = resolver.getProperty("spring.data.redis.host", "localhost");
        int redisPort = resolver.getProperty("spring.data.redis.port", Integer.class, 6379);
        String redisPassword = resolver.getProperty("spring.data.redis.password", "");
        try {
            RedisURI.Builder builder = RedisURI.builder()
                    .withHost(redisHost)
                    .withPort(redisPort)
                    .withTimeout(Duration.ofSeconds(3));
            if (redisPassword != null && !redisPassword.isBlank()) {
                builder.withPassword(redisPassword.toCharArray());
            }
            RedisClient client = RedisClient.create(builder.build());
            try {
                StatefulRedisConnection<String, String> connection = client.connect();
                connection.sync().ping();
                connection.close();
            } finally {
                client.shutdown();
            }
        } catch (Exception e) {
            issues.append("连不上 Redis（").append(e.getMessage()).append("）；");
        }

        if (issues.length() == 0) {
            available = Boolean.TRUE;
            problem = null;
        } else {
            available = Boolean.FALSE;
            problem = issues.toString();
        }
        return problem;
    }

    /** 读应用自己那份配置，命令行上的 -D 参数优先级更高，跟应用保持一致 */
    private static PropertySourcesPropertyResolver resolver() {
        ConfigurableEnvironment environment = new StandardEnvironment();
        YamlPropertySourceLoader loader = new YamlPropertySourceLoader();
        for (String name : CONFIG_FILES) {
            Resource resource = new ClassPathResource(name);
            if (!resource.exists()) {
                continue;
            }
            try {
                for (PropertySource<?> source : loader.load(name, resource)) {
                    environment.getPropertySources().addLast(source);
                }
            } catch (IOException e) {
                log.warn("读配置 {} 失败：{}", name, e.getMessage());
            }
        }
        return new PropertySourcesPropertyResolver(environment.getPropertySources());
    }

    private static String firstNonBlank(String first, String second) {
        return first != null && !first.isBlank() ? first : (second == null ? "" : second);
    }
}
