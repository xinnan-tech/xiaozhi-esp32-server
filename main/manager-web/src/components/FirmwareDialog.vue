<template>
  <el-dialog :title="title" :visible.sync="dialogVisible" :close-on-click-modal="false" @close="handleClose" @open="handleOpen">
    <el-form ref="form" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="Firmware Name" prop="firmwareName">
        <el-input v-model="form.firmwareName" placeholder="Please enter firmware name (board + version)"></el-input>
      </el-form-item>
      <el-form-item label="Firmware Type" prop="type">
        <el-select v-model="form.type" placeholder="Please select firmware type" style="width: 100%;" filterable :disabled="isTypeDisabled">
          <el-option v-for="item in firmwareTypes" :key="item.key" :label="item.name" :value="item.key"></el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="Version" prop="version">
        <el-input v-model="form.version" placeholder="Please enter version (x.x.x format)"></el-input>
      </el-form-item>
      <el-form-item label="Firmware File" prop="firmwarePath">
        <el-upload ref="upload" class="upload-demo" action="#" :http-request="handleUpload"
          :before-upload="beforeUpload" :accept="'.bin,.apk'" :limit="1" :multiple="false" :auto-upload="true"
          :on-remove="handleRemove">
          <el-button size="small" type="primary">Click to Upload</el-button>
          <div slot="tip" class="el-upload__tip">Only firmware files (.bin/.apk) can be uploaded, and must not exceed 100MB</div>
        </el-upload>
        <el-progress v-if="isUploading || uploadStatus === 'success'" :percentage="uploadProgress"
          :status="uploadStatus"></el-progress>
        <div class="hint-text">
          <span>Warm Reminder: Please upload the pre-merge xiaozhi.bin file, not the post-merge merged-binary.bin file</span>
        </div>
      </el-form-item>
      <el-form-item label="Remarks" prop="remark">
        <el-input type="textarea" v-model="form.remark" placeholder="Please enter remarks information"></el-input>
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
          { required: true, message: 'Please enter version', trigger: 'blur' },
          { pattern: /^\d+\.\d+\.\d+$/, message: 'Incorrect version format, please enter x.x.x format', trigger: 'blur' }
        ],
        firmwarePath: [
          { required: false, message: 'Please upload firmware file', trigger: 'change' }
        ]
      }
    }
  },
  computed: {
    isTypeDisabled() {
      // If there is an id, it means edit mode, disable type selection
      return !!this.form.id
    }
  },
  created() {
    // Remove getDictDataByType call
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
    // Remove getFirmwareTypes method
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
          // If it's add mode and no file uploaded, show error
          if (!this.form.id && !this.form.firmwarePath) {
            this.$message.error('Please upload firmware file')
            return
          }
          // Leave closing dialog logic to parent component after successful submission
          this.$emit('submit', this.form)
        }
      })
    },
    beforeUpload(file) {
      const isValidSize = file.size / 1024 / 1024 < 100
      const isValidType = ['.bin', '.apk'].some(ext => file.name.toLowerCase().endsWith(ext))

      if (!isValidType) {
        this.$message.error('Only .bin/.apk format firmware files can be uploaded!')
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

      // Use setTimeout to implement simple 0-50% transition
      const timer = setTimeout(() => {
        if (this.uploadProgress < 50) {  // Only set when progress is less than 50%
          this.uploadProgress = 50
        }
      }, 1000)

      Api.ota.uploadFirmware(file, (res) => {
        clearTimeout(timer)  // Clear timer
        res = res.data
        if (res.code === 0) {
          this.form.firmwarePath = res.data
          this.form.size = file.size
          this.uploadProgress = 100
          this.uploadStatus = 'success'
          this.$message.success('Firmware file uploaded successfully')
          // Hide progress bar after 2 seconds delay
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
          // Only update when progress is greater than 50%
          if (progress > 50) {
            this.uploadProgress = progress
          }
          // If upload is complete but no success response yet, keep progress bar visible
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
      // Reset upload related states
      this.uploadProgress = 0
      this.uploadStatus = ''
      this.isUploading = false
      // Reset file related fields in form
      if (!this.form.id) {  // Only reset when adding new
        this.form.firmwarePath = ''
        this.form.size = 0
      }
      // Reset upload component regardless of edit mode
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