<template>
  <div>
    <el-dialog
      :title="$t('agentSnapshot.title')"
      :visible="visible"
      width="860px"
      class="agent-snapshot-dialog"
      :before-close="guardRestoreInFlightClose"
      :close-on-click-modal="!restoring"
      :close-on-press-escape="!restoring"
      :show-close="!restoring"
      @open="open"
      @close="close"
    >
      <template slot="title">
        <div class="snapshot-dialog-title">
          <i class="el-icon-time snapshot-title-icon" aria-hidden="true"></i>
          <span>{{ $t('agentSnapshot.title') }}</span>
        </div>
      </template>

      <div class="snapshot-table-wrapper">
        <el-table
          v-loading="loading"
          :data="snapshots"
          :row-key="snapshotRowKey"
          :row-class-name="snapshotRowClassName"
          size="small"
          class="snapshot-table"
          :empty-text="loading ? ' ' : $t('agentSnapshot.empty')"
        >
        <el-table-column
          prop="versionNo"
          :label="$t('agentSnapshot.version')"
          width="90"
        >
          <template slot-scope="scope">
            <div class="version-cell">
              <span>#{{ scope.row.versionNo }}</span>
              <span
                v-if="scope.row.isLatestSnapshot"
                class="latest-version-icon"
                :title="$t('agentSnapshot.currentVersion')"
              ></span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="createdAt"
          :label="$t('agentSnapshot.createdAt')"
          width="170"
        >
          <template slot-scope="scope">
            {{ formatTime(scope.row.createdAt) || "—" }}
          </template>
        </el-table-column>
        <el-table-column
          prop="source"
          :label="$t('agentSnapshot.source')"
          width="110"
        >
          <template slot-scope="scope">
            {{ sourceLabel(scope.row.source) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('agentSnapshot.changedFields')" min-width="220">
          <template slot-scope="scope">
            <div v-if="(scope.row.changedFields || []).length" class="field-tags">
              <el-tag
                v-for="field in scope.row.changedFields"
                :key="field"
                size="mini"
                effect="plain"
              >
                {{ fieldLabel(field) }}
              </el-tag>
            </div>
            <span v-else class="field-tags-empty">—</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('agentSnapshot.actions')" width="190" fixed="right">
          <template slot-scope="scope">
            <el-button
              v-if="canViewSnapshot(scope.row)"
              type="text"
              size="small"
              @click="viewSnapshot(scope.row)"
            >
              {{ $t('agentSnapshot.view') }}
            </el-button>
            <el-button
              v-if="canRestoreSnapshot(scope.row)"
              type="text"
              size="small"
              @click="restoreSnapshot(scope.row)"
            >
              {{ $t('agentSnapshot.restore') }}
            </el-button>
            <el-button
              v-if="canDeleteSnapshot(scope.row)"
              type="text"
              size="small"
              class="snapshot-delete-button"
              :loading="deletingSnapshotId === scope.row.id"
              @click="deleteSnapshot(scope.row)"
            >
              {{ $t('agentSnapshot.delete') }}
            </el-button>
          </template>
        </el-table-column>
        </el-table>
      </div>

      <div class="pagination-row">
        <el-pagination
          :current-page="page"
          :page-size="limit"
          :total="total"
          layout="prev, pager, next, total"
          small
          @current-change="handlePageChange"
        />
      </div>
    </el-dialog>

    <el-dialog
      :title="detailDialogTitle"
      :visible.sync="detailVisible"
      width="860px"
      class="snapshot-detail-dialog"
    >
      <template slot="title">
        <div class="snapshot-dialog-title">
          <i class="el-icon-time snapshot-title-icon" aria-hidden="true"></i>
          <span>{{ detailDialogTitle }}</span>
        </div>
      </template>

      <div v-loading="detailLoading" class="snapshot-diff">
        <template v-if="currentSnapshot && snapshotDiffs.length">
          <div class="detail-summary">
            <span>#{{ currentSnapshot.versionNo }}</span>
            <span>{{ formatTime(currentSnapshot.createdAt) }}</span>
            <span>{{ sourceLabel(currentSnapshot.source) }}</span>
          </div>

          <div
            v-for="item in snapshotDiffs"
            :key="item.field"
            class="diff-item"
          >
            <div class="diff-field">{{ item.label }}</div>
            <div v-if="item.single" class="diff-values is-single" :class="{ 'is-complex': item.complex }">
              <div class="diff-pane diff-after">
                <div class="diff-pane-title">{{ item.valueTitle }}</div>
                <div v-if="item.displayType === 'functions'" class="function-change-view is-single">
                  <div v-if="item.functionStates.length" class="function-toggle-list">
                    <div
                      v-for="(functionState, stateIndex) in item.functionStates"
                      :key="`function-state-${item.field}-${functionState.pluginId}-${stateIndex}`"
                      class="function-toggle-card is-single"
                    >
                      <div class="function-toggle-head">
                        <span class="function-dot"></span>
                        <div class="function-change-title-wrap">
                          <div class="function-change-title-row">
                            <span class="function-change-name">{{ functionState.name }}</span>
                          </div>
                        </div>
                      </div>

                      <div
                        class="function-state-pane is-after is-enabled"
                      >
                        <div class="function-state-title">
                          <span>{{ item.valueTitle }}</span>
                          <span class="function-state-badge">{{ functionState.status }}</span>
                        </div>
                        <div v-if="functionState.params.length" class="function-state-params">
                          <div
                            v-for="param in functionState.params"
                            :key="`${functionState.pluginId}-single-${param.key}`"
                            class="function-param-row"
                          >
                            <span class="param-key">{{ param.label }}</span>
                            <span class="param-value">{{ param.value }}</span>
                          </div>
                        </div>
                        <div v-else class="function-state-empty">{{ functionState.note }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="value-empty">{{ $t('agentSnapshot.emptyValue') }}</div>
                </div>
                <div v-else class="diff-value" :class="valueClass(item)">
                  <div
                    v-if="item.displayType === 'markdown'"
                    class="markdown-body"
                    v-html="renderMarkdownValue(item.afterValue)"
                  ></div>
                  <pre v-else class="diff-text">{{ item.afterText }}</pre>
                </div>
              </div>
            </div>
            <div v-else-if="item.displayType === 'functions'" class="function-change-view">
              <div v-if="item.functionChanges.length" class="function-toggle-list">
                <div
                  v-for="(change, changeIndex) in item.functionChanges"
                  :key="`function-change-${item.field}-${change.pluginId}-${changeIndex}`"
                  class="function-toggle-card"
                  :class="`is-${change.type}`"
                >
                  <div class="function-toggle-head">
                    <span class="function-dot"></span>
                    <div class="function-change-title-wrap">
                      <div class="function-change-title-row">
                        <span class="function-change-name">{{ change.name }}</span>
                        <span class="function-change-badge">{{ change.badge }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="function-state-grid">
                    <div
                      class="function-state-pane is-before"
                      :class="{ 'is-enabled': change.before.active, 'is-disabled': !change.before.active }"
                    >
                      <div class="function-state-title">
                        <span>{{ item.beforeTitle }}</span>
                        <span class="function-state-badge">{{ change.before.status }}</span>
                      </div>
                      <div v-if="change.before.active && change.before.params.length" class="function-state-params">
                        <div
                          v-for="param in change.before.params"
                          :key="`${change.pluginId}-before-${param.key}`"
                          class="function-param-row"
                          :class="{ 'is-changed': param.changed }"
                        >
                          <span class="param-key">{{ param.label }}</span>
                          <span class="param-value">{{ param.value }}</span>
                        </div>
                      </div>
                      <div v-else class="function-state-empty">{{ change.before.note }}</div>
                    </div>

                    <div
                      class="function-state-pane is-after"
                      :class="{ 'is-enabled': change.after.active, 'is-disabled': !change.after.active }"
                    >
                      <div class="function-state-title">
                        <span>{{ item.afterTitle }}</span>
                        <span class="function-state-badge">{{ change.after.status }}</span>
                      </div>
                      <div v-if="change.after.active && change.after.params.length" class="function-state-params">
                        <div
                          v-for="param in change.after.params"
                          :key="`${change.pluginId}-after-${param.key}`"
                          class="function-param-row"
                          :class="{ 'is-changed': param.changed }"
                        >
                          <span class="param-key">{{ param.label }}</span>
                          <span class="param-value">{{ param.value }}</span>
                        </div>
                      </div>
                      <div v-else class="function-state-empty">{{ change.after.note }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="value-empty">{{ $t('agentSnapshot.noFunctionChange') }}</div>
            </div>
            <div v-else class="diff-values" :class="{ 'is-complex': item.complex }">
              <div class="diff-pane diff-before">
                <div class="diff-pane-title">{{ item.beforeTitle }}</div>
                <div class="diff-value" :class="valueClass(item)">
                  <div
                    v-if="item.displayType === 'markdown'"
                    class="markdown-body"
                    v-html="renderMarkdownValue(item.beforeValue)"
                  ></div>
                  <pre v-else class="diff-text">{{ item.beforeText }}</pre>
                </div>
              </div>
              <div class="diff-pane diff-after">
                <div class="diff-pane-title">{{ item.afterTitle }}</div>
                <div class="diff-value" :class="valueClass(item)">
                  <div
                    v-if="item.displayType === 'markdown'"
                    class="markdown-body"
                    v-html="renderMarkdownValue(item.afterValue)"
                  ></div>
                  <pre v-else class="diff-text">{{ item.afterText }}</pre>
                </div>
              </div>
            </div>
          </div>
        </template>
        <el-empty
          v-else-if="!detailLoading"
          :description="$t('agentSnapshot.noChangedContent')"
          :image-size="80"
        />
      </div>
    </el-dialog>

    <el-dialog
      :title="restorePreviewTitle"
      :visible.sync="restorePreviewVisible"
      width="860px"
      class="snapshot-detail-dialog"
      :before-close="guardRestoreInFlightClose"
      :close-on-click-modal="!restoring"
      :close-on-press-escape="!restoring"
      :show-close="!restoring"
    >
      <template slot="title">
        <div class="snapshot-dialog-title">
          <i class="el-icon-time snapshot-title-icon" aria-hidden="true"></i>
          <span>{{ restorePreviewTitle }}</span>
        </div>
      </template>

      <div v-loading="restorePreviewLoading" class="snapshot-diff">
        <template v-if="restorePreviewSnapshot && restorePreviewDiffs.length">
          <div class="detail-summary">
            <span>#{{ restorePreviewSnapshot.versionNo }}</span>
            <span>{{ formatTime(restorePreviewSnapshot.createdAt) }}</span>
            <span>{{ sourceLabel(restorePreviewSnapshot.source) }}</span>
          </div>

          <div
            v-for="item in restorePreviewDiffs"
            :key="item.field"
            class="diff-item"
          >
            <div class="diff-field">{{ item.label }}</div>
            <div v-if="item.displayType === 'functions'" class="function-change-view">
              <div v-if="item.functionChanges.length" class="function-toggle-list">
                <div
                  v-for="(change, changeIndex) in item.functionChanges"
                  :key="`restore-function-change-${item.field}-${change.pluginId}-${changeIndex}`"
                  class="function-toggle-card"
                  :class="`is-${change.type}`"
                >
                  <div class="function-toggle-head">
                    <span class="function-dot"></span>
                    <div class="function-change-title-wrap">
                      <div class="function-change-title-row">
                        <span class="function-change-name">{{ change.name }}</span>
                        <span class="function-change-badge">{{ change.badge }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="function-state-grid">
                    <div
                      class="function-state-pane is-before"
                      :class="{ 'is-enabled': change.before.active, 'is-disabled': !change.before.active }"
                    >
                      <div class="function-state-title">
                        <span>{{ item.beforeTitle }}</span>
                        <span class="function-state-badge">{{ change.before.status }}</span>
                      </div>
                      <div v-if="change.before.active && change.before.params.length" class="function-state-params">
                        <div
                          v-for="param in change.before.params"
                          :key="`${change.pluginId}-restore-before-${param.key}`"
                          class="function-param-row"
                          :class="{ 'is-changed': param.changed }"
                        >
                          <span class="param-key">{{ param.label }}</span>
                          <span class="param-value">{{ param.value }}</span>
                        </div>
                      </div>
                      <div v-else class="function-state-empty">{{ change.before.note }}</div>
                    </div>

                    <div
                      class="function-state-pane is-after"
                      :class="{ 'is-enabled': change.after.active, 'is-disabled': !change.after.active }"
                    >
                      <div class="function-state-title">
                        <span>{{ item.afterTitle }}</span>
                        <span class="function-state-badge">{{ change.after.status }}</span>
                      </div>
                      <div v-if="change.after.active && change.after.params.length" class="function-state-params">
                        <div
                          v-for="param in change.after.params"
                          :key="`${change.pluginId}-restore-after-${param.key}`"
                          class="function-param-row"
                          :class="{ 'is-changed': param.changed }"
                        >
                          <span class="param-key">{{ param.label }}</span>
                          <span class="param-value">{{ param.value }}</span>
                        </div>
                      </div>
                      <div v-else class="function-state-empty">{{ change.after.note }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="value-empty">{{ $t('agentSnapshot.noFunctionChange') }}</div>
            </div>
            <div v-else class="diff-values" :class="{ 'is-complex': item.complex }">
              <div class="diff-pane diff-before">
                <div class="diff-pane-title">{{ item.beforeTitle }}</div>
                <div class="diff-value" :class="valueClass(item)">
                  <div
                    v-if="item.displayType === 'markdown'"
                    class="markdown-body"
                    v-html="renderMarkdownValue(item.beforeValue)"
                  ></div>
                  <pre v-else class="diff-text">{{ item.beforeText }}</pre>
                </div>
              </div>
              <div class="diff-pane diff-after">
                <div class="diff-pane-title">{{ item.afterTitle }}</div>
                <div class="diff-value" :class="valueClass(item)">
                  <div
                    v-if="item.displayType === 'markdown'"
                    class="markdown-body"
                    v-html="renderMarkdownValue(item.afterValue)"
                  ></div>
                  <pre v-else class="diff-text">{{ item.afterText }}</pre>
                </div>
              </div>
            </div>
          </div>
        </template>
        <el-empty
          v-else-if="!restorePreviewLoading"
          :description="$t('agentSnapshot.noChangedContent')"
          :image-size="80"
        />
        <el-alert
          v-if="restorePreviewSnapshot"
          class="restore-risk-alert"
          type="info"
          :closable="false"
          show-icon
          :title="$t('agentSnapshot.restoreConfirm', { version: restoreTargetVersion })"
        />
        <el-alert
          v-if="restorePreviewSnapshot"
          class="restore-risk-alert"
          type="warning"
          :closable="false"
          show-icon
          :title="$t('agentSnapshot.unsavedChangesWarning')"
        />
        <el-alert
          v-if="restoreWillClearChatHistory"
          class="restore-risk-alert"
          type="error"
          :closable="false"
          show-icon
          :title="$t('agentSnapshot.restoreMemoryDestructiveWarning')"
        />
      </div>
      <span slot="footer" class="snapshot-dialog-footer">
        <el-button
          class="snapshot-footer-button snapshot-footer-cancel"
          :disabled="restoring"
          @click="closeRestorePreview"
        >
          {{ $t('button.cancel') }}
        </el-button>
        <el-button
          class="snapshot-footer-button snapshot-footer-confirm"
          :loading="restoring"
          :disabled="restoring || restorePreviewLoading || !restorePreviewSnapshot || restorePreviewDiffs.length === 0"
          @click="confirmRestoreSnapshot"
        >
          <span class="confirm-inner">
            <i class="el-icon-refresh-left confirm-icon" aria-hidden="true"></i>
            {{ $t('agentSnapshot.confirmRestore') }}
          </span>
        </el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import Api from "@/apis/api";
import correctWord from "@/apis/module/correctWord";
import { formatDate } from "@/utils/date";
import {
  hasValidCurrentStateToken,
  normalizeSnapshotOrderedValue,
  redactSnapshotDisplayValue,
  SNAPSHOT_SECRET_REDACTED
} from "./agentSnapshotDisplayUtils.mjs";

const FALLBACK_PLUGIN_NAME_KEYS = {
  SYSTEM_PLUGIN_WEATHER: "agentSnapshot.plugin.SYSTEM_PLUGIN_WEATHER",
  SYSTEM_PLUGIN_MUSIC: "agentSnapshot.plugin.SYSTEM_PLUGIN_MUSIC",
  SYSTEM_PLUGIN_NEWS_CHINANEWS: "agentSnapshot.plugin.SYSTEM_PLUGIN_NEWS_CHINANEWS",
  SYSTEM_PLUGIN_NEWS_NEWSNOW: "agentSnapshot.plugin.SYSTEM_PLUGIN_NEWS_NEWSNOW",
  SYSTEM_PLUGIN_HA_STATE: "agentSnapshot.plugin.SYSTEM_PLUGIN_HA_STATE",
  SYSTEM_PLUGIN_HA_PLAY_MUSIC: "agentSnapshot.plugin.SYSTEM_PLUGIN_HA_PLAY_MUSIC",
  SYSTEM_PLUGIN_WEB_SEARCH: "agentSnapshot.plugin.SYSTEM_PLUGIN_WEB_SEARCH",
  SYSTEM_PLUGIN_CALL_DEVICE: "agentSnapshot.plugin.SYSTEM_PLUGIN_CALL_DEVICE"
};

const FALLBACK_FIELD_LABEL_KEYS = {
  url: "agentSnapshot.pluginField.url",
  news_sources: "agentSnapshot.pluginField.news_sources",
  default_rss_url: "agentSnapshot.pluginField.default_rss_url",
  society_rss_url: "agentSnapshot.pluginField.society_rss_url",
  world_rss_url: "agentSnapshot.pluginField.world_rss_url",
  finance_rss_url: "agentSnapshot.pluginField.finance_rss_url",
  api_key: "agentSnapshot.pluginField.api_key",
  default_location: "agentSnapshot.pluginField.default_location",
  api_host: "agentSnapshot.pluginField.api_host",
  base_url: "agentSnapshot.pluginField.base_url",
  devices: "agentSnapshot.pluginField.devices",
  provider: "agentSnapshot.pluginField.provider",
  description: "agentSnapshot.pluginField.description",
  max_results: "agentSnapshot.pluginField.max_results"
};

const MODEL_FIELD_TYPES = {
  asrModelId: "ASR",
  vadModelId: "VAD",
  llmModelId: "LLM",
  slmModelId: "SLM",
  vllmModelId: "VLLM",
  ttsModelId: "TTS",
  memModelId: "Memory",
  intentModelId: "Intent"
};

const MODEL_TYPES = ["ASR", "VAD", "LLM", "SLM", "VLLM", "TTS", "Memory", "Intent"];

const FALLBACK_MODEL_NAME_KEYS = {
  Memory_nomem: "agentSnapshot.model.Memory_nomem",
  Memory_mem_local_short: "agentSnapshot.model.Memory_mem_local_short",
  Memory_mem0ai: "agentSnapshot.model.Memory_mem0ai",
  Memory_mem_report_only: "agentSnapshot.model.Memory_mem_report_only",
  Intent_nointent: "agentSnapshot.model.Intent_nointent",
  Intent_intent_llm: "agentSnapshot.model.Intent_intent_llm",
  Intent_function_call: "agentSnapshot.model.Intent_function_call"
};

const FALLBACK_VOICE_NAME_KEYS = {
  TTS_EdgeTTS0001: "agentSnapshot.voice.TTS_EdgeTTS0001",
  TTS_EdgeTTS0002: "agentSnapshot.voice.TTS_EdgeTTS0002",
  TTS_EdgeTTS0003: "agentSnapshot.voice.TTS_EdgeTTS0003",
  TTS_EdgeTTS0004: "agentSnapshot.voice.TTS_EdgeTTS0004",
  TTS_EdgeTTS0005: "agentSnapshot.voice.TTS_EdgeTTS0005",
  TTS_EdgeTTS0006: "agentSnapshot.voice.TTS_EdgeTTS0006"
};

const CHAT_HISTORY_CONF_LABEL_KEYS = {
  0: "agentSnapshot.chatHistoryConf.none",
  1: "agentSnapshot.chatHistoryConf.text",
  2: "agentSnapshot.chatHistoryConf.textVoice"
};
export default {
  name: "AgentSnapshotDialog",
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    agentId: {
      type: String,
      required: true
    },
    currentVersionNo: {
      type: Number,
      default: null
    }
  },
  data() {
    return {
      loading: false,
      detailLoading: false,
      detailVisible: false,
      restorePreviewLoading: false,
      restorePreviewVisible: false,
      restoring: false,
      snapshots: [],
      currentSnapshot: null,
      restorePreviewSnapshot: null,
      restorePreviewRow: null,
      deletingSnapshotId: null,
      pluginMetadata: {},
      pluginMetadataLoaded: false,
      pluginMetadataLoading: null,
      modelNameMap: {},
      modelMetadataLoaded: false,
      modelMetadataLoading: null,
      voiceNameMap: {},
      voiceMetadataLoading: {},
      loadedVoiceModelIds: {},
      correctWordNameMap: {},
      correctWordMetadataLoaded: false,
      correctWordMetadataLoading: null,
      snapshotFetchSeq: 0,
      detailFetchSeq: 0,
      restorePreviewFetchSeq: 0,
      restoreActionSeq: 0,
      deleteActionSeq: 0,
      historyAnchorVersionNo: null,
      historyTotal: 0,
      page: 1,
      limit: 10,
      total: 0
    };
  },
  computed: {
    detailDialogTitle() {
      if (!this.currentSnapshot) {
        return this.$t("agentSnapshot.detailTitle");
      }
      return this.formatVersionRangeTitle(
        this.$t("agentSnapshot.detailTitle"),
        this.currentSnapshot.beforeVersionNo,
        this.currentSnapshot.afterVersionNo || this.currentSnapshot.versionNo
      );
    },
    restorePreviewTitle() {
      if (!this.restorePreviewSnapshot) {
        return this.$t("agentSnapshot.restorePreviewTitle");
      }
      const beforeVersionNo = this.restorePreviewSnapshot.beforeVersionNo || this.resolveCurrentVersionNo();
      const afterVersionNo = this.restorePreviewSnapshot.afterVersionNo || this.restorePreviewSnapshot.versionNo;
      return this.formatVersionRangeTitle(
        this.$t("agentSnapshot.restorePreviewTitle"),
        beforeVersionNo,
        afterVersionNo
      );
    },
    snapshotDiffs() {
      if (!this.currentSnapshot) {
        return [];
      }

      if (this.currentSnapshot.isSingleSnapshot) {
        return this.buildSingleConfigItems(
          this.currentSnapshot.snapshotData || {},
          this.currentSnapshot.fieldOrder || []
        );
      }

      if (!this.hasAfterSnapshotData(this.currentSnapshot)) {
        return [];
      }

      const beforeData = this.currentSnapshot.snapshotData || {};
      const afterData = this.currentSnapshot.afterSnapshotData || {};
      return this.buildDiffs(beforeData, afterData, this.currentSnapshot.changedFields, {
        beforeLabel: this.$t("agentSnapshot.beforeChange"),
        afterLabel: this.$t("agentSnapshot.afterChange"),
        beforeVersionNo: this.currentSnapshot.beforeVersionNo,
        afterVersionNo: this.currentSnapshot.afterVersionNo || this.currentSnapshot.versionNo,
        fieldOrder: this.currentSnapshot.fieldOrder,
        forceCompare: Boolean(this.currentSnapshot.forceCompare)
      });
    },
    restorePreviewDiffs() {
      if (!this.restorePreviewSnapshot) {
        return [];
      }

      return this.buildDiffs(
        this.restorePreviewSnapshot.beforeSnapshotData || {},
        this.restorePreviewSnapshot.afterSnapshotData || {},
        [],
        {
          beforeLabel: this.$t("agentSnapshot.beforeRestore"),
          afterLabel: this.$t("agentSnapshot.afterRestore"),
          beforeVersionNo: this.restorePreviewSnapshot.beforeVersionNo || this.resolveCurrentVersionNo(),
          afterVersionNo: this.restorePreviewSnapshot.afterVersionNo || this.restorePreviewSnapshot.versionNo,
          fieldOrder: this.restorePreviewSnapshot.fieldOrder,
          forceCompare: true
        }
      );
    },
    restoreWillClearChatHistory() {
      const beforeMemModelId = this.restorePreviewSnapshot?.beforeSnapshotData?.memModelId;
      const afterMemModelId = this.restorePreviewSnapshot?.afterSnapshotData?.memModelId;
      return beforeMemModelId !== "Memory_nomem" && afterMemModelId === "Memory_nomem";
    },
    restoreTargetVersion() {
      return this.restorePreviewSnapshot?.versionNo || this.restorePreviewRow?.versionNo || "";
    }
  },
  watch: {
    currentVersionNo(newValue, oldValue) {
      if (this.visible && newValue !== oldValue) {
        this.historyAnchorVersionNo = null;
        this.fetchSnapshots({ clearTable: false });
      }
    }
  },
  beforeDestroy() {
    this.cancelPendingSnapshotRequests();
  },
  methods: {
    buildSingleConfigItems(snapshotData = {}, fieldOrder = []) {
      const fields = Array.from(new Set(this.snapshotFieldOrder(fieldOrder, {}, snapshotData)));
      return fields.map((field) => {
        const value = this.getFieldValue(snapshotData, field);
        const displayType = this.displayType(field);
        return {
          field,
          label: this.fieldLabel(field),
          beforeValue: null,
          afterValue: value,
          beforeText: "",
          afterText: this.formatDisplayValue(field, value, snapshotData),
          displayType,
          single: true,
          valueTitle: this.$t("agentSnapshot.configValue"),
          functionStates: displayType === "functions"
            ? this.buildSingleFunctionStates(value)
            : [],
          complex: this.isComplexValue(value)
        };
      });
    },
    buildDiffs(beforeData, afterData, changedFields, options = {}) {
      const fields = this.resolveDiffFields(
        beforeData,
        afterData,
        changedFields,
        options.fieldOrder,
        options.forceCompare
      );
      return fields.map((field) => {
        const beforeValue = this.getFieldValue(beforeData, field);
        const afterValue = this.getFieldValue(afterData, field);
        const displayType = this.displayType(field);
        return {
          field,
          label: this.fieldLabel(field),
          beforeValue,
          afterValue,
          beforeText: this.formatDisplayValue(field, beforeValue, beforeData),
          afterText: this.formatDisplayValue(field, afterValue, afterData),
          displayType,
          beforeTitle: this.formatPaneTitle(options.beforeLabel || this.$t("agentSnapshot.before"), options.beforeVersionNo),
          afterTitle: this.formatPaneTitle(options.afterLabel || this.$t("agentSnapshot.after"), options.afterVersionNo),
          functionChanges: displayType === "functions"
            ? this.buildFunctionChanges(beforeValue, afterValue)
            : [],
          complex: this.isComplexValue(beforeValue) || this.isComplexValue(afterValue)
        };
      });
    },
    close() {
      if (this.restoring) {
        return;
      }
      this.cancelPendingSnapshotRequests();
      this.historyAnchorVersionNo = null;
      this.$emit("update:visible", false);
    },
    guardRestoreInFlightClose(done) {
      if (this.restoring) {
        return;
      }
      done();
    },
    closeRestorePreview() {
      if (this.restoring) {
        return;
      }
      this.restorePreviewVisible = false;
    },
    open() {
      this.historyAnchorVersionNo = null;
      this.page = 1;
      this.fetchSnapshots();
    },
    cancelPendingSnapshotRequests() {
      this.snapshotFetchSeq += 1;
      this.detailFetchSeq += 1;
      this.restorePreviewFetchSeq += 1;
      this.restoreActionSeq += 1;
      this.deleteActionSeq += 1;
      this.loading = false;
      this.detailLoading = false;
      this.restorePreviewLoading = false;
      this.restoring = false;
      this.deletingSnapshotId = null;
    },
    snapshotRowKey(row) {
      return row?.id || `${row?.versionNo || ""}-${row?.createdAt || ""}`;
    },
    snapshotRowClassName({ row }) {
      return row?.isLatestSnapshot ? "current-version-row" : "";
    },
    canViewSnapshot(row) {
      return !!row?.id;
    },
    canRestoreSnapshot(row) {
      return !!row?.id && !row.isLatestSnapshot;
    },
    canDeleteSnapshot(row) {
      return !!row && !row.isLatestSnapshot;
    },
    fetchSnapshots(options = {}) {
      if (!this.agentId) {
        this.snapshots = [];
        this.total = 0;
        this.historyTotal = 0;
        return;
      }
      const { clearTable = true } = options;
      const requestSeq = ++this.snapshotFetchSeq;
      const displayStart = (this.page - 1) * this.limit;
      const displayEnd = displayStart + this.limit;
      const historyFetchLimit = Math.max(displayEnd + 1, this.limit, 1);
      this.ensurePluginMetadata();
      this.ensureModelMetadata();
      this.loading = true;
      if (clearTable) {
        this.snapshots = [];
      }
      Api.agent.getAgentSnapshots(
        this.agentId,
        this.snapshotQueryParams({ page: "1", limit: String(historyFetchLimit) }),
        ({ data }) => {
          if (requestSeq !== this.snapshotFetchSeq) {
            return;
          }
          this.loading = false;
          if (data.code === 0) {
            const historyRows = this.decorateSnapshotRows(data.data?.list || []);
            if (!this.historyAnchorVersionNo && historyRows[0]?.versionNo) {
              this.historyAnchorVersionNo = Number(historyRows[0].versionNo);
            }
            this.historyTotal = data.data?.total || 0;
            this.total = this.historyTotal;
            this.snapshots = this.applyPreviousChangedFields(
              historyRows.slice(displayStart, displayEnd),
              historyRows
            );
          } else {
            this.$message.error(data.msg || this.$t("agentSnapshot.fetchFailed"));
          }
        },
        () => {
          if (requestSeq !== this.snapshotFetchSeq) {
            return;
          }
          this.loading = false;
          this.$message.error(this.$t("agentSnapshot.fetchFailed"));
        }
      );
    },
    handlePageChange(page) {
      this.page = page;
      this.fetchSnapshots();
    },
    viewSnapshot(row) {
      if (!this.canViewSnapshot(row)) {
        return;
      }
      this.detailVisible = true;
      this.detailLoading = true;
      this.currentSnapshot = null;
      const requestSeq = ++this.detailFetchSeq;
      this.ensurePluginMetadata();
      this.ensureModelMetadata();
      this.buildVersionDiffSnapshot(row)
        .then((snapshot) => this.ensureDisplayMetadata(snapshot).then(() => snapshot))
        .then((snapshot) => {
          if (requestSeq !== this.detailFetchSeq) {
            return;
          }
          this.currentSnapshot = snapshot;
        })
        .catch(() => {
          if (requestSeq !== this.detailFetchSeq) {
            return;
          }
          this.$message.error(this.$t("agentSnapshot.detailFailed"));
        })
        .finally(() => {
          if (requestSeq === this.detailFetchSeq) {
            this.detailLoading = false;
          }
        });
    },
    restoreSnapshot(row) {
      if (!this.canRestoreSnapshot(row)) {
        return;
      }
      this.restorePreviewVisible = true;
      this.restorePreviewLoading = true;
      this.restorePreviewRow = row;
      this.restorePreviewSnapshot = null;
      const requestSeq = ++this.restorePreviewFetchSeq;
      this.ensurePluginMetadata();
      this.ensureModelMetadata();

      this.fetchSnapshotDetail(row.id).then((targetSnapshot) => {
        if (requestSeq !== this.restorePreviewFetchSeq) {
          return Promise.resolve();
        }
        if (
          !this.isPlainObject(targetSnapshot.currentSnapshotData)
          || !hasValidCurrentStateToken(targetSnapshot.currentStateToken)
        ) {
          throw new Error("Snapshot detail is missing its atomic current-state preview");
        }
        const previewSnapshot = {
          ...targetSnapshot,
          currentStateToken: targetSnapshot.currentStateToken,
          beforeSnapshotData: targetSnapshot.currentSnapshotData,
          afterSnapshotData: targetSnapshot.snapshotData || {},
          beforeVersionNo: this.resolveCurrentVersionNo(),
          afterVersionNo: targetSnapshot.versionNo,
          fieldOrder: targetSnapshot.fieldOrder || []
        };
        return this.ensureDisplayMetadata(previewSnapshot).then(() => {
          if (requestSeq !== this.restorePreviewFetchSeq) {
            return;
          }
          this.restorePreviewSnapshot = previewSnapshot;
        });
      }).catch(() => {
        if (requestSeq !== this.restorePreviewFetchSeq) {
          return;
        }
        this.restorePreviewVisible = false;
        this.$message.error(this.$t("agentSnapshot.detailFailed"));
      }).finally(() => {
        if (requestSeq === this.restorePreviewFetchSeq) {
          this.restorePreviewLoading = false;
        }
      });
    },
    decorateSnapshotRows(rows) {
      return (rows || []).map((row, index) => ({
        ...row,
        isLatestSnapshot: index === 0
      }));
    },
    confirmRestoreSnapshot() {
      if (this.restoring || !this.restorePreviewRow) {
        return;
      }
      const snapshotId = this.restorePreviewRow.id;
      const currentStateToken = this.restorePreviewSnapshot?.currentStateToken;
      if (!hasValidCurrentStateToken(currentStateToken)) {
        this.invalidateRestorePreview();
        this.$message.error(this.$t("agentSnapshot.restoreFailed"));
        return;
      }

      if (!this.restoreWillClearChatHistory) {
        this.submitRestoreSnapshot(snapshotId, currentStateToken);
        return;
      }

      this.restoring = true;
      const requestSeq = ++this.restoreActionSeq;
      this.$confirm(
        this.$t("agentSnapshot.restoreMemoryDestructiveWarning"),
        this.$t("common.warning"),
        {
          confirmButtonText: this.$t("common.confirm"),
          cancelButtonText: this.$t("common.cancel"),
          type: "error"
        }
      ).then(() => {
        if (requestSeq !== this.restoreActionSeq) {
          return;
        }
        this.submitRestoreSnapshot(snapshotId, currentStateToken, requestSeq);
      }).catch(() => {
        if (requestSeq === this.restoreActionSeq) {
          this.restoring = false;
        }
      });
    },
    submitRestoreSnapshot(snapshotId, currentStateToken, confirmedRequestSeq = null) {
      if (!hasValidCurrentStateToken(currentStateToken)) {
        this.restoring = false;
        this.invalidateRestorePreview();
        this.$message.error(this.$t("agentSnapshot.restoreFailed"));
        return;
      }
      const requestSeq = confirmedRequestSeq ?? ++this.restoreActionSeq;
      if (requestSeq !== this.restoreActionSeq) {
        return;
      }
      this.restoring = true;
      Api.agent.restoreAgentSnapshot(this.agentId, snapshotId, currentStateToken, ({ data }) => {
        if (requestSeq !== this.restoreActionSeq) {
          return;
        }
        this.restoring = false;
        if (data.code === 0) {
          this.$message.success(this.$t("agentSnapshot.restoreSuccess"));
          this.restorePreviewVisible = false;
          this.restorePreviewSnapshot = null;
          this.restorePreviewRow = null;
          this.detailVisible = false;
          this.$emit("restored");
          this.historyAnchorVersionNo = null;
          this.fetchSnapshots();
        } else {
          this.invalidateRestorePreview();
          this.$message.error(this.restoreFailedMessage(data));
        }
      }, () => {
        if (requestSeq !== this.restoreActionSeq) {
          return;
        }
        this.restoring = false;
        this.invalidateRestorePreview();
        this.$message.error(this.$t("agentSnapshot.restoreFailed"));
      });
    },
    invalidateRestorePreview() {
      this.restorePreviewFetchSeq += 1;
      this.restorePreviewLoading = false;
      this.restorePreviewVisible = false;
      this.restorePreviewSnapshot = null;
      this.restorePreviewRow = null;
    },
    deleteSnapshot(row) {
      if (!this.canDeleteSnapshot(row)) {
        return;
      }
      this.$confirm(
        this.$t("agentSnapshot.deleteConfirm", { version: row.versionNo }),
        this.$t("common.warning"),
        {
          confirmButtonText: this.$t("common.confirm"),
          cancelButtonText: this.$t("common.cancel"),
          type: "warning"
        }
      ).then(() => {
        const requestSeq = ++this.deleteActionSeq;
        this.deletingSnapshotId = row.id;
        Api.agent.deleteAgentSnapshot(this.agentId, row.id, ({ data }) => {
          if (requestSeq !== this.deleteActionSeq) {
            return;
          }
          this.deletingSnapshotId = null;
          if (data.code === 0) {
            this.$message.success(this.$t("agentSnapshot.deleteSuccess"));
            if (this.snapshots.length <= 1 && this.page > 1) {
              this.page -= 1;
            }
            this.fetchSnapshots();
          } else {
            this.$message.error(data.msg || this.$t("agentSnapshot.deleteFailed"));
          }
        }, () => {
          if (requestSeq !== this.deleteActionSeq) {
            return;
          }
          this.deletingSnapshotId = null;
          this.$message.error(this.$t("agentSnapshot.deleteFailed"));
        });
      }).catch(() => {});
    },
    hasAfterSnapshotData(snapshot) {
      return !!(
        snapshot &&
        snapshot.afterSnapshotData &&
        Object.keys(snapshot.afterSnapshotData).length > 0
      );
    },
    resolveCurrentVersionNo() {
      const propVersionNo = Number(this.currentVersionNo);
      if (Number.isFinite(propVersionNo) && propVersionNo > 0) {
        return propVersionNo;
      }

      const latestRow = this.snapshots.find((item) => item.isLatestSnapshot) || this.snapshots[0];
      if (latestRow?.versionNo) {
        return latestRow.versionNo;
      }

      return null;
    },
    formatPaneTitle(label, versionNo) {
      return versionNo ? `${label} #${versionNo}` : label;
    },
    formatVersionRangeTitle(label, beforeVersionNo, afterVersionNo) {
      if (beforeVersionNo && afterVersionNo) {
        return `${label} #${beforeVersionNo} → #${afterVersionNo}`;
      }
      if (beforeVersionNo) {
        return `${label} #${beforeVersionNo}`;
      }
      if (afterVersionNo) {
        return `${label} #${afterVersionNo}`;
      }
      return label;
    },
    fetchSnapshotDetail(snapshotId) {
      return new Promise((resolve, reject) => {
        Api.agent.getAgentSnapshot(this.agentId, snapshotId, ({ data }) => {
          if (data.code === 0) {
            resolve(data.data);
          } else {
            reject(data);
          }
        }, reject);
      });
    },
    fetchSnapshotRows(params) {
      return new Promise((resolve, reject) => {
        Api.agent.getAgentSnapshots(this.agentId, this.snapshotQueryParams(params), ({ data }) => {
          if (data.code === 0) {
            resolve(data.data || { list: [], total: 0 });
          } else {
            reject(data);
          }
        }, reject);
      });
    },
    snapshotQueryParams(params = {}) {
      if (!this.historyAnchorVersionNo) {
        return params;
      }
      return {
        ...params,
        maxVersionNo: String(this.historyAnchorVersionNo)
      };
    },
    applyPreviousChangedFields(rows, sourceRows) {
      return rows.map((row) => {
        const versionNo = Number(row.versionNo);
        if (!Number.isFinite(versionNo)) {
          return {
            ...row,
            changedFields: row.changedFields || []
          };
        }
        const previousRow = this.findPreviousSnapshotRow(row, sourceRows);
        return {
          ...row,
          previousSnapshotId: previousRow?.id || null,
          previousVersionNo: previousRow?.versionNo || null,
          changedFields: row.changedFields || []
        };
      });
    },
    findPreviousSnapshotRow(row, sourceRows) {
      const versionNo = Number(row?.versionNo);
      if (!Number.isFinite(versionNo)) {
        return null;
      }
      return (sourceRows || []).find((item) => {
        return Number(item.versionNo) < versionNo;
      }) || null;
    },
    buildVersionDiffSnapshot(row) {
      return this.buildSavedVersionDiffSnapshot(row);
    },
    buildSavedVersionDiffSnapshot(row) {
      const versionNo = Number(row.versionNo);
      const displayVersionNo = Number.isFinite(versionNo) ? versionNo : row.versionNo;
      return this.fetchSnapshotDetail(row.id).then((selectedSnapshot) => {
        if (!this.hasPreviousSnapshot(row)) {
          return this.buildSingleSnapshotDetail(selectedSnapshot, row, displayVersionNo);
        }

        return this.fetchPreviousSnapshotDetail(row).then((previousSnapshot) => {
          if (!previousSnapshot?.id) {
            return this.buildSingleSnapshotDetail(selectedSnapshot, row, displayVersionNo);
          }
          const adjacentVersion = this.isAdjacentVersion(previousSnapshot.versionNo, displayVersionNo);
          return {
            ...selectedSnapshot,
            versionNo: displayVersionNo,
            changedFields: adjacentVersion ? (selectedSnapshot.changedFields || row.changedFields || []) : [],
            forceCompare: !adjacentVersion,
            snapshotData: previousSnapshot.snapshotData || {},
            afterSnapshotData: selectedSnapshot.snapshotData || {},
            beforeVersionNo: previousSnapshot.versionNo,
            afterVersionNo: displayVersionNo,
            fieldOrder: selectedSnapshot.fieldOrder || previousSnapshot.fieldOrder || row.fieldOrder || []
          };
        });
      });
    },
    buildSingleSnapshotDetail(selectedSnapshot, row, displayVersionNo) {
      return {
        ...selectedSnapshot,
        versionNo: displayVersionNo,
        isSingleSnapshot: true,
        changedFields: selectedSnapshot.changedFields || row.changedFields || [],
        snapshotData: selectedSnapshot.snapshotData || {},
        afterSnapshotData: selectedSnapshot.snapshotData || {},
        afterVersionNo: displayVersionNo,
        fieldOrder: selectedSnapshot.fieldOrder || row.fieldOrder || []
      };
    },
    isAdjacentVersion(beforeVersionNo, afterVersionNo) {
      const beforeVersion = Number(beforeVersionNo);
      const afterVersion = Number(afterVersionNo);
      return Number.isFinite(beforeVersion) && Number.isFinite(afterVersion) && afterVersion - beforeVersion === 1;
    },
    hasPreviousSnapshot(row) {
      const versionNo = Number(row?.versionNo);
      return !!(
        row?.previousSnapshotId ||
        row?.previousVersionNo ||
        (Number.isFinite(versionNo) && versionNo > 1)
      );
    },
    fetchPreviousSnapshotDetail(row) {
      if (row?.previousSnapshotId) {
        return this.fetchSnapshotDetail(row.previousSnapshotId)
          .catch(() => this.fetchPreviousSnapshotDetailWithoutId(row));
      }
      return this.fetchPreviousSnapshotDetailWithoutId(row);
    },
    fetchPreviousSnapshotDetailWithoutId(row) {
      if (row?.previousVersionNo) {
        return this.fetchSnapshotDetailByVersion(row.previousVersionNo)
          .catch(() => this.fetchNearestPreviousSnapshotDetail(row));
      }
      return this.fetchNearestPreviousSnapshotDetail(row);
    },
    fetchNearestPreviousSnapshotDetail(row) {
      return this.fetchSnapshotRowBeforeVersion(row?.versionNo).then((previousRow) => {
        if (!previousRow?.id) {
          return null;
        }
        return this.fetchSnapshotDetail(previousRow.id).catch(() => null);
      });
    },
    fetchSnapshotDetailByVersion(versionNo) {
      return this.fetchSnapshotRowByVersion(versionNo).then((row) => {
        if (!row?.id) {
          return Promise.reject(new Error("snapshot not found"));
        }
        return this.fetchSnapshotDetail(row.id);
      });
    },
    fetchSnapshotRowByVersion(versionNo) {
      const version = Number(versionNo);
      if (!Number.isFinite(version) || version < 1) {
        return Promise.resolve(null);
      }

      const cached = this.snapshots.find((item) => {
        return Number(item.versionNo) === version;
      });
      if (cached) {
        return Promise.resolve(cached);
      }

      const pageNo = this.historyTotal > 0
        ? Math.max(Math.floor((this.historyTotal - version) / this.limit) + 1, 1)
        : 1;
      return this.fetchSnapshotRows({
        page: String(pageNo),
        limit: String(this.limit)
      }).then((data) => {
        const row = (data.list || []).find((item) => Number(item.versionNo) === version);
        if (row || !this.historyTotal || this.historyTotal <= this.limit) {
          return row || null;
        }
        return this.fetchSnapshotRows({
          page: "1",
          limit: String(this.historyTotal)
        }).then((fallbackData) => {
          return (fallbackData.list || []).find((item) => Number(item.versionNo) === version) || null;
        });
      });
    },
    fetchSnapshotRowBeforeVersion(versionNo) {
      const cached = this.findPreviousSnapshotRow({ versionNo }, this.snapshots);
      if (cached) {
        return Promise.resolve(cached);
      }

      return this.fetchSnapshotRows({
        page: "1",
        limit: String(Math.max(this.historyTotal, this.limit, 1))
      }).then((data) => this.findPreviousSnapshotRow({ versionNo }, data.list || []));
    },
    ensurePluginMetadata() {
      if (this.pluginMetadataLoaded) {
        return Promise.resolve();
      }
      if (this.pluginMetadataLoading) {
        return this.pluginMetadataLoading;
      }

      this.pluginMetadataLoading = new Promise((resolve) => {
        Api.model.getPluginFunctionList(null, ({ data }) => {
          if (data.code === 0) {
            const metadata = {};
            (data.data || []).forEach((item) => {
              metadata[item.id] = {
                ...item,
                fieldsMeta: this.parsePluginFields(item.fields)
              };
            });
            this.pluginMetadata = metadata;
            this.pluginMetadataLoaded = true;
          }
          resolve();
        }, () => {
          this.pluginMetadataLoaded = true;
          resolve();
        });
      }).finally(() => {
        this.pluginMetadataLoading = null;
      });

      return this.pluginMetadataLoading;
    },
    ensureModelMetadata() {
      if (this.modelMetadataLoaded) {
        return Promise.resolve();
      }
      if (this.modelMetadataLoading) {
        return this.modelMetadataLoading;
      }

      const fetchers = MODEL_TYPES.map((type) => {
        return new Promise((resolve) => {
          const callback = ({ data }) => {
            if (data.code === 0) {
              resolve((data.data || []).map((item) => ({
                id: item.id,
                name: item.modelName
              })));
            } else {
              resolve([]);
            }
          };

          if (type === "LLM") {
            Api.model.getLlmModelCodeList("", callback, () => resolve([]));
          } else {
            Api.model.getModelNames(type, "", callback, () => resolve([]));
          }
        });
      });

      this.modelMetadataLoading = Promise.all(fetchers)
        .then((groups) => {
          const metadata = {};
          groups.flat().forEach((item) => {
            if (item.id) {
              metadata[item.id] = item.name || item.id;
            }
          });
          this.modelNameMap = metadata;
          this.modelMetadataLoaded = true;
        })
        .finally(() => {
          this.modelMetadataLoading = null;
        });

      return this.modelMetadataLoading;
    },
    ensureDisplayMetadata(snapshot) {
      const beforeData = snapshot.beforeSnapshotData || snapshot.snapshotData || {};
      const afterData = snapshot.afterSnapshotData || {};
      return Promise.all([
        this.ensureModelMetadata(),
        this.ensureVoiceMetadataForData(beforeData, afterData),
        this.ensureCorrectWordMetadataForData(beforeData, afterData)
      ]);
    },
    ensureCorrectWordMetadataForData(...dataList) {
      const hasCorrectWordIds = dataList.some((data) => {
        return Array.isArray(data?.correctWordFileIds) && data.correctWordFileIds.length > 0;
      });
      return hasCorrectWordIds ? this.ensureCorrectWordMetadata() : Promise.resolve();
    },
    ensureCorrectWordMetadata() {
      if (this.correctWordMetadataLoaded) {
        return Promise.resolve();
      }
      if (this.correctWordMetadataLoading) {
        return this.correctWordMetadataLoading;
      }

      this.correctWordMetadataLoading = new Promise((resolve) => {
        correctWord.selectAll(({ data }) => {
          if (data.code === 0) {
            const metadata = {};
            (data.data || []).forEach((item) => {
              if (item.id) {
                metadata[item.id] = item.fileName || item.id;
              }
            });
            this.correctWordNameMap = metadata;
            this.correctWordMetadataLoaded = true;
          }
          resolve();
        }, () => {
          // 权限不足或元数据服务不可用时保留原始 ID，不扩大文件列表的访问边界。
          this.correctWordMetadataLoaded = true;
          resolve();
        });
      }).finally(() => {
        this.correctWordMetadataLoading = null;
      });

      return this.correctWordMetadataLoading;
    },
    ensureVoiceMetadataForData(...dataList) {
      const modelIds = Array.from(new Set(
        dataList
          .map((data) => data && data.ttsModelId)
          .filter(Boolean)
      ));

      return Promise.all(modelIds.map((modelId) => this.ensureVoiceMetadata(modelId)));
    },
    ensureVoiceMetadata(modelId) {
      if (!modelId || this.loadedVoiceModelIds[modelId]) {
        return Promise.resolve();
      }
      if (this.voiceMetadataLoading[modelId]) {
        return this.voiceMetadataLoading[modelId];
      }

      this.voiceMetadataLoading = {
        ...this.voiceMetadataLoading,
        [modelId]: new Promise((resolve) => {
          Api.model.getModelVoices(modelId, "", ({ data }) => {
            if (data.code === 0) {
              const nextVoiceNameMap = { ...this.voiceNameMap };
              (data.data || []).forEach((voice) => {
                if (voice.id) {
                  nextVoiceNameMap[voice.id] = voice.name || voice.id;
                  nextVoiceNameMap[`${modelId}:${voice.id}`] = voice.name || voice.id;
                }
              });
              this.voiceNameMap = nextVoiceNameMap;
              this.loadedVoiceModelIds = {
                ...this.loadedVoiceModelIds,
                [modelId]: true
              };
            }
            resolve();
          }, () => {
            this.loadedVoiceModelIds = {
              ...this.loadedVoiceModelIds,
              [modelId]: true
            };
            resolve();
          });
        }).finally(() => {
          const { [modelId]: dropped, ...rest } = this.voiceMetadataLoading;
          this.voiceMetadataLoading = rest;
        })
      };

      return this.voiceMetadataLoading[modelId];
    },
    parsePluginFields(fields) {
      if (!fields) {
        return [];
      }
      if (Array.isArray(fields)) {
        return fields;
      }
      if (typeof fields === "string") {
        try {
          const parsed = JSON.parse(fields);
          return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
          return [];
        }
      }
      return [];
    },
    fetchCurrentAgentData() {
      const configPromise = new Promise((resolve, reject) => {
        Api.agent.getDeviceConfig(this.agentId, ({ data }) => {
          if (data.code === 0) {
            resolve(data.data || {});
          } else {
            reject(data);
          }
        }, reject);
      });
      const tagsPromise = this.fetchCurrentAgentTags();

      return Promise.all([configPromise, tagsPromise]).then(([data, tags]) => {
        return this.normalizeAgentData({
          ...data,
          tags,
          tagNames: tags.map((tag) => tag.tagName)
        });
      });
    },
    fetchCurrentAgentTags() {
      return new Promise((resolve, reject) => {
        Api.agent.getAgentTags(this.agentId, ({ data }) => {
          if (data.code === 0) {
            resolve(data.data || []);
          } else {
            reject(data);
          }
        }, reject);
      });
    },
    normalizeAgentData(data) {
      const tags = data.tags || [];
      return {
        ...data,
        functions: (data.functions || []).map((item) => ({
          pluginId: item.pluginId,
          paramInfo: this.parseParamInfo(item.paramInfo)
        })),
        tags,
        tagNames: data.tagNames || tags.map((tag) => tag.tagName)
      };
    },
    parseParamInfo(paramInfo) {
      if (!paramInfo) {
        return {};
      }
      if (typeof paramInfo === "string") {
        try {
          return JSON.parse(paramInfo);
        } catch (error) {
          return {};
        }
      }
      return paramInfo;
    },
    displayType(field) {
      if (field === "functions") {
        return "functions";
      }
      if (field === "systemPrompt") {
        return "markdown";
      }
      return "text";
    },
    valueClass(item) {
      return [`is-${item.displayType || "text"}`];
    },
    normalizeFunctions(value) {
      return Object.values(this.normalizeFunctionMap(value)).map((item) => ({
        pluginId: item.pluginId,
        name: this.functionDisplayName(item.pluginId),
        params: this.functionParamRows(item.pluginId, item.params)
      }));
    },
    normalizeFunctionList(value) {
      if (!value) {
        return [];
      }
      if (typeof value === "string") {
        try {
          const parsed = JSON.parse(value);
          return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
          return [];
        }
      }
      return Array.isArray(value) ? value : [];
    },
    normalizeFunctionParams(value) {
      if (!value) {
        return {};
      }
      if (typeof value === "string") {
        try {
          const parsed = JSON.parse(value);
          return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
        } catch (error) {
          return {};
        }
      }
      return value && typeof value === "object" && !Array.isArray(value) ? value : {};
    },
    normalizeFunctionMap(value) {
      return this.normalizeFunctionList(value).reduce((result, item) => {
        const pluginId = item.pluginId || item.id || item.providerCode || item.name;
        if (!pluginId) {
          return result;
        }
        result[pluginId] = {
          pluginId,
          params: this.normalizeFunctionParams(item.paramInfo ?? item.params)
        };
        return result;
      }, {});
    },
    buildFunctionChanges(beforeValue, afterValue) {
      const beforeMap = this.normalizeFunctionMap(beforeValue);
      const afterMap = this.normalizeFunctionMap(afterValue);
      const pluginIds = Array.from(new Set([
        ...Object.keys(beforeMap),
        ...Object.keys(afterMap)
      ]));

      return pluginIds.reduce((changes, pluginId) => {
        const beforeFunc = beforeMap[pluginId];
        const afterFunc = afterMap[pluginId];

        if (!beforeFunc && afterFunc) {
          changes.push(this.createFunctionChange("added", null, afterFunc));
          return changes;
        }

        if (beforeFunc && !afterFunc) {
          changes.push(this.createFunctionChange("removed", beforeFunc, null));
          return changes;
        }

        const changedParamKeys = this.changedFunctionParamKeys(
          pluginId,
          beforeFunc.params,
          afterFunc.params
        );
        if (changedParamKeys.length) {
          changes.push(this.createFunctionChange("updated", beforeFunc, afterFunc, changedParamKeys));
        }
        return changes;
      }, []);
    },
    createFunctionChange(type, beforeFunc, afterFunc, changedParamKeys = []) {
      const pluginId = (afterFunc || beforeFunc).pluginId;
      const name = this.functionDisplayName(pluginId);
      const statusMap = {
        added: {
          badge: this.$t("agentSnapshot.function.added")
        },
        removed: {
          badge: this.$t("agentSnapshot.function.removed")
        },
        updated: {
          badge: this.$t("agentSnapshot.function.updated")
        }
      };
      return {
        type,
        pluginId,
        name,
        ...statusMap[type],
        before: this.buildFunctionState(pluginId, beforeFunc, changedParamKeys),
        after: this.buildFunctionState(pluginId, afterFunc, changedParamKeys)
      };
    },
    buildFunctionState(pluginId, func, changedParamKeys = []) {
      if (!func) {
        return {
          active: false,
          status: this.$t("agentSnapshot.function.disabled"),
          params: [],
          note: this.$t("agentSnapshot.function.disabledNote")
        };
      }

      const params = this.functionParamRows(pluginId, func.params, changedParamKeys);
      return {
        active: true,
        status: this.$t("agentSnapshot.function.enabled"),
        params,
        note: params.length ? "" : this.$t("agentSnapshot.function.noParams")
      };
    },
    buildSingleFunctionStates(value) {
      return this.normalizeFunctions(value).map((func) => ({
        pluginId: func.pluginId,
        name: func.name,
        status: this.$t("agentSnapshot.function.enabled"),
        params: func.params,
        note: func.params.length ? "" : this.$t("agentSnapshot.function.noParams")
      }));
    },
    changedFunctionParamKeys(pluginId, beforeParams, afterParams) {
      const safeBeforeParams = beforeParams || {};
      const safeAfterParams = afterParams || {};
      const paramKeys = Array.from(new Set([
        ...Object.keys(safeBeforeParams),
        ...Object.keys(safeAfterParams)
      ]));

      return paramKeys.reduce((keys, key) => {
        if (this.isSameValue(safeBeforeParams[key], safeAfterParams[key])) {
          return keys;
        }
        keys.push(key);
        return keys;
      }, []);
    },
    functionParamRows(pluginId, params, changedParamKeys = []) {
      const normalizedParams = params || {};
      const fieldKeys = this.functionFields(pluginId).map((field) => field.key);
      const paramKeys = Array.from(new Set([
        ...fieldKeys,
        ...Object.keys(normalizedParams)
      ])).filter((key) => key);

      return paramKeys.map((key) => ({
        key,
        label: this.functionParamLabel(pluginId, key),
        value: this.formatFunctionParamValue(normalizedParams[key], key),
        changed: changedParamKeys.includes(key)
      }));
    },
    functionDisplayName(pluginId) {
      const meta = this.resolveFunctionMeta(pluginId);
      return meta?.name || this.translateKey(FALLBACK_PLUGIN_NAME_KEYS[pluginId], pluginId)
        || pluginId || this.$t("agentSnapshot.emptyValue");
    },
    functionParamLabel(pluginId, key) {
      const field = this.functionFields(pluginId).find((item) => item.key === key);
      return field?.label || this.translateKey(FALLBACK_FIELD_LABEL_KEYS[key], key) || key;
    },
    functionFields(pluginId) {
      const meta = this.resolveFunctionMeta(pluginId);
      return Array.isArray(meta?.fieldsMeta) ? meta.fieldsMeta : [];
    },
    resolveFunctionMeta(pluginId) {
      if (!pluginId) {
        return null;
      }
      if (this.pluginMetadata[pluginId]) {
        return this.pluginMetadata[pluginId];
      }
      return Object.values(this.pluginMetadata).find((item) => {
        return item.id === pluginId || item.providerCode === pluginId || item.name === pluginId;
      }) || null;
    },
    formatFunctionParamValue(value, key = "") {
      if (value === null || value === undefined || value === "") {
        return this.$t("agentSnapshot.emptyValue");
      }
      const displayValue = this.localizedSnapshotDisplayValue(value, key);
      if (typeof displayValue === "object") {
        return JSON.stringify(displayValue);
      }
      return String(displayValue);
    },
    renderMarkdownValue(value) {
      const displayValue = this.localizedSnapshotDisplayValue(value);
      if (displayValue === null || displayValue === undefined || String(displayValue).trim() === "") {
        return `<span class="markdown-empty">${this.escapeHtml(this.$t("agentSnapshot.emptyValue"))}</span>`;
      }

      const lines = String(displayValue).replace(/\r\n/g, "\n").split("\n");
      const html = [];
      let paragraph = [];
      const listStack = [];

      const closeParagraph = () => {
        if (paragraph.length) {
          html.push(`<p>${paragraph.map((line) => this.renderInlineMarkdown(line)).join("<br>")}</p>`);
          paragraph = [];
        }
      };
      const closeOneList = () => {
        const list = listStack.pop();
        if (!list) {
          return;
        }
        if (list.liOpen) {
          html.push("</li>");
        }
        html.push(`</${list.type}>`);
      };
      const closeLists = () => {
        while (listStack.length) {
          closeOneList();
        }
      };
      const openList = (type, indent) => {
        html.push(`<${type}>`);
        listStack.push({ type, indent, liOpen: false });
      };
      const alignList = (type, indent) => {
        while (listStack.length && indent < listStack[listStack.length - 1].indent) {
          closeOneList();
        }

        let current = listStack[listStack.length - 1];
        if (current && indent === current.indent && type !== current.type) {
          closeOneList();
        }

        current = listStack[listStack.length - 1];
        if (!current || indent > current.indent || indent !== current.indent) {
          openList(type, indent);
        }
      };
      const addListItem = (type, indent, text) => {
        closeParagraph();
        alignList(type, indent);
        const current = listStack[listStack.length - 1];
        if (current.liOpen) {
          html.push("</li>");
        }
        html.push(`<li>${this.renderInlineMarkdown(text)}`);
        current.liOpen = true;
      };

      lines.forEach((rawLine) => {
        const normalizedLine = rawLine.replace(/\t/g, "  ");
        const line = normalizedLine.trim();
        if (!line) {
          closeParagraph();
          closeLists();
          return;
        }

        const heading = line.match(/^(#{1,6})\s+(.+)$/);
        if (heading) {
          closeParagraph();
          closeLists();
          const level = Math.min(heading[1].length, 4);
          html.push(`<h${level}>${this.renderInlineMarkdown(heading[2])}</h${level}>`);
          return;
        }

        const indent = normalizedLine.match(/^ */)[0].length;
        const listContent = normalizedLine.slice(indent);
        const unordered = listContent.match(/^[-*+]\s+(.+)$/);
        if (unordered) {
          addListItem("ul", indent, unordered[1]);
          return;
        }

        const ordered = listContent.match(/^\d+\.\s+(.+)$/);
        if (ordered) {
          addListItem("ol", indent, ordered[1]);
          return;
        }

        closeLists();
        paragraph.push(line);
      });

      closeParagraph();
      closeLists();
      return html.join("");
    },
    renderInlineMarkdown(value) {
      return this.escapeHtml(value)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/__([^_]+)__/g, "<strong>$1</strong>")
        .replace(/\*([^*]+)\*/g, "<em>$1</em>");
    },
    escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    },
    restoreFailedMessage(data) {
      return data?.msg
        ? `${this.$t("agentSnapshot.restoreFailedRollback")}: ${data.msg}`
        : this.$t("agentSnapshot.restoreFailedRollback");
    },
    resolveDiffFields(beforeData, afterData, changedFields = null, fieldOrder = [], forceCompare = false) {
      const hasBackendChangedFields = Array.isArray(changedFields);
      const safeChangedFields = hasBackendChangedFields ? changedFields : [];
      const directFields = safeChangedFields
        .filter((field) => field && field !== "restore")
        .map((field) => this.canonicalField(field));
      if (!forceCompare && hasBackendChangedFields) {
        return Array.from(new Set(directFields));
      }

      const candidates = this.snapshotFieldOrder(fieldOrder, beforeData, afterData);

      return Array.from(new Set(candidates)).filter((field) => {
        return !this.isSameFieldValue(
          field,
          this.getFieldValue(beforeData, field),
          this.getFieldValue(afterData, field)
        );
      });
    },
    snapshotFieldOrder(fieldOrder = [], beforeData = {}, afterData = {}) {
      const backendOrder = Array.isArray(fieldOrder) ? fieldOrder : [];
      if (backendOrder.length) {
        return backendOrder.map((field) => this.canonicalField(field));
      }
      const dataFields = [
        ...Object.keys(beforeData || {}),
        ...Object.keys(afterData || {})
      ].map((field) => this.canonicalField(field));
      return Array.from(new Set(dataFields)).filter((field) => field !== "tags");
    },
    canonicalField(field) {
      return field === "tags" || field === "tagIds" ? "tagNames" : field;
    },
    getFieldValue(data, field) {
      if (!data) {
        return null;
      }
      if (field === "tagNames") {
        return data.tagNames || (data.tags || []).map((tag) => tag.tagName);
      }
      if (field === "tagIds") {
        return (data.tags || []).map((tag) => tag.id).filter(Boolean);
      }
      return data[field];
    },
    isSameValue(left, right) {
      return this.isEquivalentValue(this.normalizeValue(left), this.normalizeValue(right));
    },
    isSameFieldValue(field, left, right) {
      return this.isEquivalentValue(
        this.normalizeValueForField(field, left),
        this.normalizeValueForField(field, right)
      );
    },
    normalizeValueForField(field, value) {
      if (field === "functions") {
        return this.normalizeFunctionMap(value);
      }
      if (field === "contextProviders") {
        return normalizeSnapshotOrderedValue(Array.isArray(value) ? value : []);
      }
      if (["ttsVolume", "ttsRate", "ttsPitch"].includes(field)) {
        return this.normalizeDefaultTtsNumber(value);
      }
      if (field === "summaryMemory") {
        return value === null || value === undefined || String(value).trim() === "" ? "" : String(value);
      }
      if (field === "correctWordFileIds" || field === "tagNames") {
        return Array.isArray(value)
          ? value.filter((item) => item !== null && item !== undefined && String(item).trim() !== "")
            .map((item) => String(item))
            .sort()
          : [];
      }
      return this.normalizeValue(value);
    },
    normalizeDefaultTtsNumber(value) {
      if (value === null || value === undefined || String(value).trim() === "") {
        return null;
      }
      if (typeof value === "number") {
        return Math.trunc(value);
      }
      const text = String(value).trim();
      return /^[+-]?\d+$/.test(text) ? Number.parseInt(text, 10) : text;
    },
    isEquivalentValue(left, right) {
      if (left === SNAPSHOT_SECRET_REDACTED || right === SNAPSHOT_SECRET_REDACTED) {
        return true;
      }
      if (Array.isArray(left) || Array.isArray(right)) {
        if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) {
          return false;
        }
        return left.every((item, index) => this.isEquivalentValue(item, right[index]));
      }
      if (this.isPlainObject(left) || this.isPlainObject(right)) {
        if (!this.isPlainObject(left) || !this.isPlainObject(right)) {
          return false;
        }
        const keys = Array.from(new Set([
          ...Object.keys(left),
          ...Object.keys(right)
        ]));
        return keys.every((key) => this.isEquivalentValue(left[key], right[key]));
      }
      return left === right;
    },
    normalizeValue(value) {
      return normalizeSnapshotOrderedValue(value);
    },
    isPlainObject(value) {
      return value !== null && typeof value === "object" && !Array.isArray(value);
    },
    formatDisplayValue(field, value, data = {}) {
      if (MODEL_FIELD_TYPES[field]) {
        return this.modelDisplayName(value);
      }
      if (field === "ttsVoiceId") {
        return this.voiceDisplayName(data.ttsModelId, value);
      }
      if (field === "chatHistoryConf") {
        return this.translateKey(CHAT_HISTORY_CONF_LABEL_KEYS[value] || CHAT_HISTORY_CONF_LABEL_KEYS[Number(value)])
          || this.formatValue(value);
      }
      if (field === "correctWordFileIds") {
        return this.correctWordDisplayNames(value);
      }
      return this.formatValue(value, field);
    },
    modelDisplayName(value) {
      if (value === null || value === undefined || value === "") {
        return this.$t("agentSnapshot.emptyValue");
      }
      return this.modelNameMap[value] || this.translateKey(FALLBACK_MODEL_NAME_KEYS[value], String(value)) || String(value);
    },
    voiceDisplayName(modelId, value) {
      if (value === null || value === undefined || value === "") {
        return this.$t("agentSnapshot.emptyValue");
      }
      return this.voiceNameMap[`${modelId}:${value}`] || this.voiceNameMap[value]
        || this.translateKey(FALLBACK_VOICE_NAME_KEYS[value], String(value)) || String(value);
    },
    correctWordDisplayNames(value) {
      if (!Array.isArray(value) || value.length === 0) {
        return this.$t("agentSnapshot.emptyValue");
      }
      return value
        .map((id) => this.correctWordNameMap[id] || id)
        .join(", ");
    },
    formatValue(value, parentKey = "") {
      if (value === null || value === undefined || value === "") {
        return this.$t("agentSnapshot.emptyValue");
      }
      if (Array.isArray(value) && value.length === 0) {
        return this.$t("agentSnapshot.emptyValue");
      }
      const displayValue = this.localizedSnapshotDisplayValue(value, parentKey);
      if (Array.isArray(displayValue) && displayValue.every((item) => this.isPrimitiveValue(item))) {
        return displayValue.join(", ");
      }
      if (this.isComplexValue(displayValue)) {
        return JSON.stringify(displayValue, null, 2);
      }
      return String(displayValue);
    },
    localizedSnapshotDisplayValue(value, parentKey = "") {
      return redactSnapshotDisplayValue(
        value,
        this.$t("agentSnapshot.secretRedacted"),
        parentKey
      );
    },
    isPrimitiveValue(value) {
      return value === null || ["string", "number", "boolean"].includes(typeof value);
    },
    isComplexValue(value) {
      return value !== null && typeof value === "object";
    },
    formatTime(value) {
      return formatDate(value);
    },
    sourceLabel(source) {
      const key = `agentSnapshot.source.${source || "config"}`;
      return this.$te && this.$te(key) ? this.$t(key) : source;
    },
    fieldLabel(field) {
      const key = `agentSnapshot.field.${field}`;
      return this.$te && this.$te(key) ? this.$t(key) : field;
    },
    translateKey(key, fallback = "") {
      return key && this.$te && this.$te(key) ? this.$t(key) : fallback;
    }
  }
};
</script>

<style lang="scss" scoped>
@import '@/styles/global.scss';

::v-deep .el-dialog {
  margin-top: 6vh !important;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

::v-deep .el-dialog__header {
  padding: 16px 20px 12px;
  background: linear-gradient(135deg, #e2eeff, #edeafe);
  text-align: left;
}

::v-deep .el-dialog__title {
  color: #1a1a1a;
  font-size: 16px;
  font-weight: 500;
}

.snapshot-dialog-title {
  display: inline-flex;
  align-items: center;
  font-size: 18px;

  > span {
    line-height: 18px;
    font-weight: 500;
  }
}

.snapshot-title-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-right: 8px;
  color: #4a7cfd;
  font-size: 24px;
  line-height: 1;
}

::v-deep .el-dialog__headerbtn {
  top: 12px;
  right: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);

  .el-dialog__close {
    position: static;
    color: #666;
    font-size: 18px;
    transform: none;
  }

  &:hover {
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);

    .el-dialog__close {
      color: #333;
    }
  }
}

::v-deep .el-dialog__body {
  padding: 20px;
}

::v-deep .el-dialog__footer {
  padding: 12px 20px 16px;
}

.snapshot-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.snapshot-footer-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 96px;
  height: 36px;
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s ease;

  & + .snapshot-footer-button {
    margin-left: 0;
  }
}

.snapshot-footer-cancel {
  border: 1px solid #d7e1ff;
  background: #f7f9ff;
  color: #4a7cfd;

  &:hover,
  &:focus {
    border-color: #4a7cfd;
    background: #eef4ff;
    color: #4a7cfd;
    box-shadow: 0 2px 8px rgba(74, 124, 253, 0.14);
    transform: translateY(-2px);
  }
}

.snapshot-footer-confirm {
  border: none;
  background: linear-gradient(to right, #4a7cfd, #8154fc);
  color: #fff;

  &:hover,
  &:focus {
    border-color: transparent;
    background: linear-gradient(to right, #4a7cfd, #8154fc);
    color: #fff;
    box-shadow: 0 2px 8px rgba(74, 124, 253, 0.3);
    transform: translateY(-2px);
    opacity: 0.88;
  }

  &.is-disabled,
  &.is-disabled:hover,
  &.is-disabled:focus {
    border-color: transparent;
    background: linear-gradient(to right, #a0b4fd, #b8a4fd);
    color: rgba(255, 255, 255, 0.6);
    box-shadow: none;
    transform: none;
    cursor: not-allowed;
    opacity: 1;
  }
}

.confirm-inner {
  display: inline-flex;
  align-items: center;
}

.confirm-icon {
  margin-right: 5px;
  font-size: 16px;
}

.snapshot-table {
  width: 100%;
}

.snapshot-table-wrapper {
  max-height: 62vh;
  overflow: auto;
  @include scrollbar-style;
}

.version-cell {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  white-space: nowrap;
}

.latest-version-icon {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.12);
}

::v-deep .current-version-row {
  background: #fbfffa;
}

.snapshot-delete-button {
  color: #f56c6c;
}

.field-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.field-tags-empty {
  color: #a3a8b8;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.snapshot-diff {
  min-height: 220px;
  max-height: 62vh;
  overflow: auto;
  padding-right: 2px;
  @include scrollbar-style;
}

.restore-risk-alert {
  margin-top: 14px;
}

.detail-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  color: #606266;
  font-size: 12px;
  text-align: left;
}

.detail-summary span {
  padding: 4px 9px;
  border-radius: 4px;
  background: #f4f6ff;
  color: #4d5b7c;
}

.diff-item {
  margin-bottom: 16px;
  overflow: hidden;
  border: 1px solid #e9e9e9;
  border-radius: 8px;
  background: #fff;
}

.diff-field {
  padding: 12px 16px;
  border-bottom: 1px solid #e9e9e9;
  background: #fafbff;
  color: #3d4566;
  font-size: 16px;
  font-weight: 700;
  text-align: left;
}

.diff-values {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.diff-values.is-single {
  grid-template-columns: minmax(0, 1fr);
}

.diff-pane {
  min-width: 0;
  padding: 12px 14px;
  text-align: left;
}

.diff-after {
  border-left: 1px solid #e9e9e9;
}

.diff-values.is-single .diff-after {
  border-left: 0;
}

.diff-pane-title {
  margin-bottom: 8px;
  color: #3d4566;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  text-align: left;
}

.diff-value {
  box-sizing: border-box;
  min-height: 40px;
  max-height: 260px;
  overflow: auto;
  padding: 9px 12px;
  margin: 0;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.45;
  word-break: break-word;
  text-align: left;
  @include scrollbar-style;
}

.diff-before .diff-value {
  background: #fff8f8;
  color: #663434;
}

.diff-after .diff-value {
  background: #f7fbf4;
  color: #2d5c3a;
}

.is-complex .diff-value {
  max-height: 340px;
}

.diff-text {
  margin: 0;
  font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  text-align: left;
}

.function-change-view {
  padding: 16px;
  background: #fff;
}

.function-change-view.is-single {
  padding: 0;
}

.function-toggle-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.function-toggle-card {
  padding: 14px 16px;
  border: 1px solid #dfe7ff;
  border-radius: 8px;
  background: #fbfdff;
  box-shadow: 0 2px 8px rgba(31, 48, 96, 0.04);
}

.function-toggle-card.is-added {
  border-color: #dcefdc;
  background: #fbfffa;
}

.function-toggle-card.is-removed {
  border-color: #f5d6d6;
  background: #fffafa;
}

.function-toggle-card.is-updated {
  border-color: #dfe7ff;
  background: #fbfdff;
}

.function-toggle-card.is-single .function-state-pane {
  margin-top: 10px;
}

.function-toggle-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.function-dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 50%;
  background: #6278ff;
}

.function-toggle-card.is-removed .function-dot {
  background: #f56c6c;
}

.function-toggle-card.is-added .function-dot {
  background: #67c23a;
}

.function-change-title-wrap {
  min-width: 0;
  flex: 1;
}

.function-change-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.function-change-name {
  color: #30415f;
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  word-break: break-word;
}

.function-change-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef4ff;
  color: #4d65d9;
  font-size: 12px;
  line-height: 1.5;
}

.function-toggle-card.is-added .function-change-badge {
  background: #edf8e8;
  color: #4f9b2d;
}

.function-toggle-card.is-removed .function-change-badge {
  background: #fff0f0;
  color: #d24b4b;
}

.function-state-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  margin-top: 10px;
}

.function-state-pane {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #edf0f7;
  border-radius: 6px;
  background: #fff;
}

.function-state-pane.is-before {
  background: #fffafa;
}

.function-state-pane.is-after {
  background: #fbfffa;
}

.function-state-pane.is-disabled {
  background: #fafbff;
}

.function-state-title {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  color: #3d4566;
  font-size: 14px;
  font-weight: 600;
}

.function-state-badge {
  flex: 0 0 auto;
  padding: 1px 8px;
  border-radius: 999px;
  background: #edf8e8;
  color: #4f9b2d;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
}

.function-state-pane.is-disabled .function-state-badge {
  background: #f0f2f7;
  color: #8b93a7;
}

.function-state-params {
  display: block;
}

.function-param-row {
  display: grid;
  grid-template-columns: minmax(78px, 118px) minmax(0, 1fr);
  align-items: stretch;
}

.function-param-row + .function-param-row {
  border-top: 1px solid #e6ebf5;
}

.function-param-row.is-changed {
  background: #fff7e6;
}

.param-key {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
  min-height: 28px;
  padding: 5px 10px 5px 0;
  color: #69738f;
  font-size: 12px;
  line-height: 1.35;
  text-align: right;
  overflow-wrap: anywhere;
}

.param-value {
  min-width: 0;
  min-height: 28px;
  padding: 5px 0 5px 10px;
  border-left: 1px solid #e6ebf5;
  color: #303133;
  font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}

.function-state-empty {
  color: #a3a8b8;
  font-size: 13px;
  line-height: 1.6;
}

.value-empty {
  color: #a3a8b8;
  font-size: 13px;
}

.markdown-body {
  color: inherit;
  font-size: 13px;
  line-height: 1.7;
  text-align: left;
  white-space: normal;
}

.markdown-body ::v-deep h1,
.markdown-body ::v-deep h2,
.markdown-body ::v-deep h3,
.markdown-body ::v-deep h4 {
  margin: 0 0 8px;
  color: #3d4566;
  font-weight: 700;
  line-height: 1.4;
}

.markdown-body ::v-deep h1 {
  font-size: 18px;
}

.markdown-body ::v-deep h2 {
  font-size: 16px;
}

.markdown-body ::v-deep h3,
.markdown-body ::v-deep h4 {
  font-size: 14px;
}

.markdown-body ::v-deep p {
  margin: 0 0 8px;
}

.markdown-body ::v-deep p:last-child,
.markdown-body ::v-deep ul:last-child,
.markdown-body ::v-deep ol:last-child {
  margin-bottom: 0;
}

.markdown-body ::v-deep ul,
.markdown-body ::v-deep ol {
  margin: 0 0 8px;
  padding-left: 20px;
}

.markdown-body ::v-deep li {
  margin-bottom: 4px;
}

.markdown-body ::v-deep code {
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(87, 120, 255, 0.12);
  color: #3d4566;
  font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 12px;
}

.markdown-body ::v-deep strong {
  color: #303133;
  font-weight: 700;
}

.markdown-body ::v-deep .markdown-empty {
  color: #a3a8b8;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 720px) {
  .diff-values {
    grid-template-columns: 1fr;
  }

  .diff-after {
    border-left: 0;
    border-top: 1px solid #e9e9e9;
  }

  .function-state-grid,
  .function-param-row {
    grid-template-columns: 1fr;
  }

  .param-key {
    justify-content: flex-start;
    padding: 7px 0 2px;
    text-align: left;
  }

  .param-value {
    min-height: 0;
    padding: 0 0 7px;
    border-left: 0;
  }
}
</style>
