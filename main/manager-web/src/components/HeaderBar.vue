<template>
  <el-header class="header">
    <div style="display: flex;justify-content: space-between;">
      <div style="display: flex;align-items: center;gap: 10px;">
        <img src="@/assets/xiaozhi-logo.png" alt="" style="width: 56px;height: 56px;" />
        <img src="@/assets/xiaozhi-ai.png" alt="" style="width: 78px;height: 16px;" />
        <div class="equipment-management" @click="goHome">
          <img src="@/assets/home/equipment.png" alt="" style="width: 16px;height: 14px;" />
          设备管理
        </div>
        <div class="console">
          <i class="el-icon-s-grid" style="font-size: 14px;color: #979db1;" />
          控制台
        </div>
        <div class="equipment-management2">
          设备管理
          <img src="@/assets/home/close.png" alt="" style="width: 8px;height: 8px;" />
        </div>
      </div>
      <div style="display: flex;align-items: center;gap: 10px;">
        <div class="serach-box">
          <el-input placeholder="输入名称搜索.." v-model="serach" />
          <img src="@/assets/home/search.png" alt=""
               style="width: 16px;height: 16px;margin-right: 15px;cursor: pointer;" />
        </div>
        <img src="@/assets/home/avatar.png" alt="" style="width: 28px;height: 28px;" />
        <div class="user-info">
          158 3632 4642
        </div>
      </div>
    </div>
  </el-header>
</template>

<script>
export default {
  name: 'HeaderBar',
  data() {
    return { serach: '' }
  },
  methods: {
    goHome() {
      // 跳转到首页
      this.$router.push('/')
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
  width: 110px;
  height: 32px;
  border-radius: 16px;
  background: #5778ff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-weight: 500;
  color: #fff;
  font-size: 14px;
}

.equipment-management2 {
  width: 116px;
  height: 30px;
  border-radius: 15px;
  background: #fff;
  display: flex;
  justify-content: center;
  font-size: 12px;
  color: #979db1;
  font-weight: 400;
  gap: 10px;
  color: #3d4566;
  margin-left: 20px;
  align-items: center;
}

.header {
  background: #f6fcfe66;
  border: 1px solid #fff;
}

.serach-box {
  display: flex;
  width: 306px;
  height: 40px;
  border-radius: 20px;
  background-color: #e2f5f7;
  align-items: center;
}

.user-info {
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.02px;
  text-align: left;
  color: #3d4566;
}
.console {
  width: 120px;
  height: 30px;
  border-radius: 15px;
  background: radial-gradient(50% 50% at 50% 50%, #fff 0%, #e8f0ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #979db1;
  font-weight: 400;
  gap: 10px;
  color: #979db1;
  margin-left: 20px;
}
</style>