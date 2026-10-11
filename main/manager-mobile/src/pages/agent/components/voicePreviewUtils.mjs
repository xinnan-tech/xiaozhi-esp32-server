/** @param {Record<string, any>} voice */
export function hasVoicePreview(voice) {
  return Boolean(voice?.isClone || voice?.voiceDemo || voice?.voice_demo)
}

export function createVoicePreviewRequestGate() {
  let sequence = 0

  return {
    begin() {
      sequence += 1
      return sequence
    },
    invalidate() {
      sequence += 1
    },
    isCurrent(requestId) {
      return requestId === sequence
    },
  }
}

/**
 * @param {{ id: string, isClone?: boolean, voiceDemo?: string | null }} voice
 * @param {(cloneId: string) => Promise<string>} getCloneAudioId
 * @param {string} baseUrl
 */
export async function resolveVoicePreviewUrl(voice, getCloneAudioId, baseUrl) {
  if (!voice?.isClone) {
    return typeof voice?.voiceDemo === 'string' ? voice.voiceDemo : ''
  }
  if (!voice.id) {
    return ''
  }

  const uuid = await getCloneAudioId(voice.id)
  if (!uuid) {
    return ''
  }

  return `${baseUrl.replace(/\/+$/, '')}/voiceClone/play/${encodeURIComponent(uuid)}`
}
