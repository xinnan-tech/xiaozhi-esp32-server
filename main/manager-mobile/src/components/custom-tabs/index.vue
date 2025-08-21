<script setup lang="ts">
interface TabItem {
  label: string
  value: string | number
  icon: string
  activeIcon: string
}

interface Props {
  tabList: TabItem[]
  modelValue?: string | number
}

interface Emits {
  (e: 'update:modelValue', value: string | number): void
  (e: 'change', item: TabItem, index: number): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
})

const emit = defineEmits<Emits>()

const activeValue = computed(() => {
  return props.modelValue || (props.tabList[0]?.value ?? '')
})

function handleTabClick(item: TabItem, index: number) {
  emit('update:modelValue', item.value)
  emit('change', item, index)
}
</script>

<template>
  <view class="custom-tabs">
    <view
      v-for="(item, index) in tabList"
      :key="item.value"
      class="tab-item"
      :class="{ active: activeValue === item.value }"
      @click="handleTabClick(item, index)"
    >
      <view class="tab-icon">
        <image
          :src="activeValue === item.value ? item.activeIcon : item.icon"
          class="icon-img"
          mode="aspectFit"
        />
      </view>
      <view class="tab-text">
        {{ item.label }}
      </view>
      <view v-if="activeValue === item.value" class="tab-indicator" />
    </view>
  </view>
</template>

<style scoped>
.custom-tabs {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background-color: #ffffff;
  padding: 0 16rpx;
  border-top: 1rpx solid #eeeeee;
  box-sizing: border-box;
}

.tab-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16rpx 12rpx 12rpx;
  flex: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-icon {
  width: 48rpx;
  height: 48rpx;
  margin-bottom: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-img {
  width: 100%;
  height: 100%;
}

.tab-text {
  font-size: 24rpx;
  color: #9d9ea3;
  line-height: 1.2;
  text-align: center;
  transition: color 0.2s ease;
}

.tab-item.active .tab-text {
  color: #336cff;
  font-weight: 500;
}

.tab-indicator {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 48rpx;
  height: 4rpx;
  background-color: #336cff;
  border-radius: 2rpx;
}

/* 适配不同尺寸屏幕 */
@media (max-width: 375px) {
  .tab-text {
    font-size: 22rpx;
  }

  .tab-icon {
    width: 44rpx;
    height: 44rpx;
  }
}
</style>
