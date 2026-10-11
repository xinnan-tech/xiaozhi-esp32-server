<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationBarTitleText": "Agent",
    "navigationStyle": "custom"
  }
}
</route>

<script lang="ts" setup>
import { onLoad } from '@dcloudio/uni-app'
import { onMounted, ref } from 'vue'
import CustomTabs from '@/components/custom-tabs/index.vue'
import ChatHistory from '@/pages/chat-history/index.vue'
import DeviceManagement from '@/pages/device/index.vue'
import VoiceprintManagement from '@/pages/voiceprint/index.vue'
import AgentEdit from './edit.vue'

defineOptions({
  name: 'AgentIndex',
})

// Get distance from screen boundary to safe area
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


// Agent ID
const currentAgentId = ref('default')

// Current tab
const currentTab = ref('agent-config')

// Refresh and loading status
const refreshing = ref(false)

// Calculate whether to enable pull-to-refresh (not enabled on role edit page)
const refresherEnabled = computed(() => {
  return currentTab.value !== 'agent-config'
})

// Child component reference
const deviceRef = ref()
const chatRef = ref()
const voiceprintRef = ref()

// Tab configuration
const tabList = [
  {
    label: 'Role Configuration',
    value: 'agent-config',
    icon: '/static/tabbar/robot.png',
    activeIcon: '/static/tabbar/robot_activate.png',
  },
  {
    label: 'Device Management',
    value: 'device-management',
    icon: '/static/tabbar/device.png',
    activeIcon: '/static/tabbar/device_activate.png',
  },
  {
    label: 'Chat History',
    value: 'chat-history',
    icon: '/static/tabbar/chat.png',
    activeIcon: '/static/tabbar/chat_activate.png',
  },
  {
    label: 'Voiceprint Management',
    value: 'voiceprint-management',
    icon: '/static/tabbar/microphone.png',
    activeIcon: '/static/tabbar/microphone_activate.png',
  },
]

// Return to previous page
function goBack() {
  uni.navigateBack()
}

// Handle tab switching
function handleTabChange(item: any) {
  console.log('Tab changed:', item)
}

// Pull to refresh
async function onRefresh() {
  // Agent edit page does not need refresh
  if (currentTab.value === 'agent-config') {
    return
  }

  refreshing.value = true

  try {
    switch (currentTab.value) {
      case 'device-management':
        if (deviceRef.value?.refresh) {
          await deviceRef.value.refresh()
        }
        break
      case 'chat-history':
        if (chatRef.value?.refresh) {
          await chatRef.value.refresh()
        }
        break
      case 'voiceprint-management':
        if (voiceprintRef.value?.refresh) {
          await voiceprintRef.value.refresh()
        }
        break
    }
  }
  catch (error) {
    console.error('Refresh failed:', error)
  }
  finally {
    refreshing.value = false
  }
}

// Load more on reach bottom
async function onLoadMore() {
  // Only chat history needs to load more
  if (currentTab.value === 'chat-history' && chatRef.value?.loadMore) {
    await chatRef.value.loadMore()
  }
}

// Receive page parameters
onLoad((options) => {
  if (options?.agentId) {
    currentAgentId.value = options.agentId
    console.log('Received agent ID:', options.agentId)
  }
})

onMounted(async () => {
  // Page initialization
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- Navigation Bar -->
    <wd-navbar title="Agent" safe-area-inset-top>
      <template #left>
        <wd-icon name="arrow-left" size="18" @click="goBack" />
      </template>
    </wd-navbar>

    <!-- Custom Tabs -->
    <CustomTabs
      v-model="currentTab"
      :tab-list="tabList"
      @change="handleTabChange"
    />

    <!-- Main content scroll area -->
    <scroll-view
      scroll-y
      :style="{ height: `calc(100vh - ${safeAreaInsets?.top || 0}px - 180rpx)` }"
      class="box-border flex-1 bg-[#f5f7fb]"
      enable-back-to-top
      :refresher-enabled="refresherEnabled"
      :refresher-triggered="refreshing"
      @refresherrefresh="onRefresh"
      @scrolltolower="onLoadMore"
    >
      <!-- Tab content -->
      <view class="flex-1">
        <AgentEdit
          v-if="currentTab === 'agent-config'"
          :agent-id="currentAgentId"
        />
        <DeviceManagement
          v-else-if="currentTab === 'device-management'"
          ref="deviceRef"
          :agent-id="currentAgentId"
        />
        <ChatHistory
          v-else-if="currentTab === 'chat-history'"
          ref="chatRef"
          :agent-id="currentAgentId"
        />
        <VoiceprintManagement
          v-else-if="currentTab === 'voiceprint-management'"
          ref="voiceprintRef"
          :agent-id="currentAgentId"
        />
      </view>
    </scroll-view>
  </view>
</template>

<style scoped>
</style>
