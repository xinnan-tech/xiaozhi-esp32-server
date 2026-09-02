<template>
  <CustomDialog
    :title="title"
    :visible.sync="visible"
    width="700px"
    class="param-dialog-wrapper"
    @confirm="submit"
    @close="cancel"
    :confirmLoading="saving"
  >
    <el-form :model="localForm" :rules="rules" ref="form" label-width="auto" label-position="left" class="param-form">
      <el-form-item :label="$t('replacementDialog.fileName')" prop="fileName">
        <el-input v-model="localForm.fileName" :placeholder="$t('replacementDialog.fileNamePlaceholder')"
          @input="clearFieldError('fileName')"></el-input>
      </el-form-item>

      <el-form-item :label="$t('replacementDialog.content')" prop="content" class="content-item">
        <div class="content-wrapper">
          <el-input
            type="textarea"
            v-model="localForm.content"
            :placeholder="$t('replacementDialog.contentPlaceholder')"
            :rows="8"
            @input="clearFieldError('content')"
          ></el-input>
          <p class="format-tip">{{ $t('replacementDialog.formatTip') }}</p>
          <div class="upload-section">
            <el-upload
              class="upload-btn"
              action=""
              :auto-upload="false"
              :show-file-list="false"
              accept=".txt"
              :on-change="handleFileChange"
            >
              <el-button size="small" type="primary" class="upload-file-btn">
                <div class="upload-file-content">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 4px;">
                    <path d="M7 1V13M1 7H13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                  <div>
                    <p>{{ $t('replacementDialog.clickUploadTip') }}</p>
                    <p>{{ $t('replacementDialog.uploadCoverTip') }}</p>
                  </div>
                </div>
              </el-button>
            </el-upload>
            <span class="word-count" :class="{ 'over-limit': isOverLimit }">
              {{ wordCountText }}{{ $t('replacementDialog.wordCountUnit') }}
            </span>
          </div>
        </div>
      </el-form-item>
    </el-form>
  </CustomDialog>
</template>

<script>
import CustomDialog from './CustomDialog.vue';

