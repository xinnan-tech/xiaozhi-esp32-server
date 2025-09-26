<script setup lang="ts">
import { ref } from 'vue'
import { t } from '@/i18n'
import UltrasonicConfig from './components/ultrasonic-config.vue'
import WifiConfig from './components/wifi-config.vue'
import WifiSelector from './components/wifi-selector.vue'

// 类型定义
interface WiFiNetwork {
  ssid: string
  rssi: number
  authmode: number
  channel: number
}

// 配网类型
const configType = ref<'wifi' | 'ultrasonic'>('wifi')

// 配网模式选择器状态
const configTypeSelectorShow = ref(false)

// WiFi选择器引用
const wifiSelectorRef = ref<InstanceType<typeof WifiSelector>>()

// 选择的WiFi网络信息
const selectedWifiInfo = ref<{
  network: WiFiNetwork | null
  password: string
}>({
  network: null,
  password: '',
})

// 配网模式选项
const configTypeOptions = [
  {
    name: t('deviceConfig.wifiConfig'),
    value: 'wifi' as const,
  },
  // {
  //   name: t('deviceConfig.ultrasonicConfig'),
  //   value: 'ultrasonic' as const,
  // },
]

// 显示配网模式选择器
function showConfigTypeSelector() {
  configTypeSelectorShow.value = true
}

// 配网模式选择器确认
function onConfigTypeConfirm(item: { name: string, value: 'wifi' | 'ultrasonic' }) {
  configType.value = item.value
  configTypeSelectorShow.value = false
}

// 配网模式选择器取消
function onConfigTypeCancel() {
  configTypeSelectorShow.value = false
}

// WiFi网络选择事件
function onNetworkSelected(network: WiFiNetwork | null, password: string) {
  selectedWifiInfo.value = { network, password }
}

// ESP32连接状态变化事件
function onConnectionStatusChange(connected: boolean) {
  console.log('ESP32连接状态:', connected)
}

// 在组件挂载后设置导航栏标题
import { onMounted } from 'vue'
onMounted(() => {
  uni.setNavigationBarTitle({
    title: t('deviceConfig.pageTitle')
  })
})
</script>

<template>
  <view class="min-h-screen bg-[#f5f7fb]">
    <wd-navbar :title="t('deviceConfig.pageTitle')" safe-area-inset-top />

    <view class="box-border px-[20rpx]">
      <!-- 配网方式选择 -->
      <view class="pb-[20rpx] first:pt-[20rpx]">
        <text class="text-[32rpx] text-[#232338] font-bold">
            {{ t('deviceConfig.configMethod') }}
          </text>
      </view>

      <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:border-[#336cff] active:bg-[#eef3ff]" @click="showConfigTypeSelector">
          <text class="text-[28rpx] text-[#232338] font-medium">
              {{ t('deviceConfig.configMethod') }}
            </text>
            <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
              {{ configType === 'wifi' ? t('deviceConfig.wifiConfig') : t('deviceConfig.ultrasonicConfig') }}
            </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>
      </view>

      <!-- WiFi网络选择 -->
      <view class="pb-[20rpx]">
        <text class="text-[32rpx] text-[#232338] font-bold">
            {{ t('deviceConfig.networkConfig') }}
          </text>
      </view>

      <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <wifi-selector
          ref="wifiSelectorRef"
          @network-selected="onNetworkSelected"
          @connection-status="onConnectionStatusChange"
        />
      </view>

      <!-- 配网操作 -->
      <view v-if="selectedWifiInfo.network" class="flex-1">
        <!-- WiFi配网组件 -->
        <wifi-config
          v-if="configType === 'wifi'"
          :selected-network="selectedWifiInfo.network"
          :password="selectedWifiInfo.password"
        />

        <!-- 超声波配网组件 -->
        <ultrasonic-config
          v-else-if="configType === 'ultrasonic'"
          :selected-network="selectedWifiInfo.network"
          :password="selectedWifiInfo.password"
        />
      </view>
    </view>

    <!-- 配网模式选择器 -->
    <wd-action-sheet
      v-model="configTypeSelectorShow"
      :actions="configTypeOptions.map(item => ({ name: item.name, value: item.value }))"
      @close="onConfigTypeCancel"
      @select="({ item }) => onConfigTypeConfirm(item)"
    />
  </view>
</template>

<route lang="jsonc" type="page">
{
  "style": {
    "navigationBarTitleText": "设备配置",
    "navigationStyle": "custom"
  }
}
</route>
