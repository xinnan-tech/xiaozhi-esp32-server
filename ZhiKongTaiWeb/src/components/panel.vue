<template>
  <div class="app">
    <NavBar current-tab="device" @tab-change="handleTabChange"/>
    <main class="content">
      <div class="page-header">
        <div class="header-left">
         
          <div class="breadcrumb">
            <router-link to="/">首页</router-link> /
            <span>设备管理</span>
          </div>
        </div>
      </div>
      <button class="add-btn" @click="showBindDialog = true">
            <i class="icon-plus"></i>添加设备
      </button>
      <!-- 绑定设备弹窗 -->
      <div v-if="showBindDialog" class="dialog-overlay">
        <div class="dialog">
          <h3>绑定新设备</h3>
          <div class="form-group">
            <label>请输入6位认证码：</label>
            <input 
              type="text" 
              v-model="authCode"
              maxlength="6"
              pattern="\d*"
              placeholder="请输入6位数字认证码"
              @input="handleAuthCodeInput"
            />
          </div>
          <div class="dialog-buttons">
            <button @click="showBindDialog = false">取消</button>
            <button 
              class="primary" 
              @click="handleBindDevice"
              :disabled="authCode.length !== 6 || isBinding"
            >
              {{ isBinding ? '绑定中...' : '确认绑定' }}
            </button>
          </div>
        </div>
      </div>

      <template v-if="devices.length > 0">
        <div class="device-list">
          <DeviceCard
            v-for="device in devices"
            :key="device.id"
            :device-id="device.id"
            :device-note="device.note"
            :device-type="device.type"
            :last-activity="formatLastActivity(device.config.last_chat_time)"
            :selected-modules="device.config.selected_module"
            :device-config="device.config"
            @configure="handleRoleConfig(device)"
            @voiceprint="handleVoiceprint(device)"
            @history="handleHistory(device)"
            @delete="handleDelete(device)"
          />
        </div>
      </template>
     
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import NavBar from './NavBar.vue';
import DeviceCard from './DeviceCard.vue';
import apiClient from '../utils/api';

const router = useRouter();
const devices = ref([]);

// 绑定设备相关的状态
const showBindDialog = ref(false);
const authCode = ref('');
const isBinding = ref(false);

// 处理认证码输入，只允许数字
const handleAuthCodeInput = (event) => {
  authCode.value = event.target.value.replace(/\D/g, '').slice(0, 6);
};

// 处理设备绑定
const handleBindDevice = async () => {
  if (authCode.value.length !== 6) {
    alert('请输入6位数字认证码');
    return;
  }

  isBinding.value = true;
  try {
    const response = await apiClient.post('/api/config/bind_device', {
      auth_code: authCode.value
    });

    if (response.data.success) {
      alert('设备绑定成功');
      showBindDialog.value = false;
      authCode.value = '';
      // 刷新设备列表
      loadDevices();
    } else {
      throw new Error(response.data.message);
    }
  } catch (error) {
    alert(error.response?.data?.message || error.message || '绑定失败');
  } finally {
    isBinding.value = false;
  }
};

// 将现有的加载设备方法提取出来
const loadDevices = async () => {
  try {
    const response = await apiClient.get('/api/config/devices');
    
    if (response.data.success) {
      const deviceArray = Object.entries(response.data.data).map(([id, config]) => ({
        id,
        config,
        type: '面包板（WiFi）',
        version: '0.9.9',
        lastActivity: '3 天前',
        note: ''
      }));
      devices.value = deviceArray;
    } else {
      throw new Error(response.data.message || '加载设备失败');
    }
  } catch (error) {
    console.error('Error loading devices:', error);
    // Show error message to user
    const errorMessage = error.message || '加载设备失败，请检查网络连接';
    alert(errorMessage);
    
    // If user is not logged in, redirect will be handled by api interceptor
  }
};

const formatLastActivity = (timestamp) => {
  if (!timestamp) return '从未对话';
  
  const now = Date.now();
  const lastChat = timestamp * 1000;
  const diffMinutes = Math.floor((now - lastChat) / (1000 * 60));
  
  if (diffMinutes < 60) {
    return `${diffMinutes} 分钟前`;
  }
  
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours} 小时前`;
  }
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} 天前`;
};

const handleRoleConfig = (device) => {
  // 在跳转前保存完整的设备配置到 localStorage
  localStorage.setItem(`deviceConfig_${device.id}`, JSON.stringify({
    selected_module: device.config.selected_module || {},
    prompt: device.config.prompt || '',
    nickname: device.config.nickname || '小智'
  }));
  
  // 跳转到角色配置页面
  router.push(`/role-setting/${device.id}`);
};

const handleVoiceprint = (device) => {
  console.log('Voiceprint device:', device.id);
};

const handleHistory = (device) => {
  console.log('History device:', device.id);
};

const handleDelete = async (device) => {
  try {
    const response = await apiClient.post('/api/config/delete_device', {
      device_id: device.id
    });
    
    if (response.data.success) {
      devices.value = devices.value.filter(d => d.id !== device.id);
      alert('设备已删除');
    } else {
      throw new Error(response.data.message || '删除失败');
    }
  } catch (error) {
    console.error('Error deleting device:', error);
    alert('删除设备失败: ' + error.message);
  }
};

const handleTabChange = (tab) => {
  if (tab === 'home') {
    router.push('/');
  }
};

// Load devices on mount
onMounted(loadDevices);
</script>

<style scoped>
.app {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

.header {
  display: flex;
  align-items: center;
  height: 60px;
  padding: 0 20px;
  background-color: #001529;
  color: white;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  margin-right: 40px;
  cursor: pointer;
  transition: opacity 0.3s;
}

.logo:hover {
  opacity: 0.8;
}

.nav {
  display: flex;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  color: white;
  text-decoration: none;
}

.nav-item.active {
  background-color: #4178EE;
}

.icon-device {
  margin-right: 8px;
}

.content {
  flex: 1;
  padding: 20px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.breadcrumb {
  margin-bottom: 20px;
  color: #666;
}

.breadcrumb a {
  color: #666;
  text-decoration: none;
}

.action-bar {
  margin-bottom: 20px;
}

.add-device-btn {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.icon-plus {
  margin-right: 8px;
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.device-card {
  background: white;
  border-radius: 4px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
  color: #f56c6c;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.empty-message {
  text-align: center;
  color: #666;
  padding: 24px;
}

.empty-message p {
  margin: 8px 0 0;
  font-size: 14px;
  line-height: 1.6;
}

.icon-info {
  display: inline-block;
  width: 24px;
  height: 24px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23999'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z'/%3E%3C/svg%3E");
  background-size: contain;
  opacity: 0.6;
}

.page-header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
  height: 36px;
}

.add-btn:hover {
  background-color: #218838;
}

.icon-plus {
  font-size: 16px;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: white;
  padding: 24px;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
}

.dialog h3 {
  margin: 0 0 20px;
  font-size: 18px;
  color: #2c3e50;
}

.dialog .form-group {
  margin-bottom: 20px;
}

.dialog label {
  display: block;
  margin-bottom: 8px;
  color: #4a5568;
}

.dialog input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 16px;
}

.dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-buttons button {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.dialog-buttons button.primary {
  background-color: #28a745;
  color: white;
  border-color: #28a745;
}

.dialog-buttons button.primary:disabled {
  background-color: #90be9c;
  border-color: #90be9c;
  cursor: not-allowed;
}

.breadcrumb {
  margin-bottom: 0;
}
</style>