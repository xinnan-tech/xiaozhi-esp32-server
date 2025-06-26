<template>
  <div class="welcome" @keyup.enter="retrievePassword">
    <el-container style="height: 100%;">
      <!-- 保持相同的头部 -->
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" style="width: 45px;height: 45px;" />
          <img loading="lazy" alt="" src="@/assets/xiaozhi-ai.png" style="height: 18px;" />
        </div>
      </el-header>
      <div class="login-person">
        <img loading="lazy" alt="" src="@/assets/login/register-person.png" style="width: 100%;" />
      </div>
      <el-main style="position: relative;">
        <form @submit.prevent="retrievePassword">
          <div class="login-box">
            <!-- 修改标题部分 -->
            <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
              <img loading="lazy" alt="" src="@/assets/login/hi.png" style="width: 34px;height: 34px;" />
              <div class="login-text">重置密码</div>
              <div class="login-welcome">
                PASSWORD RETRIEVE
              </div>
            </div>

            <div style="padding: 0 30px;">
              <!-- 手机号输入 -->
              <div class="input-box">
                <div style="display: flex; align-items: center; width: 100%;">
                  <el-select v-model="form.areaCode" style="width: 220px; margin-right: 10px;">
                    <el-option v-for="item in mobileAreaList" :key="item.key" :label="`${item.name} (${item.key})`"
                      :value="item.key" />
                  </el-select>
                  <el-input v-model="form.mobile" placeholder="请输入手机号码" />
                </div>
              </div>

              <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                  <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                  <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;" />
                </div>
                <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="验证码"
                  style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
              </div>

              <!-- 手机验证码 -->
              <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                  <img loading="lazy" alt="" class="input-icon" src="@/assets/login/phone.png" />
                  <el-input v-model="form.mobileCaptcha" placeholder="请输入手机验证码" style="flex: 1;" maxlength="6" />
                </div>
                <el-button type="primary" class="send-captcha-btn" :disabled="!canSendMobileCaptcha"
                  @click="sendMobileCaptcha">
                  <span>
                    {{ countdown > 0 ? `${countdown}秒后重试` : '发送验证码' }}
                  </span>
                </el-button>
              </div>

              <!-- 新密码 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.newPassword" placeholder="请输入新密码" type="password" />
              </div>

              <!-- 确认新密码 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.confirmPassword" placeholder="请确认新密码" type="password" />
              </div>

              <!-- 修改底部链接 -->
              <div style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;margin-top: 20px;">
                <div style="cursor: pointer;" @click="goToLogin">返回登录</div>
              </div>
            </div>

            <!-- 修改按钮文本 -->
            <div class="login-btn" @click="retrievePassword">立即修改</div>

            <!-- 保持相同的协议声明 -->
            <div style="font-size: 14px;color: #979db1;">
              同意
              <div style="display: inline-block;color: #5778FF;cursor: pointer;">《用户协议》</div>
              和
              <div style="display: inline-block;color: #5778FF;cursor: pointer;">《隐私政策》</div>
            </div>
          </div>
        </form>
      </el-main>

      <!-- 保持相同的页脚 -->
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
  name: 'retrieve',
  components: {
    VersionFooter
  },
  computed: {
    ...mapState({
      allowUserRegister: state => state.pubConfig.allowUserRegister,
      mobileAreaList: state => state.pubConfig.mobileAreaList
    }),
    canSendMobileCaptcha() {
      return this.countdown === 0 && validateMobile(this.form.mobile, this.form.areaCode);
    }
  },
  data() {
    return {
      form: {
        areaCode: '+86',
        mobile: '',
        captcha: '',
        captchaId: '',
        smsCode: '',
        newPassword: '',
        confirmPassword: ''
      },
      captchaUrl: '',
      countdown: 0,
      timer: null
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
          const blob = new Blob([res.data], { type: res.data.type });
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

    // 发送手机验证码
    sendMobileCaptcha() {
      if (!validateMobile(this.form.mobile, this.form.areaCode)) {
        showDanger('请输入正确的手机号码');
        return;
      }

      // 验证图形验证码
      if (!this.validateInput(this.form.captcha, '请输入图形验证码')) {
        this.fetchCaptcha();
        return;
      }

      // 清除可能存在的旧定时器
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }

      // 开始倒计时
      this.countdown = 60;
      this.timer = setInterval(() => {
        if (this.countdown > 0) {
          this.countdown--;
        } else {
          clearInterval(this.timer);
          this.timer = null;
        }
      }, 1000);

      // 调用发送验证码接口
      Api.user.sendSmsVerification({
        phone: this.form.areaCode + this.form.mobile,
        captcha: this.form.captcha,
        captchaId: this.form.captchaId
      }, (res) => {
        showSuccess('验证码发送成功');
      }, (err) => {
        showDanger(err.data.msg || '验证码发送失败');
        this.countdown = 0;
        this.fetchCaptcha();
      });
    },

    // 修改逻辑
    retrievePassword() {
      // 验证逻辑
      if (!validateMobile(this.form.mobile, this.form.areaCode)) {
        showDanger('请输入正确的手机号码');
        return;
      }
      if (!this.form.captcha) {
        showDanger('请输入图形验证码');
        return;
      }
      if (!this.form.mobileCaptcha) {
        showDanger('请输入短信验证码');
        return;
      }
      if (this.form.newPassword !== this.form.confirmPassword) {
        showDanger('两次输入的密码不一致');
        return;
      }

      Api.user.retrievePassword({
        phone: this.form.areaCode + this.form.mobile,
        password: this.form.newPassword,
        code: this.form.mobileCaptcha
      }, (res) => {
        showSuccess('密码重置成功');
        goToPage('/login');
      }, (err) => {
        showDanger(err.data.msg || '重置失败');
        if (err.data != null && err.data.msg != null && err.data.msg.indexOf('图形验证码') > -1) {
          this.fetchCaptcha()
        }
      });
    },

    goToLogin() {
      goToPage('/login')
    }
  },
  beforeDestroy() {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }
}
</script>

<style lang="scss" scoped>
@import './auth.scss';

.send-captcha-btn {
  margin-right: -5px;
  min-width: 100px;
  height: 40px;
  line-height: 40px;
  border-radius: 4px;
  font-size: 14px;
  background: rgb(87, 120, 255);
  border: none;
  padding: 0;

  &:disabled {
    background: #c0c4cc;
    cursor: not-allowed;
  }
}
</style>
