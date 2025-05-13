<template>
  <el-header class="header">
    <div class="header-container">
      <!-- 左侧元素 -->
      <div class="header-left" @click="goHome">
        <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" class="logo-img" />
        <img loading="lazy" alt="" src="@/assets/xiaozhi-ai.png" class="brand-img" />
      </div>

      <!-- 中间导航菜单 -->
      <div class="header-center">
        <div class="equipment-management"
          :class="{ 'active-tab': $route.path === '/home' || $route.path === '/role-config' || $route.path === '/device-management' }"
          @click="goHome">
          <img loading="lazy" alt="" src="@/assets/header/robot.png"
            :style="{ filter: $route.path === '/home' || $route.path === '/role-config' || $route.path === '/device-management' ? 'brightness(0) invert(1)' : 'None' }" />
          智能体管理
        </div>
        <div v-if="isSuperAdmin" class="equipment-management" :class="{ 'active-tab': $route.path === '/model-config' }"
          @click="goModelConfig">
          <img loading="lazy" alt="" src="@/assets/header/model_config.png"
            :style="{ filter: $route.path === '/model-config' ? 'brightness(0) invert(1)' : 'None' }" />
          模型配置
        </div>
        <div v-if="isSuperAdmin" class="equipment-management"
          :class="{ 'active-tab': $route.path === '/user-management' }" @click="goUserManagement">
          <img loading="lazy" alt="" src="@/assets/header/user_management.png"
            :style="{ filter: $route.path === '/user-management' ? 'brightness(0) invert(1)' : 'None' }" />
          用户管理
        </div>
        <div v-if="isSuperAdmin" class="equipment-management"
          :class="{ 'active-tab': $route.path === '/ota-management' }" @click="goOtaManagement">
          <img loading="lazy" alt="" src="@/assets/header/firmware_update.png"
            :style="{ filter: $route.path === '/ota-management' ? 'brightness(0) invert(1)' : 'None' }" />
          OTA管理
        </div>
        <el-dropdown v-if="isSuperAdmin" trigger="click" class="equipment-management more-dropdown"
          :class="{ 'active-tab': $route.path === '/dict-management' || $route.path === '/params-management' }">
          <span class="el-dropdown-link">
            <img loading="lazy" alt="" src="@/assets/header/param_management.png"
              :style="{ filter: $route.path === '/dict-management' || $route.path === '/params-management' ? 'brightness(0) invert(1)' : 'None' }" />
            参数字典
            <i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item @click.native="goParamManagement">
              参数管理
            </el-dropdown-item>
            <el-dropdown-item @click.native="goDictManagement">
              字典管理
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>

      <!-- 右侧元素 -->
      <div class="header-right">
        <div class="search-container" v-if="$route.path === '/home'">
          <el-input v-model="search" placeholder="输入名称搜索.." class="custom-search-input"
            @keyup.enter.native="handleSearch">
            <i slot="suffix" class="el-icon-search search-icon" @click="handleSearch"></i>
          </el-input>
        </div>
        <img loading="lazy" alt="" src="@/assets/home/avatar.png" class="avatar-img" />
        <el-dropdown trigger="click" class="user-dropdown">
          <span class="el-dropdown-link">
            {{ userInfo.username || '加载中...' }}<i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item @click.native="showChangePasswordDialog">修改密码</el-dropdown-item>
            <el-dropdown-item @click.native="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <ChangePasswordDialog v-model="isChangePasswordDialogVisible" />
  </el-header>
</template>

<script>
import userApi from '@/apis/module/user';
import { mapActions, mapGetters } from 'vuex';
import ChangePasswordDialog from './ChangePasswordDialog.vue'; // 引入修改密码弹窗组件


export default {
  name: 'HeaderBar',
  components: {
    ChangePasswordDialog
  },
  props: ['devices'],  // 接收父组件设备列表
  data() {
    return {
      search: '',
      userInfo: {
        username: '',
        mobile: ''
      },
      isChangePasswordDialogVisible: false // 控制修改密码弹窗的显示
    }
  },
  computed: {
    ...mapGetters(['getIsSuperAdmin']),
    isSuperAdmin() {
      return this.getIsSuperAdmin;
    }
  },
  mounted() {
    this.fetchUserInfo()
  },
  methods: {
    goHome() {
      // 跳转到首页
      this.$router.push('/home')
    },
    goUserManagement() {
      this.$router.push('/user-management')
    },
    goModelConfig() {
      this.$router.push('/model-config')
    },
    goParamManagement() {
      this.$router.push('/params-management')
    },
    goOtaManagement() {
      this.$router.push('/ota-management')
    },
    goDictManagement() {
      this.$router.push('/dict-management')
    },
    // 获取用户信息
    fetchUserInfo() {
      userApi.getUserInfo(({ data }) => {
        this.userInfo = data.data
        if (data.data.superAdmin !== undefined) {
          this.$store.commit('setUserInfo', data.data);
        }
      })
    },

    // 处理搜索
    handleSearch() {
      const searchValue = this.search.trim();

      // 如果搜索内容为空，触发重置事件
      if (!searchValue) {
        this.$emit('search-reset');
        return;
      }

      try {
        // 创建不区分大小写的正则表达式
        const regex = new RegExp(searchValue, 'i');
        // 触发搜索事件，将正则表达式传递给父组件
        this.$emit('search', regex);
      } catch (error) {
        console.error('正则表达式创建失败:', error);
        this.$message.error({
          message: '搜索关键词格式不正确',
          showClose: true
        });
      }
    },
    // 显示修改密码弹窗
    showChangePasswordDialog() {
      this.isChangePasswordDialogVisible = true;
    },
    // 退出登录
    async handleLogout() {
      try {
        // 调用 Vuex 的 logout action
        await this.logout();
        this.$message.success({
          message: '退出登录成功',
          showClose: true
        });
      } catch (error) {
        console.error('退出登录失败:', error);
        this.$message.error({
          message: '退出登录失败，请重试',
          showClose: true
        });
      }
    },

    // 使用 mapActions 引入 Vuex 的 logout action
    ...mapActions(['logout'])
  }
}
</script>

<style scoped>
.header {
  background: #f6fcfe66;
  border: 1px solid #fff;
  height: 63px !important;
  min-width: 900px;
  /* 设置最小宽度防止过度压缩 */
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
  height: 20px;
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
  padding: 0 9px;
  width: px;
  height: 30px;
  border-radius: 15px;
  background: #deeafe;
  display: flex;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
  gap: 7px;
  color: #3d4566;
  margin-left: 1px;
  align-items: center;
  transition: all 0.3s ease;
  cursor: pointer;
  flex-shrink: 0;
  /* 防止导航按钮被压缩 */
  padding: 0px 15px;
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

.custom-search-input>>>.el-input__inner {
  height: 30px;
  border-radius: 15px;
  background-color: #fff;
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

  .custom-search-input>>>.el-input__inner {
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

.equipment-management.more-dropdown {
  position: relative;
}

.equipment-management.more-dropdown .el-dropdown-menu {
  position: absolute;
  right: 0;
  min-width: 120px;
  margin-top: 5px;
}

.el-dropdown-menu__item {
  min-width: 60px;
  padding: 8px 20px;
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .equipment-management.more-dropdown .el-dropdown-menu {
    position: fixed;
    right: 10px;
    top: 60px;
    z-index: 2000;
  }
}
</style>