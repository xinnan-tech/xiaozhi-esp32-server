<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">{{ $t("roleConfig.title") }}</h2>
    </div>

    <div class="main-wrapper" v-loading="agentReloading">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="config-card" shadow="never">
            <div class="config-header">
              <div class="header-left">
                <div class="header-icon">
                  <img loading="lazy" src="@/assets/home/setting-user.png" alt="" />
                </div>
                <span class="header-title">{{ form.agentName }}</span>
                <span v-if="currentVersionNo" class="current-version-tag">
                  {{ $t("roleConfig.currentVersion", { version: currentVersionNo }) }}
                </span>
              </div>
              <div class="header-tags">
                <el-tag
                  v-for="tag in dynamicTags"
                  :key="tag.id"
                  class="custom-tag"
                  closable
                  :disable-transitions="false"
                  @close="handleClose(tag.id)">
                  {{tag.tagName}}
                </el-tag>
                <el-input
                  class="input-new-tag"
                  v-if="inputVisible"
                  v-model="inputValue"
                  ref="saveTagInput"
                  size="small"
                  maxLength="20"
                  @keyup.enter.native="handleInputConfirm"
                  @blur="handleInputConfirm"
                >
                </el-input>
                <el-button class="custom-tag-btn" v-else size="small" @click="showInput">+ {{ $t("roleConfig.addTag") }}</el-button>
              </div>
              <div class="header-actions">
                <div class="hint-text">
                  <img loading="lazy" src="@/assets/home/info.png" alt="" />
                  <span>{{ $t("roleConfig.restartNotice") }}</span>
                </div>
                <el-button class="history-btn" @click="showSnapshotDialog = true">
                  {{ $t("roleConfig.snapshotHistory") }}
                </el-button>
                <el-button
                  type="primary"
                  class="save-btn"
                  :disabled="configInteractionBlocked"
                  @click="saveConfig"
                >
                  {{ $t("roleConfig.saveConfig") }}
                </el-button>
                <el-button class="reset-btn" @click="resetConfig">{{
                  $t("roleConfig.reset")
                }}</el-button>
                <button class="custom-close-btn" @click="goToHome">×</button>
              </div>
            </div>
            <div class="divider"></div>

            <el-form ref="form" :model="form" label-width="72px">
              <div class="form-content">
                <div class="form-grid">
                  <div class="form-column">
                    <el-form-item>
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.agentName')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.agentName') }}:</span>
                        </el-tooltip>
                      </template>
                      <el-input
                        v-model="form.agentName"
                        class="form-input"
                        maxlength="64"
                      />
                    </el-form-item>
                    <el-form-item>
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.roleTemplate')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.roleTemplate') }}:</span>
                        </el-tooltip>
                      </template>
                      <div class="template-container">
                        <div
                          v-for="(template, index) in templates"
                          :key="`template-${index}`"
                          class="template-item"
                          :class="{ 'template-loading': loadingTemplate }"
                          @click="selectTemplate(template)"
                        >
                          {{ template.agentName }}
                        </div>
                      </div>
                    </el-form-item>
                    <el-form-item class="context-provider-item">
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.contextProvider')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.contextProvider') }}:</span>
                        </el-tooltip>
                      </template>
                      <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="color: #606266; font-size: 13px;">
                          {{ $t('roleConfig.contextProviderSuccess', { count: currentContextProviders.length }) }}<a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/context-provider-integration.md" target="_blank" class="doc-link">{{ $t('roleConfig.contextProviderDocLink') }}</a>
                        </span>
                        <el-button
                          class="edit-function-btn"
                          size="small"
                          @click="openContextProviderDialog"
                        >
                          {{ $t('roleConfig.editContextProvider') }}
                        </el-button>
                      </div>
                    </el-form-item>
                    <el-form-item>
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.roleIntroduction')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.roleIntroduction') }}:</span>
                        </el-tooltip>
                      </template>
                      <el-input
                        type="textarea"
                        rows="8"
                        resize="none"
                        :placeholder="$t('roleConfig.pleaseEnterContent')"
                        v-model="form.systemPrompt"
                        maxlength="2000"
                        show-word-limit
                        class="form-textarea"
                      />
                    </el-form-item>

                    <el-form-item>
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.memoryHis')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.memoryHis') }}:</span>
                        </el-tooltip>
                      </template>
                      <el-input
                        type="textarea"
                        rows="4"
                        resize="none"
                        v-model="form.summaryMemory"
                        maxlength="2000"
                        show-word-limit
                        class="form-textarea"
                        :disabled="form.model.memModelId !== 'Memory_mem_local_short'"
                      />
                    </el-form-item>
                    <el-form-item
                      style="display: none"
                    >
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.languageCode')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.languageCode') }}:</span>
                        </el-tooltip>
                      </template>
                      <el-input
                        v-model="form.langCode"
                        :placeholder="$t('roleConfig.pleaseEnterLangCode')"
                        maxlength="10"
                        show-word-limit
                        class="form-input"
                      />
                    </el-form-item>
                    <el-form-item
                      style="display: none"
                    >
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.interactionLanguage')" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.interactionLanguage') }}:</span>
                        </el-tooltip>
                      </template>
                      <el-input
                        v-model="form.language"
                        :placeholder="$t('roleConfig.pleaseEnterLangName')"
                        maxlength="10"
                        show-word-limit
                        class="form-input"
                      />
                    </el-form-item>
                  </div>
                  <div class="form-column">
                    <div class="model-row">
                      <el-form-item 
                        v-if="featureStatus.vad" 
                        class="model-item"
                      >
                        <template #label>
                          <el-tooltip :content="$t('roleConfig.tooltip.vad')" placement="top" effect="light" popper-class="custom-tooltip">
                            <span>{{ $t('roleConfig.vad') }}</span>
                          </el-tooltip>
                        </template>
                        <div class="model-select-wrapper">
                          <el-select
                            v-model="form.model.vadModelId"
                            filterable
                            :placeholder="$t('roleConfig.pleaseSelect')"
                            class="form-select"
                            @change="handleModelChange('VAD', $event)"
                          >
                            <el-option
                              v-for="(item, optionIndex) in modelOptions['VAD']"
                              :key="`option-vad-${optionIndex}`"
                              :label="item.label"
                              :value="item.value"
                            />
                          </el-select>
                        </div>
                      </el-form-item>
                      <el-form-item 
                        v-if="featureStatus.asr" 
                        class="model-item"
                      >
                        <template #label>
                          <el-tooltip :content="$t('roleConfig.tooltip.asr')" placement="top" effect="light" popper-class="custom-tooltip">
                            <span>{{ $t('roleConfig.asr') }}</span>
                          </el-tooltip>
                        </template>
                        <div class="model-select-wrapper">
                          <el-select
                            v-model="form.model.asrModelId"
                            filterable
                            :placeholder="$t('roleConfig.pleaseSelect')"
                            class="form-select"
                            @change="handleModelChange('ASR', $event)"
                          >
                            <el-option
                              v-for="(item, optionIndex) in modelOptions['ASR']"
                              :key="`option-asr-${optionIndex}`"
                              :label="item.label"
                              :value="item.value"
                            />
                          </el-select>
                        </div>
                      </el-form-item>
                    </div>
                    <div class="model-row">
                      <el-form-item class="model-item">
                        <template #label>
                          <el-tooltip :content="$t('roleConfig.tooltip.llm')" placement="top" effect="light" popper-class="custom-tooltip">
                            <span>{{ $t('roleConfig.llm') }}</span>
                          </el-tooltip>
                        </template>
                        <div class="model-select-wrapper">
                          <el-select
                            v-model="form.model.llmModelId"
                            filterable
                            :placeholder="$t('roleConfig.pleaseSelect')"
                            class="form-select"
                            @change="handleModelChange('LLM', $event)"
                          >
                            <el-option
                              v-for="(item, optionIndex) in modelOptions['LLM']"
                              :key="`option-asr-${optionIndex}`"
                              :label="item.label"
                              :value="item.value"
                            />
                          </el-select>
                        </div>
                      </el-form-item>
                      <el-form-item class="model-item">
                        <template #label>
                          <el-tooltip :content="$t('roleConfig.tooltip.slm')" placement="top" effect="light" popper-class="custom-tooltip">
                            <span>{{ $t('roleConfig.slm') }}</span>
                          </el-tooltip>
                        </template>
                        <div class="model-select-wrapper">
                          <el-select
                            v-model="form.model.slmModelId"
                            filterable
                            :placeholder="$t('roleConfig.pleaseSelect')"
                            class="form-select"
                          >
                            <el-option
                              v-for="(item, optionIndex) in modelOptions['LLM']"
                              :key="`option-asr-${optionIndex}`"
                              :label="item.label"
                              :value="item.value"
                            />
                          </el-select>
                        </div>
                      </el-form-item>
                    </div>
                    <el-form-item
                      v-for="(model, index) in models.slice(4)"
                      :key="`model-${index}`"
                      class="model-item"
                    >
                      <template #label>
                        <el-tooltip :content="$t('roleConfig.tooltip.' + model.type.toLowerCase())" placement="top" effect="light" popper-class="custom-tooltip">
                          <span>{{ $t('roleConfig.' + model.type.toLowerCase()) }}</span>
                        </el-tooltip>
                      </template>
                      <div class="model-select-wrapper">
                        <el-select
                          v-model="form.model[model.key]"
                          filterable
                          :disabled="model.type === 'TTS' && voiceOptionsLoading"
                          :placeholder="$t('roleConfig.pleaseSelect')"
                          class="form-select"
                          @change="handleModelChange(model.type, $event)"
                        >
                          <el-option
                            v-for="(item, optionIndex) in modelOptions[model.type]"
                            v-if="!item.isHidden"
                            :key="`option-${index}-${optionIndex}`"
                            :label="item.label"
                            :value="item.value"
                          />
                        </el-select>
                        <div v-if="showFunctionIcons(model.type)" class="function-icons">
                          <el-tooltip
                            v-for="func in currentFunctions"
                            :key="func.name"
                            effect="light"
                            placement="top"
                          >
                            <div slot="content">
                              <div><strong>{{ $t('roleConfig.functionName') }}</strong> {{ func.name }}</div>
                            </div>
                            <div class="icon-dot">
                              {{ getFunctionDisplayChar(func.name) }}
                            </div>
                          </el-tooltip>
                          <el-button
                            class="edit-function-btn"
                            @click="openFunctionDialog"
                            :class="{ 'active-btn': showFunctionDialog }"
                          >
                            {{ $t("roleConfig.editFunctions") }}
                          </el-button>
                        </div>
                        <div
                          v-if="
                            model.type === 'Memory' &&
                            form.model.memModelId !== 'Memory_nomem'
                          "
                          class="chat-history-options"
                        >
                          <el-radio-group
                            v-model="form.chatHistoryConf"
                            @change="updateChatHistoryConf"
                          >
                            <el-radio-button :label="1">{{
                              $t("roleConfig.reportText")
                            }}</el-radio-button>
                            <el-radio-button :label="2">{{
                              $t("roleConfig.reportTextVoice")
                            }}</el-radio-button>
                          </el-radio-group>
                        </div>
                      </div>
                    </el-form-item>
                    <div class="model-row">
                      <!-- Language filter -->
                      <el-form-item class="model-item language-select-item">
                        <template #label>
                          <el-tooltip :content="$t('roleConfig.tooltip.language')" placement="top" effect="light" popper-class="custom-tooltip">
                            <span>{{ $t('roleConfig.language') }}</span>
                          </el-tooltip>
                        </template>
                        <div class="model-select-wrapper">
                          <el-select
                            v-model="selectedLanguage"
                            :disabled="voiceOptionsLoading"
                            :placeholder="$t('roleConfig.selectLanguage')"
                            class="form-select language-select"
                            @change="handleLanguageChange"
                          >
                            <el-option
                              v-for="(lang, index) in languageOptions"
                              :key="`lang-${index}`"
                              :label="lang.label"
                              :value="lang.value"
                            />
                          </el-select>
                        </div>
                      </el-form-item>

                      <!-- Voice selector -->
                      <el-form-item class="model-item">
                        <template #label>
                          <el-tooltip :content="$t('roleConfig.tooltip.voiceType')" placement="top" effect="light" popper-class="custom-tooltip">
                            <span>{{ $t('roleConfig.voiceType') }}</span>
                          </el-tooltip>
                        </template>
                        <div class="model-select-wrapper">
                          <el-select
                            v-model="form.ttsVoiceId"
                            filterable
                            :disabled="voiceOptionsLoading"
                            :placeholder="$t('roleConfig.pleaseSelect')"
                            class="form-select"
                            @change="handleVoiceChange"
                          >
                            <el-option
                              v-for="(item, index) in voiceOptions"
                              :key="`voice-${index}`"
                              :label="item.label"
                              :value="item.value"
                            >
                              <div
                                style="
                                  display: flex;
                                  justify-content: space-between;
                                  align-items: center;
                                "
                              >
                                <span>{{ item.label }}</span>
                                <template v-if="hasAudioPreview(item)">
                                  <el-button
                                    type="text"
                                    :icon="
                                      playingVoice &&
                                      currentPlayingVoiceId === item.value &&
                                      !isPaused
                                        ? 'el-icon-video-pause'
                                        : 'el-icon-video-play'
                                    "
                                    size="small"
                                    @click.stop="toggleAudioPlayback(item.value)"
                                    :loading="false"
                                    class="play-button"
                                  />
                                </template>
                              </div>
                            </el-option>
                          </el-select>
                          <el-button
                            class="edit-function-btn"
                            style="margin-left: 10px;"
                            @click="openTtsAdvancedSettings"
                          >
                            {{ $t('roleConfig.advancedSettings') }}
                          </el-button>
                        </div>
                      </el-form-item>
                    </div>
                  </div>
                </div>
              </div>
            </el-form>
          </el-card>
        </div>
      </div>
    </div>
    <function-dialog
      v-model="showFunctionDialog"
      :functions="currentFunctions"
      :all-functions="allFunctions"
      :agent-id="$route.query.agentId"
      @update-functions="handleUpdateFunctions"
      @dialog-closed="handleDialogClosed"
    />
    <context-provider-dialog
      :visible.sync="showContextProviderDialog"
      :providers="currentContextProviders"
      @confirm="handleUpdateContext"
    />
    <tts-advanced-settings
      :visible.sync="showTtsAdvancedDialog"
      :settings="ttsSettings"
      :checked-replacement-word-ids="checkedReplacementWordIds"
      @save="handleTtsSettingsSave"
    />
      <agent-snapshot-dialog
        v-if="$route.query.agentId"
        :visible.sync="showSnapshotDialog"
        :agent-id="$route.query.agentId"
        :current-version-no="currentVersionNo"
        @restored="handleSnapshotRestored"
      />
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import { getServiceUrl } from "@/apis/api";
import RequestService from "@/apis/httpRequest";
import FunctionDialog from "@/components/FunctionDialog.vue";
import ContextProviderDialog from "@/components/ContextProviderDialog.vue";
import TtsAdvancedSettings from "@/components/TtsAdvancedSettings.vue";
import AgentSnapshotDialog from "@/components/AgentSnapshotDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import i18n from "@/i18n";
import featureManager from "@/utils/featureManager"; 
import VersionFooter from "@/components/VersionFooter.vue";

