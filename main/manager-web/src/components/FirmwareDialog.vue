<template>
  <el-dialog :title="title" :visible.sync="dialogVisible" :close-on-click-modal="false" @close="handleClose" @open="handleOpen">
    <el-form ref="form" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="Firmware Name" prop="firmwareName">
        <el-input v-model="form.firmwareName" placeholder="Enter firmware name (board + version)"></el-input>
      </el-form-item>
      <el-form-item label="Firmware Type" prop="type">
        <el-select v-model="form.type" placeholder="Select firmware type" style="width: 100%;" filterable :disabled="isTypeDisabled">
          <el-option v-for="item in firmwareTypes" :key="item.key" :label="item.name" :value="item.key"></el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="Version" prop="version">
        <el-input v-model="form.version" placeholder="Enter version (x.x.x format)"></el-input>
      </el-form-item>
      <el-form-item label="Firmware File" prop="firmwarePath">
        <el-upload ref="upload" class="upload-demo" action="#" :http-request="handleUpload"
          :before-upload="beforeUpload" :accept="'.bin,.apk'" :limit="1" :multiple="false" :auto-upload="true"
          :on-remove="handleRemove">
          <el-button size="small" type="primary">Click to Upload</el-button>
          <div slot="tip" class="el-upload__tip">Only firmware files (.bin/.apk) are allowed, max 100MB</div>
        </el-upload>
        <el-progress v-if="isUploading || uploadStatus === 'success'" :percentage="uploadProgress"
          :status="uploadStatus"></el-progress>
        <div class="hint-text">
          <span>Note: Please upload the original xiaozhi.bin file, not the merged-binary.bin file</span>
        </div>
      </el-form-item>
      <el-form-item label="Remarks" prop="remark">
        <el-input type="textarea" v-model="form.remark" placeholder="Enter remarks"></el-input>
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleCancel">Cancel</el-button>
      <el-button type="primary" @click="handleSubmit">Confirm</el-button>
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
          { required: true, message: 'Please enter firmware name (board + version)', trigger: 'blur' }
        ],
        type: [
          { required: true, message: 'Please select firmware type', trigger: 'change' }
        ],
        version: [
          { required: true, message: 'Please enter version number', trigger: 'blur' },
          { pattern: /^\d+\.\d+\.\d+$/, message: 'Invalid version format, please enter x.x.x format', trigger: 'blur' }
        ],
        firmwarePath: [
          { required: false, message: 'Please upload firmware file', trigger: 'change' }
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
          // If in add mode and no file uploaded, show error
          if (!this.form.id && !this.form.firmwarePath) {
            this.$message.error('Please upload firmware file')
            return
          }
          // Let parent component handle dialog closing logic after successful submission
          this.$emit('submit', this.form)
        }
      })
    },
    beforeUpload(file) {
      const isValidSize = file.size / 1024 / 1024 < 100
      const isValidType = ['.bin', '.apk'].some(ext => file.name.toLowerCase().endsWith(ext))

      if (!isValidType) {
        this.$message.error('Only .bin/.apk firmware files are allowed!')
        return false
      }
      if (!isValidSize) {
        this.$message.error('Firmware file size cannot exceed 100MB!')
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
          this.$message.success('Firmware file uploaded successfully')
          // Hide progress bar after 2 seconds
          setTimeout(() => {
            this.isUploading = false
          }, 2000)
        } else {
          this.uploadStatus = 'exception'
          this.$message.error(res.msg || 'File upload failed')
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