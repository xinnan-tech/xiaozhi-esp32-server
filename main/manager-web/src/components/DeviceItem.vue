<template>
  <div class="device-item">
    <div style="display: flex;justify-content: space-between;">
      <div style="font-weight: 700;font-size: 18px;text-align: left;color: #3d4566;">
        {{ device.agentName }}
      </div>
      <div>
        <img src="@/assets/home/delete.png" alt="" class="action-icon delete-icon"
          @click.stop="handleDelete" />
        <el-tooltip class="item" effect="dark" :content="device.systemPrompt" placement="top"
          popper-class="custom-tooltip">
          <img src="@/assets/home/info.png" alt="" class="action-icon info-icon" />
        </el-tooltip>
      </div>
    </div>
    <div class="device-name">
      Language Model: {{ device.llmModelName }}
    </div>
    <div class="device-name">
      Voice Model: {{ device.ttsModelName }} ({{ device.ttsVoiceName }})
    </div>
    <div style="display: flex;gap: 8px;align-items: center;flex-wrap: wrap;">
      <div class="settings-btn" @click="handleConfigure">
        Configure Role
      </div>
       <div class="settings-btn" @click="handleVoicePrint">
        Voice Recognition
      </div>
      <div class="settings-btn" @click="handleDeviceManage">
        Devices ({{ device.deviceCount }})
      </div>
      <div class="settings-btn" @click="handleChatHistory"
        :class="{ 'disabled-btn': device.memModelId === 'Memory_nomem' }">
        <el-tooltip v-if="device.memModelId === 'Memory_nomem'" content="Please enable memory in 'Configure Role' first" placement="top">
          <span>Chat History</span>
        </el-tooltip>
        <span v-else>Chat History</span>
      </div>
    </div>
    <div class="version-info">
      <div>Last Conversation: {{ formattedLastConnectedTime }}</div>
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
  computed: {
    formattedLastConnectedTime() {
      if (!this.device.lastConnectedAt) return 'No conversations yet';

      const lastTime = new Date(this.device.lastConnectedAt);
      const now = new Date();
      const diffMinutes = Math.floor((now - lastTime) / (1000 * 60));

      if (diffMinutes <= 1) {
        return 'Just now';
      } else if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
      } else if (diffMinutes < 24 * 60) {
        const hours = Math.floor(diffMinutes / 60);
        const minutes = diffMinutes % 60;
        return `${hours} hour${hours > 1 ? 's' : ''} ${minutes > 0 ? minutes + ' minute' + (minutes > 1 ? 's' : '') : ''} ago`;
      } else {
        return this.device.lastConnectedAt;
      }
    }
  },
  methods: {
    handleDelete() {
      this.$emit('delete', this.device.agentId)
    },
    handleConfigure() {
      this.$router.push({ path: '/role-config', query: { agentId: this.device.agentId } });
    },
    handleVoicePrint() {
      this.$router.push({ path: '/voice-print', query: { agentId: this.device.agentId } });
    },
    handleDeviceManage() {
      this.$router.push({ path: '/device-management', query: { agentId: this.device.agentId } });
    },
    handleChatHistory() {
      if (this.device.memModelId === 'Memory_nomem') {
        return
      }
      this.$emit('chat-history', { agentId: this.device.agentId, agentName: this.device.agentName })
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
  font-size: 11px;
  color: #5778ff;
  background: #e6ebff;
  width: auto;
  padding: 0 10px;
  height: 22px;
  line-height: 22px;
  cursor: pointer;
  border-radius: 11px;
  white-space: nowrap;
  display: inline-block;
}

.version-info {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 12px;
  color: #979db1;
  font-weight: 400;
}

.disabled-btn {
  background: #e6e6e6;
  color: #999;
  cursor: not-allowed;
}

.action-icon {
  width: 24px;
  height: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-right: 10px;
  border-radius: 4px;
  padding: 2px;
}

.action-icon:hover {
  transform: scale(1.2);
  background-color: rgba(87, 120, 255, 0.1);
}

.delete-icon:hover {
  background-color: rgba(245, 108, 108, 0.1);
  filter: brightness(1.2);
}

.info-icon {
  margin-right: 0;
}

.info-icon:hover {
  background-color: rgba(64, 158, 255, 0.1);
  filter: brightness(1.2);
}
</style>

<style>
.custom-tooltip {
  max-width: 400px;
  word-break: break-word;
}
</style>