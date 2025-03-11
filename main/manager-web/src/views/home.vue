<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <el-header class="header">
        <div style="display: flex;justify-content: space-between;">
          <div style="display: flex;align-items: center;gap: 8px;margin-top: 10px;">
            <img src="@/assets/xiaozhi-logo.png" alt="" style="width: 45px;height: 45px;" />
            <img src="@/assets/xiaozhi-ai.png" alt="" style="width: 70px;height: 13px;" />
            <div class="equipment-management" @click="settingDevice=false">
              <img src="@/assets/home/equipment.png" alt="" style="width: 12px;height: 11px;" />
              设备管理
            </div>
            <div class="console">
              <i class="el-icon-s-grid" style="font-size: 11px;color: #979db1;" />
              控制台
            </div>
            <div class="equipment-management2">
              设备管理
              <img src="@/assets/home/close.png" alt="" style="width: 6px;height: 6px;" />
            </div>
          </div>
          <div style="display: flex;align-items: center;gap: 8px;margin-top: 10px">
            <div class="serach-box">
              <el-input placeholder="输入名称搜索.." v-model="serach" style="border: none; background: transparent;" @keyup.enter.native="handleSearch"  />
              <img src="@/assets/home/search.png" alt=""
                style="width: 12px;height: 12px;margin-right: 11px;cursor: pointer;" @click="handleSearch" />
            </div>
            <img src="@/assets/home/avatar.png" alt="" style="width: 21px;height: 21px;" />
            <div class="user-info">
              {{ userInfo.mobile }}
            </div>
          </div>
        </div>
      </el-header>
      <el-main style="padding: 15px;display: flex;flex-direction: column;">
        <div v-show="!settingDevice">
          <div class="add-device">
            <div class="add-device-bg">
              <div class="hellow-text" style="margin-top: 23px;">
                您好，小智</div>
              <div class="hellow-text">让我们度过<div style="display: inline-block;color: #5778FF;">
                  美好的一天！
                </div>
              </div>
              <div class="hi-hint">
                Hello, Let's have a wonderful day!</div>
              <div class="add-device-btn" @click="showAddDialog">
                <div class="left-add">
                  添加设备
                </div>
                <div style="width: 17px;height: 10px;background: #5778ff;margin-left: -8px;" />
                <div class="right-add">
                  <i class="el-icon-right" style="font-size: 23px;color: #fff;" />
                </div>
              </div>
            </div>
          </div>
          <div
            style="display: flex;flex-wrap: wrap;margin-top: 15px;gap: 15px;justify-content: flex-start;box-sizing: border-box;">
            <div class="device-item" v-for="(item,index) in filteredDeviceList" :key="index">
              <div style="display: flex;justify-content: space-between; align-items: center; ">
                <div style="font-weight: 700;font-size: 18px;text-align: left;color: #3d4566;">
<!--                  CC:ba:97:11:a6:ac-->
                  {{item.list[0]?.mac_address}}
                </div>
                <div style="display: flex;align-items: center;">
                  <img src="@/assets/home/delete.png" alt=""
                    style="width: 18px;height: 18px;margin-right: 8px;" @click="unbindDevice(item.list[0]?.id)" />
                  <img src="@/assets/home/info.png" alt="" style="width: 18px;height: 18px;" />
                </div>
              </div>
              <div class="device-name">
                设备型号：{{item.list[0]?.device_type}}
              </div>
              <div style="display: flex;gap: 8px;align-items: center;">
                <div class="settings-btn" @click="clickSettingDevice">
                  配置角色</div>
                <div class="settings-btn">
                  声纹识别</div>
                <div class="settings-btn">
                  历史对话</div>
                <el-switch :value="item.list[0]?.ota_upgrade && true || false" inactive-text="OTA升级:" :width="32"
                  style="margin-left: auto;" />
              </div>
              <div class="version-info">
                <div>最近对话：{{item.list[0]?.recent_chat_time}}</div>
                <div>APP版本：{{item.list[0]?.app_version}}</div>
              </div>
            </div>
          </div>
        </div>
