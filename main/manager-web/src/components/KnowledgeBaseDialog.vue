<template>
  <el-dialog :title="title" :visible="dialogVisible" width="600px" class="knowledge-base-dialog" @close="handleClose">
    <el-form ref="knowledgeBaseForm" :model="form" :rules="rules" label-width="100px" size="medium">
      <el-form-item :label="$t('knowledgeBaseDialog.name')" prop="name">
        <el-input v-model="form.name" :placeholder="$t('knowledgeBaseDialog.namePlaceholder')" clearable></el-input>
      </el-form-item>
      <el-form-item :label="$t('knowledgeBaseDialog.description')" prop="description">
        <el-input v-model="form.description" :placeholder="$t('knowledgeBaseDialog.descriptionPlaceholder')"
          type="textarea" :rows="4" maxlength="300" show-word-limit></el-input>
      </el-form-item>
      <el-form-item :label="$t('knowledgeBaseDialog.ragModel')" prop="ragModelId">
        <el-select v-model="form.ragModelId" :placeholder="$t('knowledgeBaseDialog.ragModelPlaceholder')" clearable
          filterable style="width: 100%" @focus="loadRAGModels">
          <el-option v-for="model in ragModels" :key="model.id" :label="model.modelName" :value="model.id">
          </el-option>
        </el-select>
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose">{{ $t('knowledgeBaseDialog.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('knowledgeBaseDialog.confirm') }}</el-button>
    </div>
  </el-dialog>
</template>

<script>
import Api from "@/apis/api";

export default {
  name: "KnowledgeBaseDialog",
  props: {
    title: {
      type: String,
      default: ""
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        datasetId: null,
        ragModelId: null,
        name: "",
        description: ""
      })
    }
  },
  data() {
    return {
      dialogVisible: this.visible,
      ragModels: [],
      rules: {
        name: [
          {
            required: true,
            message: this.$t("knowledgeBaseDialog.nameRequired"),
            trigger: "blur"
          },
          {
            min: 1,
            max: 50,
            message: this.$t("knowledgeBaseDialog.nameLength"),
            trigger: "blur"
          },
          {
            pattern: /^[\u4e00-\u9fa5a-zA-Z0-9\s-_]+$/,
            message: this.$t("knowledgeBaseDialog.namePattern"),
            trigger: "blur"
          }
        ],
        description: [
          {
            required: true,
            message: this.$t("knowledgeBaseDialog.descriptionRequired"),
            trigger: "blur"
          },
          {
            max: 300,
            message: this.$t("knowledgeBaseDialog.descriptionLength"),
            trigger: "blur"
          }
        ],
        ragModelId: [
          {
            required: true,
            message: this.$t("knowledgeBaseDialog.ragModelRequired"),
            trigger: "change"
          }
        ]
      }
    };
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
      if (val) {
        // 对话框显示时加载RAG模型列表
        this.loadRAGModels();

        // 如果是新增知识库且没有设置ragModelId，则默认选择第一个RAG模型
        if (!this.form.id && !this.form.ragModelId && this.ragModels.length > 0) {
          this.$set(this.form, 'ragModelId', this.ragModels[0].id);
        }

        if (this.$refs.knowledgeBaseForm) {
          this.$refs.knowledgeBaseForm.clearValidate();
        }
      }
    },
    // 监听RAG模型列表变化，确保新增时能正确设置默认值
    ragModels(newModels) {
      if (newModels.length > 0) {
        // 如果是新增知识库且没有设置ragModelId，则默认选择第一个RAG模型
        if (!this.form.id && !this.form.ragModelId) {
          this.$set(this.form, 'ragModelId', newModels[0].id);
        }
      }
    }
  },
  methods: {
    handleClose() {
      // 不重置表单字段，以便在编辑时能保留之前的选择
      // 只在对话框关闭时重置验证状态
      if (this.$refs.knowledgeBaseForm) {
        this.$refs.knowledgeBaseForm.clearValidate();
      }
      this.dialogVisible = false;
      this.$emit("update:visible", false);
    },
    handleSubmit() {
      console.log('KnowledgeBaseDialog handleSubmit called');
      this.$refs.knowledgeBaseForm.validate(valid => {
        console.log('Form validation result:', valid);
        if (valid) {
          console.log('Emitting submit event with form:', this.form);
          this.$emit("submit", {
            ...this.form
          });
        }
      });
    },
    loadRAGModels() {
      if (this.ragModels.length > 0) {
        return; // 已经加载过，避免重复加载
      }

      console.log('开始加载RAG模型列表');
      Api.model.getRAGModels((res) => {
        console.log('RAG模型列表响应:', res);
        if (res.data && res.data.code === 0) {
          this.ragModels = res.data.data || [];
          console.log('RAG模型列表加载成功，共', this.ragModels.length, '个模型');

          // 如果是新增知识库且没有设置ragModelId，则默认选择第一个RAG模型
          if (!this.form.id && !this.form.ragModelId && this.ragModels.length > 0) {
            this.$set(this.form, 'ragModelId', this.ragModels[0].id);
            console.log('已设置默认RAG模型:', this.ragModels[0].id);
          }
        } else {
          console.error('获取RAG模型列表失败:', res.data?.msg);
          this.$message.error(this.$t('knowledgeBaseDialog.loadRAGModelsFailed'));
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.knowledge-base-dialog {
  ::v-deep .el-dialog {
    border-radius: 20px;
    overflow: hidden;
  }

  ::v-deep .el-dialog__body {
    padding: 20px 30px;
  }

  ::v-deep .el-form-item {
    margin-bottom: 20px;
  }

  ::v-deep .el-form-item__label {
    font-weight: 500;
    color: #34495e;
    font-size: 14px;
  }

  ::v-deep .el-input {
    .el-input__inner {
      height: 36px;
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  ::v-deep .el-textarea {
    .el-textarea__inner {
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  ::v-deep .el-select {
    .el-input__inner {
      height: 36px;
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>