export default {
  name: "RoleConfigPage",
  components: { HeaderBar, FunctionDialog, ContextProviderDialog, TtsAdvancedSettings, AgentSnapshotDialog, VersionFooter },
  data() {
    return {
      showContextProviderDialog: false,
      showTtsAdvancedDialog: false,
      showSnapshotDialog: false,
      ttsSettings: {
        volume: 0,
        speed: 0,
        pitch: 0
      },
      tempSummaryMemory: "",
      form: {
        agentCode: "",
        agentName: "",
        ttsVoiceId: "",
        ttsVolume: null,
        ttsRate: null,
        ttsPitch: null,
        chatHistoryConf: 0,
        systemPrompt: "",
        summaryMemory: "",
        langCode: "",
        language: "",
        sort: "",
        model: {
          ttsModelId: "",
          vadModelId: "",
          asrModelId: "",
          llmModelId: "",
          slmModelId: "",
          vllmModelId: "",
          memModelId: "",
          intentModelId: "",
        },
      },
      models: [
        { label: this.$t("roleConfig.vad"), key: "vadModelId", type: "VAD" },
        { label: this.$t("roleConfig.asr"), key: "asrModelId", type: "ASR" },
        { label: this.$t("roleConfig.llm"), key: "llmModelId", type: "LLM" },
        { label: this.$t("roleConfig.slm"), key: "slmModelId", type: "SLM" },
        { label: this.$t("roleConfig.vllm"), key: "vllmModelId", type: "VLLM" },
        { label: this.$t("roleConfig.intent"), key: "intentModelId", type: "Intent" },
        { label: this.$t("roleConfig.memory"), key: "memModelId", type: "Memory" },
        { label: this.$t("roleConfig.tts"), key: "ttsModelId", type: "TTS" },
      ],
      llmModeTypeMap: new Map(),
      modelOptions: {},
      templates: [],
      loadingTemplate: false,
      voiceOptions: [],
      voiceDetails: {}, // Save complete voice info
      showFunctionDialog: false,
      currentVersionNo: null,
      currentFunctions: [],
      currentContextProviders: [],
      allFunctions: [],
      originalFunctions: [],
      playingVoice: false,
      isPaused: false,
      currentAudio: null,
      currentPlayingVoiceId: null,
      // Language filter related state
      languageOptions: [], // Language Options List
      selectedLanguage: '', // Currently selected language
      ttsLanguageTouched: false,
      ttsVoiceTouched: false,
      voiceFetchSeq: 0,
      voiceOptionsLoading: false,
      lastValidTtsDraft: null,
      agentReloading: false,
      agentReloadSeq: 0,
      agentConfigFetchSeq: 0,
      agentTagsFetchSeq: 0,
      currentVersionFetchSeq: 0,
      agentConfigLoaded: false,
      agentFunctionsLoaded: false,
      agentTagsLoaded: false,
      currentVersionLoaded: false,
      pluginMetadataReady: false,
      pluginMetadataLoading: null,
      // Feature status
      featureStatus: {
        vad: false, // Language detection activity status
        asr: false, // Speech recognition feature state
      },
      dynamicTags: [],
      originalTagNames: [],
      inputVisible: false,
      inputValue: '',
      checkedReplacementWordIds: []
    };
  },
  computed: {
    configInteractionBlocked() {
      return this.agentReloading
        || this.voiceOptionsLoading
        || !this.agentConfigLoaded
        || !this.agentFunctionsLoaded
        || !this.agentTagsLoaded;
    }
  },
  methods: {
    goToHome() {
      this.$router.push("/home");
    },
    normalizeFunctionParams(params, fallback = {}) {
      if (params === null || params === undefined || params === '') {
        return { ...fallback };
      }
      if (typeof params === 'string') {
        try {
          const parsed = JSON.parse(params);
          return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
            ? parsed
            : { ...fallback };
        } catch (error) {
          return { ...fallback };
        }
      }
      if (typeof params === 'object' && !Array.isArray(params)) {
        return { ...params };
      }
      return { ...fallback };
    },
    async saveConfig() {
      if (this.configInteractionBlocked) {
        return;
      }
      const configData = {
        agentCode: this.form.agentCode,
        agentName: this.form.agentName,
        asrModelId: this.form.model.asrModelId,
        vadModelId: this.form.model.vadModelId,
        llmModelId: this.form.model.llmModelId,
        slmModelId: this.form.model.slmModelId,
        vllmModelId: this.form.model.vllmModelId,
        ttsModelId: this.form.model.ttsModelId,
        chatHistoryConf: this.form.chatHistoryConf,
        memModelId: this.form.model.memModelId,
        intentModelId: this.form.model.intentModelId,
        systemPrompt: this.form.systemPrompt,
        summaryMemory: this.form.summaryMemory,
        langCode: this.form.langCode,
        language: this.form.language,
        sort: this.form.sort,
        functions: this.currentFunctions.map((item) => {
          return {
            pluginId: item.id,
            paramInfo: this.normalizeFunctionParams(item.params),
          };
        }),
        contextProviders: this.currentContextProviders,
        correctWordFileIds: this.checkedReplacementWordIds,
      };
      const tagNames = this.dynamicTags.map(tag => tag.tagName);
      const tagsChanged = !this.isSameStringList(tagNames, this.originalTagNames);
      if (tagsChanged) {
        configData.tagNames = tagNames;
      }
      if (this.shouldSubmitTtsLanguage()) {
        configData.ttsLanguage = this.selectedLanguage;
      }
      if (this.ttsVoiceTouched && this.form.ttsVoiceId !== null && this.form.ttsVoiceId !== undefined) {
        configData.ttsVoiceId = this.form.ttsVoiceId;
      }
      const submittedTtsLanguageTouched = this.ttsLanguageTouched;
      const submittedTtsVoiceTouched = this.ttsVoiceTouched;
      const submittedTtsLanguage = configData.ttsLanguage;
      const submittedTtsVoiceId = configData.ttsVoiceId;
      const submittedVoiceFetchSeq = this.voiceFetchSeq;

      // Pass only if user has set TTS parameters (not null/undefined)
      if (this.form.ttsVolume !== null && this.form.ttsVolume !== undefined) {
        configData.ttsVolume = this.form.ttsVolume;
      }
      if (this.form.ttsRate !== null && this.form.ttsRate !== undefined) {
        configData.ttsRate = this.form.ttsRate;
      }
      if (this.form.ttsPitch !== null && this.form.ttsPitch !== undefined) {
        configData.ttsPitch = this.form.ttsPitch;
      }
      const agentId = this.$route.query.agentId;
      Api.agent.updateAgentConfig(agentId, configData, ({ data }) => {
        if (data.code === 0) {
          const afterSave = () => {
            if (tagsChanged) {
              this.originalTagNames = [...tagNames];
            }
            if (submittedVoiceFetchSeq === this.voiceFetchSeq
              && submittedTtsLanguageTouched
              && this.selectedLanguage === submittedTtsLanguage) {
              this.form.ttsLanguage = submittedTtsLanguage;
              this.ttsLanguageTouched = false;
            }
            if (submittedVoiceFetchSeq === this.voiceFetchSeq
              && submittedTtsVoiceTouched
              && this.form.ttsVoiceId === submittedTtsVoiceId) {
              this.ttsVoiceTouched = false;
            }
            if (submittedVoiceFetchSeq === this.voiceFetchSeq) {
              this.lastValidTtsDraft = this.captureTtsDraft();
            }
            this.$message.success({
              message: i18n.t("roleConfig.saveSuccess"),
              showClose: true,
            });
            this.fetchCurrentVersion(agentId);
          };
          afterSave();
        } else {
          this.$message.error({
            message: data.msg || i18n.t("roleConfig.saveFailed"),
            showClose: true,
          });
        }
      });
      
    },
    async reloadAgentPage(agentId, options = {}) {
      if (!agentId) {
        return false;
      }
      const requestSeq = ++this.agentReloadSeq;
      this.agentReloading = true;
      if (options.closeEditors) {
        this.showSnapshotDialog = false;
        this.showFunctionDialog = false;
        this.showContextProviderDialog = false;
        this.showTtsAdvancedDialog = false;
        this.inputVisible = false;
      }

      const results = await Promise.all([
        this.fetchAgentConfig(agentId, { showError: false }),
        this.getAgentTags(agentId, { showError: false }),
        this.fetchCurrentVersion(agentId, { showError: false })
      ]);
      if (requestSeq !== this.agentReloadSeq) {
        return false;
      }

      this.agentReloading = false;
      if (!this.pluginMetadataReady && this.agentConfigLoaded) {
        this.$message.error(i18n.t("roleConfig.fetchPluginsFailed"));
      } else if (!results.every(Boolean)) {
        this.$message.error(i18n.t("roleConfig.fetchConfigFailed"));
      }
      return results.every(Boolean);
    },
    handleSnapshotRestored() {
      const agentId = this.$route.query.agentId;
      if (agentId) {
        this.reloadAgentPage(agentId, { closeEditors: true });
      }
    },
    fetchCurrentVersion(agentId, options = {}) {
      const requestSeq = ++this.currentVersionFetchSeq;
      this.currentVersionLoaded = false;
      if (!agentId) {
        this.currentVersionNo = null;
        this.currentVersionLoaded = true;
        return Promise.resolve(true);
      }

      return new Promise((resolve) => {
        const handleFailure = (error) => {
          if (requestSeq !== this.currentVersionFetchSeq) {
            resolve(false);
            return;
          }
          this.currentVersionLoaded = false;
          if (options.showError !== false) {
            this.$message.error(error?.data?.msg || i18n.t("roleConfig.fetchConfigFailed"));
          }
          resolve(false);
        };
        Api.agent.getDeviceConfig(agentId, ({ data }) => {
          if (requestSeq !== this.currentVersionFetchSeq) {
            resolve(false);
            return;
          }
          if (data?.code === 0) {
            this.currentVersionNo = data.data?.currentVersionNo || null;
            this.currentVersionLoaded = true;
            resolve(true);
          } else {
            handleFailure(data);
          }
        }, handleFailure);
      });
    },
    resetConfig() {
      this.$confirm(i18n.t("roleConfig.confirmReset"), i18n.t("message.info"), {
        confirmButtonText: i18n.t("button.ok"),
        cancelButtonText: i18n.t("button.cancel"),
        type: "warning",
      })
        .then(() => {
          this.selectedLanguage = "";
          this.ttsLanguageTouched = true;
          this.ttsVoiceTouched = true;
          this.form = {
            agentCode: "",
            agentName: "",
            ttsVoiceId: "",
            ttsLanguage: "",
            chatHistoryConf: 0,
            systemPrompt: "",
            summaryMemory: "",
            langCode: "",
            language: "",
            sort: "",
            model: {
              ttsModelId: "",
              vadModelId: "",
              asrModelId: "",
              llmModelId: "",
              slmModelId: "",
              vllmModelId: "",
              memModelId: "",
              intentModelId: "",
            },
          };
          this.fetchVoiceOptions("");
          this.dynamicTags = [];
          this.currentFunctions = [];
          this.$message.success({
            message: i18n.t("roleConfig.resetSuccess"),
            showClose: true,
          });
        })
        .catch(() => {});
    },
    fetchTemplates() {
      Api.agent.getAgentTemplate(({ data }) => {
        if (data.code === 0) {
          this.templates = data.data;
        } else {
          this.$message.error(data.msg || i18n.t("roleConfig.fetchTemplatesFailed"));
        }
      });
    },
    selectTemplate(template) {
      if (this.loadingTemplate) return;
      this.loadingTemplate = true;
      try {
        this.applyTemplateData(template);
        this.$message.success({
          message: `${template.agentName}${i18n.t("roleConfig.templateApplied")}`,
          showClose: true,
        });
      } catch (error) {
        this.$message.error({
          message: i18n.t("roleConfig.applyTemplateFailed"),
          showClose: true,
        });
        console.error("Failed to apply template:", error);
      } finally {
        this.loadingTemplate = false;
      }
    },
    applyTemplateData(templateData) {
      const rollbackState = this.cloneTtsDraft(this.lastValidTtsDraft) || this.captureTtsDraft();
      const currentLanguage = this.selectedLanguage;
      this.form = {
        ...this.form,
        agentName: templateData.agentName || this.form.agentName,
        ttsVoiceId: templateData.ttsVoiceId || this.form.ttsVoiceId,
        chatHistoryConf: templateData.chatHistoryConf || this.form.chatHistoryConf,
        systemPrompt: templateData.systemPrompt || this.form.systemPrompt,
        summaryMemory: templateData.summaryMemory || this.form.summaryMemory,
        langCode: templateData.langCode || this.form.langCode,
        model: {
          ttsModelId: templateData.ttsModelId || this.form.model.ttsModelId,
          vadModelId: templateData.vadModelId || this.form.model.vadModelId,
          asrModelId: templateData.asrModelId || this.form.model.asrModelId,
          llmModelId: templateData.llmModelId || this.form.model.llmModelId,
          slmModelId: templateData.llmModelId || this.form.model.slmModelId,
          vllmModelId: templateData.vllmModelId || this.form.model.vllmModelId,
          memModelId: templateData.memModelId || this.form.model.memModelId,
          intentModelId: templateData.intentModelId || this.form.model.intentModelId,
        },
      };
      if (templateData.ttsLanguage) {
        this.selectedLanguage = templateData.ttsLanguage;
      }
      if (templateData.ttsModelId || templateData.ttsVoiceId || templateData.ttsLanguage) {
        this.fetchVoiceOptions(this.form.model.ttsModelId, {
          autoSelectVoice: true,
          preferredLanguage: templateData.ttsLanguage || (templateData.ttsVoiceId ? "" : currentLanguage),
          preferredVoiceId: templateData.ttsVoiceId || "",
          rollbackState,
          markTouched: true
        });
      }
    },
    buildCurrentFunctions(savedMappings) {
      if (!Array.isArray(savedMappings)) {
        throw new TypeError("Invalid agent function mappings");
      }
      return savedMappings.map((mapping) => {
        const pluginId = mapping.pluginId || mapping.id;
        const meta = this.pluginMetadataReady
          ? this.allFunctions.find((item) => item.id === pluginId)
          : null;
        return {
          id: pluginId,
          name: meta?.name || mapping.name || pluginId,
          params: this.normalizeFunctionParams(mapping.paramInfo ?? mapping.params, meta?.params || {}),
          fieldsMeta: meta?.fieldsMeta || []
        };
      }).filter((item) => item.id);
    },
    enrichCurrentFunctionsWithMetadata() {
      if (!this.agentFunctionsLoaded || !this.pluginMetadataReady) {
        return;
      }
      this.currentFunctions = this.currentFunctions.map((item) => {
        const meta = this.allFunctions.find((candidate) => candidate.id === item.id);
        if (!meta) {
          return {
            ...item,
            params: this.normalizeFunctionParams(item.params),
            fieldsMeta: item.fieldsMeta || []
          };
        }
        return {
          ...item,
          name: meta.name || item.name || item.id,
          params: this.normalizeFunctionParams(item.params, meta.params),
          fieldsMeta: meta.fieldsMeta || []
        };
      });
      this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
    },
    fetchAgentConfig(agentId, options = {}) {
      const requestSeq = ++this.agentConfigFetchSeq;
      this.agentConfigLoaded = false;
      this.agentFunctionsLoaded = false;
      this.voiceFetchSeq += 1;
      this.voiceOptionsLoading = false;

      return new Promise((resolve) => {
        const handleFailure = (error) => {
          if (requestSeq !== this.agentConfigFetchSeq) {
            resolve(false);
            return;
          }
          this.agentConfigLoaded = false;
          this.agentFunctionsLoaded = false;
          if (options.showError !== false) {
            this.$message.error(error?.data?.msg || i18n.t("roleConfig.fetchConfigFailed"));
          }
          resolve(false);
        };

        Api.agent.getDeviceConfig(agentId, ({ data }) => {
          if (requestSeq !== this.agentConfigFetchSeq) {
            resolve(false);
            return;
          }
          if (data?.code !== 0 || !data.data) {
            handleFailure(data);
            return;
          }

          try {
            const agentData = data.data;
            if (agentData.functions != null && !Array.isArray(agentData.functions)) {
              throw new TypeError("Invalid agent function mappings");
            }
            if (agentData.contextProviders != null && !Array.isArray(agentData.contextProviders)) {
              throw new TypeError("Invalid context providers");
            }
            if (agentData.correctWordFileIds != null && !Array.isArray(agentData.correctWordFileIds)) {
              throw new TypeError("Invalid correct-word mappings");
            }
            this.tempSummaryMemory = "";
            this.ttsLanguageTouched = false;
            this.ttsVoiceTouched = false;
            this.form = {
              ...this.form,
              ...agentData,
              model: {
                ttsModelId: agentData.ttsModelId,
                vadModelId: agentData.vadModelId,
                asrModelId: agentData.asrModelId,
                llmModelId: agentData.llmModelId,
                slmModelId: agentData.slmModelId,
                vllmModelId: agentData.vllmModelId,
                memModelId: agentData.memModelId,
                intentModelId: agentData.intentModelId,
              },
            };
            this.selectedLanguage = agentData.ttsLanguage || "";
            this.voiceOptions = [];
            this.voiceDetails = {};
            this.languageOptions = [];
            this.lastValidTtsDraft = this.captureTtsDraft();
            this.fetchVoiceOptions(agentData.ttsModelId, {
              preferredLanguage: agentData.ttsLanguage,
              preferredVoiceId: agentData.ttsVoiceId
            });

            this.ttsSettings = {
              volume: this.form.ttsVolume || 0,
              speed: this.form.ttsRate || 0,
              pitch: this.form.ttsPitch || 0
            };
            this.checkedReplacementWordIds = agentData.correctWordFileIds || [];
            this.currentContextProviders = agentData.contextProviders || [];
            this.currentFunctions = this.buildCurrentFunctions(agentData.functions || []);
            this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
            this.agentFunctionsLoaded = true;
            this.agentConfigLoaded = true;

            const metadataPromise = this.pluginMetadataReady
              ? Promise.resolve(true)
              : this.fetchAllFunctions({ showError: options.showError });
            metadataPromise.then((metadataReady) => {
              if (requestSeq === this.agentConfigFetchSeq && metadataReady) {
                this.enrichCurrentFunctionsWithMetadata();
                this.updateIntentOptionsVisibility();
              }
              resolve(true);
            }).catch(handleFailure);
          } catch (error) {
            handleFailure(error);
          }
        }, handleFailure);
      });
    },
    fetchModelOptions() {
      this.models.forEach((model) => {
        if (model.type != "LLM") {
          Api.model.getModelNames(model.type, "", ({ data }) => {
            if (data.code === 0) {
              this.$set(
                this.modelOptions,
                model.type,
                data.data.map((item) => ({
                  value: item.id,
                  label: item.modelName,
                  isHidden: false,
                }))
              );

              // If it is an intent recognition option, update visibility based on the current LLM type
              if (model.type === "Intent") {
                this.updateIntentOptionsVisibility();
              }
            } else {
              this.$message.error(data.msg || i18n.t("roleConfig.fetchModelsFailed"));
            }
          });
        } else {
          Api.model.getLlmModelCodeList("", ({ data }) => {
            if (data.code === 0) {
              let LLMdata = [];
              data.data.forEach((item) => {
                LLMdata.push({
                  value: item.id,
                  label: item.modelName,
                  isHidden: false,
                });
                this.llmModeTypeMap.set(item.id, item.type);
              });
              this.$set(this.modelOptions, model.type, LLMdata);
            } else {
              this.$message.error(data.msg || this.$t('roleConfig.fetchModelsFailed'));
            }
          });
        }
      });
    },
    fetchVoiceOptions(modelId, options = {}) {
      const requestSeq = ++this.voiceFetchSeq;
      if (!modelId) {
        this.voiceOptionsLoading = false;
        this.voiceOptions = [];
        this.voiceDetails = {};
        this.languageOptions = [];
        this.selectedLanguage = '';
        this.lastValidTtsDraft = this.captureTtsDraft();
        return;
      }
      this.voiceOptionsLoading = true;
      Api.model.getModelVoices(modelId, "", ({ data }) => {
        if (requestSeq !== this.voiceFetchSeq) {
          return;
        }
        const draft = data.code === 0
          ? this.buildTtsDraft(modelId, data.data, options)
          : null;
        if (!draft) {
          this.handleVoiceOptionsFailure(requestSeq, options.rollbackState);
          return;
        }
        this.applyTtsDraft(draft, options);
        this.voiceOptionsLoading = false;
        this.lastValidTtsDraft = this.captureTtsDraft();
      }, () => {
        this.handleVoiceOptionsFailure(requestSeq, options.rollbackState);
      });
    },
    cloneTtsDraft(draft) {
      return draft ? JSON.parse(JSON.stringify(draft)) : null;
    },
    captureTtsDraft() {
      return {
        modelId: this.form.model.ttsModelId,
        language: this.selectedLanguage,
        storedLanguage: this.form.ttsLanguage,
        voiceId: this.form.ttsVoiceId,
        languageTouched: this.ttsLanguageTouched,
        voiceTouched: this.ttsVoiceTouched,
        voiceOptions: this.cloneTtsDraft(this.voiceOptions) || [],
        voiceDetails: this.cloneTtsDraft(this.voiceDetails) || {},
        languageOptions: this.cloneTtsDraft(this.languageOptions) || []
      };
    },
    restoreTtsDraft(draft) {
      const restored = this.cloneTtsDraft(draft);
      if (!restored) {
        return false;
      }
      this.form.model.ttsModelId = restored.modelId;
      this.selectedLanguage = restored.language;
      this.form.ttsLanguage = restored.storedLanguage;
      this.form.ttsVoiceId = restored.voiceId;
      this.ttsLanguageTouched = restored.languageTouched;
      this.ttsVoiceTouched = restored.voiceTouched;
      this.voiceOptions = restored.voiceOptions;
      this.voiceDetails = restored.voiceDetails;
      this.languageOptions = restored.languageOptions;
      this.lastValidTtsDraft = restored;
      return true;
    },
    splitVoiceLanguages(voice) {
      return voice && voice.languages
        ? voice.languages.split(/[、；;,，]/).map(lang => lang.trim()).filter(Boolean)
        : [];
    },
    buildTtsDraft(modelId, voices, options = {}) {
      if (!Array.isArray(voices) || voices.length === 0) {
        return null;
      }
      const voiceDetails = voices.reduce((result, voice) => {
        if (voice && voice.id) {
          result[voice.id] = voice;
        }
        return result;
      }, {});
      const validVoices = Object.values(voiceDetails);
      if (validVoices.length === 0) {
        return null;
      }

      const allLanguages = new Set();
      validVoices.forEach((voice) => {
        this.splitVoiceLanguages(voice).forEach((language) => allLanguages.add(language));
      });
      const languageOptions = Array.from(allLanguages).map((language) => ({
        value: language,
        label: language
      }));
      const languageExists = (language) => language
        && languageOptions.some((option) => option.value === language);
      const preferredVoiceId = options.preferredVoiceId || this.form.ttsVoiceId;
      const preferredVoiceLanguage = this.splitVoiceLanguages(voiceDetails[preferredVoiceId])[0] || "";
      const languageCandidates = [
        options.preferredLanguage,
        preferredVoiceLanguage,
        this.form.ttsLanguage,
        this.selectedLanguage,
        languageOptions[0]?.value
      ];
      const preferredVoiceHasNoLanguage = Boolean(
        voiceDetails[preferredVoiceId]
        && this.splitVoiceLanguages(voiceDetails[preferredVoiceId]).length === 0
      );
      let language = options.preferredLanguage === "" && preferredVoiceHasNoLanguage
        ? ""
        : languageCandidates.find(languageExists) || "";
      const filterVoices = (targetLanguage) => validVoices.filter((voice) => {
        const languages = this.splitVoiceLanguages(voice);
        return languages.length === 0 || languages.includes(targetLanguage);
      });
      let filteredVoices = filterVoices(language);
      if (filteredVoices.length === 0) {
        const fallbackVoice = validVoices.find((voice) => this.splitVoiceLanguages(voice).length > 0);
        if (fallbackVoice) {
          language = this.splitVoiceLanguages(fallbackVoice)[0];
          filteredVoices = filterVoices(language);
        } else {
          filteredVoices = validVoices;
        }
      }
      if (filteredVoices.length === 0) {
        return null;
      }

      const preferredVoice = filteredVoices.find((voice) => voice.id === preferredVoiceId);
      const voice = preferredVoice || (options.autoSelectVoice ? filteredVoices[0] : null);
      return {
        modelId,
        language,
        voiceId: voice?.id || preferredVoiceId || "",
        voiceDetails,
        languageOptions,
        voiceOptions: filteredVoices.map((item) => ({
          value: item.id,
          label: item.name,
          voiceDemo: item.voiceDemo,
          voice_demo: item.voice_demo,
          isClone: Boolean(item.isClone),
          train_status: item.trainStatus
        }))
      };
    },
    applyTtsDraft(draft, options = {}) {
      this.form.model.ttsModelId = draft.modelId;
      this.voiceDetails = draft.voiceDetails;
      this.languageOptions = draft.languageOptions;
      this.voiceOptions = draft.voiceOptions;
      this.selectedLanguage = draft.language;
      this.form.ttsLanguage = draft.language;
      this.form.ttsVoiceId = draft.voiceId;
      if (options.markTouched) {
        this.ttsLanguageTouched = true;
        this.ttsVoiceTouched = true;
      }
      this.ttsSettings = {
        volume: this.form.ttsVolume !== null && this.form.ttsVolume !== undefined ? this.form.ttsVolume : 0,
        speed: this.form.ttsRate !== null && this.form.ttsRate !== undefined ? this.form.ttsRate : 0,
        pitch: this.form.ttsPitch !== null && this.form.ttsPitch !== undefined ? this.form.ttsPitch : 0
      };
    },
    handleVoiceOptionsFailure(requestSeq, rollbackState) {
      if (requestSeq !== this.voiceFetchSeq) {
        return;
      }
      this.voiceOptionsLoading = false;
      if (!this.restoreTtsDraft(rollbackState)) {
        this.voiceOptions = [];
        this.voiceDetails = {};
        this.languageOptions = [];
      }
      this.$message.error(i18n.t("ttsModel.fetchVoicesFailed"));
    },
    getVoiceDefaultLanguage(voiceId) {
      if (!voiceId || !this.voiceDetails || !this.voiceDetails[voiceId]?.languages) {
        return "";
      }
      const languages = this.voiceDetails[voiceId].languages
        .split(/[、；;,，]/)
        .map(lang => lang.trim())
        .filter(Boolean);
      return languages[0] || "";
    },
    
    // Filter voices by language
    filterVoicesByLanguage(options = {}) {
      if (!this.voiceDetails || Object.keys(this.voiceDetails).length === 0) {
        this.voiceOptions = [];
        return;
      }

      const allVoices = Object.values(this.voiceDetails);

      // Filter voices by selected language
      const filteredVoices = allVoices.filter(voice => {
        const languagesArray = this.splitVoiceLanguages(voice);
        if (languagesArray.length === 0) {
          // Valid voices for undeclared languages are interpreted by the provider; no frontend filtering enforced
          return true;
        }
        return languagesArray.includes(this.selectedLanguage);
      });

      this.voiceOptions = filteredVoices.map((voice) => ({
        value: voice.id,
        label: voice.name,
        voiceDemo: voice.voiceDemo,
        voice_demo: voice.voice_demo,
        isClone: Boolean(voice.isClone),
        train_status: voice.trainStatus,
      }));

      // Check if the currently selected voice supports the current language; if not, select the first one
      const currentVoiceSupportsLanguage = this.form.ttsVoiceId &&
        filteredVoices.some(voice => voice.id === this.form.ttsVoiceId);

      if (!currentVoiceSupportsLanguage && options.autoSelectVoice) {
        this.form.ttsVoiceId = filteredVoices.length > 0 ? filteredVoices[0].id : '';
        this.ttsVoiceTouched = true;
      }

      // Sync to ttsSettings (if value is null, use 0 as display default without modifying the form value)
      this.ttsSettings = {
        volume: this.form.ttsVolume !== null && this.form.ttsVolume !== undefined ? this.form.ttsVolume : 0,
        speed: this.form.ttsRate !== null && this.form.ttsRate !== undefined ? this.form.ttsRate : 0,
        pitch: this.form.ttsPitch !== null && this.form.ttsPitch !== undefined ? this.form.ttsPitch : 0
      };
    },
    handleLanguageChange() {
      this.ttsLanguageTouched = true;
      this.form.ttsLanguage = this.selectedLanguage;
      this.filterVoicesByLanguage({ autoSelectVoice: true });
      if (this.form.ttsVoiceId) {
        this.lastValidTtsDraft = this.captureTtsDraft();
      }
    },
    handleVoiceChange() {
      this.ttsVoiceTouched = true;
      if (this.selectedLanguage) {
        this.form.ttsLanguage = this.selectedLanguage;
        this.ttsLanguageTouched = true;
      }
      if (this.form.ttsVoiceId) {
        this.lastValidTtsDraft = this.captureTtsDraft();
      }
    },
    shouldSubmitTtsLanguage() {
      return this.ttsLanguageTouched;
    },

    getFunctionDisplayChar(name) {
      if (!name || name.length === 0) return "";

      for (let i = 0; i < name.length; i++) {
        const char = name[i];
        if (/[\u4e00-\u9fa5a-zA-Z0-9]/.test(char)) {
          return char;
        }
      }

      // If no valid characters are found, return the first character
      return name.charAt(0);
    },
    showFunctionIcons(type) {
      return type === "Intent" && this.form.model.intentModelId !== "Intent_nointent";
    },
    handleModelChange(type, value) {
      if (type === "Intent" && value !== "Intent_nointent") {
        this.fetchAllFunctions().then((metadataReady) => {
          if (metadataReady) {
            this.enrichCurrentFunctionsWithMetadata();
          }
        });
      }
      if (type === "Memory") {
        if (value === "Memory_nomem") {
          // Models without memory do not record chat history by default
          this.form.chatHistoryConf = 0;
        } else {
          // Models with memory record text and voice by default
          this.form.chatHistoryConf = 2;
        }
        if (value === "Memory_nomem" || value === "Memory_mem_report_only") {
          this.tempSummaryMemory = this.form.summaryMemory;
          this.form.summaryMemory = "";
        } else if (this.tempSummaryMemory !== "" && this.form.summaryMemory === "") {
          this.form.summaryMemory = this.tempSummaryMemory;
          this.tempSummaryMemory = "";
        }
      }
      if (type === "LLM") {
        // Update the visibility of intent recognition options when the LLM type changes
        this.updateIntentOptionsVisibility();
      }
      if (type === "TTS") {
        const rollbackState = this.cloneTtsDraft(this.lastValidTtsDraft);
        this.fetchVoiceOptions(value, {
          autoSelectVoice: true,
          preferredLanguage: rollbackState?.language || this.selectedLanguage,
          rollbackState,
          markTouched: true
        });
      }
    },
    parsePluginFields(fields) {
      if (Array.isArray(fields)) {
        return fields;
      }
      if (typeof fields !== "string" || !fields.trim()) {
        return [];
      }
      try {
        const parsed = JSON.parse(fields);
        return Array.isArray(parsed) ? parsed : [];
      } catch (error) {
        return [];
      }
    },
    fetchAllFunctions(options = {}) {
      if (this.pluginMetadataReady) {
        return Promise.resolve(true);
      }
      if (this.pluginMetadataLoading) {
        return this.pluginMetadataLoading;
      }

      this.pluginMetadataLoading = new Promise((resolve) => {
        let settled = false;
        const finish = (ready, error) => {
          if (settled) {
            return;
          }
          settled = true;
          this.pluginMetadataReady = ready;
          if (!ready && options.showError !== false) {
            this.$message.error(error?.data?.msg || error?.msg || i18n.t("roleConfig.fetchPluginsFailed"));
          }
          resolve(ready);
        };

        Api.model.getPluginFunctionList(null, ({ data }) => {
          if (data?.code !== 0) {
            finish(false, data);
            return;
          }
          try {
            this.allFunctions = (data.data || []).map((item) => {
              const fieldsMeta = this.parsePluginFields(item.fields);
              const params = fieldsMeta.reduce((result, field) => {
                if (field?.key) {
                  result[field.key] = field.default;
                }
                return result;
              }, {});
              return { ...item, fieldsMeta, params };
            });
            finish(true);
          } catch (error) {
            finish(false, error);
          }
        }, (error) => finish(false, error));
      }).finally(() => {
        this.pluginMetadataLoading = null;
      });

      return this.pluginMetadataLoading;
    },
    openFunctionDialog() {
      if (this.agentReloading || !this.agentFunctionsLoaded) {
        return;
      }
      if (this.pluginMetadataReady) {
        this.enrichCurrentFunctionsWithMetadata();
        this.showFunctionDialog = true;
        return;
      }
      this.fetchAllFunctions().then((metadataReady) => {
        if (metadataReady) {
          this.enrichCurrentFunctionsWithMetadata();
          this.showFunctionDialog = true;
        }
      });
    },
    openContextProviderDialog() {
      this.showContextProviderDialog = true;
    },
    openTtsAdvancedSettings() {
      this.showTtsAdvancedDialog = true;
    },
    handleTtsSettingsSave(settings) {
      const { replacementWordIds, changedTtsFields = [], ...ttsSettings } = settings;
      this.checkedReplacementWordIds = replacementWordIds;
      // Save TTS settings
      this.ttsSettings = ttsSettings;
      const changedFields = new Set(changedTtsFields);
      if (changedFields.has("volume")) {
        this.form.ttsVolume = ttsSettings.volume;
      }
      if (changedFields.has("speed")) {
        this.form.ttsRate = ttsSettings.speed;
      }
      if (changedFields.has("pitch")) {
        this.form.ttsPitch = ttsSettings.pitch;
      }
    },
    handleUpdateContext(providers) {
      this.currentContextProviders = providers;
    },
    handleUpdateFunctions(selected) {
      this.currentFunctions = selected;
    },
    handleDialogClosed(saved) {
      if (!saved) {
        this.currentFunctions = JSON.parse(JSON.stringify(this.originalFunctions));
      } else {
        this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
      }
      this.showFunctionDialog = false;
    },
    updateIntentOptionsVisibility() {
      // Update visibility of intent recognition options based on the currently selected LLM type
      const currentLlmId = this.form.model.llmModelId;
      if (!currentLlmId || !this.modelOptions["Intent"]) return;

      const llmType = this.llmModeTypeMap.get(currentLlmId);
      if (!llmType) return;

      this.modelOptions["Intent"].forEach((item) => {
        if (item.value === "Intent_function_call") {
          // If llmType is openai or ollama, allow selecting function_call
          // Otherwise hide function_call option
          if (llmType === "openai" || llmType === "ollama") {
            item.isHidden = false;
          } else {
            item.isHidden = true;
          }
        } else {
          // Other intent recognition options always visible
          item.isHidden = false;
        }
      });

      // If the current intent recognition is function_call but the LLM type does not support it, set it to the first optional item
      if (
        this.form.model.intentModelId === "Intent_function_call" &&
        llmType !== "openai" &&
        llmType !== "ollama"
      ) {
        // Find the first visible option
        const firstVisibleOption = this.modelOptions["Intent"].find(
          (item) => !item.isHidden
        );
        if (firstVisibleOption) {
          this.form.model.intentModelId = firstVisibleOption.value;
        } else {
          // If no visible options exist, set to Intent_nointent
          this.form.model.intentModelId = "Intent_nointent";
        }
      }
    },
    // Check if audio preview exists
    hasAudioPreview(item) {
      // Check if audio is cloned
      // Use the isClone field actually returned by the backend
      const isCloneAudio = Boolean(item.isClone);
      
      // Check for valid audio URL, using only fields actually returned by the backend
      const hasValidAudioUrl = !!((item.voice_demo || item.voiceDemo)?.trim());
      
      // Cloned audio always shows play button; regular audio shows it only with a valid URL
      return isCloneAudio || hasValidAudioUrl;
    },

    // Toggle audio play/pause
    toggleAudioPlayback(voiceId) {
      // If the clicked audio is currently playing, toggle pause/play state
      if (this.playingVoice && this.currentPlayingVoiceId === voiceId) {
        if (this.isPaused) {
          // Resume playback from paused state
          this.currentAudio.play().catch((error) => {
            console.error("Failed to resume playback:", error);
            this.$message.warning(this.$t('roleConfig.cannotResumeAudio'));
          });
          this.isPaused = false;
        } else {
          // Pause playback
          this.currentAudio.pause();
          this.isPaused = true;
        }
        return;
      }

      // Otherwise start playing new audio
      this.playVoicePreview(voiceId);
    },

    // Play voice preview
    playVoicePreview(voiceId = null) {
      // If voiceId is provided, use it; otherwise, use the currently selected one
      const targetVoiceId = voiceId || this.form.ttsVoiceId;

      if (!targetVoiceId) {
        this.$message.warning(this.$t('roleConfig.selectVoiceFirst'));
        return;
      }

      // Stop currently playing audio
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio = null;
      }

      // Reset playback state
      this.isPaused = false;
      this.currentPlayingVoiceId = targetVoiceId;

      try {
        // Get audio URL from saved voice details
        const voiceDetail = this.voiceDetails[targetVoiceId];

        // Add debug info
        console.log("Selected voice ID:", targetVoiceId);
        console.log("Voice details:", voiceDetail);

        // Try multiple possible audio property names
        let audioUrl = null;
        let isCloneAudio = false;

        if (voiceDetail) {
          // Use the isClone field returned by the backend to determine if audio is cloned
          isCloneAudio = Boolean(voiceDetail.isClone);
          console.log(
            "Cloned audio judgment result:",
            isCloneAudio,
            "Training status:",
            voiceDetail.train_status
          );

          // Get audio URL
          if (isCloneAudio && voiceDetail.id) {
            // For cloned audio, use the correct interface provided by the backend
            // Note: Fetching the audio URL requires two steps
            // 1. First, obtain the audio download ID
            // 2. Then use this ID to construct the playback URL
            // Due to async operations, request getAudioId first
            console.log("Cloned audio detected, preparing to fetch audio URL:", voiceDetail.id);

            // Create a Promise to handle async audio URL retrieval
            const getCloneAudioUrl = () => {
              return new Promise((resolve) => {
                // First call the getAudioId API to obtain a temporary UUID.
                RequestService.sendRequest()
                  .url(`${getServiceUrl()}/voiceClone/audio/${voiceDetail.id}`)
                  .method("POST")
                  .success((res) => {
                    if (res.data.code === 0 && res.data.data) {
                      // Process the returned data format by wrapping res.data in an additional .data layer
                      const audioId = res.data.data;
                      console.log("Retrieved audio ID:", audioId);
                      // Build playback URL using returned UUID
                      const playUrl = `${getServiceUrl()}/voiceClone/play/${audioId}`;
                      console.log("Build cloned audio playback URL:", playUrl);
                      resolve(playUrl);
                    } else {
                      console.error("Failed to get audio ID:", res.msg);
                      resolve(null);
                    }
                  })
                  .networkFail((err) => {
                    console.error("Failed to request audio ID API:", err);
                    resolve(null);
                  })
                  .send();
              });
            };

            // Set Playback State
            this.playingVoice = true;
            // Create Audio instance
            this.currentAudio = new Audio();
            // Set Volume
            this.currentAudio.volume = 1.0;

            // Set timeout to prevent excessive loading time
            const timeoutId = setTimeout(() => {
              if (this.currentAudio && this.playingVoice) {
                this.$message.warning(this.$t('roleConfig.audioLoadTimeout'));
                this.playingVoice = false;
              }
            }, 10000); // 10-second timeout

            // Listen for playback error
            this.currentAudio.onerror = () => {
              clearTimeout(timeoutId);
              console.error("Audio playback clone error");
              this.$message.warning(this.$t('roleConfig.cloneAudioPlayFailed'));
              this.playingVoice = false;
            };

            // Monitor playback start, clear timeout
            this.currentAudio.onplay = () => {
              clearTimeout(timeoutId);
            };

            // Listen for playback end
            this.currentAudio.onended = () => {
              this.playingVoice = false;
            };

            // Handle async URL fetch and playback
            getCloneAudioUrl().then((url) => {
              if (url) {
                // Set audio URL and play
                this.currentAudio.src = url;
                this.currentAudio.play().catch((error) => {
                  clearTimeout(timeoutId);
                  console.error("Failed to play cloned audio:", error);
                  this.$message.warning(this.$t('roleConfig.cannotPlayCloneAudio'));
                  this.playingVoice = false;
                });
              } else {
                clearTimeout(timeoutId);
                this.$message.warning(this.$t('roleConfig.getCloneAudioFailed'));
                this.playingVoice = false;
              }
            });

            // Return to avoid executing subsequent standard audio playback logic
            return;
          } else {
            // For standard audio, use only fields actually returned by the backend
            audioUrl =
              voiceDetail.voiceDemo ||
              voiceDetail.voice_demo;
          }

          // If not found, check for fields in URL format
          if (!audioUrl) {
            for (const key in voiceDetail) {
              const value = voiceDetail[key];
              if (
                typeof value === "string" &&
                (value.startsWith("http://") ||
                  value.startsWith("https://") ||
                  value.endsWith(".mp3") ||
                  value.endsWith(".wav") ||
                  value.endsWith(".ogg"))
              ) {
                audioUrl = value;
                console.log(`Possible audio URL found in field '${key}':`, audioUrl);
                break;
              }
            }
          }
        }

        if (!audioUrl) {
          // Display friendly prompt if no audio URL is present
          this.$message.warning(this.$t('roleConfig.noPreviewAudio'));
          return;
        }

        // Handling logic for non-cloned audio
        if (!isCloneAudio) {
          // Set Playback State
          this.playingVoice = true;

          // Create and play audio
          this.currentAudio = new Audio();
          this.currentAudio.src = audioUrl;

          // Set Volume
          this.currentAudio.volume = 1.0;

          // Set timeout to prevent excessive loading time
          const timeoutId = setTimeout(() => {
            if (this.currentAudio && this.playingVoice) {
              this.$message.warning(this.$t('roleConfig.audioLoadTimeout'));
              this.playingVoice = false;
            }
          }, 10000); // 10-second timeout

          // Listen for playback error
          this.currentAudio.onerror = () => {
            clearTimeout(timeoutId);
            console.error("Audio playback error");
            this.$message.warning(this.$t('roleConfig.audioPlayFailed'));
            this.playingVoice = false;
          };

          // Monitor playback start, clear timeout
          this.currentAudio.onplay = () => {
            clearTimeout(timeoutId);
          };

          // Listen for playback end
          this.currentAudio.onended = () => {
            this.playingVoice = false;
          };

          // Start audio playback
          this.currentAudio.play().catch((error) => {
            clearTimeout(timeoutId);
            console.error("Playback failed:", error);
            this.$message.warning(this.$t('roleConfig.cannotPlayAudio'));
            this.playingVoice = false;
          });
        }
      } catch (error) {
        console.error("Error during audio playback:", error);
        this.$message.error(this.$t('roleConfig.audioPlayError'));
        this.playingVoice = false;
      }
    },
    updateChatHistoryConf() {
      if (this.form.model.memModelId === "Memory_nomem") {
        this.form.chatHistoryConf = 0;
      }
    },
    // Load feature status
    async loadFeatureStatus() {
      try {
        // Ensure featureManager is fully initialized
        await featureManager.waitForInitialization();
        const config = featureManager.getConfig();
        this.featureStatus.voiceprintRecognition = config.voiceprintRecognition || false;
        this.featureStatus.vad = config.vad || false;
        this.featureStatus.asr = config.asr || false;
      } catch (error) {
        console.error("Failed to load feature status:", error);
      }
    },
    handleClose(id) {
      this.dynamicTags = this.dynamicTags.filter((item) => item.id !== id);
    },

    showInput() {
      this.inputVisible = true;
      this.$nextTick(_ => {
        this.$refs.saveTagInput.$refs.input.focus();
      });
    },

    handleInputConfirm() {
      let inputValue = this.inputValue;
      if (inputValue) {
        const tag = { id: `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, tagName: inputValue };
        this.dynamicTags.push(tag);
      }
      this.inputVisible = false;
      this.inputValue = '';
    },
    getAgentTags(agentId, options = {}) {
      const requestSeq = ++this.agentTagsFetchSeq;
      this.agentTagsLoaded = false;
      if (!agentId) {
        this.dynamicTags = [];
        this.originalTagNames = [];
        this.agentTagsLoaded = true;
        return Promise.resolve(true);
      }

      return new Promise((resolve) => {
        const handleFailure = (error) => {
          if (requestSeq !== this.agentTagsFetchSeq) {
            resolve(false);
            return;
          }
          this.agentTagsLoaded = false;
          if (options.showError !== false) {
            this.$message.error(error?.data?.msg || i18n.t("roleConfig.fetchConfigFailed"));
          }
          resolve(false);
        };
        Api.agent.getAgentTags(agentId, ({ data }) => {
          if (requestSeq !== this.agentTagsFetchSeq) {
            resolve(false);
            return;
          }
          if (data?.code === 0) {
            try {
              this.dynamicTags = Array.isArray(data.data) ? data.data : [];
              this.originalTagNames = this.dynamicTags.map(tag => tag.tagName);
              this.agentTagsLoaded = true;
              resolve(true);
            } catch (error) {
              handleFailure(error);
            }
          } else {
            handleFailure(data);
          }
        }, handleFailure);
      });
    },
    isSameStringList(left, right) {
      if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) {
        return false;
      }
      return left.every((value, index) => value === right[index]);
    },
    handleSaveAgentTags(agentId, tagNames = this.dynamicTags.map(tag => tag.tagName)) {
      return new Promise((resolve, reject) => {
        Api.agent.saveAgentTags(agentId, { tagNames }, ({ data }) => {
          if (data.code === 0) {
            this.originalTagNames = [...tagNames];
            resolve();
          } else {
            reject(data.msg);
          }
        });
      });
    }
  },
  beforeDestroy() {
    this.agentReloadSeq += 1;
    this.agentConfigFetchSeq += 1;
    this.agentTagsFetchSeq += 1;
    this.currentVersionFetchSeq += 1;
    this.voiceFetchSeq += 1;
  },
  async mounted() {
    this.lastValidTtsDraft = this.captureTtsDraft();
    const agentId = this.$route.query.agentId;
    if (agentId) {
      this.reloadAgentPage(agentId);
    }
    this.fetchModelOptions();
    this.fetchTemplates();
    // Load feature states to ensure featureManager is initialized
    await this.loadFeatureStatus();
  },
};
</script>

<style lang="scss" scoped>
::v-deep .el-radio-group {
  .is-active {
    .el-radio-button__inner {
      &:hover {
        color: #fff !important;
      }
    }
  }
}
.welcome {
  min-width: 900px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background: #eff4ff;
  background-size: cover;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
  color: #2c3e50;
}

.main-wrapper {
  height: calc(100vh - 63px - 35px - 60px);
  margin: 0 22px;
  border-radius: 15px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  overflow: auto;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.config-card {
  background: white;
  border: none;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow-y: auto;
}

.config-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 0 0 5px 0;
  font-weight: 700;
  font-size: 19px;
  color: #3d4566;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 13px;
  flex-shrink: 0;
}

.header-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  padding-bottom: 4px;
  &::-webkit-scrollbar {
      height: 6px;
      background: #e6ebff;
    }
    &::-webkit-scrollbar-thumb {
      background: #5778ff;
      border-radius: 8px;
    }
}

.header-tags .el-tag {
  flex-shrink: 0;
}

.current-version-tag {
  flex-shrink: 0;
  padding: 3px 9px;
  border: 1px solid #dfe7ff;
  border-radius: 999px;
  background: #f4f7ff;
  color: #5778ff;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
}

.more-tag {
  cursor: pointer;
  flex-shrink: 0;
}

.all-tags-popover {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px;
}

.header-icon {
  width: 37px;
  height: 37px;
  background: #5778ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-icon img {
  width: 19px;
  height: 19px;
}

.divider {
  height: 1px;
  background: #e8f0ff;
}

.form-content {
  padding: 2vh 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-column {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-input {
  width: 100%;
}

.form-select {
  flex: 1;
  width: 100%;
  height: 36px;
}

.play-button {
  color: #409eff;
  transition: color 0.3s;
}

.play-button:hover {
  color: #66b1ff;
}

.play-button.is-loading {
  color: #909399;
}

.form-textarea {
  width: 100%;
}

.voice-select-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.template-container {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.template-item {
  height: 4vh;
  min-width: 60px;
  padding: 0 12px;
  border-radius: 8px;
  background: #e6ebff;
  line-height: 4vh;
  font-weight: 400;
  font-size: 11px;
  text-align: center;
  color: #5778ff;
  cursor: pointer;
  transition: background-color 0.3s ease;
  white-space: nowrap;
}

.template-item:hover {
  background-color: #d0d8ff;
}

.model-select-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
}

.model-row {
  display: flex;
  gap: 20px;
  margin-bottom: 6px;
}

.model-row .model-item {
  flex: 1;
  margin-bottom: 0;
}

.model-row .language-select-item {
  flex: 0 0 35%;
  max-width: 35%;
}

.model-row .language-select-item .language-select {
  width: 100%;
}

.model-row .el-form-item__label {
  font-size: 12px !important;
  color: #3d4566 !important;
  font-weight: 400;
  line-height: 22px;
  padding-bottom: 2px;
}

.function-icons {
  display: flex;
  align-items: center;
  margin-left: auto;
  padding-left: 10px;
}

.icon-dot {
  width: 25px;
  height: 25px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #5778ff;
  font-weight: bold;
  font-size: 12px;
  margin-right: 8px;
  position: relative;
  background-color: #e6ebff;
}

::v-deep .el-form-item__label {
  font-size: 12px !important;
  color: #3d4566 !important;
  font-weight: 400;
  line-height: 22px;
  padding-bottom: 2px;
}

::v-deep .el-textarea .el-input__count {
  color: #909399;
  background: none;
  position: absolute;
  font-size: 12px;
  right: 3%;
}

.custom-close-btn {
  position: absolute;
  top: 25%;
  right: 0;
  transform: translateY(-50%);
  width: 35px;
  height: 35px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
}

.custom-close-btn:hover {
  color: #409eff;
  border-color: #409eff;
}

.edit-function-btn {
  background: #e6ebff;
  color: #5778ff;
  border: 1px solid #adbdff;
  border-radius: 18px;
  padding: 10px 20px;
  transition: all 0.3s;
}

.edit-function-btn.active-btn {
  background: #5778ff;
  color: white;
}

.chat-history-options {
  display: flex;
  gap: 10px;
  min-width: 250px;
  justify-content: flex-end;
}

.chat-history-options ::v-deep .el-radio-button {
  border-color: #5778ff;
}

.chat-history-options ::v-deep .el-radio-button .el-radio-button__inner {
  color: #5778ff;
  border-color: #5778ff;
  background-color: transparent;
}

.chat-history-options ::v-deep .el-radio-button.is-active .el-radio-button__inner {
  background-color: #5778ff;
  border-color: #5778ff;
  color: white;
}

.chat-history-options ::v-deep .el-radio-button .el-radio-button__inner:hover {
  color: #5778ff;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.header-actions .hint-text {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #979db1;
  font-size: 12px;
  margin-right: 8px;
}

.header-actions .hint-text img {
  width: 16px;
  height: 16px;
}

.header-actions .save-btn {
  background: #5778ff;
  color: white;
  border: none;
  border-radius: 18px;
  padding: 8px 16px;
  height: 32px;
  font-size: 14px;
}

.header-actions .history-btn {
  background: #ffffff;
  color: #4d5b7c;
  border: 1px solid #d8dce8;
  border-radius: 18px;
  padding: 8px 16px;
  height: 32px;
  font-size: 14px;
}

.header-actions .reset-btn {
  background: #e6ebff;
  color: #5778ff;
  border: 1px solid #adbdff;
  border-radius: 18px;
  padding: 8px 16px;
  height: 32px;
}

.header-actions .custom-close-btn {
  position: static;
  transform: none;
  width: 32px;
  height: 32px;
  margin-left: 8px;
}

.context-provider-item ::v-deep .el-form-item__label {
  line-height: 42px !important;
}

.doc-link {
  color: #5778ff;
  text-decoration: none;
  margin-left: 4px;

  &:hover {
    text-decoration: underline;
  }
}

.slider-wrapper {
  width: 100%;
  padding-right: 12px;
}

.slider-hint {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;
}

.tts-slider {
  width: 100%;
}

.tts-slider ::v-deep .el-slider__input {
  width: 80px;
}

.tts-slider ::v-deep .el-input__inner {
  text-align: center;
  padding: 0 8px;
}
.custom-tag {
  background: #e6ebff;
  color: #5778ff;
  border-radius: 8px;
  font-size: 12px;
  font-weight: normal;
  border: none;
}
.custom-tag-btn {
  background: #e6ebff;
  color: #5778ff;
  border-radius: 8px;
  font-weight: normal;
  border: 1px solid #e6ebff;
  &:hover {
    background-color: #d0d8ff;
  }
}
.input-new-tag {
  width: 90px;
  &::v-deep(.el-input__inner) {
    width: 90px !important;
  }
}

</style>

<style>
.custom-tooltip {
  max-width: 400px !important;
  word-break: break-word;
}
</style>
