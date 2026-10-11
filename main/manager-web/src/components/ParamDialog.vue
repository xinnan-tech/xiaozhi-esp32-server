<template>
  <CustomDialog
    :title="title"
    :visible.sync="visible"
    width="720px"
    class="param-dialog-wrapper"
    @confirm="submit"
    @close="cancel"
    :confirmLoading="saving"
    :confirmText="$t('button.ok')"
    :cancelText="$t('button.cancel')"
  >
    <div class="dialog-container">
      <el-form :model="form" :rules="rules" ref="form" label-width="auto" label-position="left" class="param-form">
        <el-form-item :label="$t('paramDialog.paramCode')" prop="paramCode" class="form-item">
          <el-input v-model="form.paramCode" :placeholder="$t('paramDialog.paramCodePlaceholder')"
            class="custom-input"></el-input>
        </el-form-item>

        <el-form-item :label="$t('paramDialog.paramValue')" prop="paramValue" class="form-item">
          <el-input v-model="form.paramValue" :placeholder="$t('paramDialog.paramValuePlaceholder')"
            class="custom-input"></el-input>
        </el-form-item>

        <el-form-item :label="$t('paramDialog.valueType')" prop="valueType" class="form-item">
          <el-select v-model="form.valueType" :placeholder="$t('paramDialog.valueTypePlaceholder')"
            class="custom-select">
            <el-option v-for="item in valueTypeOptions" :key="item.value" :label="$t(`paramDialog.${item.value}Type`)"
              :value="item.value" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('paramDialog.remark')" prop="remark" class="form-item remark-item">
          <el-input type="textarea" v-model="form.remark" :placeholder="$t('paramDialog.remarkPlaceholder')" :rows="3"
            class="custom-textarea"></el-input>
        </el-form-item>
      </el-form>
    </div>
  </CustomDialog>
</template>

<script>
import CustomDialog from './CustomDialog.vue';
export default {
  props: {
    title: {
      type: String,
      default: 'Add Parameter'
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        paramCode: '',
        paramValue: '',
        valueType: 'string',
        remark: ''
      })
    }
  },
  components: {
    CustomDialog
  },
  data() {
    return {
      dialogKey: Date.now(),
      saving: false,
      valueTypeOptions: [
        { value: 'string' },
        { value: 'number' },
        { value: 'boolean' },
        { value: 'array' },
        { value: 'json' }
      ],
      rules: {
        paramCode: [
          { required: true, message: this.$t('paramDialog.requiredParamCode'), trigger: "blur" }
        ],
        paramValue: [
          { required: true, message: this.$t('paramDialog.requiredParamValue'), trigger: "blur" }
        ],
        valueType: [
          { required: true, message: this.$t('paramDialog.requiredValueType'), trigger: "change" }
        ]
      }
    };
  },
  methods: {
    submit() {
      this.$refs.form.validate((valid) => {
        if (valid) {
          this.saving = true; // Start loading
          this.$emit('submit', this.form);
        }
      });
    },
    cancel() {
      this.saving = false; // Reset status when cancelled
      this.$emit('cancel');
    },

    // Provided for parent component to call to reset saving status
    resetSaving() {
      this.saving = false;
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.dialogKey = Date.now();
      } else {
        // When dialog closes, reset saving status
        this.saving = false;
      }
    }
  }
};
</script>

<style scoped lang="scss">
.param-dialog-wrapper {
  .param-form {
    .form-item {
      margin-bottom: 28px;
      :deep(.el-form-item__label) {
        color: #475569;
        font-weight: 500;
        padding-right: 14px;
        text-align: right;
        font-size: 15px;
        letter-spacing: 0.2px;
        line-height: 44px;
      }
    }

    .custom-input {
      :deep(.el-input__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        height: 44px;
        padding: 0 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .custom-select {
      width: 100%;

      :deep(.el-input__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        height: 44px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }

    .custom-textarea {
      :deep(.el-textarea__inner) {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 10px 14px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 14px;
        color: #334155;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        line-height: 1.5;

        &:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
          background-color: #ffffff;
        }

        &::placeholder {
          color: #94a3b8;
          font-weight: 400;
        }
      }
    }
  }
}
</style>
