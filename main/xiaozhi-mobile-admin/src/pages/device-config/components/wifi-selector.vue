<script setup lang="ts">
import { computed, defineEmits, defineExpose, onMounted, ref } from 'vue'
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
  autoConnect?: boolean // 是否自动检测ESP32连接
}

const props = withDefaults(defineProps<Props>(), {
  autoConnect: true,
})

// Emits
const emit = defineEmits<{
  'network-selected': [network: WiFiNetwork | null, password: string]
  'connection-status': [connected: boolean]
}>()

// Toast 实例
const toast = useToast()

// 响应式数据
const isConnectedToESP32 = ref(false)
const checkingConnection = ref(false)
const scanning = ref(false)
const wifiNetworks = ref<WiFiNetwork[]>([])
const selectedNetwork = ref<WiFiNetwork | null>(null)
const password = ref('')
const selectorExpanded = ref(false)

// 计算属性
const networkDisplayText = computed(() => {
  if (!selectedNetwork.value)
    return '请选择WiFi网络'
  return selectedNetwork.value.ssid
})

// 检查xiaozhi连接状态
async function checkESP32Connection() {
  checkingConnection.value = true
  try {
    const response = await uni.request({
      url: 'http://192.168.4.1/scan',
      method: 'GET',
      timeout: 3000,
    })
    isConnectedToESP32.value = response.statusCode === 200
    emit('connection-status', isConnectedToESP32.value)
    console.log('xiaozhi连接状态:', isConnectedToESP32.value)
  }
  catch (error) {
    isConnectedToESP32.value = false
    emit('connection-status', false)
    console.log('xiaozhi连接检查失败:', error)
  }
  finally {
    checkingConnection.value = false
  }
}

// 扫描WiFi网络
async function scanWifi() {
  if (!isConnectedToESP32.value) {
    toast.error('请先连接xiaozhi热点')
    return
  }

  scanning.value = true
  console.log('开始扫描WiFi网络')

  try {
    const response = await uni.request({
      url: 'http://192.168.4.1/scan',
      method: 'GET',
      timeout: 10000,
    })

    console.log('WiFi扫描响应:', response)

    if (response.statusCode === 200 && response.data) {
      const data = response.data as any
      if (data.success && Array.isArray(data.networks)) {
        wifiNetworks.value = data.networks
        console.log(`扫描成功，发现 ${data.networks.length} 个网络`)
      }
      else if (Array.isArray(response.data)) {
        // 兼容旧格式
        wifiNetworks.value = response.data.map((item: any) => ({
          ssid: item.ssid,
          rssi: item.rssi,
          authmode: item.authmode,
          channel: item.channel || 0,
        }))
      }
      else {
        throw new TypeError('扫描接口返回格式异常')
      }
    }
    else {
      throw new Error(`HTTP ${response.statusCode}`)
    }
  }
  catch (error) {
    console.error('WiFi扫描失败:', error)
    toast.error('扫描失败，请检查xiaozhi连接')
  }
  finally {
    scanning.value = false
  }
}

// 显示网络选择器
async function showNetworkSelector() {
  // 实时检测xiaozhi连接状态
  await checkESP32Connection()

  if (!isConnectedToESP32.value) {
    toast.error('请先连接xiaozhi热点')
    return
  }

  selectorExpanded.value = true

  // 如果还没有网络列表，自动扫描
  if (wifiNetworks.value.length === 0) {
    scanWifi()
  }
}

// 选择网络
function selectNetwork(network: WiFiNetwork) {
  selectedNetwork.value = network
  password.value = ''
  selectorExpanded.value = false
  console.log('选择网络:', network.ssid)

  // 通知父组件
  emit('network-selected', network, '')
}

// 密码变化时通知父组件
function onPasswordChange() {
  emit('network-selected', selectedNetwork.value, password.value)
}

// 获取当前选择的网络和密码
function getSelectedNetworkInfo() {
  return {
    network: selectedNetwork.value,
    password: password.value,
  }
}

// 重置选择
function reset() {
  selectedNetwork.value = null
  password.value = ''
  wifiNetworks.value = []
  selectorExpanded.value = false
  emit('network-selected', null, '')
}

// 获取信号强度描述
function getSignalStrength(rssi: number): string {
  if (rssi >= -50)
    return '信号强'
  if (rssi >= -60)
    return '信号良好'
  if (rssi >= -70)
    return '信号一般'
  return '信号弱'
}

// 获取信号强度颜色
function getSignalColor(rssi: number): string {
  if (rssi >= -50)
    return '#52c41a'
  if (rssi >= -60)
    return '#73d13d'
  if (rssi >= -70)
    return '#faad14'
  return '#ff4d4f'
}

// 暴露方法给父组件
defineExpose({
  checkESP32Connection,
  scanWifi,
  getSelectedNetworkInfo,
  reset,
})

// 生命周期
onMounted(() => {
  if (props.autoConnect) {
    checkESP32Connection()
  }
})
</script>