<div v-show="settingDevice" style="border-radius: 18px;background: #fafcfe;">
          <div
            style="padding: 17px 27px;font-weight: 700;font-size: 21px;text-align: left;color: #3d4566;display: flex;gap: 14px;align-items: center;">
            <div
              style="width: 41px;height: 41px;background: #5778ff;border-radius: 50%;display: flex;align-items: center;justify-content: center;">
              <img src="@/assets/home/setting-user.png" alt="" style="width: 21px;height: 21px;" />
            </div>
            CC:ba:97:11:a6:ac
          </div>
          <div style="height: 1px;background: #e8f0ff;" />
          <el-form ref="form" :model="form" label-width="81px">
            <div style="padding: 18px 28px;max-width: 890px;">
              <el-form-item label="助手昵称：">
                <div class="input-46" style="width: 57.5%;">
                  <el-input v-model="form.name" />
                </div>
              </el-form-item>
              <el-form-item label="角色模版：">
                <div style="display: flex;gap: 10px;">
                  <div class="template-item">
                    台湾女友</div>
                  <div class="template-item">
                    土豆子</div>
                  <div class="template-item">
                    英语老师</div>
                  <div class="template-item">
                    好奇小男孩</div>
                  <div class="template-item">
                    汪汪队队长</div>
                </div>
              </el-form-item>
              <el-form-item label="角色音色：">
                <div style="display: flex;gap: 9px;align-items: center;">
                  <div class="input-46" style="flex:1.4;">
                    <el-select v-model="form.timbre" placeholder="请选择" style="width: 100%;">
                      <el-option v-for="item in options" :key="item.value" :label="item.label"
                        :value="item.value">
                      </el-option>
                    </el-select>
                  </div>
                  <div class="audio-box">
                    <audio src="http://music.163.com/song/media/outer/url?id=447925558.mp3" controls
                      style="height: 100%;width: 100%;" />
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="角色介绍：">
                <div class="textarea-box">
                  <el-input type="textarea" rows="5.4" resize="none" placeholder="请输入内容"
                    v-model="form.introduction" maxlength="2000" show-word-limit />
                </div>
              </el-form-item>
              <el-form-item label="记忆体：">
                <div class="textarea-box">
                  <el-input type="textarea" rows="5.4" resize="none" placeholder="请输入内容"
                    v-model="form.prompt" maxlength="1000" />
                  <div class="prompt-bottom">
                    <div style="display: flex;gap: 10px;align-items: center;">
                      <div style="color: #979db1;font-size: 12px;">当前记忆（每次对话后重新生成）</div>
                      <div class="clear-btn">
                        <i class="el-icon-delete-solid" style="font-size: 12px;" />
                        清除
                      </div>
                    </div>
                    <div style="color: #979db1;font-size:12px;">{{form.prompt.length}}/1000</div>
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="语言模型（内测）：" class="lh-form-item">
                <div style="display: flex;gap: 9px;">
                  <div class="input-46" style="width: 100%;">
                    <el-select v-model="form.model" placeholder="请选择" style="width: 100%;">
                      <el-option v-for="item in options" :key="item.value" :label="item.label"
                        :value="item.value">
                      </el-option>
                    </el-select>
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="" class="lh-form-item">
                <div style="color: #979db1;text-align: left;">除了“Qwen
                  实时”，其他模型通常会增加约1秒的延迟。改变模型后，建议清空记忆体，以免影响体验。</div>
              </el-form-item>
            </div>
          </el-form>
          <div style="display: flex;padding: 18px;gap: 9px;align-items: center;">
            <div class="save-btn">
              保存配置</div>
            <div class="reset-btn">
              重制</div>
            <div class="clear-text">
              <img src="@/assets/home/red-info.png" alt="" style="width: 21px;height: 21px;" />
              保存配置后，需要重启设备，新的配置才会生效。
            </div>
          </div>
        </div>
        <div
          style="font-size: 12px;font-weight: 400;margin-top: auto;padding-top: 30px;color: #979db1;">
          ©2025 xiaozhi-esp32-server
        </div>
      </el-main>
    </el-container>
    <el-dialog :visible.sync="addDeviceDialogVisible" width="400px" center>
      <div
        style="margin: 0 20px 20px;display: flex;align-items: center;gap: 10px;font-weight: 700;font-size: 20px;text-align: left;color: #3d4566;;">
        <div
          style="width: 36px;height: 36px;border-radius: 50%;background: #5778ff;display: flex;align-items: center;justify-content: center;">
          <img src="@/assets/home/equipment.png" alt="" style="width: 16px;height: 14px;" />
        </div>
        添加设备
      </div>
      <div style="height: 1px;background: #e8f0ff;" />
      <div style="margin: 30px 20px;">
        <div style="font-weight: 400;font-size: 14px;text-align: left;color: #3d4566;">
          <div style="color: red;display: inline-block;">*</div>验证码：
        </div>
        <div class="input-46" style="margin-top: 10px;">
          <el-input placeholder="请输入设备播报的6位数验证码.." v-model="deviceCode" />
        </div>
      </div>
      <div style="display: flex;margin: 0 20px;gap: 10px;">
        <div class="dialog-btn" @click="addDeviceDialogVisible=false">确定</div>
        <div class="dialog-btn"
          style="background: #e6ebff;border: 1px solid #adbdff;color: #5778ff;"
          @click="addDeviceDialogVisible=false">
          取消</div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
