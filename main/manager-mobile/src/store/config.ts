import type { PublicConfig } from '../api/auth'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPublicConfig } from '../api/auth'

// 初始化状态
const initialConfigState: PublicConfig = {
  enableMobileRegister: false,
  version: '',
  year: '',
  allowUserRegister: false,
  mobileAreaList: [],
  beianIcpNum: '',
  beianGaNum: '',
  name: import.meta.env.VITE_APP_TITLE,
}

export const useConfigStore = defineStore(
  'config',
  () => {
    // 定义全局配置
    const config = ref<PublicConfig>({ ...initialConfigState })

    // 设置配置信息
    const setConfig = (val: PublicConfig) => {
      config.value = val
    }

    // 获取公共配置
    const fetchPublicConfig = async () => {
      try {
        const configData = await getPublicConfig()
        console.log(configData)

        setConfig(configData)
        return configData
      }
      catch (error) {
        console.error('获取公共配置失败:', error)
        throw error
      }
    }

    // 重置配置
    const resetConfig = () => {
      config.value = { ...initialConfigState }
    }

    return {
      config,
      setConfig,
      fetchPublicConfig,
      resetConfig,
    }
  },
  {
    persist: {
      key: 'config',
      serializer: {
        serialize: state => JSON.stringify(state.config),
        deserialize: value => ({ config: JSON.parse(value) }),
      },
    },
  },
)
