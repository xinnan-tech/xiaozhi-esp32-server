package xiaozhi.common.cache;

import java.util.Collection;
import java.util.Map;

/**
 * 缓存工具的通用方法定义
 * @author zjy
 * @since 2025-3-11
 */
public interface CacheUtils {
    // 基础键值对操作
    /**
     * 将一个值存储在缓存中，并设置过期时间
     * @param key 键
     * @param value 值
     * @param expire 过期时间（秒）
     */
    void set(String key, Object value, long expire);

    /**
     * 将一个值存储在缓存中，使用默认过期时间
     * @param key 键
     * @param value 值
     */
    void set(String key, Object value);

    /**
     * 从缓存中获取一个值，并设置新的过期时间
     * @param key 键
     * @param expire 过期时间（秒）
     * @return 缓存中对应键的值
     */
    Object get(String key, long expire);

    /**
     * 从缓存中获取一个值
     * @param key 键
     * @return 缓存中对应键的值
     */
    Object get(String key);

    /**
     * 从缓存删除一个值
     * @param key 键
     */
    void delete(String key);

    /**
     * 从缓存批量删除多个值
     * @param keys 包含多个键的集合
     */
    void delete(Collection<String> keys);

    // 哈希操作

    /**
     * 将一对键值对（map）存入缓存,默认过期时间
     * @param key 缓存的key
     * @param field 值的key
     * @param value 值的value
     */
    void hSet(String key, String field, Object value);

    /**
     * 将一对键值对（map）存入缓存,设置过期时间
     * @param key 缓存的key
     * @param field 值的key
     * @param value 值的value
     * @param expire 过期时间
     */
    void hSet(String key, String field, Object value, long expire);

    /**
     * 获取指定缓存里键值对组，里的指定键的值
     * @param key 缓存的key
     * @param field 值的key
     * @return 值的value
     */
    Object hGet(String key, String field);

    /**
     * 获取指定缓存里所有键值对
     * @param key 缓存的key
     * @return 键值对集合
     */
    Map<String, Object> hGetAll(String key);

    /**
     * 将一组键值对（map）存入缓存,默认过期时间
     * @param key 缓存的key
     * @param map 存入的键值对数据
     */
    void hMSet(String key, Map<String, Object> map);

    /**
     * 将一组键值对（map）存入缓存,设置过期时间
     * @param key 缓存的key
     * @param map 存入的键值对数据
     * @param expire 过期时间
     */
    void hMSet(String key, Map<String, Object> map, long expire);

    // 列表操作

    /**
     * 将一个值推入缓存的List结构的左侧，默认过期时间
     * @param key 缓存的key
     * @param value 值
     */
    void leftPush(String key, Object value);

    /**
     * 将一个值推入缓存的List结构的左侧，设置过期时间
     * @param key 缓存的key
     * @param value 值
     * @param expire 过期时间
     */
    void leftPush(String key, Object value, long expire);

    /**
     * 从缓存的List结构的右侧弹出一个值。
     * @param key 缓存的key
     * @return 值
     */
    Object rightPop(String key);


    // 设置过期时间
    /**
     * 指定一个缓存的key，设置过期时间
     * @param key 缓存的key
     * @param expire 过期时间
     */
    void expire(String key, long expire);
}
