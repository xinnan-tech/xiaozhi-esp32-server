<template>
  <el-dialog :title="title" :visible.sync="visible" width="60%" @close="handleClose">
    <el-form ref="templateForm" :model="templateData" label-width="120px" :rules="rules">
      <el-form-item label="模板名称" prop="agentName">
        <el-input v-model="templateData.agentName" placeholder="请输入模板名称" />
      </el-form-item>
      <el-form-item label="语言编码" prop="langCode">
        <el-input v-model="templateData.langCode" placeholder="请输入语言编码，如zh-CN" />
      </el-form-item>
      <el-form-item label="交互语种" prop="language">
        <el-input v-model="templateData.language" placeholder="请输入交互语种，如中文" />
      </el-form-item>
      <el-form-item label="排序" prop="sort">
        <el-input-number v-model="templateData.sort" :min="0" placeholder="请输入排序值" />
      </el-form-item>
      <el-form-item label="聊天记录配置">
        <el-select v-model="templateData.chatHistoryConf" placeholder="请选择聊天记录配置">
          <el-option label="不记录" :value="0" />
          <el-option label="仅记录文本" :value="1" />
          <el-option label="记录文本和语音" :value="2" />
        </el-select>
      </el-form-item>
      <el-form-item label="角色设定参数" prop="systemPrompt">
        <el-input v-model="templateData.systemPrompt" type="textarea" placeholder="请输入角色设定参数" :rows="4" />
        <div class="form-tip">角色设定参数将作为智能体的系统提示，定义智能体的行为和回答风格</div>
      </el-form-item>
      <el-form-item label="总结记忆" prop="summaryMemory">
        <el-input v-model="templateData.summaryMemory" type="textarea" placeholder="请输入总结记忆" :rows="4" />
        <div class="form-tip">总结记忆将作为智能体的初始记忆，帮助智能体理解上下文</div>
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSave">确定</el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'AgentTemplateDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: ''
    },
    templateData: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      // 表单验证规则
      rules: {
        agentName: [
          { required: true, message: '请输入模板名称', trigger: 'blur' },
          { min: 2, max: 50, message: '模板名称长度在 2 到 50 个字符', trigger: 'blur' }
        ],
        langCode: [
          { required: true, message: '请输入语言编码', trigger: 'blur' }
        ],
        language: [
          { required: true, message: '请输入交互语种', trigger: 'blur' }
        ],
        systemPrompt: [
          { required: true, message: '请输入角色设定参数', trigger: 'blur' },
          { min: 10, message: '角色设定参数至少需要 10 个字符', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    // 处理关闭对话框
    handleClose() {
      this.$emit('update:visible', false)
    },
    
    // 处理保存模板
    handleSave() {
      this.$refs.templateForm.validate((valid) => {
        if (valid) {
          this.$emit('save', this.templateData)
        }
      })
    }
  }
}
</script>

<style scoped>
.form-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 5px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>