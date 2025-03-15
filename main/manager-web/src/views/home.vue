<template>
  <div class="welcome">
      <!-- 公共头部 -->
      <HeaderBar />
      <el-main style="padding: 20px;display: flex;flex-direction: column;">
        <div>
          <!-- 首页内容 -->
          <div class="add-device">
            <div class="add-device-bg">
              <div class="hellow-text" style="margin-top: 30px;">
                您好，小智
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
                  添加设备
                </div>
                <div style="width: 23px;height: 13px;background: #5778ff;margin-left: -10px;" />
                <div class="right-add">
                  <i class="el-icon-right" style="font-size: 30px;color: #fff;" />
                </div>
              </div>
            </div>
          </div>
          <div style="display: flex;flex-wrap: wrap;margin-top: 20px;gap: 20px;justify-content: space-between;box-sizing: border-box;">
            <DeviceItem v-for="(item,index) in devices" :key="index" :device="item" @configure="goToRoleConfig" />
          </div>
        </div>
        <div style="font-size: 12px;font-weight: 400;margin-top: auto;padding-top: 30px;color: #979db1;">
          ©2025 xiaozhi-esp32-server
        </div>
        <AddDeviceDialog :visible.sync="addDeviceDialogVisible" @added="handleDeviceAdded" />
      </el-main>
  </div>

</template>

<script>
import DeviceItem from '@/components/DeviceItem.vue'
import AddDeviceDialog from '@/components/AddDeviceDialog.vue'
import HeaderBar from '@/components/HeaderBar.vue'
export default {
  name: 'HomePage',
  components: { DeviceItem, AddDeviceDialog, HeaderBar },
  data() {
    return {
      addDeviceDialogVisible: false,
      // 此处模拟设备列表（10条数据）
      devices: Array.from({ length: 10 }, (_, i) => ({
        id: i,
        mac: 'CC:ba:97:11:a6:ac',
        model: 'esp32-s3-touch-amoled-1.8',
        lastConversation: '6天前',
        appVersion: '1.1.0'
      }))
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
    handleDeviceAdded(deviceCode) {
      // 根据需要处理添加设备后逻辑，比如刷新设备列表等
      console.log('设备验证码：', deviceCode)
    }
  }
}
</script>

<style scoped>
.welcome {
  min-width: 1200px;
  min-height: 675px;
  height: 100vh;
  background-image: url("@/assets/home/background.png");
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
  height: 260px;
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(
      269.62deg,
      #e0e6fd 0%,
      #cce7ff 49.69%,
      #d3d3fe 100%
  );
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
    margin-left: 100px;
    color: #3d4566;
    font-size: 44px;
    font-weight: 700;
    letter-spacing: 0;
  }

  .hi-hint {
    font-weight: 400;
    font-size: 12px;
    text-align: left;
    color: #818cae;
    margin-left: 100px;
    margin-top: 7px;
  }
}

.add-device-btn {
  display: flex;
  align-items: center;
  margin-left: 100px;
  margin-top: 20px;
  cursor: pointer;

  .left-add {
    width: 140px;
    height: 46px;
    border-radius: 23px;
    background: #5778ff;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    line-height: 46px;
  }

  .right-add {
    width: 46px;
    height: 46px;
    border-radius: 50%;
    background: #5778ff;
    margin-left: -8px;
    display: flex;
    justify-content: center;
    align-items: center;
  }
}
</style>