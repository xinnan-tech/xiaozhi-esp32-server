<script lang="ts" setup>
import type { Device, FirmwareType } from '@/api/device'
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'wot-design-uni'
import { bindDevice, getBindDevices, getFirmwareTypes, unbindDevice, updateDeviceAutoUpdate } from '@/api/device'
import { toast } from '@/utils/toast'
import { parseDeviceLastConnectedAtTimestamp } from './deviceTimeUtils.mjs'

defineOptions({
  name: 'DeviceManage',
})

// Receive props
interface Props {
  agentId?: string
}

const props = withDefaults(defineProps<Props>(), {
  agentId: 'default'
})

// Get screen boundary to safe area distance
let safeAreaInsets: any
let systemInfo: any

// #ifdef MP-WEIXIN
systemInfo = uni.getWindowInfo()
safeAreaInsets = systemInfo.safeArea
  ? {
      top: systemInfo.safeArea.top,
      right: systemInfo.windowWidth - systemInfo.safeArea.right,
      bottom: systemInfo.windowHeight - systemInfo.safeArea.bottom,
      left: systemInfo.safeArea.left,
    }
  : null
// #endif

// #ifndef MP-WEIXIN
systemInfo = uni.getSystemInfoSync()
safeAreaInsets = systemInfo.safeAreaInsets
// #endif

// Device data
const deviceList = ref<Device[]>([])
const firmwareTypes = ref<FirmwareType[]>([])
const loading = ref(false)

// Message component
const message = useMessage()

// Use passed agent ID
const currentAgentId = computed(() => {
  return props.agentId
})

// Get device list
async function loadDeviceList() {
  try {
    console.log('Get device list')

    // Check if there is currently selected agent
    if (!currentAgentId.value) {
      console.warn('No selected agent')
      deviceList.value = []
      return
    }

    loading.value = true
    const response = await getBindDevices(currentAgentId.value)
    deviceList.value = response || []
  }
  catch (error) {
    console.error('Failed to get device list:', error)
    deviceList.value = []
  }
  finally {
    loading.value = false
  }
}

// Refresh method exposed to parent component
async function refresh() {
  await loadDeviceList()
}

// Get device type name
function getDeviceTypeName(boardKey: string): string {
  const firmwareType = firmwareTypes.value.find(type => type.key === boardKey)
  return firmwareType?.name || boardKey
}

// Format time
function formatTime(timeStr: string) {
  if (!timeStr)
    return 'Never connected'
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000)
    return 'Just now'
  if (diff < 3600000)
    return `${Math.floor(diff / 60000)} minutes ago`
  if (diff < 86400000)
    return `${Math.floor(diff / 3600000)} hours ago`
  if (diff < 604800000)
    return `${Math.floor(diff / 86400000)} days ago`

  return date.toLocaleDateString()
}

// Toggle OTA auto update
async function toggleAutoUpdate(device: Device) {
  try {
    const newStatus = device.autoUpdate === 1 ? 0 : 1
    await updateDeviceAutoUpdate(device.id, newStatus)
    device.autoUpdate = newStatus
    toast.success(newStatus === 1 ? 'OTA auto upgrade enabled' : 'OTA auto upgrade disabled')
  }
  catch (error: any) {
    console.error('Failed to update device OTA status:', error)
    toast.error('Operation failed, please try again')
  }
}

// Unbind device
async function handleUnbindDevice(device: Device) {
  try {
    await unbindDevice(device.id)
    await loadDeviceList()
    toast.success('Device unbound')
  }
  catch (error: any) {
    console.error('Failed to unbind device:', error)
    toast.error('Unbind failed, please try again')
  }
}

// Confirm unbind device
function confirmUnbindDevice(device: Device) {
  message.confirm({
    title: 'Unbind Device',
    msg: `Are you sure you want to unbind device "${device.macAddress}"?`,
    confirmButtonText: 'Confirm Unbind',
    cancelButtonText: 'Cancel',
  }).then(() => {
    handleUnbindDevice(device)
  }).catch(() => {
    // User cancelled
  })
}

// Bind new device
async function handleBindDevice(code: string) {
  try {
    if (!currentAgentId.value) {
      toast.error('Please select an agent first')
      return
    }

    await bindDevice(currentAgentId.value, code.trim())
    await loadDeviceList()
    toast.success('Device bound successfully!')
  }
  catch (error: any) {
    console.error('Failed to bind device:', error)
    const errorMessage = error?.message || 'Binding failed, please check if the verification code is correct'
    toast.error(errorMessage)
  }
}

