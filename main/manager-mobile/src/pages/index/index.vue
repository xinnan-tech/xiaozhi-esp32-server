<!-- 使用 type="home" 属性设置首页，其他页面不需要设置，默认为page -->
<route lang="jsonc" type="home">
{
  "layout": "tabbar",
  "style": {
    // 'custom' 表示开启自定义导航栏，默认 'default'
    "navigationStyle": "custom",
    "navigationBarTitleText": "首页"
  }
}
</route>

<script lang="ts" setup>
import type { Agent } from '@/api/agent/types'
import { ref } from 'vue'
import { useMessage } from 'wot-design-uni'
import useZPaging from 'z-paging/components/z-paging/js/hooks/useZPaging.js'
import { createAgent, deleteAgent, getAgentList } from '@/api/agent/agent'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'Home',
})

// 获取屏幕边界到安全区域距离
let safeAreaInsets: any
let systemInfo: any

// #ifdef MP-WEIXIN
// 微信小程序使用新的API
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
// 其他平台继续使用uni API
systemInfo = uni.getSystemInfoSync()
safeAreaInsets = systemInfo.safeAreaInsets
// #endif

// Agent data
const agentList = ref<Agent[]>([])
const pagingRef = ref()
useZPaging(pagingRef)
// 消息组件
const message = useMessage()

// z-paging查询列表数据
async function queryList(pageNo: number, pageSize: number) {
  try {
    console.log('z-paging get agent list')

    const response = await getAgentList()

    // 更新本地列表
    agentList.value = response

    // 直接返回全部数据，不需要分页处理
    pagingRef.value.complete(response)
  }
  catch (error) {
    console.error('Failed to get agent list:', error)
    // 告知z-paging数据加载失败
    pagingRef.value.complete(false)
  }
}

// Create agent
async function handleCreateAgent(agentName: string) {
  try {
    await createAgent({ agentName: agentName.trim() })
    // 创建成功后刷新列表
    pagingRef.value.reload()
    toast.success(`Agent "${agentName}" created successfully!`)
  }
  catch (error: any) {
    console.error('Failed to create agent:', error)
    const errorMessage = error?.message || 'Creation failed, please try again'
    toast.error(errorMessage)
  }
}

// Delete agent
async function handleDeleteAgent(agent: Agent) {
  try {
    await deleteAgent(agent.id)
    // 删除成功后刷新列表
    pagingRef.value.reload()
    toast.success(`Agent "${agent.agentName}" has been deleted`)
  }
  catch (error: any) {
    console.error('Failed to delete agent:', error)
    const errorMessage = error?.message || 'Deletion failed, please try again'
    toast.error(errorMessage)
  }
}

// 进入编辑页面
function goToEditAgent(agent: Agent) {
  // Pass agent ID to edit page
  uni.navigateTo({
    url: `/pages/agent/index?agentId=${agent.id}`,
  })
}

// 点击卡片进入编辑
function handleCardClick(agent: Agent) {
  goToEditAgent(agent)
}

// 打开创建对话框
function openCreateDialog() {
  message
    .prompt({
      title: 'Create Agent',
      msg: '',
      inputPlaceholder: 'e.g., Customer Service Assistant, Voice Assistant, Q&A Bot',
      inputValue: '',
      inputPattern: /^[\u4E00-\u9FA5a-z0-9\s]{1,50}$/i,
      confirmButtonText: 'Create Now',
      cancelButtonText: 'Cancel',
    })
    .then(async (result: any) => {
      if (result.value && String(result.value).trim()) {
        await handleCreateAgent(String(result.value).trim())
      }
    })
    .catch(() => {
      // 用户取消操作
    })
}

// 格式化时间
function formatTime(timeStr: string) {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000)
    return 'Just now'
  if (diff < 3600000)
    return `${Math.floor(diff / 60000)} minutes ago`
  if (diff < 86400000)
    return `${Math.floor(diff / 3600000)} hours ago`
  return `${Math.floor(diff / 86400000)} days ago`
}

