<template>
  <header class="header">
    <div class="nav-item" :class="{ active: $route.path === '/' }" @click="switchTab('/')">小智 AI</div>
    <nav class="nav">
      <div class="nav-item" :class="{ active: $route.path === '/panel' }" @click="switchTab('/panel')">
        <i class="icon-device"></i> 设备管理
      </div>
    </nav>
  </header>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();

const switchTab = (path) => {
  router.push(path);
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
</style>
