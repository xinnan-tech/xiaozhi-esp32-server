<script lang="ts" setup>
import type { AgentDetail, ModelOption, PluginDefinition, RoleTemplate, TtsVoice } from '@/api/agent/types'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { getAgentDetail, getAgentTags, getAllLanguage, getModelOptions, getPluginFunctions, getRoleTemplates, getVoiceCloneAudioId, updateAgent } from '@/api/agent/agent'
import { t } from '@/i18n'
import { usePluginStore, useProvider, useSpeedPitch } from '@/store'
import { getEnvBaseUrl } from '@/utils'
import { toast } from '@/utils/toast'
import AgentSnapshotPanel from './components/AgentSnapshotPanel.vue'
import { filterTtsVoicesByLanguage, hasUsableTtsVoiceMetadata } from './components/agentSnapshotUtils.mjs'
import { createVoicePreviewRequestGate, hasVoicePreview, resolveVoicePreviewUrl } from './components/voicePreviewUtils.mjs'

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
  slmModelId: '',
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
  slm: t('agent.pleaseSelect'),
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
const showSnapshotPanel = ref(false)
const currentVersionNo = ref<number | null>(null)
const snapshotReloadBlocked = ref(false)
const snapshotReloadFailed = ref(false)

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

interface VoiceOption {
  id?: string
  value: string
  name: string
  voiceDemo?: string | null
  voice_demo?: string | null
  isClone: boolean
  train_status?: number
}

// 音色选项数据
const voiceOptions = ref<VoiceOption[]>([])
// 保存完整的音色信息
const voiceDetails = ref<Record<string, TtsVoice>>({})

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
  slm: false,
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
const languageOptions = ref<any[]>([])
const isVisibleReport = ref(false)
const tempSummaryMemory = ref('')
const selectedTtsLanguage = ref('')
const ttsLanguageTouched = ref(false)
const ttsVoiceTouched = ref(false)
const ttsOptionsLoading = ref(false)
const ttsOptionsModelId = ref('')
const originalTagNames = ref<string[]>([])
const originalAgentDetail = ref<AgentDetail | null>(null)
let ttsOptionsRequestSequence = 0
let agentDetailRequestSequence = 0
let agentTagRequestSequence = 0
let snapshotReloadSequence = 0

interface SnapshotRestoreContext {
  agentId: string
  actionSequence: number
}

// 音频播放相关
const audioRef = ref<UniApp.InnerAudioContext | null>(null)
const playingVoiceId = ref<string>('')
const voicePreviewRequestGate = createVoicePreviewRequestGate()

// 使用插件store
const pluginStore = usePluginStore()
const speedPitchStore = useSpeedPitch()
const providerStore = useProvider()

const EDITABLE_AGENT_FIELDS: Array<keyof AgentDetail> = [
  'agentName',
  'systemPrompt',
  'summaryMemory',
  'vadModelId',
  'asrModelId',
  'llmModelId',
  'slmModelId',
  'vllmModelId',
  'intentModelId',
  'memModelId',
  'ttsModelId',
  'chatHistoryConf',
  'langCode',
  'language',
  'sort',
]

const hasUnsavedChanges = computed(() => {
  if (loading.value || !originalAgentDetail.value) {
    return false
  }
  return stableSerialize(buildCurrentEditableState()) !== stableSerialize(buildOriginalEditableState())
})

function buildCurrentEditableState() {
  const original = originalAgentDetail.value as AgentDetail
  const current = formData.value as Record<string, any>
  const changedTtsFields = new Set(speedPitchStore.changedFields)
  return {
    ...pickEditableFields(current),
    ttsLanguage: ttsLanguageTouched.value ? selectedTtsLanguage.value : original.ttsLanguage,
    ttsVoiceId: ttsVoiceTouched.value ? current.ttsVoiceId : original.ttsVoiceId,
    ttsVolume: changedTtsFields.has('ttsVolume') ? speedPitchStore.speedPitch.ttsVolume : original.ttsVolume,
    ttsRate: changedTtsFields.has('ttsRate') ? speedPitchStore.speedPitch.ttsRate : original.ttsRate,
    ttsPitch: changedTtsFields.has('ttsPitch') ? speedPitchStore.speedPitch.ttsPitch : original.ttsPitch,
    functions: normalizeAgentFunctions(current.functions || []),
    contextProviders: providerStore.providers,
    tagNames: dynamicTags.value.map((tag: any) => tag.tagName).filter(Boolean).sort(),
  }
}

