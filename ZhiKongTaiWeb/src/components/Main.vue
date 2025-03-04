<template>
  <div class="main-container">
    <NavBar current-tab="home" @tab-change="handleTabChange"/>
    <div class="landing-page">
      <div class="content">
        <div class="robot-image">
          <img src="../assets/robot.png" alt="Robot mascot" />
        </div>
        
        <h1 class="slogan">让我们一起探索人工智能与机器人技术的迷人世界！</h1>
        
        <div class="button-group">
          <button class="action-button tutorial-button" @click="openTutorial">
            <i class="icon-tutorial"></i> DIY 教程
          </button>
          
          <button class="action-button github-button" @click="openGithubClient">
            <i class="icon-github"></i> Github客户端
          </button>

          <button class="action-button github-button" @click="openGithubServer">
            <i class="icon-github"></i> Github服务端
          </button>

          <button class="action-button github-button" @click="openGithubWeb">
            <i class="icon-github"></i> Web客户端
          </button>
          
          <button class="action-button control-panel-button" @click="enterPanel">
            <i class="icon-control-panel"></i> 控制台
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import NavBar from './NavBar.vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const openTutorial = () => {
  window.open('https://ccnphfhqs21z.feishu.cn/wiki/F5krwD16viZoF0kKkvDcrZNYnhb', '_blank');
};

const openGithubClient = () => {
  window.open('https://github.com/78/xiaozhi-esp32', '_blank');
};

const openGithubServer = () => {
  window.open('https://github.com/xinnan-tech/xiaozhi-esp32-server', '_blank');
};

const openGithubWeb = () => {
  window.open('https://github.com/TOM88812/xiaozhi-web-client', '_blank');
};

const enterPanel = () => {
  router.push('/panel');
};

const handleTabChange = (tab) => {
  if (tab === 'device') {
    router.push('/panel');
  }
};
</script>

<style scoped>
.main-container {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.landing-page {
  flex: 1;
  width: 100%;
  background-color: #f5f7fa;
  padding: 40px 20px;
  overflow: hidden;
  display: flex;
  align-items: flex-start; /* 改为flex-start */
  justify-content: center;
  padding-top: 15vh; /* 添加顶部内边距，视窗高度的15% */
}

.content {
  max-width: 800px;
  text-align: center;
  padding: 0 20px;
  margin: 0 auto; /* 改为0 auto */
}

.robot-image {
  margin-bottom: 30px; /* 减小间距 */
}

.robot-image img {
  width: 100px; /* 稍微调小图片尺寸 */
  height: auto;
}

.slogan {
  font-size: 22px; /* 稍微调小字体 */
  line-height: 1.4;
  color: #333;
  margin-bottom: 40px; /* 减小间距 */
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 15px; /* 减小按钮间距 */
  margin: 0 auto;
}

.action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 24px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background-color: white;
  color: #333;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tutorial-button i:before {
  content: '\1F4D6';
  margin-right: 8px;
}

.github-button {
  background-color: #24292e;
  color: white;
  border-color: #24292e;
  margin: 0 10px; /* 添加按钮间距 */
}

.github-button i:before {
  content: '\f09b';
  font-family: 'Font Awesome 5 Brands';
  margin-right: 8px;
}

.control-panel-button {
  background-color: #4178EE;
  color: white;
  border-color: #4178EE;
}

.control-panel-button i:before {
  content: '\1F39B';
  margin-right: 8px;
}

@media (max-width: 600px) {
  .button-group {
    flex-direction: column;
  }
  
  .action-button {
    width: 100%;
  }
}

/* 移除 margin-top: 60px */
#app {
  margin-top: 0;
}
</style>