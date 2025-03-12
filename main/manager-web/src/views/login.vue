<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <el-header>
        <div
            style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img src="@/assets/xiaozhi-logo.png" alt="" style="width: 45px;height: 45px;"/>
          <img src="@/assets/xiaozhi-ai.png" alt="" style="width: 70px;height: 13px;"/>
        </div>
      </el-header>
      <el-main style="position: relative;">
        <div class="login-box">
          <div
              style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img src="@/assets/login/hi.png" alt="" style="width: 34px;height: 34px;"/>
            <div class="login-text">登录</div>
            <div class="login-welcome">
              WELCOME TO LOGIN
            </div>
          </div>
          <div style="padding: 0 30px;">
            <div class="input-box">
              <img src="@/assets/login/username.png" alt="" class="input-icon"/>
              <el-input v-model="form.username" placeholder="请输入用户名"/>
            </div>
            <div class="input-box">
              <img src="@/assets/login/password.png" alt="" class="input-icon"/>
              <el-input v-model="form.password" type="password" placeholder="请输入密码"/>
            </div>
            <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
              <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                <img src="@/assets/login/shield.png" alt="" class="input-icon"/>
                <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;"/>
              </div>
              <img v-if="captchaUrl"
                   :src="captchaUrl"
                   alt="验证码"
                   style="width: 150px; height: 40px; cursor: pointer;"
                   @click="fetchCaptcha"
              />
            </div>
            <div
                style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;display: flex;justify-content: space-between;margin-top: 20px;">
              <div style="cursor: pointer;" @click="goToRegister">新用户注册</div>
            </div>
          </div>
          <div class="login-btn" @click="login">登陆</div>
          <div style="font-size: 14px;color: #979db1;">
            登录即同意
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《用户协议》</div>
            和
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《隐私政策》</div>
          </div>
        </div>
      </el-main>
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
  name: 'login',
  data() {
    return {
      activeName: "username",
      form: {
        username: '',
        password: '',
        captcha: '',
        captchaId: ''
      },
      captchaUuid: '',
      captchaUrl: ''
    }
  },
  mounted() {
    this.fetchCaptcha();
  },
  methods: {
    fetchCaptcha() {
      this.captchaUuid = getUUID();

      Api.user.getCaptcha(this.captchaUuid, (res) => {
        if (res.status === 200) {
          const blob = new Blob([res.data], {type: res.data.type});
          this.captchaUrl = URL.createObjectURL(blob);

        } else {
          console.error('验证码加载异常:', error);
          showDanger('验证码加载失败，点击刷新')
        }
      });
    },

    async login() {
      if (!this.form.username.trim()) {  // 替换isNull校验
        showDanger('用户名不能为空')
        return
      }
      if (!this.form.password.trim()) {  // 替换isNull校验
        showDanger('密码不能为空')
        return
      }
      if (!this.form.captcha.trim()) {  // 替换isNull校验
        showDanger('验证码不能为空')
        return
      }

      this.form.captchaId = this.captchaUuid
      Api.user.login(this.form, ({data}) => {
        console.log(data)
        showSuccess('登陆成功！')
        goToPage('/home')
      })
      setTimeout(() => {
        this.fetchCaptcha()
      }, 1000)
    },

    goToRegister() {
      goToPage('/register')
    }
  }
}
</script>
<style scoped lang="scss">
@import './auth.scss'; // 添加这行引用
</style>
