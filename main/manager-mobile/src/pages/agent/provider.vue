<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationBarTitleText": "编辑源",
    "navigationStyle": "custom"
  }
}
</route>

<script lang="ts" setup>
import type { Providers } from '@/api/agent/types'
import { onMounted, ref } from 'vue'
import { t } from '@/i18n'
import { useProvider } from '@/store/provider'

defineOptions({
  name: 'Provider',
})

const providerStore = useProvider()

const localProviders = ref<Providers[]>([])

function initLocalData() {
  localProviders.value = providerStore.providers.map((p) => {
    const headers = p.headers || {}
    return {
      url: p.url,
      headers: Object.entries(headers).map(([key, value]: [string, string]) => ({ key, value })),
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
      const headersObj = {}
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

  providerStore.updateProviders(result as Providers[])
  goBack()
}

function goBack() {
  uni.navigateBack()
}

onMounted(() => {
  initLocalData()
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- 头部导航 -->
    <wd-navbar
      :title="t('contextProviderDialog.title')"
      safe-area-inset-top
      left-arrow
      :bordered="false"
      @click-left="goBack"
    >
      <template #left>
        <wd-icon name="arrow-left" size="18" />
      </template>
    </wd-navbar>
    <view class="flex-1 overflow-y-auto px-[20rpx] pt-[20rpx]">
      <view v-if="localProviders.length === 0" class="flex flex-col items-center justify-center gap-[30rpx] py-[100rpx]">
        <text class="text-[28rpx] text-[#9d9ea3]">
          {{ t('contextProviderDialog.noContextApi') }}
        </text>
        <wd-button type="primary" size="small" @click="addProvider(0)">
          {{ t('contextProviderDialog.add') }}
        </wd-button>
      </view>

      <view v-else class="flex flex-col">
        <view v-for="(provider, pIndex) in localProviders" :key="pIndex" class="mb-[30rpx]">
          <view class="flex-1 border border-l-[6rpx] border-[#eee] border-l-[#336cff] rounded-[16rpx] bg-[#fff] p-[20rpx] shadow-[0_4rpx_16rpx_rgba(0,0,0,0.05)]">
            <view class="mb-[30rpx] flex items-center justify-between">
              <view class="flex gap-[16rpx]">
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
            <view class="mb-[40rpx] flex items-center gap-[20rpx]">
              <text class="w-[140rpx] text-[28rpx] text-[#606266] font-semibold">
                {{ t('contextProviderDialog.apiUrl') }}
              </text>
              <wd-input
                v-model="provider.url"
                class="flex-1"
                :placeholder="t('contextProviderDialog.apiUrlPlaceholder')"
              />
            </view>

            <view class="flex items-start gap-[20rpx]">
              <view class="mt-[6rpx] w-[140rpx] text-[28rpx] text-[#606266] font-semibold">
                {{ t('contextProviderDialog.requestHeaders') }}
              </view>
              <view class="flex flex-1 flex-col gap-[20rpx] border border-[#dcdfe6] rounded-[12rpx] border-dashed bg-[#fcfcfc] p-[4rpx]">
                <view
                  v-for="(header, hIndex) in provider.headers"
                  :key="hIndex"
                  class="flex flex-col gap-[16rpx] rounded-[12rpx] bg-[#fff]"
                >
                  <view class="flex items-center gap-[8rpx]">
                    <wd-input
                      v-model="header.key"
                      placeholder="key"
                      class="w-full"
                    />
                  </view>
                  <view class="flex items-center gap-[8rpx]">
                    <wd-input
                      v-model="header.value"
                      placeholder="value"
                      class="w-full"
                    />
                  </view>
                  <view class="flex self-start gap-[12rpx]">
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
                <view v-if="provider.headers.length === 0" class="flex items-center justify-center py-[20rpx] text-[26rpx] text-[#909399]">
                  <text class="mr-[16rpx]">
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

    <view class="flex gap-[20rpx] border-t border-[#eee] px-[30rpx] py-[30rpx]">
      <wd-button type="primary" class="h-[80rpx] flex-1 rounded-[12rpx] text-[28rpx]" @click="handleConfirm">
        {{ t('contextProviderDialog.confirm') }}
      </wd-button>
    </view>
  </view>
</template>

<style scoped lang="scss">
</style>
