<template>
  <div class="welcome">
    <!-- Common header -->
    <HeaderBar :devices="devices" @search="handleSearch" @search-reset="handleSearchReset" />
    <el-main style="padding: 20px;display: flex;flex-direction: column;">
      <div>
        <!-- Home page content -->
        <div class="add-device">
          <div class="add-device-bg">
            <div class="hellow-text" style="padding-top: 30px;">
              {{ $t('home.greeting') }}
            </div>
            <div class="hellow-text">
              {{ $t('home.wish') }}
            </div>
            <div class="hi-hint">
              let's have a wonderful day!
            </div>
            <div class="add-device-options">
            <div class="search-container">
              <div class="search-wrapper">
                  <el-input
                    v-model="search"
                    :placeholder="$t('header.searchPlaceholder')"
                    class="custom-search-input"
                    @keyup.enter.native="handleSearch"
                    @clear="handleSearchReset"
                    clearable
                    ref="searchInput"
                    @focus="showSearchHistory"
                    @blur="hideSearchHistory"
                  >
                    <i slot="suffix" class="el-icon-search search-icon" @click="handleSearch"></i>
                  </el-input>
                  <!-- Search history dropdown -->
                  <div v-if="showHistory && searchHistory.length > 0" class="search-history-dropdown">
                    <div class="search-history-header">
                      <span>{{ $t("header.searchHistory") }}</span>
                      <el-button type="text" size="small" class="clear-history-btn" @click="clearSearchHistory">
                        {{ $t("header.clearHistory") }}
                      </el-button>
                    </div>
                    <div class="search-history-list">
                      <div v-for="(item, index) in searchHistory" :key="index" class="search-history-item"
                        @click.stop="selectSearchHistory(item)">
                        <span class="history-text">{{ item }}</span>
                        <i class="el-icon-close clear-item-icon" @click.stop="removeSearchHistory(index)"></i>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <el-button icon="el-icon-plus" class="add-device-btn" @click="showAddDialog">{{ $t('home.addAgent') }}</el-button>
            </div>
          </div>
        </div>
        <div class="device-list-container">
          <template v-if="isLoading">
            <div v-for="i in skeletonCount" :key="'skeleton-' + i" class="skeleton-item">
              <div class="skeleton-image"></div>
              <div class="skeleton-content">
                <div class="skeleton-line"></div>
                <div class="skeleton-line-short"></div>
              </div>
            </div>
          </template>

          <template v-else>
            <DeviceItem v-for="(item, index) in devices" :key="index" :device="item" @configure="goToRoleConfig"
              @deviceManage="handleDeviceManage" @delete="handleDeleteAgent" @chat-history="handleShowChatHistory" />
          </template>
        </div>
      </div>
      <AddWisdomBodyDialog :visible.sync="addDeviceDialogVisible" @confirm="handleWisdomBodyAdded" />
      <el-dialog
        :visible.sync="deleteAgentDialogVisible"
        :close-on-click-modal="!isDeletingAgent"
        :close-on-press-escape="!isDeletingAgent"
        :show-close="!isDeletingAgent"
        width="520px"
        append-to-body
        class="delete-agent-dialog"
        @closed="resetDeleteAgentDialog"
      >
        <template slot="title">
          <div class="delete-agent-title">
            <img src="@/assets/knowledge-base/level.png" class="delete-agent-title-icon" />
            <span>{{ $t('home.deleteConfirmTitle') }}</span>
          </div>
        </template>
        <div class="delete-agent-content">
          <i class="el-icon-warning-outline delete-agent-warning"></i>
          <div class="delete-agent-message">
            <div class="delete-agent-copy-guard" @copy.prevent @cut.prevent @contextmenu.prevent>
              {{ $t('home.confirmDeleteAgent', { agentName: deleteTargetAgentName }) }}
            </div>
            <div class="delete-agent-target delete-agent-copy-guard" @copy.prevent @cut.prevent @contextmenu.prevent>
              {{ deleteTargetAgentName }}
            </div>
            <el-input
              ref="deleteAgentConfirmInput"
              v-model="deleteAgentConfirmText"
              class="delete-agent-input"
              :placeholder="$t('home.deleteAgentNamePlaceholder')"
              clearable
              @paste.native.prevent="handleDeleteAgentPaste"
              @drop.native.prevent="handleDeleteAgentPaste"
              @contextmenu.native.prevent
              @keyup.enter.native="confirmDeleteAgent"
            />
            <div v-if="deleteAgentConfirmText && !isDeleteAgentNameMatched" class="delete-agent-helper">
              {{ $t('home.deleteAgentNameMismatch') }}
            </div>
          </div>
        </div>
        <span slot="footer" class="delete-agent-footer">
          <el-button class="delete-agent-cancel" :disabled="isDeletingAgent" @click="closeDeleteAgentDialog">{{ $t('button.cancel') }}</el-button>
          <el-button
            class="delete-agent-confirm"
            type="primary"
            :loading="isDeletingAgent"
            :disabled="!isDeleteAgentNameMatched"
            @click="confirmDeleteAgent"
          >
            {{ $t('button.ok') }}
          </el-button>
        </span>
      </el-dialog>
    </el-main>
    <el-footer>
      <version-footer />
    </el-footer>
    <chat-history-dialog :visible.sync="showChatHistory" :agent-id="currentAgentId" :agent-name="currentAgentName" />
  </div>

