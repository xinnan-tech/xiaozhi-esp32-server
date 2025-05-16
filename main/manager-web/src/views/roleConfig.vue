<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">角色配置</h2>
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
                  <span>保存配置后，需要重启设备，新的配置才会生效。</span>
                </div>
                <el-button type="primary" class="save-btn" @click="saveConfig">保存配置</el-button>
                <el-button class="reset-btn" @click="resetConfig">重置</el-button>
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
                    <el-form-item label="助手昵称：">
                      <el-input v-model="form.agentName" class="form-input" maxlength="10" />
                    </el-form-item>
                    <el-form-item label="角色模版：">
                      <div class="template-container">
                        <div v-for="(template, index) in templates" :key="`template-${index}`" class="template-item"
                          :class="{ 'template-loading': loadingTemplate }" @click="selectTemplate(template)">
                          {{ template.agentName }}
                        </div>
                      </div>
                    </el-form-item>
                    <el-form-item label="角色介绍：">
                      <el-input type="textarea" rows="9" resize="none" placeholder="请输入内容" v-model="form.systemPrompt"
                        maxlength="2000" show-word-limit class="form-textarea" />
                    </el-form-item>

                    <el-form-item label="记忆：">
                      <el-input type="textarea" rows="6" resize="none" v-model="form.summaryMemory" maxlength="2000"
                        show-word-limit class="form-textarea"
                        :disabled="form.model.memModelId !== 'Memory_mem_local_short'" />
                    </el-form-item>
                    <el-form-item label="语言编码：" style="display: none;">
                      <el-input v-model="form.langCode" placeholder="请输入语言编码，如：zh_CN" maxlength="10" show-word-limit
                        class="form-input" />
                    </el-form-item>
                    <el-form-item label="交互语种：" style="display: none;">
                      <el-input v-model="form.language" placeholder="请输入交互语种，如：中文" maxlength="10" show-word-limit
                        class="form-input" />
                    </el-form-item>
                  </div>
                  <div class="form-column">
                    <el-form-item v-for="(model, index) in models" :key="`model-${index}`" :label="model.label"
                      class="model-item">
                      <div class="model-select-wrapper">
                        <el-select v-model="form.model[model.key]" filterable placeholder="请选择" class="form-select"
                          @change="handleModelChange(model.type, $event)">
                          <el-option v-for="(item, optionIndex) in modelOptions[model.type]"
                            :key="`option-${index}-${optionIndex}`" :label="item.label" :value="item.value" />
                        </el-select>
                        <div v-if="showFunctionIcons(model.type)" class="function-icons">
                          <el-tooltip v-for="func in currentFunctions" :key="func.name" effect="dark" placement="top"
                            popper-class="custom-tooltip">
                            <div slot="content">
                              <div><strong>功能名称:</strong> {{ func.name }}</div>
                              <div v-if="Object.keys(func.params).length > 0">
                                <strong>参数配置:</strong>
                                <div v-for="(value, key) in func.params" :key="key">
                                  {{ key }}: {{ value }}
                                </div>
                              </div>
                              <div v-else>无参数配置</div>
                            </div>
                            <div class="icon-dot" :style="{ backgroundColor: getFunctionColor(func.name) }">
                              {{ func.name.charAt(0) }}
                            </div>
                          </el-tooltip>
                          <el-button class="edit-function-btn" @click="showFunctionDialog = true"
                            :class="{ 'active-btn': showFunctionDialog }">
                            编辑功能
                          </el-button>
                        </div>
                        <div v-if="model.type === 'Memory' && form.model.memModelId !== 'Memory_nomem'"
                          class="chat-history-options">
                          <el-radio-group v-model="form.chatHistoryConf" @change="updateChatHistoryConf">
                            <el-radio-button :label="1">上报文字</el-radio-button>
                            <el-radio-button :label="2">上报文字+语音</el-radio-button>
                          </el-radio-group>
                        </div>
                      </div>
                    </el-form-item>
                    <el-form-item label="角色音色">
                      <el-select v-model="form.ttsVoiceId" placeholder="请选择" class="form-select">
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

    <function-dialog v-model="showFunctionDialog" :functions="currentFunctions"
      @update-functions="handleUpdateFunctions" @dialog-closed="handleDialogClosed" />
  </div>
</template>

