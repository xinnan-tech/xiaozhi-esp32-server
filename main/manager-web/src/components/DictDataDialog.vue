<template>
  <CustomDialog
    :title="title"
    :visible.sync="dialogVisible"
    width="600px"
    @confirm="submit"
    @close="cancel"
    :confirmLoading="saving"
  >
    <el-form :model="form" :rules="rules" ref="form" label-width="auto" label-position="left">
      <el-form-item :label="$t('dictDataDialog.dictLabel')" prop="dictLabel" class="form-item">
        <el-input v-model="form.dictLabel" :placeholder="$t('dictDataDialog.dictLabelPlaceholder')" />
      </el-form-item>
      <el-form-item :label="$t('dictDataDialog.dictValue')" prop="dictValue" class="form-item">
        <el-input v-model="form.dictValue" :placeholder="$t('dictDataDialog.dictValuePlaceholder')" />
      </el-form-item>
      <el-form-item :label="$t('dictDataDialog.sort')" prop="sort" class="form-item">
        <el-input-number v-model="form.sort" :min="0" :max="999" class="custom-input-number"></el-input-number>
      </el-form-item>
    </el-form>
  </CustomDialog>
</template>

<script>
import CustomDialog from './CustomDialog.vue';
export default {
  name: 'DictDataDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: () => this.$t('dictDataDialog.addDictData')
    },
    dictData: {
      type: Object,
      default: () => ({})
    },
    dictTypeId: {
      type: [Number, String],
      default: null
    }
  },
  components: {
    CustomDialog
  },
  data() {
    return {
      dialogVisible: this.visible,
      saving: false,
      form: {
        id: null,
        dictTypeId: null,
        dictLabel: '',
        dictValue: '',
        sort: 0
      },
      rules: {
        dictLabel: [{ required: true, message: this.$t('dictDataDialog.requiredDictLabel'), trigger: 'blur' }],
        dictValue: [{ required: true, message: this.$t('dictDataDialog.requiredDictValue'), trigger: 'blur' }]
      }
    };
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
    },
    dialogVisible(val) {
      this.$emit('update:visible', val);
      if (!val) {
        this.saving = false;
      }
    },
    dictData: {
      handler(val) {
        if (val) {
          this.form = { ...val };
        }
      },
      immediate: true
    },
    dictTypeId: {
      handler(val) {
        if (val) {
          this.form.dictTypeId = val;
        }
      },
      immediate: true
    }
  },
  methods: {
    submit() {
      this.$refs.form.validate((valid) => {
        if (valid) {
          this.saving = true;
          this.$emit('save', this.form);
        }
      });
    },
    cancel() {
      this.saving = false;
      this.$emit('cancel');
    },
    resetSaving() {
      this.saving = false;
    }
  }
};
</script>

<style scoped lang="scss">
.custom-input-number {
  width: 100%;
}
</style>
