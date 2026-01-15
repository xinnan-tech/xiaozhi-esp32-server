<template>
  <div>
    <!-- 桌面端布局 -->
    <div v-if="showComponent" class="hidden lg:flex items-center space-x-4" :class="$store.state.deviceStatus.isOnline ? '' : 'opacity-60'">
      <!-- 设备状态指示器 -->
      <div class="flex items-center space-x-2">
        <!-- 在线状态图标 -->
        <div class="flex items-center space-x-1">
          <div
            :class="[
              'w-2 h-2 rounded-full',
              $store.state.deviceStatus.isOnline ? 'bg-green-500' : 'bg-gray-400'
            ]"
          ></div>
          <span :class="[
            'text-sm font-medium',
            $store.state.deviceStatus.isOnline ? 'text-gray-700' : 'text-gray-500'
          ]">
            {{ $store.state.deviceStatus.isOnline ? $t('device.online') : $t('device.offline') }}
          </span>
        </div>

        <!-- 网络状态 -->
        <div v-if="$store.state.deviceStatus.isOnline && $store.state.deviceInfo.network" class="flex items-center space-x-1">
          <!-- Wi-Fi图标 -->
          <WifiIcon v-if="$store.state.deviceInfo.network.type === 'wifi'" color="text-blue-500" />
          <!-- 4G信号图标 -->
          <Signal4GIcon v-else-if="$store.state.deviceInfo.network.type === '4g'" />
          <span class="text-xs text-gray-500">{{ getSignalDisplayText($store.state.deviceInfo.network.signal, $t) }}</span>
        </div>
      </div>

      <!-- 设备详细信息 -->
      <div v-if="$store.state.deviceStatus.isOnline" class="flex items-center space-x-4 text-sm text-gray-600">
        <!-- 芯片信息 -->
        <div v-if="$store.state.deviceInfo.chip" class="flex items-center space-x-1">
          <ChipIcon />
          <span>{{ $store.state.deviceInfo.chip.model }}</span>
        </div>

        <!-- Flash大小 -->
        <div v-if="$store.state.deviceInfo.flash" class="flex items-center space-x-1">
          <FlashIcon />
          <span>{{ $store.state.deviceInfo.flash.size }}</span>
        </div>

        <!-- 开发板信息 -->
        <div v-if="$store.state.deviceInfo.board" class="flex items-center space-x-1">
          <BoardIcon />
          <span>{{ $store.state.deviceInfo.board.model }}</span>
        </div>

        <!-- 屏幕分辨率 -->
        <div v-if="$store.state.deviceInfo.screen" class="flex items-center space-x-1">
          <ScreenIcon />
          <span>{{ $store.state.deviceInfo.screen.resolution }}</span>
        </div>
      </div>

    </div>

    <!-- 移动端布局 -->
    <div v-if="showComponent" class="lg:hidden flex flex-col bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <!-- 头部状态栏 -->
      <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div class="flex items-center space-x-2">
          <div
            :class="[
              'w-2.5 h-2.5 rounded-full',
              $store.state.deviceStatus.isOnline ? 'bg-green-500' : 'bg-red-400'
            ]"
          ></div>
          <span :class="[
            'text-sm font-medium',
            $store.state.deviceStatus.isOnline ? 'text-gray-800' : 'text-gray-600'
          ]">
            {{ $store.state.deviceStatus.isOnline ? $t('device.online') : $t('device.offline') }}
          </span>
        </div>

        <!-- 网络状态 -->
        <div v-if="$store.state.deviceStatus.isOnline && $store.state.deviceInfo.network" class="flex items-center space-x-1">
          <WifiIcon v-if="$store.state.deviceInfo.network.type === 'wifi'" color="text-blue-500" />
          <Signal4GIcon v-else-if="$store.state.deviceInfo.network.type === '4g'" />
          <span class="text-xs font-medium text-gray-600">{{ getSignalDisplayText($store.state.deviceInfo.network.signal, $t) }}</span>
        </div>
      </div>

      <!-- 设备信息区域 -->
      <div v-if="$store.state.deviceStatus.isOnline" class="px-4 py-3">
        <div class="grid grid-cols-1 gap-2.5">
          <!-- 第一行：芯片和开发板 -->
          <div class="flex justify-between items-center py-1.5 border-b border-gray-100">
            <div v-if="$store.state.deviceInfo.chip" class="flex items-center space-x-2 flex-1">
              <ChipIcon class="flex-shrink-0" />
              <div class="min-w-0 flex-1">
                <div class="text-xs text-gray-500 leading-tight">{{ $t('device.chip') }}</div>
                <div class="text-sm text-gray-800 font-medium truncate">{{ $store.state.deviceInfo.chip.model }}</div>
              </div>
            </div>

            <div v-if="$store.state.deviceInfo.board" class="flex items-center space-x-2 flex-1 ml-3">
              <BoardIcon class="flex-shrink-0" />
              <div class="min-w-0 flex-1">
                <div class="text-xs text-gray-500 leading-tight">{{ $t('device.board') }}</div>
                <div class="text-sm text-gray-800 font-medium truncate">{{ $store.state.deviceInfo.board.model }}</div>
              </div>
            </div>
          </div>

          <!-- 第二行：Flash和屏幕 -->
          <div class="flex justify-between items-center py-1.5">
            <div v-if="$store.state.deviceInfo.flash" class="flex items-center space-x-2 flex-1">
              <FlashIcon class="flex-shrink-0" />
              <div class="min-w-0 flex-1">
                <div class="text-xs text-gray-500 leading-tight">{{ $t('device.flash') }}</div>
                <div class="text-sm text-gray-800 font-medium">{{ $store.state.deviceInfo.flash.size }}</div>
              </div>
            </div>

            <div v-if="$store.state.deviceInfo.screen" class="flex items-center space-x-2 flex-1 ml-3">
              <ScreenIcon class="flex-shrink-0" />
              <div class="min-w-0 flex-1">
                <div class="text-xs text-gray-500 leading-tight">{{ $t('device.screen') }}</div>
                <div class="text-sm text-gray-800 font-medium">{{ $store.state.deviceInfo.screen.resolution }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { WifiIcon, Signal4GIcon, ChipIcon, FlashIcon, BoardIcon, ScreenIcon } from '@/components/icons'

const getSignalDisplayText = (signal, t) => {
  if (!signal) return t('device.signal.unknown')

  switch (signal.toLowerCase()) {
    case 'strong':
      return t('device.signal.strong')
    case 'medium':
      return t('device.signal.medium')
    case 'weak':
      return t('device.signal.weak')
    case 'none':
      return t('device.signal.none')
    default:
      return signal
  }
}

</script>

<script>
  export default {
    name: 'DeviceStatus',
    data() {
      return {

      }
    },
    computed: {
      // 根据是否有token决定是否显示组件
      showComponent() {
        return this.hasToken
      }
    },
    // 初始化组件
    mounted() {
      this.$store.dispatch('deviceStatus/initializeDeviceStatus');
    },
    // 清理资源
    destroyed() {
      this.$store.dispatch('deviceStatus/cleanupDeviceStatus');

    }
  }
</script>