<script>
import Api from '@/apis/api';
import FunctionDialog from "@/components/FunctionDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";

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
          memModelId: "",
          intentModelId: "",
        }
      },
      models: [
        { label: '语音活动检测(VAD)', key: 'vadModelId', type: 'VAD' },
        { label: '语音识别(ASR)', key: 'asrModelId', type: 'ASR' },
        { label: '大语言模型(LLM)', key: 'llmModelId', type: 'LLM' },
        { label: '意图识别(Intent)', key: 'intentModelId', type: 'Intent' },
        { label: '记忆(Memory)', key: 'memModelId', type: 'Memory' },
        { label: '语音合成(TTS)', key: 'ttsModelId', type: 'TTS' },
      ],
      modelOptions: {},
      templates: [],
      loadingTemplate: false,
      voiceOptions: [],
      showFunctionDialog: false,
      currentFunctions: [],
      functionColorMap: [
        '#FF6B6B', '#4ECDC4', '#45B7D1',
        '#96CEB4', '#FFEEAD', '#D4A5A5', '#A2836E'
      ],
      allFunctions: [
        { name: '天气', params: {} },
        { name: '新闻', params: {} },
        { name: '工具', params: {} },
        { name: '退出', params: {} }
      ],
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
        functions: this.currentFunctions
      };
      Api.agent.updateAgentConfig(this.$route.query.agentId, configData, ({ data }) => {
        if (data.code === 0) {
          this.$message.success({
            message: '配置保存成功',
            showClose: true
          });
        } else {
          this.$message.error({
            message: data.msg || '配置保存失败',
            showClose: true
          });
        }
      });
    },
    resetConfig() {
      this.$confirm('确定要重置配置吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
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
            memModelId: "",
            intentModelId: "",
          }
        }
        this.currentFunctions = [];
        this.$message.success({
          message: '配置已重置',
          showClose: true
        })
      }).catch(() => { });
    },
    fetchTemplates() {
      Api.agent.getAgentTemplate(({ data }) => {
        if (data.code === 0) {
          this.templates = data.data;
        } else {
          this.$message.error(data.msg || '获取模板列表失败');
        }
      });
    },
    selectTemplate(template) {
      if (this.loadingTemplate) return;
      this.loadingTemplate = true;
      try {
        this.applyTemplateData(template);
        this.$message.success({
          message: `「${template.agentName}」模板已应用`,
          showClose: true
        });
      } catch (error) {
        this.$message.error({
          message: '应用模板失败',
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
              memModelId: data.data.memModelId,
              intentModelId: data.data.intentModelId
            }
          };
          this.currentFunctions = data.data.functions || [];
        } else {
          this.$message.error(data.msg || '获取配置失败');
        }
      });
    },
    fetchModelOptions() {
      this.models.forEach(model => {
        Api.model.getModelNames(model.type, '', ({ data }) => {
          if (data.code === 0) {
            this.$set(this.modelOptions, model.type, data.data.map(item => ({
              value: item.id,
              label: item.modelName
            })));
          } else {
            this.$message.error(data.msg || '获取模型列表失败');
          }
        });
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
    getFunctionColor(name) {
      const hash = [...name].reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return this.functionColorMap[hash % 7];
    },
    showFunctionIcons(type) {
      // TODO 暂时不放出来
      return false;
      // return type === 'Intent' &&
      //   this.form.model.intentModelId !== 'Intent_nointent';
    },
    handleModelChange(type, value) {
      if (type === 'Intent' && value !== 'Intent_nointent') {
        this.fetchFunctionList();
      }
      if (type === 'Memory' && value === 'Memory_nomem') {
        this.form.chatHistoryConf = 0;
      }
      if (type === 'Memory' && value !== 'Memory_nomem' && (this.form.chatHistoryConf === 0 || this.form.chatHistoryConf === null)) {
        this.form.chatHistoryConf = 2;
      }
    },
    fetchFunctionList() {
      // 使用假数据代替API调用
      return new Promise(resolve => {
        setTimeout(() => {
          this.currentFunctions = [
            { name: '天气', params: { city: '北京' } },
            { name: '新闻', params: { type: '科技' } }
          ];
          resolve();
        }, 500);
      });
    },
    handleUpdateFunctions(selected) {
      this.currentFunctions = selected;
      console.log('保存的功能列表:', selected);
      this.$message.success('功能配置已保存');
    },
    handleDialogClosed(saved) {
      if (!saved) {
        // 如果未保存，恢复原始功能列表
        this.currentFunctions = JSON.parse(JSON.stringify(this.originalFunctions));
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
      this.fetchFunctionList().then(() => {
        this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
      });
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
  color: white;
  font-weight: bold;
  font-size: 12px;
  margin-right: 8px;
  position: relative;
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