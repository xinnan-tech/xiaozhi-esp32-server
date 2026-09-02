<script lang="ts" setup>
import type { AgentSnapshot, AgentSnapshotData } from '@/api/agent/types'
import { computed, ref, watch } from 'vue'
import { useMessage } from 'wot-design-uni/components/wd-message-box'
import {
  deleteAgentSnapshot,
  getAgentSnapshot,
  getAgentSnapshots,
  getCorrectWordFiles,
  getModelOptions,
  getPluginFunctions,
  getTTSVoices,
  restoreAgentSnapshot,
} from '@/api/agent/agent'
import { getCurrentLanguage, t } from '@/i18n'
import { toast } from '@/utils/toast'
import {
  isSensitiveKey,
  normalizeSnapshotTtsNumber as normalizeDefaultTtsNumber,
  normalizeSnapshotOrderedList,
  redactSnapshotDisplayValue,
  SNAPSHOT_SECRET_REDACTED,
  stablePrettyStringify,
  toIntlLocale,
  willRestorePermanentlyDeleteChatHistory,
} from './agentSnapshotUtils.mjs'

defineOptions({
  name: 'AgentSnapshotPanel',
})

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  currentVersionNo: null,
  hasUnsavedChanges: false,
  mutationBusy: false,
})

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'restored', context: { agentId: string, actionSequence: number }): void
}>()

interface Props {
  visible?: boolean
  agentId: string
  currentVersionNo?: number | null
  hasUnsavedChanges?: boolean
  mutationBusy?: boolean
}

interface SnapshotRow extends AgentSnapshot {
  isLatestSnapshot?: boolean
  previousSnapshotId?: string | null
  previousVersionNo?: number | null
}

interface VersionDetail {
  mode: 'view' | 'restore'
  single: boolean
  row: SnapshotRow
  beforeData: AgentSnapshotData
  afterData: AgentSnapshotData
  changedFields: string[]
  fieldOrder: string[]
  forceCompare?: boolean
  beforeVersionNo?: number | null
  afterVersionNo?: number | null
  currentStateToken?: string
}

interface DetailItem {
  field: string
  label: string
  beforeText: string
  afterText: string
  single: boolean
  recordedOnly?: boolean
  redactedDifference?: boolean
}

interface RestoreActionContext {
  actionSequence: number
  agentId: string
  snapshotId: string
  currentStateToken: string
  detailRequestSequence: number
  willClearChatHistory: boolean
}

const message = useMessage()
const restoring = ref(false)

const panelVisible = computed({
  get: () => props.visible,
  set: (value) => {
    if (!value && restoring.value) {
      return
    }
    emit('update:visible', value)
  },
})

const loading = ref(false)
const detailLoading = ref(false)
const deletingSnapshotId = ref('')
const snapshots = ref<SnapshotRow[]>([])
const page = ref(1)
const limit = 10
const total = ref(0)
const historyAnchorVersionNo = ref<number | null>(null)
const detailVisible = ref(false)
const detailPopupVisible = computed({
  get: () => detailVisible.value,
  set: (value) => {
    if (!value && restoring.value) {
      return
    }
    detailVisible.value = value
  },
})
const currentDetail = ref<VersionDetail | null>(null)
const pluginNameMap = ref<Record<string, string>>({})
const modelNameMap = ref<Record<string, string>>({})
const voiceNameMap = ref<Record<string, string>>({})
const correctWordNameMap = ref<Record<string, string>>({})
const loadedVoiceModelIds = ref<Record<string, boolean>>({})
const metadataLoaded = ref(false)
const correctWordMetadataLoaded = ref(false)
let detailRequestSequence = 0
let snapshotRequestSequence = 0
let restoreActionSequence = 0
let restorePostActionSequence: number | null = null
let restorePreviewRequestSequence: number | null = null

const MODEL_TYPES = ['ASR', 'VAD', 'LLM', 'VLLM', 'TTS', 'Memory', 'Intent']
const MODEL_FIELD_TYPES: Record<string, string> = {
  asrModelId: 'ASR',
  vadModelId: 'VAD',
  llmModelId: 'LLM',
  slmModelId: 'LLM',
  vllmModelId: 'VLLM',
  ttsModelId: 'TTS',
  memModelId: 'Memory',
  intentModelId: 'Intent',
}

const CHAT_HISTORY_CONF_LABEL_KEYS: Record<string, string> = {
  0: 'agentSnapshot.chatHistoryConf.none',
  1: 'agentSnapshot.chatHistoryConf.text',
  2: 'agentSnapshot.chatHistoryConf.textVoice',
}

const SNAPSHOT_FIELD_ORDER = [
  'agentName',
  'agentCode',
  'asrModelId',
  'vadModelId',
  'llmModelId',
  'slmModelId',
  'vllmModelId',
  'ttsModelId',
  'ttsLanguage',
  'ttsVoiceId',
  'ttsVolume',
  'ttsRate',
  'ttsPitch',
  'memModelId',
  'intentModelId',
  'chatHistoryConf',
  'systemPrompt',
  'summaryMemory',
  'langCode',
  'language',
  'sort',
  'functions',
  'contextProviders',
  'correctWordFileIds',
  'tagNames',
]

