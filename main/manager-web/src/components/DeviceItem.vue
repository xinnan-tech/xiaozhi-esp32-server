<template>
  <div class="device-item">
    <div style="display: flex;justify-content: space-between;">
      <div style="font-weight: 700;font-size: 24px;text-align: left;color: #3d4566;">
        {{ device.mac }}
      </div>
      <div>
        <img src="@/assets/home/delete.png" alt=""
             style="width: 24px;height: 24px;margin-right: 10px;" />
        <img src="@/assets/home/info.png" alt="" style="width: 24px;height: 24px;" />
      </div>
    </div>
    <div class="device-name">
      设备型号：{{ device.model }}
    </div>
    <div style="display: flex;gap: 10px;align-items: center;">
      <div class="settings-btn" @click="$emit('configure')">
        配置角色
      </div>
      <div class="settings-btn">
        声纹识别
      </div>
      <div class="settings-btn">
        历史对话
      </div>
      <el-switch v-model="switchValue" inactive-text="OTA升级:" :width="42"
                 style="margin-left: auto;" />
    </div>
    <div class="version-info">
      <div>最近对话：{{ device.lastConversation }}</div>
      <div>APP版本：{{ device.appVersion }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DeviceItem',
  props: {
    device: { type: Object, required: true }
  },
  data() {
    return { switchValue: false }
  }
}
</script>
<style scoped>
.device-item {
  width: 455px;
  border-radius: 20px;
  background: #fafcfe;
  padding: 30px;
  box-sizing: border-box;
}
.device-name {
  margin: 10px 0 14px;
  font-weight: 400;
  font-size: 14px;
  color: #3d4566;
  text-align: left;
}

.settings-btn {
  font-weight: 500;
  font-size: 14px;
  color: #5778ff;
  background: #e6ebff;
  width: 76px;
  height: 28px;
  line-height: 28px;
  cursor: pointer;
  border-radius: 14px;
}

.version-info {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  font-size: 14px;
  color: #979db1;
  font-weight: 400;
}
</style>