// Open bind device dialog
function openBindDialog() {
  message
    .prompt({
      title: 'Bind Device',
      inputPlaceholder: 'Please enter device verification code',
      inputValue: '',
      inputPattern: /^\d{6}$/,
      confirmButtonText: 'Bind Now',
      cancelButtonText: 'Cancel',
    })
    .then(async (result: any) => {
      if (result.value && String(result.value).trim()) {
        await handleBindDevice(String(result.value).trim())
      }
    })
    .catch(() => {
      // User cancelled operation
    })
}

// Get device type list
async function loadFirmwareTypes() {
  try {
    const response = await getFirmwareTypes()
    firmwareTypes.value = response
  }
  catch (error) {
    console.error('Failed to get device types:', error)
  }
}

onMounted(async () => {
  // Agent simplified to default

  loadFirmwareTypes()
  loadDeviceList()
})

// Expose methods to parent component
defineExpose({
  refresh,
})
</script>

<template>
  <view class="device-container" style="background: #f5f7fb; min-height: 100%;">
    <!-- Loading state -->
    <view v-if="loading && deviceList.length === 0" class="loading-container">
      <wd-loading color="#336cff" />
      <text class="loading-text">
        Loading...
      </text>
    </view>

    <!-- Device list -->
    <view v-else-if="deviceList.length > 0" class="device-list">
      <!-- Device card list -->
      <view class="box-border flex flex-col gap-[24rpx] p-[20rpx]">
        <view v-for="device in deviceList" :key="device.id">
          <wd-swipe-action>
            <view class="cursor-pointer bg-[#fbfbfb] p-[32rpx] transition-all duration-200 active:bg-[#f8f9fa]">
              <view class="flex items-start justify-between">
                <view class="flex-1">
                  <view class="mb-[16rpx] flex items-center justify-between">
                    <text class="max-w-[60%] break-all text-[32rpx] text-[#232338] font-semibold">
                      {{ getDeviceTypeName(device.board) }}
                    </text>
                  </view>

                  <view class="mb-[20rpx]">
                    <text class="mb-[12rpx] block text-[28rpx] text-[#65686f] leading-[1.4]">
                      MAC Address: {{ device.macAddress }}
                    </text>
                    <text class="mb-[12rpx] block text-[28rpx] text-[#65686f] leading-[1.4]">
                      Firmware Version: {{ device.appVersion }}
                    </text>
                    <text class="block text-[28rpx] text-[#65686f] leading-[1.4]">
                      Last Conversation: {{ formatTime(device.lastConnectedAt) }}
                    </text>
                  </view>

                  <view class="flex items-center justify-between border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx]">
                    <text class="text-[28rpx] text-[#232338] font-medium">
                      OTA Update
                    </text>
                    <wd-switch
                      :model-value="device.autoUpdate === 1"
                      size="24"
                      @change="toggleAutoUpdate(device)"
                    />
                  </view>
                </view>
              </view>
            </view>

            <template #right>
              <view class="h-full flex">
                <view
                  class="h-full min-w-[120rpx] flex items-center justify-center bg-[#ff4d4f] p-x-[32rpx] text-[28rpx] text-white font-medium"
                  @click.stop="confirmUnbindDevice(device)"
                >
                  <wd-icon name="delete" />
                  <text>Unbind</text>
                </view>
              </view>
            </template>
          </wd-swipe-action>
        </view>
      </view>
    </view>

    <!-- Empty state -->
    <view v-else-if="!loading" class="empty-container">
      <view class="flex flex-col items-center justify-center p-[100rpx_40rpx] text-center">
        <wd-icon name="phone" custom-class="text-[120rpx] text-[#d9d9d9] mb-[32rpx]" />
        <text class="mb-[16rpx] text-[32rpx] text-[#666666] font-medium">
          No devices yet
        </text>
        <text class="text-[26rpx] text-[#999999] leading-[1.5]">
          Click the + button in the bottom right to bind your first device
        </text>
      </view>
    </view>

    <!-- FAB bind device button -->
    <wd-fab type="primary" size="small" icon="add" :draggable="true" :expandable="false" @click="openBindDialog" />

    <!-- MessageBox component -->
    <wd-message-box />
  </view>
</template>

<style scoped>
.device-container {
  position: relative;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 40rpx;
}

.loading-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #666666;
}

:deep(.wd-swipe-action) {
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
  border: 1rpx solid #eeeeee;
}

:deep(.wd-icon) {
  font-size: 32rpx;
}
</style>
