<template>
  <el-dialog :visible.sync="visible" width="400px" center>
    <div style="margin: 0 10px 10px;display: flex;align-items: center;gap: 10px;font-weight: 700;font-size: 20px;text-align: left;color: #3d4566;">
      <div style="width: 40px;height: 40px;border-radius: 50%;background: #5778ff;display: flex;align-items: center;justify-content: center;">
        <img src="@/assets/login/shield.png" alt="" style="width: 19px;height: 23px; filter: brightness(0) invert(1);" />
      </div>
      用户新密码
    </div>
    <div style="height: 1px;background: #e8f0ff;" />
    <div style="margin: 22px 15px;">
      <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;">
        <div style="color: red;display: inline-block;">*</div>
        用户新密码：
      </div>
      <div class="input-46" style="margin-top: 12px;">
        <el-input
          v-model="password"
          type="text"
          :readonly="true"
          style="font-weight: bold; color: #333;"
        />
      </div>
    </div>
    <div style="display: flex;margin: 15px 15px;gap: 7px;">
      <div
        class="dialog-btn"
        style="background: #e6ebff;border: 1px solid #adbdff;color: #5778ff;"
        @click="closeDialog"
      >
        关闭
      </div>
      <div
        class="dialog-btn"
        style="background: #5778ff;color: white;"
        @click="copyPassword"
      >
        复制密码
      </div>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'ViewPasswordDialog',
  props: {
    visible: { type: Boolean, required: true },
    password: { type: String, default: '' }
  },
  methods: {
    closeDialog() {
      this.$emit('update:visible', false)
    },
    copyPassword() {
      navigator.clipboard.writeText(this.password)
      this.$message.success('密码已复制')
    }
  }
}
</script>

<style scoped>
.input-46 {
  border: 1px solid #e4e6ef;
  background: #f6f8fb;
  border-radius: 15px;
}

.dialog-btn {
  cursor: pointer;
  flex: 1;
  border-radius: 23px;
  height: 40px;
  font-weight: 500;
  font-size: 12px;
  line-height: 40px;
  text-align: center;
}

::v-deep .el-dialog {
  border-radius: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

::v-deep .el-dialog__headerbtn {
  display: none;
}

::v-deep .el-dialog__body {
  padding: 4px 6px;
}

::v-deep .el-input__inner {
  background-color: #f6f8fb !important;
  cursor: default !important;
}
</style>
