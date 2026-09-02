export const SNAPSHOT_SECRET_REDACTED = '__SNAPSHOT_SECRET_REDACTED__'

/** @param {unknown} voices */
export function hasUsableTtsVoiceMetadata(voices) {
  return Array.isArray(voices) && voices.length > 0
}

/**
 * @param {unknown} currentMemModelId
 * @param {unknown} targetMemModelId
 */
export function willRestorePermanentlyDeleteChatHistory(currentMemModelId, targetMemModelId) {
  return currentMemModelId !== 'Memory_nomem' && targetMemModelId === 'Memory_nomem'
}

/**
 * @param {Array<Record<string, any>>} voices
 * @param {string} language
 */
export function filterTtsVoicesByLanguage(voices, language) {
  if (!language) {
    return voices
  }
  return voices.filter((voice) => {
    if (typeof voice.languages !== 'string' || !voice.languages.trim()) {
      return false
    }
    return voice.languages
      .split(/[、；;,，]/)
      .map(item => item.trim())
      .filter(Boolean)
      .includes(language)
  })
}

/** @param {unknown} value */
export function normalizeSnapshotTtsNumber(value) {
  if (value === undefined || value === null || String(value).trim() === '') {
    return null
  }
  if (typeof value === 'number') {
    return Math.trunc(value)
  }
  const text = String(value).trim()
  return /^[+-]?\d+$/.test(text) ? Number.parseInt(text, 10) : text
}

/**
 * Normalize object-key order without changing array order. Context providers
 * are consumed sequentially by the runtime, so their list order is semantic.
 * @param {unknown} value
 */
export function normalizeSnapshotOrderedList(value) {
  if (!Array.isArray(value)) {
    return []
  }
  return value
    .filter(item => item !== undefined && item !== null)
    .map(normalizeDisplayObject)
}

/**
 * @param {unknown} value
 * @param {string} redactedLabel
 * @param {string} [parentKey]
 * @returns {unknown}
 */
export function redactSnapshotDisplayValue(value, redactedLabel, parentKey = '') {
  if (value === SNAPSHOT_SECRET_REDACTED || isSensitiveKey(parentKey)) {
    return redactedLabel
  }
  if (Array.isArray(value)) {
    return value.map(item => redactSnapshotDisplayValue(item, redactedLabel, parentKey))
  }
  if (isPlainObject(value)) {
    const entryNameKey = Object.keys(value).find((key) => {
      return ['key', 'name'].includes(key.toLowerCase())
        && typeof value[key] === 'string'
        && isSensitiveKey(value[key])
    })
    const entryValueKey = Object.keys(value).find(key => key.toLowerCase() === 'value')
    return Object.keys(value).sort().reduce((result, key) => {
      const semanticKey = resolveUrlSemanticKey(parentKey, key)
      if (entryNameKey && key === entryValueKey) {
        result[key] = redactedLabel
      }
      else {
        result[key] = redactSnapshotDisplayValue(value[key], redactedLabel, semanticKey)
      }
      return result
    }, {})
  }
  if (typeof value === 'string' && isSnapshotUrlValue(parentKey, value)) {
    return redactUrl(value, redactedLabel, parentKey)
  }
  return value
}

/** @param {unknown} value */
export function stablePrettyStringify(value) {
  return JSON.stringify(normalizeDisplayObject(value), null, 2)
}

/** @param {string} language */
export function toIntlLocale(language) {
  return language.replace('_', '-')
}

/** @param {string} key */
export function isSensitiveKey(key) {
  const normalized = String(key).toLowerCase().replace(/[^a-z0-9]/g, '')
  return normalized === 'authorization'
    || normalized.includes('authorization')
    || normalized.includes('authentication')
    || normalized === 'auth'
    || normalized.endsWith('auth')
    || normalized === 'cookie'
    || normalized === 'cookie2'
    || normalized === 'setcookie'
    || normalized === 'setcookie2'
    || normalized.endsWith('cookie')
    || normalized === 'session'
    || normalized.endsWith('session')
    || normalized.includes('sessionid')
    || normalized.includes('sessionkey')
    || normalized.includes('sessiontoken')
    || normalized.includes('sessioncookie')
    || normalized.endsWith('sessid')
    || normalized === 'token'
    || normalized.endsWith('token')
    || normalized.includes('apikey')
    || normalized.includes('appkey')
    || normalized.includes('accesskey')
    || normalized.includes('subscriptionkey')
    || normalized.includes('privatekey')
    || normalized.includes('password')
    || normalized.includes('passwd')
    || normalized.includes('secret')
    || normalized.includes('credential')
}

/**
 * @param {string} value
 * @param {string} redactedLabel
 * @param {string} parentKey
 */
