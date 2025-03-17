<template>
  <el-dialog :visible.sync="visible" width="480px" center>
    <div style="margin: 0 20px 20px;display: flex;align-items: center;gap: 10px;font-weight: 700;font-size: 20px;text-align: left;color: #3d4566;">
      <div style="width: 36px;height: 36px;border-radius: 50%;background: #5778ff;display: flex;align-items: center;justify-content: center;">
        <img src="@/assets/home/equipment.png" alt="" style="width: 16px;height: 14px;" />
      </div>
      添加设备
    </div>
    <div style="height: 1px;background: #e8f0ff;" />
    <div style="margin: 30px 20px;">
      <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;">
        <div style="color: red;display: inline-block;">*</div>验证码：
      </div>
      <div class="input-46" style="margin-top: 10px;">
        <el-input placeholder="请输入设备播报的6位数验证码.." v-model="deviceCode" />
      </div>
    </div>
    <div style="display: flex;margin: 0 20px;gap: 10px;">
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
export default {
  name: 'AddDeviceDialog',
  props: {
    visible: { type: Boolean, required: true }
  },
  data() {
    return { deviceCode: "" }
  },
  methods: {
    confirm() {
      this.$emit('update:visible', false)
      this.$emit('added', this.deviceCode)
      this.deviceCode = ""
    },
    cancel() {
      this.$emit('update:visible', false)
      this.deviceCode = ""
    }
  }
}
</script>

<style scoped>


.input-46 {
  border: 1px solid #e4e6ef;
  background: #f6f8fb;
  border-radius: 10px;
}

.dialog-btn {
  cursor: pointer;
  flex: 1;
  border-radius: 23px;
  background: #5778ff;
  height: 46px;
  font-weight: 500;
  font-size: 14px;
  color: #fff;
  line-height: 46px;
  text-align: center;
}
</style>