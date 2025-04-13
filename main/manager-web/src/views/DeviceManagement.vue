<template>
  <div class="welcome">
    <HeaderBar />
    <el-main style="padding: 20px; display: flex; flex-direction: column;">
      <div class="table-container">
        <h3 class="device-list-title">设备列表</h3>
        <el-table ref="deviceTable" :data="paginatedDeviceList" @selection-change="handleSelectionChange" style="width: 100%; margin-top: 20px" border stripe>
          <el-table-column type="selection" align="center" width="60"></el-table-column>
          <el-table-column label="设备型号" prop="model" flex></el-table-column>
          <el-table-column label="固件版本" prop="firmwareVersion" width="120"></el-table-column>
          <el-table-column label="Mac地址" prop="macAddress"></el-table-column>
          <el-table-column label="绑定时间" prop="bindTime" width="200"></el-table-column>
          <el-table-column label="最近对话" prop="lastConversation" width="140"></el-table-column>
          <el-table-column label="备注" width="180">
            <template slot-scope="scope">
              <el-input v-if="scope.row.isEdit" v-model="scope.row.remark" size="mini"
                @blur="stopEditRemark(scope.$index)"></el-input>
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
              <el-switch v-model="scope.row.otaSwitch" size="mini" active-color="#13ce66"
                inactive-color="#ff4949"></el-switch>
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
        <div class="table_bottom">
          <div class="ctrl_btn">
            <el-button size="mini" type="primary" class="select-all-btn" @click="toggleAllSelection">
                {{ isAllSelected ? '取消全选' : '全选' }}
            </el-button>
            <el-button type="primary" size="mini" class="add-device-btn" @click="handleAddDevice">
                新增
            </el-button>
          </div>
          <div class="custom-pagination">
            <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">首页</button>
            <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">上一页</button>
            <button
              v-for="page in visiblePages"
              :key="page"
              class="pagination-btn"
              :class="{ active: page === currentPage }"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">下一页</button>
            <span class="total-text">共{{ deviceList.length }}条记录</span>
          </div>
        </div>
      </div>
      <div class="copyright">
        ©2025 xiaozhi-esp32-server
      </div>
      <AddDeviceDialog :visible.sync="addDeviceDialogVisible" :agent-id="currentAgentId"
        @refresh="fetchBindDevices(currentAgentId)" />
    </el-main>
  </div>
</template>

<script>
import Api from '@/apis/api';
import AddDeviceDialog from "@/components/AddDeviceDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";

export default {
  components: { HeaderBar, AddDeviceDialog },
  data() {
    return {
      addDeviceDialogVisible: false,
       selectedDevices: [],
      isAllSelected: false,
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
    },
    pageCount() {
    return Math.ceil(this.deviceList.length / this.pageSize);
    },
    visiblePages() {
      const pages = [];
      const maxVisible = 3;
      let start = Math.max(1, this.currentPage - 1);
      let end = Math.min(this.pageCount, start + maxVisible - 1);

      if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    },
  },
  mounted() {
    const agentId = this.$route.query.agentId;
    if (agentId) {
      this.fetchBindDevices(agentId);
    }
  },
  methods: {

    handleSelectionChange(val) {
      this.selectedDevices = val;
      this.isAllSelected = val.length === this.paginatedDeviceList.length;
    },
    toggleAllSelection() {
      this.$refs.deviceTable.toggleAllSelection();
    },


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
      this.$confirm('确认要解绑该设备吗？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        Api.device.unbindDevice(device_id, ({ data }) => {
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
    goFirst() {
      this.currentPage = 1;
    },
    goPrev() {
      if (this.currentPage > 1) this.currentPage--;
    },
    goNext() {
      if (this.currentPage < this.pageCount) this.currentPage++;
    },
    goToPage(page) {
      this.currentPage = page;
    },

    fetchBindDevices(agentId) {
      this.loading = true;
      Api.device.getAgentBindDevices(agentId, ({ data }) => {
        this.loading = false;
        if (data.code === 0) {
          // 格式化日期并按照绑定时间降序排列
          this.deviceList = data.data.map(device => {
            // 格式化绑定时间
            const bindDate = new Date(device.createDate);
            const formattedBindTime = `${bindDate.getFullYear()}-${(bindDate.getMonth() + 1).toString().padStart(2, '0')}-${bindDate.getDate().toString().padStart(2, '0')} ${bindDate.getHours().toString().padStart(2, '0')}:${bindDate.getMinutes().toString().padStart(2, '0')}:${bindDate.getSeconds().toString().padStart(2, '0')}`;
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
  background: linear-gradient(145deg, #e6eeff, #eff0ff);
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
  background: linear-gradient(135deg, #6b8cff, #a966ff) !important;
  border: none !important;
  color: white !important;
  margin-left: 10px;
  height: 32px;
  padding: 7px 12px;
  border-radius: 4px !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
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

.custom-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 15px;
}

.pagination-btn {
  min-width: 28px;
  height: 32px;
  padding: 0 12px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  background: #dee7ff;
  color: #606266;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.pagination-btn:first-child,
.pagination-btn:nth-child(2),
.pagination-btn:nth-last-child(2) {
  min-width: 60px;
}

.pagination-btn:hover {
  background: #d7dce6;
}

.pagination-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pagination-btn.active {
  background: #5f70f3 !important;
  color: #ffffff !important;
  border-color: #5f70f3 !important;
}

.total-text {
  color: #909399;
  font-size: 14px;
  margin-left: 10px;
}

.table_bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}

.ctrl_btn {
  display: flex;
  gap: 8px;
  padding-left: 26px;

  .el-button {
    min-width: 72px;
    height: 32px;
    padding: 7px 12px;
    border-radius: 4px;
    border: none;
    transition: all 0.3s;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
  }

  .el-button--primary {
    background: #5f70f3;
    color: white;
  }
}


</style>
