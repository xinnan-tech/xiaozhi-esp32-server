<route lang="jsonc" type="page">{
  "layout": "default",
  "style": {
    "navigationBarTitleText": "设置",
    "navigationStyle": "custom"
  }
}</route>

<script lang="ts" setup>
import { clearServerBaseUrlOverride, getEnvBaseUrl, getServerBaseUrlOverride, setServerBaseUrlOverride } from '@/utils'
import { isMp } from '@/utils/platform'
import { computed, onMounted, reactive, ref } from 'vue'
import { useToast } from 'wot-design-uni'

defineOptions({
  name: 'SettingsPage',
})

const toast = useToast()

// 缓存信息
const cacheInfo = reactive({
  storageSize: '0MB',
  imageCache: '0MB',
  dataCache: '0MB',
})

// 服务端地址设置
const baseUrlInput = ref('')
const urlError = ref('')

// 系统信息（保留）
const systemInfo = computed(() => {
  const info = uni.getSystemInfoSync()
  return `${info.platform} ${info.system}`
})

// 读取本地覆盖地址
function loadServerBaseUrl() {
  const override = getServerBaseUrlOverride()
  baseUrlInput.value = override || getEnvBaseUrl()
}

// 获取缓存信息
function getCacheInfo() {
  try {
    const info = uni.getStorageInfoSync()
    const totalSize = (info.currentSize || 0) / 1024 // KB to MB
    cacheInfo.storageSize = `${totalSize.toFixed(2)}MB`
  }
  catch (error) {
    console.error('获取缓存信息失败:', error)
  }
}

// 验证URL格式
function validateUrl() {
  urlError.value = ''
  
  if (!baseUrlInput.value) {
    return
  }
  
  if (!/^https?:\/\/.+\/xiaozhi$/.test(baseUrlInput.value)) {
    urlError.value = '请输入有效的服务端地址（以 http 或 https 开头，并以 /xiaozhi 结尾）'
  }
}

// 测试服务端地址
async function testServerBaseUrl() {
  // 先清除错误信息
  urlError.value = ''
  
  if (!baseUrlInput.value || !/^https?:\/\/.+\/xiaozhi$/.test(baseUrlInput.value)) {
    return false
  }

  try {
    const response = await uni.request({
      url: `${baseUrlInput.value}/api/ping`,
      method: 'GET',
      timeout: 3000
    })

    if (response.statusCode === 200) {
      return true
    } else {
      toast.error('无效地址，请检查服务端是否启动或网络连接是否正常')
      return false
    }
  } catch (error) {
    console.error('测试服务端地址失败:', error)
    toast.error('无效地址，请检查服务端是否启动或网络连接是否正常')
    return false
  }
}

// 保存服务端地址
async function saveServerBaseUrl() {
  if (!baseUrlInput.value || !/^https?:\/\/.+\/xiaozhi$/.test(baseUrlInput.value)) {
    toast.warning('请输入有效的服务端地址（以 http 或 https 开头，并以 /xiaozhi 结尾）')
    return
  }

  // 测试地址有效性
  const isServerValid = await testServerBaseUrl()
  if (!isServerValid) {
    return
  }
  setServerBaseUrlOverride(baseUrlInput.value)

  // 切换请求地址后清空所有缓存
  clearAllCacheAfterUrlChange()

  uni.showModal({
      title: '重启应用',
      content: '服务端地址已保存并清空缓存，是否立即重启生效？',
      confirmText: '立即重启',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          restartApp()
        }
        else {
          toast.success('已保存，可稍后手动重启应用')
        }
      },
    })
  }

// 重置为 env 默认
function resetServerBaseUrl() {
  clearServerBaseUrlOverride()
  baseUrlInput.value = getEnvBaseUrl()

  // 切换请求地址后清空所有缓存
  clearAllCacheAfterUrlChange()

  uni.showModal({
    title: '重启应用',
    content: '已重置为默认地址并清空缓存，是否立即重启生效？',
    confirmText: '立即重启',
    cancelText: '稍后',
    success: (res) => {
      if (res.confirm) {
        restartApp()
      }
      else {
        toast.success('已重置，可稍后手动重启应用')
      }
    },
  })
}

