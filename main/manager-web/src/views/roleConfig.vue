<template>
  <div class="welcome">
    <HeaderBar />
    <el-main style="padding: 16px;display: flex;flex-direction: column;">
      <div style="border-radius: 16px;background: #fafcfe; border: 1px solid #e8f0ff;">
        <div
          style="padding: 15px 24px;font-weight: 700;font-size: 19px;text-align: left;color: #3d4566;display: flex;gap: 13px;align-items: center;">
          <div
            style="width: 37px;height: 37px;background: #5778ff;border-radius: 50%;display: flex;align-items: center;justify-content: center;">
            <img loading="lazy" src="@/assets/home/setting-user.png" alt="" style="width: 19px;height: 19px;" />
          </div>
          {{ form.agentName }}
        </div>
        <div style="height: 1px;background: #e8f0ff;" />
        <el-form ref="form" :model="form" label-width="72px">
          <div style="padding: 16px 24px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
              <div>
                <el-form-item label="助手昵称：">
                  <div class="input-46" style="width: 100%;">
                    <el-input v-model="form.agentName" />
                  </div>
                </el-form-item>
                <el-form-item label="角色模版：">
                  <div style="display: flex;gap: 8px;flex-wrap: wrap;">
                    <div v-for="(template, index) in templates" :key="`template-${index}`" class="template-item"
                      :class="{ 'template-loading': loadingTemplate }" @click="selectTemplate(template)">
                      {{ template.agentName }}
                    </div>
                  </div>
                </el-form-item>
                <el-form-item label="角色介绍：">
                  <div class="textarea-box">
                    <el-input type="textarea" rows="5" resize="none" placeholder="请输入内容" v-model="form.systemPrompt"
                      maxlength="2000" show-word-limit />
                  </div>
                </el-form-item>
                <el-form-item label="语言编码：">
                  <div class="input-46" style="width: 100%;">
                    <el-input v-model="form.langCode" placeholder="请输入语言编码，如：zh_CN" maxlength="10" show-word-limit />
                  </div>
                </el-form-item>
                <el-form-item label="交互语种：">
                  <div class="input-46" style="width: 100%;">
                    <el-input v-model="form.language" placeholder="请输入交互语种，如：中文" maxlength="10" show-word-limit />
                  </div>
                </el-form-item>
              </div>
              <div>
                <el-form-item v-for="(model, index) in models" :key="`model-${index}`" :label="model.label"
                  class="model-item">
                  <el-select v-model="form.model[model.key]" filterable placeholder="请选择" class="select-field">
                    <el-option v-for="(item, optionIndex) in modelOptions[model.type]"
                      :key="`option-${index}-${optionIndex}`" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="角色音色：">
                  <div style="display: flex;gap: 8px;align-items: center;">
                    <div class="input-46" style="width: 100%;">
                      <el-select v-model="form.ttsVoiceId" placeholder="请选择" style="width: 100%;">
                        <el-option v-for="(item, index) in voiceOptions" :key="`voice-${index}`" :label="item.label"
                          :value="item.value" />
                      </el-select>
                    </div>
                  </div>
                </el-form-item>
              </div>
            </div>
          </div>
        </el-form>
        <div style="display: flex;padding: 16px;gap: 8px;align-items: center;">
          <div class="save-btn" @click="saveConfig">
            保存配置
          </div>
          <div class="reset-btn" @click="resetConfig">
            重制
          </div>
          <div class="clear-text">
            <img loading="lazy" src="@/assets/home/red-info.png" alt="" style="width: 19px;height: 19px;" />
            保存配置后，需要重启设备，新的配置才会生效。
          </div>
        </div>
      </div>
      <div class="copyright">
        ©2025 xiaozhi-esp32-server
      </div>
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from "@/components/HeaderBar.vue";


export default {
  name: 'RoleConfigPage',
  components: { HeaderBar },
  data() {
    return {
      form: {
        agentCode: "",
        agentName: "",
        ttsVoiceId: "",
        systemPrompt: "",
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
    }
  },
  methods: {
    saveConfig() {
      const configData = {
        agentCode: this.form.agentCode,
        agentName: this.form.agentName,
        asrModelId: this.form.model.asrModelId,
        vadModelId: this.form.model.vadModelId,
        llmModelId: this.form.model.llmModelId,
        ttsModelId: this.form.model.ttsModelId,
        ttsVoiceId: this.form.ttsVoiceId,
        memModelId: this.form.model.memModelId,
        intentModelId: this.form.model.intentModelId,
        systemPrompt: this.form.systemPrompt,
        langCode: this.form.langCode,
        language: this.form.language,
        sort: this.form.sort
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
        // 重置表单
        this.form = {
          agentCode: "",
          agentName: "",
          ttsVoiceId: "",
          systemPrompt: "",
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
        this.$message.success({
          message: '配置已重置',
          showClose: true
        })
      }).catch(() => {
      })
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
        systemPrompt: templateData.systemPrompt || this.form.systemPrompt,
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
        } else {
          this.$message.error(data.msg || '获取配置失败');
        }
      });
    },
    fetchModelOptions() {
      // 为每个模型类型获取选项
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
    }
  },
  watch: {
    'form.model.ttsModelId': {
      handler(newVal, oldVal) {
        console.log('TTS模型变化:', newVal);
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
    }
    this.fetchModelOptions();
    this.fetchTemplates();
  }
}
</script>

<style scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(145deg, #e6eeff, #eff0ff);
  background-size: cover;
  /* 确保背景图像覆盖整个元素 */
  background-position: center;
  /* 从顶部中心对齐 */
  -webkit-background-size: cover;
  /* 兼容老版本WebKit浏览器 */
  -o-background-size: cover;
  /* 兼容老版本Opera浏览器 */
}

.el-form-item ::v-deep .el-form-item__label {
  font-size: 10px !important;
  color: #3d4566 !important;
  font-weight: 400;
  line-height: 22px;
  padding-bottom: 2px;
}

.select-field {
  width: 100%;
  max-width: 720px;
  border: 1px solid #e4e6ef;
  background: #f6f8fb;
  border-radius: 8px;
  height: 36px !important;
}

.audio-box {
  flex: 1;
  height: 37px;
  border-radius: 20px;
  border: 1px solid #e4e6ef;
}

.clear-btn {
  width: 48px;
  height: 19px;
  background: #fd8383;
  border-radius: 10px;
  line-height: 19px;
  font-size: 11px;
  color: #fff;
  cursor: pointer;
}

.clear-text {
  color: #979db1;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
}

.template-item {
  height: 37px;
  width: 76px;
  border-radius: 8px;
  background: #e6ebff;
  line-height: 37px;
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

.prompt-bottom {
  margin-bottom: 4px;
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
  align-items: center;
}

.input-46 {
  border: 1px solid #e4e6ef;
  background: #f6f8fb;
  border-radius: 8px;
  height: 36px !important;
}

.save-btn,
.reset-btn {
  width: 112px;
  height: 37px;
  border-radius: 18px;
  line-height: 37px;
  box-sizing: border-box;
  cursor: pointer;
  font-size: 11px
}

.save-btn {
  border-radius: 18px;
  background: #5778ff;
  color: #fff;
}

.reset-btn {
  border: 1px solid #adbdff;
  background: #e6ebff;
  color: #5778ff;
}

.textarea-box {
  border: 1px solid #e4e6ef;
  border-radius: 8px;
  background: #f6f8fb;
}
</style>
