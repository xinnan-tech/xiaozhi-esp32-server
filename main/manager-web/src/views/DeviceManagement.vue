<template>
  <div class="welcome">
        <HeaderBar />
    <el-main style="padding: 20px; display: flex; flex-direction: column;">
      <div class="table-container">
         <h3 class="device-list-title">设备列表</h3>
        <el-button type="primary" class="add-device-btn" @click="handleAddDevice">
          + 添加设备
        </el-button>
        <el-table :data="deviceList" style="width: 100%; margin-top: 20px" border stripe>
          <el-table-column label="设备型号" prop="model" flex></el-table-column>
          <el-table-column label="固件版本" prop="firmwareVersion" width="140"></el-table-column>
          <el-table-column label="Mac地址" prop="macAddress" width="220"></el-table-column>
          <el-table-column label="绑定时间" prop="bindTime" width="260"></el-table-column>
          <el-table-column label="最近对话" prop="lastConversation" width="100"></el-table-column>
          <el-table-column label="备注" width="220">
             <template slot-scope="scope">
              <el-input v-if="scope.row.isEdit" v-model="scope.row.remark" size="mini" @blur="stopEditRemark(scope.$index)"></el-input>
              <span v-else>
                <i v-if="!scope.row.remark" class="el-icon-edit" @click="startEditRemark(scope.$index, scope.row)"></i>
                <span v-else @click="startEditRemark(scope.$index, scope.row)">
                  {{ scope.row.remark }}
                </span>
              </span>
            </template>
          </el-table-column>
          <el-table-column label="OTA升级" width="120">
            <template slot-scope="scope">
              <el-switch v-model="scope.row.otaSwitch" size="mini" active-color="#13ce66" inactive-color="#ff4949"></el-switch>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template slot-scope="scope">
              <el-button size="mini" type="text" @click="handleUnbind(scope.row)" style="color: #ff4949">
                解绑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div style="font-size: 12px; font-weight: 400; margin-top: auto; padding-top: 30px; color: #979db1;">
        ©2025 xiaozhi-esp32-server
      </div>
      <AddDeviceDialog :visible.sync="addDeviceDialogVisible" @added="handleDeviceAdded" />
    </el-main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import AddDeviceDialog from "@/components/AddDeviceDialog.vue";

export default {
  components: {HeaderBar, AddDeviceDialog },
  data() {
    return {
      addDeviceDialogVisible: false,
      deviceList: [
        {
          model: 'xingzhi-cube-0.96oled-wifi',
          firmwareVersion: '1.4.6',
          macAddress: 'fc:01:2c:c5:d5:7c',
          bindTime: '2025-03-10 18:16:21',
          lastConversation: '6 天前',
          remark: '',
          isEdit: false,
          otaSwitch: false
        },
        {
          model: 'xingzhi-board-1.3tft-ble',
          firmwareVersion: '2.1.0',
          macAddress: 'ac:12:3d:e7:f8:9a',
          bindTime: '2025-03-12 09:30:15',
          lastConversation: '4 天前',
          remark: '测试设备',
          isEdit: false,
          otaSwitch: true
      },
      {
        model: 'xingzhi-kit-0.91oled-4g',
        firmwareVersion: '1.8.3',
        macAddress: 'bc:45:6f:1e:2d:3c',
        bindTime: '2025-03-15 14:22:08',
        lastConversation: '2 天前',
        remark: '生产环境设备',
        isEdit: false,
        otaSwitch: false
      }
      ]
    };
  },
  methods: {
    handleAddDevice() {
      // 添加设备逻辑
      this.addDeviceDialogVisible = true;
    },
    startEditRemark(index, row) {
      this.deviceList[index].isEdit = true;
    },
    stopEditRemark(index) {
      this.deviceList[index].isEdit = false;
    },
    handleUnbind(device) {
      // 解绑逻辑
      console.log('解绑设备', device);
    },
    handleDeviceAdded(deviceCode) {
      console.log('添加的智慧体名称：', deviceCode);
    },
  }
};
</script>

<style scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-image: url("@/assets/home/background.png");
  background-size: cover;
  background-position: center;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.table-container {
  background: #f9fafc;
  padding: 20px;
  border-radius: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-top: 15px;
}

.add-device-btn {
  float: right;
  background: #409eff;
  border: none;
  border-radius: 10px;
  width: 105px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  gap: 8px;
  margin-bottom: 15px;
  &:hover {
    background: #3a8ee6;
  }
}

.device-list-title {
  float: left;
  font-size: 18px;
  font-weight: 700;
  margin: 5px;
  color: #2c3e50;
}

.el-icon-edit {
  color: #409eff;
  cursor: pointer;
  font-size: 14px;
  vertical-align: middle;
}

</style>