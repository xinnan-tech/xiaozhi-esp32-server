<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "Forgot Password"
  }
}
</route>

<script lang="ts" setup>
import { computed, onMounted, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { useConfigStore } from "@/store";
import { getEnvBaseUrl, sm2Encrypt } from "@/utils";
import { toast } from "@/utils/toast";
// Import i18n helpers.
import { t, initI18n } from "@/i18n";
// Import API methods.
import { retrievePassword, sendSmsCode } from "@/api/auth";

// Get the safe-area inset from the screen bounds.
let safeAreaInsets;
let systemInfo;

// #ifdef MP-WEIXIN
// WeChat Mini Program uses the newer window API.
systemInfo = uni.getWindowInfo();
safeAreaInsets = systemInfo.safeArea
  ? {
      top: systemInfo.safeArea.top,
      right: systemInfo.windowWidth - systemInfo.safeArea.right,
      bottom: systemInfo.windowHeight - systemInfo.safeArea.bottom,
      left: systemInfo.safeArea.left,
    }
  : null
// #endif

// #ifndef MP-WEIXIN
// Other platforms continue to use the classic uni API.
systemInfo = uni.getSystemInfoSync();
safeAreaInsets = systemInfo.safeAreaInsets;
// #endif

// Form data model.
interface ForgotPasswordData {
  mobile: string
  captcha: string
  captchaId: string
  mobileCaptcha: string
  newPassword: string
  confirmPassword: string
  areaCode: string
}

const formData = ref<ForgotPasswordData>({
  mobile: "",
  captcha: "",
  captchaId: "",
  mobileCaptcha: "",
  newPassword: "",
  confirmPassword: "",
  areaCode: "+1",
});

// Captcha image.
const captchaImage = ref("");
const loading = ref(false);

// Load public configuration from the store.
const configStore = useConfigStore();

// State for area code action sheet
const showAreaCodeSheet = ref(false);
const selectedAreaCode = ref("+1");
const areaCodeList = computed(() =>
  (configStore.config.mobileAreaList || [{ name: "United States", key: "+1" }]).map((item) => {
    return {
      value: item.key,
      label: `${item.name} (${item.key})`,
    }
  }),
)

function isValidMobileNumber(value: string) {
  const normalized = value.replace(/\D/g, "");
  return normalized.length >= 4 && normalized.length <= 15;
}

const canSendMobileCaptcha = computed(() => {
  const mobile = formData.value.mobile;
  return isValidMobileNumber(mobile) && smsCountdown.value === 0;
});

// SM2 public key.
const sm2PublicKey = computed(() => {
  return configStore.config.sm2PublicKey;
});

// SMS verification countdown.
const smsCountdown = ref(0);
const smsLoading = ref(false);

// Open the area-code picker.
function openAreaCodeSheet() {
  showAreaCodeSheet.value = true
}

// Select an area code.
function selectAreaCode(item: { value: string; label: string }) {
  selectedAreaCode.value = item.value;
  formData.value.areaCode = item.value;
  showAreaCodeSheet.value = false;
}

// Close the area-code picker.
function closeAreaCodeSheet() {
  showAreaCodeSheet.value = false
}

// Generate a UUID for the captcha request.
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// Refresh the image captcha.
async function refreshCaptcha() {
  const uuid = generateUUID()
  formData.value.captchaId = uuid
  captchaImage.value = `${getEnvBaseUrl()}/user/captcha?uuid=${uuid}&t=${Date.now()}`
}

// Send the SMS verification code.
async function handleSendSmsCode() {
  // Validate the phone number format.
  if (!isValidMobileNumber(formData.value.mobile)) {
    toast.warning(t("retrievePassword.inputCorrectMobile"));
    return;
  }

  if (!formData.value.captcha) {
    toast.warning(t('retrievePassword.captchaRequired'))
    return
  }

  try {
    smsLoading.value = true;
    // Convert the phone number into international format.
    const internationalPhone = formData.value.areaCode + formData.value.mobile;
    // Call the SMS code endpoint.
    await sendSmsCode({
      phone: internationalPhone,
      captcha: formData.value.captcha,
      captchaId: formData.value.captchaId,
    })

    toast.success(t('retrievePassword.captchaSendSuccess'))

    // Start the countdown timer.
    smsCountdown.value = 60;
    const timer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000);
  } catch (error: any) {
    // Handle captcha validation errors.
    if (error.message.includes("10067")) {
      toast.warning(t("login.captchaError"));
    }
    // Refresh the image captcha after a failed send.
    refreshCaptcha();
  } finally {
    smsLoading.value = false;
  }
}

