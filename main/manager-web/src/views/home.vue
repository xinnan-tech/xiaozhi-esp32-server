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
              你好，小智
            </div>
            <div class="hellow-text">
              让我们度过
              <div style="display: inline-block;color: #5778FF;">
                美好的一天！
              </div>
            </div>
            <div class="hi-hint">
              Hello, Let's have a wonderful day!
            </div>
            <div class="add-device-btn" @click="showAddDialog">
              <div class="left-add">
                添加智能体
              </div>
              <div style="width: 23px;height: 13px;background: #5778ff;margin-left: -10px;" />
              <div class="right-add">
                <i class="el-icon-right" style="font-size: 20px;color: #fff;" />
              </div>
            </div>
          </div>
        </div>
        <div class="device-list-container">
          <DeviceItem v-for="(item, index) in devices" :key="index" :device="item" @configure="goToRoleConfig"
            @deviceManage="handleDeviceManage" @delete="handleDeleteAgent" />
        </div>
      </div>
      <div class="copyright">
        ©2025 xiaozhi-esp32-server
      </div>
      <AddWisdomBodyDialog :visible.sync="addDeviceDialogVisible" @confirm="handleWisdomBodyAdded" />
    </el-main>
  </div>

</template>

<script>
import Api from '@/apis/api';
import AddWisdomBodyDialog from '@/components/AddWisdomBodyDialog.vue';
import DeviceItem from '@/components/DeviceItem.vue';
import HeaderBar from '@/components/HeaderBar.vue';

export default {
  name: 'HomePage',
  components: { DeviceItem, AddWisdomBodyDialog, HeaderBar },
  data() {
    return {
      addDeviceDialogVisible: false,
      devices: [],
      originalDevices: [],
      isSearching: false,
      searchRegex: null
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
      Api.agent.getAgentList(({ data }) => {
        this.originalDevices = data.data.map(item => ({
          ...item,
          agentId: item.id // 字段映射
        }));
        this.handleSearchReset(); // 重置搜索状态
      });
    },
    // 删除智能体
    handleDeleteAgent(agentId) {
      this.$confirm('确定要删除该智能体吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        Api.agent.deleteAgent(agentId, (res) => {
          if (res.data.code === 0) {
            this.$message.success({
              message: '删除成功',
              showClose: true
            });
            this.fetchAgentList(); // 刷新列表
          } else {
            this.$message.error({
              message: res.data.msg || '删除失败',
              showClose: true
            });
          }
        });
      }).catch(() => { });
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
    font-size: 10px;
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
    font-size: 10px;
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
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
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
</style>