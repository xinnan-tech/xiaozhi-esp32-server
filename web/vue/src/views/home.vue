<template>
  <div class="welcome">
    <el-container style="height: 100%;">
      <el-header class="header">
        <div style="display: flex;justify-content: space-between;">
          <div style="display: flex;align-items: center;gap: 8px;">
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
          <div style="display: flex;align-items: center;gap: 8px;">
            <div class="serach-box">
              <el-input placeholder="输入名称搜索.." v-model="serach" />
              <img src="@/assets/home/search.png" alt=""
                style="width: 12px;height: 12px;margin-right: 11px;cursor: pointer;" />
            </div>
            <img src="@/assets/home/avatar.png" alt="" style="width: 21px;height: 21px;" />
            <div class="user-info">
              158 3632 4642</div>
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
            style="display: flex;flex-wrap: wrap;margin-top: 15px;gap: 15px;justify-content: space-between;box-sizing: border-box;">
            <div class="device-item" v-for="(item,index) in 10" :key="index">
              <div style="display: flex;justify-content: space-between;">
                <div style="font-weight: 700;font-size: 18px;text-align: left;color: #3d4566;">
                  CC:ba:97:11:a6:ac
                </div>
                <div>
                  <img src="@/assets/home/delete.png" alt=""
                    style="width: 18px;height: 18px;margin-right: 8px;" />
                  <img src="@/assets/home/info.png" alt="" style="width: 18px;height: 18px;" />
                </div>
              </div>
              <div class="device-name">
                设备型号：esp32-s3-touch-amoled-1.8
              </div>
              <div style="display: flex;gap: 8px;align-items: center;">
                <div class="settings-btn" @click="clickSettingDevice">
                  配置角色</div>
                <div class="settings-btn">
                  声纹识别</div>
                <div class="settings-btn">
                  历史对话</div>
                <el-switch v-model="switchValue" inactive-text="OTA升级:" :width="32"
                  style="margin-left: auto;" />
              </div>
              <div class="version-info">
                <div>最近对话：6天前</div>
                <div>APP版本：1.1.0</div>
              </div>
            </div>
          </div>
        </div>
<div v-show="settingDevice" style="border-radius: 20px;background: #fafcfe;">
          <div
            style="padding: 19px 30px;font-weight: 700;font-size: 24px;text-align: left;color: #3d4566;display: flex;gap: 16px;align-items: center;">
            <div
              style="width: 46px;height: 46px;background: #5778ff;border-radius: 50%;display: flex;align-items: center;justify-content: center;">
              <img src="@/assets/home/setting-user.png" alt="" style="width: 24px;height: 24px;" />
            </div>
            CC:ba:97:11:a6:ac
          </div>
          <div style="height: 1px;background: #e8f0ff;" />
          <el-form ref="form" :model="form" label-width="90px">
            <div style="padding: 20px 30px;max-width: 990px;">
              <el-form-item label="助手昵称：">
                <div class="input-46">
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
                <div style="display: flex;gap: 10px;align-items: center;">
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
                  <el-input type="textarea" rows="6" resize="none" placeholder="请输入内容"
                    v-model="form.introduction" maxlength="2000" show-word-limit />
                </div>
              </el-form-item>
              <el-form-item label="记忆体：">
                <div class="textarea-box">
                  <el-input type="textarea" rows="6" resize="none" placeholder="请输入内容"
                    v-model="form.prompt" maxlength="1000" />
                  <div class="prompt-bottom">
                    <div style="display: flex;gap: 10px;align-items: center;">
                      <div style="color: #979db1;font-size: 14px;">当前记忆（每次对话后重新生成）</div>
                      <div class="clear-btn">
                        <i class="el-icon-delete-solid" style="font-size: 14px;" />
                        清除
                      </div>
                    </div>
                    <div style="color: #979db1;font-size:14px;">{{form.prompt.length}}/1000</div>
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="语言模型（内测）：" class="lh-form-item">
                <div style="display: flex;gap: 10px;">
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
          <div style="display: flex;padding: 20px;gap: 10px;align-items: center;">
            <div class="save-btn">
              保存配置</div>
            <div class="reset-btn">
              重制</div>
            <div class="clear-text">
              <img src="@/assets/home/red-info.png" alt="" style="width: 24px;height: 24px;" />
              保存配置后，需要重启设备，新的配置才会生效。
            </div>
          </div>
        </div>
        <div
          style="font-size: 12px;font-weight: 400;margin-top: auto;padding-top: 30px;color: #979db1;">
          ©2025 xiaozhi-esp32-server</div>
      </el-main>
    </el-container>
    <el-dialog :visible.sync="addDeviceDialogVisible" width="480px" center>
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

export default {
  name: 'home',
  data() {
    return {
      serach: '',
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
      }]
    }
  },
  methods: {
    showAddDialog() {
      this.addDeviceDialogVisible = true;
    },
    clickSettingDevice() {
      this.settingDevice = true
    }
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
  width: 230px;
  height: 30px;
  border-radius: 15px;
  background-color: #e2f5f7;
  align-items: center;
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
  width: 75px;
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
  width: 341px;
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
  .el-textarea .el-input__count {
    color: #979db1;
    font-size: 11px;
    right: 15px;
    background-color: transparent;
  }
  .el-input__inner {
    border: none;
    background-color: transparent;
    padding: 0 5px 0 15px;
  }
  .input-46 .el-input__inner {
    padding: 0 15px;
    height: 46px;
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
