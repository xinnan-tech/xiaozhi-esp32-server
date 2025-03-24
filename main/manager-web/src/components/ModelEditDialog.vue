<template>
  <el-dialog :visible.sync="dialogVisible" width="800px" center>
    <el-form :model="form" ref="form" label-width="70px">
      <el-row :gutter="20" class="form-row">
        <el-col :span="12">
          <el-form-item label="模型编码">
            <el-input v-model="form.code" placeholder="请输入内容" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="模型名称">
            <el-input v-model="form.name" placeholder="请输入内容" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 供应商 -->
      <el-row :gutter="20" class="form-row">
        <el-col :span="12">
          <el-form-item label="供应器">
            <el-select v-model="form.supplier" placeholder="请选择">
              <el-option label="openai" value="openai" />
              <el-option label="dify" value="dify" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
           <el-form-item>
            <div style="display: flex; align-items: center;">
              <span class="el-form-item__label" style="width: 70px;">设成默认</span>
              <el-switch v-model="form.isDefault" style="margin-right: 20px;" />
              <span class="el-form-item__label" style="width: 70px;">是否启用</span>
              <el-switch v-model="form.isEnable" />
            </div>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 文档 -->
      <el-row :gutter="20" class="form-row">
        <el-col :span="12">
          <el-form-item label="文档地址">
            <el-input v-model="form.docUrl" placeholder="请输入内容" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排序号">
            <el-input-number v-model="form.sort" :min="1" :max="999" controls-position="right" placeholder="123"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 备注 -->
      <el-form-item label="备注" class="form-row">
        <el-input type="textarea" v-model="form.remark" :rows="2" placeholder="请输入"
        />
      </el-form-item>

      <div class="vertical-fields">
        <el-form-item label="接口地址">
          <el-input v-model="form.apiUrl" placeholder="请输入base_url" />
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="form.modelName" placeholder="请输入model_name" />
        </el-form-item>
        <el-form-item label="密钥信息">
          <el-input v-model="form.apiKey" placeholder="请输入api_key" show-password/>
        </el-form-item>
      </div>
    </el-form>

    <div slot="footer" class="dialog-footer">
      <el-button type="primary" @click="handleSave">保存</el-button>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: "ModelConfigDialog",
  props: {
    visible: { type: Boolean, default: false },
    configData: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      dialogVisible: this.visible,
      form: {
        code: "",
        name: "",
        supplier: "",
        isDefault: true,
        isEnable: true,
        docUrl: "",
        sort: 123,
        remark: "",
        apiUrl: "",
        modelName: "",
        apiKey: ""
      }
    };
  },
  watch: {
    dialogVisible(val) {
      this.$emit('update:visible', val);
    },
    visible(val) {
      this.dialogVisible = val;
      if (val) this.form = { ...this.form, ...this.configData };
    }
  },
  methods: {
    handleSave() {
      this.$emit("submit", this.form);
      this.dialogVisible = false;
    }
  }
};
</script>

<style scoped>
.dialog-footer {
  margin-top: -30px;
  text-align: center;
}
.el-form-item {
  margin-bottom: 18px;
}
.el-input-number {
  width: 100%;
}
.form-row {
  margin-bottom: 12px;
}

.vertical-fields {
  margin-top: 8px;
}

.dialog-footer {
  margin-top: -10px;
  text-align: center;
}
.el-input-number {
  width: 100%;
}

.el-input__inner {
  height: 36px;
  line-height: 36px;
}

.el-form-item__label {
  text-align: left;
  padding-right: 10px;
}
</style>
