/* eslint-disable test/no-import-node-test -- zero-dependency API regression gate */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const agentApiSource = await readFile(new URL("./agent.js", import.meta.url), "utf8");
const snapshotDialogSource = await readFile(
  new URL("../../components/AgentSnapshotDialog.vue", import.meta.url),
  "utf8"
);

function sourceBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  assert.notEqual(start, -1, `missing source marker: ${startMarker}`);
  assert.notEqual(end, -1, `missing source marker: ${endMarker}`);
  return source.slice(start, end);
}

test("snapshot restore sends the preview token once without an automatic replay", () => {
  const source = sourceBetween(
    agentApiSource,
    "restoreAgentSnapshot(agentId",
    "// 删除智能体配置快照"
  );

  assert.match(source, /restoreAgentSnapshot\(agentId, snapshotId, currentStateToken, callback, onTerminalFailure\)/);
  assert.match(source, /\.method\('POST'\)/);
  assert.match(source, /\.data\(\{ currentStateToken \}\)/);
  assert.match(source, /terminateCallbackRequest\(onTerminalFailure, error\)/);
  assert.doesNotMatch(source, /retryCallbackRequest|RequestService\.reAjaxFun|this\.restoreAgentSnapshot/);
});

test("snapshot deletion terminates on network failure without an automatic replay", () => {
  const source = sourceBetween(
    agentApiSource,
    "deleteAgentSnapshot(agentId",
    "// 新增方法：获取智能体模板"
  );

  assert.match(source, /deleteAgentSnapshot\(agentId, snapshotId, callback, onTerminalFailure\)/);
  assert.match(source, /\.method\('DELETE'\)/);
  assert.match(source, /terminateCallbackRequest\(onTerminalFailure, error\)/);
  assert.doesNotMatch(source, /retryCallbackRequest|RequestService\.reAjaxFun|this\.deleteAgentSnapshot/);
});

test("restore preview uses the state data and token from one snapshot-detail response", () => {
  const source = sourceBetween(
    snapshotDialogSource,
    "restoreSnapshot(row)",
    "decorateSnapshotRows(rows)"
  );

  assert.match(source, /this\.fetchSnapshotDetail\(row\.id\)\.then\(\(targetSnapshot\)/);
  assert.match(source, /beforeSnapshotData: targetSnapshot\.currentSnapshotData/);
  assert.match(source, /hasValidCurrentStateToken\(targetSnapshot\.currentStateToken\)/);
  assert.doesNotMatch(source, /fetchCurrentAgentData|fetchCurrentAgentTags|Promise\.all/);
});

test("snapshot dialogs cannot close while a restore request is in flight", () => {
  const guardedDialogs = snapshotDialogSource.match(/:before-close="guardRestoreInFlightClose"/g) || [];
  const hiddenCloseButtons = snapshotDialogSource.match(/:show-close="!restoring"/g) || [];
  assert.equal(guardedDialogs.length, 2);
  assert.equal(hiddenCloseButtons.length, 2);
  assert.match(
    snapshotDialogSource,
    /class="snapshot-footer-button snapshot-footer-cancel"[\s\S]*?:disabled="restoring"[\s\S]*?@click="closeRestorePreview"/
  );

  const closeMethods = sourceBetween(
    snapshotDialogSource,
    "    close() {",
    "    open() {"
  );
  assert.match(closeMethods, /close\(\) \{\s+if \(this\.restoring\) \{\s+return;/);
  assert.match(closeMethods, /guardRestoreInFlightClose\(done\) \{\s+if \(this\.restoring\) \{\s+return;[\s\S]*?done\(\);/);
  assert.match(closeMethods, /closeRestorePreview\(\) \{\s+if \(this\.restoring\) \{\s+return;[\s\S]*?this\.restorePreviewVisible = false;/);
});

test("destructive restore requires a second explicit warning before the POST", () => {
  const source = sourceBetween(
    snapshotDialogSource,
    "    confirmRestoreSnapshot() {",
    "    deleteSnapshot(row) {"
  );

  assert.match(
    source,
    /if \(!this\.restoreWillClearChatHistory\) \{\s+this\.submitRestoreSnapshot\(snapshotId, currentStateToken\);\s+return;\s+\}/
  );
  assert.match(
    source,
    /this\.\$confirm\(\s+this\.\$t\("agentSnapshot\.restoreMemoryDestructiveWarning"\),[\s\S]*?type: "error"[\s\S]*?\)\.then\(\(\) => \{[\s\S]*?this\.submitRestoreSnapshot\(snapshotId, currentStateToken, requestSeq\);/
  );
  assert.match(source, /if \(this\.restoring \|\| !this\.restorePreviewRow\) \{\s+return;/);
});

test("a terminal restore failure invalidates the atomic preview instead of replaying it", () => {
  const source = sourceBetween(
    snapshotDialogSource,
    "    submitRestoreSnapshot(snapshotId",
    "    deleteSnapshot(row) {"
  );

  assert.match(source, /else \{\s+this\.invalidateRestorePreview\(\);\s+this\.\$message\.error\(this\.restoreFailedMessage\(data\)\);/);
  assert.match(source, /\}, \(\) => \{[\s\S]*?this\.invalidateRestorePreview\(\);\s+this\.\$message\.error\(this\.\$t\("agentSnapshot\.restoreFailed"\)\);/);
  assert.match(source, /invalidateRestorePreview\(\) \{[\s\S]*?this\.restorePreviewSnapshot = null;[\s\S]*?this\.restorePreviewRow = null;/);
});

test("the latest snapshot does not expose a restore action", () => {
  const source = sourceBetween(
    snapshotDialogSource,
    "    canRestoreSnapshot(row) {",
    "    canDeleteSnapshot(row) {"
  );

  assert.match(source, /!!row\?\.id && !row\.isLatestSnapshot/);
  assert.match(snapshotDialogSource, /v-if="canRestoreSnapshot\(scope\.row\)"/);
  assert.match(
    snapshotDialogSource,
    /restoreSnapshot\(row\) \{\s+if \(!this\.canRestoreSnapshot\(row\)\) \{\s+return;/
  );
});
