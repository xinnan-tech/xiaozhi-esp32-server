<template>
  <CustomDialog
    :title="title"
    :visible.sync="innerVisible"
    :confirm-loading="saving"
    width="600px"
    @confirm="submit"
    @cancel="cancel"
  >
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
  </CustomDialog>
</template>

<script>
import api from '@/apis/api';
import CustomDialog from './CustomDialog.vue';

export default {
  components: { CustomDialog },
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
  computed: {
    innerVisible: {
      get() {
        return this.visible;
      },
      set(val) {
        this.$emit('update:visible', val);
      }
    }
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
          this.saving = true;
          this.$emit('submit', {
            form: this.form,
            done: () => {
              this.saving = false;
            }
          });

          setTimeout(() => {
            this.saving = false;
          }, 3000);
        }
      });
    },
    cancel() {
      this.saving = false;
      this.$emit('cancel');
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.saving = false;
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

<style scoped lang="scss">
.audio-icon {
  font-size: 20px;
  cursor: pointer;
  margin: 0 5px;
  color: #1890ff;
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
</style>
