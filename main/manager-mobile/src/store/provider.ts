import type { Providers } from '@/api/agent/types'
import { defineStore } from 'pinia'

export const useProvider = defineStore('provider', () => {
  const providers = ref<Providers[]>([])

  const updateProviders = (val: Providers[]) => {
    providers.value = val
  }

  return {
    providers,
    updateProviders,
  }
}, {
  persist: {
    key: 'providers',
    serializer: {
      serialize: state => JSON.stringify(state.providers),
      deserialize: value => ({ providers: JSON.parse(value) }),
    },
  },
})
