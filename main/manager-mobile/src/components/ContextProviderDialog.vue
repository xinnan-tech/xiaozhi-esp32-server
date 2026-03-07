<script lang="ts" setup>
import { ref, watch } from 'vue'
import { t } from '@/i18n'

interface Props {
  visible?: boolean
  providers?: Array<{
    url: string
    headers: Record<string, string>
  }>
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  providers: () => [],
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'confirm': [value: Array<{
    url: string
    headers: Record<string, string>
  }>]
}>()

const localProviders = ref<Array<{
  url: string
  headers: Array<{
    key: string
    value: string
  }>
}>>([])

function initLocalData() {
  localProviders.value = props.providers.map((p) => {
    const headers = p.headers || {}
    return {
      url: p.url || '',
      headers: Object.entries(headers).map(([key, value]) => ({ key, value })),
    }
  })

  if (localProviders.value.length === 0) {
    localProviders.value.push({ url: '', headers: [{ key: '', value: '' }] })
  }
}

function addProvider(index: number) {
  localProviders.value.splice(index, 0, {
    url: '',
    headers: [{ key: '', value: '' }],
  })
}

function removeProvider(index: number) {
  localProviders.value.splice(index, 1)
}

function addHeader(pIndex: number, hIndex: number) {
  localProviders.value[pIndex].headers.splice(hIndex, 0, { key: '', value: '' })
}

function removeHeader(pIndex: number, hIndex: number) {
  localProviders.value[pIndex].headers.splice(hIndex, 1)
}

function handleConfirm() {
  const result = localProviders.value
    .filter(p => p.url.trim() !== '')
    .map((p) => {
      const headersObj: Record<string, string> = {}
      p.headers.forEach((h) => {
        if (h.key.trim()) {
          headersObj[h.key.trim()] = h.value
        }
      })
      return {
        url: p.url.trim(),
        headers: headersObj,
      }
    })

  emit('confirm', result)
  emit('update:visible', false)
}

function handleClose() {
  emit('update:visible', false)
}

watch(() => props.visible, (val) => {
  if (val) {
    initLocalData()
  }
})
</script>

<template>
  <view v-if="visible" class="context-provider-dialog-mask" @click="handleClose">
    <view class="context-provider-dialog" @click.stop>
      <view class="dialog-header">
        <text class="dialog-title">
          {{ t('contextProviderDialog.title') }}
        </text>
      </view>

      <view class="dialog-content">
        <view v-if="localProviders.length === 0" class="empty-container">
          <text class="empty-text">
            {{ t('contextProviderDialog.noContextApi') }}
          </text>
          <wd-button type="primary" size="small" @click="addProvider(0)">
            {{ t('contextProviderDialog.add') }}
          </wd-button>
        </view>

        <view v-else class="providers-list">
          <view v-for="(provider, pIndex) in localProviders" :key="pIndex" class="provider-item">
            <view class="provider-card">
              <view class="card-header">
                <view class="card-controls">
                  <wd-button
                    type="icon"
                    icon="add"
                    size="small"
                    class="!h-[60rpx] !w-[60rpx] !bg-[#66b1ff] !text-[#fff]"
                    @click="addProvider(pIndex + 1)"
                  />
                  <wd-button
                    type="icon"
                    icon="decrease"
                    size="small"
                    class="!h-[60rpx] !w-[60rpx] !bg-[#F56C6C] !text-[#fff]"
                    @click="removeProvider(pIndex)"
                  />
                </view>
              </view>
              <view class="input-row">
                <text class="label-text">
                  {{ t('contextProviderDialog.apiUrl') }}
                </text>
                <wd-input
                  v-model="provider.url"
                  class="flex-1"
                  :placeholder="t('contextProviderDialog.apiUrlPlaceholder')"
                />
              </view>

              <view class="headers-section">
                <view class="label-text" style="margin-top: 6px;">
                  {{ t('contextProviderDialog.requestHeaders') }}
                </view>
                <view class="headers-list">
                  <view
                    v-for="(header, hIndex) in provider.headers"
                    :key="hIndex"
                    class="header-row-vertical"
                  >
                    <view class="header-input-group">
                      <wd-input
                        v-model="header.key"
                        placeholder="key"
                        class="header-input-full"
                      />
                    </view>
                    <view class="header-input-group">
                      <wd-input
                        v-model="header.value"
                        placeholder="value"
                        class="header-input-full"
                      />
                    </view>
                    <view class="header-controls">
                      <wd-button
                        type="icon"
                        icon="add"
                        size="small"
                        class="!h-[50rpx] !w-[50rpx] !border-[1rpx] !border-solid !bg-[#ecf5ff] !text-[#b3d8ff]"
                        @click="addHeader(pIndex, hIndex + 1)"
                      />
                      <wd-button
                        type="icon"
                        icon="decrease"
                        size="small"
                        class="!h-[50rpx] !w-[50rpx] !border-[1rpx] !border-solid !bg-[#fef0f0] !text-[#F56C6C]"
                        @click="removeHeader(pIndex, hIndex)"
                      />
                    </view>
                  </view>
                  <view v-if="provider.headers.length === 0" class="header-row empty-header">
                    <text class="no-header-text">
                      {{ t('contextProviderDialog.noHeaders') }}
                    </text>
                    <wd-button type="text" size="small" @click="addHeader(pIndex, 0)">
                      {{ t('contextProviderDialog.addHeader') }}
                    </wd-button>
                  </view>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="dialog-footer">
        <wd-button class="cancel-btn" @click="handleClose">
          {{ t('contextProviderDialog.cancel') }}
        </wd-button>
        <wd-button type="primary" class="confirm-btn" @click="handleConfirm">
          {{ t('contextProviderDialog.confirm') }}
        </wd-button>
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
.context-provider-dialog-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.context-provider-dialog {
  background: #fff;
  // border-radius: 20rpx;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx;
  border-bottom: 1px solid #eee;
}

