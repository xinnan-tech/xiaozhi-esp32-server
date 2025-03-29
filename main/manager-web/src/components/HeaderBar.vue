<template>
  <el-header class="header">
    <div class="header-container">
      <!-- 左侧元素 -->
      <div class="header-left">
        <img alt="" src="@/assets/xiaozhi-logo.png" class="logo-img"/>
        <img alt="" src="@/assets/xiaozhi-ai.png" class="brand-img"/>
      </div>

      <!-- 中间导航菜单 -->
      <div class="header-center">
        <div class="equipment-management" :class="{ 'active-tab': $route.path === '/home' }" @click="goHome">
          <img alt="" src="@/assets/header/roboot.png" :style="{ filter: $route.path === '/home' ? 'brightness(0) invert(1)' : 'None' }"/>
          智能体管理
        </div>
        <div class="equipment-management" :class="{ 'active-tab': $route.path === '/user-management' }" @click="goUserManagement">
          <img alt="" src="@/assets/header/user_management.png" :style="{ filter: $route.path === '/user-management' ? 'brightness(0) invert(1)' : 'None' }"/>
          用户管理
        </div>
        <div class="equipment-management" :class="{ 'active-tab': $route.path === '/model-config' }" @click="goModelConfig">
          <img alt="" src="@/assets/header/model_config.png" :style="{ filter: $route.path === '/model-config' ? 'brightness(0) invert(1)' : 'None' }"/>
          模型配置
        </div>
      </div>

      <!-- 右侧元素 -->
      <div class="header-right">
        <div class="search-container">
          <el-input
            v-model="serach"
            placeholder="输入名称搜索.."
            class="custom-search-input"
            @keyup.enter.native="handleSearch"
          >
            <i slot="suffix" class="el-icon-search search-icon" @click="handleSearch"></i>
          </el-input>
        </div>
        <img alt="" src="@/assets/home/avatar.png" class="avatar-img"/>
        <el-dropdown trigger="click" class="user-dropdown">
          <span class="el-dropdown-link">
             {{ userInfo.mobile || '加载中...' }}<i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item icon="el-icon-plus" @click.native="">个人中心</el-dropdown-item>
            <el-dropdown-item icon="el-icon-circle-plus" @click.native="showChangePasswordDialog">修改密码</el-dropdown-item>
            <el-dropdown-item icon="el-icon-circle-plus-outline" @click.native="">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <ChangePasswordDialog :visible.sync="isChangePasswordDialogVisible"/>
  </el-header>
</template>

<script>
import userApi from '@/apis/module/user';
import ChangePasswordDialog from './ChangePasswordDialog.vue'; // 引入修改密码弹窗组件

export default {
  name: 'HeaderBar',
  components: {
    ChangePasswordDialog
  },
  props: ['devices'],  // 接收父组件设备列表
  data() {
    return {
      serach: '',
      userInfo: {
        username: '',
        mobile: ''
      },
      isChangePasswordDialogVisible: false // 控制修改密码弹窗的显示
    }
  },
  mounted() {
    this.fetchUserInfo()
  },
  methods: {
    goHome() {
      // 跳转到首页
      this.$router.push('/')
    },
    goUserManagement() {
      this.$router.push('/user-management')
    },
    goModelConfig() {
      this.$router.push('/model-config')
    },
    // 获取用户信息
    fetchUserInfo() {
      userApi.getUserInfo(({data}) => {
        this.userInfo = data.data
      })
    },

    // 处理搜索
    handleSearch() {
      const searchValue = this.serach.trim();
      let filteredDevices;

      if (!searchValue) {
        // 当搜索内容为空时，显示原始完整列表
        filteredDevices = this.$parent.originalDevices;
      } else {
        // 过滤逻辑
        filteredDevices = this.devices.filter(device => {
          return device.agentName.includes(searchValue) ||
              device.ttsModelName.includes(searchValue) ||
              device.ttsVoiceName.includes(searchValue);
        });
      }

      this.$emit('search-result', filteredDevices);
    },

    // 显示修改密码弹窗
    showChangePasswordDialog() {
      this.isChangePasswordDialogVisible = true;
    }
  }
}
</script>

<style scoped>
.header {
  background: #f6fcfe66;
  border: 1px solid #fff;
  height: 53px !important;
  min-width: 900px; /* 设置最小宽度防止过度压缩 */
  overflow: hidden;
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 120px;
}

.logo-img {
  width: 42px;
  height: 42px;
}

.brand-img {
  width: 58px;
  height: 12px;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 25px;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 300px;
  justify-content: flex-end;
}

.equipment-management {
  width: 82px;
  height: 24px;
  border-radius: 12px;
  background: #deeafe;
  display: flex;
  justify-content: center;
  font-size: 10px;
  font-weight: 500;
  gap: 7px;
  color: #3d4566;
  margin-left: 1px;
  align-items: center;
  transition: all 0.3s ease;
  cursor: pointer;
  flex-shrink: 0; /* 防止导航按钮被压缩 */
}

.equipment-management.active-tab {
  background: #5778ff !important;
  color: #fff !important;
}

.equipment-management img {
  width: 15px;
  height: 13px;
}

.search-container {
  margin-right: 15px;
  min-width: 150px;
  flex-grow: 1;
  max-width: 220px;
}

.custom-search-input >>> .el-input__inner {
  height: 30px;
  border-radius: 15px;
  background-color: #e2e5f8;
  border: 1px solid #e4e6ef;
  padding-left: 15px;
  font-size: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  width: 100%;
}

.search-icon {
  cursor: pointer;
  color: #909399;
  margin-right: 8px;
  font-size: 14px;
  line-height: 30px;
}

.avatar-img {
  width: 21px;
  height: 21px;
  flex-shrink: 0;
}

.user-dropdown {
  flex-shrink: 0;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .header-center {
    gap: 14px;
  }

  .equipment-management {
    width: 70px;
    font-size: 9px;
  }
}

@media (max-width: 1024px) {
  .search-container {
    margin-right: 10px;
    max-width: 150px;
  }

  .header-right {
    gap: 5px;
  }
}

@media (max-width: 900px) {
  .header-left {
    margin-right: auto;
  }

  .search-container {
    max-width: 150px;
  }
}

@media (max-width: 768px) {
  .search-container {
    max-width: 145px;
  }

  .custom-search-input >>> .el-input__inner {
    padding-left: 10px;
    font-size: 11px;
  }
}

@media (max-width: 600px) {
  .search-container {
    max-width: 120px;
    min-width: 100px;
  }
}
</style>