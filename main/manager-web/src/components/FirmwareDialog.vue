<template>
  <el-dialog :title="title" :visible.sync="dialogVisible" :close-on-click-modal="false" @close="handleClose" @open="handleOpen">
    <el-form ref="form" :model="form" :rules="rules" label-width="auto">
      <el-form-item :label="$t('firmwareDialog.firmwareName')" prop="firmwareName">
        <el-input v-model="form.firmwareName" :placeholder="$t('firmwareDialog.firmwareNamePlaceholder')"></el-input>
      </el-form-item>
      <el-form-item :label="$t('firmwareDialog.firmwareType')" prop="type">
        <el-select v-model="form.type" :placeholder="$t('firmwareDialog.firmwareTypePlaceholder')" style="width: 100%;" filterable :disabled="isTypeDisabled">
          <el-option v-for="item in firmwareTypes" :key="item.key" :label="item.name" :value="item.key"></el-option>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('firmwareDialog.version')" prop="version">
        <el-input v-model="form.version" :placeholder="$t('firmwareDialog.versionPlaceholder')"></el-input>
      </el-form-item>
      <el-form-item :label="$t('firmwareDialog.firmwareFile')" prop="firmwarePath">
        <el-upload ref="upload" class="upload-demo" action="#" :http-request="handleUpload"
          :before-upload="beforeUpload" :accept="'.bin,.apk'" :limit="1" :multiple="false" :auto-upload="true"
          :on-remove="handleRemove">
          <el-button size="small" type="primary">{{ $t('firmwareDialog.clickUpload') }}</el-button>
          <div slot="tip" class="el-upload__tip">{{ $t('firmwareDialog.uploadTip') }}</div>
        </el-upload>
        <el-progress v-if="isUploading || uploadStatus === 'success'" :percentage="uploadProgress"
          :status="uploadStatus"></el-progress>
        <div class="hint-text">
          <span>{{ $t('firmwareDialog.uploadHint') }}</span>
        </div>
      </el-form-item>
      <el-form-item :label="$t('firmwareDialog.remark')" prop="remark">
        <el-input type="textarea" v-model="form.remark" :placeholder="$t('firmwareDialog.remarkPlaceholder')"></el-input>
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleCancel">{{ $t('button.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('button.save') }}</el-button>
    </div>
  </el-dialog>
</template>

<script>
import Api from '@/apis/api';

export default {
  name: 'FirmwareDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: ''
    },
    form: {
      type: Object,
      default: () => ({})
    },
    firmwareTypes: {
      type: Array,
      default: () => []
    }
  },

  data() {
    return {
      uploadProgress: 0,
      uploadStatus: '',
      isUploading: false,
      dialogVisible: this.visible,
      rules: {
        firmwareName: [
          { required: true, message: this.$t('firmwareDialog.requiredFirmwareName'), trigger: 'blur' }
        ],
        type: [
          { required: true, message: this.$t('firmwareDialog.requiredFirmwareType'), trigger: 'change' }
        ],
        version: [
          { required: true, message: this.$t('firmwareDialog.requiredVersion'), trigger: 'blur' },
          { pattern: /^\d+\.\d+\.\d+$/, message: this.$t('firmwareDialog.versionFormatError'), trigger: 'blur' }
        ],
        firmwarePath: [
          { required: false, message: this.$t('firmwareDialog.requiredFirmwareFile'), trigger: 'change' }
        ]
      }
    }
  },
  computed: {
    isTypeDisabled() {
      // 如果有id，说明是编辑模式，禁用类型选择
      return !!this.form.id
    }
  },
  created() {
    // 移除 getDictDataByType 调用
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
    },
    dialogVisible(val) {
      this.$emit('update:visible', val);
    },
  },
  methods: {
    // 移除 getFirmwareTypes 方法
    handleClose() {
      this.dialogVisible = false;
      this.$emit('cancel');
    },
    handleCancel() {
      this.$refs.form.clearValidate();
      this.$emit('cancel');
    },
    handleSubmit() {
      this.$refs.form.validate(valid => {
        if (valid) {
          // 如果是新增模式且没有上传文件，则提示错误
          if (!this.form.id && !this.form.firmwarePath) {
            this.$message.error(this.$t('firmwareDialog.requiredFirmwareFile'))
            return
          }
          // 提交成功后将关闭对话框的逻辑交给父组件处理
          this.$emit('submit', this.form)
        }
      })
    },
    beforeUpload(file) {
      const isValidSize = file.size / 1024 / 1024 < 100
      const isValidType = ['.bin', '.apk'].some(ext => file.name.toLowerCase().endsWith(ext))

      if (!isValidType) {
          this.$message.error(this.$t('firmwareDialog.invalidFileType'))
          return false
        }
        if (!isValidSize) {
          this.$message.error(this.$t('firmwareDialog.invalidFileSize'))
          return false
        }
      return true
    },
    handleUpload(options) {
      const { file } = options
      this.uploadProgress = 0
      this.uploadStatus = ''
      this.isUploading = true

      // 使用setTimeout实现简单的0-50%过渡
      const timer = setTimeout(() => {
        if (this.uploadProgress < 50) {  // 只有当进度小于50%时才设置
          this.uploadProgress = 50
        }
      }, 1000)

      Api.ota.uploadFirmware(file, (res) => {
        clearTimeout(timer)  // 清除定时器
        res = res.data
        if (res.code === 0) {
          this.form.firmwarePath = res.data
          this.form.size = file.size
          this.uploadProgress = 100
          this.uploadStatus = 'success'
          this.$message.success(this.$t('firmwareDialog.uploadSuccess'))
          // 延迟2秒后隐藏进度条
          setTimeout(() => {
            this.isUploading = false
          }, 2000)
        } else {
          this.uploadStatus = 'exception'
          this.$message.error(res.msg || this.$t('firmwareDialog.uploadFailed'))
          this.isUploading = false
        }
      }, (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          // 只有当进度大于50%时才更新
          if (progress > 50) {
            this.uploadProgress = progress
          }
          // 如果上传完成但还没收到成功响应，保持进度条显示
          if (progress === 100) {
            this.uploadStatus = ''
          }
        }
      })
    },
    handleRemove() {
      this.form.firmwarePath = ''
      this.form.size = 0
      this.uploadProgress = 0
      this.uploadStatus = ''
      this.isUploading = false
    },
    handleOpen() {
      // 重置上传相关状态
      this.uploadProgress = 0
      this.uploadStatus = ''
      this.isUploading = false
      // 重置表单中的文件相关字段
      if (!this.form.id) {  // 只在新增时重置
        this.form.firmwarePath = ''
        this.form.size = 0
      }
      // 无论是否编辑模式，都重置上传组件
      this.$nextTick(() => {
        if (this.$refs.upload) {
          this.$refs.upload.clearFiles()
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
::v-deep .el-dialog {
  border-radius: 20px;
}

.upload-demo {
  text-align: left;
}

.el-upload__tip {
  line-height: 1.2;
  padding-top: 2%;
  color: #909399;
}

.hint-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
</style>