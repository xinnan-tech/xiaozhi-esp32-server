<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "声纹管理"
  }
}
</route>

<script lang="ts" setup>
import type { ChatHistory, CreateSpeakerData, VoicePrint } from '@/api/voiceprint'
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'wot-design-uni'
import { useToast } from 'wot-design-uni/components/wd-toast'
import useZPaging from 'z-paging/components/z-paging/js/hooks/useZPaging.js'
import { createVoicePrint, deleteVoicePrint, getChatHistory, getVoicePrintList, updateVoicePrint } from '@/api/voiceprint'
import { useAgentStore } from '@/store'

defineOptions({
  name: 'VoicePrintManage',
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

const message = useMessage()
const toast = useToast()

// 页面数据
const voicePrintList = ref<VoicePrint[]>([])
const chatHistoryList = ref<ChatHistory[]>([])
const chatHistoryActions = ref<any[]>([])
const swipeStates = ref<Record<string, 'left' | 'close' | 'right'>>({})
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
    // 刷新声纹列表
    pagingRef.value.reload()
  }
  closeAgentSelector()
}

// 弹窗相关
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showChatHistoryDialog = ref(false)
const addForm = ref<CreateSpeakerData>({
  agentId: '',
  audioId: '',
  sourceName: '',
  introduce: '',
})
const editForm = ref<VoicePrint>({
  id: '',
  audioId: '',
  sourceName: '',
  introduce: '',
  createDate: '',
})

// z-paging查询列表数据
async function queryList(pageNo: number, pageSize: number) {
  try {
    console.log('z-paging获取声纹列表')

    // 检查是否有当前选中的智能体
    if (!currentAgentId.value) {
      console.warn('没有选中的智能体')
      pagingRef.value.complete([])
      return
    }

    const data = await getVoicePrintList(currentAgentId.value)

    // 初始化滑动状态
    const list = data || []
    list.forEach((item) => {
      if (!swipeStates.value[item.id]) {
        swipeStates.value[item.id] = 'close'
      }
    })

    // 直接返回全部数据，不需要分页处理
    pagingRef.value.complete(list)
  }
  catch (error) {
    console.error('获取声纹列表失败:', error)
    // 告知z-paging数据加载失败
    pagingRef.value.complete(false)
  }
}

// 获取声纹列表(兼容旧代码)
async function loadVoicePrintList() {
  pagingRef.value?.reload()
}

// 获取语音对话记录
async function loadChatHistory() {
  try {
    if (!currentAgentId.value) {
      toast.error('请先选择智能体')
      return
    }

    const data = await getChatHistory(currentAgentId.value)
    chatHistoryList.value = data || []
    // 转换为ActionSheet格式
    chatHistoryActions.value = chatHistoryList.value.map((item, index) => ({
      name: item.content,
      audioId: item.audioId,
      index,
    }))
    showChatHistoryDialog.value = true
  }
  catch (error) {
    console.error('获取对话记录失败:', error)
    toast.error('获取对话记录失败')
  }
}

// 打开添加弹窗
function openAddDialog() {
  if (!currentAgentId.value) {
    toast.error('请先选择智能体')
    return
  }

  addForm.value = {
    agentId: currentAgentId.value,
    audioId: '',
    sourceName: '',
    introduce: '',
  }
  showAddDialog.value = true
}

// 打开编辑弹窗
function openEditDialog(item: VoicePrint) {
  editForm.value = { ...item }
  showEditDialog.value = true
}

// 获取选中音频的显示内容
function getSelectedAudioContent(audioId: string) {
  if (!audioId)
    return '点击选择声纹向量'
  const chatItem = chatHistoryList.value.find(item => item.audioId === audioId)
  return chatItem ? chatItem.content : `已选择: ${audioId.substring(0, 8)}...`
}

// 选择声纹向量
function selectAudioId({ item }: { item: any }) {
  if (showAddDialog.value) {
    addForm.value.audioId = item.audioId
  }
  else if (showEditDialog.value) {
    editForm.value.audioId = item.audioId
  }
  showChatHistoryDialog.value = false
}

// 提交添加说话人
async function submitAdd() {
  if (!addForm.value.sourceName.trim()) {
    toast.error('请输入姓名')
    return
  }
  if (!addForm.value.audioId) {
    toast.error('请选择声纹向量')
    return
  }

  try {
    await createVoicePrint(addForm.value)
    toast.success('添加成功')
    showAddDialog.value = false
    pagingRef.value.reload()
  }
  catch (error) {
    console.error('添加说话人失败:', error)
    toast.error('添加说话人失败')
  }
}

