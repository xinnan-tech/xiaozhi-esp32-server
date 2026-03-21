<script lang="ts" setup>
import type { AgentDetail, ModelOption, PluginDefinition, RoleTemplate } from '@/api/agent/types'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { getAgentDetail, getAgentTags, getAllLanguage, getModelOptions, getPluginFunctions, getRoleTemplates, updateAgent, updateAgentTags } from '@/api/agent/agent'
import { t } from '@/i18n'
import { usePluginStore, useProvider, useSpeedPitch } from '@/store'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'AgentEdit',
})

const props = withDefaults(defineProps<Props>(), {
  agentId: '',
})

// 组件参数
interface Props {
  agentId?: string
}

const agentId = computed(() => props.agentId)

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
  ttsLanguage: '',
  ttsVolume: 0,
  ttsRate: 0,
  ttsPitch: 0,
})

// 显示名称数据
const displayNames = ref({
// 显示名称数据
  vad: t('agent.pleaseSelect'),
  asr: t('agent.pleaseSelect'),
  llm: t('agent.pleaseSelect'),
  vllm: t('agent.pleaseSelect'),
  intent: t('agent.pleaseSelect'),
  memory: t('agent.pleaseSelect'),
  tts: t('agent.pleaseSelect'),
  voiceprint: t('agent.pleaseSelect'),
  report: t('agent.pleaseSelect'),
  language: t('agent.pleaseSelect'),
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
const voiceOptions = ref([])
// 保存完整的音色信息
const voiceDetails = ref({})

// 上报模式选项数据
const reportOptions = [
  { name: t('agent.reportText'), value: 1 },
  { name: t('agent.reportTextVoice'), value: 2 },
]

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
  language: false,
  report: false,
})

const allFunctions = ref<PluginDefinition[]>([])
const dynamicTags = ref([])
const inputValue = ref('')
const inputVisible = ref(false)
const languageOptions = ref([])
const isVisibleReport = ref(false)

// 音频播放相关
const audioRef = ref<UniApp.InnerAudioContext | null>(null)
const playingVoiceId = ref<string>('')

// 使用插件store
const pluginStore = usePluginStore()
const speedPitchStore = useSpeedPitch()
const providerStore = useProvider()

// tabs
const tabList = [
  {
    label: '角色配置',
    value: 'home',
    icon: '/static/tabbar/robot.png',
    activeIcon: '/static/tabbar/robot_activate.png',
  },
  {
    label: '设备管理',
    value: 'category',
    icon: '/static/tabbar/device.png',
    activeIcon: '/static/tabbar/device_activate.png',
  },
  {
    label: '聊天记录',
    value: 'settings',
    icon: '/static/tabbar/chat.png',
    activeIcon: '/static/tabbar/chat_activate.png',
  },
  {
    label: '声纹管理',
    value: 'profile',
    icon: '/static/tabbar/voiceprint.png',
    activeIcon: '/static/tabbar/voiceprint_activate.png',
  },
]
function handleCloseTag(id: string) {
  dynamicTags.value = dynamicTags.value.filter(tag => tag.id !== id)
}

function showInput() {
  inputVisible.value = true
}

function handleInputConfirm() {
  if (inputValue.value) {
    dynamicTags.value.push({ id: new Date().getTime(), tagName: inputValue.value.trim() })
    inputValue.value = ''
  }
  inputVisible.value = false
}

// 打开上下文源编辑弹窗
function openContextProviderDialog() {
  uni.navigateTo({
    url: '/pages/agent/provider',
  })
}

