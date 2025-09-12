<template>
  <form>
    <el-dialog :visible.sync="dialogVisible"  width="24%" center>
      <div
        style="margin: 0 10px 10px;display: flex;align-items: center;gap: 10px;font-weight: 700;font-size: 20px;text-align: left;color: #3d4566;">
        <div
          style="width: 40px;height: 40px;border-radius: 50%;background: #5778ff;display: flex;align-items: center;justify-content: center;">
          <img loading="lazy" src="@/assets/login/shield.png" alt=""
            style="width: 19px;height: 23px; filter: brightness(0) invert(1);" />
        </div>
        {{ $t('changePassword.title') }}
      </div>
      <div style="height: 1px;background: #e8f0ff;" />
      <div style="margin: 22px 15px;">
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;">
          <div style="color: red;display: inline-block;">*</div>
          {{ $t('changePassword.oldPasswordLabel') }}
        </div>
        <div class="input-46" style="margin-top: 12px;">
          <el-input :placeholder="$t('changePassword.oldPasswordPlaceholder')" v-model="oldPassword" type="password" show-password />
        </div>
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;margin-top: 12px;">
          <div style="color: red;display: inline-block;">*</div>
          {{ $t('changePassword.newPasswordLabel') }}
        </div>
        <div class="input-46" style="margin-top: 12px;">
          <el-input :placeholder="$t('changePassword.newPasswordPlaceholder')" v-model="newPassword" type="password" show-password />
        </div>
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;margin-top: 12px;">
          <div style="color: red;display: inline-block;">*</div>
          {{ $t('changePassword.confirmPasswordLabel') }}
        </div>
        <div class="input-46" style="margin-top: 12px;">
          <el-input :placeholder="$t('changePassword.confirmPasswordPlaceholder')" v-model="confirmNewPassword" type="password" show-password />
        </div>
      </div>
      <div style="display: flex;margin: 15px 15px;gap: 7px;">
        <div class="dialog-btn" @click="confirm">
          {{ $t('changePassword.confirmButton') }}
        </div>
        <div class="dialog-btn" style="background: #e6ebff;border: 1px solid #adbdff;color: #5778ff;" @click="cancel">
          {{ $t('changePassword.cancelButton') }}
        </div>
      </div>
    </el-dialog>
  </form>
</template>

<script>
import userApi from '@/apis/module/user';
import { mapActions } from 'vuex';
import { changeLanguage } from '@/i18n';

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
      dialogVisible: this.value,
      oldPassword: "",
      newPassword: "",
      confirmNewPassword: ""
    }
  },
  watch: {
    value(val) {
      this.dialogVisible = val;
    },
    dialogVisible(val) {
      this.$emit('input', val);
    }
  },
  methods: {
    ...mapActions(['logout']), // 引入Vuex的logout action
    confirm() {
      if (!this.oldPassword.trim() || !this.newPassword.trim() || !this.confirmNewPassword.trim()) {
        this.$message.error(this.$t('changePassword.allFieldsRequired'));
        return;
      }
      if (this.newPassword !== this.confirmNewPassword) {
        this.$message.error(this.$t('changePassword.passwordsNotMatch'));
        return;
      }
      if (this.newPassword === this.oldPassword) {
        this.$message.error(this.$t('changePassword.newPasswordSameAsOld'));
        return;
      }

      // 修改后的接口调用
      userApi.changePassword(this.oldPassword, this.newPassword, (res) => {
        if (res.data.code === 0) {
          this.$message.success({
            message: this.$t('changePassword.passwordChangedSuccessfully'),
            showClose: true
          });
          this.logout().then(() => {
            this.$router.push('/login');
            this.$emit('update:visible', false);
          });
        } else {
          this.$message.error(res.data.msg || this.$t('changePassword.changeFailed'));
        }
      }, (err) => {
        this.$message.error(err.msg || this.$t('changePassword.changeFailed'));
      });
      this.$emit('input', false);
    },
    cancel() {
      this.dialogVisible = false;
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