const hasMore = computed(() => snapshots.value.length < total.value)
const detailItems = computed(() => {
  if (!currentDetail.value) {
    return []
  }
  return buildDetailItems(currentDetail.value)
})
const detailTitle = computed(() => {
  if (!currentDetail.value) {
    return t('agentSnapshot.detailTitle')
  }
  const label = currentDetail.value.mode === 'restore'
    ? t('agentSnapshot.restorePreviewTitle')
    : t('agentSnapshot.detailTitle')
  return formatVersionRangeTitle(label, currentDetail.value.beforeVersionNo, currentDetail.value.afterVersionNo)
})
const restoreWillClearChatHistory = computed(() => {
  if (!currentDetail.value || currentDetail.value.mode !== 'restore') {
    return false
  }
  return willRestorePermanentlyDeleteChatHistory(
    currentDetail.value.beforeData?.memModelId,
    currentDetail.value.afterData?.memModelId,
  )
})
const displayedCurrentVersionNo = computed(() => historyAnchorVersionNo.value || props.currentVersionNo)
const canConfirmRestore = computed(() => {
  return !restoring.value
    && !props.mutationBusy
    && currentDetail.value?.mode === 'restore'
    && detailItems.value.length > 0
    && Boolean(currentDetail.value.currentStateToken?.trim())
})

watch(() => props.visible, (visible) => {
  if (visible) {
    openPanel()
  }
  else {
    invalidateRestoreAction()
    invalidateSnapshotRequest()
    closeDetail(true)
  }
})

watch(detailVisible, (visible) => {
  if (!visible) {
    invalidateDetailRequest()
  }
}, { flush: 'sync' })

watch(() => props.currentVersionNo, () => {
  if (props.visible) {
    openPanel()
  }
})

watch(() => props.agentId, (currentAgentId, previousAgentId) => {
  if (currentAgentId === previousAgentId) {
    return
  }
  invalidateRestoreAction()
  invalidateSnapshotRequest()
  closeDetail(true)
  if (props.visible) {
    openPanel()
  }
}, { flush: 'sync' })

watch(() => props.mutationBusy, (mutationBusy) => {
  if (!mutationBusy) {
    return
  }
  const restorePostInFlight = restoring.value
    && restorePostActionSequence === restoreActionSequence
  if (restorePostInFlight) {
    return
  }
  const pendingRestorePreview = restorePreviewRequestSequence !== null
    || currentDetail.value?.mode === 'restore'
  const pendingRestoreConfirmation = restoring.value
    && restorePostActionSequence !== restoreActionSequence
  if (!pendingRestorePreview && !pendingRestoreConfirmation) {
    return
  }
  if (pendingRestoreConfirmation) {
    invalidateRestoreAction()
  }
  restorePreviewRequestSequence = null
  closeDetail(true)
  toast.warning(t('agentSnapshot.mutationBusy'))
}, { flush: 'sync' })

async function openPanel() {
  const requestId = ++snapshotRequestSequence
  // The first page must be unanchored so that a stale parent page cannot hide
  // versions created by another client. The response establishes a stable
  // anchor for all subsequent pages in this panel session.
  historyAnchorVersionNo.value = null
  page.value = 1
  snapshots.value = []
  await loadSnapshots(true, requestId)
}

async function loadSnapshots(reset = false, requestId = snapshotRequestSequence) {
  if (!props.agentId) {
    snapshots.value = []
    total.value = 0
    return
  }

  try {
    loading.value = true
    const nextPage = reset ? 1 : page.value
    const params: Record<string, number> = {
      page: nextPage,
      limit,
    }
    if (!reset && historyAnchorVersionNo.value) {
      params.maxVersionNo = historyAnchorVersionNo.value
    }
    const result = await getAgentSnapshots(props.agentId, params)
    if (!isActiveSnapshotRequest(requestId)) {
      return
    }
    const responseRows = result?.list || []
    if (reset) {
      historyAnchorVersionNo.value = responseRows[0]?.versionNo || null
    }
    const rows = decorateSnapshotRows(responseRows)
    const mergedRows = reset ? rows : [...snapshots.value, ...rows]
    snapshots.value = attachPreviousRows(mergedRows)
    total.value = result?.total || 0
    page.value = nextPage + 1
  }
  catch (error) {
    if (!isActiveSnapshotRequest(requestId)) {
      return
    }
    console.error('Failed to load snapshots:', error)
    toast.error(t('agentSnapshot.fetchFailed'))
  }
  finally {
    if (isActiveSnapshotRequest(requestId)) {
      loading.value = false
    }
  }
}

function isActiveSnapshotRequest(requestId: number) {
  return props.visible && requestId === snapshotRequestSequence
}

function invalidateSnapshotRequest() {
  snapshotRequestSequence += 1
  loading.value = false
}

function decorateSnapshotRows(rows: AgentSnapshot[]): SnapshotRow[] {
  return rows.map(row => ({
    ...row,
    isLatestSnapshot: Boolean(historyAnchorVersionNo.value && row.versionNo === historyAnchorVersionNo.value),
  }))
}

function attachPreviousRows(rows: SnapshotRow[]) {
  return rows.map((row) => {
    const previousRow = findPreviousSnapshotRow(row, rows)
    return {
      ...row,
      previousSnapshotId: previousRow?.id || null,
      previousVersionNo: previousRow?.versionNo || null,
    }
  })
}

function findPreviousSnapshotRow(row: SnapshotRow, rows: SnapshotRow[]) {
  const versionNo = Number(row.versionNo)
  if (!Number.isFinite(versionNo)) {
    return null
  }
  return rows.find(item => Number(item.versionNo) < versionNo) || null
}

async function viewSnapshot(row: SnapshotRow) {
  detailVisible.value = true
  const requestId = ++detailRequestSequence
  detailLoading.value = true
  currentDetail.value = null
  try {
    const metadataRequest = ensureMetadata()
    const detail = await buildSavedVersionDetail(row)
    if (!isActiveDetailRequest(requestId)) {
      return
    }
    currentDetail.value = detail
    // Names are enhancement metadata. Render the snapshot immediately with
    // stable IDs, then update names reactively as metadata arrives.
    void Promise.allSettled([
      metadataRequest,
      ensureDisplayMetadata(detail.beforeData, detail.afterData),
    ])
  }
  catch (error) {
    if (!isActiveDetailRequest(requestId)) {
      return
    }
    console.error('Failed to load snapshot detail:', error)
    toast.error(t('agentSnapshot.detailFailed'))
    detailVisible.value = false
  }
  finally {
    if (isActiveDetailRequest(requestId)) {
      detailLoading.value = false
    }
  }
}