</template>

<script>
import Api from '@/apis/api';
import { mapState } from "vuex";
import AddWisdomBodyDialog from '@/components/AddWisdomBodyDialog.vue';
import ChatHistoryDialog from '@/components/ChatHistoryDialog.vue';
import DeviceItem from '@/components/DeviceItem.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import VersionFooter from '@/components/VersionFooter.vue';

export default {
  name: 'HomePage',
  components: { DeviceItem, AddWisdomBodyDialog, HeaderBar, VersionFooter, ChatHistoryDialog },
  data() {
    return {
      addDeviceDialogVisible: false,
      devices: [],
      originalDevices: [],
      isSearching: false,
      searchRegex: null,
      isLoading: true,
      skeletonCount: localStorage.getItem('skeletonCount') || 8,
      showChatHistory: false,
      currentAgentId: '',
      currentAgentName: ''
    }
  },

  mounted() {
    this.fetchAgentList();
  },

  methods: {
    showAddDialog() {
      this.addDeviceDialogVisible = true
    },
    goToRoleConfig() {
      // Navigate to role configuration page after clicking configure role
      this.$router.push('/role-config')
    },
    handleWisdomBodyAdded(res) {
      this.fetchAgentList();
      this.addDeviceDialogVisible = false;
    },
    handleDeviceManage() {
      this.$router.push('/device-management');
    },
    handleSearchReset() {
      this.isSearching = false;
      this.searchRegex = null;
      this.devices = [...this.originalDevices];
    },
    applySearchFilter() {
      if (!this.isSearching || !this.searchRegex) {
        this.devices = [...this.originalDevices];
        return;
      }

      this.devices = this.originalDevices.filter(device => {
        return this.searchRegex.test(device.agentName);
      });
    },
    // Search and update agent list
    handleSearchResult(filteredList) {
      this.devices = filteredList; // Update device list
    },
    // Get agent list
    fetchAgentList() {
      this.isLoading = true;
      Api.agent.getAgentList(({ data }) => {
        if (data?.data) {
          this.originalDevices = data.data.map(item => ({
            ...item,
            agentId: item.id
          }));

          // Dynamically set skeleton screen count (optional)
          this.skeletonCount = Math.min(
            Math.max(this.originalDevices.length, 3), // Minimum 3
            10 // Maximum 10
          );

          this.handleSearchReset();
        }
        this.isLoading = false;
      }, (error) => {
        console.error('Failed to fetch agent list:', error);
        this.isLoading = false;
      });
    },
    // Delete agent
    handleDeleteAgent(agentId) {
      this.$confirm(this.$t('home.confirmDeleteAgent'), 'Prompt', {
        confirmButtonText: this.$t('button.ok'),
        cancelButtonText: this.$t('button.cancel'),
        type: 'warning'
      }).then(() => {
        Api.agent.deleteAgent(agentId, (res) => {
          if (res.data.code === 0) {
            this.$message.success({
              message: this.$t('home.deleteSuccess'),
              showClose: true
            });
            this.fetchAgentList(); // Refresh list
          } else {
            this.$message.error({
              message: res.data.msg || this.$t('home.deleteFailed'),
              showClose: true
            });
          }
        });
      }).catch(() => { });
    },
    handleShowChatHistory({ agentId, agentName }) {
      this.currentAgentId = agentId;
      this.currentAgentName = agentName;
      this.showChatHistory = true;
    },
    // Handle search
    handleSearch() {
      const searchValue = this.search.trim();

      // If search content is empty, trigger reset event
      if (!searchValue) {
        this.handleSearchReset();
        return;
      }

      // Save search history
      this.saveSearchHistory(searchValue);

      // Blur the input field after search completion to trigger the blur event and hide search history
      if (this.$refs.searchInput) {
        this.$refs.searchInput.blur();
      }

      this.isSearching = true;
      this.isLoading = true;
      // Detect MAC address format: contains 4 colons
      const isMac = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(searchValue)
      const searchType = isMac ? 'mac' : 'name';
      Api.agent.searchAgent(searchValue, searchType, ({ data }) => {
        if (data?.data) {
          this.devices = data.data.map(item => ({
            ...item,
            agentId: item.id
          }));
        }
        this.isLoading = false;
      }, (error) => {
        console.error('Failed to search agents:', error);
        this.isLoading = false;
        this.$message.error(this.$t('message.searchFailed'));
      });
    },

    // Show search history
    showSearchHistory() {
      this.showHistory = true;
    },

    // Hide search history
    hideSearchHistory() {
      // Delay hiding to allow click events to execute
      setTimeout(() => {
        this.showHistory = false;
      }, 200);
    },

    // Load search history
    loadSearchHistory() {
      try {
        const history = localStorage.getItem(this.SEARCH_HISTORY_KEY);
        if (history) {
          this.searchHistory = JSON.parse(history);
        }
      } catch (error) {
        console.error("Failed to load search history:", error);
        this.searchHistory = [];
      }
    },

    // Save search history
    saveSearchHistory(keyword) {
      if (!keyword || this.searchHistory.includes(keyword)) {
        return;
      }

      // Add to beginning of history
      this.searchHistory.unshift(keyword);

      // Limit history record count
      if (this.searchHistory.length > this.MAX_HISTORY_COUNT) {
        this.searchHistory = this.searchHistory.slice(0, this.MAX_HISTORY_COUNT);
      }

      // Save to localStorage
      try {
        localStorage.setItem(this.SEARCH_HISTORY_KEY, JSON.stringify(this.searchHistory));
      } catch (error) {
        console.error("Failed to save search history:", error);
      }
    },

    // Select search history item
    selectSearchHistory(keyword) {
      this.search = keyword;
      this.handleSearch();
    },

    // Remove single search history item
    removeSearchHistory(index) {
      this.searchHistory.splice(index, 1);
      try {
        localStorage.setItem(this.SEARCH_HISTORY_KEY, JSON.stringify(this.searchHistory));
      } catch (error) {
        console.error("Failed to update search history:", error);
      }
    },

    // Clear all search history
    clearSearchHistory() {
      this.searchHistory = [];
      try {
        localStorage.removeItem(this.SEARCH_HISTORY_KEY);
      } catch (error) {
        console.error("Failed to clear search history:", error);
      }
    },
  }
}
</script>

