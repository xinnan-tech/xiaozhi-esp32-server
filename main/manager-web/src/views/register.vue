<template>
  <div class="welcome" @keyup.enter="register">
    <el-container style="height: 100%;">
      <!-- Keep the same header -->
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.svg" style="width: 45px;height: 45px;" />
          <!-- <img loading="lazy" alt="" src="@/assets/xiaozhi-ai.png" style="height: 18px;" /> -->
        </div>
      </el-header>
      <div class="login-person">
        <img loading="lazy" alt="" src="@/assets/login/register-person.png" style="width: 100%;" />
      </div>
      <el-main style="position: relative;">
        <div class="login-box">
          <!-- Title section -->
          <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img loading="lazy" alt="" src="@/assets/login/hi.png" style="width: 34px;height: 34px;" />
            <div class="login-text">Register</div>
            <div class="login-welcome">
              WELCOME TO REGISTER
            </div>
          </div>

          <div style="padding: 0 30px;">
            <form @submit.prevent="register">
              <!-- Username/phone input box -->
              <div class="input-box" v-if="!enableMobileRegister">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/username.png" />
                <el-input v-model="form.username" placeholder="Enter username" />
              </div>

              <!-- Mobile registration section -->
              <template v-if="enableMobileRegister">
                <div class="input-box">
                  <div style="display: flex; align-items: center; width: 100%;">
                    <el-select v-model="form.areaCode" style="width: 220px; margin-right: 10px;">
                      <el-option v-for="item in mobileAreaList" :key="item.key" :label="`${item.name} (${item.key})`"
                        :value="item.key" />
                    </el-select>
                    <el-input v-model="form.mobile" placeholder="Enter phone number" />
                  </div>
                </div>

                <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                  <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                    <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                    <el-input v-model="form.captcha" placeholder="Enter verification code" style="flex: 1;" />
                  </div>
                  <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="Captcha"
                    style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
                </div>

                <!-- Mobile verification code -->

                <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                  <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                    <img loading="lazy" alt="" class="input-icon" src="@/assets/login/phone.png" />
                    <el-input v-model="form.mobileCaptcha" placeholder="Enter SMS code" style="flex: 1;" maxlength="6" />
                  </div>
                  <el-button type="primary" class="send-captcha-btn" :disabled="!canSendMobileCaptcha"
                    @click="sendMobileCaptcha">
                    <span>
                      {{ countdown > 0 ? `Retry in ${countdown}s` : 'Send Code' }}
                    </span>
                  </el-button>
                </div>
              </template>

              <!-- Password input box -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.password" placeholder="Enter password" type="password" show-password />
              </div>

              <!-- Confirm password -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.confirmPassword" placeholder="Confirm password" type="password" show-password />
              </div>

              <!-- Captcha section -->
              <div v-if="!enableMobileRegister"
                style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                  <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                  <el-input v-model="form.captcha" placeholder="Enter verification code" style="flex: 1;" />
                </div>
                <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="Captcha"
                  style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
              </div>

              <!-- Bottom link -->
              <div style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;margin-top: 20px;">
                <div style="cursor: pointer;" @click="goToLogin">Already have an account? Login now</div>
              </div>
            </form>
          </div>

          <!-- Button text -->
          <div class="login-btn" @click="register">Register Now</div>

          <!-- Agreement declaration -->
          <div style="font-size: 14px;color: #979db1;">
            By registering, you agree to the
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">Terms of Service</div>
            and
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">Privacy Policy</div>
          </div>
        </div>
      </el-main>

      <!-- Footer -->
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
  name: 'register',
  components: {
    VersionFooter
  },
  computed: {
    ...mapState({
      allowUserRegister: state => state.pubConfig.allowUserRegister,
      enableMobileRegister: state => state.pubConfig.enableMobileRegister,
      mobileAreaList: state => state.pubConfig.mobileAreaList
    }),
    canSendMobileCaptcha() {
      return this.countdown === 0 && validateMobile(this.form.mobile, this.form.areaCode);
    }
  },
  data() {
    return {
      form: {
        username: '',
        password: '',
        confirmPassword: '',
        captcha: '',
        captchaId: '',
        areaCode: '+86',
        mobile: '',
        mobileCaptcha: ''
      },
      captchaUrl: '',
      countdown: 0,
      timer: null
    }
  },
  mounted() {
    this.$store.dispatch('fetchPubConfig').then(() => {
      if (!this.allowUserRegister) {
        showDanger('User registration is currently not allowed');
        setTimeout(() => {
          goToPage('/login');
        }, 1500);
      }
    });
    this.fetchCaptcha();
  },
  methods: {
    // Reuse captcha fetch method
    fetchCaptcha() {
      this.form.captchaId = getUUID();
      Api.user.getCaptcha(this.form.captchaId, (res) => {
        if (res.status === 200) {
          const blob = new Blob([res.data], { type: res.data.type });
          this.captchaUrl = URL.createObjectURL(blob);

        } else {
          console.error('Captcha loading error:', error);
          showDanger('Failed to load captcha, click to refresh');
        }
      });
    },

    // Encapsulate input validation logic
    validateInput(input, message) {
      if (!input.trim()) {
        showDanger(message);
        return false;
      }
      return true;
    },

    // Send mobile verification code
    sendMobileCaptcha() {
      if (!validateMobile(this.form.mobile, this.form.areaCode)) {
        showDanger('Please enter a valid phone number');
        return;
      }

      // Verify captcha
      if (!this.validateInput(this.form.captcha, 'Please enter the captcha')) {
        this.fetchCaptcha();
        return;
      }

      // Clear any existing timer
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }

      // Start countdown
      this.countdown = 60;
      this.timer = setInterval(() => {
        if (this.countdown > 0) {
          this.countdown--;
        } else {
          clearInterval(this.timer);
          this.timer = null;
        }
      }, 1000);

      // Call send verification code API
      Api.user.sendSmsVerification({
        phone: this.form.areaCode + this.form.mobile,
        captcha: this.form.captcha,
        captchaId: this.form.captchaId
      }, (res) => {
        showSuccess('Verification code sent successfully');
      }, (err) => {
        showDanger(err.data.msg || 'Failed to send verification code');
        this.countdown = 0;
        this.fetchCaptcha();
      });
    },

    // Registration logic
    register() {
      if (this.enableMobileRegister) {
        // Mobile registration validation
        if (!validateMobile(this.form.mobile, this.form.areaCode)) {
          showDanger('Please enter a valid phone number');
          return;
        }
        if (!this.form.mobileCaptcha) {
          showDanger('Please enter the SMS verification code');
          return;
        }
      } else {
        // Username registration validation
        if (!this.validateInput(this.form.username, 'Username cannot be empty')) {
          return;
        }
      }

      // Validate password
      if (!this.validateInput(this.form.password, 'Password cannot be empty')) {
        return;
      }
      if (this.form.password !== this.form.confirmPassword) {
        showDanger('Passwords do not match')
        return
      }
      // Validate captcha
      if (!this.validateInput(this.form.captcha, 'Verification code cannot be empty')) {
        return;
      }

      if (this.enableMobileRegister) {
        this.form.username = this.form.areaCode + this.form.mobile
      }

      Api.user.register(this.form, ({ data }) => {
        showSuccess('Registration successful!')
        goToPage('/login')
      }, (err) => {
        showDanger(err.data.msg || 'Registration failed')
        if (err.data != null && err.data.msg != null && (err.data.msg.indexOf('captcha') > -1 || err.data.msg.indexOf('图形验证码') > -1)) {
          this.fetchCaptcha()
        }
      })
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
  padding: 0px;

  &:disabled {
    background: #c0c4cc;
    cursor: not-allowed;
  }
}
</style>
