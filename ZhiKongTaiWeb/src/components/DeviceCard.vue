<template>
  <div class="device-card">
    <div class="card-header">
      <div class="device-code">{{ deviceId }}</div>
      <div class="card-actions">
        <button class="action-btn delete" @click="handleDelete">🗑️</button>
        <button class="action-btn info">ℹ️</button>
      </div>
    </div>
    
    <div class="card-body">
      <div class="device-info">
        <div class="info-label">设备型号：</div>
        <div class="info-value">{{ deviceType }}</div>
      </div>
      
      <div class="device-actions">
        <button class="device-action-btn" @click="handleConfigure">配置角色</button>
        <button class="device-action-btn">声纹识别</button>
        <button class="device-action-btn">历史对话</button>
        
        <div class="ota-toggle">
          <span class="ota-label">OTA升级：</span>
          <label class="toggle">
            <input type="checkbox" :checked="false">
            <span class="slider round"></span>
          </label>
        </div>
      </div>
      
      <div class="device-footer">
        <div class="last-active">最近对话：{{ lastActivity}}</div>
        <div class="app-version">客户端版本：{{ "v1.0.0" }}</div>
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
  background-color: var(--card-bg);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.device-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.device-code {
  font-weight: 600;
  font-size: 1rem;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background-color: #f5f5f5;
  transition: background-color 0.2s ease;
}

.action-btn:hover {
  background-color: #e0e0e0;
}

.action-btn.delete:hover {
  background-color: #ffebee;
}

.card-body {
  padding: 1rem;
}

.device-info {
  display: flex;
  margin-bottom: 1rem;
}

.info-label {
  color: var(--light-text);
  font-size: 0.9rem;
  margin-right: 0.5rem;
}

.info-value {
  font-size: 0.9rem;
}

.device-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.device-action-btn {
  padding: 0.4rem 0.8rem;
  background-color: #f0f4ff;
  border: none;
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--text-color);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.device-action-btn:hover {
  background-color: #e6f0ff;
}

.ota-toggle {
  display: flex;
  align-items: center;
  margin-top: 0.5rem;
  width: 100%;
}

.ota-label {
  font-size: 0.8rem;
  color: var(--light-text);
  margin-right: 0.5rem;
}

/* 开关样式 */
.toggle {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
}

input:checked + .slider {
  background-color: var(--primary-color);
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.slider.round {
  border-radius: 20px;
}

.slider.round:before {
  border-radius: 50%;
}

.device-footer {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--lighter-text);
  margin-top: 1rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 576px) {
  .device-actions {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .device-action-btn {
    width: 100%;
  }
}
</style>