<style scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #eff4ff;
  background-size: cover;
  /* Ensure background image covers the entire element */
  background-position: center;
  /* Align from top center */
  -webkit-background-size: cover;
  /* Compatible with older WebKit browsers */
  -o-background-size: cover;
  /* Compatible with older Opera browsers */
}

.add-device {
  height: 195px;
  border-radius: 15px;
  position: relative;
  background: linear-gradient(269.62deg,
      #e0e6fd 0%,
      #cce7ff 49.69%,
      #d3d3fe 100%);
}

.add-device-bg {
  width: 100%;
  height: 100%;
  text-align: left;
  background-image: url("@/assets/home/main-top-bg.png");
  background-size: cover;
  /* Ensure background image covers the entire element */
  background-position: center;
  /* Align from top center */
  -webkit-background-size: cover;
  /* Compatible with older WebKit browsers */
  -o-background-size: cover;
  box-sizing: border-box;

  /* Compatible with older Opera browsers */
  .hellow-text {
    margin-left: 75px;
    color: #3d4566;
    font-size: 33px;
    font-weight: 700;
    letter-spacing: 0;
  }

  .hi-hint {
    font-weight: 400;
    font-size: 12px;
    text-align: left;
    color: #818cae;
    margin-left: 75px;
    margin-top: 5px;
  }
}
.add-device-options {
  display: flex;
  margin-top: 16px;
  margin-left: 75px;
  align-items: center;
}

.add-device-btn {
  color: #fff;
  margin-left: 10px;
  background: #3375fd;
  border-radius: 20px;
}

.search-container {
  width: 360px;
  margin-right: 5px;
}

.search-wrapper {
  position: relative;
}

.custom-search-input {
  &::v-deep .el-input__inner {
    border-radius: 20px;
    border: 1px solid transparent;
    box-shadow: 0 2px 2px 0 #cfe1fb;
  }
  &::v-deep .el-input__suffix {
    right: 10px;
  }
  &::v-deep .el-input__suffix-inner {
    display: flex;
    align-items: center;
    height: 100%;
    cursor: pointer;
  }
  .search-icon {
    font-size: 14px;
  }
}

.search-wrapper {
  position: relative;
}

.search-history-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e4e6ef;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 1000;
  margin-top: 2px;
}

