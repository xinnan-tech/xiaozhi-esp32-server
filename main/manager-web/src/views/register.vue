<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <!-- 保持相同的头部 -->
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img src="@/assets/xiaozhi-logo.png" alt="" style="width: 45px;height: 45px;"/>
          <img src="@/assets/xiaozhi-ai.png" alt="" style="width: 70px;height: 13px;"/>
        </div>
      </el-header>

      <el-main style="position: relative;">
        <div class="login-box">
          <!-- 修改标题部分 -->
          <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img src="@/assets/login/hi.png" alt="" style="width: 34px;height: 34px;"/>
            <div class="login-text">注册</div>
            <div class="login-welcome">
              WELCOME TO REGISTER
            </div>
          </div>

          <div style="padding: 0 30px;">
            <!-- 用户名输入框 -->
            <div class="input-box">
              <img src="@/assets/login/username.png" alt="" class="input-icon"/>
              <el-input v-model="form.username" placeholder="请输入用户名"/>
            </div>

            <!-- 密码输入框 -->
            <div class="input-box">
              <img src="@/assets/login/password.png" alt="" class="input-icon"/>
              <el-input v-model="form.password" type="password" placeholder="请输入密码"/>
            </div>

            <!-- 新增确认密码 -->
            <div class="input-box">
              <img src="@/assets/login/password.png" alt="" class="input-icon"/>
              <el-input v-model="form.confirmPassword" type="password" placeholder="请确认密码"/>
            </div>

            <!-- 验证码部分保持相同 -->
            <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
              <img 
                :src="captchaUrl" 
                alt="验证码"
                style="width: 150px; height: 40px; cursor: pointer;"
                @click="fetchCaptcha"
              />
              <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                <img src="@/assets/login/shield.png" alt="" class="input-icon"/>
                <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;"/>
              </div>
            </div>

            <!-- 修改底部链接 -->
            <div style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;margin-top: 20px;">
              <div style="cursor: pointer;" @click="goToLogin">已有账号？立即登录</div>
            </div>
          </div>

          <!-- 修改按钮文本 -->
          <div class="login-btn" @click="register">立即注册</div>
          
          <!-- 保持相同的协议声明 -->
          <div style="font-size: 14px;color: #979db1;">
            注册即同意
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《用户协议》</div>
            和
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《隐私政策》</div>
          </div>
        </div>
      </el-main>

      <!-- 保持相同的页脚 -->
      <el-footer>
        <div style="font-size: 12px;font-weight: 400;color: #979db1;">
          ©2025 xiaozhi-esp32-server
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import { showDanger, showSuccess, goToPage } from '@/utils'
import api from '@/apis/request'

export default {
  name: 'register',
  data() {
    return {
      form: {
        username: '',
        password: '',
        confirmPassword: '',
        captcha: ''
      },
      captchaUuid: '',
      captchaUrl: ''
    }
  },
  mounted() {
    this.fetchCaptcha();
  },
  methods: {
    // 复用验证码获取方法
    async fetchCaptcha() {
      this.captchaUuid = Date.now().toString()
      try {
        const response = await api.get(`/captcha?uuid=${this.captchaUuid}`, {
          responseType: 'blob',
          headers: {
            'Content-Type': 'image/gif',
            'Pragma': 'No-cache',
            'Cache-Control': 'no-cache'
          }
        });
        if (response.data) {
          const blob = new Blob([response.data], { type: response.data.type });
          this.captchaUrl = URL.createObjectURL(blob);
        }
      } catch (error) {
        console.error('验证码加载异常:', error);
        showDanger('验证码加载失败，点击刷新');
      }
    },

    // 注册逻辑
    async register() {
      if (!this.form.username.trim()) {
        showDanger('用户名不能为空')
        return
      }
      if (!this.form.password.trim()) {
        showDanger('密码不能为空')
        return
      }
      if (this.form.password !== this.form.confirmPassword) {
        showDanger('两次输入的密码不一致')
        return
      }
      if (!this.form.captcha.trim()) {
        showDanger('验证码不能为空')
        return
      }

      try {
        await api.post('/user/register', {
          username: this.form.username,
          password: this.form.password,
          captcha: this.form.captcha,
          uuid: this.captchaUuid
        })
        showSuccess('注册成功！')
        goToPage('/login')
      } catch (error) {
        const msg = error.response?.data?.msg || '注册失败'
        showDanger(msg)
        this.fetchCaptcha()
      }
    },

    goToLogin() {
      goToPage('/login')
    }
  }
}
</script>

<style scoped lang="scss">
@import './auth.scss';  // 修改为导入新建的SCSS文件
</style>