// @ is an alias to /src

import Api from '@/apis/api';

export default {
  name: 'home',
  data() {
    return {
      serach: '', // 搜索框输入内容
      deviceList: [], // 原始设备列表
      filteredDeviceList: [], // 过滤后的设备列表
      switchValue: false,
      addDeviceDialogVisible: false,
      deviceCode: "",
      settingDevice: false,
      form: {
        name: "",
        timbre: "",
        introduction: "",
        prompt: "",
        model: ""
      },
      options: [{
        value: '选项1',
        label: '黄金糕'
      }, {
        value: '选项2',
        label: '双皮奶'
      }],
      userInfo: {
        mobile: '' // 初始化用户信息
      }
    };
  },
  methods: {
    showAddDialog() {
      this.addDeviceDialogVisible = true;
    },
    clickSettingDevice() {
      this.settingDevice = true
    },
    // 获取用户信息
    fetchUserInfo() {
      Api.user.getUserInfo(({data}) => {
        this.userInfo = data.data
      });
    },
    // 获取已绑设备
    getList(){
      Api.user.getHomeList(({data})=>{
        this.deviceList = data.data; // 保存原始设备列表
        this.filteredDeviceList = data.data; // 初始化过滤后的设备列表
      })
    },
    // 处理搜索
    handleSearch() {
      if (this.serach.trim() === '') {
        // 如果搜索框为空，显示全部设备
        this.filteredDeviceList = this.deviceList;
      } else {
        // 过滤设备列表
        this.filteredDeviceList = this.deviceList.filter(device => {
          return (
            device.list[0]?.mac_address?.includes(this.serach) ||  // 匹配MAC地址
            device.list[0]?.device_type?.includes(this.serach) ||  // 匹配设备型号
            device.list[0]?.app_version?.includes(this.serach)     // 匹配APP版本
          );
        });
      }
    },
    // 解绑设备
    unbindDevice(device_id) {
      this.$confirm('确定要解绑该设备吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        // 调用解绑设备的接口
        Api.user.unbindDevice(device_id, ({ data }) => {
          if (data.code === 0) {
            this.$message.success('解绑成功');
            this.getList();
          } else {
            this.$message.error(data.msg || '解绑失败');
          }
        });
      }).catch(() => {
        // 用户取消操作
        this.$message.info('已取消解绑');
      });
    },
  },
  mounted() {
    this.fetchUserInfo(); // 组件加载时获取用户信息
    this.getList(); // 初始化设备列表
  }
}
</script>

