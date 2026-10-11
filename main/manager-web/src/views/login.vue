<template>
  <div class="welcome">
    <el-container style="height: 100%">
      <el-header>
        <div style="
            display: flex;
            align-items: center;
            margin-top: 15px;
            margin-left: 10px;
            gap: 10px;
          ">
          <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" style="width: 45px; height: 45px" />
        </div>
      </el-header>
      <div class="login-person">
        <img loading="lazy" alt="" src="@/assets/login/login-person.png" style="width: 100%" />
      </div>
      <el-main style="position: relative">
        <div class="login-box" @keyup.enter="login">
          <div style="
              display: flex;
              align-items: center;
              gap: 20px;
              margin-bottom: 39px;
              padding: 0 30px;
            ">
            <img loading="lazy" alt="" src="@/assets/login/hi.png" style="width: 34px; height: 34px" />
            <div class="login-text">{{ $t("login.title") }}</div>

            <div class="login-welcome">
              {{ $t("login.welcome") }}
            </div>

            <!-- Language switching dropdown menu -->
            <el-dropdown trigger="click" class="title-language-dropdown"
              @visible-change="handleLanguageDropdownVisibleChange">
              <span class="el-dropdown-link">
                <span class="current-language-text">{{ currentLanguageText }}</span>
                <i class="el-icon-arrow-down el-icon--right" :class="{ 'rotate-down': languageDropdownVisible }"></i>
              </span>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item v-for="lang in languageOptions" :key="lang.code"
                  @click.native="changeLanguage(lang.code)">
                  {{ $t(lang.labelKey) }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </el-dropdown>
          </div>
          <div style="padding: 0 30px">
            <!-- Username login -->
            <template v-if="!isMobileLogin">
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/username.png" />
                <el-input v-model="form.username" :placeholder="$t('login.usernamePlaceholder')" />
              </div>
            </template>

            <!-- Mobile number login -->
            <template v-else>
              <div class="input-box">
                <div style="display: flex; align-items: center; width: 100%">
                  <el-select v-model="form.areaCode" style="width: 220px; margin-right: 10px" filterable>
                    <el-option v-for="item in mobileAreaList" :key="item.key" :label="`${item.name} (${item.key})`"
                      :value="item.key" />
                  </el-select>
                  <el-input v-model="form.mobile" :placeholder="$t('login.mobilePlaceholder')" />
                </div>
              </div>
            </template>

            <div class="input-box">
              <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
              <el-input v-model="form.password" :placeholder="$t('login.passwordPlaceholder')" type="password"
                show-password />
            </div>
            <div style="
                display: flex;
                align-items: center;
                margin-top: 20px;
                width: 100%;
                gap: 10px;
              ">
              <div class="input-box" style="width: calc(100% - 130px); margin-top: 0">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                <el-input v-model="form.captcha" :placeholder="$t('login.captchaPlaceholder')" style="flex: 1" />
              </div>
              <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="Captcha"
                style="width: 150px; height: 40px; cursor: pointer" @click="fetchCaptcha" />
            </div>
            <div style="
                font-weight: 400;
                font-size: 14px;
                text-align: left;
                color: #5778ff;
                display: flex;
                justify-content: space-between;
                margin-top: 20px;
              ">
              <div v-if="allowUserRegister" style="cursor: pointer" @click="goToRegister">
                {{ $t("login.register") }}
              </div>
              <div style="cursor: pointer" @click="goToForgetPassword" v-if="enableMobileRegister">
                {{ $t("login.forgetPassword") }}
              </div>
            </div>
          </div>
          <div class="login-btn" @click="login">{{ $t("login.login") }}</div>

          <!-- Login method switching button -->
          <div class="login-type-container" v-if="enableMobileRegister">
            <div style="display: flex; gap: 10px">
              <el-tooltip :content="$t('login.mobileLogin')" placement="bottom">
                <el-button :type="isMobileLogin ? 'primary' : 'default'" icon="el-icon-mobile" circle
                  @click="switchLoginType('mobile')"></el-button>
              </el-tooltip>
              <el-tooltip :content="$t('login.usernameLogin')" placement="bottom">
                <el-button :type="!isMobileLogin ? 'primary' : 'default'" icon="el-icon-user" circle
                  @click="switchLoginType('username')"></el-button>
              </el-tooltip>
            </div>
          </div>
          <div style="font-size: 14px; color: #979db1">
            {{ $t("login.agreeTo") }}
            <div style="display: inline-block; color: #5778ff; cursor: pointer"
              @click="openPage('/user-agreement-en.html')">
              {{ $t("login.userAgreement") }}
            </div>
            {{ $t("login.and") }}
            <div style="display: inline-block; color: #5778ff; cursor: pointer"
              @click="openPage('/privacy-policy-en.html')">
              {{ $t("login.privacyPolicy") }}
            </div>
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
import Api from "@/apis/api";
import VersionFooter from "@/components/VersionFooter.vue";
import i18n, { changeLanguage, supportedLanguages, getLanguageLabelKey } from "@/i18n";
import { getUUID, goToPage, showDanger, showSuccess, sm2Encrypt, validateMobile } from "@/utils";
import { mapState } from "vuex";

export default {
  name: "login",
  components: {
    VersionFooter,
  },
  computed: {
    ...mapState({
      allowUserRegister: (state) => state.pubConfig.allowUserRegister,
      enableMobileRegister: (state) => state.pubConfig.enableMobileRegister,
      mobileAreaList: (state) => state.pubConfig.mobileAreaList,
      sm2PublicKey: (state) => state.pubConfig.sm2PublicKey,
    }),
    // Get current language
    currentLanguage() {
      return i18n.locale || "en";
    },
    // Get current language display text
    currentLanguageText() {
      return this.$t(getLanguageLabelKey(this.currentLanguage));
    },
    languageOptions() {
      return supportedLanguages;
    },
  },
  data() {
    return {
      activeName: "username",
      form: {
        username: "",
        password: "",
        captcha: "",
        captchaId: "",
        areaCode: "+1",
        mobile: "",
      },
      captchaUuid: "",
      captchaUrl: "",
      isMobileLogin: false,
      languageDropdownVisible: false,
    };
  },
  mounted() {
    this.fetchCaptcha();
    this.$store.dispatch("fetchPubConfig").then(() => {
      // Determine default login method based on configuration
      this.isMobileLogin = this.enableMobileRegister;
    });
  },
  methods: {
    fetchCaptcha() {
      if (this.$store.getters.getToken) {
        if (this.$route.path !== "/home") {
          this.$router.push("/home");
        }
      } else {
        this.captchaUuid = getUUID();

        Api.user.getCaptcha(this.captchaUuid, (res) => {
          if (res.status === 200) {
            const blob = new Blob([res.data], { type: 'image/gif' });
            this.captchaUrl = URL.createObjectURL(blob);
          } else {
            showDanger("Captcha loading failed, click to refresh");
          }
        });
      }
    },

    // Handle language dropdown menu visibility change
    handleLanguageDropdownVisibleChange(visible) {
      this.languageDropdownVisible = visible;
    },

    // Switch language
    changeLanguage(lang) {
      changeLanguage(lang);
      this.languageDropdownVisible = false;
      this.$message.success({
        message: this.$t("message.success"),
        showClose: true,
      });
    },

    // Switch login method
    switchLoginType(type) {
      this.isMobileLogin = type === "mobile";
      // Clear form
      this.form.username = "";
      this.form.mobile = "";
      this.form.password = "";
      this.form.captcha = "";
      this.fetchCaptcha();
    },

    // Encapsulate input validation logic
    validateInput(input, messageKey) {
      if (!input.trim()) {
        showDanger(this.$t(messageKey));
        return false;
      }
      return true;
    },

    async login() {
      if (this.isMobileLogin) {
        // Mobile number login validation
        if (!validateMobile(this.form.mobile, this.form.areaCode)) {
          showDanger(this.$t('login.requiredMobile'));
          return;
        }
        // Concatenate mobile number as username
        this.form.username = this.form.areaCode + this.form.mobile;
      } else {
        // Username login validation
        if (!this.validateInput(this.form.username, 'login.requiredUsername')) {
          return;
        }
      }

      // Validate password
      if (!this.validateInput(this.form.password, 'login.requiredPassword')) {
        return;
      }
      // Validate captcha
      if (!this.validateInput(this.form.captcha, 'login.requiredCaptcha')) {
        return;
      }

      if (!this.sm2PublicKey) {
        showDanger(this.$t('sm2.publicKeyNotConfigured'));
        return;
      }

      let encryptedPassword;
      try {
        const captchaAndPassword = this.form.captcha + this.form.password;
        encryptedPassword = sm2Encrypt(this.sm2PublicKey, captchaAndPassword);
      } catch (error) {
        console.error("Password encryption failed:", error);
        showDanger(this.$t('sm2.encryptionFailed'));
        return;
      }

      const plainUsername = this.form.username;
      this.form.captchaId = this.captchaUuid;
      const loginData = {
        username: plainUsername,
        password: encryptedPassword,
        captchaId: this.form.captchaId
      };

      Api.user.login(
        loginData,
        ({ data }) => {
          showSuccess(this.$t('login.loginSuccess'));
          this.$store.commit("setToken", JSON.stringify(data.data));
          goToPage("/home");
        },
        (err) => {
          // Use backend returned internationalization message directly
          let errorMessage = err.data.msg || "Login failed";
          
          showDanger(errorMessage);
          if (
            err.data != null &&
            err.data.msg != null &&
            err.data.msg.indexOf("Captcha") > -1
          ) {
            this.fetchCaptcha();
          }
        }
      );

      // Re-fetch captcha
      setTimeout(() => {
        this.fetchCaptcha();
      }, 1000);
    },

    goToRegister() {
      goToPage("/register");
    },
    goToForgetPassword() {
      goToPage("/retrieve-password");
    },
    openPage(url) {
      window.open(url, "_blank");
    },
  },
};
</script>
<style lang="scss" scoped>
@import "./auth.scss";

.login-type-container {
  margin: 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-language-dropdown {
  margin-left: auto;
}

.current-language-text {
  margin-left: 4px;
  margin-right: 4px;
  font-size: 12px;
  color: #3d4566;
}

.language-dropdown {
  margin-left: auto;
}

.rotate-down {
  transform: rotate(180deg);
  transition: transform 0.3s ease;
}

.el-icon-arrow-down {
  transition: transform 0.3s ease;
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
