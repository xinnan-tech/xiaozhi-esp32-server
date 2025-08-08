// 聊天会话列表项
export interface ChatSession {
  sessionId: string
  createdAt: string
  chatCount: number
}

// 聊天会话列表响应
export interface ChatSessionsResponse {
  total: number
  list: ChatSession[]
}

// 聊天消息
export interface ChatMessage {
  createdAt: string
  chatType: 1 | 2 // 1是用户，2是AI
  content: string
  audioId: string | null
  macAddress: string
}

// 用户消息内容（需要解析JSON）
export interface UserMessageContent {
  speaker: string
  content: string
}

// 获取聊天会话列表参数
export interface GetSessionsParams {
  page: number
  limit: number
}

// 音频播放相关
export interface AudioResponse {
  data: string // 音频下载ID
}
