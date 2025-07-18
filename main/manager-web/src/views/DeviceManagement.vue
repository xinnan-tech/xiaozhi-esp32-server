<template>
  <div class="welcome">
    <HeaderBar/>

    <div class="operation-bar">
      <h2 class="page-title">设备管理</h2>
      <div class="right-operations">
        <el-input placeholder="请输入设备型号或Mac地址查询" v-model="searchKeyword" class="search-input"
                  @keyup.enter.native="handleSearch" clearable/>
        <el-button class="btn-search" @click="handleSearch">搜索</el-button>
      </div>
    </div>

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="device-card" shadow="never">
            <el-table ref="deviceTable" :data="paginatedDeviceList" class="transparent-table"
                      :header-cell-class-name="headerCellClassName" v-loading="loading"
                      element-loading-text="拼命加载中"
                      element-loading-spinner="el-icon-loading" element-loading-background="rgba(255, 255, 255, 0.7)">
              <el-table-column label="选择" align="center" width="120">
                <template slot-scope="scope">
                  <el-checkbox v-model="scope.row.selected"></el-checkbox>
                </template>
              </el-table-column>
              <el-table-column label="设备型号" prop="model" align="center">
                <template slot-scope="scope">
                  {{ getFirmwareTypeName(scope.row.model) }}
                </template>
              </el-table-column>
              <el-table-column label="固件版本" prop="firmwareVersion" align="center"></el-table-column>
              <el-table-column label="Mac地址" prop="macAddress" align="center"></el-table-column>
              <el-table-column label="绑定时间" prop="bindTime" align="center"></el-table-column>
              <el-table-column label="最近对话" prop="lastConversation" align="center"></el-table-column>
              <el-table-column label="备注" align="center">
                <template #default="{ row }">
                  <el-input
                      v-show="row.isEdit"
                      v-model="row.remark"
                      size="mini"
                      maxlength="64"
                      show-word-limit
                      @blur="onRemarkBlur(row)"
                      @keyup.enter.native="onRemarkEnter(row)"
                  />
                  <span v-show="!row.isEdit" class="remark-view">
                  <i
                      class="el-icon-edit"
                      @click="row.isEdit = true"
                      style="cursor: pointer;"
                  ></i>
                  <span @click="row.isEdit = true">
                    {{ row.remark || '—' }}
                  </span>
                </span>
                </template>
              </el-table-column>
              <el-table-column label="OTA升级" align="center">
                <template slot-scope="scope">
                  <el-switch v-model="scope.row.otaSwitch" size="mini" active-color="#13ce66" inactive-color="#ff4949"
                             @change="handleOtaSwitchChange(scope.row)"></el-switch>
                </template>
              </el-table-column>
              <el-table-column label="操作" align="center">
                <template slot-scope="scope">
                  <el-button size="mini" type="text" @click="handleUnbind(scope.row.device_id)">
                    解绑
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="table_bottom">
              <div class="ctrl_btn">
                <el-button size="mini" type="primary" class="select-all-btn" @click="handleSelectAll">
                  {{ isAllSelected ? '取消全选' : '全选' }}
                </el-button>
                <el-button type="success" size="mini" class="add-device-btn" @click="handleAddDevice">
                  验证码绑定
                </el-button>
                <el-button type="success" size="mini" class="add-device-btn" @click="handleManualAddDevice">
                  手动添加
                </el-button>
                <el-button size="mini" type="danger" icon="el-icon-delete" @click="deleteSelected">解绑</el-button>
              </div>
              <div class="custom-pagination">
                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                  <el-option v-for="item in pageSizeOptions" :key="item" :label="`${item}条/页`" :value="item">
                  </el-option>
                </el-select>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">首页</button>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">上一页</button>
                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                        :class="{ active: page === currentPage }" @click="goToPage(page)">
                  {{ page }}
                </button>
                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">下一页</button>
                <span class="total-text">共{{ deviceList.length }}条记录</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <AddDeviceDialog :visible.sync="addDeviceDialogVisible" :agent-id="currentAgentId"
                     @refresh="fetchBindDevices(currentAgentId)"/>
    <ManualAddDeviceDialog :visible.sync="manualAddDeviceDialogVisible" :agent-id="currentAgentId"
                     @refresh="fetchBindDevices(currentAgentId)"/>

  </div>