export default {
  components: {
    CustomDialog
  },
  props: {
    title: {
      type: String,
      default: '新增替换词'
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: undefined,
        fileName: '',
        content: ''
      })
    }
  },
  data() {
    const MAX_WORD_COUNT = 4000;

    const validateContent = (rule, value, callback) => {
      if (!value || !value.trim()) {
        callback(new Error(this.$t('replacementDialog.requiredContent')));
        return;
      }

      const lines = this.getValidLines(value);
      const lineCount = lines.length;

      if (lineCount > MAX_WORD_COUNT) {
        callback(new Error(this.$t('replacementDialog.maxWordCountExceeded', { max: MAX_WORD_COUNT })));
        return;
      }

      for (let i = 0; i < lines.length; i++) {
        const pipeCount = (lines[i].match(/\|/g) || []).length;
        if (pipeCount !== 1) {
          callback(new Error(this.$t('replacementDialog.invalidPipeCount', { line: i + 1 })));
          return;
        }
        const parts = lines[i].split('|');
        if (!parts[0] || !parts[0].trim()) {
          callback(new Error(this.$t('replacementDialog.emptyOriginal', { line: i + 1 })));
          return;
        }
        if (!parts[1] || !parts[1].trim()) {
          callback(new Error(this.$t('replacementDialog.emptyReplacement', { line: i + 1 })));
          return;
        }
        const specialCharRegex = /[!@#$%^&*()_+=\[\]{};':"\\<>?\/`~]/;
        if (specialCharRegex.test(parts[0])) {
          callback(new Error(this.$t('replacementDialog.invalidOriginalChar', { line: i + 1 })));
          return;
        }
        if (specialCharRegex.test(parts[1])) {
          callback(new Error(this.$t('replacementDialog.invalidReplacementChar', { line: i + 1 })));
          return;
        }
      }
      callback();
    };

    return {
      dialogKey: Date.now(),
      saving: false,
      localForm: {
        id: undefined,
        fileName: '',
        content: ''
      },
      maxWordCount: MAX_WORD_COUNT,
      rules: {
        fileName: [
          { required: true, message: this.$t('replacementDialog.requiredFileName'), trigger: "blur" }
        ],
        content: [
          { required: true, validator: validateContent, trigger: "blur" }
        ]
      }
    };
  },
  computed: {
    wordCount() {
      if (!this.localForm.content) return 0;
      const contentStr = Array.isArray(this.localForm.content)
        ? this.localForm.content.join('\n')
        : this.localForm.content;
      if (!contentStr.trim()) {
        return 0;
      }
      const lines = this.getValidLines();
      return lines.filter(line => line.includes('|')).length;
    },

    isOverLimit() {
      return this.wordCount > this.maxWordCount;
    },

    wordCountText() {
      return `${this.wordCount} / ${this.maxWordCount}`;
    }
  },
  methods: {
    getValidLines() {
      if (!this.localForm.content) return [];
      const contentStr = Array.isArray(this.localForm.content) 
        ? this.localForm.content.join('\n') 
        : this.localForm.content;
      return contentStr.split(/\r?\n/).filter(line => line.trim());
    },

    clearFieldError(field) {
      if (this.$refs.form) {
        this.$refs.form.clearValidate(field);
      }
    },

    handleFileChange(file) {
      if (!file) return;

      const rawFile = file.raw;
      if (!rawFile) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        this.localForm.content = content;

        const lines = this.getValidLines(content);
        if (lines.length > this.maxWordCount) {
          this.$message.warning(
            this.$t('replacementDialog.maxWordCountExceeded', { max: this.maxWordCount })
          );
        }

        this.$nextTick(() => {
          if (this.$refs.form) {
            this.$refs.form.clearValidate('content');
          }
        });
      };
      reader.onerror = () => {
        this.$message.error(this.$t('replacementDialog.readFileError'));
      };
      reader.readAsText(rawFile);
    },

    submit() {
      this.$refs.form.validate((valid) => {
        if (valid) {
          if (this.isOverLimit) {
            this.$message.error(
              this.$t('replacementDialog.maxWordCountExceeded', { max: this.maxWordCount })
            );
            return;
          }

          const submitData = {
            id: this.localForm.id,
            fileName: this.localForm.fileName,
            content: this.getValidLines()
          };
          this.saving = true;
          this.$emit('submit', submitData);
        }
      });
    },

    cancel() {
      this.saving = false;
      this.dialogKey = Date.now();
      this.$emit('cancel');
    },

    resetSaving() {
      this.saving = false;
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.localForm.id = this.form.id;
        this.localForm.fileName = this.form.fileName || '';
        const contentData = this.form.content;
        this.localForm.content = Array.isArray(contentData) ? contentData.join('\n') : (contentData || '');
        this.$nextTick(() => {
          if (this.$refs.form) {
            this.$refs.form.clearValidate();
          }
        });
      } else {
        this.saving = false;
      }
    }
  }
};
</script>

<style scoped lang="scss">
.param-dialog-wrapper {
  .param-form {
    .content-item {
      :deep(.el-form-item__content) {
        line-height: 1;
      }
    }

    .content-wrapper {
      width: 100%;
    }

    .format-tip {
      text-align: left;
      font-size: 12px;
      color: #5778ff;
    }

    .upload-section {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 12px;
    }

    .upload-btn {
      display: inline-block;
    }

    .upload-file-btn {
      background: #3b82f6;
      border-color: #3b82f6;
      border-radius: 6px;
      font-size: 13px;
      padding: 8px 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      .upload-file-content {
        display: flex;
        flex-direction: row;
        align-items: center;
        > div {
          text-align: left;
          > p {
            margin: 4px;
          }
        }
      }

      &:hover {
        background: #2563eb;
        border-color: #2563eb;
        transform: translateY(-1px);
      }
    }

    .word-count {
      font-size: 13px;
      color: #64748b;
      font-weight: 500;
      transition: color 0.3s ease;

      &.over-limit {
        color: #ef4444;
        font-weight: 600;
      }
    }
  }
}
</style>