.search-history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
  color: #909399;
}

.clear-history-btn {
  color: #909399;
  font-size: 11px;
  padding: 0;
  height: auto;
}

.clear-history-btn:hover {
  color: #606266;
}

.search-history-list {
  max-height: 200px;
  overflow-y: auto;
}

.search-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 12px;
  color: #606266;
}

.search-history-item:hover {
  background-color: #f5f7fa;
}

.search-wrapper {
  position: relative;
}

.search-history-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e4e6ef;
  border-radius: 10px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 1000;
  margin-top: 6px;
}

.clear-history-btn {
  color: #909399;
  font-size: 12px;
  padding: 0;
  height: auto;
}

.clear-history-btn:hover {
  color: #606266;
}

.search-history-list {
  max-height: 200px;
  overflow-y: auto;
}

.search-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 12px;
  color: #606266;
}

.search-history-item:hover {
  background-color: #f5f7fa;
}

.search-history-item:hover .clear-item-icon {
  visibility: visible;
}

.clear-item-icon:hover {
  color: #ff4949;
}

.clear-item-icon {
  font-size: 10px;
  color: #909399;
  visibility: hidden;
}

.device-list-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 30px;
  padding: 30px 0;
}

/* In DeviceItem.vue styles */
.device-item {
  margin: 0 !important;
  /* Avoid conflicts */
  width: auto !important;
}

.footer {
  font-size: 12px;
  font-weight: 400;
  margin-top: auto;
  padding-top: 30px;
  color: #979db1;
  text-align: center;
  /* Center display */
}

/* Skeleton screen animation */
@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}

.skeleton-item {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  height: 120px;
  position: relative;
  overflow: hidden;
  margin-bottom: 20px;
}

