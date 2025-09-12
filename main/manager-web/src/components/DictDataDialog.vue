<template>
    <el-dialog :title="title" :visible.sync="dialogVisible" width="30%" @close="handleClose">
        <el-form :model="form" :rules="rules" ref="form" label-width="auto">
            <el-form-item :label="$t('dictDataDialog.dictLabel')" prop="dictLabel">
                <el-input v-model="form.dictLabel" :placeholder="$t('dictDataDialog.dictLabelPlaceholder')"></el-input>
            </el-form-item>
            <el-form-item :label="$t('dictDataDialog.dictValue')" prop="dictValue">
                <el-input v-model="form.dictValue" :placeholder="$t('dictDataDialog.dictValuePlaceholder')"></el-input>
            </el-form-item>
            <el-form-item :label="$t('dictDataDialog.sort')" prop="sort">
                <el-input-number v-model="form.sort" :min="0" :max="999" style="width: 100%;"></el-input-number>
            </el-form-item>
        </el-form>
        <div slot="footer" class="dialog-footer">
            <el-button @click="handleClose">{{ $t('button.cancel') }}</el-button>
            <el-button type="primary" @click="handleSave">{{ $t('button.save') }}</el-button>
        </div>
    </el-dialog>
</template>

<script>
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
    data() {
        return {
            dialogVisible: this.visible,
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
        }
    },
    watch: {
        dictData: {
            handler(val) {
                if (val) {
                    this.form = { ...val }
                }
            },
            immediate: true
        },
        dictTypeId: {
            handler(val) {
                if (val) {
                    this.form.dictTypeId = val
                }
            },
            immediate: true
        },
        visible(val) {
          this.dialogVisible = val;
        },
        dialogVisible(val) {
          this.$emit('update:visible', val);
        }
    },
    methods: {
        handleClose() {
          this.dialogVisible = false;
          this.resetForm();
        },
        resetForm() {
            this.form = {
                id: null,
                dictTypeId: this.dictTypeId,
                dictLabel: '',
                dictValue: '',
                sort: 0
            }
            this.$refs.form?.resetFields()
        },
        handleSave() {
            this.$refs.form.validate(valid => {
                if (valid) {
                    this.$emit('save', this.form)
                }
            })
        }
    }
}
</script>

<style scoped>
.dialog-footer {
    text-align: right;
}
:deep(.el-dialog) {
    border-radius: 15px;
}

</style>