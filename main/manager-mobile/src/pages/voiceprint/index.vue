<script lang="ts" setup>
import type { ChatHistory, CreateSpeakerData, VoicePrint } from '@/api/voiceprint'
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'wot-design-uni/components/wd-message-box'
import { useToast } from 'wot-design-uni/components/wd-toast'
import { createVoicePrint, deleteVoicePrint, getChatHistory, getVoicePrintList, updateVoicePrint } from '@/api/voiceprint'

defineOptions({
  name: 'VoicePrintManage',
})

// Receive props
interface Props {
  agentId?: string
}

const props = withDefaults(defineProps<Props>(), {
  agentId: 'default'
})

// Get screen boundary to safe area distance
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

// Page data
const voicePrintList = ref<VoicePrint[]>([])
const chatHistoryList = ref<ChatHistory[]>([])
const chatHistoryActions = ref<any[]>([])
const swipeStates = ref<Record<string, 'left' | 'close' | 'right'>>({})
const loading = ref(false)

// Use passed agent ID
const currentAgentId = computed(() => {
  return props.agentId
})

// Agent selection related functions have been removed

// Dialog related
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

// Get voiceprint list
async function loadVoicePrintList() {
  try {
    console.log('Get voiceprint list')

    // Check if there is currently selected agent
    if (!currentAgentId.value) {
      console.warn('No selected agent')
      voicePrintList.value = []
      return
    }

    loading.value = true
    const data = await getVoicePrintList(currentAgentId.value)

    // Initialize swipe status
    const list = data || []
    list.forEach((item) => {
      if (!swipeStates.value[item.id]) {
        swipeStates.value[item.id] = 'close'
      }
    })

    voicePrintList.value = list
  }
  catch (error) {
    console.error('Failed to get voiceprint list:', error)
    voicePrintList.value = []
  }
  finally {
    loading.value = false
  }
}

// Refresh method exposed to parent component
async function refresh() {
  await loadVoicePrintList()
}

// Get voice conversation records
async function loadChatHistory() {
  try {
    if (!currentAgentId.value) {
      toast.error('Please select an agent first')
      return
    }

    const data = await getChatHistory(currentAgentId.value)
    chatHistoryList.value = data || []
    // Convert to ActionSheet format
    chatHistoryActions.value = chatHistoryList.value.map((item, index) => ({
      name: item.content,
      audioId: item.audioId,
      index,
    }))
    showChatHistoryDialog.value = true
  }
  catch (error) {
    console.error('Failed to get conversation records:', error)
    toast.error('Failed to get conversation records')
  }
}

