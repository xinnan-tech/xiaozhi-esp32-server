import type { Ref } from 'vue'
import { defineStore } from 'pinia'
import { ref } from 'vue'

// Supported language type
export type Language = 'en' | 'de' | 'vi' | 'pt_BR'

const supportedLanguages: Language[] = ['en', 'de', 'vi', 'pt_BR']

export const useLangStore = defineStore(
  'lang',
  () => {
    // Get language setting from local storage, fallback to default if missing or unsupported
    const savedLang = uni.getStorageSync('app_language') as string | null
    const initialLang = supportedLanguages.includes(savedLang as Language) ? (savedLang as Language) : 'en'
    const currentLang = ref<Language>(initialLang)

    // Switch language
    const changeLang = (lang: Language) => {
      currentLang.value = lang
      // Persist language setting
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
