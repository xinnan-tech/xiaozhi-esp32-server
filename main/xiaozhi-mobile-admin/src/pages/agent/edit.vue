<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "编辑"
  }
}
</route>

<script lang="ts" setup>
import type { AgentDetail, ModelOption, PluginDefinition, RoleTemplate } from '@/api/agent/types'
import { onLoad } from '@dcloudio/uni-app'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { getAgentDetail, getModelOptions, getPluginFunctions, getRoleTemplates, getTTSVoices, updateAgent } from '@/api/agent/agent'
import { useAgentStore, usePluginStore } from '@/store'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'AgentEdit',
})

// 页面参数
const agentId = ref('')

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

// 智能体管理
const agentStore = useAgentStore()
const showAgentPicker = ref<boolean>(false)

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
  if (selectedAgentId !== agentId.value) {
    // 设置当前智能体
    agentStore.setCurrentAgent(selectedAgentId)
    // 跳转到新的智能体编辑页面
    uni.redirectTo({
      url: `/pages/agent/edit?id=${selectedAgentId}`,
    })
  }
  closeAgentSelector()
}

// 表单数据
const formData = ref<Partial<AgentDetail>>({
  agentName: '',
  systemPrompt: '',
  summaryMemory: '',
  vadModelId: '',
  asrModelId: '',
  llmModelId: '',
  vllmModelId: '',
  intentModelId: '',
  memModelId: '',
  ttsModelId: '',
  ttsVoiceId: '',
})

// 显示名称数据
const displayNames = ref({
  vad: '请选择',
  asr: '请选择',
  llm: '请选择',
  vllm: '请选择',
  intent: '请选择',
  memory: '请选择',
  tts: '请选择',
  voiceprint: '请选择',
})

// 角色模板数据
const roleTemplates = ref<RoleTemplate[]>([])
const selectedTemplateId = ref('')

// 加载状态
const loading = ref(false)
const saving = ref(false)

// 模型选项数据
const modelOptions = ref<{
  [key: string]: ModelOption[]
}>({
  VAD: [],
  ASR: [],
  LLM: [],
  VLLM: [],
  Intent: [],
  Memory: [],
  TTS: [],
})

// 音色选项数据
const voiceOptions = ref<{ id: string, name: string }[]>([])

// 选择器显示状态
const pickerShow = ref<{
  [key: string]: boolean
}>({
  vad: false,
  asr: false,
  llm: false,
  vllm: false,
  intent: false,
  memory: false,
  tts: false,
  voiceprint: false,
})

const allFunctions = ref<PluginDefinition[]>([])

// 使用插件store
const pluginStore = usePluginStore()

// 监听当前智能体变化，自动加载数据
watch(() => agentStore.currentAgentId, async (newId) => {
  if (newId && newId !== agentId.value) {
    agentId.value = newId
    await loadAgentDetail()
  }
}, { immediate: true })

// 加载智能体详情
async function loadAgentDetail() {
  if (!agentId.value)
    return

  try {
    loading.value = true
    const detail = await getAgentDetail(agentId.value)
    formData.value = { ...detail }

    // 更新插件store
    pluginStore.setCurrentAgentId(agentId.value)
    pluginStore.setCurrentFunctions(detail.functions || [])

    // 如果有TTS模型，加载对应的音色选项
    if (detail.ttsModelId) {
      await loadVoiceOptions(detail.ttsModelId)
    }

    // 等待模型选项加载完成后再更新显示名称
    await nextTick()
    updateDisplayNames()
  }
  catch (error) {
    console.error('加载智能体详情失败:', error)
    toast.error('加载失败')
  }
  finally {
    loading.value = false
  }
}

