import { ref } from 'vue'
import { defineStore } from 'pinia'

// 支持的语言类型
export type Language = 'zh_CN' | 'en' | 'zh_TW' | 'de' | 'vi'

export interface LangStore {
  currentLang: Language
  changeLang: (lang: Language) => void
}

export const useLangStore = defineStore(
  'lang',
  (): LangStore => {
    // 从本地存储获取语言设置，如果没有则使用默认值
    const savedLang = uni.getStorageSync('app_language') as Language | null
    const currentLang = ref<Language>(savedLang || 'zh_CN')

    // 切换语言
    const changeLang = (lang: Language) => {
      currentLang.value = lang
      // 将语言设置保存到本地存储
      uni.setStorageSync('app_language', lang)
    }

    return {
      currentLang,
      changeLang,
    }
  },
  {
    persist: {
      key: 'lang',
      serializer: {
        serialize: state => JSON.stringify(state.currentLang),
        deserialize: value => ({ currentLang: JSON.parse(value) }),
      },
    },
  },
)