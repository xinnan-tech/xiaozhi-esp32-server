<template>
  <div class="device-item">
    <div style="display: flex;justify-content: space-between;">
      <div style="font-weight: 700;font-size: 18px;text-align: left;color: #3d4566;">
         {{ device.agentName }}
      </div>
      <div>
        <img src="@/assets/home/delete.png" alt=""
             style="width: 18px;height: 18px;margin-right: 10px;" @click.stop="handleDelete" />
        <img src="@/assets/home/info.png" alt="" style="width: 18px;height: 18px;" />
      </div>
    </div>
    <div class="device-name">
      设备型号：{{ device.ttsModelName }}
    </div>
    <div class="device-name">
      音色模型：{{ device.ttsVoiceName }}
    </div>
    <div style="display: flex;gap: 10px;align-items: center;">
      <div class="settings-btn" @click="handleConfigure">
        配置角色
      </div>
      <div class="settings-btn">
        声纹识别
      </div>
      <div class="settings-btn">
        历史对话
      </div>
      <div class="settings-btn"  @click="handleDeviceManage">
        设备管理
      </div>
    </div>
    <div class="version-info">
      <div>最近对话：{{ device.lastConnectedAt }}</div>
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
  },
  methods: {
    handleDelete() {
      this.$emit('delete', this.device.agentId)
    },
    handleConfigure() {
      this.$router.push({ path: '/role-config', query: { agentId: this.device.agentId } });
    },
    handleDeviceManage() {
      this.$router.push({ path: '/device-management', query: { agentId: this.device.agentId } });
    }
  }
}
</script>
<style scoped>
.device-item {
  width: 342px;
  border-radius: 20px;
  background: #fafcfe;
  padding: 22px;
  box-sizing: border-box;
}
.device-name {
  margin: 7px 0 10px;
  font-weight: 400;
  font-size: 11px;
  color: #3d4566;
  text-align: left;
}

.settings-btn {
  font-weight: 500;
  font-size: 10px;
  color: #5778ff;
  background: #e6ebff;
  width: 57px;
  height: 21px;
  line-height: 21px;
  cursor: pointer;
  border-radius: 14px;
}

.version-info {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 10px;
  color: #979db1;
  font-weight: 400;
}

</style>