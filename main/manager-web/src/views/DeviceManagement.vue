<template>
  <div class="welcome">
    <HeaderBar />

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <el-card class="device-card" shadow="never">
            <div class="operation-header">
              <h2 class="page-title">{{ $t('device.management') }}</h2>
              <div class="right-operations">
                <el-input :placeholder="$t('device.searchPlaceholder')" v-model="searchKeyword" class="search-input"
                  @keyup.enter.native="handleSearch" clearable />
                <CustomButton icon="el-icon-search" type="confirm" @click="handleSearch">{{ $t('device.search') }}</CustomButton>
              </div>
            </div>
            <CustomTable
              ref="deviceTable"
              :data="paginatedDeviceList"
              :columns="tableColumns"
              :loading="loading"
              :loading-text="$t('deviceManagement.loading')"
              :show-selection="true"
              :show-operations="true"
              :operations-label="$t('device.operation')"
              :total="filteredDeviceList.length"
              :current-page="currentPage"
              :page-size="pageSize"
              :page-size-options="pageSizeOptions"
              @size-change="handlePageSizeChange"
              @page-change="goToPage"
            >
              <template slot="model" slot-scope="scope">
                {{ getFirmwareTypeName(scope.row.model) }}
              </template>
              <template slot="macAddress" slot-scope="scope">
                <MacAddressMask :macAddress="scope.row.macAddress" />
              </template>
              <template slot="deviceStatus" slot-scope="scope">
                <el-tag v-if="scope.row.deviceStatus === 'online'" type="success">{{ $t('device.online') }}</el-tag>
                <el-tag v-else type="danger">{{ $t('device.offline') }}</el-tag>
              </template>
              <template slot="remark" slot-scope="scope">
                <el-input v-show="scope.row.isEdit" v-model="scope.row.remark" size="mini" maxlength="64" show-word-limit
                  @blur="onRemarkBlur(scope.row)" @keyup.enter.native="onRemarkEnter(scope.row)" />
                <span v-show="!scope.row.isEdit" class="remark-view">
                  <i class="el-icon-edit" @click="scope.row.isEdit = true" style="cursor: pointer;"></i>
                  <span @click="scope.row.isEdit = true">
                    {{ scope.row.remark || '-' }}
                  </span>
                </span>
              </template>
              <template slot="otaSwitch" slot-scope="scope">
                <el-switch v-model="scope.row.otaSwitch" size="mini" active-color="#13ce66" inactive-color="#ff4949"
                  @change="handleOtaSwitchChange(scope.row)"></el-switch>
              </template>
              <template slot="operations" slot-scope="scope">
                <el-button size="mini" type="text" @click="handleUnbind(scope.row.device_id)">
                  {{ $t('device.unbind') }}
                </el-button>
                <el-button v-if="isGenerate(scope.row)" size="mini" type="text" @click="handleGenertor(scope.row)">
                  {{ $t('device.deviceThemeGeneration') }}
                </el-button>
              </template>
              <template slot="footer-btns">
                <div class="ctrl_btn">
                  <CustomButton :icon="isCurrentPageAllSelected ? 'el-icon-circle-close' : 'el-icon-circle-check'" size="small" @click="handleSelectAll">
                    {{ isCurrentPageAllSelected ? $t('common.deselectAll') : $t('common.selectAll') }}
                  </CustomButton>
                  <CustomButton icon="el-icon-plus" type="add" size="small" @click="handleAddDevice">
                    {{ $t('device.bindWithCode') }}
                  </CustomButton>
                  <CustomButton icon="el-icon-plus" type="add" size="small" @click="handleManualAddDevice">
                    {{ $t('device.manualAdd') }}
                  </CustomButton>
                  <CustomButton size="small" type="delete" icon="el-icon-delete" @click="deleteSelected">
                    {{ $t('device.unbind') }}
                  </CustomButton>
                </div>
              </template>
            </CustomTable>
          </el-card>
        </div>
      </div>
    </div>

    <AddDeviceDialog :visible.sync="addDeviceDialogVisible" :agent-id="currentAgentId"
      @refresh="fetchBindDevices(currentAgentId)" />
    <ManualAddDeviceDialog :visible.sync="manualAddDeviceDialogVisible" :agent-id="currentAgentId"
      @refresh="fetchBindDevices(currentAgentId)" />
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from '@/apis/api';
import AddDeviceDialog from "@/components/AddDeviceDialog.vue";
import HeaderBar from "@/components/HeaderBar.vue";
import ManualAddDeviceDialog from "@/components/ManualAddDeviceDialog.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import MacAddressMask from "@/components/MacAddressMask.vue";
import CustomButton from "@/components/CustomButton.vue";
import CustomTable from "@/components/CustomTable.vue";
import {
  compareTimestamps,
  formatCreateDate,
  formatTimestamp,
  hasTimestampValue,
  parseLegacyDate,
  parseTimestamp,
} from '@/utils/deviceTime.mjs';

