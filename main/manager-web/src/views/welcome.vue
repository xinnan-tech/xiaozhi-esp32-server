<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <el-header>
        <div
          style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img src="@/assets/xiaozhi-logo.png" alt="" style="width: 45px;height: 45px;" />
          <img src="@/assets/xiaozhi-ai.png" alt="" style="width: 70px;height: 13px;" />
        </div>
      </el-header>
      <el-main style="position: relative;">
        <div style="margin-left: 18%;position: absolute;top: 50%;transform: translateY(-50%);margin-top: -20px">
          <div style="display: flex;align-items: center;margin-bottom: 27px;">
            <div class="left-pillar" />
            <div class="hi-text-bg" />
            <div class="hi-text">Hi，你好</div>
          </div>
          <div class="introduction">让我们一起探索</div>
          <div class="introduction">人工智能与机器人技术</div>
          <div class="introduction">的迷人世界！</div>

          <!-- 副标题 -->
          <p class="english-subtitle">Let's explore the fascinating world</p>

          <!-- 按钮 -->
          <div style="margin-top: 60px;display: flex;gap: 20px;">
            <div class="btn">
              <img src="@/assets/welcome/questions.png" alt="" class="btn-icon" />
              DIY教程
            </div>
            <div class="btn">
              <img src="@/assets/welcome/github.png" alt="" class="btn-icon" />
              GitHub
            </div>
            <div class="btn" style="background: #5778ff;color: #fff;" @click="jumpHome">
              <img src="@/assets/welcome/more.png" alt="" class="btn-icon" />
              控制台
            </div>
          </div>

        </div>
      </el-main>
      <el-footer>
        <div style="font-size: 12px;font-weight: 400;color: #3D4566">
          ©2025 xiaozhi-esp32-server</div>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
// @ is an alias to /src

export default {
  name: 'home',
  methods:{
    jumpHome(){
      this.$router.push('/home')
    }
  }
}
</script>
<style scoped lang="scss">
.welcome {
  min-width: 1200px;
  min-height: 675px;
  height: 100vh;
  background-image: url("@/assets/welcome/background.png");
  background-size: cover;
  /* 确保背景图像覆盖整个元素 */
  background-position: center;
  /* 从顶部中心对齐 */
  -webkit-background-size: cover;
  /* 兼容老版本WebKit浏览器 */
  -o-background-size: cover;
  /* 兼容老版本Opera浏览器 */
}
.left-pillar {
  width: 4px;
  height: 36px;
  background: #5778ff;
}
.hi-text-bg {
  width: 129px;
  height: 36px;
  background: linear-gradient(90.66deg, #5778ff 0%, #f5f6fa00 100%);
  opacity: 0.5;
}
.hi-text {
  line-height: 36px;
  font-weight: 700;
  font-size: 14px;
  text-align: left;
  color: #3d4566;
  padding-left: 14px;
  position: absolute;
}
.introduction {
  font-weight: 700;
  font-size: 42px;
  text-align: left;
  color: #3d4566;
}
.btn {
  width: 100px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: 28px;
  display: flex;
  gap: 10px;
  font-weight: 400;
  font-size: 12px;
  text-align: left;
  color: #3d4566;
  cursor: pointer;
  background-color: #fff;
}
.btn-icon {
  width: 12px;
  height: 12px;
}
.english-subtitle {
  font-size: 11px;
  color: #818cae;
  text-align: left;
  margin-top: 5px;
  position: relative;
  top: 8px;
}
</style>
