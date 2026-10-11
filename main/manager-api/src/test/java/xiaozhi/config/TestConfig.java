package xiaozhi.config;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;

import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.security.service.CaptchaService;

/**
 * Test configuration for mocking external services
 */
@TestConfiguration
@Profile("test")
public class TestConfig {

    /**
     * Mock Redis connection factory for testing
     */
    @Bean
    @Primary
    public RedisConnectionFactory redisConnectionFactory() {
        // Return a mock or in-memory Redis connection factory
        // For now, we'll use LettuceConnectionFactory with localhost
        // In a real scenario, you might want to use embedded Redis
        return new LettuceConnectionFactory();
    }

    /**
     * Mock RedisUtils for testing
     */
    @Bean
    @Primary
    public RedisUtils redisUtils() {
        return new MockRedisUtils();
    }

    /**
     * Mock CaptchaService for testing
     */
    @Bean
    @Primary
    public CaptchaService captchaService() {
        return new MockCaptchaService();
    }

    /**
     * Mock implementation of RedisUtils for testing
     */
    public static class MockRedisUtils extends RedisUtils {
        private final java.util.Map<String, Object> mockCache = new java.util.concurrent.ConcurrentHashMap<>();
        private final java.util.Map<String, java.util.Map<String, Object>> mockHashCache = new java.util.concurrent.ConcurrentHashMap<>();

        @Override
        public void set(String key, Object value) {
            mockCache.put(key, value);
        }

        @Override
        public void set(String key, Object value, long timeout) {
            mockCache.put(key, value);
        }

        @Override
        public Object get(String key) {
            return mockCache.get(key);
        }

        public void delete(String key) {
            mockCache.remove(key);
        }

        public boolean hasKey(String key) {
            return mockCache.containsKey(key);
        }

        public void clear() {
            mockCache.clear();
            mockHashCache.clear();
        }

        // Mock hash operations
        public Object hGet(String key, String field) {
            java.util.Map<String, Object> hash = mockHashCache.get(key);
            return hash != null ? hash.get(field) : null;
        }

        public void hSet(String key, String field, Object value) {
            mockHashCache.computeIfAbsent(key, k -> new java.util.concurrent.ConcurrentHashMap<>()).put(field, value);
        }

        public java.util.Map<String, Object> hGetAll(String key) {
            return mockHashCache.getOrDefault(key, new java.util.HashMap<>());
        }

        public void hDel(String key, String... fields) {
            java.util.Map<String, Object> hash = mockHashCache.get(key);
            if (hash != null) {
                for (String field : fields) {
                    hash.remove(field);
                }
            }
        }

        public boolean hExists(String key, String field) {
            java.util.Map<String, Object> hash = mockHashCache.get(key);
            return hash != null && hash.containsKey(field);
        }
    }

    /**
     * Mock implementation of CaptchaService for testing
     */
    public static class MockCaptchaService implements CaptchaService {
        
        @Override
        public void create(jakarta.servlet.http.HttpServletResponse response, String uuid) throws java.io.IOException {
            // Mock implementation - do nothing
        }

        @Override
        public boolean validate(String uuid, String code, Boolean delete) {
            // Always return true for testing
            return true;
        }

        @Override
        public void sendSMSValidateCode(String phone) {
            // Mock implementation - do nothing
        }

        @Override
        public boolean validateSMSValidateCode(String phone, String code, Boolean delete) {
            // Always return true for testing
            return true;
        }
    }
}
