<script lang="ts" setup>
import type { AgentDetail, ModelOption, PluginDefinition, RoleTemplate } from '@/api/agent/types'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { getAgentDetail, getModelOptions, getPluginFunctions, getRoleTemplates, getTTSVoices, updateAgent } from '@/api/agent/agent'
import { usePluginStore } from '@/store'
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
  }
  catch (error) {
    console.error('保存失败:', error)
    toast.error('保存失败')
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

// 监听插件配置更新
function watchPluginUpdates() {
  // 监听store中的插件配置变化
  watch(() => pluginStore.currentFunctions, (newFunctions) => {
    console.log('插件配置已更新:', newFunctions)
    formData.value.functions = newFunctions
  }, { deep: true })
}

onMounted(async () => {
  // 初始化插件配置监听
  watchPluginUpdates()

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
    <!-- 基础信息标题 -->
    <view class="pb-[20rpx] first:pt-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        基础信息
      </text>
    </view>

    <!-- 基础信息卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          助手昵称
        </text>
        <input
          v-model="formData.agentName"
          class="box-border h-[80rpx] w-full border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[16rpx_20rpx] text-[28rpx] text-[#232338] leading-[1.4] outline-none focus:border-[#336cff] focus:bg-white placeholder:text-[#9d9ea3]"
          type="text"
          placeholder="请输入助手昵称"
        >
      </view>

      <view class="mb-[24rpx] last:mb-0">
        <text class="mb-[12rpx] block text-[28rpx] text-[#232338] font-medium">
          角色模式
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
          角色介绍
        </text>
        <textarea
          v-model="formData.systemPrompt"
          :maxlength="2000"
          placeholder="请输入角色介绍"
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
        模型配置
      </text>
    </view>

    <!-- 模型配置卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="flex flex-col gap-[16rpx]">
        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('vad')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            语音活动检测
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.vad }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('asr')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            语音识别
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.asr }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('llm')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            大语言模型
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.llm }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('vllm')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            视觉大模型
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.vllm }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('intent')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            意图识别
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.intent }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('memory')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            记忆
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.memory }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>
      </view>
    </view>

    <!-- 语音设置标题 -->
    <view class="pb-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        语音设置
      </text>
    </view>

    <!-- 语音设置卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="flex flex-col gap-[16rpx]">
        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('tts')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            语音合成
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.tts }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:bg-[#eef3ff]" @click="openPicker('voiceprint')">
          <text class="text-[28rpx] text-[#232338] font-medium">
            角色音色
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ displayNames.voiceprint }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>

        <view class="flex items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx]">
          <view class="text-[28rpx] text-[#232338] font-medium">
            插件
          </view>
          <view class="cursor-pointer rounded-[20rpx] bg-[rgba(51,108,255,0.1)] px-[24rpx] py-[12rpx] text-[24rpx] text-[#336cff] transition-all duration-300 active:bg-[#336cff] active:text-white" @click="handleTools">
            <text>编辑功能</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 记忆历史标题 -->
    <view class="pb-[20rpx]">
      <text class="text-[32rpx] text-[#232338] font-bold">
        历史记忆
      </text>
    </view>

    <!-- 记忆历史卡片 -->
    <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
      <view class="mb-[24rpx] last:mb-0">
        <textarea
          v-model="formData.summaryMemory"
          placeholder="记忆内容"
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
        {{ saving ? '保存中...' : '保存' }}
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
      @close="onPickerCancel('tts')"
      @select="({ item }) => onPickerConfirm('tts', item.value, item.name)"
    />

    <wd-action-sheet
      v-model="pickerShow.voiceprint"
      :actions="voiceOptions && voiceOptions.map(item => ({ name: item.name, value: item.id }))"
      @close="onPickerCancel('voiceprint')"
      @select="({ item }) => onPickerConfirm('voiceprint', item.value, item.name)"
    />
  </view>
</template>
