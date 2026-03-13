import { defineStore } from 'pinia'

export const useSpeedPitch = defineStore('speedPitch', () => {
  const speedPitch = ref({
    ttsVolume: 0,
    ttsRate: 0,
    ttsPitch: 0,
  })

  const updateSpeedPitch = (val: typeof speedPitch.value) => {
    speedPitch.value = val
  }

  return {
    speedPitch,
    updateSpeedPitch,
  }
}, {
  persist: {
    key: 'speedPitch',
    serializer: {
      serialize: state => JSON.stringify(state.speedPitch),
      deserialize: value => ({ speedPitch: JSON.parse(value) }),
    },
  },
})
