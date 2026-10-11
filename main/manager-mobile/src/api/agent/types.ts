// 智能体列表数据类型
export interface Agent {
  id: string
  agentName: string
  ttsModelName: string
  ttsVoiceName: string
  llmModelName: string
  vllmModelName: string
  memModelId: string
  systemPrompt: string
  summaryMemory: string | null
  lastConnectedAt: string | null
  deviceCount: number
  tags: Record<string, string>[]
}

// 智能体创建数据类型
export interface AgentCreateData {
  agentName: string
}

// 智能体详情数据类型
export interface AgentDetail {
  id: string
  userId: string
  agentCode: string
  agentName: string
  asrModelId: string
  vadModelId: string
  llmModelId: string
  slmModelId: string
  vllmModelId: string
  ttsModelId: string
  ttsVoiceId: string
  memModelId: string
  intentModelId: string
  chatHistoryConf: number
  systemPrompt: string
  summaryMemory: string
  langCode: string
  language: string
  sort: number
  creator: string
  createdAt: string
  updater: string
  updatedAt: string
  ttsLanguage: string | null
  ttsVolume: number | null
  ttsRate: number | null
  ttsPitch: number | null
  currentVersionNo?: number | null
  tagNames?: string[]
  functions: AgentFunction[]
  contextProviders: Providers[]
}

export interface Providers {
  url: string
  headers: Array<{
    key: string
    value: string
  }>
}

export interface AgentFunction {
  id?: string
  agentId?: string
  pluginId: string
  paramInfo: Record<string, string | number | boolean> | null
}

export interface PageData<T> {
  list: T[]
  total: number
}

export interface AgentSnapshotData extends Partial<AgentDetail> {
  correctWordFileIds?: string[]
  tagNames?: string[]
  tags?: Array<{
    tagName?: string
    [key: string]: any
  }>
  [key: string]: any
}

export interface AgentSnapshot {
  id: string
  agentId: string
  userId?: string
  versionNo: number
  changedFields?: string[]
  fieldOrder?: string[]
  source?: string
  restoreFromSnapshotId?: string | null
  restoreFromVersionNo?: number | null
  currentStateToken?: string
  currentSnapshotData?: AgentSnapshotData
  creator?: string
  createdAt?: string
  snapshotData?: AgentSnapshotData
  afterSnapshotData?: AgentSnapshotData
}

export interface AgentSnapshotPageParams {
  page?: number
  limit?: number
  maxVersionNo?: number
}

export interface CorrectWordFile {
  id: string
  fileName: string
  wordCount?: number
}

export interface TtsVoice {
  id: string
  name: string
  voiceDemo?: string | null
  languages?: string | null
  isClone?: boolean | null
}

// 角色模板数据类型
export interface RoleTemplate {
  id: string
  agentCode: string
  agentName: string
  asrModelId: string
  vadModelId: string
  llmModelId: string
  vllmModelId: string
  ttsModelId: string
  ttsVoiceId: string
  ttsLanguage?: string | null
  memModelId: string
  intentModelId: string
  chatHistoryConf: number
  systemPrompt: string
  summaryMemory: string
  langCode: string
  language: string
  sort: number
  creator: string
  createdAt: string
  updater: string
  updatedAt: string
}

// 模型选项数据类型
export interface ModelOption {
  id: string
  modelName: string
}

export interface PluginField {
  key: string
  type: string
  label: string
  default: string
  selected?: boolean
  editing?: boolean
}

export interface PluginDefinition {
  id: string
  modelType: string
  providerCode: string
  name: string
  fields: PluginField[] // 注意：原始是字符串，需要先 JSON.parse
  sort: number
  updater: string
  updateDate: string
  creator: string
  createDate: string
  [key: string]: any
}
