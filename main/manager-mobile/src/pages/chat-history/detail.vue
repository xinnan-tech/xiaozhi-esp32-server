<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "Chat Detail"
  }
}
</route>

<script lang="ts" setup>
import type { ChatMessage, UserMessageContent } from '@/api/chat-history/types'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { getAudioId, getChatHistory } from '@/api/chat-history/chat-history'
import { t } from '@/i18n'
import { debounce, getEnvBaseUrl } from '@/utils'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'ChatDetail',
})

// Get distance from screen bounds to safe area
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

// Page Parameters
const sessionId = ref('')
const agentId = ref('')

// Agent info (simplified)
const currentAgent = computed(() => {
  return {
    id: agentId.value,
    agentName: t('chatHistory.assistantName'),
  }
})

// Chat data
const messageList = ref<ChatMessage[]>([])
const loading = ref(false)

// Audio playback related
const audioContext = ref<UniApp.InnerAudioContext | null>(null)
const playingAudioId = ref<string | null>(null)
const expandedToolResults = ref({})

// Go back
function goBack() {
  uni.navigateBack()
}

// Load chat history
async function loadChatHistory() {
  if (!sessionId.value || !agentId.value) {
    console.error('Missing required parameters')
    return
  }

  try {
    loading.value = true
    const response = await getChatHistory(agentId.value, sessionId.value)
    messageList.value = response
  }
  catch (error) {
    console.error('Failed to fetch chat history:', error)
    toast.error(t('chatHistory.loadFailed'))
  }
  finally {
    loading.value = false
  }
}

// Parse user message content
function parseUserMessage(content: string): UserMessageContent | null {
  try {
    return JSON.parse(content)
  }
  catch {
    return null
  }
}

// Get message display content
function getMessageContent(message: ChatMessage): string {
  if (message.chatType === 1) {
    // User message, requires JSON parsing
    const parsed = parseUserMessage(message.content)
    return parsed ? parsed.content : message.content
  }
  else {
    // AI message, display directly
    return message.content
  }
}

// Get speaker name
function getSpeakerName(message: ChatMessage): string {
  if (message.chatType === 1) {
    const parsed = parseUserMessage(message.content)
    return parsed ? parsed.speaker : t('chatHistory.userName')
  }
  else {
    return currentAgent.value?.agentName || t('chatHistory.aiAssistantName')
  }
}

// Format time
function formatTime(timeStr: string) {
  if (!timeStr)
    return t('chatHistory.unknownTime')

  // Process time string to ensure correct format
  const date = new Date(timeStr.replace(' ', 'T')) // Convert to ISO format
  const now = new Date()

  // Check if date is valid
  if (Number.isNaN(date.getTime())) {
    return timeStr // If parsing fails, return original string directly
  }

  const diff = now.getTime() - date.getTime()

  // Less than 1 minute
  if (diff < 60000)
    return t('chatHistory.justNow')

  // Less than 1 hour
  if (diff < 3600000)
    return t('chatHistory.minutesAgo', { minutes: Math.floor(diff / 60000) })

  // Less than 1 day (24 hours)
  if (diff < 86400000)
    return t('chatHistory.hoursAgo', { hours: Math.floor(diff / 3600000) })

  // Less than 7 days
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return t('chatHistory.daysAgo', { days })
  }

  // Over 7 days, show specific date
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const currentYear = now.getFullYear()

  // If current year, do not display year
  if (year === currentYear) {
    return `${month}-${day}`
  }

  return `${year}-${month}-${day}`
}

