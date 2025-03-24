<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <!-- 保持相同的头部 -->
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img alt="" src="@/assets/xiaozhi-logo.png" style="width: 45px;height: 45px;"/>
          <img alt="" src="@/assets/xiaozhi-ai.png" style="width: 70px;height: 13px;"/>
        </div>
      </el-header>

      <el-main style="position: relative;">
        <div class="login-box">
          <!-- 修改标题部分 -->
          <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img alt="" src="@/assets/login/hi.png" style="width: 34px;height: 34px;"/>
            <div class="login-text">注册</div>
            <div class="login-welcome">
              WELCOME TO REGISTER
            </div>
          </div>

          <div style="padding: 0 30px;">
            <!-- 用户名输入框 -->
            <div class="input-box">
              <img alt="" class="input-icon" src="@/assets/login/username.png"/>
              <el-input v-model="form.username" placeholder="请输入用户名"/>
            </div>

            <!-- 密码输入框 -->
            <div class="input-box">
              <img alt="" class="input-icon" src="@/assets/login/password.png"/>
              <el-input v-model="form.password" placeholder="请输入密码" type="password"/>
            </div>

            <!-- 新增确认密码 -->
            <div class="input-box">
              <img alt="" class="input-icon" src="@/assets/login/password.png"/>
              <el-input v-model="form.confirmPassword" placeholder="请确认密码" type="password"/>
            </div>

            <!-- 验证码部分保持相同 -->
            <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
              <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                <img alt="" class="input-icon" src="@/assets/login/shield.png"/>
                <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;"/>
              </div>
              <img v-if="captchaUrl"
                   :src="captchaUrl"
                   alt="验证码"
                   style="width: 150px; height: 40px; cursor: pointer;"
                   @click="fetchCaptcha"
              />
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
import {getUUID, goToPage, showDanger, showSuccess} from '@/utils'
import Api from '@/apis/api';

export default {
  name: 'register',
  data() {
    return {
      form: {
        username: '',
        password: '',
        confirmPassword: '',
        captcha: '',
        captchaId: ''
      },
      captchaUrl: ''
    }
  },
  mounted() {
    this.fetchCaptcha();
  },
  methods: {
    // 复用验证码获取方法
    fetchCaptcha() {
      this.form.captchaId = getUUID();
      Api.user.getCaptcha(this.form.captchaId, (res) => {
        if (res.status === 200) {
          const blob = new Blob([res.data], {type: res.data.type});
          this.captchaUrl = URL.createObjectURL(blob);

        } else {
          console.error('验证码加载异常:', error);
          showDanger('验证码加载失败，点击刷新');
        }
      });
    },

    // 封装输入验证逻辑
    validateInput(input, message) {
      if (!input.trim()) {
        showDanger(message);
        return false;
      }
      return true;
    },
    // 注册逻辑
    register() {
      // 验证用户名
      if (!this.validateInput(this.form.username, '用户名不能为空')) {
        return;
      }
      // 验证密码
      if (!this.validateInput(this.form.password, '密码不能为空')) {
        return;
      }
      if (this.form.password !== this.form.confirmPassword) {
        showDanger('两次输入的密码不一致')
        return
      }
      // 验证验证码
      if (!this.validateInput(this.form.captcha, '验证码不能为空')) {
        return;
      }

      Api.user.register(this.form, ({data}) => {
        console.log(data)
        if (data.code === 0) {
          showSuccess('注册成功！')
          goToPage('/login')
        } else {
          showDanger(data.msg || '注册失败')
          this.fetchCaptcha()
        }
      })
      setTimeout(() => {
        this.fetchCaptcha()
      }, 1000)
    },

    goToLogin() {
      goToPage('/login')
    }
  }
}
</script>

<style lang="scss" scoped>
@import './auth.scss'; // 修改为导入新建的SCSS文件
</style>
