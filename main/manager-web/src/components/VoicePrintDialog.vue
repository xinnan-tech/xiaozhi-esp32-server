<template>
  <el-dialog :title="title" :visible.sync="visible" width="520px" class="param-dialog-wrapper" :append-to-body="true"
    :close-on-click-modal="false" :key="dialogKey" custom-class="custom-param-dialog" :show-close="false">
    <div class="dialog-container">
      <div class="dialog-header">
        <h2 class="dialog-title">{{ title }}</h2>
        <button class="custom-close-btn" @click="cancel">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 1L1 13M1 1L13 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </button>
      </div>

      <el-form :model="form" :rules="rules" ref="form" label-width="auto" label-position="left" class="param-form">
        <el-form-item :label="$t('voicePrintDialog.voicePrintVector')" prop="audioId" class="form-item">
          <el-select v-model="form.audioId" :placeholder="$t('voicePrintDialog.selectVoiceMessage')" class="custom-select">
            <el-option v-for="item in valueTypeOptions" :key="item.audioId" :label="item.content" :value="item.audioId">
              <span style="float: left">{{ item.content }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                <i :class="getAudioIconClass(item.audioId)" @click.stop="playAudio(item.audioId)"
                  class="audio-icon"></i>
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('voicePrintDialog.name')" prop="sourceName" class="form-item">
          <el-input v-model="form.sourceName" :placeholder="$t('voicePrintDialog.enterName')" class="custom-input"></el-input>
        </el-form-item>

        <el-form-item :label="$t('voicePrintDialog.description')" prop="introduce" class="form-item remark-item">
          <el-input type="textarea" v-model="form.introduce" :placeholder="$t('voicePrintDialog.enterDescription')" :rows="3" class="custom-textarea"
            maxlength="100" show-word-limit></el-input>
        </el-form-item>
      </el-form>

      <div class="dialog-footer">
        <el-button type="primary" @click="submit" class="save-btn" :loading="saving" :disabled="saving">
          {{ $t('voicePrintDialog.save') }}
        </el-button>
        <el-button @click="cancel" class="cancel-btn">
          {{ $t('voicePrintDialog.cancel') }}
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import api from '@/apis/api';

export default {
  props: {
    title: {
      type: String,
      default: '添加说话人'
    },
    visible: {
      type: Boolean,
      default: false
    },
    agentId: {
      type: String
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        audioId: '',
        sourceName: '',
        introduce: ''
      })
    }
  },
  data() {
    return {
      dialogKey: Date.now(),
      saving: false,
      playingAudioId: null,
      audioElement: null,
      valueTypeOptions: [
        { audioId: '', content: '' }
      ],
      rules: {
        introduce: [
          { required: true, message: '请输入描述', trigger: "blur" }
        ],
        sourceName: [
          { required: true, message: '请输入名称', trigger: "blur" }
        ],
        audioId: [
          { required: true, message: '请选择音频向量', trigger: "change" }
        ]
      }
    };
  },
  methods: {
    getAudioIconClass(audioId) {
      if (this.playingAudioId === audioId) {
        return 'el-icon-loading';
      }
      return 'el-icon-video-play';
    },
    playAudio(audioId) {
      if (this.playingAudioId === audioId) {
        // 如果正在播放当前音频，则停止播放
        if (this.audioElement) {
          this.audioElement.pause();
          this.audioElement = null;
        }
        this.playingAudioId = null;
        return;
      }

      // 停止当前正在播放的音频
      if (this.audioElement) {
        this.audioElement.pause();
        this.audioElement = null;
      }

      // 先获取音频下载ID
      this.playingAudioId = audioId;
      api.agent.getAudioId(audioId, (res) => {
        if (res.data && res.data.data) {
          // 使用获取到的下载ID播放音频
          this.audioElement = new Audio(api.getServiceUrl() + `/agent/play/${res.data.data}`);

          this.audioElement.onended = () => {
            this.playingAudioId = null;
            this.audioElement = null;
          };

          this.audioElement.play();
        }
      });
    },
    submit() {
      this.$refs.form.validate((valid) => {
        if (valid) {
          this.saving = true; // 开始加载
          this.$emit('submit', {
            form: this.form,
            done: () => {
              this.saving = false; // 加载完成
            }
          });

          setTimeout(() => {
            this.saving = false;
          }, 3000);
        }
      });
    },
    cancel() {
      this.saving = false; // 取消时重置状态
      this.$emit('cancel');
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.dialogKey = Date.now();
        api.agent.getRecentlyFiftyByAgentId(this.agentId, ((data) => {
          this.valueTypeOptions = data.data.data.map(item => ({
            ...item
          }));
        }))
      }
    },
    'form.audioId'(newVal) {
      if (newVal == null || newVal == "") {
        return
      }
      if (this.valueTypeOptions.some(item => item.audioId === newVal)) {
        return;
      }
      api.agent.getContentByAudioId(newVal, ((data) => {
        this.valueTypeOptions.push({
          audioId: newVal, content: data.data.data
        })
      }))
    }
  }
};
</script>

<style>
.custom-param-dialog {
  border-radius: 16px !important;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15) !important;
  border: none !important;

  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 0 !important;
    border-radius: 16px;
  }
}
</style>

<style scoped lang="scss">
.audio-icon {
  font-size: 20px;
  cursor: pointer;
  margin: 0 5px;
  color: #1890ff;
}

.param-dialog-wrapper {
  .dialog-container {
    padding: 24px 32px;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  }

  .dialog-header {
    position: relative;
    margin-bottom: 24px;
    text-align: center;
  }

  .dialog-title {
    font-size: 20px;
    color: #1e293b;
    margin: 0;
    padding: 0;
    font-weight: 600;
    letter-spacing: 0.5px;
  }

  .custom-close-btn {
    position: absolute;
    top: -8px;
    right: -8px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: #f1f5f9;
    color: #64748b;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    outline: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

    &:hover {
      color: #ffffff;
      background: #ef4444;
      transform: rotate(90deg);
      box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2);
    }

    svg {
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
  }

  .param-form {
    .form-item {
      margin-bottom: 20px;

      :deep(.el-form-item__label) {
        color: #475569;
        font-weight: 500;
        padding-right: 12px;
        text-align: right;
        font-size: 14px;
        letter-spacing: 0.2px;
      }
    }

    .custom-input {
      :deep(.el-input__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        height: 42px;
        padding: 0 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .custom-select {
      width: 100%;

      :deep(.el-input__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        height: 42px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .custom-textarea {
      :deep(.el-textarea__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 12px 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        line-height: 1.5;

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .remark-item :deep(.el-form-item__label) {
      margin-top: -4px;
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: center;
    padding: 16px 0 0;
    margin-top: 16px;

    .save-btn {
      width: 120px;
      height: 42px;
      font-size: 14px;
      font-weight: 500;
      border-radius: 8px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      background: #3b82f6;
      color: white;
      border: none;
      letter-spacing: 0.5px;
      box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);

      &:hover {
        background: #2563eb;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
      }

      &:active {
        transform: translateY(0);
        box-shadow: 0 2px 3px rgba(59, 130, 246, 0.2);
      }
    }

    .cancel-btn {
      width: 120px;
      height: 42px;
      font-size: 14px;
      font-weight: 500;
      border-radius: 8px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      background: #ffffff;
      color: #64748b;
      border: 1px solid #e2e8f0;
      margin-left: 16px;
      letter-spacing: 0.5px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

      &:hover {
        background: #f8fafc;
        color: #475569;
        border-color: #cbd5e1;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      &:active {
        transform: translateY(0);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
      }
    }
  }
}
</style>
