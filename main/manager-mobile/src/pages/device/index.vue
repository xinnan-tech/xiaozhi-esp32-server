<script lang="ts" setup>
import type { Device, FirmwareType } from '@/api/device'
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'wot-design-uni'
import { bindDevice, bindDeviceManual, getBindDevices, getFirmwareTypes, unbindDevice, updateDeviceAutoUpdate } from '@/api/device'
import { t } from '@/i18n'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'DeviceManage',
})

const props = withDefaults(defineProps<Props>(), {
  agentId: 'default',
})

const actions = [
  { key: 'code', name: t('manualAddDeviceDialog.bindWithCode') },
  { key: 'manual', name: t('manualAddDeviceDialog.title') },
]

// 接收props
interface Props {
  agentId?: string
}

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
const isBindDevice = ref(false)

// 手动绑定弹窗
const isManualBindDialog = ref(false)
const manualBindForm = ref({
  board: '',
  appVersion: '',
  macAddress: '',
})

// 表单校验错误提示
const formErrors = ref({
  board: '',
  appVersion: '',
  macAddress: '',
})

// MAC地址正则校验
const macRegex = /^(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}$/i

function selectBindMode(row) {
  if (row.item.key === 'code') {
    openBindDialog()
  }
  else if (row.item.key === 'manual') {
    // 打开弹窗前重置表单和错误提示
    manualBindForm.value = {
      board: '',
      appVersion: '',
      macAddress: '',
    }
    formErrors.value = {
      board: '',
      appVersion: '',
      macAddress: '',
    }
    isManualBindDialog.value = true
  }
}

// 消息组件
const message = useMessage()

// 使用传入的智能体ID
const currentAgentId = computed(() => {
  return props.agentId
})

