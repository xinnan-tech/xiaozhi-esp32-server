<script setup lang="ts">
import { onHide, onLaunch, onShow } from '@dcloudio/uni-app'
import { watch, onMounted } from 'vue'
import { usePageAuth } from '@/hooks/usePageAuth'
import { useConfigStore } from '@/store'
import { t } from '@/i18n'
import { useLangStore } from '@/store/lang'
import 'abortcontroller-polyfill/dist/abortcontroller-polyfill-only'

usePageAuth()

const configStore = useConfigStore()
const langStore = useLangStore()

onLaunch(() => {
  console.log('App Launch')
  // 获取公共配置
  configStore.fetchPublicConfig().catch((error) => {
    console.error('获取公共配置失败:', error)
  })
})
onShow(() => {
  console.log('App Show')
  // 使用setTimeout延迟执行，确保tabBar已经初始化
  setTimeout(() => {
    updateTabBarText()
  }, 100)
})

// 动态更新tabBar文本
function updateTabBarText() {
  try {
    // 设置首页tabBar文本
    uni.setTabBarItem({
      index: 0,
      text: t('tabBar.home'),
      success: () => {},
      fail: (err) => {
        console.log('设置首页tabBar文本失败:', err)
      }
    })
    
    // 设置配网tabBar文本
    uni.setTabBarItem({
      index: 1,
      text: t('tabBar.deviceConfig'),
      success: () => {},
      fail: (err) => {
        console.log('设置配网tabBar文本失败:', err)
      }
    })
    
    // 设置系统tabBar文本
    uni.setTabBarItem({
      index: 2,
      text: t('tabBar.settings'),
      success: () => {},
      fail: (err) => {
        console.log('设置系统tabBar文本失败:', err)
      }
    })
  } catch (error) {
    console.log('更新tabBar文本时出错:', error)
  }
}
// 监听语言切换事件
onMounted(() => {
  // 监听语言变化，当语言改变时自动更新tabBar文本
  watch(() => langStore.currentLang, () => {
    console.log('语言已切换，更新tabBar文本')
    // 语言切换后立即更新tabBar文本
    updateTabBarText()
  })
})

onHide(() => {
  console.log('App Hide')
})
</script>

<style lang="scss">
swiper,
scroll-view {
  flex: 1;
  height: 100%;
  overflow: hidden;
}

image {
  width: 100%;
  height: 100%;
  vertical-align: middle;
}
</style>
