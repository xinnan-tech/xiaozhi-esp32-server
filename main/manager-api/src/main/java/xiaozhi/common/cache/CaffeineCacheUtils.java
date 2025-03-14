package xiaozhi.common.cache;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Expiry;
import org.checkerframework.checker.index.qual.NonNegative;
import org.checkerframework.checker.nullness.qual.NonNull;
import org.springframework.stereotype.Component;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * 基于Caffeine写的缓存工具类
 * @author zjy
 * @since 2025-3-12
 */
@Component
public class CaffeineCacheUtils implements CacheUtils{
    // 自定义包装类，用于存储缓存值和对应的过期时间
    private static class CacheEntry<T> {
        T value; // 缓存值
        long expireNanos; // 过期时间（纳秒）

        public CacheEntry(T value, long expireNanos) {
            this.value = value;
            this.expireNanos = expireNanos;
        }
    }

    private final Cache<String, CacheEntry<?>> CACHE;
    public CaffeineCacheUtils() {
        // 创建一个 Caffeine 缓存实例
        CACHE = Caffeine.newBuilder()
                .expireAfter(new Expiry<String, CacheEntry<?>>() {
                    @Override
                    public long expireAfterCreate(@NonNull String key, @NonNull CacheEntry<?> cacheEntry, long currentTime) {
                        return  cacheEntry.expireNanos; // 返回包装类中的过期时间
                    }

                    @Override
                    public long expireAfterUpdate(@NonNull String key, @NonNull CacheEntry<?> cacheEntry, long currentTime, @NonNegative long currentDuration) {
                        return cacheEntry.expireNanos; // 更新时也使用包装类中的过期时间
                    }

                    @Override
                    public long expireAfterRead(@NonNull String key, @NonNull CacheEntry<?> cacheEntry, long currentTime, @NonNegative long currentDuration) {
                        return currentDuration; // 读取时也使用包装类中的过期时间
                    }
                })
                .build();
    }
    /**
     *
     * @param key 缓存key
     * @param value 值
     * @param duration 过期时间
     * @param unit 过期单位
     * @param <T> 泛型
     */
    private <T> void cachePut(String key, T value, long duration, TimeUnit unit) {
        long expireNanos = unit.toNanos(duration); // 将过期时间转换为纳秒
        CacheEntry<T> cacheEntry = new CacheEntry<>(value, expireNanos);
        CACHE.put(key, cacheEntry); // 将包装类放入缓存
    }

    /**
     *
     * @param key 缓存key
     * @param clazz 返回类型的值
     * @return 值
     * @param <T> 泛型
     */
    private <T> T cacheGet(String key, Class<T> clazz) {
        CacheEntry<?> cacheEntry = CACHE.getIfPresent(key); // 获取包装类
        if (cacheEntry == null) {
            return null; // 如果缓存不存在，返回 null
        }
        if (!clazz.isInstance(cacheEntry.value) ){
            throw new RenException(ErrorCode.CAFFEINE_ERROR);
        }
        return clazz.cast(cacheEntry.value); // 返回包装类中的值
    }

    public final static long DEFAULT_EXPIRE = 60 * 60 * 24L; // 默认过期时长为24小时，单位：秒
    public final static long HOUR_ONE_EXPIRE = 60 * 60 ; // 过期时长为1小时，单位：秒
    public final static long HOUR_SIX_EXPIRE = 60 * 60 * 6L; // 过期时长为6小时，单位：秒
    public final static long NOT_EXPIRE = -1L; // 不设置过期时长
    @Override
    public void set(String key, Object value, long expire) {
        if (expire == NOT_EXPIRE) {
            cachePut(key, value, Long.MAX_VALUE, TimeUnit.SECONDS);
        } else {
            cachePut(key, value, expire, TimeUnit.SECONDS);
        }
    }

    @Override
    public void set(String key, Object value) {
        cachePut(key, value, DEFAULT_EXPIRE, TimeUnit.SECONDS);
    }

    @Override
    public Object get(String key, long expire) {
        Object object = cacheGet(key, Object.class);
        cachePut(key, object, expire, TimeUnit.SECONDS);
        return object;
    }

    @Override
    public Object get(String key) {
        return cacheGet(key, Object.class);
    }

    @Override
    public void delete(String key) {
        CACHE.invalidate(key);
    }

    @Override
    public void delete(Collection<String> keys) {
        CACHE.invalidateAll(keys);
    }

