<template>
  <el-dialog
      :visible.sync="visible"
      width="975px"
      center
      custom-class="custom-dialog"
      :show-close="false"
      class="center-dialog"

  >
    <div style="margin: 0 18px; text-align: left; padding: 10px; border-radius: 10px;">
      <div style="font-size: 30px; color: #3d4566; margin-top: -10px; margin-bottom: 10px; text-align: center;">
        添加模型
      </div>

      <!-- 关闭按钮 -->
      <button class="custom-close-btn" @click="handleClose">
        ×
      </button>

      <!-- 模型信息部分 -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <div style="font-size: 20px; font-weight: bold; color: #3d4566;">模型信息</div>
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="display: flex; align-items: center;">
            <span style="margin-right: 8px;">是否启用</span>
            <el-switch v-model="formData.isEnabled" class="custom-switch"></el-switch>
          </div>
          <div style="display: flex; align-items: center;">
            <span style="margin-right: 8px;">设为默认</span>
            <el-switch v-model="formData.isDefault" class="custom-switch"></el-switch>
          </div>
        </div>
      </div>

      <div style="height: 2px; background: #e9e9e9; margin-bottom: 22px;"></div>

      <el-form :model="formData" label-width="100px" label-position="left" class="custom-form">
        <!-- 第一行：模型名称和模型编码 -->
        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="模型名称" prop="modelName" style="flex: 1;">
            <el-input
                v-model="formData.modelName"
                placeholder="请输入模型名称"
                class="custom-input-bg"
            ></el-input>
          </el-form-item>
          <el-form-item label="模型编码" prop="modelCode" style="flex: 1;">
            <el-input
                v-model="formData.modelCode"
                placeholder="请输入模型编码"
                class="custom-input-bg"
            ></el-input>
          </el-form-item>
        </div>

        <!-- 第二行：供应器和排序号 -->
        <div style="display: flex; gap: 20px; margin-bottom: 0;">
          <el-form-item label="供应器" prop="supplier" style="flex: 1;">
            <el-select
                v-model="formData.supplier"
                placeholder="请选择"
                class="custom-select custom-input-bg"
                style="width: 100%;"
            >
              <el-option label="硅基流动" value="硅基流动"></el-option>
              <el-option label="智脑科技" value="智脑科技"></el-option>
              <el-option label="云智科技" value="云智科技"></el-option>
              <el-option label="其他" value="其他"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="排序号" prop="sortOrder" style="flex: 1;">
            <el-input
                v-model="formData.sort"
                placeholder="请输入排序号"
                class="custom-input-bg"
            ></el-input>
          </el-form-item>
        </div>

        <!-- 文档地址 -->
        <el-form-item label="文档地址" prop="docLink" style="margin-bottom: 27px;">
          <el-input
              v-model="formData.docLink"
              placeholder="请输入文档地址"
              class="custom-input-bg"
          ></el-input>
        </el-form-item>

        <!-- 备注 -->
        <el-form-item label="备注" prop="remark" class="prop-remark">
          <el-input
              v-model="formData.remark"
              type="textarea"
              :rows="3"
              placeholder="请输入模型备注"
              class="custom-input-bg"
          ></el-input>
        </el-form-item>
      </el-form>

      <!-- 调用信息部分 -->
      <div style="font-size: 20px; font-weight: bold; color: #3d4566; margin-bottom: 15px;">调用信息</div>
      <div style="height: 2px; background: #e9e9e9; margin-bottom: 15px;"></div>

      <el-form :model="formData" label-width="100px" label-position="left" class="custom-form">
        <!-- 第一行：模型名称和接口地址 -->
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
          <el-form-item label="模型名称" prop="param1" style="flex: 0.5; margin-bottom: 0;">
            <el-input
                v-model="formData.configJson.param1"
                placeholder="请输入model_name"
                class="custom-input-bg"
            ></el-input>
          </el-form-item>
          <el-form-item label="接口地址" prop="param2" style="flex: 1; margin-bottom: 0;">
            <el-input
                v-model="formData.configJson.param2"
                placeholder="请输入base_url"
                class="custom-input-bg"
            ></el-input>
          </el-form-item>
        </div>

        <!-- 秘钥信息 -->
        <el-form-item label="秘钥信息" prop="apiKey">
          <el-input
              v-model="formData.configJson.apiKey"
              placeholder="请输入api_key"
              show-password
              class="custom-input-bg"
          ></el-input>
        </el-form-item>
      </el-form>
    </div>

    <!-- 保存按钮 -->
    <div style="display: flex;justify-content: center;">
      <el-button
          type="primary"
          @click="confirm"
          class="save-btn"
      >
        保存
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'AddModelDialog',
  props: {
    visible: {type: Boolean, required: true},
    modelType: {type: String, required: true}
  },
  data() {
    return {
      formData: {
        modelName: '',
        modelCode: '',
        supplier: '',
        sort: 1,
        docLink: '',
        remark: '',
        isEnabled: true,
        isDefault: true,
        configJson: {
          param1: '',
          param2: '',
          apiKey: ''
        }
      }
    }
  },
  methods: {
    confirm() {
      if (!this.formData.modelName || !this.formData.modelCode || !this.formData.supplier ||
          !this.formData.configJson.param1 || !this.formData.configJson.param2 || !this.formData.configJson.apiKey) {
        this.$message.error('请填写所有必填字段');
        return;
      }

      this.$emit('confirm', {
        ...this.formData,
        provideType: this.formData.supplier
      });
      this.$emit('update:visible', false);
      this.resetForm();
    },
    resetForm() {
      this.formData = {
        modelName: '',
        modelCode: '',
        supplier: '',
        sort: 1,
        docLink: '',
        remark: '',
        isEnabled: true,
        isDefault: true,
        configJson: {
          param1: '',
          param2: '',
          apiKey: ''
        }
      };
    },
    handleClose() {
      this.resetForm();
      this.$emit('update:visible', false);
    }
  }
}
</script>

