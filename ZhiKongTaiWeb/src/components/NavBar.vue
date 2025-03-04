<template>
      <!-- 顶部导航栏 -->
      <header class="header">
      <div class="logo-container">
        <div class="logo">
          <img src="../assets/robot.png" alt="小智AI" />
        </div>
       <span class="logo-text"><router-link to="/">小智.AI</router-link></span>
      </div>
      
      <div class="nav-buttons">
        <button class="nav-button active" @click="enterPanel">
          <span class="icon">⚙️</span>
          设备管理
        </button>
      </div>
    
    </header>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();

const switchTab = (path) => {
  router.push(path);
};
const enterPanel = () => {
  router.push('/panel');
};

</script>


<style scoped>
.header {
  display: flex;
  align-items: center;
  height: 60px;
  padding: 0;
  background-color: #001529;
  color: white;
  width: 100%;
  position: relative;
  left: 0;
  right: 0;
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
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.3s;
}

.active {
  background-color: #4178EE;
}

.icon-device {
  margin-right: 8px;
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

</style>
