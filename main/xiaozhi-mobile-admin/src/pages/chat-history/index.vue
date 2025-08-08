<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "聊天记录"
  }
}
</route>

<script lang="ts" setup>
import type { ChatSession } from '@/api/chat-history/types'
import { computed, onMounted, ref } from 'vue'
import useZPaging from 'z-paging/components/z-paging/js/hooks/useZPaging.js'
import { getChatSessions } from '@/api/chat-history/chat-history'
import { useAgentStore } from '@/store'

defineOptions({
  name: 'ChatHistory',
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

// 聊天会话数据
const sessionList = ref<ChatSession[]>([])
const pagingRef = ref()
useZPaging(pagingRef)

// 智能体管理
const agentStore = useAgentStore()
const showAgentPicker = ref(false)

// 获取当前选中的智能体ID
const currentAgentId = computed(() => {
  return agentStore.currentAgentId
})

// 获取智能体选项
const agentOptions = computed(() => {
  return agentStore.getAgentOptions
})

// 显示智能体选择器
function showAgentSelector() {
  showAgentPicker.value = true
}

// 关闭智能体选择器
function closeAgentSelector() {
  showAgentPicker.value = false
}

// 处理智能体切换
function handleAgentSwitch({ item }: { item: any }) {
  const selectedAgentId = item.value
  if (selectedAgentId !== currentAgentId.value) {
    // 设置当前智能体
    agentStore.setCurrentAgent(selectedAgentId)
    // 刷新会话列表
    pagingRef.value.reload()
  }
  closeAgentSelector()
}

// z-paging查询列表数据
async function queryList(pageNo: number, pageSize: number) {
  try {
    console.log('z-paging获取聊天会话列表')

    // 检查是否有当前选中的智能体
    if (!currentAgentId.value) {
      console.warn('没有选中的智能体')
      pagingRef.value.complete([])
      return
    }

    const response = await getChatSessions(currentAgentId.value, {
      page: pageNo,
      limit: pageSize,
    })

    // 使用z-paging的分页机制
    if (pageNo === 1) {
      pagingRef.value.complete(response.list, response.total)
    }
    else {
      pagingRef.value.addData(response.list)
    }
  }
  catch (error) {
    console.error('获取聊天会话列表失败:', error)
    pagingRef.value.complete(false)
  }
}

// 格式化时间
function formatTime(timeStr: string) {
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

// 进入聊天详情
function goToChatDetail(session: ChatSession) {
  uni.navigateTo({
    url: `/pages/chat-history/detail?sessionId=${session.sessionId}&agentId=${currentAgentId.value}`,
  })
}

onMounted(async () => {
  // 确保智能体列表已加载
  if (!agentStore.isLoaded) {
    await agentStore.loadAgentList()
  }
})
</script>

<template>
  <z-paging
    ref="pagingRef"
    v-model="sessionList"
    :refresher-enabled="true"
    :auto-show-back-to-top="true"
    :loading-more-enabled="true"
    :show-loading-more="true"
    :hide-empty-view="false"
    empty-view-text="暂无聊天记录"
    empty-view-img=""
    :refresher-threshold="80"
    :back-to-top-style="{
      backgroundColor: '#fff',
      borderRadius: '50%',
      width: '56px',
      height: '56px',
    }"
    @query="queryList"
  >
    <!-- 顶部导航栏区域 -->
    <template #top>
      <view class="navbar-section">
        <!-- 状态栏背景 -->
        <view class="status-bar" :style="{ height: `${safeAreaInsets?.top}px` }" />
        <wd-navbar :title="agentStore.currentAgent?.agentName || '聊天记录'">
          <template #right>
            <wd-icon name="filter1" size="18" @click="showAgentSelector" />
          </template>
        </wd-navbar>
      </view>
    </template>

    <!-- 聊天会话列表 -->
    <view class="session-list">
      <view
        v-for="session in sessionList"
        :key="session.sessionId"
        class="session-item"
        @click="goToChatDetail(session)"
      >
        <view class="session-card">
          <view class="session-info">
            <view class="session-header">
              <text class="session-title">
                对话记录 {{ session.sessionId.substring(0, 8) }}...
              </text>
              <text class="session-time">
                {{ formatTime(session.createdAt) }}
              </text>
            </view>
            <view class="session-meta">
              <text class="chat-count">
                共 {{ session.chatCount }} 条对话
              </text>
            </view>
          </view>
          <wd-icon name="arrow-right" custom-class="arrow-icon" />
        </view>
      </view>
    </view>

    <!-- 自定义空状态 -->
    <template #empty>
      <view class="empty-state">
        <wd-icon name="chat" custom-class="empty-icon" />
        <text class="empty-text">
          暂无聊天记录
        </text>
        <text class="empty-desc">
          与智能体的对话记录会显示在这里
        </text>
      </view>
    </template>

    <!-- 智能体选择器 -->
    <wd-action-sheet
      v-model="showAgentPicker"
      :actions="agentOptions"
      title="选择智能体"
      @close="closeAgentSelector"
      @select="handleAgentSwitch"
    />
  </z-paging>
</template>

<style lang="scss" scoped>
// z-paging内容区域样式
:deep(.z-paging-content) {
  background: #f5f7fb;
}

.navbar-section {
  background: #ffffff;
}

.status-bar {
  background: #ffffff;
  width: 100%;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding: 20rpx;
  box-sizing: border-box;
}

.session-item {
  background: #fbfbfb;
  border-radius: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
  border: 1rpx solid #eeeeee;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;

  &:active {
    background: #f8f9fa;
  }
}

.session-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32rpx;

  .session-info {
    flex: 1;

    .session-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12rpx;

      .session-title {
        font-size: 32rpx;
        font-weight: 600;
        color: #232338;
        max-width: 70%;
        word-break: break-all;
      }

      .session-time {
        font-size: 24rpx;
        color: #9d9ea3;
      }
    }

    .session-meta {
      .chat-count {
        font-size: 28rpx;
        color: #65686f;
      }
    }
  }

  :deep(.arrow-icon) {
    font-size: 24rpx;
    color: #c7c7cc;
    margin-left: 16rpx;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 40rpx;
  text-align: center;

  :deep(.empty-icon) {
    font-size: 120rpx;
    color: #d9d9d9;
    margin-bottom: 32rpx;
  }

  .empty-text {
    font-size: 32rpx;
    color: #666666;
    margin-bottom: 16rpx;
    font-weight: 500;
  }

  .empty-desc {
    font-size: 26rpx;
    color: #999999;
    line-height: 1.5;
  }
}
</style>