// Play audio
const playAudio = debounce(async (audioId: string) => {
  if (!audioId) {
    toast.error(t('chatHistory.invalidAudioId'))
    return
  }

  try {
    // Stop other audio playback if active
    if (audioContext.value) {
      audioContext.value.stop()
    }
    // Pause playback if the current audio ID matches the request ID
    if (playingAudioId.value === audioId) {
      playingAudioId.value = null
      return
    }

    // Get audio download ID
    const downloadId = await getAudioId(audioId)

    // Construct audio playback URL
    const baseUrl = getEnvBaseUrl()
    const audioUrl = `${baseUrl}/agent/play/${downloadId}`

    // Create audio context
    if (!audioContext.value) {
      audioContext.value = uni.createInnerAudioContext()
    }
    audioContext.value.src = audioUrl

    // Set Playback State
    playingAudioId.value = audioId

    // Listen for playback completion
    audioContext.value.onEnded(() => {
      playingAudioId.value = null
      if (audioContext.value) {
        audioContext.value.destroy()
        audioContext.value = null
      }
    })

    // Listen for playback error
    audioContext.value.onError((error) => {
      console.error('Audio playback failed:', error)
      toast.error(t('chatHistory.audioPlayFailed'))
      playingAudioId.value = null
      if (audioContext.value) {
        audioContext.value.destroy()
        audioContext.value = null
      }
    })

    // Start playback
    audioContext.value.play()
  }
  catch (error) {
    console.error('Failed to play audio:', error)
    toast.error(t('chatHistory.playAudioFailed'))
    playingAudioId.value = null
  }
}, 400)

function extractContentFromString(content: string) {
  if (!content || content.trim() === '') {
    return content
  }

  // Attempt to parse as JSON
  try {
    const jsonObj = JSON.parse(content)

    // If in array format (containing text and tool)
    if (Array.isArray(jsonObj)) {
      return jsonObj
    }

    // If it is an object with a content field
    if (jsonObj && typeof jsonObj === 'object' && jsonObj.content) {
      return jsonObj.content
    }
  }
  catch (e) {
    // If not valid JSON, return original content directly
  }

  // If not JSON format or missing content field, return original content directly
  return content
}

function toggleToolResult(messageIndex, itemIndex) {
  const key = `${messageIndex}-${itemIndex}`
  expandedToolResults.value[key] = !expandedToolResults.value[key]
}

function isToolResultCollapsed(messageIndex, itemIndex) {
  const key = `${messageIndex}-${itemIndex}`
  // Collapsed by default (true means collapsed)
  return !expandedToolResults.value[key]
}

function getFirstLineText(text: string) {
  if (!text) {
    return ''
  }
  const firstLine = text.split('\n')[0]
  return firstLine.length < text.length ? `${firstLine}...` : text
}

onLoad((options) => {
  if (options?.sessionId && options?.agentId) {
    sessionId.value = options.sessionId
    agentId.value = options.agentId
  }
  else {
    console.error('Missing required parameters')
    toast.error(t('chatHistory.parameterError'))
  }
})

onShow(() => {
  loadChatHistory()
})

