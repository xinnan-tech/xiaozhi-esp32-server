<template>
  <CustomDialog
    :title="$t('manualAddDeviceDialog.title')"
    :visible="visible"
    width="600px"
    :destroy-on-close="false"
    @close="closeDialog"
    @confirm="submitForm"
  >
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
  </CustomDialog>
</template>

<script>
import Api from '@/apis/api';
import CustomDialog from './CustomDialog.vue';

export default {
  name: 'ManualAddDeviceDialog',
  components: { CustomDialog },
  props: {
    visible: { type: Boolean, required: true },
    agentId: { type: String, required: true }
  },
  data() {
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
    };
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
    }
  }
};
</script>
