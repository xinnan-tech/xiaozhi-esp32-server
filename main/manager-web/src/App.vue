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
  top: 70px !important;
}
</style>
<script>
import CacheViewer from '@/components/CacheViewer.vue';
import { logCacheStatus } from '@/utils/cacheViewer';

export default {
  name: 'App',
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
    // 检测是否为移动设备且VUE_APP_H5_URL不为空，如果两个条件都满足则跳转到H5页面
    if (this.isMobileDevice() && process.env.VUE_APP_H5_URL) {
      window.location.href = process.env.VUE_APP_H5_URL;
      return;
    }
    
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
        '%c[' + this.$t('system.name') + '] ' + this.$t('cache.cdnEnabled'),
        'color: #409EFF; font-weight: bold;'
      );
      console.info(
        '按下 Alt+C 组合键或在控制台运行 checkCDNCacheStatus() 可以查看CDN缓存状态'
      );

      // 检查Service Worker状态
      this.checkServiceWorkerStatus();
    } else {
      console.info(
        '%c[' + this.$t('system.name') + '] ' + this.$t('cache.cdnDisabled'),
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
    isMobileDevice() {
      // 检测是否为移动设备的函数
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },
    
    async checkServiceWorkerStatus() {
      // 检查Service Worker是否已注册
      if ('serviceWorker' in navigator) {
        try {
          const registrations = await navigator.serviceWorker.getRegistrations();
          if (registrations.length > 0) {
            console.info(
              '%c[' + this.$t('system.name') + '] ' + this.$t('cache.serviceWorkerRegistered'),
              'color: #67C23A; font-weight: bold;'
            );

            // 输出缓存状态到控制台
            setTimeout(async () => {
              const hasCaches = await logCacheStatus();
              if (!hasCaches) {
                console.info(
                '%c[' + this.$t('system.name') + '] ' + this.$t('cache.noCacheDetected'),
                'color: #E6A23C; font-weight: bold;'
              );

              // 开发环境下提供额外提示
              if (process.env.NODE_ENV === 'development') {
                console.info(
                  '%c[' + this.$t('system.name') + '] ' + this.$t('cache.swDevEnvWarning'),
                  'color: #E6A23C; font-weight: bold;'
                );
                console.info(this.$t('cache.swCheckMethods'));
                console.info('1. ' + this.$t('cache.swCheckMethod1'));
                console.info('2. ' + this.$t('cache.swCheckMethod2'));
                console.info('3. ' + this.$t('cache.swCheckMethod3'));
              }
              }
            }, 2000);
          } else {
            console.info(
                  '%c[' + this.$t('system.name') + '] ' + this.$t('cache.serviceWorkerNotRegistered'),
                  'color: #F56C6C; font-weight: bold;'
                );

                if (process.env.NODE_ENV === 'development') {
                  console.info(
                    '%c[' + this.$t('system.name') + '] ' + this.$t('cache.swDevEnvNormal'),
                    'color: #E6A23C; font-weight: bold;'
                  );
                  console.info(this.$t('cache.swProdOnly'));
                  console.info(this.$t('cache.swTestingTitle'));
                  console.info('1. ' + this.$t('cache.swTestingStep1'));
                  console.info('2. ' + this.$t('cache.swTestingStep2'));
                }
          }
        } catch (error) {
          console.error('检查Service Worker状态失败:', error);
        }
      } else {
          console.warn(this.$t('cache.swNotSupported'));
        }
    }
  }
};
</script>