// 获取设备列表
async function loadDeviceList() {
  try {
    // 检查是否有当前选中的智能体
    if (!currentAgentId.value) {
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
    return t('device.neverConnected')
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000)
    return t('device.justNow')
  if (diff < 3600000)
    return t('device.minutesAgo', { minutes: Math.floor(diff / 60000) })
  if (diff < 86400000)
    return t('device.hoursAgo', { hours: Math.floor(diff / 3600000) })
  if (diff < 604800000)
    return t('device.daysAgo', { days: Math.floor(diff / 86400000) })

  return date.toLocaleDateString()
}

// 切换OTA自动更新
async function toggleAutoUpdate(device: Device) {
  try {
    const newStatus = device.autoUpdate === 1 ? 0 : 1
    await updateDeviceAutoUpdate(device.id, newStatus)
    device.autoUpdate = newStatus
    toast.success(newStatus === 1 ? t('device.otaAutoUpdateEnabled') : t('device.otaAutoUpdateDisabled'))
  }
  catch (error: any) {
    console.error('更新设备OTA状态失败:', error)
    toast.error(t('device.operationFailed'))
  }
}

// 解绑设备
async function handleUnbindDevice(device: Device) {
  try {
    await unbindDevice(device.id)
    await loadDeviceList()
    toast.success(t('device.deviceUnbound'))
  }
  catch (error: any) {
    console.error('解绑设备失败:', error)
    toast.error(t('device.unbindFailed'))
  }
}

// 确认解绑设备
function confirmUnbindDevice(device: Device) {
  message.confirm({
    title: t('device.unbindDevice'),
    msg: t('device.confirmUnbindDevice', { macAddress: device.macAddress }),
    confirmButtonText: t('device.confirmUnbind'),
    cancelButtonText: t('device.cancel'),
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
      toast.error(t('device.pleaseSelectAgent'))
      return
    }

    await bindDevice(currentAgentId.value, code.trim())
    await loadDeviceList()
    toast.success(t('device.deviceBindSuccess'))
  }
  catch (error: any) {
    console.error('绑定设备失败:', error)
    const errorMessage = error?.message || t('device.bindFailed')
    toast.error(errorMessage)
  }
}

// 打开绑定设备对话框
function openBindDialog() {
  message
    .prompt({
      title: t('device.bindDevice'),
      inputPlaceholder: t('device.enterDeviceCode'),
      inputValue: '',
      inputPattern: /^\d{6}$/,
      confirmButtonText: t('device.bindNow'),
      cancelButtonText: t('device.cancel'),
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

// 手动绑定设备
async function handleManualBind() {
  try {
    // 先校验整个表单
    const isValid = validateForm()
    if (!isValid) {
      return
    }

    if (!currentAgentId.value) {
      toast.error(t('device.pleaseSelectAgent'))
      return
    }

    await bindDeviceManual({
      agentId: currentAgentId.value,
      board: manualBindForm.value.board,
      appVersion: manualBindForm.value.appVersion,
      macAddress: manualBindForm.value.macAddress,
    })
    await loadDeviceList()
    toast.success(t('manualAddDeviceDialog.addSuccess'))
    isManualBindDialog.value = false
    // 重置表单和错误提示
    manualBindForm.value = {
      board: '',
      appVersion: '',
      macAddress: '',
    }
    formErrors.value = {
      board: '',
      appVersion: '',
      macAddress: '',
    }
  }
  catch (error: any) {
    const errorMessage = error?.message || t('manualAddDeviceDialog.addFailed')
    toast.error(errorMessage)
  }
}

// 校验单个字段
function validateField(field: string) {
  switch (field) {
    case 'board':
      if (!manualBindForm.value.board) {
        formErrors.value.board = t('manualAddDeviceDialog.deviceTypePlaceholder')
      }
      else {
        formErrors.value.board = ''
      }
      break
    case 'appVersion':
      if (!manualBindForm.value.appVersion) {
        formErrors.value.appVersion = t('manualAddDeviceDialog.firmwareVersionPlaceholder')
      }
      else {
        formErrors.value.appVersion = ''
      }
      break
    case 'macAddress':
      if (!manualBindForm.value.macAddress) {
        formErrors.value.macAddress = t('manualAddDeviceDialog.macAddressPlaceholder')
      }
      else if (!macRegex.test(manualBindForm.value.macAddress)) {
        formErrors.value.macAddress = t('manualAddDeviceDialog.invalidMacAddress')
      }
      else {
        formErrors.value.macAddress = ''
      }
      break
  }
}

// 清除字段错误提示
function clearFieldError(field: string) {
  formErrors.value[field] = ''
}

// 处理选择器变化
function handlePickerChange() {
  clearFieldError('board')
}

// 校验整个表单
function validateForm(): boolean {
  let isValid = true

  // 校验设备类型
  if (!manualBindForm.value.board) {
    formErrors.value.board = t('manualAddDeviceDialog.deviceTypePlaceholder')
    isValid = false
  }
  else {
    formErrors.value.board = ''
  }

  // 校验固件版本
  if (!manualBindForm.value.appVersion) {
    formErrors.value.appVersion = t('manualAddDeviceDialog.firmwareVersionPlaceholder')
    isValid = false
  }
  else {
    formErrors.value.appVersion = ''
  }

  // 校验MAC地址
  if (!manualBindForm.value.macAddress) {
    formErrors.value.macAddress = t('manualAddDeviceDialog.macAddressPlaceholder')
    isValid = false
  }
  else if (!macRegex.test(manualBindForm.value.macAddress)) {
    formErrors.value.macAddress = t('manualAddDeviceDialog.invalidMacAddress')
    isValid = false
  }
  else {
    formErrors.value.macAddress = ''
  }

  return isValid
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
        {{ t('device.loading') }}
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
                      {{ t('device.macAddress') }}：{{ device.macAddress }}
                    </text>
                    <text class="mb-[12rpx] block text-[28rpx] text-[#65686f] leading-[1.4]">
                      {{ t('device.firmwareVersion') }}：{{ device.appVersion }}
                    </text>
                    <text class="block text-[28rpx] text-[#65686f] leading-[1.4]">
                      {{ t('device.lastConnection') }}：{{ formatTime(device.lastConnectedAt) }}
                    </text>
                  </view>

                  <view class="flex items-center justify-between border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx]">
                    <text class="text-[28rpx] text-[#232338] font-medium">
                      {{ t('device.otaUpdate') }}
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
                  <text>{{ t('device.unbind') }}</text>
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
          {{ t('device.noDevice') }}
        </text>
        <text class="text-[26rpx] text-[#999999] leading-[1.5]">
          {{ t('device.clickToBindFirstDevice') }}
        </text>
      </view>
    </view>

    <!-- FAB 绑定设备按钮 -->
    <wd-fab type="primary" size="small" icon="add" :draggable="true" :expandable="false" @click="isBindDevice = true" />

    <!-- MessageBox 组件 -->
    <wd-message-box />
    <wd-action-sheet v-model="isBindDevice" :actions="actions" @close="isBindDevice = false" @select="selectBindMode" />

    <!-- 手动绑定设备弹窗 -->
    <wd-popup v-model="isManualBindDialog" position="bottom" :close-on-click-modal="false" custom-style="border-radius: 24rpx 24rpx 0 0;">
      <view class="manual-bind-dialog">
        <view class="dialog-header">
          <text class="dialog-title">
            {{ t('manualAddDeviceDialog.title') }}
          </text>
          <wd-icon name="close" size="20" @click="isManualBindDialog = false" />
        </view>

        <view class="dialog-content">
          <view class="form-item">
            <text class="form-label">
              {{ t('manualAddDeviceDialog.deviceType') }}
              <text class="required">
                *
              </text>
            </text>
            <wd-picker
              v-model="manualBindForm.board"
              class="custom-wd-picker"
              :columns="firmwareTypes.map(item => ({ value: item.key, label: item.name }))"
              :placeholder="t('manualAddDeviceDialog.deviceTypePlaceholder')"
              :cancel-button-text="t('common.cancel')"
              :confirm-button-text="t('common.confirm')"
              @confirm="handlePickerChange"
            />
            <text v-if="formErrors.board" class="error-text">
              {{ formErrors.board }}
            </text>
          </view>

          <view class="form-item">
            <text class="form-label">
              {{ t('manualAddDeviceDialog.firmwareVersion') }}
              <text class="required">
                *
              </text>
            </text>
            <wd-input
              v-model="manualBindForm.appVersion"
              :placeholder="t('manualAddDeviceDialog.firmwareVersionPlaceholder')"
              @input="clearFieldError('appVersion')"
              @blur="validateField('appVersion')"
            />
            <text v-if="formErrors.appVersion" class="error-text">
              {{ formErrors.appVersion }}
            </text>
          </view>

          <view class="form-item">
            <text class="form-label">
              {{ t('manualAddDeviceDialog.macAddress') }}
              <text class="required">
                *
              </text>
            </text>
            <wd-input
              v-model="manualBindForm.macAddress"
              :placeholder="t('manualAddDeviceDialog.macAddressPlaceholder')"
              @input="validateField('macAddress')"
              @blur="validateField('macAddress')"
            />
            <text v-if="formErrors.macAddress" class="error-text">
              {{ formErrors.macAddress }}
            </text>
          </view>
        </view>

        <view class="dialog-footer">
          <wd-button block type="primary" @click="handleManualBind">
            {{ t('manualAddDeviceDialog.confirm') }}
          </wd-button>
        </view>
      </view>
    </wd-popup>
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
::v-deep .wd-action-sheet__popup,
::v-deep .wd-popup {
  z-index: 100 !important;
}
.custom-wd-picker ::v-deep .wd-picker__cell {
  padding-left: 0 !important;
}

:deep(.wd-icon) {
  font-size: 32rpx;
}

.manual-bind-dialog {
  padding: 32rpx;
  background: #ffffff;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32rpx;
}

.dialog-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #232338;
}

.dialog-content {
  margin-bottom: 32rpx;
}

.form-item {
  margin-bottom: 24rpx;
}

.form-label {
  display: block;
  font-size: 28rpx;
  color: #65686f;
  margin-bottom: 12rpx;
}

.required {
  color: #ff4d4f;
  margin-left: 4rpx;
}

.error-text {
  display: block;
  font-size: 24rpx;
  color: #ff4d4f;
  margin-top: 8rpx;
}

.dialog-footer {
  padding-top: 16rpx;
}
</style>
