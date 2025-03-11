package xiaozhi.common.cache;

import java.util.Collection;
import java.util.Map;

/**
 * 缓存的通用方法
 * @author zjy
 * @since 2025-3-11
 */
public interface CacheUtils {
    // 基础键值对操作
    void set(String key, Object value, long expire);
    void set(String key, Object value);
    Object get(String key, long expire);
    Object get(String key);
    void delete(String key);
    void delete(Collection<String> keys);

    // 哈希操作
    void hSet(String key, String field, Object value);
    void hSet(String key, String field, Object value, long expire);
    Object hGet(String key, String field);
    Map<String, Object> hGetAll(String key);
    void hMSet(String key, Map<String, Object> map);
    void hMSet(String key, Map<String, Object> map, long expire);

    // 列表操作
    void leftPush(String key, Object value);
    void leftPush(String key, Object value, long expire);
    Object rightPop(String key);

    // 设置过期时间
    void expire(String key, long expire);
}