// 页面显示时刷新列表
onShow(() => {
  console.log('Home onShow, refreshing agent list')
  if (pagingRef.value) {
    pagingRef.value.reload()
  }
})
</script>

<template>
  <z-paging
    ref="pagingRef" v-model="agentList" :refresher-enabled="true" :auto-show-back-to-top="true"
    :loading-more-enabled="false" :show-loading-more="false" :hide-empty-view="false" empty-view-text="No agents yet"
    empty-view-img="" :refresher-threshold="80" :back-to-top-style="{
      backgroundColor: '#fff',
      borderRadius: '50%',
      width: '56px',
      height: '56px',
    }" @query="queryList"
  >
    <!-- 固定在顶部的横幅区域 -->
    <template #top>
      <view class="banner-section" :style="{ paddingTop: `${safeAreaInsets?.top + 100}rpx` }">
        <view class="banner-content">
          <view class="welcome-info">
            <text class="greeting">
              Hello, Smart Manager
            </text>
            <text class="subtitle">
              Let's have a <text class="highlight">
                wonderful day!
              </text>
            </text>
            <text class="english-subtitle">
              Hello, Let's have a wonderful day!
            </text>
          </view>
          <view class="wave-decoration">
            <!-- 添加波浪装饰 -->
            <view class="wave" />
            <view class="wave wave-2" />
          </view>
        </view>
      </view>

      <!-- 内容区域开始标识 -->
      <view class="content-section-header" />
    </template>

    <!-- Agent card list -->
    <view class="agent-list">
      <view v-for="agent in agentList" :key="agent.id" class="agent-item">
        <wd-swipe-action>
          <view class="simple-card" @click="handleCardClick(agent)">
            <view class="card-content">
              <view class="card-main">
                <view class="agent-title">
                  <text class="agent-name">
                    {{ agent.agentName }}
                  </text>
                </view>

                <view class="model-info">
                  <text class="model-text">
                    Language Model: {{ agent.llmModelName }}
                  </text>
                  <text class="model-text">
                    Voice Model: {{ agent.ttsModelName }} ({{ agent.ttsVoiceName }})
                  </text>
                </view>

                <view class="stats-row">
                  <view class="stat-chip">
                    <wd-icon name="phone" custom-class="chip-icon" />
                    <text class="chip-text">
                      Device Management({{ agent.deviceCount }})
                    </text>
                  </view>
                  <view v-if="agent.lastConnectedAt" class="stat-chip">
                    <wd-icon name="time" custom-class="chip-icon" />
                    <text class="chip-text">
                      Last conversation: {{ formatTime(agent.lastConnectedAt) }}
                    </text>
                  </view>
                </view>
              </view>

              <wd-icon name="arrow-right" custom-class="arrow-icon" />
            </view>
          </view>

          <template #right>
            <view class="swipe-actions">
              <view class="action-btn delete-btn" @click.stop="handleDeleteAgent(agent)">
                <wd-icon name="delete" />
                <text>Delete</text>
              </view>
            </view>
          </template>
        </wd-swipe-action>
      </view>
    </view>

    <!-- 自定义空状态 -->
    <template #empty>
      <view class="empty-state">
        <wd-icon name="robot" custom-class="empty-icon" />
        <text class="empty-text">
          No agents yet
        </text>
        <text class="empty-desc">
          Click the + button at bottom right to create your first agent
        </text>
      </view>
    </template>

    <!-- FAB 新增按钮 -->
    <wd-fab type="primary" icon="add" :draggable="true" :expandable="false" @click="openCreateDialog" />

    <!-- MessageBox 组件 -->
    <wd-message-box />
  </z-paging>
</template>