// Submit the password reset request.
async function handleResetPassword() {
  // Validate the form.
  if (!formData.value.mobile) {
    toast.warning(t('retrievePassword.mobileRequired'))
    return
  }

  // Validate the phone number format.
  if (!isValidMobileNumber(formData.value.mobile)) {
    toast.warning(t("retrievePassword.inputCorrectMobile"));
    return;
  }

  // Convert the phone number into international format.
  const internationalPhone = formData.value.areaCode + formData.value.mobile;

  if (!formData.value.captcha) {
    toast.warning(t('retrievePassword.captchaRequired'))
    return
  }

  if (!formData.value.mobileCaptcha) {
    toast.warning(t('retrievePassword.mobileCaptchaRequired'))
    return
  }

  if (!formData.value.newPassword) {
    toast.warning(t('retrievePassword.newPasswordRequired'))
    return
  }

  if (!formData.value.confirmPassword) {
    toast.warning(t('retrievePassword.confirmNewPasswordRequired'))
    return
  }

  if (formData.value.newPassword !== formData.value.confirmPassword) {
    toast.warning(t('retrievePassword.passwordsNotMatch'))
    return
  }

  try {
    loading.value = true

    // Ensure the SM2 public key is configured.
    if (!sm2PublicKey.value) {
      toast.warning(t('sm2.publicKeyNotConfigured'))
      return
    }

    // Encrypt the password before sending it.
    let encryptedPassword;
    try {
      // Concatenate captcha and new password before encryption.
      const captchaAndPassword = formData.value.captcha + formData.value.newPassword;
      encryptedPassword = sm2Encrypt(sm2PublicKey.value, captchaAndPassword);
    } catch (error) {
      console.error("Password encryption failed:", error);
      toast.warning(t("sm2.encryptionFailed"));
      return;
    }

    // Call the password reset API.
    await retrievePassword({
      phone: internationalPhone,
      code: formData.value.mobileCaptcha,
      password: encryptedPassword,
      captchaId: formData.value.captchaId,
    })

    toast.success(t('retrievePassword.passwordUpdateSuccess'))

    // Redirect back to the login page.
    setTimeout(() => {
      uni.redirectTo({
        url: "/pages/login/index",
      });
    }, 1000);
  } catch (error: any) {
    // Handle captcha validation errors.
    if (error.message.includes("10067")) {
      toast.warning(t("login.captchaError"));
    }
    // Refresh the captcha after a failed reset.
    refreshCaptcha();
  } finally {
    loading.value = false;
  }
}

// Return to the login page.
function goBack() {
  uni.redirectTo({
    url: '/pages/login/index',
  })
}

// Fetch the captcha when the page loads.
onLoad(() => {
  refreshCaptcha()
})

// Ensure configuration and i18n are loaded on mount.
onMounted(async () => {
  if (!configStore.config.name) {
    try {
      await configStore.fetchPublicConfig();
    } catch (error) {
      console.error("Failed to fetch configuration:", error);
    }
  }
  // Initialize i18n for the current locale.
  initI18n();
});
</script>