<style scoped lang="scss">
.welcome {
  min-width: 900px;
  min-height: 506px;
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
.equipment-management,
.equipment-management2 {
  cursor: pointer;
}
.equipment-management {
  width: 83px;
  height: 24px;
  border-radius: 12px;
  background: #5778ff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 500;
  color: #fff;
  font-size: 11px;
}
.equipment-management2 {
  width: 87px;
  height: 23px;
  border-radius: 11px;
  background: #fff;
  display: flex;
  justify-content: center;
  font-size: 9px;
  font-weight: 400;
  gap: 8px;
  color: #3d4566;
  margin-left: 5px;
  align-items: center;
}
.header {
  background: #f6fcfe66;
  border: 1px solid #fff;
}
.add-device {
  height: 195px;
  border-radius: 15px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(
    269.62deg,
    #e0e6fd 0%,
    #cce7ff 49.69%,
    #d3d3fe 100%
  );
}
.audio-box {
  flex: 1;
  height: 35px;
  border-radius: 8px;
  border: 1px solid #e4e6ef;
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
    font-size: 9px;
    text-align: left;
    color: #818cae;
    margin-left: 75px;
    margin-top: 5px;
  }
}
.serach-box {
  display: flex;
  width: 250px;
  height: 30px;
  border-radius: 15px;
  background-color: #f6fcfe66;
  border: 1px solid #e4e6ef;
  align-items: center;
  padding: 0 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.user-info {
  font-weight: 600;
  font-size: 12px;
  letter-spacing: -0.02px;
  text-align: left;
  color: #3d4566;
}
.clear-btn {
  width: 45px;
  height: 18px;
  background: #fd8383;
  border-radius: 9px;
  line-height: 18px;
  font-size: 11px;
  color: #fff;
  cursor: pointer;
}
.clear-text {
  color: #979db1;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 15px;
}
.template-item {
  height: 35px;
  width: 85px;
  border-radius: 8px;
  background: #e6ebff;
  line-height: 35px;
  font-weight: 400;
  font-size: 11px;
  text-align: center;
  color: #5778ff;
}
.prompt-bottom {
  margin-bottom: 4px;display: flex;justify-content: space-between;padding: 0 15px;align-items: center;
}
.input-35 {
  border: 1px solid #e4e6ef;
  background: #f6f8fb;
  border-radius: 8px;
}
.console {
  width: 90px;
  height: 23px;
  border-radius: 11px;
  background: radial-gradient(50% 50% at 50% 50%, #fff 0%, #e8f0ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  color: #979db1;
  font-weight: 400;
  gap: 8px;
  margin-left: 15px;
}
.dialog-btn {
  cursor: pointer;
  flex: 1;
  border-radius: 17px;
  background: #5778ff;
  height: 34px;
  font-weight: 500;
  font-size: 11px;
  color: #fff;
  line-height: 34px;
  text-align: center;
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
    font-size: 11px;
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
.device-item {
  width: 345px;
  border-radius: 15px;
  background: #fafcfe;
  padding: 22px;
  box-sizing: border-box;
}
.device-name {
  margin: 8px 0 10px;
  font-weight: 400;
  font-size: 11px;
  color: #3d4566;
  text-align: left;
}
audio::-webkit-media-controls-panel {
  background-color: #fafcfe; /* 设置音频面板的控制按钮背景颜色为透明 */
}
.settings-btn {
  font-weight: 500;
  font-size: 11px;
  color: #5778ff;
  background: #e6ebff;
  width: 57px;
  height: 21px;
  line-height: 21px;
  cursor: pointer;
  border-radius: 10px;
}
.version-info {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 11px;
  color: #979db1;
  font-weight: 400;
}
.save-btn,
.reset-btn {
  width: 105px;
  height: 34px;
  border-radius: 17px;
  line-height: 34px;
  box-sizing: border-box;
  cursor: pointer;
  font-size: 12px;
}
.save-btn {
  border-radius: 23px;
  background: #5778ff;
  color: #fff;
}
.reset-btn {
  border: 1px solid #adbdff;
  background: #e6ebff;
  color: #5778ff;
}
.textarea-box {
  border: 1px solid #e4e6ef;
  border-radius: 8px;
  background: #f6f8fb;
}
::v-deep {
  .textarea-box .el-textarea__inner {
    background-color: transparent !important;
    border: none !important;
    padding: 15px;
  }
  // 搜索输入框的样式调整
  .serach-box .el-input__inner {
    border: none;
    background-color: transparent;
    padding: 0 5px 0 15px;
    font-size: 12px;
    color: #3d4566;
  }
  .el-textarea .el-input__count {
    color: #979db1;
    font-size: 11px;
    right: 15px;
    background-color: transparent;
  }
  .el-input__inner {
    //border: none;
    //background-color: transparent;
    padding: 0 5px 0 15px;
    border-radius: 8px;
  }
  .input-46 .el-input__inner {
    padding: 0 15px;
    height: 38px;
  }
  .lh-form-item {
    .el-form-item__label {
      line-height: 17px;
    }
  }
  .el-form-item__label {
    line-height: 34px;
    font-weight: 400;
    font-size: 11px;
    text-align: left;
    color: #3d4566;
  }
  .el-switch__core {
    height: 21px;
    border-radius: 10px;
  }
  .el-switch {
    line-height: 28px;
  }
  .el-switch.is-checked .el-switch__core::after {
    left: calc(100% - 4px);
  }
  .el-switch__label {
    color: #3d4566;
  }
  .el-switch__core:after {
    left: 4px;
    width: 15px;
    height: 15px;
    top: 2px;
  }
  .el-dialog__headerbtn .el-dialog__close {
    display: none;
  }
  .el-dialog__header,
  .el-dialog__footer {
    padding: 0;
  }
  .el-dialog--center .el-dialog__body {
    padding: 24px 0;
  }
  .el-dialog {
    display: flex !important;
    flex-direction: column !important;
    margin: 0 !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    overflow-y: scroll !important;
    max-height: 100vh !important;
    border-radius: 15px;
  }
}
</style>


