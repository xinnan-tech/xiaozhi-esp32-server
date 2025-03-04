<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="logo-container">
        <div class="logo">
          <img src="../assets/robot.png" alt="小智AI" />
        </div>
       <span class="logo-text"><router-link to="/">小智.AI</router-link></span>
        <!-- <span class="logo-text">小智.AI</span> -->
      </div>
      
      <div class="nav-buttons">
        <button class="nav-button active">
          <span class="icon">⚙️</span>
          设备管理
        </button>
      </div>
      <div class="search-container">
        <input 
          type="text" 
          class="search-input" 
          placeholder="输入关键搜索..." 
          v-model="searchQuery"
        />
        <button class="search-button">🔍</button>
      </div>
      
      <div class="user-info">
        <div class="user-avatar">👤</div>
        <span class="user-notification">158</span>
        <span class="user-balance">B642</span>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <main class="main-content">
      <!-- 欢迎横幅 -->
      <section class="welcome-banner">
        <div class="welcome-text">
          <h1>您好，小智</h1>
          <h2>让我们度过<span class="highlight">美好的一天</span>！</h2>
          <p class="subtitle">Hello, Let's have a wonderful day!</p>
          
          <button class="add-device-btn" @click="showBindDialog = true">
            添加设备
            <span class="arrow">→</span>
          </button>
        </div>
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
        <div class="welcome-image">
          <img src="../assets/welcome_banner.png" alt="AI图像" />
        </div>
      </section>

      <!-- 设备卡片网格 -->
      <section class="device-grid">
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
      </section>

      <!-- 分页控制 -->
      <div class="pagination">
        <button class="pagination-btn prev">
          <span class="arrow">←</span>
        </button>
        <button class="pagination-btn next">
          <span class="arrow">→</span>
        </button>
      </div>
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

<style>
:root {
  --primary-color: #4e6ef2;
  --secondary-color: #f0f4ff;
  --text-color: #333;
  --light-text: #666;
  --lighter-text: #999;
  --border-color: #eaeaea;
  --card-bg: #fff;
  --hover-color: #e6f0ff;
  --gradient-start: #4e6ef2;
  --gradient-end: #7986cb;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

body {
  background-color: #f5f7fa;
  color: var(--text-color);
  line-height: 1.6;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  max-width: 100%;
  margin: 0 auto;
}

/* 顶部导航栏样式 */
.header {
  display: flex;
  align-items: center;
  padding: 0.8rem 1.5rem;
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo-container {
  display: flex;
  align-items: center;
  margin-right: 2rem;
}

.logo {
  width: 2rem;
  height: 2rem;
  margin-right: 0.5rem;
  display: flex;
  align-items: center;
}

.logo img {
  width: 100%;
  height: auto;
}

.logo-text {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--text-color);
}

.nav-buttons {
  display: flex;
  align-items: center;
  flex-grow: 1;
}

.nav-button {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  margin-right: 1rem;
}

.nav-button .icon {
  margin-right: 0.5rem;
}

.tab-container {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-size: 0.9rem;
}

.tab-item {
  margin-right: 0.5rem;
}

.tab-close {
  cursor: pointer;
  font-weight: bold;
}

.search-container {
  display: flex;
  align-items: center;
  background-color: var(--secondary-color);
  border-radius: 20px;
  padding: 0.3rem 0.8rem;
  margin: 0 1rem;
  flex-grow: 0.5;
  max-width: 400px;
}

.search-input {
  border: none;
  background: transparent;
  flex-grow: 1;
  padding: 0.5rem;
  outline: none;
  font-size: 0.9rem;
}

.search-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-avatar {
  width: 2rem;
  height: 2rem;
  background-color: #e0e0e0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 1rem;
}

.user-notification, .user-balance {
  background-color: #f0f0f0;
  padding: 0.3rem 0.8rem;
  border-radius: 15px;
  font-size: 0.8rem;
  margin-left: 0.5rem;
}

/* 主要内容区域样式 */
.main-content {
  flex-grow: 1;
  padding: 1.5rem;
  background-color: #f5f7fa;
}

/* 欢迎横幅样式 */
.welcome-banner {
  display: flex;
  background: linear-gradient(135deg, #f0f4ff 0%, #e6f0ff 100%);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  position: relative;
  min-height: 200px; /* 原高度300px缩减为200px */
}

.welcome-text {
  padding: 1.8rem; /* 原2.5rem减少28% */
  flex: 1;
}

.welcome-text h1 {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.welcome-text h2 {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.highlight {
  color: var(--primary-color);
}

.subtitle {
  color: var(--light-text);
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}

.add-device-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.7rem 1.5rem;
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 25px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.add-device-btn:hover {
  background-color: #3d5bd9;
  transform: translateY(-2px);
}

.arrow {
  margin-left: 0.5rem;
}

.welcome-image {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.welcome-image img {
  width: 100%;
  height: 100%;
  object-fit: cover; /* 改为cover保持图片比例 */
  opacity: 0.2;
}

/* 设备卡片网格样式 */
.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

/* 分页控制样式 */
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

.pagination-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: white;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin: 0 0.5rem;
  transition: all 0.2s ease;
}

.pagination-btn:hover {
  background-color: var(--hover-color);
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
/* 响应式设计 */
@media (max-width: 1200px) {
  .welcome-banner {
    flex-direction: column;
    min-height: 160px; /* 同步降低响应式高度 */
  }
  
  .welcome-image {
    height: 120px; /* 原200px缩减为120px */
  }
}

@media (max-width: 768px) {
  .header {
    flex-wrap: wrap;
  }
  
  .search-container {
    order: 3;
    width: 100%;
    margin: 1rem 0 0;
    max-width: none;
  }
  
  .device-grid {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  }
  
  .welcome-text h1 {
    font-size: 1.5rem;
  }
  
  .welcome-text h2 {
    font-size: 1.7rem;
  }
}

@media (max-width: 576px) {
  .header {
    padding: 0.5rem;
  }
  
  .logo-text {
    display: none;
  }
  
  .nav-button {
    padding: 0.4rem 0.8rem;
    font-size: 0.8rem;
  }
  
  .tab-container {
    display: none;
  }
  
  .user-notification, .user-balance {
    padding: 0.2rem 0.5rem;
    font-size: 0.7rem;
  }
  
  .welcome-text {
    padding: 1.5rem;
  }
  
  .device-grid {
    grid-template-columns: 1fr;
  }
}
</style>


