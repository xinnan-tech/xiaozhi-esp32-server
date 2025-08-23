<template>
  <div class="home-page">
    <div class="header">
      <h1>Smart Manager System</h1>
      <p>Manager Mobile</p>
    </div>
    
    <div class="menu-grid">
      <div class="menu-item" @click="goTo('/pages/device/index')">
        <div class="icon">📱</div>
        <div class="label">Device Management</div>
      </div>
      
      <div class="menu-item" @click="goTo('/pages/agent/index')">
        <div class="icon">🤖</div>
        <div class="label">AI Agents</div>
      </div>
      
      <div class="menu-item" @click="goTo('/pages/chat-history/index')">
        <div class="icon">💬</div>
        <div class="label">Chat History</div>
      </div>
      
      <div class="menu-item" @click="goTo('/pages/voiceprint/index')">
        <div class="icon">🎤</div>
        <div class="label">Voiceprint</div>
      </div>
      
      <div class="menu-item" @click="goTo('/pages/settings/index')">
        <div class="icon">⚙️</div>
        <div class="label">Settings</div>
      </div>
      
      <div class="menu-item" @click="logout">
        <div class="icon">🚪</div>
        <div class="label">Logout</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goTo = (path: string) => {
  router.push(path)
}

const logout = () => {
  if (confirm('Are you sure you want to logout?')) {
    localStorage.removeItem('token')
    router.push('/pages/login/index')
  }
}
</script>

<style scoped>
.home-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 40px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
}

.header h1 {
  margin: 0 0 10px 0;
  font-size: 28px;
}

.header p {
  margin: 0;
  opacity: 0.9;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.menu-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.menu-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.2);
  border-color: #667eea;
}

.menu-item .icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.menu-item .label {
  font-size: 16px;
  color: #333;
  font-weight: 500;
}
</style>