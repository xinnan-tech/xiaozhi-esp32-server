<template>
  <el-dialog :title="$t('manualAddDeviceDialog.title')" :visible="visible" @close="handleClose" width="30%" center>
    <div class="dialog-content">
      <el-form :model="deviceForm" :rules="rules" ref="deviceForm" label-width="auto">
        <el-form-item :label="$t('manualAddDeviceDialog.deviceType')" prop="board">
          <el-select v-model="deviceForm.board" :placeholder="$t('manualAddDeviceDialog.deviceTypePlaceholder')" style="width: 100%">
            <el-option
              v-for="item in firmwareTypes"
              :key="item.key"
              :label="item.name"
              :value="item.key">
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('manualAddDeviceDialog.firmwareVersion')" prop="appVersion">
          <el-input v-model="deviceForm.appVersion" :placeholder="$t('manualAddDeviceDialog.firmwareVersionPlaceholder')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('manualAddDeviceDialog.macAddress')" prop="macAddress">
          <el-input v-model="deviceForm.macAddress" :placeholder="$t('manualAddDeviceDialog.macAddressPlaceholder')"></el-input>
        </el-form-item>
      </el-form>
    </div>
    <div style="display: flex;margin: 15px 15px;gap: 7px;">
      <div class="dialog-btn" @click="submitForm">{{ $t('manualAddDeviceDialog.confirm') }}</div>
      <div class="dialog-btn cancel-btn" @click="cancel">{{ $t('manualAddDeviceDialog.cancel') }}</div>
    </div>
  </el-dialog>
</template>

<script>
import Api from '@/apis/api';

export default {
  name: 'ManualAddDeviceDialog',
  props: {
    visible: { type: Boolean, required: true },
    agentId: { type: String, required: true }
  },
  data() {
    // MAC地址验证规则
    const validateMac = (rule, value, callback) => {
      const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
      if (!value) {
        callback(new Error(this.$t('manualAddDeviceDialog.requiredMacAddress')));
      } else if (!macRegex.test(value)) {
        callback(new Error(this.$t('manualAddDeviceDialog.invalidMacAddress')));
      } else {
        callback();
      }
    };

    return {
      deviceForm: {
        board: '',
        appVersion: '',
        macAddress: ''
      },
      firmwareTypes: [],
      rules: {
        board: [
          { required: true, message: this.$t('manualAddDeviceDialog.requiredDeviceType'), trigger: 'change' }
        ],
        appVersion: [
          { required: true, message: this.$t('manualAddDeviceDialog.requiredFirmwareVersion'), trigger: 'blur' }
        ],
        macAddress: [
          { required: true, validator: validateMac, trigger: 'blur' }
        ]
      }
    }
  },
  created() {
    this.getFirmwareTypes();
  },
  methods: {
    async getFirmwareTypes() {
      try {
        const res = await Api.dict.getDictDataByType('FIRMWARE_TYPE');
        this.firmwareTypes = res.data;
      } catch (error) {
        console.error('获取固件类型失败:', error);
        this.$message.error(error.message || this.$t('manualAddDeviceDialog.getFirmwareTypeFailed'));
      }
    },
    submitForm() {
      this.$refs.deviceForm.validate((valid) => {
        if (valid) {
          this.addDevice();
        }
      });
    },
    addDevice() {
      const params = {
        agentId: this.agentId,
        ...this.deviceForm
      };
      
      Api.device.manualAddDevice(params, ({ data }) => {
        if (data.code === 0) {
          this.$message.success(this.$t('manualAddDeviceDialog.addSuccess'));
          this.$emit('refresh');
          this.closeDialog();
        } else {
          this.$message.error(data.msg || this.$t('manualAddDeviceDialog.addFailed'));
        }
      });
    },
    closeDialog() {
      this.$emit('update:visible', false);
      this.$refs.deviceForm.resetFields();
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
.dialog-content {
  padding: 0 20px;
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

.cancel-btn {
  background: #e6ebff;
  border: 1px solid #adbdff;
  color: #5778ff;
}

::v-deep .el-dialog {
  border-radius: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

::v-deep .el-dialog__body {
  padding: 20px 20px;
}

::v-deep .el-form-item {
  margin-bottom: 20px;
}
</style>