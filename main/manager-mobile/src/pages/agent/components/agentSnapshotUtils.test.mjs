/* eslint-disable test/no-import-node-test -- this zero-dependency gate intentionally uses Node's built-in runner */
import assert from 'node:assert/strict'
import test from 'node:test'
import {
  filterTtsVoicesByLanguage,
  hasUsableTtsVoiceMetadata,
  isSensitiveKey,
  normalizeSnapshotOrderedList,
  normalizeSnapshotTtsNumber,
  redactSnapshotDisplayValue,
  SNAPSHOT_SECRET_REDACTED,
  stablePrettyStringify,
  toIntlLocale,
  willRestorePermanentlyDeleteChatHistory,
} from './agentSnapshotUtils.mjs'

test('rejects empty TTS metadata while keeping language-less voices selectable without a filter', () => {
  const voices = [{ id: 'voice-without-language', languages: '' }]
  assert.equal(hasUsableTtsVoiceMetadata([]), false)
  assert.equal(hasUsableTtsVoiceMetadata(voices), true)
  assert.deepEqual(filterTtsVoicesByLanguage(voices, ''), voices)
  assert.deepEqual(filterTtsVoicesByLanguage(voices, 'zh-CN'), [])
})

test('keeps inherited TTS values distinct from explicit zero', () => {
  assert.equal(normalizeSnapshotTtsNumber(null), null)
  assert.equal(normalizeSnapshotTtsNumber(''), null)
  assert.equal(normalizeSnapshotTtsNumber(0), 0)
  assert.equal(normalizeSnapshotTtsNumber('0'), 0)
})

test('warns only when restoring from a memory mode to no-memory mode', () => {
  assert.equal(willRestorePermanentlyDeleteChatHistory('Memory_mem_local_short', 'Memory_nomem'), true)
  assert.equal(willRestorePermanentlyDeleteChatHistory(undefined, 'Memory_nomem'), true)
  assert.equal(willRestorePermanentlyDeleteChatHistory('Memory_nomem', 'Memory_nomem'), false)
  assert.equal(willRestorePermanentlyDeleteChatHistory('Memory_mem_local_short', 'Memory_mem0ai'), false)
})

test('keeps context-provider order while stabilizing object keys', () => {
  const first = normalizeSnapshotOrderedList([
    { url: 'https://one.example', headers: { z: 'last', a: 'first' } },
    { url: 'https://two.example', headers: {} },
  ])
  const reversed = normalizeSnapshotOrderedList([
    { url: 'https://two.example', headers: {} },
    { headers: { a: 'first', z: 'last' }, url: 'https://one.example' },
  ])

  assert.deepEqual(first[0], {
    headers: { a: 'first', z: 'last' },
    url: 'https://one.example',
  })
  assert.notDeepEqual(first, reversed)
})

test('redacts nested credentials, header entries, URL credentials and query values', () => {
  const redacted = redactSnapshotDisplayValue({
    'apiKey': 'api-secret',
    'Authentication': 'authentication-secret',
    'X-Auth': 'auth-secret',
    'PHPSESSID': 'php-session-secret',
    'Session-Key': 'session-key-secret',
    'headers': [
      { key: 'Authorization', value: 'Bearer secret' },
      { key: 'Proxy-Authorization', value: 'Basic secret' },
      { key: 'Cookie', value: 'sid=secret' },
      { key: 'Set-Cookie', value: 'session=secret' },
      { key: 'Content-Type', value: 'application/json' },
    ],
    'marker': SNAPSHOT_SECRET_REDACTED,
    'session_id': 'session-secret',
    'url': 'https://user:pass@example.com/context?access_token=secret#fragment',
    'endpoint': 'https://example.com/callback?signature=secret',
  }, '[hidden]')

  assert.deepEqual(redacted, {
    'apiKey': '[hidden]',
    'Authentication': '[hidden]',
    'X-Auth': '[hidden]',
    'PHPSESSID': '[hidden]',
    'Session-Key': '[hidden]',
    'headers': [
      { key: 'Authorization', value: '[hidden]' },
      { key: 'Proxy-Authorization', value: '[hidden]' },
      { key: 'Cookie', value: '[hidden]' },
      { key: 'Set-Cookie', value: '[hidden]' },
      { key: 'Content-Type', value: 'application/json' },
    ],
    'marker': '[hidden]',
    'session_id': '[hidden]',
    'url': 'https://[hidden]@example.com/context?[hidden]',
    'endpoint': 'https://example.com/callback?[hidden]',
  })
})

