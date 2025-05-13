<template>
    <el-dialog :title="title" :visible.sync="dialogVisible"  width="30%" @close="handleClose">
        <el-form :model="form" :rules="rules" ref="form" label-width="120px">
            <el-form-item label="字典类型名称" prop="dictName">
                <el-input v-model="form.dictName" placeholder="请输入字典类型名称"></el-input>
            </el-form-item>
            <el-form-item label="字典类型编码" prop="dictType">
                <el-input v-model="form.dictType" placeholder="请输入字典类型编码"></el-input>
            </el-form-item>
        </el-form>
        <div slot="footer" class="dialog-footer">
            <el-button @click="handleClose">取 消</el-button>
            <el-button type="primary" @click="handleSave">确 定</el-button>
        </div>
    </el-dialog>
</template>

<script>
export default {
    name: 'DictTypeDialog',
    props: {
        visible: {
            type: Boolean,
            default: false
        },
        title: {
            type: String,
            default: '新增字典类型'
        },
        dictTypeData: {
            type: Object,
            default: () => ({})
        }
    },
    data() {
        return {
            dialogVisible: this.visible,
            form: {
                id: null,
                dictName: '',
                dictType: ''
            },
            rules: {
                dictName: [{ required: true, message: '请输入字典类型名称', trigger: 'blur' }],
                dictType: [{ required: true, message: '请输入字典类型编码', trigger: 'blur' }]
            }
        }
    },
    watch: {
        visible(val) {
          this.dialogVisible = val;
        },
        dialogVisible(val) {
          this.$emit('update:visible', val);
        },
        dictTypeData: {
            handler(val) {
                if (val) {
                    this.form = { ...val }
                }
            },
            immediate: true
        }
    },
    methods: {
        handleClose() {
            this.dialogVisible = false;
            this.resetForm()
        },
        resetForm() {
            this.form = {
                id: null,
                dictName: '',
                dictType: ''
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