// 获取音色显示名称
function getVoiceDisplayName(ttsVoiceId: string) {
  if (!ttsVoiceId)
    return '请选择'

  console.log('=== 音色映射调试 ===')
  console.log('当前音色ID:', ttsVoiceId)
  console.log('当前TTS模型:', formData.value.ttsModelId)
  console.log('可用音色选项:', voiceOptions.value)

  // 首先尝试直接从音色选项中匹配ID
  const voice = voiceOptions.value.find(v => v.id === ttsVoiceId)
  if (voice) {
    console.log('直接匹配成功:', voice)
    return voice.name
  }

  // 如果没找到，尝试兼容性映射
  if (voiceOptions.value.length > 0) {
    console.log('直接匹配失败，尝试兼容性映射')

    // 创建索引映射：voice1 → 第1个音色，voice2 → 第2个音色
    const indexMap = {
      voice1: 0,
      voice2: 1,
      voice3: 2,
      voice4: 3,
      voice5: 4,
    }

    const index = indexMap[ttsVoiceId]
    if (index !== undefined && voiceOptions.value[index]) {
      const mappedVoice = voiceOptions.value[index]
      console.log(`索引映射: ${ttsVoiceId} → index ${index} → ${mappedVoice.name}`)
      return mappedVoice.name
    }
  }

  console.log('所有映射方式都失败，返回原始ID:', ttsVoiceId)
  return ttsVoiceId
}

// 更新显示名称
function updateDisplayNames() {
  if (!formData.value)
    return

  displayNames.value.vad = getModelDisplayName('VAD', formData.value.vadModelId)
  displayNames.value.asr = getModelDisplayName('ASR', formData.value.asrModelId)
  displayNames.value.llm = getModelDisplayName('LLM', formData.value.llmModelId)
  displayNames.value.vllm = getModelDisplayName('VLLM', formData.value.vllmModelId)
  displayNames.value.intent = getModelDisplayName('Intent', formData.value.intentModelId)
  displayNames.value.memory = getModelDisplayName('Memory', formData.value.memModelId)
  displayNames.value.tts = getModelDisplayName('TTS', formData.value.ttsModelId)

  // 角色音色特殊处理
  displayNames.value.voiceprint = getVoiceDisplayName(formData.value.ttsVoiceId || '')

  console.log('最终音色显示名称:', displayNames.value.voiceprint)
}

// 加载角色模板
async function loadRoleTemplates() {
  try {
    const templates = await getRoleTemplates()
    roleTemplates.value = templates
  }
  catch (error) {
    console.error('加载角色模板失败:', error)
  }
}

// 加载模型选项
async function loadModelOptions() {
  const modelTypes = ['VAD', 'ASR', 'LLM', 'VLLM', 'Intent', 'Memory', 'TTS']

  try {
    await Promise.all(
      modelTypes?.map(async (type) => {
        console.log(`加载模型类型: ${type}`)
        const options = await getModelOptions(type)
        modelOptions.value[type] = options
        console.log(`${type} 选项:`, options)
      }) || [],
    )
    console.log('所有模型选项加载完成:', modelOptions.value)
  }
  catch (error) {
    console.error('加载模型选项失败:', error)
  }
}

// 加载TTS音色选项
async function loadVoiceOptions(ttsModelId?: string) {
  if (!ttsModelId)
    return

  try {
    console.log(`加载音色选项: ${ttsModelId}`)
    const voices = await getTTSVoices(ttsModelId)
    voiceOptions.value = voices
    console.log('音色选项:', voices)
  }
  catch (error) {
    console.error('加载音色选项失败:', error)
    voiceOptions.value = []
  }
}

// 选择角色模板
function selectRoleTemplate(templateId: string) {
  if (selectedTemplateId.value === templateId) {
    selectedTemplateId.value = ''
    return
  }

  selectedTemplateId.value = templateId
  const template = roleTemplates.value.find(t => t.id === templateId)
  if (template) {
    formData.value.systemPrompt = template.systemPrompt
    formData.value.vadModelId = template.vadModelId
    formData.value.asrModelId = template.asrModelId
    formData.value.llmModelId = template.llmModelId
    formData.value.vllmModelId = template.vllmModelId
    formData.value.intentModelId = template.intentModelId
    formData.value.memModelId = template.memModelId
    formData.value.ttsModelId = template.ttsModelId
    formData.value.ttsVoiceId = template.ttsVoiceId
  }
}