</template>

<script>
import Api from '@/apis/api';
import AddDeviceDialog from "@/components/AddDeviceDialog.vue";
import ManualAddDeviceDialog from "@/components/ManualAddDeviceDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";

export default {
  components: {
    HeaderBar, 
    AddDeviceDialog,
    ManualAddDeviceDialog
  },
  data() {
    return {
      addDeviceDialogVisible: false,
      manualAddDeviceDialogVisible: false,
      selectedDevices: [],
      isAllSelected: false,
      searchKeyword: "",
      activeSearchKeyword: "",
      currentAgentId: this.$route.query.agentId || '',
      currentPage: 1,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50, 100],
      deviceList: [],
      loading: false,
      userApi: null,
      firmwareTypes: [],
    };
  },
  computed: {
    filteredDeviceList() {
      const keyword = this.activeSearchKeyword.toLowerCase();
      if (!keyword) return this.deviceList;
      return this.deviceList.filter(device =>
          (device.model && device.model.toLowerCase().includes(keyword)) ||
          (device.macAddress && device.macAddress.toLowerCase().includes(keyword))
      );
    },

    paginatedDeviceList() {
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      return this.filteredDeviceList.slice(start, end);
    },
    pageCount() {
      return Math.ceil(this.filteredDeviceList.length / this.pageSize);
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
  created() {
    this.getFirmwareTypes()
  },
  methods: {
    async getFirmwareTypes() {
      try {
        const res = await Api.dict.getDictDataByType('FIRMWARE_TYPE')
        this.firmwareTypes = res.data
      } catch (error) {
        console.error('获取固件类型失败:', error)
        this.$message.error(error.message || '获取固件类型失败')
      }
    },
    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
    },
    handleSearch() {
      this.activeSearchKeyword = this.searchKeyword;
      this.currentPage = 1;
    },

    handleSelectAll() {
      this.isAllSelected = !this.isAllSelected;
      this.paginatedDeviceList.forEach(row => {
        row.selected = this.isAllSelected;
      });
      this.selectedDevices = this.paginatedDeviceList.filter(device => device.selected);
    },

    deleteSelected() {
      this.selectedDevices = this.paginatedDeviceList.filter(device => device.selected);
      if (this.selectedDevices.length === 0) {
        this.$message.warning({
          message: '请至少选择一条记录',
          showClose: true
        });
        return;
      }

      this.$confirm(`确认要解绑选中的 ${this.selectedDevices.length} 台设备吗？`, '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const deviceIds = this.selectedDevices.map(device => device.device_id);
        this.batchUnbindDevices(deviceIds);
      });
    },
    batchUnbindDevices(deviceIds) {
      const promises = deviceIds.map(id => {
        return new Promise((resolve, reject) => {
          Api.device.unbindDevice(id, ({data}) => {
            if (data.code === 0) {
              resolve();
            } else {
              reject(data.msg || '解绑失败');
            }
          });
        });
      });
      Promise.all(promises)
          .then(() => {
            this.$message.success({
              message: `成功解绑 ${deviceIds.length} 台设备`,
              showClose: true
            });
            this.fetchBindDevices(this.currentAgentId);
            this.selectedDevices = [];
            this.isAllSelected = false;
          })
          .catch(error => {
            this.$message.error({
              message: error || '批量解绑过程中出现错误',
              showClose: true
            });
          });
    },
    handleAddDevice() {
      this.addDeviceDialogVisible = true;
    },
    handleManualAddDevice() {
      this.manualAddDeviceDialogVisible = true;
    },
    submitRemark(row) {
      if (row._submitting) return;

      const text = (row.remark || '').trim();
      if (text.length > 64) {
        this.$message.warning('备注不能超过 64 字符');
        return;
      }
      if (text === row._originalRemark) {
        return;
      }

      row._submitting = true;
      this.updateDeviceInfo(row.device_id, { alias: text }, (ok, resp) => {
        if (ok) {
          row._originalRemark = text;
          this.$message.success('备注已保存');
        } else {
          row.remark = row._originalRemark;
          this.$message.error(resp.msg || '备注保存失败');
        }
        row._submitting = false;
      });
    },
    // 备注输入框：失焦时提交
    onRemarkBlur(row) {
      row.isEdit = false;
      setTimeout(() => {
        this.submitRemark(row);
      }, 100); // 延迟 100ms，避开 enter+blur 同时触发的窗口
    },
    // 备注输入框：按回车时提交
    onRemarkEnter(row) {
      row.isEdit = false;
      this.submitRemark(row);
    },
    handleUnbind(device_id) {
      this.$confirm('确认要解绑该设备吗？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        Api.device.unbindDevice(device_id, ({data}) => {
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
      Api.device.getAgentBindDevices(agentId, ({data}) => {
        this.loading = false;
        if (data.code === 0) {
          this.deviceList = data.data.map(device => {
            return {
              device_id: device.id,
              model: device.board,
              firmwareVersion: device.appVersion,
              macAddress: device.macAddress,
              bindTime: device.createDate,
              lastConversation: device.lastConnectedAt,
              remark: device.alias,
              _originalRemark: device.alias,
              isEdit: false,
              _submitting: false,
              otaSwitch: device.autoUpdate === 1,
              rawBindTime: new Date(device.createDate).getTime()
            };
          })
              .sort((a, b) => a.rawBindTime - b.rawBindTime);
          this.activeSearchKeyword = "";
          this.searchKeyword = "";
        } else {
          this.$message.error(data.msg || '获取设备列表失败');
        }
      });
    },
    headerCellClassName({columnIndex}) {
      if (columnIndex === 0) {
        return "custom-selection-header";
      }
      return "";
    },
    getFirmwareTypeName(type) {
      const firmwareType = this.firmwareTypes.find(item => item.key === type)
      return firmwareType ? firmwareType.name : type
    },
    updateDeviceInfo(device_id, payload, callback) {
      return Api.device.updateDeviceInfo(device_id, payload, ({data}) => {
        callback(data.code === 0, data);
      })
    },
    handleOtaSwitchChange(row) {
      this.updateDeviceInfo(row.device_id, {autoUpdate: row.otaSwitch ? 1 : 0}, (result, {msg}) => {
        if (result) {
          this.$message.success(row.otaSwitch ? '已设置成自动升级' : '已关闭自动升级');
          return;
        }
        row.otaSwitch = !row.otaSwitch
        this.$message.error(msg || '操作失败')
      })
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
  position: relative;
  flex-direction: column;
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd);
  background-size: cover;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.main-wrapper {
  margin: 5px 22px;
  border-radius: 15px;
  min-height: calc(100vh - 24vh);
  height: auto;
  max-height: 80vh;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237, 242, 255, 0.5);
  display: flex;
  flex-direction: column;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
  color: #2c3e50;
}

.right-operations {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.search-input {
  width: 280px;
  border-radius: 4px;
}

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
}

::v-deep .search-input .el-input__inner {
  border-radius: 4px;
  border: 1px solid #DCDFE6;
  background-color: white;
  transition: border-color 0.2s;
}

::v-deep .page-size-select {
  width: 100px;
  margin-right: 8px;
}

::v-deep .page-size-select .el-input__inner {
  height: 32px;
  line-height: 32px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  background: #dee7ff;
  color: #606266;
  font-size: 14px;
}

::v-deep .page-size-select .el-input__suffix {
  right: 6px;
  width: 15px;
  height: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  top: 6px;
  border-radius: 4px;
}

::v-deep .page-size-select .el-input__suffix-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

::v-deep .page-size-select .el-icon-arrow-up:before {
  content: "";
  display: inline-block;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 9px solid #606266;
  position: relative;
  transform: rotate(0deg);
  transition: transform 0.3s;
}

::v-deep .search-input .el-input__inner:focus {
  border-color: #6b8cff;
  outline: none;
}

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.content-area {
  flex: 1;
  height: 100%;
  min-width: 600px;
  overflow: auto;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.device-card {
  background: white;
  border: none;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

::v-deep .el-card__body {
  padding: 15px;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.table_bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-bottom: 10px;
}


.ctrl_btn {
  display: flex;
  gap: 8px;
  padding-left: 26px;
}

.ctrl_btn .el-button {
  min-width: 72px;
  height: 32px;
  padding: 7px 12px 7px 10px;
  font-size: 12px;
  border-radius: 4px;
  line-height: 1;
  font-weight: 500;
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.ctrl_btn .el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.ctrl_btn .el-button--primary {
  background: #5f70f3;
  color: white;
}

.ctrl_btn .el-button--success {
  background: #5bc98c;
  color: white;
}

.ctrl_btn .el-button--danger {
  background: #fd5b63;
  color: white;
}

.custom-pagination {
  display: flex;
  align-items: center;
  gap: 10px;
}

.custom-pagination .el-select {
  margin-right: 8px;
}

.custom-pagination .pagination-btn:first-child,
.custom-pagination .pagination-btn:nth-child(2),
.custom-pagination .pagination-btn:nth-last-child(2),
.custom-pagination .pagination-btn:nth-child(3) {
  min-width: 60px;
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

.custom-pagination .pagination-btn:first-child:hover,
.custom-pagination .pagination-btn:nth-child(2):hover,
.custom-pagination .pagination-btn:nth-last-child(2):hover,
.custom-pagination .pagination-btn:nth-child(3):hover {
  background: #d7dce6;
}

.custom-pagination .pagination-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.custom-pagination .pagination-btn:not(:first-child):not(:nth-child(3)):not(:nth-child(2)):not(:nth-last-child(2)) {
  min-width: 28px;
  height: 32px;
  padding: 0;
  border-radius: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: #606266;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.custom-pagination .pagination-btn:not(:first-child):not(:nth-child(3)):not(:nth-child(2)):not(:nth-last-child(2)):hover {
  background: rgba(245, 247, 250, 0.3);
}

.custom-pagination .pagination-btn.active {
  background: #5f70f3 !important;
  color: #ffffff !important;
  border-color: #5f70f3 !important;
}

.custom-pagination .pagination-btn.active:hover {
  background: #6d7cf5 !important;
}

.custom-pagination .total-text {
  color: #909399;
  font-size: 14px;
  margin-left: 10px;
}

:deep(.transparent-table) {
  background: white;
  border: none;
}

:deep(.transparent-table .el-table__header th) {
  background: white !important;
  color: black;
  border-right: none !important;
}

:deep(.transparent-table .el-table__body tr td) {
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  border-right: none !important;
}

:deep(.transparent-table .el-table__header tr th:first-child .cell),
:deep(.transparent-table .el-table__body tr td:first-child .cell) {
  padding-left: 10px;
}

:deep(.el-icon-edit) {
  color: #7079aa;
  cursor: pointer;
}

:deep(.el-icon-edit:hover) {
  color: #5a64b5;
}

:deep(.custom-selection-header .el-checkbox) {
  display: none !important;
}


:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}

:deep(.transparent-table) {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 40vh);
}

:deep(.el-table__body-wrapper) {
  flex: 1;
  overflow-y: auto;
  max-height: none !important;
}

:deep(.el-table__header-wrapper) {
  flex-shrink: 0;
}

@media (min-width: 1144px) {
  .table_bottom {
    margin-top: 40px;
  }

  :deep(.transparent-table) .el-table__body tr td {
    padding-top: 16px;
    padding-bottom: 16px;
  }
}

:deep(.el-checkbox__inner) {
  background-color: #eeeeee !important;
  border-color: #cccccc !important;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #cccccc !important;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #5f70f3 !important;
  border-color: #5f70f3 !important;
}

::v-deep .el-table--border::after,
::v-deep .el-table--group::after,
::v-deep .el-table::before {
  display: none !important;
}
</style>