<template>
  <view
    class="app-container box-border h-screen w-full"
    :style="{ paddingTop: `${safeAreaInsets?.top}px` }"
  >
    <view class="header">
      <view class="back-button" @click="goBack">
        <wd-icon name="arrow-left" custom-class="back-icon" />
      </view>
      <view class="logo-section">
        <wd-img :width="80" :height="80" round src="/static/logo.png" class="logo" />
        <text class="welcome-text">
          {{ t("retrievePassword.title") }}
        </text>
        <text class="subtitle">
          {{ t("retrievePassword.subtitle") }}
        </text>
      </view>
    </view>

    <view class="form-container">
      <view class="form">
        <!-- Phone number input -->
        <view class="input-group">
          <view class="input-wrapper mobile-wrapper">
            <view class="area-code-selector" @click="openAreaCodeSheet">
              <text class="area-code-text">
                {{ selectedAreaCode }}
              </text>
              <wd-icon name="arrow-down" custom-class="area-code-arrow" />
            </view>
            <view class="mobile-input-wrapper">
              <wd-input
                v-model="formData.mobile"
                custom-class="styled-input"
                no-border
                :placeholder="t('retrievePassword.mobilePlaceholder')"
                type="number"
                :maxlength="11"
              />
            </view>
          </view>
        </view>

        <!-- Image captcha -->
        <view class="input-group">
          <view class="input-wrapper captcha-wrapper">
            <wd-input
              v-model="formData.captcha"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.captchaPlaceholder')"
              :maxlength="6"
            />
            <view class="captcha-image" @click="refreshCaptcha">
              <image :src="captchaImage" class="captcha-img" />
            </view>
          </view>
        </view>

        <!-- SMS verification code -->
        <view class="input-group">
          <view class="input-wrapper sms-wrapper">
            <wd-input
              v-model="formData.mobileCaptcha"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.mobileCaptchaPlaceholder')"
              :maxlength="6"
            />
            <view class="sms-button" @click="handleSendSmsCode">
              <text class="sms-text">
                {{
                  smsCountdown > 0
                    ? `${smsCountdown}s`
                    : t("retrievePassword.getMobileCaptcha")
                }}
              </text>
            </view>
          </view>
        </view>

        <!-- New password -->
        <view class="input-group">
          <view class="input-wrapper">
            <wd-input
              v-model="formData.newPassword"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.newPasswordPlaceholder')"
              show-password
              :maxlength="20"
            />
          </view>
        </view>

        <!-- Confirm new password -->
        <view class="input-group">
          <view class="input-wrapper">
            <wd-input
              v-model="formData.confirmPassword"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.confirmNewPasswordPlaceholder')"
              show-password
              :maxlength="20"
            />
          </view>
        </view>

        <!-- Reset password button -->
        <view class="reset-btn" @click="handleResetPassword">
          {{ loading ? t("common.loading") : t("retrievePassword.resetButton") }}
        </view>

        <!-- Return-to-login link -->
        <view class="back-login-hint" @click="goBack">
          <text class="hint-text">
            {{ t("retrievePassword.goToLogin") }}
          </text>
        </view>
      </view>
    </view>

    <!-- Area code selection sheet -->
    <wd-action-sheet
      v-model="showAreaCodeSheet"
      :title="t('login.selectCountry')"
      :close-on-click-modal="true"
      @close="closeAreaCodeSheet"
    >
      <view class="area-code-sheet">
        <scroll-view scroll-y class="area-code-list">
          <view
            v-for="item in areaCodeList"
            :key="item.value"
            class="area-code-item"
            :class="{ selected: selectedAreaCode === item.value }"
            @click="selectAreaCode(item)"
          >
            <view class="area-info">
              <text class="area-name">
                {{ item.label }}
              </text>
            </view>
            <wd-icon
              v-if="selectedAreaCode === item.value"
              name="check"
              custom-class="check-icon"
            />
          </view>
        </scroll-view>
        <view class="sheet-footer">
          <wd-button
            type="primary"
            custom-class="confirm-btn"
            @click="closeAreaCodeSheet"
          >
            {{ t("login.confirm") }}
          </wd-button>
        </view>
      </view>
    </wd-action-sheet>
  </view>
</template>

<style lang="scss" scoped>
.app-container {
  background: linear-gradient(145deg, #f5f8fd, #6baaff, #9ebbfc, #f5f8fd);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  min-height: 100vh;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
    animation: float 6s ease-in-out infinite;
  }
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

.header {
  flex: 0 0 auto;
  min-height: 280rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15% 0 40rpx 0;
  position: relative;

  .back-button {
    position: absolute;
    left: 30rpx;
    top: 50rpx;
    width: 60rpx;
    height: 60rpx;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    backdrop-filter: blur(10rpx);
    border: 1rpx solid rgba(255, 255, 255, 0.3);

    .back-icon {
      font-size: 32rpx;
      color: #ffffff;
    }
  }

  .logo-section {
    text-align: center;

    .logo {
      margin-bottom: 20rpx;
      box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.1);
    }

    .welcome-text {
      display: block;
      color: #ffffff;
      font-size: 40rpx;
      font-weight: 600;
      margin-bottom: 12rpx;
      text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.1);
    }

    .subtitle {
      display: block;
      color: rgba(255, 255, 255, 0.8);
      font-size: 26rpx;
      font-weight: 400;
    }
  }
}