// 打开选择器
function openPicker(type: string) {
  pickerShow.value[type] = true
}

// 选择器确认
async function onPickerConfirm(type: string, value: any, name: string) {
  console.log('选择器确认:', type, value, name)

  // 保存显示名称
  displayNames.value[type] = name

  switch (type) {
    case 'vad':
      formData.value.vadModelId = value
      break
    case 'asr':
      formData.value.asrModelId = value
      break
    case 'llm':
      formData.value.llmModelId = value
      break
    case 'vllm':
      formData.value.vllmModelId = value
      break
    case 'intent':
      formData.value.intentModelId = value
      displayNames.value.intent = name // 确保显示名称正确更新
      break
    case 'memory':
      formData.value.memModelId = value
      displayNames.value.memory = name // 确保显示名称正确更新
      break
    case 'tts':
      formData.value.ttsModelId = value
      // 当选择TTS模型时，自动加载对应的音色选项
      await loadVoiceOptions(value)
      // 重置音色选择
      formData.value.ttsVoiceId = ''
      displayNames.value.voiceprint = '请选择'
      break
    case 'voiceprint':
      formData.value.ttsVoiceId = value
      displayNames.value.voiceprint = name // 确保显示名称正确更新
      break
  }

  pickerShow.value[type] = false
}

// 选择器取消
function onPickerCancel(type: string) {
  pickerShow.value[type] = false
}

// 获取模型显示名称
function getModelDisplayName(modelType: string, modelId: string) {
  if (!modelId)
    return '请选择'

  // 直接从API配置数据中查找匹配的ID
  const options = modelOptions.value[modelType]

  if (!options || options.length === 0) {
    return modelId
  }

  const option = options.find(opt => opt.id === modelId)
  if (option) {
    return option.modelName
  }
  return modelId
}

// 保存智能体
async function saveAgent() {
  if (!formData.value.agentName?.trim()) {
    toast.warning('请输入助手昵称')
    return
  }

  if (!formData.value.systemPrompt?.trim()) {
    toast.warning('请输入角色介绍')
    return
  }

  try {
    saving.value = true
    await updateAgent(agentId.value, formData.value)

    toast.success('保存成功')

    setTimeout(() => {
      uni.navigateBack()
    }, 1000)
  }
  catch (error) {
    console.error('保存失败:', error)
    toast.error('保存失败')
  }
  finally {
    saving.value = false
  }
}

// 返回上一页
function goBack() {
  uni.navigateBack()
}

function loadPluginFunctions() {
  getPluginFunctions().then((res) => {
    const processedFunctions = res?.map((item) => {
      const meta = JSON.parse(item.fields || '[]')
      const params = meta.reduce((m: any, f: any) => {
        m[f.key] = f.default
        return m
      }, {})
      return { ...item, fieldsMeta: meta, params }
    }) || []

    allFunctions.value = processedFunctions
    // 同时更新到store
    pluginStore.setAllFunctions(processedFunctions)
  })
}

function handleTools() {
  console.log('当前插件配置:', formData.value.functions)

  // 确保store中有最新数据
  pluginStore.setCurrentAgentId(agentId.value)
  pluginStore.setCurrentFunctions(formData.value.functions || [])
  pluginStore.setAllFunctions(allFunctions.value)

  uni.navigateTo({
    url: '/pages/agent/tools',
  })
}

// 监听插件配置更新
function watchPluginUpdates() {
  // 监听store中的插件配置变化
  watch(() => pluginStore.currentFunctions, (newFunctions) => {
    console.log('插件配置已更新:', newFunctions)
    formData.value.functions = newFunctions
  }, { deep: true })
}

onLoad((options) => {
  if (options?.id) {
    agentId.value = options.id
  }
})

