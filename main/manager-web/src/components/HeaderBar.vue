<template>
  <el-header class="header">
    <div style="display: flex;justify-content: space-between;margin-top: 6px; ">
      <div style="display: flex;align-items: center;gap: 10px;">
        <img alt="" src="@/assets/xiaozhi-logo.png" style="width: 42px;height: 42px;"/>
        <img alt="" src="@/assets/xiaozhi-ai.png" style="width: 58px;height: 12px;"/>
        <div class="equipment-management" @click="goHome">
          <img alt="" src="@/assets/home/equipment.png" style="width: 12px;height: 10px;"/>
          智能体管理
        </div>
        <div class="equipment-management2" :class="{ 'active-tab': $route.path === '/user-management' }" @click="goUserManagement">
          用户管理
        </div>
        <div class="equipment-management2" :class="{ 'active-tab': $route.path === '/model-config' }" @click="goModelConfig">
          模型配置
        </div>
      </div>
      <div style="display: flex;align-items: center;gap: 7px; margin-top: 2px;">
        <div class="serach-box">
          <el-input v-model="serach" placeholder="输入名称搜索.." style="border: none; background: transparent;"
                    @keyup.enter.native="handleSearch"/>
          <img alt="" src="@/assets/home/search.png"
               style="width: 14px;height: 14px;margin-right: 11px;cursor: pointer;" @click="handleSearch"/>
        </div>
        <img alt="" src="@/assets/home/avatar.png" style="width: 21px;height: 21px;"/>
        <el-dropdown trigger="click">
          <span class="el-dropdown-link">
             {{ userInfo.username }}<i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item icon="el-icon-plus" @click.native="">个人中心</el-dropdown-item>
            <el-dropdown-item icon="el-icon-circle-plus" @click.native="">修改密码</el-dropdown-item>
            <el-dropdown-item icon="el-icon-circle-plus-outline" @click.native="">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </div>
  </el-header>
</template>

<script>
import userApi from '@/apis/module/user'


export default {
  name: 'HeaderBar',
  props: ['devices'],  // 接收父组件设备列表
  data() {
    return {
      serach: '',
      userInfo: {
        username: '',
        mobile: ''
      }
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
        this.userInfo = {
          username: data.data.mobile, // 暂时先使用手机号作为用户名
          mobile: data.data.mobile
        }
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
    }

  }

}
</script>

<style scoped>
.equipment-management,
.equipment-management2 {
  cursor: pointer;
}

.equipment-management {
  width: 82px;
  height: 24px;
  border-radius: 12px;
  background: #5778ff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-weight: 500;
  color: #fff;
  font-size: 10px;
}

.equipment-management2 {
  width: 82px;
  height: 24px;
  border-radius: 12px;
  background: #fff;
  display: flex;
  justify-content: center;
  font-size: 10px;
  font-weight: 500;
  gap: 7px;
  color: #3d4566;
  margin-left: 1px;
  align-items: center;
  transition: all 0.3s ease;
}

.equipment-management2.active-tab {
  background: #5778ff !important;
  color: #fff !important;
}

.header {
  background: #f6fcfe66;
  border: 1px solid #fff;
  height: 53px !important;
}

.serach-box {
  display: flex;
  width: 220px;
  height: 30px;
  border-radius: 15px;
  background-color: #f6fcfe66;
  border: 1px solid #e4e6ef;
  align-items: center;
  padding: 0 7px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-right: 15px;
}

.serach-box /deep/ .el-input__inner {
  border-radius: 15px;
  height: 100%;
  width: 100%;
  border: 0;
  background: transparent;
  padding-left: 12px;
}


.user-info {
  font-weight: 600;
  font-size: 12px;
  letter-spacing: -0.02px;
  text-align: left;
  color: #3d4566;
}

</style>
