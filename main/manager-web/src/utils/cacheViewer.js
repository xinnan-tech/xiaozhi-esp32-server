/**
 * 缓存查看工具 - 用于检查CDN资源是否已被Service Worker缓存
 */

/**
 * 获取所有Service Worker缓存的名称
 * @returns {Promise<string[]>} 缓存名称列表
 */
export const getCacheNames = async () => {
  if (!('caches' in window)) {
    return [];
  }
  
  try {
    return await caches.keys();
  } catch (error) {
    console.error('获取缓存名称失败:', error);
    return [];
  }
};

/**
 * 获取指定缓存中的所有URL
 * @param {string} cacheName 缓存名称
 * @returns {Promise<string[]>} 缓存的URL列表
 */
export const getCacheUrls = async (cacheName) => {
  if (!('caches' in window)) {
    return [];
  }
  
  try {
    const cache = await caches.open(cacheName);
    const requests = await cache.keys();
    return requests.map(request => request.url);
  } catch (error) {
    console.error(`获取缓存 ${cacheName} 的URL失败:`, error);
    return [];
  }
};

/**
 * 检查特定URL是否已被缓存
 * @param {string} url 要检查的URL
 * @returns {Promise<boolean>} 是否已缓存
 */
export const isUrlCached = async (url) => {
  if (!('caches' in window)) {
    return false;
  }
  
  try {
    const cacheNames = await getCacheNames();
    for (const cacheName of cacheNames) {
      const cache = await caches.open(cacheName);
      const match = await cache.match(url);
      if (match) {
        return true;
      }
    }
    return false;
  } catch (error) {
    console.error(`检查URL ${url} 是否缓存失败:`, error);
    return false;
  }
};

/**
 * 获取当前页面所有CDN资源的缓存状态
 * @returns {Promise<Object>} 缓存状态对象
 */
export const checkCdnCacheStatus = async () => {
  // 从CDN缓存中查找资源
  const cdnCaches = ['cdn-stylesheets', 'cdn-scripts'];
  const results = {
    css: [],
    js: [],
    totalCached: 0,
    totalNotCached: 0
  };
  
  for (const cacheName of cdnCaches) {
    try {
      const urls = await getCacheUrls(cacheName);
      
      // 区分CSS和JS资源
      for (const url of urls) {
        if (url.endsWith('.css')) {
          results.css.push({ url, cached: true });
        } else if (url.endsWith('.js')) {
          results.js.push({ url, cached: true });
        }
        results.totalCached++;
      }
    } catch (error) {
      console.error(`获取 ${cacheName} 缓存信息失败:`, error);
    }
  }
  
  return results;
};

/**
 * 清除所有Service Worker缓存
 * @returns {Promise<boolean>} 是否成功清除
 */
export const clearAllCaches = async () => {
  if (!('caches' in window)) {
    return false;
  }
  
  try {
    const cacheNames = await getCacheNames();
    for (const cacheName of cacheNames) {
      await caches.delete(cacheName);
    }
    return true;
  } catch (error) {
    console.error('清除所有缓存失败:', error);
    return false;
  }
};

/**
 * 将缓存状态输出到控制台
 */
export const logCacheStatus = async () => {
  console.group('Service Worker 缓存状态');
  
  const cacheNames = await getCacheNames();
  console.log('已发现的缓存:', cacheNames);
  
  for (const cacheName of cacheNames) {
    const urls = await getCacheUrls(cacheName);
    console.group(`缓存: ${cacheName} (${urls.length} 项)`);
    urls.forEach(url => console.log(url));
    console.groupEnd();
  }
  
  console.groupEnd();
  return cacheNames.length > 0;
}; 