<script lang="ts" setup>
import { ref, watch } from 'vue'
import { t } from '@/i18n'

interface Props {
  visible?: boolean
  settings?: {
    volume: number
    speed: number
    pitch: number
  }
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  settings: () => ({
    volume: 0,
    speed: 0,
    pitch: 0,
  }),
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'confirm': [value: {
    volume: number
    speed: number
    pitch: number
  }]
}>()

const localSettings = ref({
  volume: 0,
  speed: 0,
  pitch: 0,
})

function initLocalData() {
  localSettings.value = {
    volume: props.settings.volume || 0,
    speed: props.settings.speed || 0,
    pitch: props.settings.pitch || 0,
  }
}

function handleConfirm() {
  emit('confirm', localSettings.value)
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
  <view v-if="visible" class="voice-settings-dialog-mask" @click="handleClose">
    <view class="voice-settings-dialog" @click.stop>
      <view class="dialog-header">
        <text class="dialog-title">
          {{ t('agent.languageConfig') }}
        </text>
      </view>

      <view class="dialog-content">
        <!-- 音量调节 -->
        <view class="setting-item">
          <text class="setting-label">
            {{ t('agent.ttsVolume') }}
          </text>
          <view class="slider-container">
            <wd-slider
              v-model="localSettings.volume"
              :min="-100"
              :max="100"
              :step="1"
              :show-value="false"
              custom-class="voice-slider"
            />
            <text class="slider-value">
              {{ localSettings.volume }}
            </text>
          </view>
          <text class="setting-desc">
            {{ t('agent.volumeHint') }}
          </text>
        </view>

        <!-- 语速调节 -->
        <view class="setting-item">
          <text class="setting-label">
            {{ t('agent.ttsRate') }}
          </text>
          <view class="slider-container">
            <wd-slider
              v-model="localSettings.speed"
              :min="-100"
              :max="100"
              :step="1"
              :show-value="false"
              custom-class="voice-slider"
            />
            <text class="slider-value">
              {{ localSettings.speed }}
            </text>
          </view>
          <text class="setting-desc">
            {{ t('agent.speedHint') }}
          </text>
        </view>

        <!-- 音调调节 -->
        <view class="setting-item">
          <text class="setting-label">
            {{ t('agent.ttsPitch') }}
          </text>
          <view class="slider-container">
            <wd-slider
              v-model="localSettings.pitch"
              :min="-100"
              :max="100"
              :step="1"
              :show-value="false"
              custom-class="voice-slider"
            />
            <text class="slider-value">
              {{ localSettings.pitch }}
            </text>
          </view>
          <text class="setting-desc">
            {{ t('agent.pitchHint') }}
          </text>
        </view>
      </view>

      <view class="dialog-footer">
        <wd-button class="cancel-btn" @click="handleClose">
          {{ t('agent.cancel') }}
        </wd-button>
        <wd-button type="primary" class="confirm-btn" @click="handleConfirm">
          {{ t('agent.save') }}
        </wd-button>
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
.voice-settings-dialog-mask {
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

.voice-settings-dialog {
  background: #fff;
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
  padding: 30rpx;
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
  padding: 40rpx;
  display: flex;
  flex-direction: column;
  gap: 50rpx;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.setting-label {
  font-size: 30rpx;
  font-weight: 600;
  color: #232338;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.voice-slider {
  flex: 1;
}

.slider-value {
  font-size: 28rpx;
  color: #336cff;
  font-weight: 500;
  min-width: 80rpx;
  text-align: right;
}

.setting-desc {
  font-size: 24rpx;
  color: #9d9ea3;
  margin-top: 10rpx;
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

.confirm-btn {
  background-color: #336cff !important;
}

/* 自定义滑块样式 */
:deep(.wd-slider) {
  --wd-slider-bar-background: #e6ebff;
  --wd-slider-bar-active-background: #336cff;
  --wd-slider-thumb-border-color: #336cff;
  --wd-slider-thumb-background: #336cff;
  --wd-slider-thumb-size: 32rpx;
}
</style>