<template>
  <view class="wifi-selector">
    <!-- Xiaozhi连接状态 -->
    <view v-if="props.autoConnect" class="connection-status">
      <view v-if="!isConnectedToESP32" class="status-warning">
        <view class="status-content">
          <text class="warning-text">
            请先连接xiaozhi热点 (xiaozhi-XXXXXX)
          </text>
          <wd-button
            size="small"
            type="primary"
            :loading="checkingConnection"
            @click="checkESP32Connection"
          >
            {{ checkingConnection ? '检测中...' : '重新检测' }}
          </wd-button>
        </view>
      </view>
      <view v-else class="status-success">
        <view class="status-content">
          <text class="success-text">
            已连接xiaozhi热点
          </text>
          <wd-button
            size="small"
            :loading="checkingConnection"
            @click="checkESP32Connection"
          >
            {{ checkingConnection ? '检测中...' : '刷新状态' }}
          </wd-button>
        </view>
      </view>
    </view>

    <!-- WiFi网络选择器 -->
    <view class="network-selector">
      <view class="selector-item" @click="showNetworkSelector">
        <text class="selector-label">
          WiFi网络
        </text>
        <text class="selector-value">
          {{ networkDisplayText }}
        </text>
        <wd-icon name="arrow-right" custom-class="arrow-icon" />
      </view>
    </view>

    <!-- 展开的网络列表 -->
    <view v-if="selectorExpanded" class="network-list-overlay">
      <view class="network-list-container">
        <view class="list-header">
          <text class="list-title">
            选择WiFi网络
          </text>
          <view class="list-actions">
            <wd-button
              type="primary"
              size="small"
              :loading="scanning"
              @click="scanWifi"
            >
              {{ scanning ? '扫描中...' : '刷新扫描' }}
            </wd-button>
            <wd-button
              size="small"
              @click="selectorExpanded = false"
            >
              取消
            </wd-button>
          </view>
        </view>

        <view class="network-list">
          <view v-if="wifiNetworks.length === 0 && !scanning" class="empty-state">
            <text class="empty-text">
              暂无WiFi网络
            </text>
            <text class="empty-tip">
              请点击刷新扫描
            </text>
          </view>

          <view v-else class="wifi-list">
            <view
              v-for="network in wifiNetworks"
              :key="network.ssid"
              class="wifi-item"
              @click="selectNetwork(network)"
            >
              <view class="wifi-info">
                <view class="wifi-name">
                  {{ network.ssid }}
                </view>
                <view class="wifi-details">
                  <text class="wifi-signal">
                    信号: {{ network.rssi }}dBm
                  </text>
                  <text class="wifi-channel">
                    频道: {{ network.channel }}
                  </text>
                </view>
              </view>
              <view class="wifi-security">
                <text class="security-icon">
                  {{ network.authmode === 0 ? '开放' : '加密' }}
                </text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 密码输入 -->
    <view v-if="selectedNetwork && selectedNetwork.authmode > 0" class="password-section">
      <view class="password-item">
        <text class="password-label">
          网络密码
        </text>
        <wd-input
          v-model="password"
          placeholder="请输入WiFi密码"
          show-password
          clearable
          @input="onPasswordChange"
        />
      </view>
    </view>
  </view>
</template>

<style scoped>
.wifi-selector {
  width: 100%;
}

.connection-status {
  margin-bottom: 24rpx;
}

.status-warning {
  padding: 24rpx;
  background-color: #fff3cd;
  border: 1rpx solid #ffeaa7;
  border-radius: 16rpx;
}

.status-success {
  padding: 24rpx;
  background-color: #d4edda;
  border: 1rpx solid #c3e6cb;
  border-radius: 16rpx;
}

.status-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.warning-text {
  color: #856404;
  font-size: 28rpx;
}

.success-text {
  color: #155724;
  font-size: 28rpx;
}

.network-selector {
  margin-bottom: 24rpx;
}

.selector-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx;
  background: #f5f7fb;
  border-radius: 12rpx;
  border: 1rpx solid #eeeeee;
  cursor: pointer;
  transition: all 0.3s ease;
}

.selector-item:active {
  background: #eef3ff;
  border-color: #336cff;
}

.selector-label {
  font-size: 28rpx;
  color: #232338;
  font-weight: 500;
}

.selector-value {
  flex: 1;
  text-align: right;
  font-size: 26rpx;
  color: #65686f;
  margin: 0 16rpx;
}

:deep(.arrow-icon) {
  font-size: 20rpx;
  color: #9d9ea3;
}

.network-list-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

.network-list-container {
  width: 100%;
  max-height: 70vh;
  background-color: #ffffff;
  border-radius: 20rpx 20rpx 0 0;
  padding: 32rpx;
  box-sizing: border-box;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
  padding-bottom: 16rpx;
  border-bottom: 1rpx solid #eeeeee;
}

.list-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #232338;
}

.list-actions {
  display: flex;
  gap: 16rpx;
}

.network-list {
  max-height: 50vh;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 20rpx;
  background-color: #fbfbfb;
  border-radius: 16rpx;
  border: 1rpx solid #eeeeee;
}

.empty-text {
  font-size: 32rpx;
  color: #65686f;
  margin-bottom: 16rpx;
}

.empty-tip {
  font-size: 24rpx;
  color: #9d9ea3;
}

.wifi-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.wifi-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32rpx 24rpx;
  background-color: #fbfbfb;
  border: 2rpx solid #eeeeee;
  border-radius: 16rpx;
  transition: all 0.3s ease;
  cursor: pointer;
}

.wifi-item:active {
  transform: scale(0.98);
  background-color: #f0f6ff;
  border-color: #336cff;
}

.wifi-info {
  flex: 1;
}

.wifi-name {
  font-size: 32rpx;
  font-weight: 600;
  color: #232338;
  margin-bottom: 8rpx;
}

.wifi-details {
  display: flex;
  gap: 24rpx;
}

.wifi-signal,
.wifi-channel {
  font-size: 24rpx;
  color: #65686f;
}

.security-icon {
  font-size: 24rpx;
  color: #65686f;
  margin-left: 20rpx;
}

.password-section {
  margin-top: 24rpx;
}

.password-item {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.password-label {
  font-size: 28rpx;
  color: #232338;
  font-weight: 500;
}
</style>
