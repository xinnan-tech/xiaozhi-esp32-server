<template>
  <form>
    <el-dialog :visible.sync="value" width="400px" center>
      <div
        style="margin: 0 10px 10px;display: flex;align-items: center;gap: 10px;font-weight: 700;font-size: 20px;text-align: left;color: #3d4566;">
        <div
          style="width: 40px;height: 40px;border-radius: 50%;background: #5778ff;display: flex;align-items: center;justify-content: center;">
          <img loading="lazy" src="@/assets/login/shield.png" alt=""
            style="width: 19px;height: 23px; filter: brightness(0) invert(1);" />
        </div>
        修改密码
      </div>
      <div style="height: 1px;background: #e8f0ff;" />
      <div style="margin: 22px 15px;">
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;">
          <div style="color: red;display: inline-block;">*</div>
          旧密码：
        </div>
        <div class="input-46" style="margin-top: 12px;">
          <el-input placeholder="请输入旧密码" v-model="oldPassword" type="password" show-password />
        </div>
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;margin-top: 12px;">
          <div style="color: red;display: inline-block;">*</div>
          新密码：
        </div>
        <div class="input-46" style="margin-top: 12px;">
          <el-input placeholder="请输入新密码" v-model="newPassword" type="password" show-password />
        </div>
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;margin-top: 12px;">
          <div style="color: red;display: inline-block;">*</div>
          确认新密码：
        </div>
        <div class="input-46" style="margin-top: 12px;">
          <el-input placeholder="请再次输入新密码" v-model="confirmNewPassword" type="password" show-password />
        </div>
      </div>
      <div style="display: flex;margin: 15px 15px;gap: 7px;">
        <div class="dialog-btn" @click="confirm">
          确定
        </div>
        <div class="dialog-btn" style="background: #e6ebff;border: 1px solid #adbdff;color: #5778ff;" @click="cancel">
          取消
        </div>
      </div>
    </el-dialog>
  </form>
</template>

<script>
import userApi from '@/apis/module/user';
import { mapActions } from 'vuex';

export default {
  name: 'ChangePasswordDialog',
  props: {
    value: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      oldPassword: "",
      newPassword: "",
      confirmNewPassword: ""
    }
  },
  methods: {
    ...mapActions(['logout']), // 引入Vuex的logout action
    confirm() {
      if (!this.oldPassword.trim() || !this.newPassword.trim() || !this.confirmNewPassword.trim()) {
        this.$message.error('请填写所有字段');
        return;
      }
      if (this.newPassword !== this.confirmNewPassword) {
        this.$message.error('两次输入的新密码不一致');
        return;
      }
      if (this.newPassword === this.oldPassword) {
        this.$message.error('新密码不能与旧密码相同');
        return;
      }

      // 修改后的接口调用
      userApi.changePassword(this.oldPassword, this.newPassword, (res) => {
        if (res.data.code === 0) {
          this.$message.success({
            message: '密码修改成功，请重新登录',
            showClose: true
          });
          this.logout().then(() => {
            this.$router.push('/login');
            this.$emit('update:visible', false);
          });
        } else {
          this.$message.error(res.data.msg || '密码修改失败');
        }
      }, (err) => {
        this.$message.error(err.msg || '密码修改失败');
      });
      this.$emit('input', false);
    },
    cancel() {
      this.$emit('input', false);
      this.resetForm();
    },
    resetForm() {
      this.oldPassword = "";
      this.newPassword = "";
      this.confirmNewPassword = "";
    }
  }
}
</script>

<style scoped>
.input-46 {
  background: #f6f8fb;
  border-radius: 15px;
}

.dialog-btn {
  cursor: pointer;
  flex: 1;
  border-radius: 23px;
  background: #5778ff;
  height: 40px;
  font-weight: 500;
  font-size: 12px;
  color: #fff;
  line-height: 40px;
  text-align: center;
}

::v-deep .el-dialog {
  border-radius: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

::v-deep .el-dialog__headerbtn {
  display: none;
}

::v-deep .el-dialog__body {
  padding: 4px 6px;
}

::v-deep .el-dialog__header {
  padding: 10px;
}
</style>