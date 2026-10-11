import type {
  Agent,
  AgentCreateData,
  AgentDetail,
  AgentSnapshot,
  AgentSnapshotPageParams,
  CorrectWordFile,
  ModelOption,
  PageData,
  RoleTemplate,
  TtsVoice,
} from './types'
import { http } from '@/http/request/alova'

// 获取智能体详情
export function getAgentDetail(id: string) {
  return http.Get<AgentDetail>(`/agent/${id}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取角色模板列表
export function getRoleTemplates() {
  return http.Get<RoleTemplate[]>('/agent/template', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取模型选项
export function getModelOptions(modelType: string, modelName: string = '') {
  return http.Get<ModelOption[]>('/models/names', {
    params: {
      modelType,
      modelName,
    },
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取智能体列表
export function getAgentList() {
  return http.Get<Agent[]>('/agent/list', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 创建智能体
export function createAgent(data: AgentCreateData) {
  return http.Post<string>('/agent', data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// 删除智能体
export function deleteAgent(id: string) {
  return http.Delete(`/agent/${id}`, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// 获取TTS音色列表
export function getTTSVoices(ttsModelId: string, voiceName: string = '') {
  return http.Get<TtsVoice[]>(`/models/${ttsModelId}/voices`, {
    params: {
      voiceName,
    },
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 更新智能体
export function updateAgent(id: string, data: Partial<AgentDetail> & { tagNames?: string[] }) {
  return http.Put(`/agent/${id}`, data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取插件列表
export function getPluginFunctions() {
  return http.Get<any[]>(`/models/provider/plugin/names`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取mcp接入点
export function getMcpAddress(agentId: string) {
  return http.Get<string>(`/agent/mcp/address/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
      isExposeError: true,
    },
  })
}

// 获取mcp工具
export function getMcpTools(agentId: string) {
  return http.Get<string[]>(`/agent/mcp/tools/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取声纹列表
export function getVoicePrintList(agentId: string) {
  return http.Get<any[]>(`/agent/voice-print/list/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取语音对话记录
export function getChatHistoryUser(agentId: string) {
  return http.Get<any[]>(`/agent/${agentId}/chat-history/user`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 新增声纹说话人
export function createVoicePrint(data: { agentId: string, audioId: string, sourceName: string, introduce: string }) {
  return http.Post('/agent/voice-print', data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// 获取智能体标签
export function getAgentTags(agentId: string) {
  return http.Get<any[]>(`/agent/${agentId}/tags`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 更新智能体标签
export function updateAgentTags(agentId: string, data) {
  return http.Put(`/agent/${agentId}/tags`, data, {
    meta: {
      ignoreAuth: false,
      isExposeError: true,
    },
  })
}

// 获取所有语言
export function getAllLanguage(modelId: string) {
  return http.Get<TtsVoice[]>(`/models/${modelId}/voices`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

/**
 * 获取克隆音色的临时播放ID
 * @param cloneId 克隆音色记录ID
 */
export function getVoiceCloneAudioId(cloneId: string) {
  return http.Post<string>(`/voiceClone/audio/${cloneId}`, {}, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// 获取智能体历史版本列表
export function getAgentSnapshots(agentId: string, params: AgentSnapshotPageParams) {
  return http.Get<PageData<AgentSnapshot>>(`/agent/${agentId}/snapshots`, {
    params,
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 获取智能体历史版本详情
export function getAgentSnapshot(agentId: string, snapshotId: string) {
  return http.Get<AgentSnapshot>(`/agent/${agentId}/snapshots/${snapshotId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// 恢复智能体历史版本
export function restoreAgentSnapshot(agentId: string, snapshotId: string, currentStateToken: string) {
  return http.Post(`/agent/${agentId}/snapshots/${snapshotId}/restore`, { currentStateToken }, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// 删除智能体历史版本
export function deleteAgentSnapshot(agentId: string, snapshotId: string) {
  return http.Delete(`/agent/${agentId}/snapshots/${snapshotId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// 获取所有替换词文件
export function getCorrectWordFiles() {
  return http.Get<CorrectWordFile[]>('/correct-word/file/select', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}
