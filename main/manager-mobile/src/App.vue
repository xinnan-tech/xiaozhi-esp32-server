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
  // Get public config
  configStore.fetchPublicConfig().catch((error) => {
    console.error('Failed to get public config:', error)
  })
})
onShow(() => {
  console.log('App Show')
  // Use setTimeout to delay execution, ensure tabBar initialized
  setTimeout(() => {
    updateTabBarText()
  }, 100)
})

// Dynamically update tabBar text
function updateTabBarText() {
  try {
    // Set home tabBar text
    uni.setTabBarItem({
      index: 0,
      text: t('tabBar.home'),
      success: () => {},
      fail: (err) => {
        console.log('Failed to set home tabBar text:', err)
      }
    })
    
    // Set config network tabBar text
    uni.setTabBarItem({
      index: 1,
      text: t('tabBar.deviceConfig'),
      success: () => {},
      fail: (err) => {
        console.log('Failed to set config network tabBar text:', err)
      }
    })
    
    // Set system tabBar text
    uni.setTabBarItem({
      index: 2,
      text: t('tabBar.settings'),
      success: () => {},
      fail: (err) => {
        console.log('Failed to set system tabBar text:', err)
      }
    })
  } catch (error) {
    console.log('Error updating tabBar text:', error)
  }
}
// Listen for language switch event
onMounted(() => {
  // Listen for language change, automatically update tabBar text
  watch(() => langStore.currentLang, () => {
    console.log('Language switched, updating tabBar text')
    // Update tabBar text immediately after language switch
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
