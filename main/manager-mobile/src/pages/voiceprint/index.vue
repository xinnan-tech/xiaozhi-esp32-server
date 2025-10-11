<script lang="ts" setup>
import type { ChatHistory, CreateSpeakerData, VoicePrint } from '@/api/voiceprint'
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'wot-design-uni'
import { useToast } from 'wot-design-uni/components/wd-toast'
import { createVoicePrint, deleteVoicePrint, getChatHistory, getVoicePrintList, updateVoicePrint } from '@/api/voiceprint'
import { t } from '@/i18n'

defineOptions({
  name: 'VoicePrintManage',
})

// 接收props
interface Props {
  agentId?: string
}

const props = withDefaults(defineProps<Props>(), {
  agentId: 'default'
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
const loading = ref(false)

// 使用传入的智能体ID
const currentAgentId = computed(() => {
  return props.agentId
})

// 智能体选择相关功能已移除

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

// 获取声纹列表
async function loadVoicePrintList() {
  try {
    console.log('获取声纹列表')

    // 检查是否有当前选中的智能体
    if (!currentAgentId.value) {
      console.warn(t('voiceprint.noSelectedAgent'))
      voicePrintList.value = []
      return
    }

    loading.value = true
    const data = await getVoicePrintList(currentAgentId.value)

    // 初始化滑动状态
    const list = data || []
    list.forEach((item) => {
      if (!swipeStates.value[item.id]) {
        swipeStates.value[item.id] = 'close'
      }
    })

    voicePrintList.value = list
  }
  catch (error) {
    console.error('获取声纹列表失败:', error)
    voicePrintList.value = []
  }
  finally {
    loading.value = false
  }
}

// 暴露给父组件的刷新方法
async function refresh() {
  await loadVoicePrintList()
}

// 获取语音对话记录
async function loadChatHistory() {
  try {
    if (!currentAgentId.value) {
      toast.error(t('voiceprint.pleaseSelectAgent'))
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
    toast.error(t('voiceprint.fetchHistoryFailed'))
  }
}

// 打开添加弹窗
function openAddDialog() {
  if (!currentAgentId.value) {
    toast.error(t('voiceprint.pleaseSelectAgent'))
    return
  }

  // 检查声纹接口是否配置（通过尝试获取声纹列表来检测）
  const checkVoicePrintConfig = async () => {
    try {
      await getVoicePrintList(currentAgentId.value)
      // 接口正常，继续打开添加弹窗
      addForm.value = {
        agentId: currentAgentId.value,
        audioId: '',
        sourceName: '',
        introduce: '',
      }
      showAddDialog.value = true
    } catch (error: any) {
      // 捕捉声纹接口未配置错误
      if (error.message && error.message.includes('请求错误[10054]')) {
        toast.error(t('voiceprint.voiceprintInterfaceNotConfigured'))
      } else {
        // 其他错误，继续打开弹窗
        addForm.value = {
          agentId: currentAgentId.value,
          audioId: '',
          sourceName: '',
          introduce: '',
        }
        showAddDialog.value = true
      }
    }
  }

  checkVoicePrintConfig()
}

// 打开编辑弹窗
function openEditDialog(item: VoicePrint) {
  editForm.value = { ...item }
  showEditDialog.value = true
}

// 获取选中音频的显示内容
function getSelectedAudioContent(audioId: string) {
  if (!audioId)
    return t('voiceprint.clickToSelectVector')
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
    toast.error(t('voiceprint.pleaseInputName'))
    return
  }
  if (!addForm.value.audioId) {
    toast.error(t('voiceprint.pleaseSelectVector'))
    return
  }

  try {
    await createVoicePrint(addForm.value)
    toast.success(t('voiceprint.addSuccess'))
    showAddDialog.value = false
    await loadVoicePrintList()
  }
  catch (error) {
    console.error('添加说话人失败:', error)
    toast.error(t('voiceprint.addFailed'))
  }
}

// 提交编辑说话人
async function submitEdit() {
  if (!editForm.value.sourceName.trim()) {
    toast.error(t('voiceprint.pleaseInputName'))
    return
  }
  if (!editForm.value.audioId) {
    toast.error(t('voiceprint.pleaseSelectVector'))
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
    toast.success(t('voiceprint.editSuccess'))
    showEditDialog.value = false
    await loadVoicePrintList()
  }
  catch (error) {
    console.error('编辑说话人失败:', error)
    toast.error(t('voiceprint.editFailed'))
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
    msg: t('voiceprint.deleteConfirmMsg'),
    title: t('voiceprint.deleteConfirmTitle'),
  }).then(async () => {
    await deleteVoicePrint(id)
    toast.success(t('voiceprint.deleteSuccess'))
    await loadVoicePrintList()
  }).catch(() => {
    console.log('点击了取消按钮')
  })
}

onMounted(async () => {
  // 智能体已简化为默认

  loadVoicePrintList()
})

// 暴露方法给父组件
defineExpose({
  refresh,
})
</script>

<template>
  <view class="voiceprint-container" style="background: #f5f7fb; min-height: 100%;">
    <!-- 加载状态 -->
    <view v-if="loading && voicePrintList.length === 0" class="loading-container">
      <wd-loading color="#336cff" />
      <text class="loading-text">
        {{ t('voiceprint.loading') }}
      </text>
    </view>

    <!-- 声纹列表 -->
    <view v-else-if="voicePrintList.length > 0" class="voiceprint-list">
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
                  {{ t('voiceprint.delete') }}
                </view>
              </view>
            </template>
          </wd-swipe-action>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else-if="!loading" class="empty-container">
      <view class="flex flex-col items-center justify-center p-[100rpx_40rpx] text-center">
        <wd-icon name="voice" custom-class="text-[120rpx] text-[#d9d9d9] mb-[32rpx]" />
        <text class="mb-[32rpx] text-[32rpx] text-[#666666] font-medium">
          {{ t('voiceprint.emptyTitle') }}
        </text>
        <text class="text-[26rpx] text-[#999999] leading-[1.5]">
          {{ t('voiceprint.emptyDesc') }}
        </text>
      </view>
    </view>

    <!-- 浮动操作按钮 -->
    <wd-fab type="primary" size="small" :draggable="true" :expandable="false" @click="openAddDialog">
      <wd-icon name="add" />
    </wd-fab>

    <!-- MessageBox 组件 -->
    <wd-message-box />
  </view>

  <!-- 添加说话人弹窗 -->
  <wd-popup
    v-model="showAddDialog" position="center" custom-style="width: 90%; max-width: 400px; border-radius: 16px;"
    safe-area-inset-bottom
  >
    <view>
      <view class="w-full flex items-center justify-between border-b-[2rpx] border-[#eeeeee] p-[32rpx_32rpx_24rpx]">
        <text class="w-full text-center text-[32rpx] text-[#232338] font-semibold">
          {{ t('voiceprint.addSpeaker') }}
        </text>
      </view>

      <view class="p-[32rpx]">
        <!-- 声纹向量选择 -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * {{ t('voiceprint.voiceVector') }}
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
            * {{ t('voiceprint.name') }}
          </text>
          <input
            v-model="addForm.sourceName"
            class="box-border h-[80rpx] w-full border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text" :placeholder="t('voiceprint.pleaseInputName')"
          >
        </view>

        <!-- 描述 -->
        <view>
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * {{ t('voiceprint.description') }}
          </text>
          <textarea
            v-model="addForm.introduce" :maxlength="100" :placeholder="t('voiceprint.pleaseInputDescription')"
            class="box-border h-[200rpx] w-full resize-none border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
            {{ (addForm.introduce || '').length }}/100
          </view>
        </view>
      </view>

      <view class="flex gap-[16rpx] border-t-[2rpx] border-[#eeeeee] p-[24rpx_32rpx_32rpx]">
        <wd-button type="info" custom-class="flex-1" @click="showAddDialog = false">
            {{ t('voiceprint.cancel') }}
          </wd-button>
          <wd-button type="primary" custom-class="flex-1" @click="submitAdd">
            {{ t('voiceprint.save') }}
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
          {{ t('voiceprint.editSpeaker') }}
        </text>
      </view>

      <view class="p-[32rpx]">
        <!-- 声纹向量选择 -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * {{ t('voiceprint.voiceVector') }}
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
            * {{ t('voiceprint.name') }}
          </text>
          <input
            v-model="editForm.sourceName"
            class="box-border h-[80rpx] w-full border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text" :placeholder="t('voiceprint.pleaseInputName')"
          >
        </view>

        <!-- 描述 -->
        <view>
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * {{ t('voiceprint.description') }}
          </text>
          <textarea
            v-model="editForm.introduce" :maxlength="100" :placeholder="t('voiceprint.pleaseInputDescription')"
            class="box-border h-[200rpx] w-full resize-none border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
            {{ (editForm.introduce || '').length }}/100
          </view>
        </view>
      </view>

      <view class="flex gap-[16rpx] border-t-[2rpx] border-[#eeeeee] p-[24rpx_32rpx_32rpx]">
        <wd-button type="info" custom-class="flex-1" @click="showEditDialog = false">
            {{ t('voiceprint.cancel') }}
          </wd-button>
          <wd-button type="primary" custom-class="flex-1" @click="submitEdit">
            {{ t('voiceprint.save') }}
          </wd-button>
      </view>
    </view>
  </wd-popup>

  <!-- 语音对话记录选择动作面板 -->
  <wd-action-sheet
    v-model="showChatHistoryDialog" :actions="chatHistoryActions" :title="t('voiceprint.selectVector')"
    @select="selectAudioId"
  />
</template>

<style scoped>
.voiceprint-container {
  position: relative;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100rpx 40rpx;
}

.loading-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #666666;
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