function buildOriginalEditableState() {
  const original = originalAgentDetail.value as AgentDetail
  return {
    ...pickEditableFields(original as unknown as Record<string, any>),
    ttsLanguage: original.ttsLanguage,
    ttsVoiceId: original.ttsVoiceId,
    ttsVolume: original.ttsVolume,
    ttsRate: original.ttsRate,
    ttsPitch: original.ttsPitch,
    functions: normalizeAgentFunctions(original.functions || []),
    contextProviders: original.contextProviders || [],
    tagNames: [...originalTagNames.value].sort(),
  }
}

function pickEditableFields(data: Record<string, any>) {
  return EDITABLE_AGENT_FIELDS.reduce<Record<string, any>>((result, field) => {
    result[field] = data[field]
    return result
  }, {})
}

function stableSerialize(value: any) {
  return JSON.stringify(sortObjectKeys(value))
}

function sortObjectKeys(value: any): any {
  if (Array.isArray(value)) {
    return value.map(sortObjectKeys)
  }
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce<Record<string, any>>((result, key) => {
      result[key] = sortObjectKeys(value[key])
      return result
    }, {})
  }
  return value
}

function cloneSerializable<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

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

// 是否禁用历史记忆输入框
const isMemoryDisabled = computed(() => formData.value.memModelId !== 'Memory_mem_local_short')

function normalizeFunctionParams(paramInfo: any) {
  if (!paramInfo)
    return {}
  if (typeof paramInfo === 'string') {
    try {
      const parsed = JSON.parse(paramInfo)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    }
    catch {
      return {}
    }
  }
  return typeof paramInfo === 'object' && !Array.isArray(paramInfo) ? { ...paramInfo } : {}
}

