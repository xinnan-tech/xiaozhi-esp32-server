<template>
  <div class="welcome">
    <!-- 公共头部 -->
    <HeaderBar :devices="devices" @search="handleSearch" @search-reset="handleSearchReset" />
    <el-main style="padding: 20px;display: flex;flex-direction: column;">
      <div>
        <!-- 首页内容 -->
        <div class="add-device">
          <div class="add-device-bg">
            <div class="hellow-text" style="margin-top: 30px;">
              Hello, Cheeko
            </div>
            <div class="hellow-text">
              Let's have a
              <div style="display: inline-block;color: #5778FF;">
                wonderful day!
              </div>
            </div>
            <div class="hi-hint">
              Hello, Let's have a wonderful day!
            </div>
            <div class="add-device-btn">
              <div class="left-add" @click="showAddDialog">
                Add Agent
              </div>
              <div style="width: 23px;height: 13px;background: #5778ff;margin-left: -10px;" />
              <div class="right-add">
                <i class="el-icon-right" @click="showAddDialog" style="font-size: 20px;color: #fff;" />
              </div>
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
    </el-main>
    <el-footer>
      <version-footer />
    </el-footer>
    <chat-history-dialog :visible.sync="showChatHistory" :agent-id="currentAgentId" :agent-name="currentAgentName" />
  </div>

</template>

