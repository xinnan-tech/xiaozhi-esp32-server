import { defineStore } from 'pinia'

const SPEED_PITCH_FIELDS = ['ttsVolume', 'ttsRate', 'ttsPitch'] as const

type SpeedPitchField = typeof SPEED_PITCH_FIELDS[number]
type SpeedPitchSettings = Record<SpeedPitchField, number>

export const useSpeedPitch = defineStore('speedPitch', () => {
  const speedPitch = ref<SpeedPitchSettings>({
    ttsVolume: 0,
    ttsRate: 0,
    ttsPitch: 0,
  })
  const changedFields = ref<SpeedPitchField[]>([])

  const updateSpeedPitch = (val: SpeedPitchSettings, options: { changedFields?: SpeedPitchField[] } = {}) => {
    speedPitch.value = val
    if (options.changedFields) {
      changedFields.value = Array.from(new Set([
        ...changedFields.value,
        ...options.changedFields,
      ]))
    }
  }

  const resetChangedFields = () => {
    changedFields.value = []
  }

  return {
    speedPitch,
    changedFields,
    updateSpeedPitch,
    resetChangedFields,
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
