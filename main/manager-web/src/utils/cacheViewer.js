/**
 * Cache viewing tool - used to check if CDN resources have been cached by Service Worker
 */

/**
 * Get all Service Worker cache names
 * @returns {Promise<string[]>} Cache name list
 */
export const getCacheNames = async () => {
  if (!('caches' in window)) {
    return [];
  }
  
  try {
    return await caches.keys();
  } catch (error) {
    console.error('Get cache names failed:', error);
    return [];
  }
};

/**
 * Get all URLs in specified cache
 * @param {string} cacheName Cache name
 * @returns {Promise<string[]>} Cached URL list
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
    console.error(`Get cache ${cacheName} URLs failed:`, error);
    return [];
  }
};

/**
 * Check if specific URL has been cached
 * @param {string} url URL to check
 * @returns {Promise<boolean>} Whether cached
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
    console.error(`Check URL ${url} cache status failed:`, error);
    return false;
  }
};

/**
 * Get cache status of all CDN resources on current page
 * @returns {Promise<Object>} Cache status object
 */
export const checkCdnCacheStatus = async () => {
  // Find resources from CDN cache
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
      
      // Distinguish CSS and JS resources
      for (const url of urls) {
        if (url.endsWith('.css')) {
          results.css.push({ url, cached: true });
        } else if (url.endsWith('.js')) {
          results.js.push({ url, cached: true });
        }
        results.totalCached++;
      }
    } catch (error) {
      console.error(`Get ${cacheName} cache information failed:`, error);
    }
  }
  
  return results;
};

/**
 * Clear all Service Worker caches
 * @returns {Promise<boolean>} Whether successfully cleared
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
    console.error('Clear all caches failed:', error);
    return false;
  }
};

/**
 * Output cache status to console
 */
export const logCacheStatus = async () => {
  console.group('Service Worker cache status');
  
  const cacheNames = await getCacheNames();
  console.log('Discovered caches:', cacheNames);
  
  for (const cacheName of cacheNames) {
    const urls = await getCacheUrls(cacheName);
    console.group(`Cache: ${cacheName} (${urls.length} items)`);
    urls.forEach(url => console.log(url));
    console.groupEnd();
  }
  
  console.groupEnd();
  return cacheNames.length > 0;
}; 