<style lang="scss" scoped>
.banner-section {
  background: linear-gradient(145deg, #9ebbfc, #6baaff, #9ebbfc, #f5f8fd);
  position: relative;
  padding: 40rpx 40rpx 80rpx 40rpx;
  overflow: hidden;

  .banner-content {
    position: relative;
    z-index: 2;
  }

  .header-actions {
    position: absolute;
    top: -50rpx;
    right: 0;
    display: flex;
    gap: 32rpx;

    .filter-icon,
    .setting-icon {
      color: white;
      cursor: pointer;
      transition: opacity 0.2s ease;

      &:active {
        opacity: 0.7;
      }
    }
  }

  .welcome-info {
    .greeting {
      display: block;
      font-size: 48rpx;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 16rpx;
      text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.1);
    }

    .subtitle {
      display: block;
      font-size: 32rpx;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 12rpx;
      font-weight: 500;

      .highlight {
        color: #ffd700;
        font-weight: 600;
      }
    }

    .english-subtitle {
      display: block;
      font-size: 24rpx;
      color: rgba(255, 255, 255, 0.7);
      font-style: italic;
    }
  }

  .wave-decoration {
    position: absolute;
    top: 0;
    right: -100rpx;
    width: 400rpx;
    height: 100%;
    opacity: 0.1;
    pointer-events: none;

    .wave {
      position: absolute;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
      border-radius: 50%;
      animation: float 6s ease-in-out infinite;

      &.wave-2 {
        top: 20%;
        right: 20%;
        animation-delay: -3s;
        opacity: 0.5;
      }
    }
  }
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }

  50% {
    transform: translateY(-30rpx) rotate(180deg);
  }
}

// 内容区域开始标识，创建白色背景过渡
.content-section-header {
  background: #ffffff;
  border-radius: 32rpx 32rpx 0 0;
  margin-top: -32rpx;
  height: 32rpx;
  position: relative;
  z-index: 1;
}

// z-paging内容区域样式
:deep(.z-paging-content) {
  background: #ffffff;
  padding: 0 0 40rpx 0;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  padding: 0 20rpx;
}

.agent-item {
  :deep(.wd-swipe-action) {
    border-radius: 16rpx;
    overflow: hidden;
    box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
    border: 1rpx solid #f0f0f0;
  }
}

.simple-card {
  background: #ffffff;
  padding: 24rpx;
  cursor: pointer;
  transition: all 0.2s ease;

  &:active {
    background: #f8f9fa;
  }

  .card-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-main {
    flex: 1;
  }

  .agent-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12rpx;

    .agent-name {
      font-size: 32rpx;
      font-weight: 600;
      color: #1a1a1a;
    }
  }

  .model-info {
    margin-bottom: 16rpx;

    .model-text {
      display: block;
      font-size: 24rpx;
      color: #666666;
      line-height: 1.5;
      margin-bottom: 4rpx;

      &:last-child {
        margin-bottom: 0;
      }
    }
  }

  .stats-row {
    display: flex;
    gap: 12rpx;
    flex-wrap: wrap;

    .stat-chip {
      display: flex;
      align-items: center;
      padding: 6rpx 12rpx;
      background: #f8f9fa;
      border-radius: 20rpx;
      border: 1rpx solid #eaeaea;

      :deep(.chip-icon) {
        font-size: 20rpx;
        color: #666666;
        margin-right: 6rpx;
      }

      .chip-text {
        font-size: 22rpx;
        color: #666666;
      }
    }
  }

  :deep(.arrow-icon) {
    font-size: 24rpx;
    color: #c7c7cc;
    margin-left: 16rpx;
  }
}

.swipe-actions {
  display: flex;
  height: 100%;

  .action-btn {
    width: 120rpx;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8rpx;
    color: #ffffff;
    font-size: 24rpx;
    font-weight: 500;
    transition: all 0.3s ease;

    &.edit-btn {
      background: #1890ff;

      &:active {
        background: #096dd9;
      }
    }

    &.delete-btn {
      background: #ff4d4f;

      &:active {
        background: #d9363e;
      }
    }

    :deep(.wd-icon) {
      font-size: 32rpx;
    }
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

@keyframes pulse {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }

  100% {
    opacity: 1;
  }
}

.filter-actions {
  padding: 32rpx;
  text-align: center;
  border-top: 1rpx solid #eeeeee;
}
</style>
