/* eslint-disable no-console */

export const register = () => {
  if (process.env.NODE_ENV === 'production' && 'serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      const swUrl = `${process.env.BASE_URL}service-worker.js`;
      
      console.info(`[小智服务] 正在尝试注册Service Worker，URL: ${swUrl}`);
      
      // 先检查Service Worker是否已注册
      navigator.serviceWorker.getRegistrations().then(registrations => {
        if (registrations.length > 0) {
          console.info('[小智服务] 发现已有Service Worker注册，正在检查更新');
        }
        
        // 继续注册Service Worker
        navigator.serviceWorker
          .register(swUrl)
          .then(registration => {
            console.info('[小智服务] Service Worker注册成功');
            
            // 更新处理
            registration.onupdatefound = () => {
              const installingWorker = registration.installing;
              if (installingWorker == null) {
                return;
              }
              installingWorker.onstatechange = () => {
                if (installingWorker.state === 'installed') {
                  if (navigator.serviceWorker.controller) {
                    // 内容已缓存更新，通知用户刷新
                    console.log('[小智服务] 新内容可用，请刷新页面');
                    // 可以在这里展示更新提示
                    const updateNotification = document.createElement('div');
                    updateNotification.style.cssText = `
                      position: fixed;
                      bottom: 20px;
                      right: 20px;
                      background: #409EFF;
                      color: white;
                      padding: 12px 20px;
                      border-radius: 4px;
                      box-shadow: 0 2px 12px 0 rgba(0,0,0,.1);
                      z-index: 9999;
                    `;
                    updateNotification.innerHTML = `
                      <div style="display: flex; align-items: center;">
                        <span style="margin-right: 10px;">发现新版本，点击刷新应用</span>
                        <button style="background: white; color: #409EFF; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">刷新</button>
                      </div>
                    `;
                    document.body.appendChild(updateNotification);
                    updateNotification.querySelector('button').addEventListener('click', () => {
                      window.location.reload();
                    });
                  } else {
                    // 一切正常，Service Worker已成功安装
                    console.log('[小智服务] 内容已缓存供离线使用');
                    
                    // 可以在这里初始化缓存
                    setTimeout(() => {
                      // 预热CDN缓存
                      const cdnUrls = [
                        'https://unpkg.com/element-ui@2.15.14/lib/theme-chalk/index.css',
                        'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css',
                        'https://unpkg.com/vue@2.6.14/dist/vue.min.js',
                        'https://unpkg.com/vue-router@3.6.5/dist/vue-router.min.js',
                        'https://unpkg.com/vuex@3.6.2/dist/vuex.min.js',
                        'https://unpkg.com/element-ui@2.15.14/lib/index.js',
                        'https://unpkg.com/axios@0.27.2/dist/axios.min.js',
                        'https://unpkg.com/opus-decoder@0.7.7/dist/opus-decoder.min.js'
                      ];
                      
                      // 预热缓存
                      cdnUrls.forEach(url => {
                        fetch(url, { mode: 'no-cors' }).catch(err => {
                          console.log(`预热缓存 ${url} 失败`, err);
                        });
                      });
                    }, 2000);
                  }
                }
              };
            };
          })
          .catch(error => {
            console.error('Service Worker 注册失败:', error);
            
            if (error.name === 'TypeError' && error.message.includes('Failed to register a ServiceWorker')) {
              console.warn('[小智服务] 注册Service Worker时出现网络错误，CDN资源可能无法缓存');
              if (process.env.NODE_ENV === 'production') {
                console.info(
                  '可能原因：1. 服务器未配置正确的MIME类型 2. 服务器SSL证书问题 3. 服务器未返回service-worker.js文件'
                );
              }
            }
          });
      });
    });
  }
};

export const unregister = () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then(registration => {
        registration.unregister();
      })
      .catch(error => {
        console.error(error.message);
      });
  }
}; 