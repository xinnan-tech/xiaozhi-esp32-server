<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">{{ $t('roleConfig.title') }}</h2>
    </div>

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="config-card" shadow="never">
            <div class="config-header">
              <div class="header-icon">
                <img loading="lazy" src="@/assets/home/setting-user.png" alt="">
              </div>
              <span class="header-title">{{ form.agentName }}</span>
              <div class="header-actions">
                <div class="hint-text">
                  <img loading="lazy" src="@/assets/home/info.png" alt="">
                  <span>{{ $t('roleConfig.restartNotice') }}</span>
                </div>
                <el-button type="primary" class="save-btn" @click="saveConfig">
                  {{ $t('roleConfig.saveConfig') }}
                </el-button>
                <el-button class="reset-btn" @click="resetConfig">{{ $t('roleConfig.reset') }}</el-button>
                <button class="custom-close-btn" @click="goToHome">
                  ×
                </button>
              </div>
            </div>
            <div class="divider"></div>

            <el-form ref="form" :model="form" label-width="72px">
              <div class="form-content">
                <div class="form-grid">
                  <div class="form-column">
                    <el-form-item :label="$t('roleConfig.agentName') + '：'">
                      <el-input v-model="form.agentName" class="form-input" maxlength="10" />
                    </el-form-item>
                    <el-form-item :label="$t('roleConfig.roleTemplate') + '：'">
                      <div class="template-container">
                        <div v-for="(template, index) in templates" :key="`template-${index}`" class="template-item"
                          :class="{ 'template-loading': loadingTemplate }" @click="selectTemplate(template)">
                          {{ template.agentName }}
                        </div>
                      </div>
                    </el-form-item>
                    <el-form-item :label="$t('roleConfig.roleIntroduction') + '：'">
                      <el-input type="textarea" rows="9" resize="none"
                        :placeholder="$t('roleConfig.pleaseEnterContent')" v-model="form.systemPrompt" maxlength="2000"
                        show-word-limit class="form-textarea" />
                    </el-form-item>

                    <el-form-item :label="$t('roleConfig.memoryHis') + '：'">
                      <el-input type="textarea" rows="6" resize="none" v-model="form.summaryMemory" maxlength="2000"
                        show-word-limit class="form-textarea"
                        :disabled="form.model.memModelId !== 'Memory_mem_local_short'" />
                    </el-form-item>
                    <el-form-item :label="$t('roleConfig.languageCode') + '：'" style="display: none;">
                      <el-input v-model="form.langCode" :placeholder="$t('roleConfig.pleaseEnterLangCode')"
                        maxlength="10" show-word-limit class="form-input" />
                    </el-form-item>
                    <el-form-item :label="$t('roleConfig.interactionLanguage') + '：'" style="display: none;">
                      <el-input v-model="form.language" :placeholder="$t('roleConfig.pleaseEnterLangName')"
                        maxlength="10" show-word-limit class="form-input" />
                    </el-form-item>
                  </div>
                  <div class="form-column">
                    <div class="model-row">
                      <el-form-item :label="$t('roleConfig.vad')" class="model-item">
                        <div class="model-select-wrapper">
                          <el-select v-model="form.model.vadModelId" filterable
                            :placeholder="$t('roleConfig.pleaseSelect')" class="form-select"
                            @change="handleModelChange('VAD', $event)">
                            <el-option v-for="(item, optionIndex) in modelOptions['VAD']"
                              :key="`option-vad-${optionIndex}`" :label="item.label" :value="item.value" />
                          </el-select>
                        </div>
                      </el-form-item>
                      <el-form-item :label="$t('roleConfig.asr')" class="model-item">
                        <div class="model-select-wrapper">
                          <el-select v-model="form.model.asrModelId" filterable
                            :placeholder="$t('roleConfig.pleaseSelect')" class="form-select"
                            @change="handleModelChange('ASR', $event)">
                            <el-option v-for="(item, optionIndex) in modelOptions['ASR']"
                              :key="`option-asr-${optionIndex}`" :label="item.label" :value="item.value" />
                          </el-select>
                        </div>
                      </el-form-item>
                    </div>
                    <el-form-item v-for="(model, index) in models.slice(2)" :key="`model-${index}`"
                      :label="$t('roleConfig.' + model.type.toLowerCase())" class="model-item">
                      <div class="model-select-wrapper">
                        <el-select v-model="form.model[model.key]" filterable
                          :placeholder="$t('roleConfig.pleaseSelect')" class="form-select"
                          @change="handleModelChange(model.type, $event)">
                          <el-option v-for="(item, optionIndex) in modelOptions[model.type]" v-if="!item.isHidden"
                            :key="`option-${index}-${optionIndex}`" :label="item.label" :value="item.value" />
                        </el-select>
                        <div v-if="showFunctionIcons(model.type)" class="function-icons">
                          <el-tooltip v-for="func in currentFunctions" :key="func.name" effect="dark" placement="top"
                            popper-class="custom-tooltip">
                            <div slot="content">
                              <div><strong>功能名称:</strong> {{ func.name }}</div>
                            </div>
                            <div class="icon-dot">
                              {{ getFunctionDisplayChar(func.name) }}
                            </div>
                          </el-tooltip>
                          <el-button class="edit-function-btn" @click="openFunctionDialog"
                            :class="{ 'active-btn': showFunctionDialog }">
                            {{ $t('roleConfig.editFunctions') }}
                          </el-button>
                        </div>
                        <div v-if="model.type === 'Memory' && form.model.memModelId !== 'Memory_nomem'"
                          class="chat-history-options">
                          <el-radio-group v-model="form.chatHistoryConf" @change="updateChatHistoryConf">
                            <el-radio-button :label="1">{{ $t('roleConfig.reportText') }}</el-radio-button>
                            <el-radio-button :label="2">{{ $t('roleConfig.reportTextVoice') }}</el-radio-button>
                          </el-radio-group>
                        </div>
                      </div>
                    </el-form-item>
                    <el-form-item :label="$t('roleConfig.voiceType')">
                      <el-select v-model="form.ttsVoiceId" :placeholder="$t('roleConfig.pleaseSelect')"
                        class="form-select">
                        <el-option v-for="(item, index) in voiceOptions" :key="`voice-${index}`" :label="item.label"
                          :value="item.value" />
                      </el-select>
                    </el-form-item>
                  </div>
                </div>
              </div>
            </el-form>
          </el-card>
        </div>
      </div>
    </div>
    <function-dialog v-model="showFunctionDialog" :functions="currentFunctions" :all-functions="allFunctions"
      :agent-id="$route.query.agentId" @update-functions="handleUpdateFunctions" @dialog-closed="handleDialogClosed" />
  </div>
