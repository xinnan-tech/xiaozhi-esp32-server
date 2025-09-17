<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">模板快速配置</h2>
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
                <!-- 以下是要删除的部分 -->
                <!-- 删除整个提示文本容器 -->
                <el-button type="primary" class="save-btn" @click="saveConfig">保存配置</el-button>
                <el-button class="reset-btn" @click="resetConfig">重置</el-button>
                <button class="custom-close-btn" @click="goToHome">
                  ×
                </button>
              </div>
            </div>
            <div class="divider"></div>

            <el-form ref="form" :model="form" label-width="72px" class="full-height-form">
              <!-- 助手昵称 -->
              <el-form-item label="助手昵称" prop="agentName" class="nickname-item">
                <el-input
                  v-model="form.agentName"
                  placeholder="请输入助手昵称"
                  :validate-event="false"
                  class="form-input"
                />
              </el-form-item>
              
              <!-- 角色介绍 -->
              <el-form-item label="角色介绍" prop="systemPrompt" class="description-item">
                <el-input
                  v-model="form.systemPrompt"
                  type="textarea"
                  placeholder="请输入角色介绍"
                  :validate-event="false"
                  show-word-limit
                  maxlength="2000"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Api from '@/apis/api';
import FunctionDialog from "@/components/FunctionDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import agentApi from '@/apis/module/agent';

