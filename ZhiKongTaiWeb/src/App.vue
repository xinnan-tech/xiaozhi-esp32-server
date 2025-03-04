<template>
  <div id="app">
    <div class="app-content">
      <router-view></router-view>
    </div>
    <Footer />
  </div>
</template>

<script>
import Footer from './components/Footer.vue';

export default {
  name: 'App',
  components: { 
    Footer 
  }
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许内容区域收缩 */
}

/* 登录注册页面的布局 */
.auth-layout {
  align-items: center;
  justify-content: center;
  padding: 20px;
}

/* 主要页面的布局 */
.main-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许内容区域收缩 */
}

/* 添加全局滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #999;
}
</style>