async function previewRestoreSnapshot(row: SnapshotRow) {
  if (!canRestoreSnapshot(row)) {
    return
  }
  if (props.mutationBusy) {
    toast.warning(t('agentSnapshot.mutationBusy'))
    return
  }
  detailVisible.value = true
  const requestId = ++detailRequestSequence
  restorePreviewRequestSequence = requestId
  detailLoading.value = true
  currentDetail.value = null
  try {
    const metadataRequest = ensureMetadata()
    const targetSnapshot = await getAgentSnapshot(props.agentId, row.id)
    if (!isActiveDetailRequest(requestId)) {
      return
    }
    if (!isPlainObject(targetSnapshot.currentSnapshotData)) {
      throw new Error('Snapshot detail is missing the atomic current-state data')
    }
    const detail: VersionDetail = {
      mode: 'restore',
      single: false,
      row: {
        ...row,
        id: targetSnapshot.id || row.id,
      },
      beforeData: targetSnapshot.currentSnapshotData,
      afterData: targetSnapshot.snapshotData || {},
      changedFields: [],
      fieldOrder: targetSnapshot.fieldOrder || [],
      forceCompare: true,
      beforeVersionNo: historyAnchorVersionNo.value || props.currentVersionNo,
      afterVersionNo: targetSnapshot.versionNo,
      currentStateToken: targetSnapshot.currentStateToken,
    }
    currentDetail.value = detail
    void Promise.allSettled([
      metadataRequest,
      ensureDisplayMetadata(detail.beforeData, detail.afterData),
    ])
  }
  catch (error) {
    if (!isActiveDetailRequest(requestId)) {
      return
    }
    console.error('Failed to load restore preview:', error)
    toast.error(t('agentSnapshot.detailFailed'))
    detailVisible.value = false
  }
  finally {
    if (restorePreviewRequestSequence === requestId) {
      restorePreviewRequestSequence = null
    }
    if (isActiveDetailRequest(requestId)) {
      detailLoading.value = false
    }
  }
}

function isActiveDetailRequest(requestId: number) {
  return detailVisible.value && requestId === detailRequestSequence
}

function invalidateDetailRequest() {
  detailRequestSequence += 1
  detailLoading.value = false
  currentDetail.value = null
}

function closeDetail(force = false) {
  if (restoring.value && !force) {
    return
  }
  if (detailVisible.value) {
    detailVisible.value = false
    return
  }
  invalidateDetailRequest()
}

async function buildSavedVersionDetail(row: SnapshotRow): Promise<VersionDetail> {
  const selectedSnapshot = await getAgentSnapshot(props.agentId, row.id)
  const previousSnapshot = await fetchPreviousSnapshot(row)
  if (previousSnapshot?.snapshotData) {
    const adjacentVersion = Number(selectedSnapshot.versionNo) - Number(previousSnapshot.versionNo) === 1
    return {
      mode: 'view',
      single: false,
      row,
      beforeData: previousSnapshot.snapshotData || {},
      afterData: selectedSnapshot.snapshotData || {},
      changedFields: adjacentVersion ? (selectedSnapshot.changedFields || row.changedFields || []) : [],
      fieldOrder: selectedSnapshot.fieldOrder || previousSnapshot.fieldOrder || row.fieldOrder || [],
      forceCompare: !adjacentVersion,
      beforeVersionNo: previousSnapshot.versionNo,
      afterVersionNo: selectedSnapshot.versionNo,
    }
  }

  return {
    mode: 'view',
    single: true,
    row,
    beforeData: {},
    afterData: selectedSnapshot.snapshotData || {},
    changedFields: selectedSnapshot.changedFields || row.changedFields || [],
    fieldOrder: selectedSnapshot.fieldOrder || row.fieldOrder || [],
    afterVersionNo: selectedSnapshot.versionNo,
  }
}

async function fetchPreviousSnapshot(row: SnapshotRow) {
  if (row.previousSnapshotId) {
    return getAgentSnapshot(props.agentId, row.previousSnapshotId)
  }
  if (!row.versionNo || row.versionNo <= 1) {
    return null
  }
  const result = await getAgentSnapshots(props.agentId, {
    page: 1,
    limit: 1,
    maxVersionNo: row.versionNo - 1,
  })
  const previousRow = result?.list?.[0]
  if (!previousRow?.id) {
    return null
  }
  return getAgentSnapshot(props.agentId, previousRow.id)
}

