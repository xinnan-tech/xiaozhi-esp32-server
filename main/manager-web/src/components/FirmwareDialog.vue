<template>
  <el-dialog :title="title" :visible.sync="dialogVisible" @close="handleClose" @open="handleOpen">
    <el-form ref="form" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="固件名称" prop="firmwareName">
        <el-input v-model="form.firmwareName" placeholder="请输入固件名称(板子+版本号)"></el-input>
      </el-form-item>
      <el-form-item label="固件类型" prop="type">
        <el-select v-model="form.type" placeholder="请选择固件类型" style="width: 100%;" filterable :disabled="isTypeDisabled">
          <el-option v-for="item in firmwareTypes" :key="item.key" :label="item.name" :value="item.key"></el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="版本号" prop="version">
        <el-input v-model="form.version" placeholder="请输入版本号(x.x.x格式)"></el-input>
      </el-form-item>
      <el-form-item label="固件文件" prop="firmwarePath">
        <el-upload ref="upload" class="upload-demo" action="#" :http-request="handleUpload"
          :before-upload="beforeUpload" :accept="'.bin,.apk'" :limit="1" :multiple="false" :auto-upload="true"
          :on-remove="handleRemove">
          <el-button size="small" type="primary">点击上传</el-button>
          <div slot="tip" class="el-upload__tip">只能上传固件文件(.bin/.apk)，且不超过100MB</div>
        </el-upload>
        <el-progress v-if="isUploading || uploadStatus === 'success'" :percentage="uploadProgress"
          :status="uploadStatus"></el-progress>
        <div class="hint-text">
          <span>温馨提示：请上传合并前的xiaozhi.bin文件，而不是合并后的merged-binary.bin文件</span>
        </div>
      </el-form-item>
      <el-form-item label="备注" prop="remark">
        <el-input type="textarea" v-model="form.remark" placeholder="请输入备注信息"></el-input>
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleCancel">取 消</el-button>
      <el-button type="primary" @click="handleSubmit">确 定</el-button>
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
          { required: true, message: '请输入固件名称(板子+版本号)', trigger: 'blur' }
        ],
        type: [
          { required: true, message: '请选择固件类型', trigger: 'change' }
        ],
        version: [
          { required: true, message: '请输入版本号', trigger: 'blur' },
          { pattern: /^\d+\.\d+\.\d+$/, message: '版本号格式不正确，请输入x.x.x格式', trigger: 'blur' }
        ],
        firmwarePath: [
          { required: false, message: '请上传固件文件', trigger: 'change' }
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
            this.$message.error('请上传固件文件')
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
        this.$message.error('只能上传.bin/.apk格式的固件文件!')
        return false
      }
      if (!isValidSize) {
        this.$message.error('固件文件大小不能超过100MB!')
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
          this.$message.success('固件文件上传成功')
          // 延迟2秒后隐藏进度条
          setTimeout(() => {
            this.isUploading = false
          }, 2000)
        } else {
          this.uploadStatus = 'exception'
          this.$message.error(res.msg || '文件上传失败')
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
        // 重置上传组件
        this.$nextTick(() => {
          if (this.$refs.upload) {
            this.$refs.upload.clearFiles()
          }
        })
      }
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