// 重启应用（App 原生重启；其他端回到首页）
function restartApp() {
  // #ifdef APP-PLUS
  plus.runtime.restart()
  // #endif
  // #ifndef APP-PLUS
  uni.reLaunch({ url: '/pages/index/index' })
  // #endif
}

// 切换地址后自动清空所有缓存
function clearAllCacheAfterUrlChange() {
  try {
    // 备份运行时覆盖地址，确保清理后恢复
    const preservedOverride = getServerBaseUrlOverride()

    // 完全清空所有缓存，包括token
    uni.clearStorageSync()

    // 清空localStorage（H5环境）
    // #ifdef H5
    if (typeof localStorage !== 'undefined') {
      localStorage.clear()
    }
    // #endif

    // 恢复运行时覆盖地址（如有），需要在清理完成后再写入
    if (preservedOverride) {
      setServerBaseUrlOverride(preservedOverride)
    }

    // 重新获取缓存信息
    getCacheInfo()
  }
  catch (error) {
    console.error('清除缓存失败:', error)
  }
}

// 清除缓存
async function clearCache() {
  try {
    uni.showModal({
      title: '确认清除',
      content: '确定要清除所有缓存吗？这将删除所有数据包括登录状态，需要重新登录。',
      success: (res) => {
        if (res.confirm) {
          clearAllCacheAfterUrlChange()
          toast.success('缓存清除成功，即将跳转到登录页')

          // 延迟跳转到登录页
          setTimeout(() => {
            uni.reLaunch({ url: '/pages/login/index' })
          }, 1500)
        }
      },
    })
  }
  catch (error) {
    console.error('清除缓存失败:', error)
    toast.error('清除缓存失败')
  }
}

// 关于我们
function showAbout() {
  uni.showModal({
    title: `关于${import.meta.env.VITE_APP_TITLE}`,
    content: `${import.meta.env.VITE_APP_TITLE}\n\n基于 Vue.js 3 + uni-app 构建的跨平台移动端管理应用，为小智ESP32智能硬件提供Device Management、智能体配置等功能。\n\n© 2025 xiaozhi-esp32-server`,
    title: `关于小智智控台`,
    content: `小智智控台\n\n基于 Vue.js 3 + uni-app 构建的跨平台移动端管理应用，为小智ESP32智能硬件提供Device Management、智能体配置等功能。\n\n© 2025 xiaozhi-esp32-server 0.7.5`,
    showCancel: false,
    confirmText: '确定',
  })
}

onMounted(async () => {
  // 仅在非小程序环境加载服务端地址设置
  if (!isMp) {
    loadServerBaseUrl()
  }
  getCacheInfo()
})
</script>

