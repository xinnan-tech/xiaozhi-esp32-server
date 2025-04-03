<template>
  <div class="welcome">
    <HeaderBar />
    <el-main style="padding: 20px; display: flex; flex-direction: column;">
      <div class="table-container">
        <h3 class="device-list-title">设备列表</h3>
        <el-button type="primary" class="add-device-btn" @click="handleAddDevice">
          + 添加设备
        </el-button>
        <el-table :data="paginatedDeviceList" style="width: 100%; margin-top: 20px" border stripe>
          <el-table-column label="设备型号" prop="model" flex></el-table-column>
          <el-table-column label="固件版本" prop="firmwareVersion" width="120"></el-table-column>
          <el-table-column label="Mac地址" prop="macAddress"></el-table-column>
          <el-table-column label="绑定时间" prop="bindTime" width="200"></el-table-column>
          <el-table-column label="最近对话" prop="lastConversation" width="140"></el-table-column>
          <el-table-column label="备注" width="180">
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
              <el-button size="mini" type="text" @click="handleUnbind(scope.row.device_id)" style="color: #ff4949">
                解绑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          class="pagination"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          :current-page="currentPage"
          :page-sizes="[5, 10, 20, 50]"
          :page-size="pageSize"
          layout="total, sizes, prev, pager, next, jumper"
          :total="deviceList.length"
        ></el-pagination>
      </div>
      <div class="copyright">
        ©2025 xiaozhi-esp32-server
      </div>
      <AddDeviceDialog :visible.sync="addDeviceDialogVisible" :agent-id="currentAgentId" @refresh="fetchBindDevices(currentAgentId)"  />
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
      currentAgentId: this.$route.query.agentId || '',
      currentPage: 1,
      pageSize: 5,
      deviceList: [],
      loading: false,
      userApi: null,
    };
  },
  computed: {
    paginatedDeviceList() {
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      return this.deviceList.slice(start, end);
    }
  },
  mounted() {
    const agentId = this.$route.query.agentId;
    import('@/apis/module/device').then(({ default: deviceApi }) => {
      this.deviceApi = deviceApi;
      if (agentId) {
        this.fetchBindDevices(agentId);
      }
    });
  },
  methods: {
    handleAddDevice() {
      this.addDeviceDialogVisible = true;
    },
    startEditRemark(index, row) {
      this.deviceList[index].isEdit = true;
    },
    stopEditRemark(index) {
      this.deviceList[index].isEdit = false;
    },
    handleUnbind(device_id) {
      if (!this.deviceApi) {
        this.$message.error('功能模块加载失败');
        return;
      }
      this.$confirm('确认要解绑该设备吗？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.deviceApi.unbindDevice(device_id, ({ data }) => {
          if (data.code === 0) {
            this.$message.success({
                message: '设备解绑成功',
                showClose: true
            });
            this.fetchBindDevices(this.$route.query.agentId);
          } else {
            this.$message.error({
            message: data.msg || '设备解绑失败',
            showClose: true
            });
          }
        });
      });
    },
    handleSizeChange(val) {
      this.pageSize = val;
    },
    handleCurrentChange(val) {
      this.currentPage = val;
    },
    fetchBindDevices(agentId) {
      this.loading = true;
      import('@/apis/module/device').then(({ default: deviceApi }) => {
        deviceApi.getAgentBindDevices(agentId, ({ data }) => {
          this.loading = false;
          if (data.code === 0) {
            // 格式化日期并按照绑定时间降序排列
            this.deviceList = data.data.map(device => {
              // 格式化绑定时间
              const bindDate = new Date(device.createDate);
              const formattedBindTime = `${bindDate.getFullYear()}-${(bindDate.getMonth()+1).toString().padStart(2, '0')}-${bindDate.getDate().toString().padStart(2, '0')} ${bindDate.getHours().toString().padStart(2, '0')}:${bindDate.getMinutes().toString().padStart(2, '0')}:${bindDate.getSeconds().toString().padStart(2, '0')}`;
              return {
                device_id: device.id,
                model: device.board,
                firmwareVersion: device.appVersion,
                macAddress: device.macAddress,
                bindTime: formattedBindTime, // 使用格式化后的时间
                lastConversation: device.lastConnectedAt,
                remark: device.alias,
                isEdit: false,
                otaSwitch: device.autoUpdate === 1,
                // 添加原始时间用于排序
                rawBindTime: new Date(device.createDate).getTime()
              };
            })
            // 按照绑定时间降序排序
            .sort((a, b) => a.rawBindTime - b.rawBindTime);
          } else {
            this.$message.error(data.msg || '获取设备列表失败');
          }
        });
      }).catch(error => {
        console.error('模块加载失败:', error);
        this.$message.error('功能模块加载失败');
      });
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

.pagination {
  margin-top: 20px;
  text-align: right;
}
</style>