test('redacts structured key/name entries without relying on property casing', () => {
  const entries = [
    { KEY: 'Authentication', VALUE: 'key secret' },
    { Name: 'X-Auth', Value: 'name secret' },
    { key: 'public-label', NAME: 'Authorization', value: 'secret selected from either marker' },
    { NAME: 'Content-Type', VALUE: 'application/json; charset=utf-8' },
  ]

  assert.deepEqual(redactSnapshotDisplayValue(entries, '[hidden]'), [
    { KEY: 'Authentication', VALUE: '[hidden]' },
    { Name: 'X-Auth', Value: '[hidden]' },
    { key: 'public-label', NAME: 'Authorization', value: '[hidden]' },
    { NAME: 'Content-Type', VALUE: 'application/json; charset=utf-8' },
  ])
})

test('redacts capability path values without hiding ordinary REST paths', () => {
  const redacted = redactSnapshotDisplayValue({
    slack: 'https://hooks.slack.com/services/T111/B222/capability-value',
    slackGov: 'https://hooks.slack-gov.com/services/T111/B222/gov-capability-value',
    discord: 'https://discord.com/api/webhooks/123456/capability-value',
    telegram: 'https://api.telegram.org/bot123456:capability-value/sendMessage',
    genericHook: 'https://example.com/api/hook/capability/continuation',
    genericHooks: 'https://example.com/api/hooks/capability/continuation',
    genericWebhook: 'https://example.com/api/webhook/capability/continuation',
    genericWebhooks: 'https://example.com/api/webhooks/capability/continuation',
    relativeUrl: '/api/webhooks/capability/continuation',
    callbackWebhookUrl: 'https://example.com/incoming/capability-value',
    nested: {
      deliveryWebhook: {
        options: {
          target: 'https://example.com/incoming/nested-capability-value',
          relativeTarget: '/incoming/nested-relative-capability-value',
        },
      },
    },
    protocolRelativeUrl: '//protocol-user:protocol-pass@example.com/context',
    jdbcUrl: 'jdbc:mysql://jdbc-user:jdbc-pass@example.com/database',
    ordinary: 'https://example.com/api/v1/agents/42',
  }, '[hidden]')

  assert.deepEqual(redacted, {
    slack: 'https://hooks.slack.com/services/T111/B222/[hidden]',
    slackGov: 'https://hooks.slack-gov.com/services/T111/B222/[hidden]',
    discord: 'https://discord.com/api/webhooks/123456/[hidden]',
    telegram: 'https://api.telegram.org/bot123456:[hidden]/sendMessage',
    genericHook: 'https://example.com/api/hook/[hidden]',
    genericHooks: 'https://example.com/api/hooks/[hidden]',
    genericWebhook: 'https://example.com/api/webhook/[hidden]',
    genericWebhooks: 'https://example.com/api/webhooks/[hidden]',
    relativeUrl: '/api/webhooks/[hidden]',
    callbackWebhookUrl: 'https://example.com/incoming/[hidden]',
    nested: {
      deliveryWebhook: {
        options: {
          target: 'https://example.com/incoming/[hidden]',
          relativeTarget: '/incoming/[hidden]',
        },
      },
    },
    protocolRelativeUrl: '//[hidden]@example.com/context',
    jdbcUrl: 'jdbc:mysql://[hidden]@example.com/database',
    ordinary: 'https://example.com/api/v1/agents/42',
  })
})

test('matches the backend sensitive key variants', () => {
  for (const key of [
    'Authentication',
    'X-Auth',
    'Proxy-Authorization',
    'Cookie',
    'Set-Cookie',
    'PHPSESSID',
    'Session-Key',
    'session_token',
    'Ocp-Apim-Subscription-Key',
  ]) {
    assert.equal(isSensitiveKey(key), true, `${key} should be redacted`)
  }
  assert.equal(isSensitiveKey('Content-Type'), false)
  assert.equal(isSensitiveKey('publicKey'), false)
})

test('formats objects stably and maps app locale names to Intl locales', () => {
  assert.equal(stablePrettyStringify({ z: 1, a: { d: 2, c: 1 } }), '{\n  "a": {\n    "c": 1,\n    "d": 2\n  },\n  "z": 1\n}')
  assert.equal(toIntlLocale('pt_BR'), 'pt-BR')
})