function handleRegulate() {
  uni.navigateTo({
    url: '/pages/agent/speedPitch',
  })
}

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

    // 更新语速音调
    speedPitchStore.updateSpeedPitch({
      ttsVolume: detail.ttsVolume || 0,
      ttsRate: detail.ttsRate || 0,
      ttsPitch: detail.ttsPitch || 0,
    })

    // 加载上下文配置
    providerStore.updateProviders(detail.contextProviders || [])

    // 如果有TTS模型，加载对应的音色选项
    if (detail.ttsModelId) {
      await fetchAllLanguag(detail.ttsModelId)
    }

    // 等待模型选项加载完成后再更新显示名称
    await nextTick()
    updateDisplayNames()
  }
  catch (error) {
    console.error('加载智能体详情失败:', error)
    toast.error(t('agent.loadFail'))
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
  displayNames.value.report = reportOptions.find(item => item.value === formData.value.chatHistoryConf)?.name
  displayNames.value.language = formData.value.ttsLanguage

  isVisibleReport.value = formData.value.memModelId !== 'Memory_nomem'

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

// 根据语言筛选音色
function filterVoicesByLanguage() {
  if (!voiceDetails.value || Object.keys(voiceDetails.value).length === 0) {
    voiceOptions.value = []
    return
  }

  const allVoices = Object.values(voiceDetails.value) as any[]

  // 根据选中的语言筛选音色
  const filteredVoices = allVoices.filter((voice) => {
    if (!voice.languages) {
      return false
    }
    const languagesArray = voice.languages.split(/[、；;,，]/).map(lang => lang.trim()).filter(lang => lang)
    return languagesArray.includes(formData.value.language)
  })

  voiceOptions.value = filteredVoices.map(voice => ({
    value: voice.id,
    name: voice.name,
    voiceDemo: voice.voiceDemo,
    voice_demo: voice.voice_demo,
    isClone: Boolean(voice.isClone),
    train_status: voice.trainStatus,
  }))

  // 检查当前选中的音色是否支持当前语言，如果不支持则选择第一个
  const currentVoiceSupportsLanguage = formData.value.ttsVoiceId
    && filteredVoices.some(voice => voice.id === formData.value.ttsVoiceId)

  if (!currentVoiceSupportsLanguage) {
    formData.value.ttsVoiceId = filteredVoices.length > 0 ? filteredVoices[0].id : ''
    displayNames.value.voiceprint = filteredVoices.length > 0 ? filteredVoices[0].name : ''
  }
  else {
    displayNames.value.voiceprint = filteredVoices.find(item => item.id === formData.value.ttsVoiceId)?.name
  }

  // 同步到ttsSettings（如果值为null，使用0作为显示默认值，但不修改form中的值）
  speedPitchStore.updateSpeedPitch({
    ttsVolume: formData.value.ttsVolume !== null && formData.value.ttsVolume !== undefined ? formData.value.ttsVolume : 0,
    ttsRate: formData.value.ttsRate !== null && formData.value.ttsRate !== undefined ? formData.value.ttsRate : 0,
    ttsPitch: formData.value.ttsPitch !== null && formData.value.ttsPitch !== undefined ? formData.value.ttsPitch : 0,
  })
}

// 根据语音合成模型加载语言
async function fetchAllLanguag(ttsModelId: string) {
  try {
    const res = await getAllLanguage(ttsModelId)
    // 保存完整的音色信息
    voiceDetails.value = res.reduce((acc, voice) => {
      acc[voice.id] = voice
      return acc
    }, {})
    // 提取所有语言选项并去重
    const allLanguages = new Set()
    res.forEach((voice) => {
      if (voice.languages) {
        const languagesArray = voice.languages.split(/[、；;,，]/).map(lang => lang.trim()).filter(lang => lang)
        languagesArray.forEach(lang => allLanguages.add(lang))
      }
    })
    languageOptions.value = Array.from(allLanguages).map(lang => ({
      value: lang,
      name: lang,
    }))

    // 使用后端返回的用户选择的语言，如果没有则使用第一个语言选项
    if (formData.value.ttsLanguage && languageOptions.value.some(option => option.value === formData.value.ttsLanguage)) {
      formData.value.language = formData.value.ttsLanguage
      displayNames.value.language = formData.value.ttsLanguage
    }
    else if (languageOptions.value.length > 0) {
      formData.value.language = languageOptions.value[0].value
      displayNames.value.language = languageOptions.value[0].value
    }

    // 根据选中的语言筛选音色
    filterVoicesByLanguage()
  }
  catch {
    languageOptions.value = []
  }
}

// 加载TTS音色选项
// async function loadVoiceOptions(ttsModelId?: string) {
//   if (!ttsModelId)
//     return

//   try {
//     console.log(`加载音色选项: ${ttsModelId}`)
//     const voices = await getTTSVoices(ttsModelId)
//     voiceOptions.value = voices
//     console.log('音色选项:', voices)
//   }
//   catch (error) {
//     console.error('加载音色选项失败:', error)
//     voiceOptions.value = []
//   }
// }

// 选择角色模板
function selectRoleTemplate(templateId: string) {
  if (selectedTemplateId.value === templateId) {
    selectedTemplateId.value = ''
    return
  }

  selectedTemplateId.value = templateId
  const template = roleTemplates.value.find(t => t.id === templateId)
  if (template) {
    formData.value = {
      ...formData.value,
      systemPrompt: template.systemPrompt || formData.value.systemPrompt,
      vadModelId: template.vadModelId || formData.value.vadModelId,
      asrModelId: template.asrModelId || formData.value.asrModelId,
      llmModelId: template.llmModelId || formData.value.llmModelId,
      vllmModelId: template.vllmModelId || formData.value.vllmModelId,
      intentModelId: template.intentModelId || formData.value.intentModelId,
      memModelId: template.memModelId || formData.value.memModelId,
      ttsModelId: template.ttsModelId || formData.value.ttsModelId,
      ttsVoiceId: template.ttsVoiceId || formData.value.ttsVoiceId,
      agentName: template.agentName || formData.value.agentName,
      chatHistoryConf: template.chatHistoryConf || formData.value.chatHistoryConf,
      summaryMemory: template.summaryMemory || formData.value.summaryMemory,
      langCode: template.langCode || formData.value.langCode,
    }
    fetchAllLanguag(template.ttsModelId || formData.value.ttsModelId)
    updateDisplayNames()
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
      formData.value.chatHistoryConf = value === 'Memory_nomem' ? 0 : 2
      displayNames.value.memory = name // 确保显示名称正确更新
      displayNames.value.report = reportOptions[1].name
      isVisibleReport.value = value !== 'Memory_nomem'
      break
    case 'tts':
      formData.value.ttsModelId = value
      await fetchAllLanguag(value)
      break
    case 'language':
      formData.value.language = value
      filterVoicesByLanguage()
      break
    case 'voiceprint':
      formData.value.ttsVoiceId = value
      displayNames.value.voiceprint = name // 确保显示名称正确更新
      break
    case 'report':
      formData.value.chatHistoryConf = value
      break
  }

  pickerShow.value[type] = false
}

// 选择器取消
function onPickerCancel(type: string) {
  pickerShow.value[type] = false
  // 关闭时停止播放
  if (type === 'voiceprint') {
    stopAudio()
  }
}

// 播放音频
function playAudio(voiceDemo: string, voiceId: string, event: Event) {
  event.stopPropagation() // 阻止事件冒泡，防止关闭下拉框

  if (!voiceDemo) {
    return
  }

  // 如果正在播放同一个音频，则停止
  if (playingVoiceId.value === voiceId) {
    stopAudio()
    return
  }

  // 停止之前的音频
  stopAudio()

  // 创建新的音频实例
  audioRef.value = uni.createInnerAudioContext()
  audioRef.value.src = voiceDemo
  playingVoiceId.value = voiceId

  // 监听播放结束
  audioRef.value.onEnded(() => {
    playingVoiceId.value = ''
  })

  // 监听播放错误
  audioRef.value.onError(() => {
    toast.error('音频播放失败')
    playingVoiceId.value = ''
  })

  // 播放音频
  audioRef.value.play()
}

// 停止音频
function stopAudio() {
  if (audioRef.value) {
    audioRef.value.stop()
    audioRef.value.destroy()
    audioRef.value = null
  }
  playingVoiceId.value = ''
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
    toast.warning(t('agent.pleaseInputAgentName'))
    return
  }

  if (!formData.value.systemPrompt?.trim()) {
    toast.warning(t('agent.pleaseInputRoleDescription'))
    return
  }

  try {
    await handleUpdateAgentTags()
  }
  catch (err) {
    toast.error(err)
    return
  }

  try {
    saving.value = true
    // 构建保存数据，包含上下文配置和语音设置
    const saveData = {
      ...formData.value,
      ...speedPitchStore.speedPitch,
      ttsLanguage: formData.value.language,
      contextProviders: providerStore.providers,
    }
    await updateAgent(agentId.value, saveData)
    loadAgentDetail()

    toast.success(t('agent.saveSuccess'))
  }
  catch (error) {
    console.error('保存失败:', error)
    toast.error(t('agent.saveFail'))
  }
  finally {
    saving.value = false
  }
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

// 获取智能体标签
async function loadAgentTags() {
  try {
    const res = await getAgentTags(agentId.value)
    dynamicTags.value = res || []
  }
  catch (error) {}
}

// 更新智能体标签
async function handleUpdateAgentTags() {
  const tagNames = dynamicTags.value.map(tag => tag.tagName)
  await updateAgentTags(agentId.value, { tagNames })
}

// 监听store中的插件配置变化
watch(() => pluginStore.currentFunctions, (newFunctions) => {
  formData.value.functions = newFunctions
}, { deep: true })

onMounted(async () => {
  loadAgentTags()

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
  <view class="bg-[#f5f7fb] px-[20rpx]">
    <!-- 基础信息标题
    <view class="pb-[20rpx] first:pt-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        {{ t('agent.basicInfo') }}
      </text>
    </view -->

    <!-- 基础信息卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          {{ t('agent.agentName') }}
        </text>
        <input
          v-model="formData.agentName"
          class="box-border h-[80rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          type="text"
          :placeholder="t('agent.inputAgentName')"
        >
      </view>

      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          {{ t('agent.agentTag') }}
        </text>
        <input
          v-if="inputVisible"
          v-model="inputValue"
          class="mb-[10rpx] box-border h-[80rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          type="text"
          :maxlength="20"
          :placeholder="t('agent.inputAgentTag')"
          @keyup.enter="handleInputConfirm"
          @blur="handleInputConfirm"
        >
        <view class="flex flex-wrap gap-[10rpx_10rpx]">
          <wd-tag v-for="tag in dynamicTags" :key="tag.id" class="items-center border !flex !border-[rgba(51,108,255,0.2)] !bg-[rgba(51,108,255,0.1)] !text-[#336cff]" round closable @close="handleCloseTag(tag.id)">
            {{ tag.tagName }}
          </wd-tag>
          <wd-button v-if="!inputVisible" class="!bg-[rgba(51,108,255,0.1)] !text-[#336cff]" size="small" icon="add" @click="showInput">
            {{ t('agent.addAgentTag') }}
          </wd-button>
        </view>
      </view>

      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          {{ t('agent.roleMode') }}
        </text>
        <view class="mt-0 flex flex-wrap gap-[12rpx]">
          <view
            v-for="template in roleTemplates"
            :key="template.id"
            class="cursor-pointer rounded-[20rpx] px-[24rpx] py-[12rpx] text-[24rpx] transition-all duration-300"
            :class="selectedTemplateId === template.id
              ? 'bg-[#336cff] text-white border border-[#336cff]'
              : 'bg-[rgba(51,108,255,0.1)] text-[#336cff] border border-[rgba(51,108,255,0.2)]'"
            @click="selectRoleTemplate(template.id)"
          >
            {{ template.agentName }}
          </view>
        </view>
      </view>

      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          {{ t('agent.contextProvider') }}
        </text>
        <view class="mt-0 flex flex-wrap items-center gap-[12rpx]">
          <text class="text-[26rpx] text-[#65686f]">
            {{ t('agent.contextProviderSuccess', { count: providerStore.providers.length }) }}
          </text>
          <a class="text-[26rpx] text-[#5778ff] no-underline" href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/context-provider-integration.md" target="_blank">
            {{ t('agent.contextProviderDocLink') }}
          </a>
          <wd-button class="!bg-[rgba(51,108,255,0.1)] !text-[#336cff]" size="small" @click="openContextProviderDialog">
            {{ t('agent.editContextProvider') }}
          </wd-button>
        </view>
      </view>

      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          {{ t('agent.roleDescription') }}
        </text>
        <textarea
          v-model="formData.systemPrompt"
          :maxlength="2000"
          :placeholder="t('agent.inputRoleDescription')"
          class="box-border h-[500rpx] w-full resize-none break-words break-all border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] text-[26rpx] text-[#232338] leading-[1.6] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
        />
        <view class="mt-[8rpx] text-right text-[22rpx] text-[#9d9ea3]">
          {{ (formData.systemPrompt || '').length }}/2000
        </view>
      </view>
    </view>

    <!-- 模型配置标题 -->
    <view class="pb-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        {{ t('agent.modelConfig') }}
      </text>
    </view>

    <!-- 模型配置卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="flex flex-col gap-[16rpx]">
        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('vad')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.vad') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.vad }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('asr')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.asr') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.asr }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('llm')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.llm') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.llm }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('vllm')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.vllm') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.vllm }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('intent')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.intent') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.intent }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('memory')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.memory') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.memory }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view v-show="isVisibleReport" class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('report')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.reportMode') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.report }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>
      </view>
    </view>

    <!-- 语音设置标题 -->
    <view class="pb-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        {{ t('agent.voiceSettings') }}
      </text>
    </view>

    <!-- 语音设置卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="flex flex-col gap-[16rpx]">
        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('tts')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.tts') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.tts }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('language')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.language') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.language }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('voiceprint')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.voiceprint') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.voiceprint }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx]">
          <view class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.languageConfig') }}
          </view>
          <view class="cursor-pointer rounded-[20rpx] bg-[rgba(51,108,255,0.1)] px-[24rpx] py-[12rpx] text-[24rpx] text-[#336cff] transition-all duration-300 active:bg-[#336cff] active:text-white" @click="handleRegulate">
            <text>{{ t('agent.editFunctions') }}</text>
          </view>
        </view>

        <view class="flex items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx]">
          <view class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.plugins') }}
          </view>
          <view class="cursor-pointer rounded-[20rpx] bg-[rgba(51,108,255,0.1)] px-[24rpx] py-[12rpx] text-[24rpx] text-[#336cff] transition-all duration-300 active:bg-[#336cff] active:text-white" @click="handleTools">
            <text>{{ t('agent.editFunctions') }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 记忆历史标题 -->
    <view class="pb-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        {{ t('agent.historyMemory') }}
      </text>
    </view>

    <!-- 记忆历史卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="mb-[24rpx] last:mb-0">
        <textarea
          v-model="formData.summaryMemory"
          :placeholder="t('agent.memoryContent')"
          disabled
          class="box-border h-[500rpx] w-full resize-none break-words break-all border border-[#eeeeee] rounded-[12rpx] bg-[#f0f0f0] p-[20rpx] text-[26rpx] text-[#65686f] leading-[1.6] opacity-80 outline-none"
        />
      </view>
    </view>

    <!-- 保存按钮 -->
    <view class="mt-[40rpx] p-0">
      <wd-button
        type="primary"
        :loading="saving"
        :disabled="saving"
        custom-class="w-full h-[80rpx] rounded-[16rpx] text-[30rpx] font-semibold bg-[#336cff] active:bg-[#2d5bd1]"
        @click="saveAgent"
      >
        {{ saving ? t('agent.saving') : t('agent.save') }}
      </wd-button>
    </view>
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
      class="custom-sheet-tts"
      @close="onPickerCancel('tts')"
      @select="({ item }) => onPickerConfirm('tts', item.value, item.name)"
    />

    <!-- 自定义语音选择弹出层 -->
    <wd-popup v-model="pickerShow.voiceprint" class="custom-popup" position="bottom" @close="onPickerCancel('voiceprint')">
      <view class="overflow-hidden rounded-[20rpx] bg-white pb-[20rpx] pt-[20rpx]">
        <view class="max-h-[600rpx] overflow-y-auto">
          <view
            v-for="voice in voiceOptions"
            :key="voice.value"
            class="flex items-center justify-between border-b border-[#f5f5f5] p-[32rpx] transition-all active:bg-[#f5f7fb]"
            @click="onPickerConfirm('voiceprint', voice.value, voice.name)"
          >
            <text :class="`flex-1 text-[28rpx] text-[#232338] ${(voice.voiceDemo || voice.voice_demo) ? '' : 'text-center'}`">
              {{ voice.name }}
            </text>
            <view v-if="voice.voiceDemo || voice.voice_demo" class="ml-[20rpx]" @click.stop="playAudio(voice.voiceDemo || voice.voice_demo, voice.value, $event)">
              <wd-icon
                :name="playingVoiceId === voice.value ? 'pause-circle' : 'play-circle'"
                size="24px"
                :custom-class="playingVoiceId === voice.value ? 'text-[#336cff]' : 'text-[#9d9ea3]'"
              />
            </view>
          </view>
        </view>
      </view>
    </wd-popup>
    <wd-action-sheet
      v-model="pickerShow.language"
      :actions="languageOptions"
      @close="onPickerCancel('language')"
      @select="({ item }) => onPickerConfirm('language', item.value, item.name)"
    />
    <wd-action-sheet
      v-model="pickerShow.report"
      :actions="reportOptions"
      @close="onPickerCancel('report')"
      @select="({ item }) => onPickerConfirm('report', item.value, item.name)"
    />
  </view>
</template>

<style lang="scss" scoped>
::v-deep .wd-tag__close {
  color: #336cff !important;
}
::v-deep .custom-popup {
  .wd-popup {
    padding: 20rpx !important;
    background: transparent !important;
  }
}
::v-deep .custom-sheet-tts {
  .wd-action-sheet {
    padding: 8px 0 !important;
    overflow: hidden;
  }
  .wd-action-sheet__actions {
    padding: 0 !important;
  }
}
</style>
