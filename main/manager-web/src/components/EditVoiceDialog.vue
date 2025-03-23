<template>
  <el-dialog :visible.sync="dialogVisible" width="900px" @close="handleClose" class="compact-dialog" :append-to-body="true">
    <el-form :model="voiceForm" :rules="rules" ref="voiceForm" label-width="80px">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="音色编码" prop="voiceCode">
            <el-input v-model="voiceForm.voiceCode" placeholder="请输入内容" class="compact-input"></el-input>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="音色名称" prop="voiceName">
            <el-input v-model="voiceForm.voiceName" placeholder="请输入内容" class="compact-input"></el-input>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="语言类型" prop="languageType">
            <el-input v-model="voiceForm.languageType" placeholder="请输入内容" class="compact-input"></el-input>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排序号" prop="sortNumber">
            <el-input-number v-model="voiceForm.sortNumber" :min="1" :controls="false" class="compact-number"></el-input-number>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="备注" prop="remark">
        <el-input v-model="voiceForm.remark" type="textarea" :rows="2" placeholder="请输入内容" class="compact-textarea"
        ></el-input>
        <div class="audio-controls">
           <div class="audio-player">
      <audio
        :src="audioUrl"
        controls
        preload="metadata"
        class="custom-audio"
      ></audio>
    </div>
          <el-button type="primary" size="mini" class="preview-btn">生成试听</el-button>
        </div>
      </el-form-item>
    </el-form>

    <div slot="footer" class="dialog-footer">
      <el-button type="primary" @click="handleSave">保存</el-button>
      <el-button type="primary" @click="handleClose">关闭</el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'EditVoiceDialog',
  props: {
    showDialog: Boolean,
    voiceData: {
      type: Object,
      default: () => ({
        voiceCode: 'wawaxiaohe',
        voiceName: '湾湾小何',
        languageType: '中文',
        sortNumber: 123
      })
    }
  },
  data() {
    return {
      dialogVisible: this.showDialog,
      voiceForm: { ...this.voiceData },
      audioUrl: 'http://music.163.com/song/media/outer/url?id=447925558.mp3',
      generatedAudio: null,
      rules: {
        voiceCode: [{ required: true, message: '请输入音色编码', trigger: 'blur' }],
        voiceName: [{ required: true, message: '请输入音色名称', trigger: 'blur' }]
      }
    }
  },
  watch: {
    showDialog(newVal) {
      this.dialogVisible = newVal
      if (newVal) this.voiceForm = { ...this.voiceData }
    }
  },
  methods: {
    handleClose() {
      this.dialogVisible = false
      this.$emit('update:showDialog', false)
    },
    handleSave() {
      this.$refs.voiceForm.validate(valid => {
        if (valid) this.$emit('save', this.voiceForm)
      })
    },
  }
}
</script>

<style scoped>
.compact-dialog {
  /deep/ .el-dialog__body {
    padding: 20px;
  }

  .el-form-item {
    margin-bottom: 16px;
  }

  .compact-input {
    width: 100%;
  }

  .compact-number {
    width: 100%;
    /deep/ .el-input__inner {
      padding-right: 10px;
    }
  }

  .compact-textarea {
    width: 100%;
    margin-bottom: 8px;
  }

  .audio-controls {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 16px;
    margin-top: 8px;


    .preview-btn {
      padding: 7px 15px;
    }
  }

  .dialog-footer {
    padding: 16px 20px 0;
    text-align: right;
    border-top: 1px solid #EBEEF5;

    .el-button {
      min-width: 80px;
    }
  }
}
</style>
