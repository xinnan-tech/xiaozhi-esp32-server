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
              <el-input v-model="form.password" placeholder="请输入密码"/>
            </div>
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
            <div
                style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;display: flex;justify-content: space-between;margin-top: 20px;">
              <div style="cursor: pointer;">新用户注册</div>
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
import axios from 'axios'
import { showDanger, showSuccess, goToPage } from '@/utils'
import api from '@/apis/request'  // 替换原来的Api导入

export default {
  name: 'login',
  data() {
    return {
      activeName: "username",
      form: {
        username: '',
        password: '',
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
    async fetchCaptcha() {
        try {
            this.captchaUuid = Date.now().toString()
            const response = await api.get(`/captcha?uuid=${this.captchaUuid}`, {
                responseType: 'blob',  // Keep this as first config option
                headers: {
                 'Accept': 'image/gif'  // Match with actual backend type
                }
            })

            // 释放之前创建的URL对象
            if (this.captchaUrl) {
                URL.revokeObjectURL(this.captchaUrl)
            }
            
            // 验证图片类型并创建新URL
            if (response.data.type === 'image/png') {
                // Directly use the received Blob
                this.captchaUrl = URL.createObjectURL(response.data)
                console.log('PNG验证码加载成功，UUID:', this.captchaUuid)
            } else {
                throw new Error(`无效的图片类型: ${response.data.type}`)
            }
        } catch (error) {
            // 清空验证码图片并显示错误
            this.captchaUrl = ''
            showDanger('验证码加载失败，请重试')
            console.error('验证码请求异常:', error)
            throw error
        }
    },
    
    async login() {
        if (isNull(this.form.username)) {
            showDanger('用户名不能为空')
            return
        }
        if (isNull(this.form.password)) {
            showDanger('密码不能为空')
            return
        }
        if (isNull(this.form.captcha)) {
            showDanger('验证码不能为空')
            return
        }
        
        try {
            const response = await api.post('/user/login', {
                username: this.form.username,
                password: this.form.password,
                captcha: this.form.captcha,
                uuid: this.captchaUuid
            })
            
            showSuccess('登录成功！')
            goToPage('/home')
        } catch (error) {
            const msg = error.response?.data?.msg || '登录失败'
            showDanger(msg)
            this.fetchCaptcha() // 自动刷新验证码
        }
    }
}      // ← 补全methods对象闭合括号
}      // ← 补全export default闭合括号
</script>
<style scoped lang="scss">
.welcome {
  min-width: 1200px;
  min-height: 675px;
  height: 100vh;
  background-image: url("@/assets/login/background.png");
  background-size: cover;
  /* 确保背景图像覆盖整个元素 */
  background-position: center;
  /* 从顶部中心对齐 */
  -webkit-background-size: cover;
  /* 兼容老版本WebKit浏览器 */
  -o-background-size: cover;
  /* 兼容老版本Opera浏览器 */
}

.login-text {
  font-weight: 700;
  font-size: 32px;
  text-align: left;
  color: #3d4566;
}

.login-welcome {
  font-weight: 400;
  font-size: 9px;
  text-align: left;
  color: #818cae;
  align-self: flex-end;
  margin-bottom: 7px;
}

.login-box {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  right: 18%;
  background-color: #fff;
  border-radius: 20px;
  padding: 35px 0;
  width: 450px;
  box-sizing: border-box;
}

.el-dropdown-link {
  font-weight: 400;
  font-size: 14px;
  text-align: left;
  color: #979db1;
}

.input-icon {
  width: 19px;
  height: 22px;
  flex-shrink: 0;
}

.login-btn {
  height: 35px;
  background: #5778ff;
  border-radius: 10px;
  font-weight: 400;
  font-size: 14px;
  cursor: pointer;
  color: #fff;
  line-height: 35px;
  margin: 35px 15px 15px;
}

.code-send {
  width: 70px;
  height: 32px;
  border-radius: 10px;
  background: #e6ebff;
  line-height: 32px;
  font-weight: 400;
  font-size: 14px;
  color: #5778ff;
  flex-shrink: 0;
  cursor: pointer;
}

.input-box {
  display: flex;
  margin-top: 20px;
  align-items: center;
  border-radius: 10px;
  background: #f6f8fb;
  border: 1px solid #e4e6ef;
  height: 40px;
  padding: 0 15px;
  gap: 20px;
}

::v-deep {
  .el-tabs__nav-wrap::after {
    height: 1px;
  }

  .el-tabs__nav-wrap::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 1px;
    background-color: #e4e7ed;
    z-index: 1;
  }

  .el-tabs__item {
    height: 65px;
    line-height: 65px;
    font-weight: 700;
    color: #3d4566;
  }

  .el-tabs__item.is-active {
    color: #5778ff;
  }

  .el-tabs__nav-scroll {
    padding: 0 30px;
  }

  .el-input__inner {
    border: none;
    background-color: transparent;
    height: 56px;
    padding: 0;
  }
}
</style>