async function confirmRestoreSnapshot() {
  const detail = currentDetail.value
  if (restoring.value || !detail || detail.mode !== 'restore' || !detail.row?.id) {
    return
  }
  if (props.mutationBusy) {
    toast.warning(t('agentSnapshot.mutationBusy'))
    return
  }
  if (!detailItems.value.length) {
    toast.info(t('agentSnapshot.noRestoreNeeded'))
    return
  }
  const currentStateToken = detail.currentStateToken?.trim()
  if (!currentStateToken) {
    console.error('Cannot restore snapshot without a current-state token')
    toast.error(t('agentSnapshot.restoreFailed'))
    return
  }
  const context: RestoreActionContext = {
    actionSequence: ++restoreActionSequence,
    agentId: props.agentId,
    snapshotId: detail.row.id,
    currentStateToken,
    detailRequestSequence,
    willClearChatHistory: restoreWillClearChatHistory.value,
  }
  // Enter the busy state before either confirmation can yield. This prevents
  // rapid taps from opening duplicate dialogs or issuing duplicate restores.
  restoring.value = true
  try {
    if (props.hasUnsavedChanges) {
      const confirmed = await requestRestoreConfirmation({
        title: t('agentSnapshot.unsavedChangesTitle'),
        msg: t('agentSnapshot.unsavedChangesWarning'),
        confirmButtonText: t('agentSnapshot.discardAndRestore'),
        cancelButtonText: t('common.cancel'),
      })
      if (!confirmed || !isActiveRestoreAction(context)) {
        return
      }
    }

    // This confirmation must be the last user interaction before the POST.
    // It is intentionally separate from the unsaved-form confirmation because
    // clearing chat history is irreversible and outside snapshot recovery.
    if (context.willClearChatHistory) {
      const confirmed = await requestRestoreConfirmation({
        title: t('agentSnapshot.confirmRestore'),
        msg: t('agentSnapshot.restoreChatHistoryDestructiveWarning'),
        confirmButtonText: t('agentSnapshot.confirmRestore'),
        cancelButtonText: t('common.cancel'),
      })
      if (!confirmed || !isActiveRestoreAction(context)) {
        return
      }
    }

    if (!isActiveRestoreAction(context)) {
      return
    }
    // Mark the irreversible request boundary only after the final mutation
    // guard. A later parent busy transition must not pretend this POST was
    // canceled; its real response still owns the terminal UI state.
    restorePostActionSequence = context.actionSequence
    await restoreAgentSnapshot(context.agentId, context.snapshotId, context.currentStateToken)
    if (!isActiveRestoreAction(context)) {
      return
    }
    toast.success(t('agentSnapshot.restoreSuccess'))
    closeDetail(true)
    emit('restored', {
      agentId: context.agentId,
      actionSequence: context.actionSequence,
    })
    if (props.visible && props.agentId === context.agentId) {
      await openPanel()
    }
  }
  catch (error) {
    if (isActiveRestoreAction(context)) {
      console.error('Failed to restore snapshot:', error)
      toast.error(t('agentSnapshot.restoreFailed'))
    }
  }
  finally {
    if (restorePostActionSequence === context.actionSequence) {
      restorePostActionSequence = null
    }
    if (context.actionSequence === restoreActionSequence) {
      restoring.value = false
    }
  }
}

async function requestRestoreConfirmation(options: Parameters<typeof message.confirm>[0]) {
  try {
    await message.confirm(options)
    return true
  }
  catch {
    return false
  }
}

function isActiveRestoreAction(context: RestoreActionContext) {
  const detail = currentDetail.value
  return restoring.value
    && context.actionSequence === restoreActionSequence
    && (!props.mutationBusy || restorePostActionSequence === context.actionSequence)
    && context.agentId === props.agentId
    && props.visible
    && detailVisible.value
    && context.detailRequestSequence === detailRequestSequence
    && detail?.mode === 'restore'
    && detail.row?.id === context.snapshotId
    && detail.currentStateToken?.trim() === context.currentStateToken
}

function invalidateRestoreAction() {
  restoreActionSequence += 1
  restoring.value = false
}

function deleteSnapshot(row: SnapshotRow) {
  message.confirm({
    title: t('agentSnapshot.delete'),
    msg: t('agentSnapshot.deleteConfirm', { version: row.versionNo }),
  }).then(async () => {
    deletingSnapshotId.value = row.id
    try {
      await deleteAgentSnapshot(props.agentId, row.id)
      toast.success(t('agentSnapshot.deleteSuccess'))
      await openPanel()
    }
    catch (error) {
      console.error('Failed to delete snapshot:', error)
      toast.error(t('agentSnapshot.deleteFailed'))
    }
    finally {
      deletingSnapshotId.value = ''
    }
  }).catch(() => {})
}

function canRestoreSnapshot(row: SnapshotRow) {
  return !!row?.id && !row.isLatestSnapshot
}

function canDeleteSnapshot(row: SnapshotRow) {
  return !!row?.id && !row.isLatestSnapshot
}

function buildDetailItems(detail: VersionDetail): DetailItem[] {
  if (detail.single) {
    return snapshotFieldOrder(detail.fieldOrder, {}, detail.afterData).map((field) => {
      const afterValue = getFieldValue(detail.afterData, field)
      return {
        field,
        label: fieldLabel(field),
        beforeText: '',
        afterText: formatDisplayValue(field, afterValue, detail.afterData),
        single: true,
        recordedOnly: false,
        redactedDifference: false,
      }
    })
  }

  return resolveDiffFields(
    detail.beforeData,
    detail.afterData,
    detail.changedFields,
    detail.fieldOrder,
    detail.forceCompare,
  ).map((field) => {
    const beforeValue = getFieldValue(detail.beforeData, field)
    const afterValue = getFieldValue(detail.afterData, field)
    const beforeText = formatDisplayValue(field, beforeValue, detail.beforeData)
    const afterText = formatDisplayValue(field, afterValue, detail.afterData)
    return {
      field,
      label: fieldLabel(field),
      beforeText,
      afterText,
      single: false,
      recordedOnly: !detail.forceCompare && isSameFieldValue(field, beforeValue, afterValue),
      redactedDifference: !isSameFieldValue(field, beforeValue, afterValue)
        && beforeText === afterText
        && beforeText.includes(t('agentSnapshot.secretRedacted')),
    }
  })
}

function resolveDiffFields(
  beforeData: AgentSnapshotData,
  afterData: AgentSnapshotData,
  changedFields: string[] = [],
  fieldOrder: string[] = [],
  forceCompare = false,
) {
  const orderedFields = snapshotFieldOrder(fieldOrder, beforeData, afterData)
  const storedFields = Array.isArray(changedFields) ? changedFields : []
  const directFields = storedFields
    .filter(field => field && field !== 'initial' && field !== 'restore')
    .map(canonicalField)
  const candidates = forceCompare ? orderedFields : directFields

  const uniqueCandidates = Array.from(new Set(candidates))
  if (!forceCompare) {
    // changedFields is an immutable fact about the saved event. Re-running
    // today's comparison rules would make old events disappear from detail.
    return uniqueCandidates
  }
  return uniqueCandidates.filter((field) => {
    return !isSameFieldValue(
      field,
      getFieldValue(beforeData, field),
      getFieldValue(afterData, field),
    )
  })
}

