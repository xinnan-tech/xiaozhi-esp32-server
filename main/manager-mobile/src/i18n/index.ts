import type { Language } from '@/store/lang'
import { ref } from 'vue'
import { useLangStore } from '@/store/lang'

// Import translation files
import en from './en'
import de from './de'
import vi from './vi'
import pt_BR from './pt_BR'

// Language pack mapping
const messages = {
  en,
  de,
  vi,
  pt_BR,
}

// Current language
const currentLang = ref<Language>('en')

// Initialize language
export function initI18n() {
  const langStore = useLangStore()
  currentLang.value = langStore.currentLang
}

// Switch language
export function changeLanguage(lang: Language) {
  currentLang.value = lang
  const langStore = useLangStore()
  langStore.changeLang(lang)
}

// Get translated text
export function t(key: string, params?: Record<string, string | number>): string {
  const langMessages = messages[currentLang.value]

  // Direct lookup for flat keys
  if (langMessages && typeof langMessages === 'object' && key in langMessages) {
    const value = langMessages[key]
    if (typeof value === 'string') {
      // Apply parameter replacements
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

  return key // Return key if translation is missing
}

// Get current language
export function getCurrentLanguage(): Language {
  return currentLang.value
}

// Get supported languages
export function getSupportedLanguages(): { code: Language, name: string }[] {
  return [
    { code: 'en', name: 'English' },
    { code: 'de', name: 'Deutsch' },
    { code: 'vi', name: 'Tiếng Việt' },
    { code: 'pt_BR', name: 'Português (Brasil)' },
  ]
}