</template>

<script>
import Api from '@/apis/api';
import FunctionDialog from "@/components/FunctionDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import i18n from '@/i18n';

export default {
  name: 'RoleConfigPage',
  components: { HeaderBar, FunctionDialog },
  data() {
    return {
      form: {
        agentCode: "",
        agentName: "",
        ttsVoiceId: "",
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
          vllmModelId: "",
          memModelId: "",
          intentModelId: "",
        }
      },
      models: [
        { label: this.$t('roleConfig.vad'), key: 'vadModelId', type: 'VAD' },
        { label: this.$t('roleConfig.asr'), key: 'asrModelId', type: 'ASR' },
        { label: this.$t('roleConfig.llm'), key: 'llmModelId', type: 'LLM' },
        { label: this.$t('roleConfig.vllm'), key: 'vllmModelId', type: 'VLLM' },
        { label: this.$t('roleConfig.intent'), key: 'intentModelId', type: 'Intent' },
        { label: this.$t('roleConfig.memory'), key: 'memModelId', type: 'Memory' },
        { label: this.$t('roleConfig.tts'), key: 'ttsModelId', type: 'TTS' }
      ],
      llmModeTypeMap: new Map(),
      modelOptions: {},
      templates: [],
      loadingTemplate: false,
      voiceOptions: [],
      showFunctionDialog: false,
      currentFunctions: [],
      allFunctions: [],
      originalFunctions: [],
    }
  },
  methods: {
    goToHome() {
      this.$router.push('/home');
    },
    saveConfig() {
      const configData = {
        agentCode: this.form.agentCode,
        agentName: this.form.agentName,
        asrModelId: this.form.model.asrModelId,
        vadModelId: this.form.model.vadModelId,
        llmModelId: this.form.model.llmModelId,
        vllmModelId: this.form.model.vllmModelId,
        ttsModelId: this.form.model.ttsModelId,
        ttsVoiceId: this.form.ttsVoiceId,
        chatHistoryConf: this.form.chatHistoryConf,
        memModelId: this.form.model.memModelId,
        intentModelId: this.form.model.intentModelId,
        systemPrompt: this.form.systemPrompt,
        summaryMemory: this.form.summaryMemory,
        langCode: this.form.langCode,
        language: this.form.language,
        sort: this.form.sort,
        functions: this.currentFunctions.map(item => {
          return ({
            pluginId: item.id,
            paramInfo: item.params
          })
        })
      };
      Api.agent.updateAgentConfig(this.$route.query.agentId, configData, ({ data }) => {
        if (data.code === 0) {
          this.$message.success({
            message: i18n.t('roleConfig.saveSuccess'),
            showClose: true
          });
        } else {
          this.$message.error({
            message: data.msg || i18n.t('roleConfig.saveFailed'),
            showClose: true
          });
        }
      });
    },
    resetConfig() {
      this.$confirm(i18n.t('roleConfig.confirmReset'), i18n.t('message.info'), {
        confirmButtonText: i18n.t('button.ok'),
        cancelButtonText: i18n.t('button.cancel'),
        type: 'warning'
      }).then(() => {
        this.form = {
          agentCode: "",
          agentName: "",
          ttsVoiceId: "",
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
            vllmModelId: "",
            memModelId: "",
            intentModelId: "",
          }
        }
        this.currentFunctions = [];
        this.$message.success({
          message: i18n.t('roleConfig.resetSuccess'),
          showClose: true
        })
      }).catch(() => {
      });
    },
    fetchTemplates() {
      Api.agent.getAgentTemplate(({ data }) => {
        if (data.code === 0) {
          this.templates = data.data;
        } else {
          this.$message.error(data.msg || i18n.t('roleConfig.fetchTemplatesFailed'));
        }
      });
    },
    selectTemplate(template) {
      if (this.loadingTemplate) return;
      this.loadingTemplate = true;
      try {
        this.applyTemplateData(template);
        this.$message.success({
          message: `${template.agentName}${i18n.t('roleConfig.templateApplied')}`,
          showClose: true
        });
      } catch (error) {
        this.$message.error({
          message: i18n.t('roleConfig.applyTemplateFailed'),
          showClose: true
        });
        console.error('应用模板失败:', error);
      } finally {
        this.loadingTemplate = false;
      }
    },
    applyTemplateData(templateData) {
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
          vllmModelId: templateData.vllmModelId || this.form.model.vllmModelId,
          memModelId: templateData.memModelId || this.form.model.memModelId,
          intentModelId: templateData.intentModelId || this.form.model.intentModelId
        }
      };
    },
    fetchAgentConfig(agentId) {
      Api.agent.getDeviceConfig(agentId, ({ data }) => {
        if (data.code === 0) {
          this.form = {
            ...this.form,
            ...data.data,
            model: {
              ttsModelId: data.data.ttsModelId,
              vadModelId: data.data.vadModelId,
              asrModelId: data.data.asrModelId,
              llmModelId: data.data.llmModelId,
              vllmModelId: data.data.vllmModelId,
              memModelId: data.data.memModelId,
              intentModelId: data.data.intentModelId
            }
          };
          // 后端只给了最小映射：[{ id, agentId, pluginId }, ...]
          const savedMappings = data.data.functions || [];

          // 先保证 allFunctions 已经加载（如果没有，则先 fetchAllFunctions）
          const ensureFuncs = this.allFunctions.length
            ? Promise.resolve()
            : this.fetchAllFunctions();

          ensureFuncs.then(() => {
            // 合并：按照 pluginId（id 字段）把全量元数据信息补齐
            this.currentFunctions = savedMappings.map(mapping => {
              const meta = this.allFunctions.find(f => f.id === mapping.pluginId);
              if (!meta) {
                // 插件定义没找到，退化处理
                return { id: mapping.pluginId, name: mapping.pluginId, params: {} };
              }
              return {
                id: mapping.pluginId,
                name: meta.name,
                // 后端如果还有 paramInfo 字段就用 mapping.paramInfo，否则用 meta.params 默认值
                params: mapping.paramInfo || { ...meta.params },
                fieldsMeta: meta.fieldsMeta  // 保留以便对话框渲染 tooltip
              };
            });
            // 备份原始，以备取消时恢复
            this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));

            // 确保意图识别选项的可见性正确
            this.updateIntentOptionsVisibility();
          });
        } else {
          this.$message.error(data.msg || i18n.t('roleConfig.fetchConfigFailed'));
        }
      });
    },
    fetchModelOptions() {
      this.models.forEach(model => {
        if (model.type != "LLM") {
          Api.model.getModelNames(model.type, '', ({ data }) => {
            if (data.code === 0) {
              this.$set(this.modelOptions, model.type, data.data.map(item => ({
                value: item.id,
                label: item.modelName,
                isHidden: false
              })));

              // 如果是意图识别选项，需要根据当前LLM类型更新可见性
              if (model.type === 'Intent') {
                this.updateIntentOptionsVisibility();
              }
            } else {
              this.$message.error(data.msg || i18n.t('roleConfig.fetchModelsFailed'));
            }
          });
        } else {
          Api.model.getLlmModelCodeList('', ({ data }) => {
            if (data.code === 0) {
              let LLMdata = []
              data.data.forEach(item => {
                LLMdata.push({
                  value: item.id,
                  label: item.modelName,
                  isHidden: false
                })
                this.llmModeTypeMap.set(item.id, item.type)
              })
              this.$set(this.modelOptions, model.type, LLMdata);
            } else {
              this.$message.error(data.msg || '获取LLM模型列表失败');
            }
          });
        }
      });
    },
    fetchVoiceOptions(modelId) {
      if (!modelId) {
        this.voiceOptions = [];
        return;
      }
      Api.model.getModelVoices(modelId, '', ({ data }) => {
        if (data.code === 0 && data.data) {
          this.voiceOptions = data.data.map(voice => ({
            value: voice.id,
            label: voice.name
          }));
        } else {
          this.voiceOptions = [];
        }
      });
    },
    getFunctionDisplayChar(name) {
      if (!name || name.length === 0) return '';

      for (let i = 0; i < name.length; i++) {
        const char = name[i];
        if (/[\u4e00-\u9fa5a-zA-Z0-9]/.test(char)) {
          return char;
        }
      }

      // 如果没有找到有效字符，返回第一个字符
      return name.charAt(0);
    },
    showFunctionIcons(type) {
      return type === 'Intent' &&
        this.form.model.intentModelId !== 'Intent_nointent';
    },
    handleModelChange(type, value) {
      if (type === 'Intent' && value !== 'Intent_nointent') {
        this.fetchAllFunctions();
      }
      if (type === 'Memory' && value === 'Memory_nomem') {
        this.form.chatHistoryConf = 0;
      }
      if (type === 'Memory' && value !== 'Memory_nomem' && (this.form.chatHistoryConf === 0 || this.form.chatHistoryConf === null)) {
        this.form.chatHistoryConf = 2;
      }
      if (type === 'LLM') {
        // 当LLM类型改变时，更新意图识别选项的可见性
        this.updateIntentOptionsVisibility();
      }
    },
    fetchAllFunctions() {
      return new Promise((resolve, reject) => {
        Api.model.getPluginFunctionList(null, ({ data }) => {
          if (data.code === 0) {
            this.allFunctions = data.data.map(item => {
              const meta = JSON.parse(item.fields || '[]');
              const params = meta.reduce((m, f) => {
                m[f.key] = f.default;
                return m;
              }, {});
              return { ...item, fieldsMeta: meta, params };
            });
            resolve();
          } else {
            this.$message.error(data.msg || i18n.t('roleConfig.fetchPluginsFailed'));
            reject();
          }
        });
      });
    },
    openFunctionDialog() {
      // 显示编辑对话框时，确保 allFunctions 已经加载
      if (this.allFunctions.length === 0) {
        this.fetchAllFunctions().then(() => this.showFunctionDialog = true);
      } else {
        this.showFunctionDialog = true;
      }
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
      // 根据当前选择的LLM类型更新意图识别选项的可见性
      const currentLlmId = this.form.model.llmModelId;
      if (!currentLlmId || !this.modelOptions['Intent']) return;

      const llmType = this.llmModeTypeMap.get(currentLlmId);
      if (!llmType) return;

      this.modelOptions['Intent'].forEach(item => {
        if (item.value === "Intent_function_call") {
          // 如果llmType是openai或ollama，允许选择function_call
          // 否则隐藏function_call选项
          if (llmType === "openai" || llmType === "ollama") {
            item.isHidden = false;
          } else {
            item.isHidden = true;
          }
        } else {
          // 其他意图识别选项始终可见
          item.isHidden = false;
        }
      });

      // 如果当前选择的意图识别是function_call，但LLM类型不支持，则设置为可选的第一项
      if (this.form.model.intentModelId === "Intent_function_call" &&
        llmType !== "openai" && llmType !== "ollama") {
        // 找到第一个可见的选项
        const firstVisibleOption = this.modelOptions['Intent'].find(item => !item.isHidden);
        if (firstVisibleOption) {
          this.form.model.intentModelId = firstVisibleOption.value;
        } else {
          // 如果没有可见选项，设置为Intent_nointent
          this.form.model.intentModelId = 'Intent_nointent';
        }
      }
    },
    updateChatHistoryConf() {
      if (this.form.model.memModelId === 'Memory_nomem') {
        this.form.chatHistoryConf = 0;
      }
    },
  },
  watch: {
    'form.model.ttsModelId': {
      handler(newVal, oldVal) {
        if (oldVal && newVal !== oldVal) {
          this.form.ttsVoiceId = '';
          this.fetchVoiceOptions(newVal);
        } else {
          this.fetchVoiceOptions(newVal);
        }
      },
      immediate: true
    },
    voiceOptions: {
      handler(newVal) {
        if (newVal && newVal.length > 0 && !this.form.ttsVoiceId) {
          this.form.ttsVoiceId = newVal[0].value;
        }
      },
      immediate: true
    }
  },
  mounted() {
    const agentId = this.$route.query.agentId;
    if (agentId) {
      this.fetchAgentConfig(agentId);
      this.fetchAllFunctions();
    }
    this.fetchModelOptions();
    this.fetchTemplates();
  }
}
</script>

<style scoped>
.welcome {
  min-width: 900px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd);
  background-size: cover;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5vh 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
  color: #2c3e50;
}

.main-wrapper {
  margin: 1vh 22px;
  border-radius: 15px;
  height: calc(100vh - 24vh);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237, 242, 255, 0.5);
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
  width: 100%;
}

.form-textarea {
  width: 100%;
}

.template-container {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.template-item {
  height: 4vh;
  width: 76px;
  border-radius: 8px;
  background: #e6ebff;
  line-height: 4vh;
  font-weight: 400;
  font-size: 11px;
  text-align: center;
  color: #5778ff;
  cursor: pointer;
  transition: background-color 0.3s ease;
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
  color: #409EFF;
  border-color: #409EFF;
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
</style>