function snapshotFieldOrder(fieldOrder: string[] = [], beforeData: AgentSnapshotData = {}, afterData: AgentSnapshotData = {}) {
  const fields = [
    ...fieldOrder,
    ...SNAPSHOT_FIELD_ORDER,
  ].map(canonicalField)
  return Array.from(new Set(fields)).filter((field) => {
    const beforeValue = getFieldValue(beforeData, field)
    const afterValue = getFieldValue(afterData, field)
    return beforeValue !== undefined || afterValue !== undefined
  })
}

function canonicalField(field: string) {
  return field === 'tags' || field === 'tagIds' ? 'tagNames' : field
}

function getFieldValue(data: AgentSnapshotData, field: string) {
  const canonicalName = canonicalField(field)
  if (canonicalName === 'tagNames') {
    return data?.tagNames ?? data?.tags?.map(tag => tag.tagName).filter(Boolean)
  }
  return data?.[canonicalName]
}

function formatDisplayValue(field: string, value: any, rowData: AgentSnapshotData = {}) {
  if (value === SNAPSHOT_SECRET_REDACTED) {
    return t('agentSnapshot.secretRedacted')
  }
  if (value === null || value === undefined || value === '') {
    return t('agentSnapshot.emptyValue')
  }
  if (MODEL_FIELD_TYPES[field]) {
    return modelNameMap.value[String(value)] || translatedFallback(`agentSnapshot.model.${value}`, String(value))
  }
  if (field === 'ttsVoiceId') {
    return voiceNameMap.value[String(value)] || translatedFallback(`agentSnapshot.voice.${value}`, String(value))
  }
  if (field === 'chatHistoryConf') {
    return t(CHAT_HISTORY_CONF_LABEL_KEYS[String(value)] || 'agentSnapshot.emptyValue')
  }
  if (field === 'functions') {
    return formatFunctions(value)
  }
  if (field === 'contextProviders') {
    return formatContextProviders(value)
  }
  if (field === 'correctWordFileIds') {
    return formatCorrectWordFileIds(value)
  }
  if (field === 'tagNames') {
    return formatStringList(value)
  }
  if (Array.isArray(value)) {
    return formatArrayValue(value)
  }
  if (typeof value === 'object') {
    return stablePrettyStringify(redactDisplayValue(value))
  }
  if (field === 'ttsLanguage' && !value && rowData.ttsVoiceId) {
    return t('agentSnapshot.emptyValue')
  }
  return String(value)
}

function formatFunctions(value: any) {
  if (!Array.isArray(value) || value.length === 0) {
    return t('agentSnapshot.emptyValue')
  }
  return value.map((item) => {
    const pluginId = item?.pluginId || item?.id || ''
    const name = pluginNameMap.value[pluginId] || translatedFallback(`agentSnapshot.plugin.${pluginId}`, pluginId || t('agentSnapshot.emptyValue'))
    const params = parseObjectValue(item?.paramInfo ?? item?.params)
    const safeParams = redactDisplayValue(params)
    return Object.keys(safeParams).length
      ? `${name}\n${stablePrettyStringify(safeParams)}`
      : name
  }).join('\n')
}

function formatContextProviders(value: any) {
  if (!Array.isArray(value) || value.length === 0) {
    return t('agentSnapshot.emptyValue')
  }
  return value.map((item, index) => {
    return `${index + 1}. ${stablePrettyStringify(redactDisplayValue(item))}`
  }).join('\n')
}

function formatCorrectWordFileIds(value: any) {
  if (!Array.isArray(value) || value.length === 0) {
    return t('agentSnapshot.emptyValue')
  }
  return formatLocalizedList(value.map(id => correctWordNameMap.value[id] || id))
}

function formatStringList(value: any) {
  if (!Array.isArray(value) || value.length === 0) {
    return t('agentSnapshot.emptyValue')
  }
  return formatLocalizedList(value)
}

function formatArrayValue(value: any[]) {
  if (!value.length) {
    return t('agentSnapshot.emptyValue')
  }
  if (value.every(item => item === null || ['string', 'number', 'boolean'].includes(typeof item))) {
    return formatLocalizedList(value)
  }
  return stablePrettyStringify(redactDisplayValue(value))
}

async function ensureMetadata() {
  if (metadataLoaded.value) {
    return
  }
  const modelResults = await Promise.allSettled(
    MODEL_TYPES.map(async (modelType) => {
      const options = await getModelOptions(modelType)
      options.forEach((option) => {
        modelNameMap.value[option.id] = option.modelName
      })
    }),
  )
  modelResults.forEach((result) => {
    if (result.status === 'rejected') {
      console.warn('Failed to load model metadata:', result.reason)
    }
  })

  try {
    const plugins = await getPluginFunctions()
    plugins.forEach((plugin) => {
      pluginNameMap.value[plugin.id] = plugin.name
    })
  }
  catch (error) {
    console.warn('Failed to load plugin metadata:', error)
  }
  metadataLoaded.value = true
}

async function ensureVoiceMetadata(...snapshots: AgentSnapshotData[]) {
  const ttsModelIds = snapshots
    .map(snapshot => snapshot?.ttsModelId)
    .filter((modelId): modelId is string => Boolean(modelId && !loadedVoiceModelIds.value[modelId]))
  const uniqueModelIds = Array.from(new Set(ttsModelIds))
  await Promise.allSettled(uniqueModelIds.map(async (modelId) => {
    const voices = await getTTSVoices(modelId)
    voices.forEach((voice) => {
      voiceNameMap.value[voice.id] = voice.name
    })
    loadedVoiceModelIds.value[modelId] = true
  }))
}