// 提交编辑说话人
async function submitEdit() {
  if (!editForm.value.sourceName.trim()) {
    toast.error('请输入姓名')
    return
  }
  if (!editForm.value.audioId) {
    toast.error('请选择声纹向量')
    return
  }

  try {
    await updateVoicePrint({
      id: editForm.value.id,
      audioId: editForm.value.audioId,
      sourceName: editForm.value.sourceName,
      introduce: editForm.value.introduce,
      createDate: editForm.value.createDate,
    })
    toast.success('编辑成功')
    showEditDialog.value = false
    pagingRef.value.reload()
  }
  catch (error) {
    console.error('编辑说话人失败:', error)
    toast.error('编辑说话人失败')
  }
}

// 处理编辑操作
function handleEdit(item: VoicePrint) {
  openEditDialog(item)
  swipeStates.value[item.id] = 'close'
}

// 删除声纹
async function handleDelete(id: string) {
  message.confirm({
    msg: '确定要删除这个说话人吗？',
    title: '确认删除',
  }).then(async () => {
    await deleteVoicePrint(id)
    toast.success('删除成功')
    pagingRef.value.reload()
  }).catch(() => {
    console.log('点击了取消按钮')
  })
}

onMounted(async () => {
  // 确保智能体列表已加载
  if (!agentStore.isLoaded) {
    await agentStore.loadAgentList()
  }
})

onShow(() => {
  if (pagingRef.value) {
    pagingRef.value.reload()
  }
})
</script>

