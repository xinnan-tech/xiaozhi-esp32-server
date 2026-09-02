/* eslint-disable test/no-import-node-test -- zero-dependency source contract gate */
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const panelSource = await readFile(new URL('./AgentSnapshotPanel.vue', import.meta.url), 'utf8')
const editSource = await readFile(new URL('../edit.vue', import.meta.url), 'utf8')

function sourceBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `missing start marker: ${startMarker}`)
  assert.notEqual(end, -1, `missing end marker: ${endMarker}`)
  return source.slice(start, end)
}

test('restore enters busy state before confirmations and requires a final destructive confirmation', () => {
  const restore = sourceBetween(
    panelSource,
    'async function confirmRestoreSnapshot()',
    'async function requestRestoreConfirmation',
  )
  const busyIndex = restore.indexOf('restoring.value = true')
  const unsavedConfirmIndex = restore.indexOf('title: t(\'agentSnapshot.unsavedChangesTitle\')')
  const destructiveConfirmIndex = restore.indexOf('msg: t(\'agentSnapshot.restoreChatHistoryDestructiveWarning\')')
  const postIndex = restore.indexOf('await restoreAgentSnapshot(')

  assert.ok(busyIndex >= 0 && busyIndex < unsavedConfirmIndex)
  assert.ok(destructiveConfirmIndex > unsavedConfirmIndex && destructiveConfirmIndex < postIndex)
  assert.match(restore, /if \(context\.willClearChatHistory\)/)
  assert.match(restore.slice(destructiveConfirmIndex, postIndex), /isActiveRestoreAction\(context\)/)
  const finalMutationGuardIndex = restore.lastIndexOf('if (!isActiveRestoreAction(context))', postIndex)
  const postBoundaryIndex = restore.indexOf('restorePostActionSequence = context.actionSequence')
  assert.ok(finalMutationGuardIndex > destructiveConfirmIndex)
  assert.ok(finalMutationGuardIndex < postBoundaryIndex && postBoundaryIndex < postIndex)
})
test('restore guards popup exits and stale action completion', () => {
  assert.match(panelSource, /if \(!value && restoring\.value\) \{\s*return\s*\}/)
  assert.equal((panelSource.match(/:close-on-click-modal="!restoring"/g) || []).length, 2)
  assert.match(panelSource, /function closeDetail\(force = false\) \{\s*if \(restoring\.value && !force\)/)
  assert.match(panelSource, /context\.agentId === props\.agentId/)
  assert.match(panelSource, /context\.detailRequestSequence === detailRequestSequence/)
  assert.match(panelSource, /if \(!isActiveRestoreAction\(context\)\) \{\s*return\s*\}\s*toast\.success/)
  assert.match(panelSource, /mutationBusy\?: boolean/)
  assert.match(panelSource, /&& !props\.mutationBusy[\s\S]*currentDetail\.value\?\.mode === 'restore'/)
  assert.match(panelSource, /&& \(!props\.mutationBusy \|\| restorePostActionSequence === context\.actionSequence\)/)
  assert.match(panelSource, /if \(restorePostInFlight\) \{\s*return\s*\}/)
})

test('post-restore detail and tag reload fail closed before save', () => {
  const save = sourceBetween(editSource, 'async function saveAgent()', 'function loadPluginFunctions()')
  const reload = sourceBetween(
    editSource,
    'async function reloadAgentAfterSnapshotRestore',
    'function isActiveSnapshotReload',
  )

  assert.ok(save.indexOf('if (snapshotReloadBlocked.value)') < save.indexOf('await updateAgent('))
  assert.match(reload, /snapshotReloadBlocked\.value = true/)
  assert.match(reload, /Promise\.all\(\[\s*getAgentDetail\(targetAgentId\),\s*getAgentTags\(targetAgentId\)/)
  assert.ok(reload.indexOf('const [detail, tags] = await Promise.all') < reload.indexOf('applyPersistedAgentDetail('))
  assert.match(reload, /snapshotReloadFailed\.value = true/)
  assert.match(editSource, /:disabled="saving \|\| ttsOptionsLoading \|\| snapshotReloadBlocked"/)
  assert.match(editSource, /v-if="snapshotReloadFailed"[\s\S]*@click="retrySnapshotReload"/)
})

test('parent mutations guard history opening and propagate into every restore gate', () => {
  const opener = sourceBetween(editSource, 'function openSnapshotPanel()', 'function isSameStringList')
  const restore = sourceBetween(
    panelSource,
    'async function confirmRestoreSnapshot()',
    'async function requestRestoreConfirmation',
  )

  assert.match(opener, /if \(saving\.value \|\| snapshotReloadBlocked\.value\) \{[\s\S]*return/)
  assert.match(editSource, /:disabled="saving \|\| snapshotReloadBlocked"[\s\S]*@click="openSnapshotPanel"/)
  assert.match(editSource, /:mutation-busy="saving \|\| snapshotReloadBlocked"/)
  assert.match(restore, /if \(props\.mutationBusy\) \{[\s\S]*return/)
  const postIndex = restore.indexOf('await restoreAgentSnapshot(')
  const finalGate = restore.lastIndexOf('if (!isActiveRestoreAction(context))', postIndex)
  assert.ok(finalGate >= 0 && finalGate < postIndex)
})

test('the latest snapshot hides restore and delete actions', () => {
  const restoreGate = sourceBetween(
    panelSource,
    'function canRestoreSnapshot(row: SnapshotRow)',
    'function canDeleteSnapshot(row: SnapshotRow)',
  )
  const deleteGate = sourceBetween(
    panelSource,
    'function canDeleteSnapshot(row: SnapshotRow)',
    'function buildDetailItems',
  )

  assert.match(restoreGate, /!!row\?\.id && !row\.isLatestSnapshot/)
  assert.match(deleteGate, /!!row\?\.id && !row\.isLatestSnapshot/)
  assert.match(panelSource, /v-if="canRestoreSnapshot\(snapshot\)"/)
  assert.match(
    panelSource,
    /async function previewRestoreSnapshot\(row: SnapshotRow\) \{\s*if \(!canRestoreSnapshot\(row\)\) \{\s*return/,
  )
})
