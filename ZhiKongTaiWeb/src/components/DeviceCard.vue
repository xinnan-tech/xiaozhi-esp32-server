<template>
  <div class="device-card">
    <div class="device-header">
      <h2 class="device-id">{{ deviceId }} <span class="note">[{{ deviceNote || '备注' }}]</span></h2>
    </div>
    
    <div class="device-details">
      <p class="device-type">设备型号：{{ deviceType }}</p>
      <p class="device-role">角色昵称：{{ deviceRole }}</p>
      <p class="device-modules">
        当前模型：
        <span class="module-item">LLM: {{ selectedModules?.LLM || '-' }}</span>
        <span class="module-item">TTS: {{ selectedModules?.TTS || '-' }}</span>
      </p>
      <p class="last-activity">最近对话：{{ lastActivity }}</p>
    </div>
    
    <div class="device-actions">
      <button class="action-btn primary" @click="handleConfigure">配置角色</button>
      <button class="action-btn" @click="$emit('voiceprint')">声纹识别</button>
      <button class="action-btn" @click="$emit('history')">历史对话</button>
      <div class="delete-container">
        <button class="action-btn danger" @click="handleDelete">
          <i class="icon-delete"></i> 删除设备
        </button>
        <div class="delete-warning">删除后设备配置将不可恢复</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import SwitchToggle from './SwitchToggle.vue';

const props = defineProps({
  deviceId: String,
  deviceNote: String,
  deviceType: {
    type: String,
    default: '未知型号（待实现）'
  },
  lastActivity: {
    type: String,
    default: '3 天前'
  },
  selectedModules: {
    type: Object,
    default: () => ({
      LLM: '-',
      TTS: '-',
      ASR: '-',
      VAD: '-'
    })
  },
  deviceConfig: {
    type: Object,
    default: () => ({})
  }
});

const deviceRole = computed(() => {
  return props.deviceConfig?.nickname || '小智';
});

// Store device config when it changes
watch(() => props.selectedModules, (newValue) => {
  if (props.deviceId) {
    localStorage.setItem(`deviceConfig_${props.deviceId}`, JSON.stringify({
      selected_module: newValue
    }));
  }
}, { deep: true });

const otaEnabled = ref(false);

const emit = defineEmits(['configure', 'voiceprint', 'history', 'delete']);

const handleDelete = () => {
  if (confirm('确认要删除此设备吗？\n\n警告：删除后设备所有配置将不可恢复！')) {
    emit('delete');
  }
};

const handleConfigure = () => {
  // 保存设备配置到 localStorage，确保 RoleSetting 可以访问
  if (props.deviceId && props.deviceConfig) {
    localStorage.setItem(`deviceConfig_${props.deviceId}`, JSON.stringify({
      selected_module: props.selectedModules,
      prompt: props.deviceConfig.prompt || '',
      nickname: props.deviceConfig.nickname || '小智'
    }));
  }
  emit('configure');
};
</script>

<style scoped>
.device-card {
  background: white;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 16px;
}

.device-id {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 16px;
}

.note {
  color: #4178EE;
  font-size: 14px;
  font-weight: normal;
}

.device-details p {
  margin-bottom: 12px;
}

.ota-upgrade {
  display: inline-flex;
  align-items: center;
  margin-left: 16px;
}

.device-actions {
  display: flex;
  margin-top: 20px;
}

.action-btn {
  padding: 8px 16px;
  margin-right: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.action-btn.primary {
  background: #4178EE;
  color: white;
  border-color: #4178EE;
}

.action-btn.danger {
  background: #fff3f3;
  border-color: #ffa4a4;
  color: #f56c6c;
}

.action-btn.danger:hover {
  background: #fde2e2;
  border-color: #f56c6c;
}

.device-modules {
  margin-bottom: 12px;
  color: #666;
}

.module-item {
  display: inline-block;
  margin-right: 16px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 0.9em;
}

.device-role {
  color: #666;
  margin-bottom: 12px;
}

.delete-container {
  position: relative;
  margin-left: auto;  /* Push delete button to the right */
}

.delete-warning {
  position: absolute;
  bottom: calc(100% + 5px);  /* Position above the button */
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  background: #fff3f3;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #ffa4a4;
  font-size: 12px;
  color: #f56c6c;
  display: none;
}

.delete-container:hover .delete-warning {
  display: block;
}

.icon-delete {
  margin-right: 4px;
}
</style>
