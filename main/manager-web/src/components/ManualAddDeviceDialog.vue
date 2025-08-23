<template>
  <el-dialog title="Manual Add Device" :visible="visible" @close="handleClose" width="30%" center>
    <div class="dialog-content">
      <el-form :model="deviceForm" :rules="rules" ref="deviceForm" label-width="100px">
        <el-form-item label="Device Model" prop="board">
          <el-select v-model="deviceForm.board" placeholder="Please select device model" style="width: 100%">
            <el-option
              v-for="item in firmwareTypes"
              :key="item.key"
              :label="item.name"
              :value="item.key">
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="Firmware Ver." prop="appVersion">
          <el-input v-model="deviceForm.appVersion" placeholder="Please enter firmware version"></el-input>
        </el-form-item>
        <el-form-item label="MAC Address" prop="macAddress">
          <el-input v-model="deviceForm.macAddress" placeholder="Please enter MAC address"></el-input>
        </el-form-item>
      </el-form>
    </div>
    <div style="display: flex;margin: 15px 15px;gap: 7px;">
      <div class="dialog-btn" @click="submitForm">Confirm</div>
      <div class="dialog-btn cancel-btn" @click="cancel">Cancel</div>
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
        callback(new Error('Please enter MAC address'));
      } else if (!macRegex.test(value)) {
        callback(new Error('Please enter correct MAC address format, e.g.: 00:1A:2B:3C:4D:5E'));
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
          { required: true, message: 'Please select device model', trigger: 'change' }
        ],
        appVersion: [
          { required: true, message: 'Please enter firmware version', trigger: 'blur' }
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
        console.error('Failed to get firmware types:', error);
        this.$message.error(error.message || 'Failed to get firmware types');
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
          this.$message.success('Device added successfully');
          this.$emit('refresh');
          this.closeDialog();
        } else {
          this.$message.error(data.msg || 'Failed to add device');
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
  padding: 20px 6px;
}

::v-deep .el-form-item {
  margin-bottom: 20px;
}
</style> 