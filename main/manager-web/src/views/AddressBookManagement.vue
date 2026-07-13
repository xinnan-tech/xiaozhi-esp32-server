<template>
  <div class="welcome">
    <HeaderBar />

    <div class="page-content">
      <!-- 左侧设备列表 -->
      <div class="left-panel">
        <div class="left-header">
          <h1 class="main-title">{{ $t('addressBookManagement.mainTitle') }}</h1>
          <p class="sub-title">{{ $t('addressBookManagement.subTitle') }}</p>
        </div>

        <div class="search-bar">
          <el-input
            :placeholder="$t('addressBookManagement.searchPlaceholder')"
            v-model="searchKeyword"
            class="search-input"
            @input="handleSearch"
            clearable
          />
        </div>

        <!-- 智能体列表 -->
        <el-collapse accordion class="agent-collapse" v-model="expandedAgentId">
          <el-collapse-item v-for="agent in filteredAgents" :key="agent.id" :name="agent.id">
            <template slot="title">
              <svg class="agent-triangle" width="8" height="12" viewBox="0 0 10 14" fill="#c8cafb">
                <path d="M2 2L8 7L2 12L2 2Z" stroke="#c8cafb" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
              </svg>
              <span class="agent-name">{{ agent.agentName }} ({{ agent.deviceCount || 0 }})</span>
            </template>
            <div class="device-list">
              <div
                v-for="device in agent.devices"
                :key="device.id"
                class="device-item"
                :class="{ active: selectedDevice && selectedDevice.id === device.id }"
                @click="handleDeviceClick(device, agent)"
              >
                <div class="device-avatar">
                  <img :src="getDeviceAvatar(device.id)" alt="avatar" />
                </div>
                <div class="device-content">
                  <div class="device-name">
                    <MacAddressMask :macAddress="device.name" />
                  </div>
                  <div class="device-row">
                    <span class="device-id">
                      <MacAddressMask :macAddress="device.deviceId" />
                    </span>
                    <span class="device-status" :class="device.online ? 'online' : 'offline'">
                      {{ device.online ? $t('addressBookManagement.online') : $t('addressBookManagement.offline') }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 右侧通讯录详情 -->
      <div class="right-panel">
        <div class="device-detail" v-if="selectedDevice">
          <!-- 设备信息头部 -->
          <div class="device-header">
            <div class="device-left">
              <div class="device-avatar-large">
                <img :src="getDeviceAvatar(selectedDevice.id)" alt="avatar" />
              </div>
              <div class="device-info">
                <div class="device-name-row">
                  <input
                    v-if="isEditingAlias"
                    v-model="editAliasValue"
                    class="alias-input"
                    ref="aliasInput"
                    @blur="handleAliasBlur"
                    @keyup.enter="handleAliasBlur"
                    autofocus
                  />
                  <span v-else class="device-name-text" @click="handleStartEdit">
                    <MacAddressMask :macAddress="selectedDevice.name" />
                  </span>
                  <i v-if="!isEditingAlias" class="el-icon-edit" @click="handleStartEdit"></i>
                </div>
                <div class="device-mac">
                  {{ $t('addressBookManagement.macAddress') }}：
                  <MacAddressMask :macAddress="selectedDevice.deviceId" />
                </div>
                <div class="device-status">
                  <span>{{ $t('addressBookManagement.status') }}：</span>
                  <span :class="selectedDevice.online ? 'online' : 'offline'">
                  <i class="status-dot"></i>
                  <span>{{ selectedDevice.online ? $t('addressBookManagement.online') : $t('addressBookManagement.offline') }}</span></span>
                </div>
              </div>
            </div>
            <div class="device-stats">
              <div class="stat-item">
                <i class="el-icon-folder"></i>
                <div class="stat-content">
                  <div class="stat-label">{{ $t('addressBookManagement.deviceGroup') }}</div>
                  <div class="stat-value-row">
                    <input
                      v-if="isEditingAgentName"
                      v-model="editAgentNameValue"
                      class="stat-edit-input"
                      ref="agentNameInput"
                      @blur="handleAgentNameBlur"
                      @keyup.enter="handleAgentNameBlur"
                      autofocus
                    />
                    <span v-else class="stat-value" @click="handleStartEditAgentName">{{ selectedAgent ? selectedAgent.agentName : '-' }}</span>
                    <i v-if="!isEditingAgentName && selectedAgent" class="el-icon-edit stat-edit-icon" @click="handleStartEditAgentName"></i>
                  </div>
                </div>
              </div>
              <div class="stat-item">
                <i class="el-icon-time"></i>
                <div class="stat-content">
                  <div class="stat-label">{{ $t('addressBookManagement.addTime') }}</div>
                  <div class="stat-value">{{ formatDeviceCreateDate(selectedDevice) }}</div>
                </div>
              </div>
              <div class="stat-item">
                <i class="el-icon-link"></i>
                <div class="stat-content">
                  <div class="stat-label">{{ $t('addressBookManagement.lastOnline') }}</div>
                  <div class="stat-value">{{ getTimeAgo(selectedDevice.lastConnectedAt) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 权限管理区域 -->
          <div class="permission-section">
            <div class="section-header">
              <div class="section-title">
                <h3>{{ $t('addressBookManagement.deviceCallPermission') }}</h3>
                <p class="section-desc">{{ $t('addressBookManagement.setPermissionDesc', { count: selectedPermissions.length }) }}</p>
              </div>
              <div class="section-actions">
                <CustomButton size="small" @click="handleCancel">{{ $t('common.cancel') }}</CustomButton>
                <CustomButton size="small" @click="handleToggleSelectAll">{{ isAllSelected ? $t('addressBookManagement.deselectAll') : $t('addressBookManagement.selectAll') }}</CustomButton>
                <CustomButton type="confirm" size="small" @click="handleSavePermissions">{{ $t('addressBookManagement.save') }}</CustomButton>
              </div>
            </div>

            <div class="permission-grid">
              <div
                v-for="device in allDevices"
                :key="device.id"
                class="permission-item"
                :class="{ active: selectedPermissions.includes(device.id) }"
              >
                <el-checkbox
                  class="permission-checkbox"
                  :value="selectedPermissions.includes(device.id)"
                  @change="(checked) => handlePermissionToggle(device.id, checked)"
                ></el-checkbox>
                <div class="permission-avatar">
                  <img :src="getDeviceAvatar(device.id)" alt="avatar" />
                </div>
                <div class="permission-content">
                  <div class="permission-name-row">
                    <input
                      v-if="editingDeviceId === device.id"
                      v-model="editingDeviceName"
                      class="permission-edit-input"
                      @blur="handleEditPermissionBlur(device)"
                      @keyup.enter="handleEditPermissionBlur(device)"
                      autofocus
                    />
                    <span v-else class="permission-name" @click.stop="handleStartEditPermission(device)">
                      <MacAddressMask :macAddress="device.addressBookAlias || device.name" />
                    </span>
                    <i v-if="editingDeviceId !== device.id" class="el-icon-edit permission-edit-btn" @click.stop="handleStartEditPermission(device)"></i>
                  </div>
                  <div class="permission-id">
                    <MacAddressMask :macAddress="device.deviceId" />
                  </div>
                  <div class="permission-status" :class="device.online ? 'online' : 'offline'">
                    {{ device.online ? $t('addressBookManagement.online') : $t('addressBookManagement.offline') }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <el-empty :description="$t('addressBookManagement.selectDevice')" v-else>
        </el-empty>
      </div>
    </div>

    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import Api from "@/apis/api.js";
import AddressBookApi from "@/apis/module/addressBook.js";
import MacAddressMask from "@/components/MacAddressMask.vue";
import CustomButton from "@/components/CustomButton.vue";
import { formatCreateDate, parseTimestamp } from '@/utils/deviceTime.mjs';

export default {
  name: "AddressBookManagement",
  components: { HeaderBar, VersionFooter, MacAddressMask, CustomButton },
  data() {
    return {
      searchKeyword: "",
      filteredAgents: [],
      selectedAgent: null,
      selectedDevice: null,
      expandedAgentId: null,
      agentDeviceOptions: [],
      allDevices: [],
      selectedPermissions: [],
      originalPermissions: [],
      isEditingAlias: false,
      editAliasValue: '',
      isEditingAgentName: false,
      editAgentNameValue: '',
      editingDeviceId: null,
      editingDeviceName: '',
      mqttServiceAvailable: false
    };
  },
  created() {
    this.fetchAgentList();
  },
  computed: {
    isAllSelected() {
      return this.allDevices.length > 0 && this.selectedPermissions.length === this.allDevices.length;
    }
  },
  methods: {
    handleSearch() {
      const keyword = this.searchKeyword.toLowerCase().trim();
      if (!keyword) {
        this.filteredAgents = this.agentDeviceOptions;
        return;
      }
      // 过滤：匹配智能体名称、设备名称或MAC地址
      this.filteredAgents = this.agentDeviceOptions.filter(agent => {
        // 匹配智能体名称
        if (agent.agentName.toLowerCase().includes(keyword)) {
          return true;
        }
        // 匹配设备名称或MAC地址
        if (agent.devices && agent.devices.some(device => {
          const name = (device.name || '').toLowerCase();
          const mac = (device.deviceId || '').toLowerCase();
          return name.includes(keyword) || mac.includes(keyword);
        })) {
          return true;
        }
        return false;
      });
    },
    fetchAgentList() {
      Api.agent.getAgentList((res) => {
        const agentList = res.data?.data || [];
        if (agentList.length > 0) {
          const agentPromises = agentList.map(agent => {
            return new Promise((resolve) => {
              Api.device.getAgentBindDevices(agent.id, (deviceRes) => {
                const deviceList = deviceRes.data?.data || deviceRes.data || [];
                agent.devices = deviceList.map(device => ({
                  id: device.id,
                  name: (device.alias && device.alias.trim()) ? device.alias : device.id,
                  alias: device.alias || '',
                  addressBookAlias: '',  // 通讯录别名，初始为空
                  type: device.board,
                  deviceId: device.macAddress,
                  remarks: device.alias || '',
                  online: false,
                  createDate: device.createDate,
                  createDateTimestamp: device.createDateTimestamp,
                  lastConnectedAt: device.lastConnectedAtTimestamp,
                  deviceStatus: 'offline'
                }));
                resolve();
              });
            });
          });
          Promise.all(agentPromises).then(() => {
            const firstDevice = agentList[0] || {};
            this.agentDeviceOptions = agentList;
            this.filteredAgents = agentList;
            // 默认选中第一项
            this.handleDeviceClick(firstDevice.devices?.[0] || {}, firstDevice);
            // 获取设备状态
            this.fetchDeviceStatus();
          });
        } else {
          this.agentDeviceOptions = [];
          this.filteredAgents = [];
        }
      });
    },
    fetchDeviceStatus() {
      // 为每个智能体获取设备状态
      this.agentDeviceOptions.forEach(agent => {
        if (!agent.id) return;
        Api.device.getDeviceStatus(agent.id, (statusRes) => {
          if (statusRes.data?.code === 0) {
            try {
              const statusData = JSON.parse(statusRes.data.data);
              if (statusData && typeof statusData === 'object') {
                this.mqttServiceAvailable = true;
                this.updateDeviceStatusFromResponse(agent, statusData);
              }
            } catch (e) {
              console.error('Parse device status error:', e);
            }
          }
        });
      });
    },
    updateDeviceStatusFromResponse(agent, statusData) {
      if (!agent.devices) return;
      agent.devices.forEach(device => {
        const macAddress = device.deviceId ? device.deviceId.replace(/:/g, '_') : 'unknown';
        const groupId = device.type ? device.type.replace(/:/g, '_') : 'GID_default';
        const mqttClientId = `${groupId}@@@${macAddress}@@@${macAddress}`;

        if (statusData[mqttClientId]) {
          const statusInfo = statusData[mqttClientId];
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
          device.online = isOnline;
          device.deviceStatus = isOnline ? 'online' : 'offline';
        } else {
          device.online = false;
          device.deviceStatus = 'offline';
        }
      });
    },
    handleDeviceClick(device, agent) {
      this.expandedAgentId = agent.id;
      this.selectedAgent = agent;
      this.selectedDevice = device;
      // 加载所有设备用于权限选择（排除当前设备）
      this.allDevices = this.agentDeviceOptions
        .flatMap(agent => agent.devices || [])
        .filter(d => d.id !== device.id);
      // 加载通讯录权限
      this.loadAddressBookPermissions(device.deviceId);
    },
    loadAddressBookPermissions(macAddress) {
      AddressBookApi.getAddressBookList(macAddress, (res) => {
        if (res.data?.code === 0) {
          const permissions = res.data.data || [];
          // 设置已选择的权限
          this.selectedPermissions = permissions
            .filter(p => p.hasPermission)
            .map(p => p.targetMac);
          // 保存初始权限状态（用于对比变更）
          this.originalPermissions = [...this.selectedPermissions];
          // 更新设备的通讯录别名
          this.allDevices.forEach(device => {
            const addrBook = permissions.find(p => p.targetMac === device.deviceId);
            if (addrBook) {
              device.addressBookAlias = addrBook.alias || '';
            } else {
              device.addressBookAlias = '';
            }
          });
        }
      });
    },
    handleStartEditPermission(device) {
      this.editingDeviceId = device.id;
      this.editingDeviceName = device.addressBookAlias || device.name;
      this.$nextTick(() => {
        const input = document.querySelector('.permission-edit-input');
        if (input) input.focus();
      });
    },
    handleEditPermissionBlur(device) {
      if (!this.editingDeviceId) return;
      const newName = this.editingDeviceName.trim();
      if (newName && newName !== (device.addressBookAlias || device.name)) {
        AddressBookApi.updateAlias({
          macAddress: this.selectedDevice.deviceId,
          targetMac: device.deviceId,
          alias: newName
        }, (res) => {
          if (res.data?.code === 0) {
            this.$message.success(this.$t('addressBookManagement.aliasSaved'));
            this.loadAddressBookPermissions(this.selectedDevice.deviceId);
          } else {
            this.$message.error(res.data?.msg || this.$t('addressBookManagement.saveFailed'));
          }
        });
      }
      this.editingDeviceId = null;
      this.editingDeviceName = '';
    },
    handlePermissionToggle(deviceId, checked) {
      if (checked) {
        if (!this.selectedPermissions.includes(deviceId)) {
          this.selectedPermissions.push(deviceId);
        }
      } else {
        const index = this.selectedPermissions.indexOf(deviceId);
        if (index > -1) {
          this.selectedPermissions.splice(index, 1);
        }
      }
    },
    handleToggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedPermissions = [];
      } else {
        this.selectedPermissions = this.allDevices.map(d => d.id);
      }
    },
    handleCancel() {
      this.selectedPermissions = [];
    },
    handleSavePermissions() {
      const promises = this.allDevices
        .filter(device => {
          const isNowSelected = this.selectedPermissions.includes(device.id);
          const wasOriginallySelected = this.originalPermissions.includes(device.id);
          return isNowSelected !== wasOriginallySelected;
        })
        .map(device => {
          const hasPermission = this.selectedPermissions.includes(device.id);
          return new Promise((resolve) => {
            AddressBookApi.updatePermission({
              macAddress: this.selectedDevice.deviceId,
              targetMac: device.deviceId,
              hasPermission: hasPermission
            }, (res) => {
              resolve(res.data?.code === 0);
            });
          });
        });
      Promise.all(promises).then((results) => {
        if (promises.length === 0) {
          this.$message.info(this.$t('addressBookManagement.noChanges'));
        } else if (results.every(r => r)) {
          this.$message.success(this.$t('addressBookManagement.permissionSaved'));
          this.originalPermissions = [...this.selectedPermissions];
          this.loadAddressBookPermissions(this.selectedDevice.deviceId);
        } else {
          this.$message.error(this.$t('addressBookManagement.partialSaveFailed'));
        }
      });
    },
    handleStartEdit() {
      this.isEditingAlias = true;
      this.editAliasValue = this.selectedDevice.name;
      this.$nextTick(() => {
        if (this.$refs.aliasInput) {
          this.$refs.aliasInput.focus();
        }
      });
    },
    handleAliasBlur() {
      if (!this.selectedDevice) return;
      const newAlias = this.editAliasValue.trim();
      if (newAlias) {
        Api.device.updateDeviceInfo(this.selectedDevice.id, { alias: newAlias }, ({ data }) => {
          if (data.code === 0) {
            this.selectedDevice.name = newAlias;
            for (const agent of this.agentDeviceOptions) {
              const device = agent.devices?.find(d => d.id === this.selectedDevice.id);
              if (device) {
                device.name = newAlias;
                device.alias = newAlias;
                break;
              }
            }
            this.$message.success(this.$t('addressBookManagement.aliasSaved'));
          } else {
            this.$message.error(data.msg || this.$t('addressBookManagement.saveFailed'));
          }
        });
      }
      this.isEditingAlias = false;
    },
    handleStartEditAgentName() {
      if (!this.selectedAgent) return;
      this.isEditingAgentName = true;
      this.editAgentNameValue = this.selectedAgent.agentName;
      this.$nextTick(() => {
        if (this.$refs.agentNameInput) {
          this.$refs.agentNameInput.focus();
        }
      });
    },
    handleAgentNameBlur() {
      if (!this.selectedAgent) return;
      if (this.editAgentNameValue.trim() && this.editAgentNameValue.trim() !== this.selectedAgent.agentName) {
        const newName = this.editAgentNameValue.trim();
        Api.agent.updateAgentConfig(this.selectedAgent.id, { agentName: newName }, ({ data }) => {
          if (data.code === 0) {
            this.selectedAgent.agentName = newName;
            // 更新列表中的智能体名称
            const agentInList = this.agentDeviceOptions.find(a => a.id === this.selectedAgent.id);
            if (agentInList) {
              agentInList.agentName = newName;
            }
            this.$message.success(this.$t('addressBookManagement.agentNameUpdated'));
          } else {
            this.$message.error(data.msg || this.$t('addressBookManagement.updateFailed'));
          }
        });
      }
      this.isEditingAgentName = false;
    },
    getTimeAgo(timestamp) {
      const ts = parseTimestamp(timestamp);
      if (ts === null) return '-';
      const now = new Date();
      const date = new Date(ts);
      const diff = now - date;

      const seconds = Math.floor(diff / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);
      const days = Math.floor(hours / 24);
      const months = Math.floor(days / 30);
      const years = Math.floor(days / 365);

      if (seconds < 60) return this.$t('addressBookManagement.justNow');
      if (minutes < 60) return this.$t('addressBookManagement.minutesAgo', { minutes });
      if (hours < 24) return this.$t('addressBookManagement.hoursAgo', { hours });
      if (days < 30) return this.$t('addressBookManagement.daysAgo', { days });
      if (months < 12) return this.$t('addressBookManagement.monthsAgo', { months });
      return this.$t('addressBookManagement.yearsAgo', { years });
    },
    formatDeviceCreateDate(device) {
      if (!device) return '-';
      return formatCreateDate(device.createDateTimestamp, device.createDate);
    },
    getDeviceAvatar(deviceId) {
      // 根据 deviceId 计算 MD5，选择对应的头像
      const avatars = [
        require('@/assets/device-avatars/xiaozhi-logo1.png'),
        require('@/assets/device-avatars/xiaozhi-logo2.png'),
        require('@/assets/device-avatars/xiaozhi-logo3.png'),
        require('@/assets/device-avatars/xiaozhi-logo4.png'),
        require('@/assets/device-avatars/xiaozhi-logo5.png'),
        require('@/assets/device-avatars/xiaozhi-logo6.png'),
        require('@/assets/device-avatars/xiaozhi-logo7.png'),
        require('@/assets/device-avatars/xiaozhi-logo8.png'),
        require('@/assets/device-avatars/xiaozhi-logo9.png'),
        require('@/assets/device-avatars/xiaozhi-logo10.png'),
        require('@/assets/device-avatars/xiaozhi-logo11.png'),
        require('@/assets/device-avatars/xiaozhi-logo12.png'),
        require('@/assets/device-avatars/xiaozhi-logo13.png'),
        require('@/assets/device-avatars/xiaozhi-logo14.png'),
        require('@/assets/device-avatars/xiaozhi-logo15.png'),
        require('@/assets/device-avatars/xiaozhi-logo16.png')
      ];
      // 简单的哈希算法，根据 deviceId 分配头像
      let hash = 0;
      for (let i = 0; i < deviceId.length; i++) {
        hash = ((hash << 5) - hash) + deviceId.charCodeAt(i);
        hash = hash & hash;
      }
      const index = Math.abs(hash) % avatars.length;
      return avatars[index];
    }
  },
};
</script>

<style lang="scss" scoped>
.welcome {
  min-width: 1200px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-size: cover;
  background: #eff4ff;
  -webkit-background-size: cover;
  -o-background-size: cover;
  overflow: hidden;

  .page-content {
    display: flex;
    flex: 1;
    margin: 20px 22px 0 22px;
    gap: 8px;
    min-height: 0;
  }
}
.agent-collapse {
  flex: 1;
  padding-right: 10px;
  padding-left: 20px;
  overflow-y: auto;
  scrollbar-width: thin;
  .agent-name {
    font-size: 14px;
    font-weight: 500;
    color: #686f85;
    text-align: left;
  }
  
  .device-list {
    display: flex;
    flex-direction: column;
    margin-top: 8px;
    .device-item {
      padding: 4px 15px;
      border-radius: 6px;
      margin-bottom: 8px;
      cursor: pointer;
      transition: all 0.3s ease;
      border: 1px solid transparent;
      display: flex;
      align-items: center;
      gap: 12px;
      background: none;

      &:hover {
        background: #ebf1fe;
      }

      &.active {
        .device-name {
          color: #7297fd !important;
        }
        border-color: #b3c0fc;
        background: #ebf1fe;
      }

      .device-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        overflow: hidden;
        flex-shrink: 0;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .device-content {
        flex: 1;
        min-width: 0;
        .device-name {
          font-size: 14px;
          color: #686f85;
          text-align: left;
          line-height: 16px;
          // margin-bottom: 4px;
        }
      }


      .device-row {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .device-id {
          font-size: 12px;
          line-height: 16px;
          color: #909399;
        }

        .device-status {
          font-size: 12px;
          line-height: 16px;
          padding: 2px 8px;
          border-radius: 4px;

          &.online {
            color: #4fbe80;
          }

          &.offline {
            color: #9ea3b0;
          }
        }
      }
    }
  }
}

.left-panel {
  width: 19%;
  background: white;
  border-radius: 15px;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.right-panel {
  flex: 1;
  background: white;
  border-radius: 15px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.device-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.device-header {
  display: flex;
  align-items: stretch;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.device-left {
  display: flex;
  align-items: flex-start;
  gap: 15px;
}

.device-avatar-large {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.device-info {
  display: flex;
  flex-direction: column;
  justify-content: center;

  .device-name-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;

    .device-name-text {
      line-height: 34px;
      font-size: 24px;
      color: #3d4566;
      cursor: pointer;
    }

    .alias-input {
      height: 28px;
      font-size: 24px;
      font-weight: 600;
      color: #3d4566;
      border: 1px solid #6b8cff;
      border-radius: 4px;
      padding: 2px 8px;
      outline: none;
      width: 200px;
    }

    i {
      cursor: pointer;
      color: #6b8cff;
      font-size: 18px;

      &:hover {
        color: #a966ff;
      }
    }
  }

  .device-mac {
    font-size: 12px;
    color: #686f85;
    margin-bottom: 4px;
    text-align: left;
  }

  .device-status {
    display: flex;
    margin-top: 4px;
    font-size: 12px;
    color: #686f85;
    text-align: left;

    .online {
      margin-left: 4px;
      color: #686f85;
      display: inline-flex;
      align-items: center;
      gap: 4px;

      .status-dot {
        margin-top: -3px;
        margin-right: 4px;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #4eb36c;
      }
    }

    .offline {
      color: #999;
      display: inline-flex;
      align-items: center;
      gap: 4px;

      .status-dot {
        margin-top: -3px;
        margin-right: 4px;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #999;
      }
    }
  }
}

.device-stats {
  display: flex;
  gap: 15px;
  align-items: stretch;
  margin-left: auto;

  .stat-item {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    padding: 12px 15px;
    border-radius: 8px;
    min-width: 140px;
    border: 1px solid #eaedf4;

    i {
      font-size: 28px;
      color: #6b8cff;
      flex-shrink: 0;
    }

    .stat-content {
      text-align: left;

      .stat-label {
        font-size: 12px;
        color: #909399;
        margin-bottom: 10px;
      }

      .stat-value {
        font-size: 14px;
        color: #3d4566;
        font-weight: 500;
      }

      .stat-value-row {
        display: flex;
        align-items: center;
        gap: 8px;

        .stat-value {
          cursor: pointer;
        }

        .stat-edit-icon {
          font-size: 14px;
          color: #909399;
          cursor: pointer;
          &:hover {
            color: #6b8cff;
          }
        }
      }

      .stat-edit-input {
        font-size: 14px;
        color: #3d4566;
        font-weight: 500;
        border: 1px solid #6b8cff;
        border-radius: 4px;
        padding: 2px 6px;
        outline: none;
        background: white;
        width: 100px;
      }
    }
  }
}

.permission-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-top: 20px;
  overflow: hidden;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 15px;

    .section-title {
      text-align: left;

      h3 {
        font-size: 24px;
        font-weight: 500;
        color: #3d4566;
        margin: 0 0 10px 0;
      }

      .section-desc {
        font-size: 12px;
        color: #909399;
        margin: 0;
      }
    }

    .section-actions {
      margin-top: 4px;
      display: flex;
    }
  }
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  grid-template-rows: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.permission-item {
  padding: 12px;
  background: linear-gradient(135deg, #f8fafd 0%, #ffffff 100%);
  border-radius: 8px;
  transition: all 0.3s ease;
  border: 2px solid #eaedf4;
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;


  &.active {
    border-color: #c6d1fd;

    .permission-name {
      color: #3765f8;
    }
  }

  .permission-checkbox {
    position: absolute;
    top: 8px;
    right: 8px;

    ::v-deep(.el-checkbox__inner) {
      width: 16px;
      height: 16px;
      border-radius: 4px;
      border-color: #dcdfe6;
      background-color: #ffffff;

      &::after {
        width: 4px;
        height: 8px;
        left: 5px;
        top: 2px;
      }
    }

    ::v-deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
      background-color: #3765f8;
      border-color: #3765f8;
    }

    ::v-deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
      color: #3765f8;
    }
  }

  .permission-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .permission-content {
    flex: 1;
    min-width: 0;
    text-align: left;

    .permission-name {
      font-size: 14px;
      color: #3d4566;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .permission-name-row {
      line-height: 22px;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .permission-name {
        flex: 1;
        margin-bottom: 0;
      }

      .permission-edit-btn {
        margin-right: 24px;
        font-size: 14px;
        color: #909399;
        cursor: pointer;
        flex-shrink: 0;
        &:hover {
          color: #6b8cff;
        }
      }
    }

    .permission-id {
      font-size: 12px;
      color: #909399;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 6px;
    }

    .permission-status {
      font-size: 12px;

      &.online {
        color: #67c23a;
      }

      &.offline {
        color: #909399;
      }
    }
  }
}

.permission-edit-input {
  font-size: 14px;
  color: #3d4566;
  border: 1px solid #6b8cff;
  border-radius: 4px;
  padding: 2px 6px;
  outline: none;
  width: calc(100% - 40px);
}

.left-header {
  margin-bottom: 20px;
  text-align: left;
  padding: 0 20px;
}

.main-title {
  font-size: 24px;
  font-weight: 500;
  color: #3d4566;
  margin: 0 0 8px 0;
}

.sub-title {
  font-size: 14px;
  color: #a6aebe;
  margin: 0;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  padding: 0 20px;
}

.agent-triangle {
  margin-right: 8px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
}

.agent-card {
  width: 100%;
  padding: 12px 0px;
  // background: #f5f7fa;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  box-sizing: border-box;

  &:hover {
    background: #e6f0ff;
  }

  &.active, &.expanded {
    border-color: #6b8cff;
    background: #e6f0ff;
  }

  .agent-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #686f85;
    transition: transform 0.3s ease;

    i {
      font-size: 14px;
    }
  }

  &.expanded .agent-icon {
    transform: rotate(90deg);
  }

  .agent-info {
    flex: 1;

    .agent-name {
      font-size: 14px;
      font-weight: 600;
      color: #3d4566;
      text-align: left;
    }

    .device-count {
      font-weight: normal;
      color: #909399;
    }
  }
}

.right-panel {
  width: 75%;
  background: white;
  border-radius: 15px;
  padding: 20px;
}

.detail-form {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 20px;

  .el-button--primary {
    background: linear-gradient(135deg, #6b8cff, #a966ff);
    border: none;
    width: 120px;
  }
}

.empty-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;

  .empty-icon {
    font-size: 60px;
    margin-bottom: 20px;
  }

  p {
    font-size: 16px;
  }
}

::v-deep(.el-input__inner) {
  height: 36px;
  border-radius: 6px;
}

::v-deep(.el-textarea__inner) {
  border-radius: 4px;
}
::v-deep(.el-collapse) {
  border: none !important;
}
::v-deep(.el-collapse-item__header) {
  border: none !important;
}
::v-deep(.el-collapse-item__wrap) {
  border: none !important;
}
::v-deep(.el-collapse-item__content) {
  padding-bottom: 0 !important;
}
::v-deep(.el-empty) {
  height: 100%;
}
</style>
