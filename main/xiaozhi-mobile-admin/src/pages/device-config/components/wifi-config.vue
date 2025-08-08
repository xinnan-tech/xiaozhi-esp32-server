<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToast } from 'wot-design-uni'

// 类型定义
interface WiFiNetwork {
  ssid: string
  rssi: number
  authmode: number
  channel: number
}

// Props
interface Props {
  selectedNetwork: WiFiNetwork | null
  password: string
}

const props = defineProps<Props>()

// Toast 实例
const toast = useToast()

// 响应式数据
const configuring = ref(false)

// 计算属性
const canSubmit = computed(() => {
  if (!props.selectedNetwork)
    return false
  if (props.selectedNetwork.authmode > 0 && !props.password)
    return false
  return true
})

// ESP32连接检查
async function checkESP32Connection() {
  try {
    const response = await uni.request({
      url: 'http://192.168.4.1/scan',
      method: 'GET',
      timeout: 3000,
    })
    return response.statusCode === 200
  }
  catch (error) {
    console.log('ESP32连接检查失败:', error)
    return false
  }
}

// 提交配网
async function submitConfig() {
  if (!props.selectedNetwork)
    return

  // 检查ESP32连接
  const connected = await checkESP32Connection()
  if (!connected) {
    toast.error('请先连接xiaozhi热点')
    return
  }

  configuring.value = true
  console.log('开始WiFi配网:', props.selectedNetwork.ssid)

  try {
    const response = await uni.request({
      url: 'http://192.168.4.1/submit',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
      },
      data: {
        ssid: props.selectedNetwork.ssid,
        password: props.selectedNetwork.authmode > 0 ? props.password : '',
      },
      timeout: 15000,
    })

    console.log('WiFi配网响应:', response)

    if (response.statusCode === 200 && (response.data as any)?.success) {
      toast.success(`配网成功！设备将连接到 ${props.selectedNetwork.ssid}，设备会自动重启。请断开xiaozhi热点连接。`)
    }
    else {
      const errorMsg = (response.data as any)?.error || '配网失败'
      toast.error(errorMsg)
    }
  }
  catch (error) {
    console.error('WiFi配网失败:', error)
    toast.error('配网失败，请检查网络连接')
  }
  finally {
    configuring.value = false
  }
}
</script>

<template>
  <view class="wifi-config">
    <!-- 选中的网络信息 -->
    <view v-if="props.selectedNetwork" class="selected-network">
      <view class="network-info">
        <view class="network-name">
          选中网络: {{ props.selectedNetwork.ssid }}
        </view>
        <view class="network-details">
          <text class="network-signal">
            信号: {{ props.selectedNetwork.rssi }}dBm
          </text>
          <text class="network-security">
            {{ props.selectedNetwork.authmode === 0 ? '开放网络' : '加密网络' }}
          </text>
        </view>
      </view>
    </view>

    <!-- 配网按钮 -->
    <view class="submit-section">
      <wd-button
        type="primary"
        size="large"
        block
        :loading="configuring"
        :disabled="!canSubmit"
        @click="submitConfig"
      >
        {{ configuring ? '配网中...' : '开始WiFi配网' }}
      </wd-button>
    </view>

    <!-- 使用说明 -->
    <view class="help-section">
      <view class="help-title">
        WiFi配网说明
      </view>
      <view class="help-content">
        <text class="help-item">
          1. 手机连接xiaozhi热点 (xiaozhi-XXXXXX)
        </text>
        <text class="help-item">
          2. 选择要配网的目标WiFi网络
        </text>
        <text class="help-item">
          3. 输入WiFi密码（如果需要）
        </text>
        <text class="help-item">
          4. 点击开始配网，等待设备连接
        </text>
        <text class="help-tip">
          配网成功后设备会自动重启并连接目标WiFi
        </text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.wifi-config {
  padding: 20rpx 0;
}

.selected-network {
  margin-bottom: 32rpx;
}

.network-info {
  padding: 24rpx;
  background-color: #f0f6ff;
  border: 1rpx solid #336cff;
  border-radius: 16rpx;
}

.network-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #232338;
  margin-bottom: 8rpx;
}

.network-details {
  display: flex;
  gap: 24rpx;
}

.network-signal,
.network-security {
  font-size: 24rpx;
  color: #65686f;
}

.submit-section {
  margin-bottom: 32rpx;
}

.help-section {
  padding: 32rpx 24rpx;
  background-color: #fbfbfb;
  border-radius: 16rpx;
  border: 1rpx solid #eeeeee;
}

.help-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #232338;
  margin-bottom: 20rpx;
}

.help-content {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.help-item {
  font-size: 24rpx;
  color: #65686f;
  line-height: 1.5;
}

.help-tip {
  font-size: 24rpx;
  color: #336cff;
  font-weight: 500;
  margin-top: 8rpx;
}
</style>