async function ensureDisplayMetadata(...snapshots: AgentSnapshotData[]) {
  await Promise.all([
    ensureVoiceMetadata(...snapshots),
    ensureCorrectWordMetadata(...snapshots),
  ])
}

async function ensureCorrectWordMetadata(...snapshots: AgentSnapshotData[]) {
  const hasCorrectWordIds = snapshots.some((snapshot) => {
    return Array.isArray(snapshot?.correctWordFileIds) && snapshot.correctWordFileIds.length > 0
  })
  if (!hasCorrectWordIds || correctWordMetadataLoaded.value) {
    return
  }
  try {
    const files = await getCorrectWordFiles()
    files.forEach((file) => {
      if (file.id) {
        correctWordNameMap.value[file.id] = file.fileName || file.id
      }
    })
    correctWordMetadataLoaded.value = true
  }
  catch (error) {
    console.warn('Failed to load correct word metadata:', error)
  }
}

function sourceLabel(source?: string) {
  return translatedFallback(`agentSnapshot.source.${source || 'config'}`, source || '')
}

function fieldLabel(field: string) {
  return translatedFallback(`agentSnapshot.field.${field}`, field)
}

function translatedFallback(key: string, fallback: string) {
  const value = t(key)
  return value === key ? fallback : value
}

function formatVersion(versionNo?: number | null) {
  return versionNo ? `#${versionNo}` : ''
}

function formatVersionRangeTitle(label: string, beforeVersionNo?: number | null, afterVersionNo?: number | null) {
  if (beforeVersionNo && afterVersionNo) {
    return `${label} #${beforeVersionNo} -> #${afterVersionNo}`
  }
  if (beforeVersionNo) {
    return `${label} #${beforeVersionNo}`
  }
  if (afterVersionNo) {
    return `${label} #${afterVersionNo}`
  }
  return label
}

function formatTime(time?: string) {
  if (!time) {
    return '-'
  }
  const date = new Date(String(time).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) {
    return String(time)
  }
  try {
    return new Intl.DateTimeFormat(toIntlLocale(getCurrentLanguage()), {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(date)
  }
  catch {
    const pad = (value: number) => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  }
}

function formatLocalizedList(values: any[]) {
  const items = values.map(value => String(value))
  try {
    return new Intl.ListFormat(toIntlLocale(getCurrentLanguage()), {
      style: 'short',
      type: 'conjunction',
    }).format(items)
  }
  catch {
    return items.join(getCurrentLanguage().startsWith('zh_') ? '、' : ', ')
  }
}

function isSameFieldValue(
  field: string,
  left: any,
  right: any,
) {
  return isEquivalentValue(
    normalizeValueForField(field, left),
    normalizeValueForField(field, right),
  )
}

function normalizeValueForField(field: string, value: any): any {
  if (field === 'ttsVolume' || field === 'ttsRate' || field === 'ttsPitch') {
    return normalizeDefaultTtsNumber(value)
  }
  if (field === 'summaryMemory') {
    return value === undefined || value === null || String(value).trim() === '' ? '' : String(value)
  }
  if (field === 'correctWordFileIds' || field === 'tagNames') {
    return normalizeStringList(value)
  }
  if (field === 'functions') {
    return normalizeFunctions(value)
  }
  if (field === 'contextProviders') {
    return normalizeSnapshotOrderedList(value)
  }
  return normalizeValue(value)
}

function normalizeStringList(value: any) {
  if (!Array.isArray(value)) {
    return []
  }
  return value
    .filter(item => item !== undefined && item !== null && String(item).trim() !== '')
    .map(item => String(item))
    .sort()
}

function normalizeFunctions(value: any) {
  if (!Array.isArray(value)) {
    return {}
  }
  const functions = value.reduce<Record<string, any>>((result, item) => {
    const pluginId = item?.pluginId
    if (pluginId) {
      result[String(pluginId)] = normalizeValue(parseObjectValue(item?.paramInfo ?? item?.params))
    }
    return result
  }, {})
  return normalizeValue(functions)
}

function parseObjectValue(value: any) {
  if (!value) {
    return {}
  }
  if (typeof value !== 'string') {
    return value
  }
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  }
  catch {
    return {}
  }
}

function isEquivalentValue(left: any, right: any): boolean {
  if (left === SNAPSHOT_SECRET_REDACTED || right === SNAPSHOT_SECRET_REDACTED) {
    return true
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) {
      return false
    }
    return left.every((item, index) => isEquivalentValue(item, right[index]))
  }
  if (isPlainObject(left) || isPlainObject(right)) {
    if (!isPlainObject(left) || !isPlainObject(right)) {
      return false
    }
    const keys = Array.from(new Set([...Object.keys(left), ...Object.keys(right)]))
    return keys.every(key => isEquivalentValue(left[key], right[key]))
  }
  return left === right
}

function normalizeValue(value: any): any {
  if (Array.isArray(value)) {
    return value.map(normalizeValue)
  }
  if (isPlainObject(value)) {
    return Object.keys(value).sort().reduce<Record<string, any>>((result, key) => {
      result[key] = isSensitiveKey(key) ? SNAPSHOT_SECRET_REDACTED : normalizeValue(value[key])
      return result
    }, {})
  }
  return value === undefined ? null : value
}

function isPlainObject(value: any): value is Record<string, any> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function redactDisplayValue(value: any, parentKey = ''): any {
  return redactSnapshotDisplayValue(value, t('agentSnapshot.secretRedacted'), parentKey)
}
</script>

