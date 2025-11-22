import { ref } from 'vue'
import { useLangStore } from '@/store/lang'
import type { Language } from '@/store/lang'

// 导入各个语言的翻译文件
import zh_CN from './zh_CN'
import en from './en'
import zh_TW from './zh_TW'
import de from './de'
import vi from './vi'

// 语言包映射
const messages = {
  zh_CN: zh_CN,
  en,
  zh_TW: zh_TW,
  de,
  vi,
}

// 当前使用的语言
const currentLang = ref<Language>('zh_CN')

// 初始化语言
export function initI18n() {
  const langStore = useLangStore()
  currentLang.value = langStore.currentLang
}

// 切换语言
export function changeLanguage(lang: Language) {
  currentLang.value = lang
  const langStore = useLangStore()
  langStore.changeLang(lang)
}

// 获取翻译文本
export function t(key: string, params?: Record<string, string | number>): string {
  const langMessages = messages[currentLang.value]

  // 直接查找扁平键名
  if (langMessages && typeof langMessages === 'object' && key in langMessages) {
    let value = langMessages[key]
    if (typeof value === 'string') {
      // 处理参数替换
      if (params) {
        let result = value
        Object.entries(params).forEach(([paramKey, paramValue]) => {
          const regex = new RegExp(`\{${paramKey}\}`, 'g')
          result = result.replace(regex, String(paramValue))
        })
        return result
      }
      return value
    }
    return key
  }

  return key // 如果找不到对应的翻译，返回key本身
}

// 获取当前语言
export function getCurrentLanguage(): Language {
  return currentLang.value
}

// 获取支持的语言列表
export function getSupportedLanguages(): { code: Language, name: string }[] {
  return [
    { code: 'zh_CN', name: '简体中文' },
    { code: 'en', name: 'English' },
    { code: 'zh_TW', name: '繁體中文' },
    { code: 'de', name: 'Deutsch' },
    { code: 'vi', name: 'Tiếng Việt' },
  ]
}