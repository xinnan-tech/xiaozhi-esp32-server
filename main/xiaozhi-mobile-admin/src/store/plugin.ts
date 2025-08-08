import type { AgentFunction, PluginDefinition } from '@/api/agent/types'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePluginStore = defineStore(
  'plugin',
  () => {
    // 所有可用插件
    const allFunctions = ref<PluginDefinition[]>([])

    // 当前智能体的插件配置
    const currentFunctions = ref<AgentFunction[]>([])

    // 当前编辑的智能体ID
    const currentAgentId = ref('')

    // 设置所有可用插件
    const setAllFunctions = (functions: PluginDefinition[]) => {
      allFunctions.value = functions
    }

    // 设置当前智能体的插件配置
    const setCurrentFunctions = (functions: AgentFunction[]) => {
      currentFunctions.value = functions
    }

    // 设置当前智能体ID
    const setCurrentAgentId = (agentId: string) => {
      currentAgentId.value = agentId
    }

    // 更新插件配置（用于保存时调用）
    const updateFunctions = (functions: AgentFunction[]) => {
      currentFunctions.value = functions
    }

    // 清空数据
    const clear = () => {
      allFunctions.value = []
      currentFunctions.value = []
      currentAgentId.value = ''
    }

    return {
      allFunctions,
      currentFunctions,
      currentAgentId,
      setAllFunctions,
      setCurrentFunctions,
      setCurrentAgentId,
      updateFunctions,
      clear,
    }
  },
  {
    persist: false, // 不持久化，每次进入页面重新加载
  },
)
