<template>
  <div id="app">
    <router-view />
    <cache-viewer v-if="isCDNEnabled" :visible.sync="showCacheViewer" />
  </div>
</template>

<style lang="scss">
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}

nav {
  padding: 30px;

  a {
    font-weight: bold;
    color: #2c3e50;

    &.router-link-exact-active {
      color: #42b983;
    }
  }
}

.copyright {
  text-align: center;
  color: rgb(0, 0, 0);
  font-size: 12px;
  font-weight: 400;
  margin-top: auto;
  padding: 30px 0 20px;
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
}

.el-message {
  top: 45px !important;
}
</style>
<script>
import CacheViewer from '@/components/CacheViewer.vue';
import { logCacheStatus } from '@/utils/cacheViewer';

export default {
  components: {
    CacheViewer
  },
  data() {
    return {
      showCacheViewer: false,
      isCDNEnabled: process.env.VUE_APP_USE_CDN === 'true'
    };
  },
  mounted() {
    // 只有在启用CDN时才添加相关事件和功能
    if (this.isCDNEnabled) {
      // 添加全局快捷键Alt+C用于显示缓存查看器
      document.addEventListener('keydown', this.handleKeyDown);
      
      // 在全局对象上添加缓存检查方法，便于调试
      window.checkCDNCacheStatus = () => {
        this.showCacheViewer = true;
      };
      
      // 在控制台输出提示信息
      console.info(
        '%c[小智服务] CDN缓存检查工具已加载', 
        'color: #409EFF; font-weight: bold;'
      );
      console.info(
        '按下 Alt+C 组合键或在控制台运行 checkCDNCacheStatus() 可以查看CDN缓存状态'
      );
      
      // 检查Service Worker状态
      this.checkServiceWorkerStatus();
    } else {
      console.info(
        '%c[小智服务] CDN模式已禁用，使用本地打包资源', 
        'color: #67C23A; font-weight: bold;'
      );
    }
  },
  beforeDestroy() {
    // 只有在启用CDN时才需要移除事件监听
    if (this.isCDNEnabled) {
      document.removeEventListener('keydown', this.handleKeyDown);
    }
  },
  methods: {
    handleKeyDown(e) {
      // Alt+C 快捷键
      if (e.altKey && e.key === 'c') {
        this.showCacheViewer = true;
      }
    },
    async checkServiceWorkerStatus() {
      // 检查Service Worker是否已注册
      if ('serviceWorker' in navigator) {
        try {
          const registrations = await navigator.serviceWorker.getRegistrations();
          if (registrations.length > 0) {
            console.info(
              '%c[小智服务] Service Worker已注册', 
              'color: #67C23A; font-weight: bold;'
            );
            
            // 输出缓存状态到控制台
            setTimeout(async () => {
              const hasCaches = await logCacheStatus();
              if (!hasCaches) {
                console.info(
                  '%c[小智服务] 还未检测到缓存，请刷新页面或等待缓存建立', 
                  'color: #E6A23C; font-weight: bold;'
                );
                
                // 开发环境下提供额外提示
                if (process.env.NODE_ENV === 'development') {
                  console.info(
                    '%c[小智服务] 在开发环境中，Service Worker可能无法正常初始化缓存',
                    'color: #E6A23C; font-weight: bold;'
                  );
                  console.info('请尝试以下方法检查Service Worker是否生效:');
                  console.info('1. 在开发者工具的Application/Application标签页中查看Service Worker状态');
                  console.info('2. 在开发者工具的Application/Cache/Cache Storage中查看缓存内容');
                  console.info('3. 使用生产构建(npm run build)并通过HTTP服务器访问以测试完整功能');
                }
              }
            }, 2000);
          } else {
            console.info(
              '%c[小智服务] Service Worker未注册，CDN资源可能无法缓存', 
              'color: #F56C6C; font-weight: bold;'
            );
            
            if (process.env.NODE_ENV === 'development') {
              console.info(
                '%c[小智服务] 在开发环境中，这是正常现象',
                'color: #E6A23C; font-weight: bold;'
              );
              console.info('Service Worker通常只在生产环境中生效');
              console.info('要测试Service Worker功能:');
              console.info('1. 运行npm run build构建生产版本');
              console.info('2. 通过HTTP服务器访问构建后的页面');
            }
          }
        } catch (error) {
          console.error('检查Service Worker状态失败:', error);
        }
      } else {
        console.warn('当前浏览器不支持Service Worker，CDN资源缓存功能不可用');
      }
    }
  }
};
</script>