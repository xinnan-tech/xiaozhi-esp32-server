<template>
  <div class="agent-item">
    <div style="display: flex;justify-content: space-between;">
      <div style="font-weight: 700;font-size: 24px;text-align: left;color: #3d4566;">
        {{ agent.agentName }}
      </div>
      <div>
        <img src="@/assets/home/delete.png" alt=""
             style="width: 24px;height: 24px;" @click="$emit('del', agent.id)" />
        <!-- <img src="@/assets/home/info.png" alt="" style="width: 24px;height: 24px;margin-left: 10px;" /> -->
      </div>
    </div>
    <div class="agent-name">
      角色音色：{{ agent.ttsModelName }}
    </div>
    <div class="agent-name">
      语言模型：{{ agent.llmModelName }}
    </div>
    <div class="agent-name">
      最近对话：{{ agent.lastConnectedAt }}
    </div>
    <div style="display: flex;gap: 10px;align-items: center;">
      <div class="settings-btn" @click="$emit('configure', agent.id, agent.agentName)">
        配置角色
      </div>
      <div class="settings-btn" @click="$emit('asr', agent.id)">
        声纹识别
      </div>
      <div class="settings-btn" @click="$emit('chat', agent.id)">
        历史对话
      </div>
      <div class="settings-btn" @click="$emit('device', agent.id)">
        设备数量({{agent.deviceCount}})
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AgentItem',
  props: {
    agent: { type: Object, required: true }
  },
  data() {
    return { }
  }
}
</script>
<style scoped>
.agent-item {
  width: 455px;
  border-radius: 20px;
  background: #fafcfe;
  padding: 30px;
  box-sizing: border-box;
}
.agent-name {
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
  line-height: 28px;
  padding: 0 14px;
  cursor: pointer;
  border-radius: 14px;
}

</style>