function normalizeAgentFunctions(functions: any[] = []) {
  return functions.map(item => ({
    ...item,
    paramInfo: normalizeFunctionParams(item.paramInfo),
  }))
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
async function loadAgentDetail(targetAgentId = agentId.value) {
  if (!targetAgentId)
    return false

  const requestId = ++agentDetailRequestSequence
  invalidateTtsMetadataRequest()
  try {
    loading.value = true
    const detail = await getAgentDetail(targetAgentId)
    if (!isActiveAgentDetailRequest(targetAgentId, requestId)) {
      return false
    }
    applyPersistedAgentDetail(detail, targetAgentId)
    await enhanceAgentDetailMetadata(detail, targetAgentId, requestId)
    return isActiveAgentDetailRequest(targetAgentId, requestId)
  }
  catch (error) {
    if (isActiveAgentDetailRequest(targetAgentId, requestId)) {
      console.error('加载智能体详情失败:', error)
      toast.error(t('agent.loadFail'))
    }
    return false
  }
  finally {
    if (isActiveAgentDetailRequest(targetAgentId, requestId)) {
      loading.value = false
    }
  }
}

function applyPersistedAgentDetail(detail: AgentDetail, targetAgentId: string) {
  const normalizedFunctions = normalizeAgentFunctions(detail.functions || [])
  tempSummaryMemory.value = ''
  ttsLanguageTouched.value = false
  ttsVoiceTouched.value = false
  ttsOptionsModelId.value = ''
  voiceOptions.value = []
  voiceDetails.value = {}
  languageOptions.value = []
  formData.value = { ...detail, functions: normalizedFunctions }
  originalAgentDetail.value = cloneSerializable({ ...detail, functions: normalizedFunctions })
  currentVersionNo.value = detail.currentVersionNo || null
  selectedTtsLanguage.value = detail.ttsLanguage || ''

  pluginStore.setCurrentAgentId(targetAgentId)
  pluginStore.setCurrentFunctions(normalizedFunctions)
  speedPitchStore.updateSpeedPitch({
    ttsVolume: detail.ttsVolume ?? 0,
    ttsRate: detail.ttsRate ?? 0,
    ttsPitch: detail.ttsPitch ?? 0,
  })
  speedPitchStore.resetChangedFields()
  providerStore.updateProviders(detail.contextProviders || [])
}

async function enhanceAgentDetailMetadata(detail: AgentDetail, targetAgentId: string, requestId: number) {
  try {
    if (detail.ttsModelId) {
      await fetchAllLanguag(detail.ttsModelId, {
        preferredLanguage: detail.ttsLanguage,
        preferredVoiceId: detail.ttsVoiceId,
      })
    }
    else {
      voiceOptions.value = []
      voiceDetails.value = {}
      languageOptions.value = []
      selectedTtsLanguage.value = ''
    }
    await nextTick()
    if (isActiveAgentDetailRequest(targetAgentId, requestId)) {
      updateDisplayNames()
    }
  }
  catch (error) {
    // Persisted agent detail has already loaded successfully. Voice metadata is
    // display enhancement only and must not keep the post-restore save barrier.
    console.warn('Failed to enhance agent detail metadata:', error)
  }
}

function isActiveAgentDetailRequest(targetAgentId: string, requestId: number) {
  return targetAgentId === agentId.value && requestId === agentDetailRequestSequence
}

function invalidateTtsMetadataRequest() {
  ttsOptionsRequestSequence += 1
  ttsOptionsLoading.value = false
  ttsOptionsModelId.value = ''
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
  displayNames.value.slm = getModelDisplayName('LLM', formData.value.slmModelId)
  displayNames.value.vllm = getModelDisplayName('VLLM', formData.value.vllmModelId)
  displayNames.value.intent = getModelDisplayName('Intent', formData.value.intentModelId)
  displayNames.value.memory = getModelDisplayName('Memory', formData.value.memModelId)
  displayNames.value.tts = getModelDisplayName('TTS', formData.value.ttsModelId)

  // 角色音色特殊处理
  displayNames.value.report = reportOptions.find(item => item.value === formData.value.chatHistoryConf)?.name

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
interface VoiceSelectionOptions {
  autoSelectVoice?: boolean
  preferredLanguage?: string | null
  preferredVoiceId?: string | null
}

interface TtsSelectionState {
  modelId: string
  voiceId: string
  language: string
  selectedLanguage: string
  languageTouched: boolean
  voiceTouched: boolean
  optionsModelId: string
  voiceOptions: VoiceOption[]
  voiceDetails: Record<string, TtsVoice>
  languageOptions: any[]
  displayNames: {
    tts: string
    voiceprint: string
    language: string
  }
}

function captureTtsSelectionState(): TtsSelectionState {
  return {
    modelId: formData.value.ttsModelId || '',
    voiceId: formData.value.ttsVoiceId || '',
    language: formData.value.ttsLanguage || '',
    selectedLanguage: selectedTtsLanguage.value,
    languageTouched: ttsLanguageTouched.value,
    voiceTouched: ttsVoiceTouched.value,
    optionsModelId: ttsOptionsModelId.value,
    voiceOptions: voiceOptions.value,
    voiceDetails: voiceDetails.value,
    languageOptions: languageOptions.value,
    displayNames: {
      tts: displayNames.value.tts,
      voiceprint: displayNames.value.voiceprint,
      language: displayNames.value.language,
    },
  }
}

function restoreTtsSelectionState(state: TtsSelectionState) {
  formData.value.ttsModelId = state.modelId
  formData.value.ttsVoiceId = state.voiceId
  formData.value.ttsLanguage = state.language
  selectedTtsLanguage.value = state.selectedLanguage
  ttsLanguageTouched.value = state.languageTouched
  ttsVoiceTouched.value = state.voiceTouched
  ttsOptionsModelId.value = state.optionsModelId
  voiceOptions.value = state.voiceOptions
  voiceDetails.value = state.voiceDetails
  languageOptions.value = state.languageOptions
  displayNames.value.tts = state.displayNames.tts
  displayNames.value.voiceprint = state.displayNames.voiceprint
  displayNames.value.language = state.displayNames.language
}

function filterVoicesByLanguage(options: VoiceSelectionOptions = {}) {
  if (!voiceDetails.value || Object.keys(voiceDetails.value).length === 0) {
    voiceOptions.value = []
    return
  }

  const allVoices = Object.values(voiceDetails.value)

  // 根据选中的语言筛选音色
  const filteredVoices = filterTtsVoicesByLanguage(allVoices, selectedTtsLanguage.value)

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

  if (!currentVoiceSupportsLanguage && options.autoSelectVoice) {
    formData.value.ttsVoiceId = filteredVoices.length > 0 ? filteredVoices[0].id : ''
    displayNames.value.voiceprint = filteredVoices.length > 0 ? filteredVoices[0].name : ''
    ttsVoiceTouched.value = true
  }
  else {
    displayNames.value.voiceprint = filteredVoices.find(item => item.id === formData.value.ttsVoiceId)?.name
      || getVoiceDisplayName(formData.value.ttsVoiceId)
  }
}

function getVoiceDefaultLanguage(ttsVoiceId: string) {
  if (!ttsVoiceId || !voiceDetails.value?.[ttsVoiceId]?.languages) {
    return ''
  }
  const languages = voiceDetails.value[ttsVoiceId].languages
    .split(/[、；;,，]/)
    .map(lang => lang.trim())
    .filter(Boolean)
  return languages[0] || ''
}

// 根据语音合成模型加载语言
async function fetchAllLanguag(ttsModelId: string, options: VoiceSelectionOptions = {}): Promise<'loaded' | 'failed' | 'stale'> {
  const requestId = ++ttsOptionsRequestSequence
  ttsOptionsLoading.value = true
  try {
    const res = await getAllLanguage(ttsModelId)
    if (requestId !== ttsOptionsRequestSequence) {
      return 'stale'
    }
    if (!Array.isArray(res)) {
      throw new TypeError('Invalid TTS voice metadata')
    }
    // An empty response cannot prove that the newly selected model accepts an
    // empty voice. Until the API exposes an explicit "voice optional"
    // capability, keep the previous tuple instead of persisting a guess.
    if (!hasUsableTtsVoiceMetadata(res)) {
      throw new Error('No TTS voice metadata is available')
    }
    // 保存完整的音色信息
    voiceDetails.value = res.reduce<Record<string, TtsVoice>>((acc, voice) => {
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

    const requestedLanguage = options.preferredLanguage
    const preferredVoiceLanguage = options.preferredVoiceId
      ? getVoiceDefaultLanguage(options.preferredVoiceId)
      : ''
    // Do not carry a language from the previous model into a provider which
    // exposes no language dimension.
    selectedTtsLanguage.value = ''
    displayNames.value.language = ''
    // 优先使用调用方指定的语言或音色默认语言，再回退到智能体当前配置
    if (requestedLanguage && languageOptions.value.some(option => option.value === requestedLanguage)) {
      selectedTtsLanguage.value = requestedLanguage
      displayNames.value.language = requestedLanguage
    }
    else if (preferredVoiceLanguage && languageOptions.value.some(option => option.value === preferredVoiceLanguage)) {
      selectedTtsLanguage.value = preferredVoiceLanguage
      displayNames.value.language = preferredVoiceLanguage
    }
    else if (formData.value.ttsLanguage && languageOptions.value.some(option => option.value === formData.value.ttsLanguage)) {
      selectedTtsLanguage.value = formData.value.ttsLanguage
      displayNames.value.language = formData.value.ttsLanguage
    }
    else if (getVoiceDefaultLanguage(formData.value.ttsVoiceId)) {
      selectedTtsLanguage.value = getVoiceDefaultLanguage(formData.value.ttsVoiceId)
      displayNames.value.language = selectedTtsLanguage.value
    }
    else if (languageOptions.value.length > 0) {
      selectedTtsLanguage.value = languageOptions.value[0].value
      displayNames.value.language = languageOptions.value[0].value
    }

    // 根据选中的语言筛选音色
    filterVoicesByLanguage(options)
    ttsOptionsModelId.value = ttsModelId
    return 'loaded'
  }
  catch (error) {
    if (requestId === ttsOptionsRequestSequence) {
      console.error('Failed to load TTS options:', error)
      ttsOptionsModelId.value = ''
    }
    return requestId === ttsOptionsRequestSequence ? 'failed' : 'stale'
  }
  finally {
    if (requestId === ttsOptionsRequestSequence) {
      ttsOptionsLoading.value = false
    }
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
async function selectRoleTemplate(templateId: string) {
  if (ttsOptionsLoading.value) {
    return
  }
  if (selectedTemplateId.value === templateId) {
    selectedTemplateId.value = ''
    return
  }

  selectedTemplateId.value = templateId
  const template = roleTemplates.value.find(t => t.id === templateId)
  if (template) {
    const previousTtsState = captureTtsSelectionState()
    const templateTtsLanguage = template.ttsLanguage?.trim() || ''
    const hasTemplateTtsLanguage = Boolean(templateTtsLanguage)
    formData.value = {
      ...formData.value,
      systemPrompt: template.systemPrompt || formData.value.systemPrompt,
      vadModelId: template.vadModelId || formData.value.vadModelId,
      asrModelId: template.asrModelId || formData.value.asrModelId,
      llmModelId: template.llmModelId || formData.value.llmModelId,
      slmModelId: template.llmModelId || formData.value.slmModelId,
      vllmModelId: template.vllmModelId || formData.value.vllmModelId,
      intentModelId: template.intentModelId || formData.value.intentModelId,
      memModelId: template.memModelId || formData.value.memModelId,
      ttsModelId: template.ttsModelId || formData.value.ttsModelId,
      ttsVoiceId: template.ttsVoiceId || formData.value.ttsVoiceId,
      ttsLanguage: hasTemplateTtsLanguage ? templateTtsLanguage : formData.value.ttsLanguage,
      agentName: template.agentName || formData.value.agentName,
      chatHistoryConf: template.chatHistoryConf || formData.value.chatHistoryConf,
      summaryMemory: template.summaryMemory || formData.value.summaryMemory,
      langCode: template.langCode || formData.value.langCode,
    }
    if (hasTemplateTtsLanguage) {
      selectedTtsLanguage.value = templateTtsLanguage
      displayNames.value.language = templateTtsLanguage
    }
    if (template.ttsModelId || template.ttsVoiceId || hasTemplateTtsLanguage) {
      const result = await fetchAllLanguag(template.ttsModelId || formData.value.ttsModelId, {
        autoSelectVoice: true,
        preferredLanguage: hasTemplateTtsLanguage ? templateTtsLanguage : '',
        preferredVoiceId: template.ttsVoiceId,
      })
      if (result === 'failed') {
        restoreTtsSelectionState(previousTtsState)
        toast.warning(t('agent.ttsOptionsLoadFailed'))
      }
      else if (result === 'loaded') {
        ttsLanguageTouched.value = true
        ttsVoiceTouched.value = true
      }
    }
    updateDisplayNames()
  }
}

// 打开选择器
function openPicker(type: string) {
  if (ttsOptionsLoading.value && (type === 'tts' || type === 'language' || type === 'voiceprint')) {
    return
  }
  pickerShow.value[type] = true
}

// 选择器确认
async function onPickerConfirm(type: string, value: any, name: string) {
  console.log('选择器确认:', type, value, name)

  const previousTtsState = type === 'tts' ? captureTtsSelectionState() : null
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
    case 'slm':
      formData.value.slmModelId = value
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
      if (value === 'Memory_nomem' || value === 'Memory_mem_report_only') {
        tempSummaryMemory.value = formData.value.summaryMemory
        formData.value.summaryMemory = ''
      }
      else if (tempSummaryMemory.value !== '' && formData.value.summaryMemory === '') {
        formData.value.summaryMemory = tempSummaryMemory.value
        tempSummaryMemory.value = ''
      }
      break
    case 'tts': {
      const preferredLanguage = selectedTtsLanguage.value
      formData.value.ttsModelId = value
      formData.value.ttsVoiceId = ''
      const result = await fetchAllLanguag(value, { autoSelectVoice: true, preferredLanguage })
      if (result === 'failed' && previousTtsState) {
        restoreTtsSelectionState(previousTtsState)
        toast.warning(t('agent.ttsOptionsLoadFailed'))
      }
      else if (result === 'loaded') {
        ttsLanguageTouched.value = true
        ttsVoiceTouched.value = true
      }
      break
    }
    case 'language':
      selectedTtsLanguage.value = value
      formData.value.ttsLanguage = value
      ttsLanguageTouched.value = true
      filterVoicesByLanguage({ autoSelectVoice: true })
      break
    case 'voiceprint':
      formData.value.ttsVoiceId = value
      ttsVoiceTouched.value = true
      if (selectedTtsLanguage.value) {
        formData.value.ttsLanguage = selectedTtsLanguage.value
        ttsLanguageTouched.value = true
      }
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
async function playAudio(voice: VoiceOption, event: Event) {
  event.stopPropagation() // 阻止事件冒泡，防止关闭下拉框

  if (!hasVoicePreview(voice)) {
    return
  }

  // 如果正在播放同一个音频，则停止
  if (playingVoiceId.value === voice.value) {
    stopAudio()
    return
  }

  // 停止之前的音频
  stopAudio()
  const requestId = voicePreviewRequestGate.begin()
  playingVoiceId.value = voice.value

  try {
    const audioUrl = await resolveVoicePreviewUrl({
      id: voice.value,
      isClone: voice.isClone,
      voiceDemo: voice.voiceDemo || voice.voice_demo,
    }, getVoiceCloneAudioId, getEnvBaseUrl())

    // 用户可能在等待克隆音色临时地址时取消或切换了音色。
    if (!voicePreviewRequestGate.isCurrent(requestId) || playingVoiceId.value !== voice.value) {
      return
    }
    if (!audioUrl) {
      toast.error(t('voiceprint.getAudioFailed'))
      playingVoiceId.value = ''
      return
    }

    // 创建新的音频实例
    const audio = uni.createInnerAudioContext()
    audioRef.value = audio
    audio.src = audioUrl

    // 监听播放结束
    audio.onEnded(() => {
      if (
        voicePreviewRequestGate.isCurrent(requestId)
        && audioRef.value === audio
        && playingVoiceId.value === voice.value
      ) {
        playingVoiceId.value = ''
      }
    })

    // 监听播放错误
    audio.onError(() => {
      if (
        voicePreviewRequestGate.isCurrent(requestId)
        && audioRef.value === audio
        && playingVoiceId.value === voice.value
      ) {
        toast.error(t('voiceprint.audioPlayFailed'))
        playingVoiceId.value = ''
      }
    })

    // 播放音频
    audio.play()
  }
  catch (error) {
    if (!voicePreviewRequestGate.isCurrent(requestId) || playingVoiceId.value !== voice.value) {
      return
    }
    console.error('获取克隆音色试听地址失败:', error)
    toast.error(t('voiceprint.getAudioFailed'))
    playingVoiceId.value = ''
  }
}

// 停止音频
function stopAudio() {
  voicePreviewRequestGate.invalidate()
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
  if (saving.value) {
    return
  }
  if (snapshotReloadBlocked.value) {
    toast.error(t(snapshotReloadFailed.value
      ? 'agentSnapshot.reloadAfterRestoreFailed'
      : 'agentSnapshot.reloadAfterRestorePending'))
    return
  }
  if (ttsOptionsLoading.value) {
    return
  }
  const ttsSelectionTouched = ttsLanguageTouched.value || ttsVoiceTouched.value
  const hasLanguageOptions = languageOptions.value.length > 0
  const hasVoiceOptions = Object.keys(voiceDetails.value).length > 0
  if (ttsSelectionTouched
    && (ttsOptionsModelId.value !== formData.value.ttsModelId
      || (hasLanguageOptions && !selectedTtsLanguage.value)
      || (hasVoiceOptions && !formData.value.ttsVoiceId))) {
    toast.warning(t('agent.ttsOptionsLoadFailed'))
    return
  }
  if (!formData.value.agentName?.trim()) {
    toast.warning(t('agent.pleaseInputAgentName'))
    return
  }

  if (!formData.value.systemPrompt?.trim()) {
    toast.warning(t('agent.pleaseInputRoleDescription'))
    return
  }

  try {
    saving.value = true
    const tagNames = dynamicTags.value.map(tag => tag.tagName)
    const tagsChanged = !isSameStringList(tagNames, originalTagNames.value)
    // 构建保存数据，包含上下文配置和语音设置
    const saveData: Record<string, any> = {
      ...formData.value,
      contextProviders: providerStore.providers,
      functions: normalizeAgentFunctions(formData.value.functions || []),
    }
    delete saveData.ttsVolume
    delete saveData.ttsRate
    delete saveData.ttsPitch
    delete saveData.ttsLanguage
    delete saveData.ttsVoiceId
    if (ttsLanguageTouched.value) {
      saveData.ttsLanguage = selectedTtsLanguage.value
    }
    if (ttsVoiceTouched.value) {
      saveData.ttsVoiceId = formData.value.ttsVoiceId
    }
    const changedTtsFields = new Set(speedPitchStore.changedFields)
    if (changedTtsFields.has('ttsVolume')) {
      saveData.ttsVolume = speedPitchStore.speedPitch.ttsVolume
    }
    if (changedTtsFields.has('ttsRate')) {
      saveData.ttsRate = speedPitchStore.speedPitch.ttsRate
    }
    if (changedTtsFields.has('ttsPitch')) {
      saveData.ttsPitch = speedPitchStore.speedPitch.ttsPitch
    }
    if (tagsChanged) {
      saveData.tagNames = tagNames
    }
    await updateAgent(agentId.value, saveData)
    if (tagsChanged) {
      originalTagNames.value = [...tagNames]
    }
    speedPitchStore.resetChangedFields()
    await loadAgentDetail()

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
  pluginStore.setCurrentFunctions(normalizeAgentFunctions(formData.value.functions || []))
  pluginStore.setAllFunctions(allFunctions.value)

  uni.navigateTo({
    url: '/pages/agent/tools',
  })
}

// 获取智能体标签
async function loadAgentTags(targetAgentId = agentId.value) {
  if (!targetAgentId) {
    return false
  }
  const requestId = ++agentTagRequestSequence
  try {
    const res = await getAgentTags(targetAgentId)
    if (!isActiveAgentTagRequest(targetAgentId, requestId)) {
      return false
    }
    dynamicTags.value = res || []
    originalTagNames.value = dynamicTags.value.map(tag => tag.tagName)
    return true
  }
  catch (error) {
    if (isActiveAgentTagRequest(targetAgentId, requestId)) {
      console.error('加载智能体标签失败:', error)
    }
    return false
  }
}

function isActiveAgentTagRequest(targetAgentId: string, requestId: number) {
  return targetAgentId === agentId.value && requestId === agentTagRequestSequence
}

async function handleSnapshotRestored(context: SnapshotRestoreContext) {
  if (!context || context.agentId !== agentId.value) {
    return
  }
  await reloadAgentAfterSnapshotRestore(context.agentId)
}

async function reloadAgentAfterSnapshotRestore(targetAgentId = agentId.value) {
  if (!targetAgentId || targetAgentId !== agentId.value) {
    return false
  }
  const reloadId = ++snapshotReloadSequence
  const detailRequestId = ++agentDetailRequestSequence
  const tagRequestId = ++agentTagRequestSequence
  snapshotReloadBlocked.value = true
  snapshotReloadFailed.value = false
  loading.value = true
  invalidateTtsMetadataRequest()

  try {
    // Apply detail and tags only after both persisted reads succeed. If either
    // fails, the old form may remain visible but cannot be saved until retry.
    const [detail, tags] = await Promise.all([
      getAgentDetail(targetAgentId),
      getAgentTags(targetAgentId),
    ])
    if (!isActiveSnapshotReload(targetAgentId, reloadId, detailRequestId, tagRequestId)) {
      return false
    }

    applyPersistedAgentDetail(detail, targetAgentId)
    dynamicTags.value = tags || []
    originalTagNames.value = dynamicTags.value.map(tag => tag.tagName)

    // Voice metadata is an optional display enhancement. Its own failure must
    // not turn a successful persisted detail+tag reload into a blocked form.
    await enhanceAgentDetailMetadata(detail, targetAgentId, detailRequestId)
    if (!isActiveSnapshotReload(targetAgentId, reloadId, detailRequestId, tagRequestId)) {
      return false
    }
    snapshotReloadBlocked.value = false
    snapshotReloadFailed.value = false
    return true
  }
  catch (error) {
    if (isActiveSnapshotReload(targetAgentId, reloadId, detailRequestId, tagRequestId)) {
      console.error('恢复后重新加载智能体失败:', error)
      snapshotReloadFailed.value = true
      toast.error(t('agentSnapshot.reloadAfterRestoreFailed'))
    }
    return false
  }
  finally {
    if (isActiveSnapshotReload(targetAgentId, reloadId, detailRequestId, tagRequestId)) {
      loading.value = false
    }
  }
}

function isActiveSnapshotReload(
  targetAgentId: string,
  reloadId: number,
  detailRequestId: number,
  tagRequestId: number,
) {
  return targetAgentId === agentId.value
    && reloadId === snapshotReloadSequence
    && detailRequestId === agentDetailRequestSequence
    && tagRequestId === agentTagRequestSequence
}

function retrySnapshotReload() {
  if (!snapshotReloadFailed.value || !agentId.value) {
    return
  }
  void reloadAgentAfterSnapshotRestore(agentId.value)
}

function openSnapshotPanel() {
  if (saving.value || snapshotReloadBlocked.value) {
    toast.warning(t('agentSnapshot.mutationBusy'))
    return
  }
  showSnapshotPanel.value = true
}

function isSameStringList(left: string[], right: string[]) {
  if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) {
    return false
  }
  return left.every((value, index) => value === right[index])
}

// 监听store中的插件配置变化
watch(() => pluginStore.currentFunctions, (newFunctions) => {
  formData.value.functions = normalizeAgentFunctions(newFunctions || [])
}, { deep: true })

watch(agentId, (currentAgentId, previousAgentId) => {
  if (currentAgentId === previousAgentId) {
    return
  }
  agentDetailRequestSequence += 1
  agentTagRequestSequence += 1
  snapshotReloadSequence += 1
  invalidateTtsMetadataRequest()
  loading.value = false
  snapshotReloadFailed.value = false
  snapshotReloadBlocked.value = Boolean(currentAgentId)
  originalAgentDetail.value = null
  originalTagNames.value = []
  if (currentAgentId) {
    void reloadAgentAfterSnapshotRestore(currentAgentId)
  }
}, { flush: 'sync' })

onMounted(async () => {
  loadAgentTags()

  // 先加载模型选项和角色模板
  await Promise.all([
    loadRoleTemplates(),
    loadModelOptions(),
    loadPluginFunctions(),
  ])

  // 然后加载智能体详情，这样可以正确映射显示名称
  if (agentId.value && !snapshotReloadBlocked.value) {
    await loadAgentDetail()
  }
})
</script>

<template>
  <view class="bg-[#f5f7fb] px-[20rpx]">
    <view class="mb-[24rpx] flex items-center justify-between border border-[#eeeeee] rounded-[20rpx] bg-white p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view>
        <text class="block text-[32rpx] text-[#232338] font-bold">
          {{ t('agent.editTitle') }}
        </text>
        <text v-if="currentVersionNo" class="mt-[8rpx] block text-[24rpx] text-[#65686f]">
          {{ t('agentSnapshot.currentVersion') }} #{{ currentVersionNo }}
        </text>
      </view>
      <wd-button
        size="small"
        type="primary"
        :disabled="saving || snapshotReloadBlocked"
        custom-class="!bg-[#336cff] !h-[64rpx] !rounded-[32rpx]"
        @click="openSnapshotPanel"
      >
        {{ t('agentSnapshot.title') }}
      </wd-button>
    </view>

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

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('slm')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('agent.slm') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.slm }}
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
          :disabled="isMemoryDisabled"
          :style="isMemoryDisabled ? 'background: #f0f0f0' : ''"
          class="box-border h-[500rpx] w-full resize-none break-words break-all border border-[#eeeeee] rounded-[12rpx] p-[20rpx] text-[26rpx] leading-[1.6] opacity-80 outline-none"
        />
      </view>
    </view>

    <!-- 保存按钮 -->
    <view class="mt-[40rpx] p-0">
      <view
        v-if="snapshotReloadBlocked"
        class="mb-[18rpx] rounded-[16rpx] bg-[rgba(245,108,108,0.1)] p-[20rpx] text-[24rpx] text-[#a34848] leading-[1.6]"
      >
        <text class="block">
          {{ t(snapshotReloadFailed ? 'agentSnapshot.reloadAfterRestoreFailed' : 'agentSnapshot.reloadAfterRestorePending') }}
        </text>
        <wd-button
          v-if="snapshotReloadFailed"
          size="small"
          type="info"
          custom-class="mt-[14rpx] !h-[60rpx]"
          @click="retrySnapshotReload"
        >
          {{ t('agentSnapshot.retryReload') }}
        </wd-button>
      </view>
      <wd-button
        type="primary"
        :loading="saving"
        :disabled="saving || ttsOptionsLoading || snapshotReloadBlocked"
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
      v-model="pickerShow.slm"
      :actions="modelOptions.LLM && modelOptions.LLM.map(item => ({ name: item.modelName, value: item.id }))"
      @close="onPickerCancel('slm')"
      @select="({ item }) => onPickerConfirm('slm', item.value, item.name)"
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
            <text :class="`flex-1 text-[28rpx] text-[#232338] ${hasVoicePreview(voice) ? '' : 'text-center'}`">
              {{ voice.name }}
            </text>
            <view v-if="hasVoicePreview(voice)" class="ml-[20rpx]" @click.stop="playAudio(voice, $event)">
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
    <AgentSnapshotPanel
      v-model:visible="showSnapshotPanel"
      :agent-id="agentId"
      :current-version-no="currentVersionNo"
      :has-unsaved-changes="hasUnsavedChanges"
      :mutation-busy="saving || snapshotReloadBlocked"
      @restored="handleSnapshotRestored"
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
