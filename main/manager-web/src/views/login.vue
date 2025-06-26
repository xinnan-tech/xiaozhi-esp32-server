<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" style="width: 45px;height: 45px;" />
          <img loading="lazy" alt="" src="@/assets/xiaozhi-ai.png" style="height: 18px;" />
        </div>
      </el-header>
      <div class="login-person">
        <img loading="lazy" alt="" src="@/assets/login/login-person.png" style="width: 100%;" />
      </div>
      <el-main style="position: relative;">
        <div class="login-box" @keyup.enter="login">
          <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img loading="lazy" alt="" src="@/assets/login/hi.png" style="width: 34px;height: 34px;" />
            <div class="login-text">登录</div>
            <div class="login-welcome">
              WELCOME TO LOGIN
            </div>
          </div>
          <div style="padding: 0 30px;">
            <!-- 用户名登录 -->
            <template v-if="!isMobileLogin">
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/username.png" />
                <el-input v-model="form.username" placeholder="请输入用户名" />
              </div>
            </template>

            <!-- 手机号登录 -->
            <template v-else>
              <div class="input-box">
                <div style="display: flex; align-items: center; width: 100%;">
                  <el-select v-model="form.areaCode" style="width: 220px; margin-right: 10px;">
                    <el-option v-for="item in mobileAreaList" :key="item.key" :label="`${item.name} (${item.key})`"
                      :value="item.key" />
                  </el-select>
                  <el-input v-model="form.mobile" placeholder="请输入手机号码" />
                </div>
              </div>
            </template>

            <div class="input-box">
              <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
              <el-input v-model="form.password" placeholder="请输入密码" type="password" />
            </div>
            <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
              <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;" />
              </div>
              <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="验证码"
                style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
            </div>
            <div
              style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;display: flex;justify-content: space-between;margin-top: 20px;">
              <div v-if="allowUserRegister" style="cursor: pointer;" @click="goToRegister">新用户注册</div>
              <div style="cursor: pointer;" @click="goToForgetPassword" v-if="enableMobileRegister">忘记密码?</div>
            </div>
          </div>
          <div class="login-btn" @click="login">登录</div>

          <!-- 登录方式切换按钮 -->
          <div class="login-type-container" v-if="enableMobileRegister">
            <el-tooltip content="手机号码登录" placement="bottom">
              <el-button :type="isMobileLogin ? 'primary' : 'default'" icon="el-icon-mobile" circle
                @click="switchLoginType('mobile')"></el-button>
            </el-tooltip>
            <el-tooltip content="用户名登录" placement="bottom">
              <el-button :type="!isMobileLogin ? 'primary' : 'default'" icon="el-icon-user" circle
                @click="switchLoginType('username')"></el-button>
            </el-tooltip>
          </div>

          <div style="font-size: 14px;color: #979db1;">
            登录即同意
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《用户协议》</div>
            和
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《隐私政策》</div>
          </div>
        </div>
      </el-main>
      <el-footer>
        <version-footer />
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import Api from '@/apis/api';
import VersionFooter from '@/components/VersionFooter.vue';
import { getUUID, goToPage, showDanger, showSuccess, validateMobile } from '@/utils';
import { mapState } from 'vuex';

export default {
  name: 'login',
  components: {
    VersionFooter
  },
  computed: {
    ...mapState({
      allowUserRegister: state => state.pubConfig.allowUserRegister,
      enableMobileRegister: state => state.pubConfig.enableMobileRegister,
      mobileAreaList: state => state.pubConfig.mobileAreaList
    })
  },
  data() {
    return {
      activeName: "username",
      form: {
        username: '',
        password: '',
        captcha: '',
        captchaId: '',
        areaCode: '+86',
        mobile: ''
      },
      captchaUuid: '',
      captchaUrl: '',
      isMobileLogin: false
    }
  },
  mounted() {
    this.fetchCaptcha();
    this.$store.dispatch('fetchPubConfig').then(() => {
      // 根据配置决定默认登录方式
      this.isMobileLogin = this.enableMobileRegister;
    });
  },
  methods: {
    fetchCaptcha() {
      if (this.$store.getters.getToken) {
        if (this.$route.path !== '/home') {
          this.$router.push('/home')
        }
      } else {
        this.captchaUuid = getUUID();

        Api.user.getCaptcha(this.captchaUuid, (res) => {
          if (res.status === 200) {
            const blob = new Blob([res.data], { type: res.data.type });
            this.captchaUrl = URL.createObjectURL(blob);
          } else {
            showDanger('验证码加载失败，点击刷新');
          }
        });
      }
    },

    // 切换登录方式
    switchLoginType(type) {
      this.isMobileLogin = type === 'mobile';
      // 清空表单
      this.form.username = '';
      this.form.mobile = '';
      this.form.password = '';
      this.form.captcha = '';
      this.fetchCaptcha();
    },

    // 封装输入验证逻辑
    validateInput(input, message) {
      if (!input.trim()) {
        showDanger(message);
        return false;
      }
      return true;
    },

    async login() {
      if (this.isMobileLogin) {
        // 手机号登录验证
        if (!validateMobile(this.form.mobile, this.form.areaCode)) {
          showDanger('请输入正确的手机号码');
          return;
        }
        // 拼接手机号作为用户名
        this.form.username = this.form.areaCode + this.form.mobile;
      } else {
        // 用户名登录验证
        if (!this.validateInput(this.form.username, '用户名不能为空')) {
          return;
        }
      }

      // 验证密码
      if (!this.validateInput(this.form.password, '密码不能为空')) {
        return;
      }
      // 验证验证码
      if (!this.validateInput(this.form.captcha, '验证码不能为空')) {
        return;
      }

      this.form.captchaId = this.captchaUuid
      Api.user.login(this.form, ({ data }) => {
        showSuccess('登录成功！');
        this.$store.commit('setToken', JSON.stringify(data.data));
        goToPage('/home');
      }, (err) => {
        showDanger(err.data.msg || '登录失败')
        if (err.data != null && err.data.msg != null && err.data.msg.indexOf('图形验证码') > -1) {
          this.fetchCaptcha()
        }
      })

      // 重新获取验证码
      setTimeout(() => {
        this.fetchCaptcha();
      }, 1000);
    },

    goToRegister() {
      goToPage('/register')
    },
    goToForgetPassword() {
      goToPage('/retrieve-password')
    },
  }
}
</script>
<style lang="scss" scoped>
@import './auth.scss';

.login-type-container {
  margin: 10px 20px;
}

:deep(.el-button--primary) {
  background-color: #5778ff;
  border-color: #5778ff;

  &:hover,
  &:focus {
    background-color: #4a6ae8;
    border-color: #4a6ae8;
  }

  &:active {
    background-color: #3d5cd6;
    border-color: #3d5cd6;
  }
}
</style>
