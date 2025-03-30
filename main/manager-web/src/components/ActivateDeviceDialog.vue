<template>
  <el-dialog :visible.sync="visible" width="400px" center>
    <div style="margin: 0 10px 10px;display: flex;align-items: center;gap: 10px;font-weight: 700;font-size: 20px;text-align: left;color: #3d4566;">
      <div style="width: 40px;height: 40px;border-radius: 50%;background: #5778ff;display: flex;align-items: center;justify-content: center;">
        <img src="@/assets/home/equipment.png" alt="" style="width: 18px;height: 15px;" />
      </div>
      激活设备
    </div>
    <div style="height: 1px;background: #e8f0ff;" />
    <div style="margin: 22px 15px;">
      <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;">
        <div style="color: red;display: inline-block;">*</div> 设备激活码：
      </div>
      <div class="input-46" style="margin-top: 12px;">
        <el-input placeholder="请输入设备播报的激活码.." v-model="activateCode" />
      </div>
    </div>
    <div style="display: flex;margin: 15px 15px;gap: 7px;">
      <div class="dialog-btn" @click="confirm">
        确定
      </div>
      <div class="dialog-btn"
           style="background: #e6ebff;border: 1px solid #adbdff;color: #5778ff;"
           @click="cancel">
        取消
      </div>
    </div>
  </el-dialog>
</template>

<script>
import userApi from '@/apis/module/user';


export default {
  name: 'ActivateDeviceDialog',
  props: {
    visible: { type: Boolean, required: true }
  },
  data() {
    return { activateCode: "" }
  },
  methods: {
    confirm() {
      if (!this.activateCode.trim()) {
        this.$message.error('请输入激活码');
        return;
      }
      userApi.activateDevice(this.activateCode, (res) => {
        this.$message.success('激活成功，请重新唤醒设备即可完成激活！');
        this.$emit('confirm', res);
        this.$emit('update:visible', false);
        console.log("res: ", res)
        this.activateCode = "";
      });
    },
    cancel() {
      this.$emit('update:visible', false)
      this.activateCode = ""
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
  background: #5778ff;
  height: 40px;
  font-weight: 500;
  font-size: 12px;
  color: #fff;
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
::v-deep .el-dialog__header{
  padding: 10px;
}
</style>