onMounted(async () => {
  // 初始化插件配置监听
  watchPluginUpdates()

  // 确保 agent store 中有数据，如果没有则加载
  if (!agentStore.isLoaded) {
    await agentStore.loadAgentList()
  }

  // 先加载模型选项和角色模板
  await Promise.all([
    loadRoleTemplates(),
    loadModelOptions(),
    loadPluginFunctions(),
  ])

  // 然后加载智能体详情，这样可以正确映射显示名称
  if (agentId.value) {
    await loadAgentDetail()
  }
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- 导航栏 -->
    <wd-navbar title="助手设置" safe-area-inset-top>
      <template #left>
        <wd-icon name="arrow-left" size="18" @click="goBack" />
      </template>
      <template #right>
        <wd-icon name="filter1" size="18" @click="showAgentSelector" />
      </template>
    </wd-navbar>

    <!-- 主内容滚动区域 -->
    <scroll-view
      scroll-y
      :style="{ height: `calc(100vh - ${safeAreaInsets?.top || 0}px - 120rpx)` }"
      class="flex-1 px-[20rpx] bg-[#f5f7fb] box-border"
      enable-back-to-top
    >
      <!-- 基础信息标题 -->
      <view class="pb-[20rpx] first:pt-[20rpx]">
        <text class="text-[36rpx] font-bold text-[#232338]">
          基础信息
        </text>
      </view>

      <!-- 基础信息卡片 -->
      <view class="bg-[#fbfbfb] rounded-[20rpx] mb-[24rpx] p-[24rpx] border border-[#eeeeee]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <view class="mb-[24rpx] last:mb-0">
          <text class="block text-[28rpx] text-[#232338] font-medium mb-[12rpx]">
            助手昵称
          </text>
          <input
            v-model="formData.agentName"
            class="w-full h-[80rpx] p-[16rpx_20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] text-[28rpx] text-[#232338] box-border leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
            type="text"
            placeholder="请输入助手昵称"
          >
        </view>

        <view class="mb-[24rpx] last:mb-0">
          <text class="block text-[28rpx] text-[#232338] font-medium mb-[12rpx]">
            角色模式
          </text>
          <view class="flex flex-wrap gap-[12rpx] mt-0">
            <view
              v-for="template in roleTemplates"
              :key="template.id"
              class="px-[24rpx] py-[12rpx] bg-[rgba(51,108,255,0.1)] text-[#336cff] rounded-[20rpx] text-[24rpx] border border-[rgba(51,108,255,0.2)] cursor-pointer transition-all duration-300"
              :class="{ 'bg-[#336cff] text-white border-[#336cff]': selectedTemplateId === template.id }"
              @click="selectRoleTemplate(template.id)"
            >
              {{ template.agentName }}
            </view>
          </view>
        </view>

        <view class="mb-[24rpx] last:mb-0">
          <text class="block text-[28rpx] text-[#232338] font-medium mb-[12rpx]">
            角色介绍
          </text>
          <textarea
            v-model="formData.systemPrompt"
            :maxlength="2000"
            placeholder="请输入角色介绍"
            class="w-full h-[500rpx] p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] text-[26rpx] text-[#232338] leading-[1.6] resize-none box-border outline-none break-words break-all focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          />
          <view class="text-right text-[22rpx] text-[#9d9ea3] mt-[8rpx]">
            {{ (formData.systemPrompt || '').length }}/2000
          </view>
        </view>
      </view>

      <!-- 模型配置标题 -->
      <view class="pb-[20rpx]">
        <text class="text-[36rpx] font-bold text-[#232338]">
          模型配置
        </text>
      </view>

      <!-- 模型配置卡片 -->
      <view class="bg-[#fbfbfb] rounded-[20rpx] mb-[24rpx] p-[24rpx] border border-[#eeeeee]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <view class="flex flex-col gap-[16rpx]">
          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('vad')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              语音活动检测
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.vad }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('asr')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              语音识别
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.asr }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('llm')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              大语言模型
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.llm }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('vllm')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              视觉大模型
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.vllm }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('intent')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              意图识别
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.intent }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('memory')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              记忆
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.memory }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>
        </view>
      </view>

      <!-- 语音设置标题 -->
      <view class="pb-[20rpx]">
        <text class="text-[36rpx] font-bold text-[#232338]">
          语音设置
        </text>
      </view>

      <!-- 语音设置卡片 -->
      <view class="bg-[#fbfbfb] rounded-[20rpx] mb-[24rpx] p-[24rpx] border border-[#eeeeee]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <view class="flex flex-col gap-[16rpx]">
          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('tts')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              语音合成
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.tts }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee] cursor-pointer transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('voiceprint')">
            <text class="text-[28rpx] text-[#232338] font-medium">
              角色音色
            </text>
            <text class="flex-1 text-right text-[26rpx] text-[#65686f] mx-[16rpx]">
              {{ displayNames.voiceprint }}
            </text>
            <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
          </view>

          <view class="flex items-center justify-between p-[20rpx] bg-[#f5f7fb] rounded-[12rpx] border border-[#eeeeee]">
            <view class="text-[28rpx] text-[#232338] font-medium">
              插件
            </view>
            <view class="px-[24rpx] py-[12rpx] bg-[rgba(51,108,255,0.1)] text-[#336cff] rounded-[20rpx] text-[24rpx] cursor-pointer transition-all duration-300 active:bg-[#336cff] active:text-white" @click="handleTools">
              <text>编辑功能</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 记忆历史标题 -->
      <view class="pb-[20rpx]">
        <text class="text-[36rpx] font-bold text-[#232338]">
          历史记忆
        </text>
      </view>

      <!-- 记忆历史卡片 -->
      <view class="bg-[#fbfbfb] rounded-[20rpx] mb-[24rpx] p-[24rpx] border border-[#eeeeee]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <view class="mb-[24rpx] last:mb-0">
          <textarea
            v-model="formData.summaryMemory"
            placeholder="记忆内容"
            disabled
            class="w-full h-[500rpx] p-[20rpx] bg-[#f0f0f0] text-[#65686f] opacity-80 rounded-[12rpx] border border-[#eeeeee] text-[26rpx] leading-[1.6] resize-none box-border outline-none break-words break-all"
          />
        </view>
      </view>

      <!-- 保存按钮 -->
      <view class="p-0 mt-[40rpx]">
        <wd-button
          type="primary"
          :loading="saving"
          :disabled="saving"
          custom-class="w-full h-[80rpx] rounded-[16rpx] text-[30rpx] font-semibold bg-[#336cff] active:bg-[#2d5bd1]"
          @click="saveAgent"
        >
          {{ saving ? '保存中...' : '保存' }}
        </wd-button>
      </view>
    </scroll-view>
    <!-- 模型选择器 -->
    <wd-action-sheet
      v-model="pickerShow.vad"
      :actions="modelOptions.VAD && modelOptions.VAD.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('vad')"
      @select="({ item }) => onPickerConfirm('vad', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.asr"
      :actions="modelOptions.ASR && modelOptions.ASR.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('asr')"
      @select="({ item }) => onPickerConfirm('asr', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.llm"
      :actions="modelOptions.LLM && modelOptions.LLM.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('llm')"
      @select="({ item }) => onPickerConfirm('llm', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.vllm"
      :actions="modelOptions.VLLM && modelOptions.VLLM.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('vllm')"
      @select="({ item }) => onPickerConfirm('vllm', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.intent"
      :actions="modelOptions.Intent && modelOptions.Intent.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('intent')"
      @select="({ item }) => onPickerConfirm('intent', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.memory"
      :actions="modelOptions.Memory && modelOptions.Memory.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('memory')"
      @select="({ item }) => onPickerConfirm('memory', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.tts"
      :actions="modelOptions.TTS && modelOptions.TTS.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('tts')"
      @select="({ item }) => onPickerConfirm('tts', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.voiceprint"
      :actions="voiceOptions && voiceOptions.map(item => ({ name: item.name, value: item.id }))"
      @close="onPickerCancel('voiceprint')"
      @select="({ item }) => onPickerConfirm('voiceprint', item.value, item.name)"
    />

    <!-- 智能体选择器 -->
    <wd-action-sheet
      v-model="showAgentPicker"
      :actions="agentOptions"
      title="切换智能体"
      @close="closeAgentSelector"
      @select="handleAgentSwitch"
    />
  </view>
</template>