    @Override
    public void hSet(String key, String field, Object value) {
        Map<String, Object> stringObjectMap = hGetAll(key);
        if (stringObjectMap == null){
            stringObjectMap = new HashMap<>();
        }
        stringObjectMap.put(field, value);
        cachePut(key, stringObjectMap, DEFAULT_EXPIRE, TimeUnit.SECONDS);
    }

    @Override
    public void hSet(String key, String field, Object value, long expire) {
        Map<String, Object> stringObjectMap = hGetAll(key);
        if (stringObjectMap == null){
            stringObjectMap = new HashMap<>();
        }
        stringObjectMap.put(field, value);
        if (expire == NOT_EXPIRE) {
            cachePut(key, stringObjectMap, Long.MAX_VALUE, TimeUnit.SECONDS);
        } else {
            cachePut(key, stringObjectMap, expire, TimeUnit.SECONDS);
        }

    }

    @Override
    public Object hGet(String key, String field) {
        Map<String, Object> stringObjectMap = hGetAll(key);
        return stringObjectMap.get(field);
    }

    @Override
    public Map<String, Object> hGetAll(String key) {
        return cacheGet(key, Map.class);
    }

    @Override
    public void hMSet(String key, Map<String, Object> map) {
        Map<String, Object> stringObjectMap = hGetAll(key);
        if (stringObjectMap == null){
            stringObjectMap = new HashMap<>(map);
        }else {
            stringObjectMap.putAll(map);
        }
        cachePut(key, stringObjectMap, DEFAULT_EXPIRE, TimeUnit.SECONDS);
    }

    @Override
    public void hMSet(String key, Map<String, Object> map, long expire) {
        Map<String, Object> stringObjectMap = hGetAll(key);
        if (stringObjectMap == null){
            stringObjectMap = new HashMap<>(map);
        }else {
            stringObjectMap.putAll(map);
        }
        if (expire == NOT_EXPIRE) {
            cachePut(key, stringObjectMap, Long.MAX_VALUE, TimeUnit.SECONDS);
        } else {
            cachePut(key, stringObjectMap, expire, TimeUnit.SECONDS);
        }
    }

    @Override
    public void leftPush(String key, Object value) {
        // 获取当前缓存中的栈
        LinkedList <Object> stack = cacheGet(key, LinkedList .class);
        // 如果不存在，创建一个新的 LinkedList
        if (stack == null) {
            stack = new LinkedList <>();
        }
        stack.addFirst(value); // 在栈顶（左侧）插入值
        cachePut(key, stack, DEFAULT_EXPIRE, TimeUnit.SECONDS);
    }

    @Override
    public void leftPush(String key, Object value, long expire) {
        LinkedList <Object> stack = cacheGet(key, LinkedList .class); // 获取当前缓存中的栈
        if (stack == null) {
            stack = new LinkedList <>(); // 如果不存在，创建一个新的 LinkedList
        }
        stack.addFirst(value); // 在栈顶（左侧）插入值
        if (expire == NOT_EXPIRE) {
            cachePut(key, stack, Long.MAX_VALUE, TimeUnit.SECONDS);
        } else {
            cachePut(key, stack, expire, TimeUnit.SECONDS);
        }
    }

    @Override
    public Object rightPop(String key) {
        LinkedList <Object> stack = cacheGet(key, LinkedList .class); // 获取当前缓存中的栈
        if (stack == null || stack.isEmpty()) {
            return null; // 如果栈不存在或为空，返回 null
        }
        Object value = stack.removeLast(); // 从栈底（右侧）弹出一个值
        if (!stack.isEmpty()) {
            cachePut(key, stack, DEFAULT_EXPIRE, TimeUnit.SECONDS); // 如果栈不为空，更新缓存
        } else {
            delete(key); // 如果栈为空，删除缓存
        }
        return value; // 返回弹出的值
    }

    @Override
    public void expire(String key, long expire) {
        CacheEntry<?> cacheEntry = CACHE.getIfPresent(key); // 获取当前缓存条目
        if (cacheEntry != null) {
            if (expire == NOT_EXPIRE) {
                expire = Long.MAX_VALUE; // 设置为永不过期
            } else {
                cacheEntry.expireNanos = TimeUnit.SECONDS.toNanos(expire); // 更新过期时间
            }
            CACHE.put(key, cacheEntry); // 更新缓存条目
        }
    }
}
