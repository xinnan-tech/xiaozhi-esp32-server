import type { Agent } from '@/api/agent/types'
import { defineStore } from 'pinia'
import { getAgentList } from '@/api/agent/agent'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    // 智能体列表
    agentList: [] as Agent[],
    // 当前选中的智能体ID
    currentAgentId: '',
    // 当前选中的智能体信息
    currentAgent: null as Agent | null,
    // 是否已加载智能体列表
    isLoaded: false,
  }),

  getters: {
    // 获取当前智能体
    getCurrentAgent: (state) => {
      return state.agentList.find(agent => agent.id === state.currentAgentId) || null
    },

    // 获取智能体列表用于选择器
    getAgentOptions: (state) => {
      return state.agentList.map(agent => ({
        name: agent.agentName,
        value: agent.id,
        agent,
      }))
    },

    // 是否有智能体列表
    hasAgents: (state) => {
      return state.agentList.length > 0
    },
  },

  actions: {
    // 加载智能体列表
    async loadAgentList() {
      try {
        const list = await getAgentList()
        this.agentList = list
        this.isLoaded = true

        // 如果没有当前选中的智能体，且列表不为空，选择第一个
        if (!this.currentAgentId && list.length > 0) {
          this.setCurrentAgent(list[0].id)
        }

        return list
      }
      catch (error) {
        console.error('加载智能体列表失败:', error)
        throw error
      }
    },

    // 设置当前智能体
    setCurrentAgent(agentId: string) {
      this.currentAgentId = agentId
      console.log(this.agentList.find(agent => agent.id === agentId), '执行')

      this.currentAgent = this.agentList.find(agent => agent.id === agentId) || null
    },

    // 添加智能体到列表
    addAgent(agent: Agent) {
      this.agentList.push(agent)

      // 如果是第一个智能体，设置为当前智能体
      if (this.agentList.length === 1) {
        this.setCurrentAgent(agent.id)
      }
    },

    // 从列表中移除智能体
    removeAgent(agentId: string) {
      const index = this.agentList.findIndex(agent => agent.id === agentId)
      if (index > -1) {
        this.agentList.splice(index, 1)

        // 如果删除的是当前选中的智能体，重新选择
        if (this.currentAgentId === agentId) {
          if (this.agentList.length > 0) {
            this.setCurrentAgent(this.agentList[0].id)
          }
          else {
            this.currentAgentId = ''
            this.currentAgent = null
          }
        }
      }
    },

    // 更新智能体信息
    updateAgent(agent: Agent) {
      const index = this.agentList.findIndex(item => item.id === agent.id)
      if (index > -1) {
        this.agentList[index] = agent

        // 如果是当前智能体，更新当前智能体信息
        if (this.currentAgentId === agent.id) {
          this.currentAgent = agent
        }
      }
    },

    // 清空状态
    clearState() {
      this.agentList = []
      this.currentAgentId = ''
      this.currentAgent = null
      this.isLoaded = false
    },
  },

  persist: {
    // 持久化当前选中的智能体ID
    // paths: ['currentAgentId'],
  },
})
