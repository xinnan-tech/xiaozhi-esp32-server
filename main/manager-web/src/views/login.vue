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
        <div class="login-box">
          <div
            style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img src="@/assets/login/hi.png" alt="" style="width: 34px;height: 34px;" />
            <div class="login-text">登录</div>
            <div class="login-welcome">
              WELCOME TO LOG IN</div>
          </div>
          <el-tabs v-model="activeName" @tab-click="handleClick">
            <el-tab-pane label="用户名" name="username">
              <div style="padding: 0 30px;">
                <div class="input-box">
                  <img src="@/assets/login/username.png" alt="" class="input-icon" />
                  <el-input v-model="form.username" placeholder="请输入用户名" />
                </div>
                <div class="input-box">
                  <img src="@/assets/login/password.png" alt="" class="input-icon" />
                  <el-input v-model="form.password" placeholder="请输入密码" />
                </div>
                <div style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;display: flex;justify-content: space-between;margin-top: 20px;">
                  <div style="cursor: pointer;">新用户注册</div>
                  <div style="cursor: pointer;">忘记密码？</div>
                </div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="手机号" name="phone">
              <div style="padding: 0 30px;">
                <div class="input-box">
                  <img src="@/assets/login/phone.png" alt="" class="input-icon" />
                  <el-input v-model="form.phoneNumber" placeholder="请输入手机号" />
                  <div style="width: 120px;flex-shrink: 0;">
                    <el-dropdown>
                      <span class="el-dropdown-link">
                        +86 中国大陆<i class="el-icon-arrow-down el-icon--right"></i>
                      </span>
                      <el-dropdown-menu slot="dropdown">
                        <el-dropdown-item>黄金糕</el-dropdown-item>
                      </el-dropdown-menu>
                    </el-dropdown>
                  </div>
                </div>
                <div style="padding: 0 12px 0 30px;margin-top: 20px;" class="input-box">
                  <img src="@/assets/login/shield.png" alt="" class="input-icon" />
                  <el-input v-model="form.phoneCode" placeholder="请输入验证码" />
                  <div class="code-send">
                    发送
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
          <div class="login-btn">登陆</div>
          <div style="font-size: 14px;color: #979db1;">
            登录即同意<div style="display: inline-block;color: #5778FF;cursor: pointer;">《用户协议》</div>和
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《隐私政策》</div>
          </div>
        </div>
      </el-main>
      <el-footer>
        <div style="font-size: 12px;font-weight: 400;color: #979db1;">
          ©2024 小智Al控制面板2.0粤ICP备2022121736号-2</div>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
// @ is an alias to /src

export default {
  name: 'login',
  data() {
    return {
      activeName: "username",
      form:{
        phoneNumber:'',
        phoneCode:'',
        username:'',
        password:''
      }
    }
  },
  methods:{
    handleClick(){

    }
  }
}
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