<script>
import Api from '@/apis/api';
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
      currentAgentName: '',
      userCache: {} // 缓存用户信息，避免重复请求
    }
  },

  mounted() {
    console.log('Home component mounted, fetching agent list'); // Debug log
    this.fetchAgentList();
  },

  activated() {
    // This runs when component is activated (useful if using keep-alive)
    console.log('Home component activated, fetching agent list'); // Debug log
    this.fetchAgentList();
  },

  created() {
    console.log('Home component created'); // Debug log
  },

  watch: {
    '$route'(to, from) {
      // Watch for route changes - refetch data when navigating back to home
      console.log('Route changed:', from.path, '->', to.path); // Debug log
      if (to.name === 'home' || to.path === '/home') {
        console.log('Navigated back to home, refetching agent list'); // Debug log
        this.$nextTick(() => {
          this.fetchAgentList();
        });
      }
    }
  },

  methods: {
    showAddDialog() {
      this.addDeviceDialogVisible = true
    },
    goToRoleConfig() {
      // 点击配置角色后跳转到角色配置页
      this.$router.push('/role-config')
    },
    handleWisdomBodyAdded(res) {
      this.fetchAgentList();
      this.addDeviceDialogVisible = false;
    },
    handleDeviceManage() {
      this.$router.push('/device-management');
    },
    handleSearch(regex) {
      this.isSearching = true;
      this.searchRegex = regex;
      this.applySearchFilter();
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
    // 搜索更新智能体列表
    handleSearchResult(filteredList) {
      this.devices = filteredList; // 更新设备列表
    },
    // 获取智能体列表
    fetchAgentList() {
      this.isLoading = true;
      console.log('Starting to fetch agent list...'); // Debug log

      // 根据用户角色决定使用哪个API
      const isAdmin = this.$store.getters.getIsSuperAdmin;
      console.log('User is admin:', isAdmin); // Debug log

      if (isAdmin) {
        // 管理员：获取所有智能体
        console.log('Fetching admin agent list...'); // Debug log
        Api.agent.getAgentList((response) => {
          console.log('Admin API response received:', response); // Debug log
          // Extract response.data to match expected structure
          this.handleAgentListResponse(response.data);
        }, (error) => {
          console.error('Failed to fetch admin agent list:', error);
          this.$message.error('Failed to load agent list. Please check your connection and try again.');
          this.isLoading = false;
        });
      } else {
        // 普通用户：只获取自己的智能体
        console.log('Fetching user agent list...'); // Debug log
        Api.agent.getUserAgentList((response) => {
          console.log('User API response received:', response); // Debug log
          // Extract response.data to match expected structure
          this.handleAgentListResponse(response.data);
        }, (error) => {
          console.error('Failed to fetch user agent list:', error);
          this.$message.error('Failed to load your agents. Please check your connection and try again.');
          this.isLoading = false;
        });
      }
    },

    // 处理智能体列表响应
    handleAgentListResponse(data) {
      console.log('Raw API Response:', data); // Debug log
      
      if (data) {
        // The parameter 'data' is already response.data from the API call
        let agentList = [];
        
        // The API response structure is nested: response.data.data.list
        if (data.data && data.data.list && Array.isArray(data.data.list)) {
          // For admin API: data.data.list (nested structure)
          agentList = data.data.list;
          console.log('Using data.data.list structure'); // Debug log
        } else if (data.list && Array.isArray(data.list)) {
          // For fallback: data.list
          agentList = data.list;
          console.log('Using data.list structure'); // Debug log
        } else if (Array.isArray(data.data)) {
          // For user API: data.data (direct array)
          agentList = data.data;
          console.log('Using data.data array structure'); // Debug log
        } else if (Array.isArray(data)) {
          // For direct array: data
          agentList = data;
          console.log('Using direct array structure'); // Debug log
        } else {
          console.error('Unexpected API response structure:', data);
          console.error('Available keys in data:', Object.keys(data || {})); // Debug log
          this.$message.error('Failed to load agent list: Invalid response format');
          this.isLoading = false;
          return;
        }

        console.log('Agent list before processing:', agentList); // Debug log

        // 处理agent数据并获取模型名称
        this.processAgentListWithModelNames(agentList);

        console.log('Final processed devices:', this.originalDevices); // Debug log

        // 动态设置骨架屏数量（可选）
        this.skeletonCount = Math.min(
          Math.max(this.originalDevices.length, 3), // 最少3个
          10 // 最多10个
        );

        this.handleSearchReset();
      } else {
        console.error('No data in API response:', data);
        this.$message.error('Failed to load agent list: No data received');
      }
      this.isLoading = false;
    },
    // Delete agent
    handleDeleteAgent(agentId) {
      this.$confirm('Are you sure you want to delete this agent?', 'Confirm', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(() => {
        Api.agent.deleteAgent(agentId, (res) => {
          if (res.data.code === 0) {
            this.$message.success({
              message: 'Deleted successfully',
              showClose: true
            });
            this.fetchAgentList(); // Refresh list
          } else {
            this.$message.error({
              message: res.data.msg || 'Failed to delete',
              showClose: true
            });
          }
        });
      }).catch(() => { });
    },

    // 处理agent列表并获取模型名称
    async processAgentListWithModelNames(agentList) {
      // 首先创建基本的设备列表
      const basicDevices = agentList
        .filter(item => item && (item.id || item.agentId))
        .map(item => ({
          ...item,
          agentId: item.agentId || item.id,
          agentName: item.agentName || item.name || 'Unknown Agent',
          // 暂时使用模型ID，稍后会被替换为模型名称
          llmModelName: item.llmModelId || 'Not configured',
          ttsModelName: item.ttsModelId || 'Not configured', 
          ttsVoiceName: item.ttsVoiceId || 'Default',
          deviceCount: item.deviceCount || 0,
          memModelId: item.memModelId || 'Memory_nomem',
          lastConnectedAt: item.lastConnectedAt || null,
          systemPrompt: item.systemPrompt || 'No system prompt configured',
          ownerUsername: item.ownerUsername || null,
          // 保留原始ID用于获取模型名称
          originalLlmModelId: item.llmModelId,
          originalTtsModelId: item.ttsModelId,
          originalTtsVoiceId: item.ttsVoiceId
        }));

      console.log('Basic devices processed:', basicDevices); // Debug log

      // 设置基本数据先显示
      this.originalDevices = basicDevices;
      this.handleSearchReset();

      // 异步获取模型名称、设备数量和用户信息
      this.fetchModelNamesForDevices();
      this.fetchDeviceCountsForAgents();
      this.fetchOwnerNamesForAgents();
    },

    // 获取所有设备的模型名称
    fetchModelNamesForDevices() {
      const uniqueLlmModels = [...new Set(this.originalDevices.map(d => d.originalLlmModelId).filter(Boolean))];
      const uniqueTtsModels = [...new Set(this.originalDevices.map(d => d.originalTtsModelId).filter(Boolean))];
      const uniqueVoiceIds = [...new Set(this.originalDevices.map(d => d.originalTtsVoiceId).filter(Boolean))];

      console.log('Fetching names for:', { uniqueLlmModels, uniqueTtsModels, uniqueVoiceIds });

      // 获取LLM模型名称
      uniqueLlmModels.forEach(modelId => {
        Api.model.getModelConfig(modelId, (response) => {
          console.log(`LLM Model response for ${modelId}:`, response);
          if (response.data && response.data.code === 0) {
            const modelName = response.data.data?.modelName || modelId;
            this.updateDeviceModelName('llmModelName', modelId, modelName);
          }
        });
      });

      // 获取TTS模型名称
      uniqueTtsModels.forEach(modelId => {
        Api.model.getModelConfig(modelId, (response) => {
          console.log(`TTS Model response for ${modelId}:`, response);
          if (response.data && response.data.code === 0) {
            const modelName = response.data.data?.modelName || modelId;
            this.updateDeviceModelName('ttsModelName', modelId, modelName);
          }
        });
      });

      // 获取TTS声音名称 (暂时跳过自定义语音，只显示ID)
      console.log('Voice IDs will be displayed as-is for now');
    },

    // 更新设备的模型名称
    updateDeviceModelName(field, originalId, newName) {
      const fieldMapping = {
        'llmModelName': 'originalLlmModelId',
        'ttsModelName': 'originalTtsModelId', 
        'ttsVoiceName': 'originalTtsVoiceId'
      };

      this.originalDevices = this.originalDevices.map(device => {
        if (device[fieldMapping[field]] === originalId) {
          return { ...device, [field]: newName };
        }
        return device;
      });

      // 如果当前显示的是搜索结果，也要更新搜索结果
      this.devices = this.devices.map(device => {
        if (device[fieldMapping[field]] === originalId) {
          return { ...device, [field]: newName };
        }
        return device;
      });

      console.log(`Updated ${field} for ${originalId} to: ${newName}`);
    },

    // 获取所有智能体的设备数量
    fetchDeviceCountsForAgents() {
      console.log('Fetching device counts for agents...');
      
      this.originalDevices.forEach(device => {
        if (device.agentId) {
          Api.device.getAgentBindDevices(device.agentId, (response) => {
            console.log(`Device response for agent ${device.agentId}:`, response);
            
            if (response.data && response.data.code === 0) {
              const devices = response.data.data || [];
              const deviceCount = Array.isArray(devices) ? devices.length : 0;
              
              // 更新设备数量
              this.updateDeviceInfo(device.agentId, 'deviceCount', deviceCount);
              console.log(`Updated device count for ${device.agentName}: ${deviceCount}`);
            }
          });
        }
      });
    },

    // 获取智能体所有者姓名
    fetchOwnerNamesForAgents() {
      console.log('Fetching owner names for agents...');
      
      const isAdmin = this.$store.getters.getIsSuperAdmin;
      
      if (isAdmin) {
        // 管理员：需要获取每个用户的真实姓名
        const uniqueUserIds = [...new Set(this.originalDevices.map(d => d.userId).filter(Boolean))];
        console.log('Unique user IDs to fetch:', uniqueUserIds);
        
        uniqueUserIds.forEach(userId => {
          // 检查缓存
          if (this.userCache[userId] && this.userCache[userId] !== `User ${userId}`) {
            console.log(`Using cached user info for ${userId}:`, this.userCache[userId]);
            this.updateOwnerNameForUserId(userId, this.userCache[userId]);
            return;
          }
          
          // 从API获取用户信息
          console.log(`Fetching user info for ${userId} via API...`);
          Api.admin.getUserById(userId, (response) => {
            console.log(`User info response for ${userId}:`, response);
            
            if (response.data && response.data.code === 0) {
              const userData = response.data.data;
              console.log(`Raw user data for ${userId}:`, userData);
              const username = userData.mobile || userData.username || userData.email || userData.name || `User ${userId}`;
              
              // 缓存用户信息
              this.userCache[userId] = username;
              
              // 更新显示
              this.updateOwnerNameForUserId(userId, username);
              
              console.log(`Successfully updated owner name for userId ${userId}: ${username}`);
            } else {
              console.error(`Failed to get user info for ${userId}:`, response);
              console.error('API response details:', response.data);
              // 如果获取失败，显示默认名称
              const fallbackName = `User ${userId}`;
              this.userCache[userId] = fallbackName;
              this.updateOwnerNameForUserId(userId, fallbackName);
              console.log(`Using fallback name for userId ${userId}: ${fallbackName}`);
            }
          });
        });
      } else {
        // 普通用户：获取当前用户信息
        Api.user.getUserInfo((response) => {
          console.log('Current user info:', response);
          
          if (response.data && response.data.code === 0) {
            const currentUser = response.data.data;
            const currentUsername = currentUser.username || currentUser.mobile || currentUser.email || 'Current User';
            
            // 所有智能体都是自己的
            this.originalDevices.forEach(device => {
              this.updateDeviceInfo(device.agentId, 'ownerUsername', currentUsername);
            });
          }
        });
      }
    },

    // 根据userId更新所有者姓名
    updateOwnerNameForUserId(userId, username) {
      this.originalDevices.forEach(device => {
        if (device.userId === userId) {
          this.updateDeviceInfo(device.agentId, 'ownerUsername', username);
        }
      });
    },

    // 更新设备信息（通用方法）
    updateDeviceInfo(agentId, field, value) {
      this.originalDevices = this.originalDevices.map(device => {
        if (device.agentId === agentId) {
          return { ...device, [field]: value };
        }
        return device;
      });

      // 同时更新搜索结果
      this.devices = this.devices.map(device => {
        if (device.agentId === agentId) {
          return { ...device, [field]: value };
        }
        return device;
      });
    },

    handleShowChatHistory({ agentId, agentName }) {
      this.currentAgentId = agentId;
      this.currentAgentName = agentName;
      this.showChatHistory = true;
    }
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
  background: linear-gradient(145deg, #e6eeff, #eff0ff);
  background-size: cover;
  /* 确保背景图像覆盖整个元素 */
  background-position: center;
  /* 从顶部中心对齐 */
  -webkit-background-size: cover;
  /* 兼容老版本WebKit浏览器 */
  -o-background-size: cover;
  /* 兼容老版本Opera浏览器 */
}

.add-device {
  height: 195px;
  border-radius: 15px;
  position: relative;
  overflow: hidden;
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
  overflow: hidden;
  background-size: cover;
  /* 确保背景图像覆盖整个元素 */
  background-position: center;
  /* 从顶部中心对齐 */
  -webkit-background-size: cover;
  /* 兼容老版本WebKit浏览器 */
  -o-background-size: cover;
  box-sizing: border-box;

  /* 兼容老版本Opera浏览器 */
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

.add-device-btn {
  display: flex;
  align-items: center;
  margin-left: 75px;
  margin-top: 15px;
  cursor: pointer;

  .left-add {
    width: 105px;
    height: 34px;
    border-radius: 17px;
    background: #5778ff;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    line-height: 34px;
  }

  .right-add {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #5778ff;
    margin-left: -6px;
    display: flex;
    justify-content: center;
    align-items: center;
  }
}

.device-list-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 30px;
  padding: 30px 0;
}

/* 在 DeviceItem.vue 的样式中 */
.device-item {
  margin: 0 !important;
  /* 避免冲突 */
  width: auto !important;
}

.footer {
  font-size: 12px;
  font-weight: 400;
  margin-top: auto;
  padding-top: 30px;
  color: #979db1;
  text-align: center;
  /* 居中显示 */
}

/* 骨架屏动画 */
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
</style>