<style>
.custom-dialog {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  background: white;
  padding-bottom: 17px;
}

.custom-dialog .el-dialog__header {
  padding: 0;
  border-bottom: none;
}

.center-dialog {
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-dialog .el-dialog {
  margin: 4% 0 auto !important;
  display: flex;
  flex-direction: column;
}

.custom-close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 35px;
  height: 35px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
}

.custom-close-btn:hover {
  color: #409EFF;
  border-color: #409EFF;
}

.custom-select .el-input__suffix {
  background: #e6e8ea;
  right: 6px;
  width: 20px;
  height: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  top: 9px;
}

.custom-select .el-input__suffix-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

.custom-select .el-icon-arrow-up:before {
  content: "";
  display: inline-block;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 7px solid #c0c4cc;
  position: relative;
  top: -2px;
  transform: rotate(180deg);
}

.custom-form .el-form-item {
  margin-bottom: 20px; /* 统一设置所有表单项的间距 */
}

.custom-form .el-form-item__label {
  color: #3d4566;
  font-weight: normal;
  text-align: right;
  padding-right: 20px;

}

.custom-form .el-form-item.prop-remark .el-form-item__label {
  margin-top: -4px;
}

/* 修改placeholder颜色 */
.custom-input-bg .el-input__inner::-webkit-input-placeholder,
.custom-input-bg .el-textarea__inner::-webkit-input-placeholder {
  color: #9c9f9e;
}

/* 输入框背景色 */
.custom-input-bg .el-input__inner,
.custom-input-bg .el-textarea__inner {
  background-color: #f6f8fc;
}


.save-btn {
  background: #e6f0fd;
  color: #237ff4;
  border: 1px solid #b3d1ff;
  width: 150px;
  height: 40px;
  font-size: 16px;
  transition: all 0.3s ease;
}

.save-btn:hover {
  background: linear-gradient(to right, #237ff4, #9c40d5);
  color: white;
  border: none;
}


/* 修改开关样式 */
.custom-switch .el-switch__core {
  border-radius: 20px;
  height: 23px;
  background-color: #c0ccda;
  width: 35px;
  padding: 0 20px; /* 调整左右内边距 */
}

.custom-switch .el-switch__core:after {
  width: 15px;
  height: 15px;
  background-color: white;
  top: 3px;
  left: 4px;
  transition: all .3s;
}

.custom-switch.is-checked .el-switch__core {
  border-color: #b5bcf0;
  background-color: #cfd7fa;
  padding: 0 20px; /* 确保启用状态也有相同的间隔 */
}

.custom-switch.is-checked .el-switch__core:after {
  left: 100%;
  margin-left: -18px;
  background-color: #1b47ee;
}


/* 调整flex布局的gap */
[style*="display: flex"] {
  gap: 20px; /* 扩大flex项间距 */
}

/* 调整输入框高度 */
.custom-input-bg .el-input__inner {
  height: 32px; /* 固定输入框高度 */
}


</style>