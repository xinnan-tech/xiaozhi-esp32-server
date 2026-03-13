<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationBarTitleText": "语音设置",
    "navigationStyle": "custom"
  }
}
</route>

<script lang="ts" setup>
import { t } from '@/i18n'
import { useSpeedPitch } from '@/store'

defineOptions({
  name: 'SpeedPitch',
})

const speedPitchStore = useSpeedPitch()

const localSettings = ref({
  ttsVolume: 0,
  ttsRate: 0,
  ttsPitch: 0,
})

function handleConfirm() {
  speedPitchStore.updateSpeedPitch(localSettings.value)
  goBack()
}

// 返回上一页并更新配置
function goBack() {
  uni.navigateBack()
}

onMounted(() => {
  localSettings.value = {
    ttsVolume: speedPitchStore.speedPitch.ttsVolume,
    ttsRate: speedPitchStore.speedPitch.ttsRate,
    ttsPitch: speedPitchStore.speedPitch.ttsPitch,
  }
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- 头部导航 -->
    <wd-navbar
      :title="t('agent.languageConfig')"
      safe-area-inset-top
      left-arrow
      :bordered="false"
      @click-left="goBack"
    >
      <template #left>
        <wd-icon name="arrow-left" size="18" />
      </template>
    </wd-navbar>
    <view class="flex flex-1 flex-col overflow-hidden">
      <view class="flex flex-1 flex-col gap-[50rpx] overflow-y-auto px-[40rpx] py-[50rpx]">
        <!-- 音量调节 -->
        <view class="flex flex-col gap-[20rpx]">
          <text class="text-[30rpx] text-[#232338] font-semibold">
            {{ t('agent.ttsVolume') }}
          </text>
          <view class="flex items-center gap-[20rpx]">
            <wd-slider
              v-model="localSettings.ttsVolume"
              :min="-100"
              :max="100"
              :step="1"
              :show-value="false"
              custom-class="voice-slider"
              class="flex-1"
            />
            <text class="min-w-[80rpx] text-right text-[28rpx] text-[#336cff] font-medium">
              {{ localSettings.ttsVolume }}
            </text>
          </view>
          <text class="mt-[10rpx] text-[24rpx] text-[#9d9ea3]">
            {{ t('agent.volumeHint') }}
          </text>
        </view>

        <!-- 语速调节 -->
        <view class="flex flex-col gap-[20rpx]">
          <text class="text-[30rpx] text-[#232338] font-semibold">
            {{ t('agent.ttsRate') }}
          </text>
          <view class="flex items-center gap-[20rpx]">
            <wd-slider
              v-model="localSettings.ttsRate"
              :min="-100"
              :max="100"
              :step="1"
              :show-value="false"
              custom-class="voice-slider"
              class="flex-1"
            />
            <text class="min-w-[80rpx] text-right text-[28rpx] text-[#336cff] font-medium">
              {{ localSettings.ttsRate }}
            </text>
          </view>
          <text class="mt-[10rpx] text-[24rpx] text-[#9d9ea3]">
            {{ t('agent.speedHint') }}
          </text>
        </view>

        <!-- 音调调节 -->
        <view class="flex flex-col gap-[20rpx]">
          <text class="text-[30rpx] text-[#232338] font-semibold">
            {{ t('agent.ttsPitch') }}
          </text>
          <view class="flex items-center gap-[20rpx]">
            <wd-slider
              v-model="localSettings.ttsPitch"
              :min="-100"
              :max="100"
              :step="1"
              :show-value="false"
              custom-class="voice-slider"
              class="flex-1"
            />
            <text class="min-w-[80rpx] text-right text-[28rpx] text-[#336cff] font-medium">
              {{ localSettings.ttsPitch }}
            </text>
          </view>
          <text class="mt-[10rpx] text-[24rpx] text-[#9d9ea3]">
            {{ t('agent.pitchHint') }}
          </text>
        </view>
      </view>

      <view class="flex gap-[20rpx] border-t border-[#eee] px-[30rpx] py-[30rpx]">
        <wd-button type="primary" class="h-[80rpx] flex-1 rounded-[12rpx] text-[28rpx] !bg-[#336cff]" @click="handleConfirm">
          {{ t('agent.save') }}
        </wd-button>
      </view>
    </view>
  </view>
</template>

<style scoped lang="scss">
/* 自定义滑块样式 */
:deep(.wd-slider) {
  --wd-slider-bar-background: #e6ebff;
  --wd-slider-bar-active-background: #336cff;
  --wd-slider-thumb-border-color: #336cff;
  --wd-slider-thumb-background: #336cff;
  --wd-slider-thumb-size: 32rpx;
}
</style>
