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
      <el-form-item :label="$t('dictTypeDialog.dictName')" prop="dictName" class="form-item">
        <el-input v-model="form.dictName" :placeholder="$t('dictTypeDialog.dictNamePlaceholder')" />
      </el-form-item>
      <el-form-item :label="$t('dictTypeDialog.dictType')" prop="dictType" class="form-item">
        <el-input v-model="form.dictType" :placeholder="$t('dictTypeDialog.dictTypePlaceholder')" />
      </el-form-item>
    </el-form>
  </CustomDialog>
</template>

<script>
import CustomDialog from './CustomDialog.vue';
export default {
  name: 'DictTypeDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: () => this.$t('dictTypeDialog.addDictType')
    },
    dictTypeData: {
      type: Object,
      default: () => ({})
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
        dictName: '',
        dictType: ''
      },
      rules: {
        dictName: [{ required: true, message: this.$t('dictTypeDialog.requiredDictName'), trigger: 'blur' }],
        dictType: [{ required: true, message: this.$t('dictTypeDialog.requiredDictType'), trigger: 'blur' }]
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
    dictTypeData: {
      handler(val) {
        if (val) {
          this.form = { ...val };
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