// Clean up audio resources on page destroy
onUnload(() => {
  if (audioContext.value) {
    audioContext.value.stop()
    audioContext.value.destroy()
    audioContext.value = null
  }
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- Status bar background -->
    <view class="w-full bg-white" :style="{ height: `${safeAreaInsets?.top}px` }" />

    <!-- Navigation bar -->
    <wd-navbar :title="t('chatHistory.pageTitle')">
      <template #left>
        <wd-icon name="arrow-left" size="18" @click="goBack" />
      </template>
    </wd-navbar>

    <!-- Chat message list -->
    <scroll-view
      scroll-y
      :style="{ height: `calc(100vh - ${safeAreaInsets?.top || 0}px - 120rpx)` }"
      class="box-border flex-1 bg-[#f5f7fb] p-[20rpx]"
      :scroll-into-view="`message-${messageList.length - 1}`"
    >
      <view v-if="loading" class="flex flex-col items-center justify-center gap-[20rpx] p-[100rpx_0]">
        <wd-loading />
        <text class="text-[28rpx] text-[#65686f]">
          {{ t('chatHistory.loading') }}
        </text>
      </view>

      <view v-else class="flex flex-col gap-[20rpx]">
        <view
          v-for="(message, index) in messageList"
          :id="`message-${index}`"
          :key="index"
          class="w-full flex"
          :class="{
            'justify-end': message.chatType === 1,
            'justify-start': message.chatType === 2,
          }"
        >
          <view
            class="max-w-[80%] flex flex-col gap-[8rpx]"
            :class="{
              'items-end': message.chatType === 1,
              'items-start': message.chatType === 2,
              'tool-message': message.chatType === 3,
            }"
          >
            <!-- Message bubble -->
            <view
              class="shadow-message break-words rounded-[20rpx] p-[24rpx] leading-[1.4]"
              :class="{
                'bg-[#336cff] text-white': message.chatType === 1,
                'bg-white text-[#232338] border border-[#eeeeee]': [2, 3].includes(message.chatType),
              }"
            >
              <template v-if="Array.isArray(extractContentFromString(message.content))">
                <div class="content-wrapper">
                  <div v-for="(item, idx) in extractContentFromString(message.content)" :key="idx">
                    <div v-if="item.type === 'text'" class="text-content">
                      {{ item.text }}
                    </div>
                    <div v-else-if="item.type === 'tool'" class="tool-call-text">
                      {{ item.text }}
                    </div>
                    <div v-else-if="item.type === 'tool_result'" class="tool-call-text">
                      <div v-if="item.text && item.text.length > 80" class="tool-result-wrapper">
                        <div v-if="isToolResultCollapsed(index, idx)" class="tool-result-collapsed">
                          {{ getFirstLineText(item.text) }}
                        </div>
                        <div v-else class="tool-result-expanded">
                          {{ item.text }}
                        </div>
                        <span class="tool-toggle-btn" @click="toggleToolResult(index, idx)">
                          <wd-icon :name="isToolResultCollapsed(index, idx) ? 'arrow-down' : 'arrow-up'" size="12" />
                        </span>
                      </div>
                      <div v-else>
                        {{ item.text }}
                      </div>
                    </div>
                  </div>
                </div>
              </template>
              <!-- Content area - Use flex layout to align icons and text -->
              <view v-else class="flex items-center gap-[12rpx]">
                <!-- Audio playback icon -->
                <view
                  v-if="message.audioId"
                  class="flex-shrink-0 cursor-pointer transition-transform duration-200 active:scale-90"
                  :class="{
                    'text-white animate-pulse-audio': message.chatType === 1 && playingAudioId === message.audioId,
                    'text-[#ffd700]': message.chatType === 1 && playingAudioId === message.audioId && playingAudioId,
                    'text-[#336cff] animate-pulse-audio': message.chatType === 2 && playingAudioId === message.audioId,
                    'text-[#ff6b35]': message.chatType === 2 && playingAudioId === message.audioId && playingAudioId,
                    'text-white': message.chatType === 1 && playingAudioId !== message.audioId,
                    'text-[#336cff]': message.chatType === 2 && playingAudioId !== message.audioId,
                  }"
                  @click="playAudio(message.audioId)"
                >
                  <wd-icon
                    :name="playingAudioId === message.audioId ? 'pause-circle-filled' : 'play-circle-filled'"
                    size="20"
                  />
                </view>

                <!-- Message content container -->
                <view class="min-w-0 flex-1">
                  <!-- Message content -->
                  <text class="block text-[28rpx]">
                    {{ getMessageContent(message) }}
                  </text>
                </view>
              </view>
            </view>

            <!-- Speaker info -->
            <text
              class="mx-[12rpx] text-[22rpx] text-[#9d9ea3]"
              :class="{
                'text-right': message.chatType === 1,
                'text-left': message.chatType === 2,
              }"
            >
              {{ formatTime(message.createdAt) }}
            </text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<style>
/* Custom shadow and animation effects; styles not expressible with UnoCSS */
.shadow-message {
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

@keyframes pulse-audio {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.animate-pulse-audio {
  animation: pulse-audio 1.5s infinite;
}

.text-content {
  display: block;
  margin-bottom: 8rpx;
}

.tool-call-text {
  color: #1890ff;
  font-family: 'Courier New', monospace;
  font-weight: 500;
  font-size: 24rpx;
  display: block;
  margin-top: 8rpx;
}

.user-message .tool-call-text {
  color: #e6f7ff;
}

.tool-message .message-content {
  background-color: #f0f0f0;
}

.tool-result-wrapper {
  position: relative;
  padding-right: 40rpx;
}

.tool-result-collapsed {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-toggle-btn {
  position: absolute;
  right: 0;
  top: 0;
  cursor: pointer;
  color: #1890ff;
  font-size: 24rpx;
}
</style>