export default {
  name: 'TemplateQuickConfig',
  components: { HeaderBar, FunctionDialog },
  data() {
    return {
      form: {
        agentCode: "小智", // 设置默认值
        agentName: "",
        ttsVoiceId: "TTS_EdgeTTS0001", // 添加默认值
        chatHistoryConf: 0,
        systemPrompt: "",
        summaryMemory: "",
        langCode: "zh", // 设置默认值
        language: "中文", // 设置默认值
        sort: 0, // 设置默认值
        model: {
          ttsModelId: "TTS_EdgeTTS", // 添加默认值
          vadModelId: "VAD_SileroVAD", // 设置默认值
          asrModelId: "ASR_FunASR", // 设置默认值
          llmModelId: "LLM_ChatGLMLLM", // 设置默认值
          vllmModelId: "VLLM_ChatGLMVLLM", // 设置默认值
          memModelId: "Memory_nomem", // 设置默认值
          intentModelId: "Intent_function_call", // 设置默认值
        }
      },
      models: [
        { label: '语音活动检测(VAD)', key: 'vadModelId', type: 'VAD' },
        { label: '语音识别(ASR)', key: 'asrModelId', type: 'ASR' },
        { label: '大语言模型(LLM)', key: 'llmModelId', type: 'LLM' },
        { label: '视觉大模型(VLLM)', key: 'vllmModelId', type: 'VLLM' },
        { label: '意图识别(Intent)', key: 'intentModelId', type: 'Intent' },
        { label: '记忆(Memory)', key: 'memModelId', type: 'Memory' },
        { label: '语音合成(TTS)', key: 'ttsModelId', type: 'TTS' }
      ],
      llmModeTypeMap: new Map(),
      modelOptions: {},
      templateId: '',
      voiceOptions: [],
      showFunctionDialog: false,
      currentFunctions: [],
      functionColorMap: [
        '#FF6B6B', '#4ECDC4', '#45B7D1',
        '#96CEB4', '#FFEEAD', '#D4A5A5', '#A2836E'
      ],
      allFunctions: [],
      originalFunctions: [],
      originalForm: null
    }
  },
  methods: {
    goToHome() {
      this.$router.push('/agent-template-management');
    },
    // 修改saveConfig方法中的响应检查逻辑
    saveConfig() {
      const configData = {
        agentCode: this.form.agentCode,
        agentName: this.form.agentName,
        // 不需要单独提交agentDescription，使用systemPrompt字段
        asrModelId: this.form.model.asrModelId,
        vadModelId: this.form.model.vadModelId,
        llmModelId: this.form.model.llmModelId,
        vllmModelId: this.form.model.vllmModelId,
        ttsModelId: this.form.model.ttsModelId,
        ttsVoiceId: this.form.ttsVoiceId,
        chatHistoryConf: this.form.chatHistoryConf,
        memModelId: this.form.model.memModelId,
        intentModelId: this.form.model.intentModelId,
        systemPrompt: this.form.systemPrompt, // 这个字段会保存角色介绍
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
      
      // 修复saveConfig方法中的回调参数结构
      // 如果有templateId，使用更新模板API
      if (this.templateId) {
        configData.id = this.templateId;
        agentApi.updateAgentTemplate(configData, (res) => {  // 修改为(res)而不是({ res })
          // 添加调试日志以便排查问题
          console.log('保存模板响应:', res);
          
          if (res && typeof res === 'object') {
            // 检查res.data是否存在且包含code=0
            if (res.data && res.data.code === 0) {
              this.$message.success({
                message: '模板配置保存成功',
                showClose: true
              });
              this.originalForm = JSON.parse(JSON.stringify(this.form));
              this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
            } else {
              this.$message.error({
                message: res?.data?.msg || '模板配置保存失败',
                showClose: true
              });
            }
          } else {
            console.error('无效的响应对象:', res);
            this.$message.error('保存失败，请检查后端服务是否正常');
          }
        });
      } else {
        // 否则使用添加模板API
        agentApi.addAgentTemplate(configData, (res) => {  // 修改为(res)而不是({ res })
          // 添加调试日志以便排查问题
          console.log('添加模板响应:', res);
          
          if (res && typeof res === 'object') {
            // 检查res.data是否存在且包含code=0
            if (res.data && res.data.code === 0) {
              this.$message.success({
                message: '模板配置保存成功',
                showClose: true
              });
              this.goToHome();
            } else {
              this.$message.error({
                message: res?.data?.msg || '模板配置保存失败',
                showClose: true
              });
            }
          } else {
            console.error('无效的响应对象:', res);
            this.$message.error('保存失败，请检查后端服务是否正常');
          }
        });
      }
    },
    resetConfig() {
      this.$confirm('确定要重置配置吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        if (this.originalForm) {
          this.form = JSON.parse(JSON.stringify(this.originalForm));
          this.currentFunctions = JSON.parse(JSON.stringify(this.originalFunctions));
        }
        this.$message.success({
          message: '配置已重置',
          showClose: true
        })
      }).catch(() => {
      });
    },
    // 修改fetchTemplateById方法中的回调参数结构
    fetchTemplateById(templateId) {
      // 获取所有模板，然后找到指定ID的模板
      agentApi.getAgentTemplate((res) => {  // 修改为(res)而不是({ data })
        // 添加调试日志以便排查问题
        console.log('获取模板列表完整响应:', res);
        
        if (res && typeof res === 'object') {
          // 检查res.data是否存在且包含code=0
          if (res.data && res.data.code === 0) {
            // 实际数据在res.data.data中，而不是res.data
            const templateList = res.data.data || [];
            console.log('实际模板列表数据:', templateList);
            
            const template = templateList.find(t => t.id === templateId);
            if (template) {
              this.applyTemplateData(template);
              this.templateId = templateId;
              this.originalForm = JSON.parse(JSON.stringify(this.form));
              this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
            } else {
              console.error('未找到指定模板，ID:', templateId);
              this.$message.error('未找到指定模板');
            }
          } else {
            console.error('获取模板失败:', res);
            this.$message.error(res?.data?.msg || '获取模板失败');
          }
        } else {
          console.error('无效的响应对象:', res);
          this.$message.error('获取模板失败，请检查后端服务是否正常');
        }
      });
    },
    applyTemplateData(templateData) {
      this.form = {
        ...this.form,
        agentName: templateData.agentName || this.form.agentName,
        agentCode: templateData.agentCode || this.form.agentCode,
        // 删除agentDescription字段的处理
        ttsVoiceId: templateData.ttsVoiceId || this.form.ttsVoiceId,
        chatHistoryConf: templateData.chatHistoryConf || this.form.chatHistoryConf,
        systemPrompt: templateData.systemPrompt || this.form.systemPrompt,
        summaryMemory: templateData.summaryMemory || this.form.summaryMemory,
        langCode: templateData.langCode || this.form.langCode,
        language: templateData.language || this.form.language,
        sort: templateData.sort || this.form.sort,
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
              this.$message.error(data.msg || '获取模型列表失败');
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
    getFunctionColor(name) {
      const hash = [...name].reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return this.functionColorMap[hash % this.functionColorMap.length];
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
            this.$message.error(data.msg || '获取插件列表失败');
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
    // 从URL参数获取templateId
    const templateId = this.$route.query.templateId;
    this.fetchModelOptions();
    this.fetchAllFunctions();
    
    if (templateId) {
      this.fetchTemplateById(templateId);
    } else {
      // 如果没有templateId，初始化一个新的模板
      this.form.agentName = '新模板';
      
      // 获取所有模板以计算最大的sort值
      agentApi.getAgentTemplate((res) => {
        if (res && typeof res === 'object' && res.data && res.data.code === 0) {
          const templateList = res.data.data || [];
          if (templateList && templateList.length > 0) {
            // 计算最大的sort值
            const maxSort = Math.max(...templateList.map(t => t.sort || 0));
            // 设置新模板的sort值为最大值+1
            this.form.sort = maxSort + 1;
          } else {
            // 如果没有模板，设置默认值为1
            this.form.sort = 1;
          }
        } else {
          console.error('获取模板列表失败，使用默认sort值');
          // 获取失败时使用默认值
          this.form.sort = 1;
        }
        
        // 保存初始状态
        this.originalForm = JSON.parse(JSON.stringify(this.form));
        this.originalFunctions = JSON.parse(JSON.stringify(this.currentFunctions));
      });
    }
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
  margin: 0 22px 22px 22px; /* 保留左右和底部边距 */
  border-radius: 15px;
  height: calc(100vh - 14vh); /* 调整高度计算 */
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237, 242, 255, 0.5);
  display: flex;
  flex-direction: column;
  padding: 0 !important; /* 确保没有内边距 */
}

.content-panel {
  flex: 1;
  overflow-y: auto;
  padding: 0 !important; /* 确保没有内边距 */
  margin: 0 !important; /* 确保没有外边距 */
}

.content-area {
  width: 100% !important;
  max-width: none !important;
  margin: 0 !important;
  height: 100% !important;
}

/* 调整config-card样式 */
.config-card {
  background: white !important;
  border-radius: 15px !important;
  overflow: hidden !important;
  height: 100% !important;
  margin: 0 !important;
  border: none !important;
  box-shadow: none !important;
}

/* 修复表单容器样式 */
.full-height-form {
  display: flex;
  flex-direction: column;
  padding: 20px;
  gap: 20px;
  height: calc(100% - 120px);
}

/* 助手昵称样式 */
.nickname-item {
  margin-bottom: 0 !important;
}

/* 修复角色介绍项目样式 */
.description-item {
  margin-bottom: 0 !important;
  display: flex;
  flex-direction: column;
}

/* 修复Element UI的textarea容器样式 */
::v-deep .description-item .el-textarea {
  height: 300px; /* 设置固定高度 */
  min-height: 200px; /* 最小高度 */
  max-height: 400px; /* 最大高度，防止超出页面 */
  display: flex;
  flex-direction: column;
}

/* 修复textarea样式 */
::v-deep .description-item .el-textarea__inner {
  height: 100% !important;
  min-height: 200px !important;
  max-height: 400px !important;
  resize: vertical !important; /* 允许垂直调整大小 */
  line-height: 1.6;
  font-size: 14px;
  padding: 10px;
  border: 1px solid #dcdfe6; /* 添加边框使其更清晰可见 */
  border-radius: 4px; /* 添加圆角 */
  background-color: #fff; /* 确保背景色为白色 */
  color: #303133; /* 确保文字颜色正常 */
}

/* 其他样式保持不变 */
::v-deep .el-form-item__label {
  font-size: 12px !important;
  color: #3d4566 !important;
  font-weight: 400;
  line-height: 22px;
  padding-bottom: 2px;
}

::v-deep .el-textarea .el-input__count {
  color: #909399;
  background: rgba(255, 255, 255, 0.8);
  position: absolute;
  font-size: 12px;
  right: 10px;
  bottom: 10px;
  padding: 2px 5px;
  border-radius: 3px;
}

/* 配置头部样式调整 */
.config-header {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  background: #f8f9ff;
}

.header-icon img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.header-title {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
}

/* 其他按钮和操作区样式保持不变 */
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

/* 隐藏所有不需要的元素 */
.model-select-wrapper, .model-row, .function-icons, .icon-dot, .edit-function-btn, .chat-history-options {
  display: none !important;
}
</style>