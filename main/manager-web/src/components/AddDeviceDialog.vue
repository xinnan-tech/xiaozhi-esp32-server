<template>
  <CustomDialog
    :title="$t('device.dialogTitle')"
    :visible.sync="visible"
    width="420px"
    :confirmLoading="loading"
    @confirm="confirm"
    @cancel="cancel"
    @close="handleClose"
    :confirmText="$t('device.confirmButton')"
    :cancelText="$t('device.cancelButton')"
  >
    <div class="add-device-body">
      <div class="add-device-label">
        <span class="required">*</span>
        {{ $t('device.verificationCode') }}
      </div>
      <el-input
        :placeholder="$t('device.verificationCodePlaceholder')"
        v-model="deviceCode"
        class="add-device-input"
        @keyup.enter.native="confirm"
      />
    </div>
  </CustomDialog>
</template>

<script>
import Api from '@/apis/api';
import CustomDialog from './CustomDialog.vue';

export default {
  name: 'AddDeviceDialog',
  components: { CustomDialog },
  props: {
    visible: { type: Boolean, required: true },
    agentId: { type: String, required: true }
  },
  data() {
    return {
      deviceCode: "",
      loading: false,
    }
  },
  methods: {
    confirm() {
      if (!/^\d{6}$/.test(this.deviceCode)) {
        this.$message.error(this.$t('device.input6DigitCode'));
        return;
      }
      this.loading = true;
      Api.device.bindDevice(
        this.agentId,
        this.deviceCode,
        ({ data }) => {
          this.loading = false;
          if (data.code === 0) {
            this.$emit('refresh');
            this.$message.success({
              message: this.$t('device.bindSuccess'),
              showClose: true
            });
            this.closeDialog();
          } else {
            this.$message.error({
              message: data.msg || this.$t('device.bindFailed'),
              showClose: true
            });
          }
        },
        (err) => {
          this.loading = false;
          const msg = err && err.data && err.data.msg;
          this.$message.error({
            message: msg || this.$t('device.bindFailed'),
            showClose: true
          });
        }
      );
    },
    closeDialog() {
      this.loading = false;
      this.deviceCode = '';
      this.$emit('update:visible', false);
    },
    cancel() {
      this.closeDialog();
    },
    handleClose() {
      this.closeDialog();
    }
  }
}
</script>

<style scoped>
.add-device-body {
  padding: 6px 4px 4px;
}

.add-device-label {
  font-size: 14px;
  color: #475569;
  text-align: left;
  margin-bottom: 12px;
}

.add-device-label .required {
  color: #f56c6c;
  margin-right: 2px;
}

.add-device-input ::v-deep(.el-input__inner) {
  height: 40px;
  border-radius: 8px;
  border-color: #e2e8f0;
  font-size: 14px;
}
</style>