export default {
  components: {
    HeaderBar,
    AddDeviceDialog,
    ManualAddDeviceDialog,
    VersionFooter,
    MacAddressMask,
    CustomButton,
    CustomTable,
  },
  data() {
    return {
      addDeviceDialogVisible: false,
      manualAddDeviceDialogVisible: false,
      selectedDeviceId: '',
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
      mqttServiceAvailable: false,
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
    isCurrentPageAllSelected() {
      return this.paginatedDeviceList.length > 0 &&
        this.paginatedDeviceList.every(device => device.selected);
    },
    tableColumns() {
      const columns = [
        { prop: 'model', label: this.$t('device.model'), align: 'center' },
        { prop: 'firmwareVersion', label: this.$t('device.firmwareVersion'), align: 'center' },
        { prop: 'macAddress', label: this.$t('device.macAddress'), align: 'center' },
        { prop: 'bindTime', label: this.$t('device.bindTime'), align: 'center' },
        { prop: 'lastConversation', label: this.$t('device.lastConversation'), align: 'center' },
      ];
      if (this.mqttServiceAvailable) {
        columns.push({ prop: 'deviceStatus', label: this.$t('device.deviceStatus'), align: 'center' });
      }
      columns.push({ prop: 'remark', label: this.$t('device.remark'), align: 'center' });
      columns.push({ prop: 'otaSwitch', label: this.$t('device.autoUpdate'), align: 'center' });
      return columns;
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
        console.error(this.$t('device.getFirmwareTypeFailed') + ':', error)
        this.$message.error(error.message || this.$t('device.getFirmwareTypeFailed'))
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
      const shouldSelectAll = !this.isCurrentPageAllSelected;
      this.paginatedDeviceList.forEach(row => {
        row.selected = shouldSelectAll;
      });
    },

    deleteSelected() {
      const selectedDevices = this.paginatedDeviceList.filter(device => device.selected);
      if (selectedDevices.length === 0) {
        this.$message.warning({
          message: this.$t('device.selectAtLeastOne'),
          showClose: true
        });
        return;
      }

      this.$confirm(this.$t('device.confirmBatchUnbind').replace('{count}', selectedDevices.length), this.$t('message.warning'), {
        confirmButtonText: this.$t('button.ok'),
        cancelButtonText: this.$t('button.cancel'),
        type: 'warning'
      }).then(() => {
        const deviceIds = selectedDevices.map(device => device.device_id);
        this.batchUnbindDevices(deviceIds);
      });
    },
    batchUnbindDevices(deviceIds) {
      const promises = deviceIds.map(id => {
        return new Promise((resolve, reject) => {
          Api.device.unbindDevice(id, ({ data }) => {
            if (data.code === 0) {
              resolve();
            } else {
              reject(data.msg || this.$t('device.bindFailed'));
            }
          });
        });
      });
      Promise.all(promises)
        .then(() => {
          this.$message.success({
            message: this.$t('device.batchUnbindSuccess').replace('{count}', deviceIds.length),
            showClose: true
          });
          this.fetchBindDevices(this.currentAgentId);
        })
        .catch(error => {
          this.$message.error({
            message: error || this.$t('device.batchUnbindError'),
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
        this.$message.warning(this.$t('device.remarkTooLong'));
        return;
      }
      if (text === row._originalRemark) {
        return;
      }

      row._submitting = true;
      this.updateDeviceInfo(row.device_id, { alias: text }, (ok, resp) => {
        if (ok) {
          row._originalRemark = text;
          this.$message.success(this.$t('device.remarkSaved'));
        } else {
          row.remark = row._originalRemark;
          this.$message.error(resp.msg || this.$t('device.remarkSaveFailed'));
        }
        row._submitting = false;
      });
    },
    onRemarkBlur(row) {
      row.isEdit = false;
      setTimeout(() => {
        this.submitRemark(row);
      }, 100);
    },
    onRemarkEnter(row) {
      row.isEdit = false;
      this.submitRemark(row);
    },
    handleUnbind(device_id) {
      this.$confirm(this.$t('device.confirmUnbind'), this.$t('message.warning'), {
        confirmButtonText: this.$t('button.ok'),
        cancelButtonText: this.$t('button.cancel'),
        type: 'warning'
      }).then(() => {
        Api.device.unbindDevice(device_id, ({ data }) => {
          if (data.code === 0) {
            this.$message.success({
              message: this.$t('device.unbindSuccess'),
              showClose: true
            });
            this.fetchBindDevices(this.$route.query.agentId);
          } else {
            this.$message.error({
              message: data.msg || this.$t('device.unbindFailed'),
              showClose: true
            });
          }
        });
      });
    },
    handleGenertor(row) {
      const pathname = window.location.pathname;
      const basePath = pathname.split('/').slice(0, -1).join('/');
      const url = `${window.location.origin}${basePath}/generator/?deviceId=${row.device_id}`;
      sessionStorage.setItem('devicePath', window.location.href);
      window.location.href = url;
    },
    goToPage(page) {
      this.currentPage = page;
    },

    fetchBindDevices(agentId) {
      this.loading = true;
      Api.device.getAgentBindDevices(agentId, ({ data }) => {
        this.loading = false;
        if (data.code === 0) {
          this.deviceList = data.data.map(device => {
            const hasCreateDateTimestamp = hasTimestampValue(device.createDateTimestamp);
            const rawBindTime = hasCreateDateTimestamp
              ? parseTimestamp(device.createDateTimestamp)
              : parseLegacyDate(device.createDate);
            return {
              device_id: device.id,
              model: device.board,
              firmwareVersion: device.appVersion,
              macAddress: device.macAddress,
              bindTime: formatCreateDate(device.createDateTimestamp, device.createDate),
              lastConversation: formatTimestamp(device.lastConnectedAtTimestamp),
              remark: device.alias,
              _originalRemark: device.alias,
              isEdit: false,
              _submitting: false,
              otaSwitch: device.autoUpdate === 1,
              rawBindTime,
              selected: false,
              deviceStatus: 'offline'
            };
          })
            .sort((firstDevice, secondDevice) => compareTimestamps(
              firstDevice.rawBindTime,
              secondDevice.rawBindTime,
            ));
          this.activeSearchKeyword = "";
          this.searchKeyword = "";

          this.fetchDeviceStatus(agentId);
        } else {
          this.$message.error(data.msg || this.$t('device.getListFailed'));
        }
      });
    },

    fetchDeviceStatus(agentId) {
      this.loading = true;
      Api.device.getDeviceStatus(agentId, ({ data }) => {
        this.loading = false;
        if (data.code === 0) {
          try {
            const statusData = JSON.parse(data.data);

            if (statusData && typeof statusData === 'object') {
              this.mqttServiceAvailable = true;
              this.updateDeviceStatusFromResponse(statusData);
            } else {
              this.mqttServiceAvailable = false;
            }
          } catch (error) {
            this.mqttServiceAvailable = false;
          }
        } else {
          this.mqttServiceAvailable = false;
        }
      });
    },

    updateDeviceStatusFromResponse(deviceStatusMap) {
      this.deviceList.forEach(device => {
        const macAddress = device.macAddress ? device.macAddress.replace(/:/g, '_') : 'unknown';
        const groupId = device.model ? device.model.replace(/:/g, '_') : 'GID_default';
        const mqttClientId = `${groupId}@@@${macAddress}@@@${macAddress}`;

        if (deviceStatusMap[mqttClientId]) {
          const statusInfo = deviceStatusMap[mqttClientId];

          let isOnline = false;
          if (statusInfo.isAlive === true) {
            isOnline = true;
          } else if (statusInfo.isAlive === false) {
            isOnline = false;
          } else if (statusInfo.isAlive === null && statusInfo.exists === true) {
            isOnline = true;
          } else {
            isOnline = false;
          }

          device.deviceStatus = isOnline ? 'online' : 'offline';
        } else {
          device.deviceStatus = 'offline';
        }
      });
    },
    getFirmwareTypeName(type) {
      const firmwareType = this.firmwareTypes.find(item => item.key === type)
      return firmwareType ? firmwareType.name : type
    },
    updateDeviceInfo(device_id, payload, callback) {
      return Api.device.updateDeviceInfo(device_id, payload, ({ data }) => {
        callback(data.code === 0, data);
      })
    },
    handleOtaSwitchChange(row) {
      this.updateDeviceInfo(row.device_id, { autoUpdate: row.otaSwitch ? 1 : 0 }, (result, { msg }) => {
        if (result) {
          this.$message.success(row.otaSwitch ? this.$t('device.autoUpdateEnabled') : this.$t('device.autoUpdateDisabled'));
          return;
        }
        row.otaSwitch = !row.otaSwitch
        this.$message.error(msg || this.$t('message.error'))
      })
    },
    isGenerate(row) {
      const version = row.firmwareVersion.replace(/\./g, '');
      return Number(version) >= 200;
    },
  }
};
</script>

<style lang="scss" scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background: #eff4ff;
  background-size: cover;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;
}

.main-wrapper {
  height: calc(100vh - 63px - 35px);
  padding: 20px 22px 0;
  position: relative;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.operation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 16px 0;
}

.page-title {
  font-weight: 500;
  font-size: 24px;
  margin: 0;
}

.right-operations {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.search-input {
  width: 240px;
}

.content-panel {
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
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  overflow: hidden;

  ::v-deep .el-card__body {
    padding: 14px 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }
}

.ctrl_btn {
  display: flex;
  gap: 8px;
}

:deep(.el-table .el-button--text) {
  color: #7079aa;
}

:deep(.el-table .el-button--text:hover) {
  color: #5a64b5;
}

:deep(.el-icon-edit) {
  color: #7079aa;
  cursor: pointer;
}

:deep(.el-icon-edit:hover) {
  color: #5a64b5;
}
</style>