<template>
  <wd-popup
    v-model="panelVisible"
    position="bottom"
    custom-class="agent-snapshot-popup"
    custom-style="height: 86vh; max-height: 900px;"
    :close-on-click-modal="!restoring"
    safe-area-inset-bottom
  >
    <view class="agent-snapshot-shell">
      <view class="agent-snapshot-header">
        <view class="agent-snapshot-title-block">
          <text class="block text-[34rpx] text-[#232338] font-bold">
            {{ t('agentSnapshot.title') }}
          </text>
          <text v-if="displayedCurrentVersionNo" class="mt-[6rpx] block text-[24rpx] text-[#65686f]">
            {{ t('agentSnapshot.currentVersion') }} {{ formatVersion(displayedCurrentVersionNo) }}
          </text>
        </view>
        <wd-icon name="close" size="22px" custom-class="agent-snapshot-close-icon text-[#65686f]" @click="panelVisible = false" />
      </view>

      <scroll-view scroll-y class="agent-snapshot-body">
        <view v-if="loading && !snapshots.length" class="py-[80rpx] text-center text-[26rpx] text-[#65686f]">
          {{ t('common.loading') }}
        </view>

        <view v-else-if="!snapshots.length" class="py-[120rpx] text-center">
          <text class="block text-[30rpx] text-[#232338] font-semibold">
            {{ t('agentSnapshot.empty') }}
          </text>
          <text class="mt-[10rpx] block text-[24rpx] text-[#8b8f9a]">
            {{ t('agentSnapshot.emptyTip') }}
          </text>
        </view>

        <view v-else class="flex flex-col gap-[20rpx]">
          <view
            v-for="snapshot in snapshots"
            :key="snapshot.id"
            class="border border-[#e8eaf0] rounded-[20rpx] bg-white p-[24rpx]"
          >
            <view class="flex items-start justify-between gap-[20rpx]">
              <view>
                <view class="flex items-center gap-[12rpx]">
                  <text class="text-[32rpx] text-[#232338] font-bold">
                    {{ formatVersion(snapshot.versionNo) }}
                  </text>
                  <text
                    v-if="snapshot.isLatestSnapshot"
                    class="rounded-full bg-[rgba(51,108,255,0.1)] px-[16rpx] py-[4rpx] text-[22rpx] text-[#336cff]"
                  >
                    {{ t('agentSnapshot.currentVersion') }}
                  </text>
                </view>
                <text class="mt-[8rpx] block text-[24rpx] text-[#8b8f9a]">
                  {{ formatTime(snapshot.createdAt) }} · {{ sourceLabel(snapshot.source) }}
                </text>
              </view>
            </view>

            <view class="mt-[18rpx] flex flex-wrap gap-[10rpx]">
              <text
                v-for="field in snapshot.changedFields || []"
                :key="field"
                class="rounded-full bg-[#f5f7fb] px-[16rpx] py-[6rpx] text-[22rpx] text-[#4d5566]"
              >
                {{ fieldLabel(field) }}
              </text>
              <text v-if="!(snapshot.changedFields || []).length" class="text-[24rpx] text-[#9d9ea3]">
                {{ t('agentSnapshot.noChangedContent') }}
              </text>
            </view>

            <view class="agent-snapshot-actions">
              <wd-button size="small" type="info" custom-class="agent-snapshot-action-button flex-1 !h-[64rpx]" @click="viewSnapshot(snapshot)">
                {{ t('agentSnapshot.view') }}
              </wd-button>
              <wd-button
                v-if="canRestoreSnapshot(snapshot)"
                size="small"
                type="primary"
                :disabled="mutationBusy"
                custom-class="agent-snapshot-action-button flex-1 !h-[64rpx] !bg-[#336cff]"
                @click="previewRestoreSnapshot(snapshot)"
              >
                {{ t('agentSnapshot.restore') }}
              </wd-button>
              <wd-button
                v-if="canDeleteSnapshot(snapshot)"
                size="small"
                type="error"
                :loading="deletingSnapshotId === snapshot.id"
                custom-class="agent-snapshot-action-button flex-1 !h-[64rpx]"
                @click="deleteSnapshot(snapshot)"
              >
                {{ t('agentSnapshot.delete') }}
              </wd-button>
            </view>
          </view>

          <wd-button
            v-if="hasMore"
            type="info"
            plain
            :loading="loading"
            custom-class="mt-[8rpx] !h-[72rpx]"
            @click="loadSnapshots(false)"
          >
            {{ t('agentSnapshot.loadMore') }}
          </wd-button>
        </view>
      </scroll-view>
    </view>
  </wd-popup>

  <wd-popup
    v-model="detailPopupVisible"
    position="bottom"
    custom-class="agent-snapshot-popup"
    custom-style="height: 88vh; max-height: 940px;"
    :close-on-click-modal="!restoring"
    safe-area-inset-bottom
  >
    <view class="agent-snapshot-shell">
      <view class="agent-snapshot-header">
        <text class="agent-snapshot-detail-title">
          {{ detailTitle }}
        </text>
        <wd-icon name="close" size="22px" custom-class="agent-snapshot-close-icon text-[#65686f]" @click="closeDetail()" />
      </view>

      <scroll-view scroll-y class="agent-snapshot-body">
        <view v-if="detailLoading" class="py-[80rpx] text-center text-[26rpx] text-[#65686f]">
          {{ t('common.loading') }}
        </view>

        <view v-else-if="!detailItems.length" class="py-[120rpx] text-center text-[26rpx] text-[#8b8f9a]">
          {{ t('agentSnapshot.noChangedContent') }}
        </view>

        <view v-else class="flex flex-col gap-[18rpx]">
          <view
            v-for="item in detailItems"
            :key="item.field"
            class="border border-[#e8eaf0] rounded-[20rpx] bg-white"
          >
            <view class="border-b border-[#f0f1f5] px-[22rpx] py-[18rpx]">
              <text class="text-[28rpx] text-[#232338] font-semibold">
                {{ item.label }}
              </text>
              <text v-if="item.recordedOnly" class="ml-[10rpx] text-[22rpx] text-[#8b8f9a]">
                {{ t('agentSnapshot.recordedChange') }}
              </text>
              <text v-if="item.redactedDifference" class="ml-[10rpx] text-[22rpx] text-[#a06a1f]">
                {{ t('agentSnapshot.redactedValueChanged') }}
              </text>
            </view>

            <view v-if="item.single" class="p-[22rpx]">
              <text class="mb-[10rpx] block text-[23rpx] text-[#8b8f9a]">
                {{ t('agentSnapshot.configValue') }}
              </text>
              <text class="block whitespace-pre-wrap break-all rounded-[14rpx] bg-[#f5f9f4] p-[18rpx] text-[25rpx] text-[#27653a] leading-[1.6]">
                {{ item.afterText }}
              </text>
            </view>

            <view v-else class="grid grid-cols-1 gap-[14rpx] p-[22rpx]">
              <view>
                <text class="mb-[10rpx] block text-[23rpx] text-[#8b8f9a]">
                  {{ currentDetail?.mode === 'restore' ? t('agentSnapshot.beforeRestore') : t('agentSnapshot.beforeChange') }}
                </text>
                <text class="block whitespace-pre-wrap break-all rounded-[14rpx] bg-[#fff7f7] p-[18rpx] text-[25rpx] text-[#7a3b3b] leading-[1.6]">
                  {{ item.beforeText }}
                </text>
              </view>
              <view>
                <text class="mb-[10rpx] block text-[23rpx] text-[#8b8f9a]">
                  {{ currentDetail?.mode === 'restore' ? t('agentSnapshot.afterRestore') : t('agentSnapshot.afterChange') }}
                </text>
                <text class="block whitespace-pre-wrap break-all rounded-[14rpx] bg-[#f5f9f4] p-[18rpx] text-[25rpx] text-[#27653a] leading-[1.6]">
                  {{ item.afterText }}
                </text>
              </view>
            </view>
          </view>

          <view
            v-if="currentDetail?.mode === 'restore'"
            class="rounded-[18rpx] bg-[rgba(51,108,255,0.08)] p-[22rpx] text-[24rpx] text-[#3557a8] leading-[1.6]"
          >
            {{ t('agentSnapshot.restoreConfirm', { version: currentDetail.afterVersionNo || '' }) }}
          </view>
          <view
            v-if="currentDetail?.mode === 'restore' && hasUnsavedChanges"
            class="rounded-[18rpx] bg-[rgba(245,108,108,0.1)] p-[22rpx] text-[24rpx] text-[#a34848] leading-[1.6]"
          >
            {{ t('agentSnapshot.unsavedChangesWarning') }}
          </view>
          <view
            v-if="restoreWillClearChatHistory"
            class="rounded-[18rpx] bg-[rgba(245,108,108,0.1)] p-[22rpx] text-[24rpx] text-[#a34848] leading-[1.6]"
          >
            {{ t('agentSnapshot.restoreChatHistoryDestructiveWarning') }}
          </view>
        </view>
      </scroll-view>

      <view
        v-if="currentDetail?.mode === 'restore'"
        class="agent-snapshot-footer"
      >
        <wd-button type="info" :disabled="restoring" custom-class="agent-snapshot-footer-button flex-1 !h-[78rpx]" @click="closeDetail()">
          {{ t('common.cancel') }}
        </wd-button>
        <wd-button
          type="primary"
          :loading="restoring"
          :disabled="restoring || !canConfirmRestore"
          custom-class="agent-snapshot-footer-button flex-1 !h-[78rpx] !bg-[#336cff]"
          @click="confirmRestoreSnapshot"
        >
          {{ t('agentSnapshot.confirmRestore') }}
        </wd-button>
      </view>
    </view>
  </wd-popup>
