<script lang="ts" setup>
import type { Device, FirmwareType } from '@/api/device'
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'wot-design-uni'
import { bindDevice, getBindDevices, getFirmwareTypes, unbindDevice, updateDeviceAutoUpdate } from '@/api/device'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'DeviceManage',
})

// 接收props
interface Props {
  agentId?: string
}

const props = withDefaults(defineProps<Props>(), {
  agentId: 'default'
})

// 获取屏幕边界到安全区域距离
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

// 设备数据
const deviceList = ref<Device[]>([])
const firmwareTypes = ref<FirmwareType[]>([])
const loading = ref(false)

// 消息组件
const message = useMessage()

// 使用传入的智能体ID
const currentAgentId = computed(() => {
  return props.agentId
})

// 获取设备列表
async function loadDeviceList() {
  try {
    console.log('获取设备列表')

    // 检查是否有当前选中的智能体
    if (!currentAgentId.value) {
      console.warn('没有选中的智能体')
      deviceList.value = []
      return
    }

    loading.value = true
    const response = await getBindDevices(currentAgentId.value)
    deviceList.value = response || []
  }
  catch (error) {
    console.error('获取设备列表失败:', error)
    deviceList.value = []
  }
  finally {
    loading.value = false
  }
}

// 暴露给父组件的刷新方法
async function refresh() {
  await loadDeviceList()
}

// 获取设备类型名称
function getDeviceTypeName(boardKey: string): string {
  const firmwareType = firmwareTypes.value.find(type => type.key === boardKey)
  return firmwareType?.name || boardKey
}

// 格式化时间
function formatTime(timeStr: string) {
  if (!timeStr)
    return '从未连接'
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000)
    return '刚刚'
  if (diff < 3600000)
    return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000)
    return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000)
    return `${Math.floor(diff / 86400000)}天前`

  return date.toLocaleDateString()
}

// 切换OTA自动更新
async function toggleAutoUpdate(device: Device) {
  try {
    const newStatus = device.autoUpdate === 1 ? 0 : 1
    await updateDeviceAutoUpdate(device.id, newStatus)
    device.autoUpdate = newStatus
    toast.success(newStatus === 1 ? 'OTA自动升级已开启' : 'OTA自动升级已关闭')
  }
  catch (error: any) {
    console.error('更新设备OTA状态失败:', error)
    toast.error('操作失败，请重试')
  }
}

// 解绑设备
async function handleUnbindDevice(device: Device) {
  try {
    await unbindDevice(device.id)
    await loadDeviceList()
    toast.success('设备已解绑')
  }
  catch (error: any) {
    console.error('解绑设备失败:', error)
    toast.error('解绑失败，请重试')
  }
}

// 确认解绑设备
function confirmUnbindDevice(device: Device) {
  message.confirm({
    title: '解绑设备',
    msg: `确定要解绑设备 "${device.macAddress}" 吗？`,
    confirmButtonText: '确定解绑',
    cancelButtonText: '取消',
  }).then(() => {
    handleUnbindDevice(device)
  }).catch(() => {
    // 用户取消
  })
}

// 绑定新设备
async function handleBindDevice(code: string) {
  try {
    if (!currentAgentId.value) {
      toast.error('请先选择智能体')
      return
    }

    await bindDevice(currentAgentId.value, code.trim())
    await loadDeviceList()
    toast.success('设备绑定成功！')
  }
  catch (error: any) {
    console.error('绑定设备失败:', error)
    const errorMessage = error?.message || '绑定失败，请检查验证码是否正确'
    toast.error(errorMessage)
  }
}

// 打开绑定设备对话框
function openBindDialog() {
  message
    .prompt({
      title: '绑定设备',
      inputPlaceholder: '请输入设备验证码',
      inputValue: '',
      inputPattern: /^\d{6}$/,
      confirmButtonText: '立即绑定',
      cancelButtonText: '取消',
    })
    .then(async (result: any) => {
      if (result.value && String(result.value).trim()) {
        await handleBindDevice(String(result.value).trim())
      }
    })
    .catch(() => {
      // 用户取消操作
    })
}

// 获取设备类型列表
async function loadFirmwareTypes() {
  try {
    const response = await getFirmwareTypes()
    firmwareTypes.value = response
  }
  catch (error) {
    console.error('获取设备类型失败:', error)
  }
}

onMounted(async () => {
  // 智能体已简化为默认

  loadFirmwareTypes()
  loadDeviceList()
})

// 暴露方法给父组件
defineExpose({
  refresh,
})
</script>

<template>
  <view class="device-container" style="background: #f5f7fb; min-height: 100%;">
    <!-- 加载状态 -->
    <view v-if="loading && deviceList.length === 0" class="loading-container">
      <wd-loading color="#336cff" />
      <text class="loading-text">
        加载中...
      </text>
    </view>

    <!-- 设备列表 -->
    <view v-else-if="deviceList.length > 0" class="device-list">
      <!-- 设备卡片列表 -->
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
                      MAC地址：{{ device.macAddress }}
                    </text>
                    <text class="mb-[12rpx] block text-[28rpx] text-[#65686f] leading-[1.4]">
                      固件版本：{{ device.appVersion }}
                    </text>
                    <text class="block text-[28rpx] text-[#65686f] leading-[1.4]">
                      最近对话：{{ formatTime(device.lastConnectedAt) }}
                    </text>
                  </view>

                  <view class="flex items-center justify-between border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx]">
                    <text class="text-[28rpx] text-[#232338] font-medium">
                      OTA升级
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
                  <text>解绑</text>
                </view>
              </view>
            </template>
          </wd-swipe-action>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else-if="!loading" class="empty-container">
      <view class="flex flex-col items-center justify-center p-[100rpx_40rpx] text-center">
        <wd-icon name="phone" custom-class="text-[120rpx] text-[#d9d9d9] mb-[32rpx]" />
        <text class="mb-[16rpx] text-[32rpx] text-[#666666] font-medium">
          暂无设备
        </text>
        <text class="text-[26rpx] text-[#999999] leading-[1.5]">
          点击右下角 + 号绑定您的第一个设备
        </text>
      </view>
    </view>

    <!-- FAB 绑定设备按钮 -->
    <wd-fab type="primary" size="small" icon="add" :draggable="true" :expandable="false" @click="openBindDialog" />

    <!-- MessageBox 组件 -->
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