<template>
  <z-paging
    ref="pagingRef" v-model="voicePrintList" :refresher-enabled="true" :auto-show-back-to-top="true"
    :loading-more-enabled="false" :show-loading-more="false" :hide-empty-view="false" empty-view-text="暂无声纹数据"
    empty-view-img="" :refresher-threshold="80" :back-to-top-style="{
      backgroundColor: '#fff',
      borderRadius: '50%',
      width: '56px',
      height: '56px',
    }" @query="queryList"
  >
    <!-- 顶部导航栏区域 -->
    <template #top>
      <view class="bg-white">
        <!-- 状态栏背景 -->
        <wd-navbar :title="agentStore.currentAgent?.agentName || '声纹管理'" safe-area-inset-top>
          <template #right>
            <wd-icon name="filter1" size="18" @click="showAgentSelector" />
          </template>
        </wd-navbar>
      </view>
    </template>

    <!-- 声纹卡片列表 -->
    <view class="box-border flex flex-col gap-[24rpx] p-[20rpx]">
      <view v-for="item in voicePrintList" :key="item.id">
        <wd-swipe-action
          :model-value="swipeStates[item.id] || 'close'"
          @update:model-value="swipeStates[item.id] = $event"
        >
          <view class="bg-[#fbfbfb] p-[32rpx]" @click="handleEdit(item)">
            <view>
              <text class="mb-[12rpx] block text-[32rpx] text-[#232338] font-semibold">
                {{ item.sourceName }}
              </text>
              <text class="mb-[12rpx] block text-[28rpx] text-[#65686f] leading-[1.4]">
                {{ item.introduce || '暂无描述' }}
              </text>
              <text class="block text-[24rpx] text-[#9d9ea3]">
                {{ item.createDate }}
              </text>
            </view>
          </view>

          <template #right>
            <view class="h-full flex">
              <view
                class="h-full min-w-[120rpx] flex items-center justify-center bg-[#ff4d4f] p-x-[32rpx] text-[28rpx] text-white font-medium"
                @click="handleDelete(item.id)"
              >
                <wd-icon name="delete" />
                删除
              </view>
            </view>
          </template>
        </wd-swipe-action>
      </view>
    </view>

    <!-- 自定义空状态 -->
    <template #empty>
      <view class="flex flex-col items-center justify-center p-[100rpx_40rpx] text-center">
        <wd-icon name="voice" custom-class="text-[120rpx] text-[#d9d9d9] mb-[32rpx]" />
        <text class="mb-[16rpx] text-[32rpx] text-[#666666] font-medium">
          暂无声纹数据
        </text>
        <text class="text-[26rpx] text-[#999999] leading-[1.5]">
          点击右下角 + 号添加您的第一个说话人
        </text>
      </view>
    </template>

    <!-- 浮动操作按钮 -->
    <wd-fab type="primary" size="small" :draggable="true" :expandable="false" @click="openAddDialog">
      <wd-icon name="add" />
    </wd-fab>
  </z-paging>

  <!-- 添加说话人弹窗 -->
  <wd-popup
    v-model="showAddDialog" position="center" custom-style="width: 90%; max-width: 400px; border-radius: 16px;"
    safe-area-inset-bottom
  >
    <view>
      <view class="w-full flex items-center justify-between border-b-[2rpx] border-[#eeeeee] p-[32rpx_32rpx_24rpx]">
        <text class="w-full text-center text-[32rpx] text-[#232338] font-semibold">
          添加说话人
        </text>
      </view>

      <view class="p-[32rpx]">
        <!-- 声纹向量选择 -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * 声纹向量
          </text>
          <view
            class="flex cursor-pointer items-center justify-between border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]"
            @click="loadChatHistory"
          >
            <text
              class="m-r-[16rpx] flex-1 text-left text-[26rpx] text-[#232338]"
              :class="{ 'text-[#9d9ea3]': !addForm.audioId }"
            >
              {{ getSelectedAudioContent(addForm.audioId) }}
            </text>
            <wd-icon name="arrow-down" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>
        </view>

        <!-- 姓名 -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * 姓名
          </text>
          <input
            v-model="addForm.sourceName"
            class="box-border h-[80rpx] w-full border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text" placeholder="请输入姓名"
          >
        </view>

        <!-- 描述 -->
        <view>
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * 描述
          </text>
          <textarea
            v-model="addForm.introduce" :maxlength="100" placeholder="请输入描述"
            class="box-border h-[200rpx] w-full resize-none border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
            {{ (addForm.introduce || '').length }}/100
          </view>
        </view>
      </view>

      <view class="flex gap-[16rpx] border-t-[2rpx] border-[#eeeeee] p-[24rpx_32rpx_32rpx]">
        <wd-button type="info" custom-class="flex-1" @click="showAddDialog = false">
          取消
        </wd-button>
        <wd-button type="primary" custom-class="flex-1" @click="submitAdd">
          保存
        </wd-button>
      </view>
    </view>
  </wd-popup>

  <!-- 编辑说话人弹窗 -->
  <wd-popup
    v-model="showEditDialog" position="center" custom-style="width: 90%; max-width: 400px; border-radius: 16px;"
    safe-area-inset-bottom
  >
    <view>
      <view class="w-full flex items-center justify-between border-b-[2rpx] border-[#eeeeee] p-[32rpx_32rpx_24rpx]">
        <text class="w-full text-center text-[32rpx] text-[#232338] font-semibold">
          编辑说话人
        </text>
      </view>

      <view class="p-[32rpx]">
        <!-- 声纹向量选择 -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * 声纹向量
          </text>
          <view
            class="flex cursor-pointer items-center justify-between border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]"
            @click="loadChatHistory"
          >
            <text
              class="m-r-[16rpx] flex-1 text-left text-[26rpx] text-[#232338]"
              :class="{ 'text-[#9d9ea3]': !editForm.audioId }"
            >
              {{ getSelectedAudioContent(editForm.audioId) }}
            </text>
            <wd-icon name="arrow-down" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>
        </view>

        <!-- 姓名 -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * 姓名
          </text>
          <input
            v-model="editForm.sourceName"
            class="box-border h-[80rpx] w-full border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text" placeholder="请输入姓名"
          >
        </view>

        <!-- 描述 -->
        <view>
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * 描述
          </text>
          <textarea
            v-model="editForm.introduce" :maxlength="100" placeholder="请输入描述"
            class="box-border h-[200rpx] w-full resize-none border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
            {{ (editForm.introduce || '').length }}/100
          </view>
        </view>
      </view>

      <view class="flex gap-[16rpx] border-t-[2rpx] border-[#eeeeee] p-[24rpx_32rpx_32rpx]">
        <wd-button type="info" custom-class="flex-1" @click="showEditDialog = false">
          取消
        </wd-button>
        <wd-button type="primary" custom-class="flex-1" @click="submitEdit">
          保存
        </wd-button>
      </view>
    </view>
  </wd-popup>

  <!-- 语音对话记录选择动作面板 -->
  <wd-action-sheet
    v-model="showChatHistoryDialog" :actions="chatHistoryActions" title="选择声纹向量"
    @select="selectAudioId"
  />

  <!-- 智能体选择器 -->
  <wd-action-sheet
    v-model="showAgentPicker" :actions="agentOptions" title="选择智能体" @close="closeAgentSelector"
    @select="handleAgentSwitch"
  />
</template>

<style>
:deep(.z-paging-content) {
  background: #f5f7fb;
}

:deep(.wd-swipe-action) {
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
  border: 1rpx solid #eeeeee;
}

:deep(.flex-1) {
  flex: 1;
}
</style>