function redactUrl(value, redactedLabel, parentKey) {
  const withoutCredentials = value.replace(
    /^((?:[a-z][a-z0-9+.-]*:)*\/\/)[^/?#\s]*@/i,
    (match, prefix) => `${prefix}${redactedLabel}@`,
  )
  const schemeMatch = /^((?:[a-z][a-z0-9+.-]*:)*\/\/)/i.exec(withoutCredentials)
  let pathRedacted = withoutCredentials
  if (schemeMatch) {
    const scheme = schemeMatch[1]
    const remainder = withoutCredentials.slice(scheme.length)
    const suffixIndex = remainder.search(/[?#]/)
    const authorityAndPath = suffixIndex < 0 ? remainder : remainder.slice(0, suffixIndex)
    const suffix = suffixIndex < 0 ? '' : remainder.slice(suffixIndex)
    const pathIndex = authorityAndPath.indexOf('/')
    const authority = pathIndex < 0 ? authorityAndPath : authorityAndPath.slice(0, pathIndex)
    const path = pathIndex < 0 ? '' : authorityAndPath.slice(pathIndex)
    let host = authority.slice(authority.lastIndexOf('@') + 1)
    if (host.startsWith('[')) {
      const closingBracket = host.indexOf(']')
      host = closingBracket > 0 ? host.slice(1, closingBracket) : host
    }
    else {
      host = host.replace(/:\d+$/, '')
    }
    host = host.toLowerCase()
    pathRedacted = `${scheme}${authority}${redactCapabilityPath(path, host, parentKey, redactedLabel)}${suffix}`
  }
  else {
    const suffixIndex = withoutCredentials.search(/[?#]/)
    const path = suffixIndex < 0 ? withoutCredentials : withoutCredentials.slice(0, suffixIndex)
    const suffix = suffixIndex < 0 ? '' : withoutCredentials.slice(suffixIndex)
    pathRedacted = `${redactCapabilityPath(path, '', parentKey, redactedLabel)}${suffix}`
  }
  const queryIndex = pathRedacted.search(/[?#]/)
  if (queryIndex < 0) {
    return pathRedacted
  }
  return `${pathRedacted.slice(0, queryIndex)}${pathRedacted[queryIndex]}${redactedLabel}`
}

/**
 * Capability URLs often carry credentials in path segments rather than in
 * query parameters. Preserve public provider IDs where their formats are
 * known, and fail closed after generic hook markers.
 * @param {string} path
 * @param {string} host
 * @param {string} parentKey
 * @param {string} redactedLabel
 */
function redactCapabilityPath(path, host, parentKey, redactedLabel) {
  if (!path) {
    return path
  }
  const segments = path.split('/')
  const normalizedSegments = segments.map(segment => segment.toLowerCase())

  if (host === 'hooks.slack.com' || host === 'hooks.slack-gov.com') {
    const servicesIndex = normalizedSegments.indexOf('services')
    const capabilityIndex = servicesIndex >= 0 ? servicesIndex + 3 : -1
    if (capabilityIndex > 0 && capabilityIndex < segments.length) {
      segments[capabilityIndex] = redactedLabel
      return segments.join('/')
    }
  }

  if (host === 'discord.com'
    || host.endsWith('.discord.com')
    || host === 'discordapp.com'
    || host.endsWith('.discordapp.com')) {
    const webhooksIndex = normalizedSegments.indexOf('webhooks')
    const capabilityIndex = webhooksIndex >= 0 ? webhooksIndex + 2 : -1
    if (capabilityIndex > 0 && capabilityIndex < segments.length) {
      segments[capabilityIndex] = redactedLabel
      return segments.join('/')
    }
  }

  if (host === 'api.telegram.org') {
    const botIndex = segments.findIndex(segment => /^bot[^:]+:.+$/i.test(segment))
    if (botIndex >= 0) {
      segments[botIndex] = segments[botIndex].replace(/^bot([^:]+):.+$/i, `bot$1:${redactedLabel}`)
      return segments.join('/')
    }
  }

  const markerIndex = normalizedSegments.findIndex(segment => /^(?:webhooks?|hooks?)$/.test(segment))
  if (markerIndex >= 0 && markerIndex + 1 < segments.length) {
    return [...segments.slice(0, markerIndex + 1), redactedLabel].join('/')
  }

  const normalizedKey = String(parentKey).toLowerCase().replace(/[^a-z0-9]/g, '')
  if (normalizedKey.includes('webhook')) {
    let lastSegmentIndex = -1
    for (let index = segments.length - 1; index >= 0; index -= 1) {
      if (segments[index].length > 0) {
        lastSegmentIndex = index
        break
      }
    }
    if (lastSegmentIndex >= 0) {
      segments[lastSegmentIndex] = redactedLabel
      return segments.join('/')
    }
  }

  return path
}

/**
 * Carry webhook capability semantics through wrapper objects such as
 * `{ deliveryWebhook: { options: { target: "https://.../secret" } } }`.
 * @param {string} parentKey
 * @param {string} childKey
 */
function resolveUrlSemanticKey(parentKey, childKey) {
  if (isWebhookSemanticKey(childKey)) {
    return childKey
  }
  if (isWebhookSemanticKey(parentKey)) {
    return childKey ? `${parentKey}.${childKey}` : parentKey
  }
  return childKey
}

/** @param {string} value */
function isWebhookSemanticKey(value) {
  const normalized = String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '')
  return normalized.includes('webhook')
    || normalized === 'hook'
    || normalized === 'hooks'
    || normalized.endsWith('hook')
    || normalized.endsWith('hooks')
}

/**
 * @param {string} parentKey
 * @param {string} value
 */
function isSnapshotUrlValue(parentKey, value) {
  const normalizedKey = String(parentKey).toLowerCase().replace(/[^a-z0-9]/g, '')
  return normalizedKey.includes('url')
    || normalizedKey.endsWith('uri')
    || normalizedKey.includes('endpoint')
    || isWebhookSemanticKey(parentKey)
    || /^(?:[a-z][a-z0-9+.-]*:)*\/\//i.test(value)
}

/** @param {unknown} value */
function normalizeDisplayObject(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeDisplayObject)
  }
  if (isPlainObject(value)) {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = normalizeDisplayObject(value[key])
      return result
    }, {})
  }
  return value
}

/**
 * @param {unknown} value
 * @returns {value is Record<string, unknown>}
 */
function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}