</template>

<style lang="scss" scoped>
:deep(.agent-snapshot-popup) {
  left: 0 !important;
  right: 0 !important;
  width: 100vw !important;
  max-width: none !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
  border-radius: 28rpx 28rpx 0 0 !important;
  background: #f5f7fb !important;
}

@media (min-width: 901px) {
  :deep(.agent-snapshot-popup) {
    width: calc(100vw - 32px) !important;
    max-width: 760px !important;
    margin: 0 auto !important;
  }
}

.agent-snapshot-shell {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f7fb;
}

.agent-snapshot-header {
  box-sizing: border-box;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32rpx 32rpx 24rpx;
  background: #fff;
  border-bottom: 1rpx solid #e8eaf0;
}

.agent-snapshot-title-block {
  min-width: 0;
}

.agent-snapshot-detail-title {
  min-width: 0;
  flex: 1;
  padding-right: 20rpx;
  color: #232338;
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.35;
  word-break: break-all;
}

.agent-snapshot-body {
  box-sizing: border-box;
  min-height: 0;
  flex: 1;
  padding: 22rpx 24rpx 28rpx;
}

.agent-snapshot-actions {
  display: flex;
  gap: 14rpx;
  margin-top: 22rpx;
}

.agent-snapshot-footer {
  box-sizing: border-box;
  flex-shrink: 0;
  display: flex;
  gap: 16rpx;
  padding: 24rpx;
  background: #fff;
  border-top: 1rpx solid #e8eaf0;
}

:deep(.agent-snapshot-close-icon) {
  flex-shrink: 0;
}

:deep(.agent-snapshot-action-button),
:deep(.agent-snapshot-footer-button) {
  min-width: 0 !important;
}

:deep(.agent-snapshot-action-button .wd-button__content),
:deep(.agent-snapshot-footer-button .wd-button__content) {
  min-width: 0;
}

:deep(.agent-snapshot-action-button .wd-button__text),
:deep(.agent-snapshot-footer-button .wd-button__text) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