<template>
  <view class="min-h-screen bg-[#f5f7fb]">
    <wd-navbar title="设置" placeholder safe-area-inset-top fixed />

    <view class="p-[24rpx]">
      <!-- 网络设置 - 仅在非小程序环境显示 -->
      <view v-if="!isMp" class="mb-[32rpx]">
        <view class="mb-[24rpx] flex items-center">
          <text class="text-[32rpx] text-[#232338] font-bold">
            网络设置
          </text>
        </view>

        <view class="border border-[#eeeeee] rounded-[24rpx] bg-[#fbfbfb] p-[32rpx] overflow-hidden"
          style="box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);">
          <view class="mb-[24rpx]">
            <text class="text-[28rpx] text-[#232338] font-semibold">
              服务端接口地址
            </text>
            <text class="mt-[8rpx] block text-[24rpx] text-[#9d9ea3]">
              修改后将自动清空缓存并重启应用
            </text>
          </view>

          <view class="mb-[24rpx]">
            <view class="w-full rounded-[16rpx] border border-[#eeeeee] bg-[#f5f7fb] overflow-hidden">
              <wd-input
                v-model="baseUrlInput"
                type="text"
                clearable
                :maxlength="200"
                placeholder="输入服务端地址，如 https://example.com/xiaozhi"
                custom-class="!border-none !bg-transparent h-[88rpx] px-[24rpx] items-center"
                input-class="text-[28rpx] text-[#232338]"
                @input="validateUrl"
                @blur="validateUrl"
              />
            </view>
            <text v-if="urlError" class="mt-[8rpx] block text-[24rpx] text-[#ff4d4f]">
              {{ urlError }}
            </text>
          </view>

          <view class="flex gap-[16rpx]">
            <wd-button type="primary"
              custom-class="flex-1 h-[88rpx] rounded-[20rpx] text-[28rpx] font-semibold bg-[#336cff] border-none shadow-[0_4rpx_16rpx_rgba(51,108,255,0.3)] active:shadow-[0_2rpx_8rpx_rgba(51,108,255,0.4)] active:scale-98"
              @click="saveServerBaseUrl">
              保存设置
            </wd-button>
            <wd-button type="default"
              custom-class="flex-1 h-[88rpx] rounded-[20rpx] text-[28rpx] font-semibold bg-white border-[#eeeeee] text-[#65686f] active:bg-[#f5f7fb]"
              @click="resetServerBaseUrl">
              恢复默认
            </wd-button>
          </view>
        </view>
      </view>

      <!-- 缓存管理 -->
      <view class="mb-[32rpx]">
        <view class="mb-[24rpx] flex items-center">
          <text class="text-[32rpx] text-[#232338] font-bold">
            缓存管理
          </text>
        </view>

        <view class="border border-[#eeeeee] rounded-[24rpx] bg-[#fbfbfb] p-[32rpx]"
          style="box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);">
          <view class="space-y-[16rpx]">
            <!-- 缓存信息展示，参考插件样式 -->
            <view
              class="flex items-center justify-between border border-[#eeeeee] rounded-[16rpx] bg-[#f5f7fb] p-[24rpx] transition-all active:bg-[#eef3ff]">
              <view>
                <text class="text-[28rpx] text-[#232338] font-medium">
                  总缓存大小
                </text>
                <text class="mt-[4rpx] block text-[24rpx] text-[#9d9ea3]">
                  应用数据总大小
                </text>
              </view>
              <text class="text-[28rpx] text-[#65686f] font-semibold">
                {{ cacheInfo.storageSize }}
              </text>
            </view>

            <!-- 清除缓存按钮，参考插件编辑按钮样式 -->
            <view
              class="flex items-center justify-between border border-[#eeeeee] rounded-[16rpx] bg-[#f5f7fb] p-[24rpx]">
              <view>
                <text class="text-[28rpx] text-[#232338] font-medium">
                  缓存清理
                </text>
                <text class="mt-[4rpx] block text-[24rpx] text-[#9d9ea3]">
                  清空所有缓存数据
                </text>
              </view>
              <view
                class="cursor-pointer rounded-[24rpx] bg-[rgba(255,107,107,0.1)] px-[28rpx] py-[16rpx] text-[24rpx] text-[#ff6b6b] font-semibold transition-all duration-300 active:scale-95 active:bg-[#ff6b6b] active:text-white"
                @click="clearCache">
                清除缓存
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- 应用信息 -->
      <view class="mb-[32rpx]">
        <view class="mb-[24rpx] flex items-center">
          <text class="text-[32rpx] text-[#232338] font-bold">
            应用信息
          </text>
        </view>

        <view class="border border-[#eeeeee] rounded-[24rpx] bg-[#fbfbfb] p-[32rpx]"
          style="box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);">
          <view
            class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[16rpx] bg-[#f5f7fb] p-[24rpx] transition-all active:bg-[#eef3ff]"
            @click="showAbout">
            <view>
              <text class="text-[28rpx] text-[#232338] font-medium">
                关于我们
              </text>
              <text class="mt-[4rpx] block text-[24rpx] text-[#9d9ea3]">
                应用版本与团队信息
              </text>
            </view>
            <wd-icon name="arrow-right" custom-class="text-[32rpx] text-[#9d9ea3]" />
          </view>
        </view>
      </view>

      <!-- 底部安全距离 -->
      <!-- 底部安全距离 -->
    <view style="height: env(safe-area-inset-bottom);" />
    </view>
  </view>
</template>

<style lang="scss" scoped>
// 保持与 edit.vue 一致的风格，样式主要通过类名控制</style>