// Open add dialog
function openAddDialog() {
  if (!currentAgentId.value) {
    toast.error('Please select an agent first')
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

// Open edit dialog
function openEditDialog(item: VoicePrint) {
  editForm.value = { ...item }
  showEditDialog.value = true
}

// Get selected audio display content
function getSelectedAudioContent(audioId: string) {
  if (!audioId)
    return 'Click to select voiceprint vector'
  const chatItem = chatHistoryList.value.find(item => item.audioId === audioId)
  return chatItem ? chatItem.content : `Selected: ${audioId.substring(0, 8)}...`
}

// Select voiceprint vector
function selectAudioId({ item }: { item: any }) {
  if (showAddDialog.value) {
    addForm.value.audioId = item.audioId
  }
  else if (showEditDialog.value) {
    editForm.value.audioId = item.audioId
  }
  showChatHistoryDialog.value = false
}

// Submit add speaker
async function submitAdd() {
  if (!addForm.value.sourceName.trim()) {
    toast.error('Please enter name')
    return
  }
  if (!addForm.value.audioId) {
    toast.error('Please select voiceprint vector')
    return
  }

  try {
    await createVoicePrint(addForm.value)
    toast.success('Added successfully')
    showAddDialog.value = false
    await loadVoicePrintList()
  }
  catch (error) {
    console.error('Failed to add speaker:', error)
    toast.error('Failed to add speaker')
  }
}

// Submit edit speaker
async function submitEdit() {
  if (!editForm.value.sourceName.trim()) {
    toast.error('Please enter name')
    return
  }
  if (!editForm.value.audioId) {
    toast.error('Please select voiceprint vector')
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
    toast.success('Edited successfully')
    showEditDialog.value = false
    await loadVoicePrintList()
  }
  catch (error) {
    console.error('Failed to edit speaker:', error)
    toast.error('Failed to edit speaker')
  }
}

// Handle edit operation
function handleEdit(item: VoicePrint) {
  openEditDialog(item)
  swipeStates.value[item.id] = 'close'
}

// Delete voiceprint
async function handleDelete(id: string) {
  message.confirm({
    msg: 'Are you sure you want to delete this speaker?',
    title: 'Confirm Delete',
  }).then(async () => {
    await deleteVoicePrint(id)
    toast.success('Delete successful')
    await loadVoicePrintList()
  }).catch(() => {
    console.log('Clicked cancel button')
  })
}

onMounted(async () => {
  // Agent simplified to default

  loadVoicePrintList()
})

// Expose methods to parent component
defineExpose({
  refresh,
})
</script>

<template>
  <view class="voiceprint-container" style="background: #f5f7fb; min-height: 100%;">
    <!-- Loading state -->
    <view v-if="loading && voicePrintList.length === 0" class="loading-container">
      <wd-loading color="#336cff" />
      <text class="loading-text">
        Loading...
      </text>
    </view>

    <!-- Voiceprint list -->
    <view v-else-if="voicePrintList.length > 0" class="voiceprint-list">
      <!-- Voiceprint card list -->
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
                  {{ item.introduce || 'No description' }}
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
                  Delete
                </view>
              </view>
            </template>
          </wd-swipe-action>
        </view>
      </view>
    </view>

    <!-- Empty state -->
    <view v-else-if="!loading" class="empty-container">
      <view class="flex flex-col items-center justify-center p-[100rpx_40rpx] text-center">
        <wd-icon name="voice" custom-class="text-[120rpx] text-[#d9d9d9] mb-[32rpx]" />
        <text class="mb-[16rpx] text-[32rpx] text-[#666666] font-medium">
          No voiceprint data
        </text>
        <text class="text-[26rpx] text-[#999999] leading-[1.5]">
          Click the + button in the bottom right corner to add your first speaker
        </text>
      </view>
    </view>

    <!-- Floating action button -->
    <wd-fab type="primary" size="small" :draggable="true" :expandable="false" @click="openAddDialog">
      <wd-icon name="add" />
    </wd-fab>

    <!-- MessageBox component -->
    <wd-message-box />
  </view>

  <!-- Add speaker dialog -->
  <wd-popup
    v-model="showAddDialog" position="center" custom-style="width: 90%; max-width: 400px; border-radius: 16px;"
    safe-area-inset-bottom
  >
    <view>
      <view class="w-full flex items-center justify-between border-b-[2rpx] border-[#eeeeee] p-[32rpx_32rpx_24rpx]">
        <text class="w-full text-center text-[32rpx] text-[#232338] font-semibold">
          Add Speaker
        </text>
      </view>

      <view class="p-[32rpx]">
        <!-- Voiceprint Vector Selection -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * Voiceprint Vector
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

        <!-- Name -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * Name
          </text>
          <input
            v-model="addForm.sourceName"
            class="box-border h-[80rpx] w-full border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text" placeholder="Please enter name"
          >
        </view>

        <!-- Description -->
        <view>
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * Description
          </text>
          <textarea
            v-model="addForm.introduce" :maxlength="100" placeholder="Please enter description"
            class="box-border h-[200rpx] w-full resize-none border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
            {{ (addForm.introduce || '').length }}/100
          </view>
        </view>
      </view>

      <view class="flex gap-[16rpx] border-t-[2rpx] border-[#eeeeee] p-[24rpx_32rpx_32rpx]">
        <wd-button type="info" custom-class="flex-1" @click="showAddDialog = false">
          Cancel
        </wd-button>
        <wd-button type="primary" custom-class="flex-1" @click="submitAdd">
          Save
        </wd-button>
      </view>
    </view>
  </wd-popup>

  <!-- Edit speaker dialog -->
  <wd-popup
    v-model="showEditDialog" position="center" custom-style="width: 90%; max-width: 400px; border-radius: 16px;"
    safe-area-inset-bottom
  >
    <view>
      <view class="w-full flex items-center justify-between border-b-[2rpx] border-[#eeeeee] p-[32rpx_32rpx_24rpx]">
        <text class="w-full text-center text-[32rpx] text-[#232338] font-semibold">
          Edit Speaker
        </text>
      </view>

      <view class="p-[32rpx]">
        <!-- Voiceprint Vector Selection -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * Voiceprint Vector
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

        <!-- Name -->
        <view class="mb-[32rpx]">
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * Name
          </text>
          <input
            v-model="editForm.sourceName"
            class="box-border h-[80rpx] w-full border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text" placeholder="Please enter name"
          >
        </view>

        <!-- Description -->
        <view>
          <text class="mb-[16rpx] block text-[28rpx] text-[#232338] font-medium">
            * Description
          </text>
          <textarea
            v-model="editForm.introduce" :maxlength="100" placeholder="Please enter description"
            class="box-border h-[200rpx] w-full resize-none border-[1rpx] border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
            {{ (editForm.introduce || '').length }}/100
          </view>
        </view>
      </view>

      <view class="flex gap-[16rpx] border-t-[2rpx] border-[#eeeeee] p-[24rpx_32rpx_32rpx]">
        <wd-button type="info" custom-class="flex-1" @click="showEditDialog = false">
          Cancel
        </wd-button>
        <wd-button type="primary" custom-class="flex-1" @click="submitEdit">
          Save
        </wd-button>
      </view>
    </view>
  </wd-popup>

  <!-- Voice chat history selection action panel -->
  <wd-action-sheet
    v-model="showChatHistoryDialog" :actions="chatHistoryActions" title="Select Voiceprint Vector"
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