.dialog-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #232338;
}

.close-icon {
  font-size: 40rpx;
  color: #9d9ea3;
  cursor: pointer;
}

.dialog-content {
  flex: 1;
  overflow-y: auto;
  padding: 20rpx;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 0;
  gap: 30rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #9d9ea3;
}

.providers-list {
  display: flex;
  flex-direction: column;
}

.provider-item {
  margin-bottom: 30rpx;
}

.provider-card {
  flex: 1;
  background: #fff;
  border-radius: 16rpx;
  border: 1px solid #eee;
  border-left: 6rpx solid #336cff;
  padding: 20rpx;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #232338;
}

.card-controls {
  display: flex;
  gap: 16rpx;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 40rpx;
}

.headers-section {
  display: flex;
  gap: 20rpx;
  align-items: flex-start;
}

.headers-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  background: #fcfcfc;
  padding: 4rpx;
  border-radius: 12rpx;
  border: 1px dashed #dcdfe6;
}

.header-row-vertical {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  background: #fff;
  // padding: 20rpx;
  border-radius: 12rpx;
  // border: 1px solid #e8e8e8;
}

.header-input-group {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.header-key-label,
.header-value-label {
  font-size: 24rpx;
  font-weight: 500;
  color: #606266;
}

.header-input-full {
  width: 100%;
}

.header-controls {
  display: flex;
  gap: 12rpx;
  // margin-top: 8rpx;
  align-self: flex-start;
}

.block-controls {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  padding-top: 10rpx;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 20rpx;
}

.label-text {
  font-size: 28rpx;
  font-weight: 600;
  color: #606266;
  width: 140rpx;
}

.headers-section {
  display: flex;
  gap: 20rpx;
  align-items: flex-start;
}

.headers-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  background: #fcfcfc;
  padding: 16rpx;
  border-radius: 12rpx;
  border: 1px dashed #dcdfe6;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.header-input {
  width: 200rpx;
}

.separator {
  color: #909399;
  font-weight: bold;
  font-size: 32rpx;
}

.row-controls {
  display: flex;
  gap: 12rpx;
  margin-left: 8rpx;
  flex-shrink: 0;
}

.empty-header {
  justify-content: center;
  padding: 20rpx;
  color: #909399;
  font-size: 26rpx;
}

.no-header-text {
  margin-right: 16rpx;
}

.flex-1 {
  flex: 1;
}

.dialog-footer {
  display: flex;
  gap: 20rpx;
  padding: 30rpx;
  border-top: 1px solid #eee;
}

.cancel-btn,
.confirm-btn {
  flex: 1;
  height: 80rpx;
  border-radius: 12rpx;
  font-size: 28rpx;
}
</style>