.skeleton-image {
  width: 80px;
  height: 80px;
  background: #f0f2f5;
  border-radius: 4px;
  float: left;
  position: relative;
  overflow: hidden;
}

.skeleton-content {
  margin-left: 100px;
}

.skeleton-line {
  height: 16px;
  background: #f0f2f5;
  border-radius: 4px;
  margin-bottom: 12px;
  width: 70%;
  position: relative;
  overflow: hidden;
}

.skeleton-line-short {
  height: 12px;
  background: #f0f2f5;
  border-radius: 4px;
  width: 50%;
}

.skeleton-item::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg,
      rgba(255, 255, 255, 0),
      rgba(255, 255, 255, 0.3),
      rgba(255, 255, 255, 0));
  animation: shimmer 1.5s infinite;
}

.delete-agent-content {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.delete-agent-title {
  display: inline-flex;
  align-items: center;
  font-size: 18px;
  font-weight: 500;
  color: #2f3a5f;
}

.delete-agent-title-icon {
  width: 24px;
  height: 24px;
  margin-right: 8px;
}

.delete-agent-warning {
  color: #e6a23c;
  font-size: 24px;
  margin-top: 4px;
}

.delete-agent-message {
  flex: 1;
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

.delete-agent-target {
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #f5f7fa;
  color: #303133;
  font-weight: 600;
  word-break: break-all;
}

.delete-agent-copy-guard {
  user-select: none;
  -webkit-user-select: none;
}

.delete-agent-input {
  margin-top: 16px;
}

.delete-agent-input::v-deep .el-input__inner {
  height: 42px;
  border-color: #d8dce8;
  border-radius: 4px;
  background: #fff;
  color: #303133;
  font-size: 14px;
}

.delete-agent-helper {
  min-height: 18px;
  margin-top: 6px;
  color: #f56c6c;
  font-size: 12px;
}

.delete-agent-footer {
  display: inline-flex;
  gap: 10px;
}

.delete-agent-dialog::v-deep .el-dialog {
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.delete-agent-dialog::v-deep .el-dialog__header {
  padding: 16px 20px 12px;
  background: linear-gradient(135deg, #e2eeff, #edeafe);
  text-align: left;
}

.delete-agent-dialog::v-deep .el-dialog__headerbtn {
  top: 12px;
  right: 16px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-agent-dialog::v-deep .el-dialog__headerbtn .el-dialog__close {
  font-size: 18px;
  color: #666;
  position: static;
  transform: none;
}

.delete-agent-dialog::v-deep .el-dialog__headerbtn:hover {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
}

.delete-agent-dialog::v-deep .el-dialog__headerbtn:hover .el-dialog__close {
  color: #333;
}

.delete-agent-dialog::v-deep .el-dialog__body {
  padding: 28px 32px 20px;
}

.delete-agent-dialog::v-deep .el-dialog__footer {
  padding: 12px 32px 24px;
}

.delete-agent-cancel,
.delete-agent-confirm {
  min-width: 92px;
  height: 40px;
  padding: 0 20px;
  border-radius: 6px;
  font-size: 15px;
}

.delete-agent-cancel {
  color: #fff;
  background: #4d94f7;
  border: none;
}

.delete-agent-cancel:hover,
.delete-agent-cancel:focus {
  color: #fff;
  background: #4d94f7;
  opacity: 0.88;
}

.delete-agent-confirm {
  background: linear-gradient(to right, #4a7cfd, #8154fc);
  border: none;
}

.delete-agent-confirm:hover,
.delete-agent-confirm:focus {
  background: linear-gradient(to right, #4a7cfd, #8154fc);
  opacity: 0.88;
}

.delete-agent-confirm.is-disabled,
.delete-agent-confirm.is-disabled:hover,
.delete-agent-confirm.is-disabled:focus {
  background: linear-gradient(to right, #4a7cfd, #8154fc);
  border: none;
  opacity: 0.45;
}
</style>
