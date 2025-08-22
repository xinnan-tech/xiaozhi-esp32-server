<template>
    <el-dialog :title="title" :visible.sync="dialogVisible" width="30%" @close="handleClose">
        <el-form :model="form" :rules="rules" ref="form" label-width="100px">
            <el-form-item label="Dictionary Label" prop="dictLabel">
                <el-input v-model="form.dictLabel" placeholder="Enter dictionary label"></el-input>
            </el-form-item>
            <el-form-item label="Dictionary Value" prop="dictValue">
                <el-input v-model="form.dictValue" placeholder="Enter dictionary value"></el-input>
            </el-form-item>
            <el-form-item label="Sort" prop="sort">
                <el-input-number v-model="form.sort" :min="0" :max="999" style="width: 100%;"></el-input-number>
            </el-form-item>
        </el-form>
        <div slot="footer" class="dialog-footer">
            <el-button @click="handleClose">Cancel</el-button>
            <el-button type="primary" @click="handleSave">Confirm</el-button>
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
            default: 'Add Dictionary Data'
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
                dictLabel: [{ required: true, message: 'Please enter dictionary label', trigger: 'blur' }],
                dictValue: [{ required: true, message: 'Please enter dictionary value', trigger: 'blur' }]
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