<template>
  <el-dialog :title="title" :visible.sync="visible" width="500px" @close="handleClose">
    <el-form ref="form" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="固件名称" prop="firmwareName">
        <el-input v-model="form.firmwareName" placeholder="请输入固件名称"></el-input>
      </el-form-item>
      <el-form-item label="固件类型" prop="type">
        <el-input v-model="form.type" placeholder="请输入固件类型"></el-input>
      </el-form-item>
      <el-form-item label="版本号" prop="version">
        <el-input v-model="form.version" placeholder="请输入版本号"></el-input>
      </el-form-item>
      <el-form-item label="固件文件" prop="firmwarePath">
        <el-upload
          class="upload-demo"
          action="#"
          :http-request="handleUpload"
          :before-upload="beforeUpload"
          :accept="'.bin,.hex,.elf'"
          :limit="1"
          :multiple="false"
          :auto-upload="true">
          <el-button size="small" type="primary">点击上传</el-button>
          <div slot="tip" class="el-upload__tip">只能上传固件文件(.bin/.hex/.elf)，且不超过100MB</div>
        </el-upload>
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
import Api from '@/apis/api'

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
    }
  },
  data() {
    return {
      rules: {
        firmwareName: [
          { required: true, message: '请输入固件名称', trigger: 'blur' }
        ],
        type: [
          { required: true, message: '请输入固件类型', trigger: 'blur' }
        ],
        version: [
          { required: true, message: '请输入版本号', trigger: 'blur' }
        ],
        firmwarePath: [
          { required: false, message: '请上传固件文件', trigger: 'change' }
        ]
      }
    }
  },
  methods: {
    handleClose() {
      this.$refs.form.clearValidate();
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
      const isValidType = ['.bin', '.hex', '.elf'].some(ext => file.name.toLowerCase().endsWith(ext))
      
      if (!isValidType) {
        this.$message.error('只能上传.bin/.hex/.elf格式的固件文件!')
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
      Api.ota.uploadFirmware(file, (res) => {
        res = res.data
        if (res.code === 0) {
          this.form.firmwarePath = res.data
          this.form.size = file.size
          this.$message.success('固件文件上传成功')
        } else {
          this.$message.error(res.msg || '文件上传失败')
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.upload-demo {
  text-align: left;
}
.el-upload__tip {
  line-height: 1.2;
  padding-top: 5px;
  color: #909399;
}
</style>