package xiaozhi.modules.knowledge.rag;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

/**
 * 知识库适配器工厂类
 * 负责创建和管理不同类型的知识库API适配器
 */
@Slf4j
public class KnowledgeBaseAdapterFactory {

    // 注册的适配器类型映射
    private static final Map<String, Class<? extends KnowledgeBaseAdapter>> adapterRegistry = new HashMap<>();

    // 适配器实例缓存
    private static final Map<String, KnowledgeBaseAdapter> adapterCache = new ConcurrentHashMap<>();

    static {
        // 注册内置适配器类型
        registerAdapter("ragflow", xiaozhi.modules.knowledge.rag.impl.RAGFlowAdapter.class);
        // 可以在这里注册更多适配器类型
    }

    /**
     * 注册新的适配器类型
     * 
     * @param adapterType  适配器类型标识
     * @param adapterClass 适配器类
     */
    public static void registerAdapter(String adapterType, Class<? extends KnowledgeBaseAdapter> adapterClass) {
        if (adapterRegistry.containsKey(adapterType)) {
            log.warn("适配器类型 '{}' 已存在，将被覆盖", adapterType);
        }
        adapterRegistry.put(adapterType, adapterClass);
        log.info("注册适配器类型: {} -> {}", adapterType, adapterClass.getSimpleName());
    }

    /**
     * 获取适配器实例
     * 
     * @param adapterType 适配器类型
     * @param config      配置参数
     * @return 适配器实例
     */
    public static KnowledgeBaseAdapter getAdapter(String adapterType, Map<String, Object> config) {
        String cacheKey = buildCacheKey(adapterType, config);

        // 检查缓存中是否已存在实例
        if (adapterCache.containsKey(cacheKey)) {
            log.debug("从缓存获取适配器实例: {}", cacheKey);
            return adapterCache.get(cacheKey);
        }

        // 创建新的适配器实例
        KnowledgeBaseAdapter adapter = createAdapter(adapterType, config);

        // 缓存适配器实例
        adapterCache.put(cacheKey, adapter);
        log.info("创建并缓存适配器实例: {}", cacheKey);

        return adapter;
    }

    /**
     * 获取适配器实例（无配置）
     * 
     * @param adapterType 适配器类型
     * @return 适配器实例
     */
    public static KnowledgeBaseAdapter getAdapter(String adapterType) {
        return getAdapter(adapterType, null);
    }

    /**
     * 获取所有已注册的适配器类型
     * 
     * @return 适配器类型集合
     */
    public static Set<String> getRegisteredAdapterTypes() {
        return adapterRegistry.keySet();
    }

    /**
     * 检查适配器类型是否已注册
     * 
     * @param adapterType 适配器类型
     * @return 是否已注册
     */
    public static boolean isAdapterTypeRegistered(String adapterType) {
        return adapterRegistry.containsKey(adapterType);
    }

    /**
     * 清除适配器缓存
     */
    public static void clearCache() {
        int cacheSize = adapterCache.size();
        adapterCache.clear();
        log.info("清除适配器缓存，共清除 {} 个实例", cacheSize);
    }

    /**
     * 移除特定适配器类型的缓存
     * 
     * @param adapterType 适配器类型
     */
    public static void removeCacheByType(String adapterType) {
        int removedCount = 0;
        for (String cacheKey : adapterCache.keySet()) {
            if (cacheKey.startsWith(adapterType + "@")) {
                adapterCache.remove(cacheKey);
                removedCount++;
            }
        }
        log.info("移除适配器类型 '{}' 的缓存，共移除 {} 个实例", adapterType, removedCount);
    }

    /**
     * 获取适配器工厂状态信息
     * 
     * @return 状态信息
     */
    public static Map<String, Object> getFactoryStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("registeredAdapterTypes", adapterRegistry.keySet());
        status.put("cachedAdapterCount", adapterCache.size());
        status.put("cacheKeys", adapterCache.keySet());
        return status;
    }

    /**
     * 创建适配器实例
     * 
     * @param adapterType 适配器类型
     * @param config      配置参数
     * @return 适配器实例
     */
    private static KnowledgeBaseAdapter createAdapter(String adapterType, Map<String, Object> config) {
        if (!adapterRegistry.containsKey(adapterType)) {
            throw new RenException(ErrorCode.RAG_ADAPTER_TYPE_NOT_SUPPORTED,
                    "不支持的适配器类型: " + adapterType);
        }

        try {
            Class<? extends KnowledgeBaseAdapter> adapterClass = adapterRegistry.get(adapterType);
            KnowledgeBaseAdapter adapter = adapterClass.getDeclaredConstructor().newInstance();

            // 初始化适配器
            if (config != null) {
                adapter.initialize(config);

                // 验证配置
                if (!adapter.validateConfig(config)) {
                    throw new RenException(ErrorCode.RAG_CONFIG_VALIDATION_FAILED,
                            "适配器配置验证失败: " + adapterType);
                }
            }

            log.info("成功创建适配器实例: {}", adapterType);
            return adapter;

        } catch (Exception e) {
            log.error("创建适配器实例失败: {}", adapterType, e);
            throw new RenException(ErrorCode.RAG_ADAPTER_CREATION_FAILED,
                    "创建适配器失败: " + adapterType + ", 错误: " + e.getMessage());
        }
    }

    /**
     * 构建缓存键
     * 
     * @param adapterType 适配器类型
     * @param config      配置参数
     * @return 缓存键
     */
    private static String buildCacheKey(String adapterType, Map<String, Object> config) {
        if (config == null || config.isEmpty()) {
            return adapterType + "@default";
        }

        // 基于配置参数生成缓存键
        StringBuilder keyBuilder = new StringBuilder(adapterType + "@");

        // 使用配置的哈希值作为缓存键的一部分
        int configHash = config.hashCode();
        keyBuilder.append(configHash);

        return keyBuilder.toString();
    }
}