.form-container {
  padding: 0 40rpx 40rpx 40rpx;
  flex: 1;
  display: flex;
  align-items: flex-start;

  .form {
    width: 100%;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 24rpx;
    padding: 40rpx 30rpx 30rpx 30rpx;
    backdrop-filter: blur(10rpx);
    box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.1);
    border: 1rpx solid rgba(255, 255, 255, 0.2);
    max-height: calc(100vh - 350rpx);
    overflow-y: auto;

    .input-group {
      margin-bottom: 24rpx;

      .input-wrapper {
        position: relative;
        background: #f8f9fa;
        border-radius: 16rpx;
        padding: 20rpx 16rpx;
        border: 2rpx solid #e9ecef;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;

        &:focus-within {
          border-color: #667eea;
          background: #ffffff;
          box-shadow: 0 0 0 6rpx rgba(102, 126, 234, 0.1);
        }

        &.mobile-wrapper {
          padding: 0;
          background: transparent;
          border: none;
          display: flex;
          gap: 20rpx;

          .area-code-selector {
            flex: 0 0 160rpx;
            background: #f8f9fa;
            border-radius: 16rpx;
            padding: 20rpx 16rpx;
            border: 2rpx solid #e9ecef;
            height: 45rpx;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: all 0.3s ease;

            &:hover {
              border-color: #667eea;
              background: #ffffff;
              box-shadow: 0 0 0 6rpx rgba(102, 126, 234, 0.1);
            }

            .area-code-text {
              font-size: 28rpx;
              color: #333333;
              font-weight: 500;
            }

            :deep(.area-code-arrow) {
              font-size: 24rpx;
              color: #999999;
              transition: transform 0.3s ease;
            }
          }

          .mobile-input-wrapper {
            flex: 1;
            background: #f8f9fa;
            border-radius: 16rpx;
            padding: 20rpx 16rpx;
            border: 2rpx solid #e9ecef;
            transition: all 0.3s ease;

            &:focus-within {
              border-color: #667eea;
              background: #ffffff;
              box-shadow: 0 0 0 6rpx rgba(102, 126, 234, 0.1);
            }
          }
        }

        &.captcha-wrapper {
          .captcha-image {
            margin-left: 20rpx;
            width: 150rpx;
            height: 60rpx;
            border-radius: 8rpx;
            overflow: hidden;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #e9ecef;
            border: 1rpx solid #ddd;

            .captcha-img {
              width: 100%;
              height: 100%;
            }
          }
        }

        &.sms-wrapper {
          .sms-button {
            margin-left: 20rpx;
            width: 180rpx;
            height: 60rpx;
            border-radius: 12rpx;
            background: #667eea;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;

            &:active {
              background: #5a6fd8;
              transform: scale(0.98);
            }

            .sms-text {
              font-size: 24rpx;
              color: #ffffff;
              font-weight: 500;
            }
          }
        }

        :deep(.styled-input) {
          background: transparent !important;
          border: none !important;
          outline: none !important;
          font-size: 32rpx;
          color: #333333;
          flex: 1;

          &::placeholder {
            color: #999999;
            font-size: 28rpx;
          }
        }
      }
    }

    .reset-btn {
      width: 100%;
      height: 80rpx;
      border: none;
      border-radius: 16rpx;
      font-size: 30rpx;
      font-weight: 600;
      color: #ffffff;
      margin-bottom: 30rpx;
      box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.3);
      transition: all 0.3s ease;
      background-color: var(--wot-button-primary-bg-color, var(--wot-color-theme, #4d80f0));
      text-align: center;
      line-height: 80rpx;

      &:active {
        transform: translateY(2rpx);
        box-shadow: 0 4rpx 12rpx rgba(102, 126, 234, 0.3);
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }

    .back-login-hint {
      text-align: center;

      .hint-text {
        color: #667eea;
        font-size: 26rpx;
        font-weight: 500;
        cursor: pointer;

        &:hover {
          text-decoration: underline;
        }
      }
    }
  }
}

// Area code selection sheet styles.
.area-code-sheet {
  background: #ffffff;
  border-radius: 24rpx 24rpx 0 0;
  overflow: hidden;

  .sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 40rpx 40rpx 20rpx 40rpx;
    border-bottom: 1rpx solid #f0f0f0;

    .sheet-title {
      font-size: 36rpx;
      font-weight: 600;
      color: #333333;
    }

    :deep(.close-icon) {
      font-size: 32rpx;
      color: #999999;
      cursor: pointer;
      padding: 10rpx;

      &:hover {
        color: #333333;
      }
    }
  }

  .area-code-list {
    max-height: 60vh;
    padding: 0 40rpx;

    .area-code-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 32rpx 0;
      border-bottom: 1rpx solid #f8f9fa;
      cursor: pointer;
      transition: background-color 0.3s ease;

      &:hover {
        background-color: #f8f9fa;
      }

      &.selected {
        background-color: rgba(102, 126, 234, 0.05);

        .area-name {
          color: #667eea;
          font-weight: 500;
        }

        .area-code {
          color: #667eea;
        }
      }

      .area-info {
        display: flex;
        flex-direction: column;
        gap: 8rpx;

        .area-name {
          font-size: 32rpx;
          color: #333333;
        }

        .area-code {
          font-size: 28rpx;
          color: #666666;
        }
      }

      :deep(.check-icon) {
        font-size: 32rpx;
        color: #667eea;
      }
    }
  }

  .sheet-footer {
    padding: 30rpx 40rpx 40rpx 40rpx;
    border-top: 1rpx solid #f0f0f0;

    :deep(.confirm-btn) {
      width: 100%;
      height: 88rpx;
      border-radius: 16rpx;
      font-size: 32rpx;
      font-weight: 600;
    }
  }
}
</style>
