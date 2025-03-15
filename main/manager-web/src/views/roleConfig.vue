<template>
  <div class="welcome">
    <!-- 公共头部 -->
    <HeaderBar/>
    <el-main style="padding: 20px;display: flex;flex-direction: column;">
      <div style="border-radius: 20px;background: #fafcfe;">
        <div
            style="padding: 19px 30px;font-weight: 700;font-size: 24px;text-align: left;color: #3d4566;display: flex;gap: 16px;align-items: center;">
          <div
              style="width: 46px;height: 46px;background: #5778ff;border-radius: 50%;display: flex;align-items: center;justify-content: center;">
            <img src="@/assets/home/setting-user.png" alt="" style="width: 24px;height: 24px;"/>
          </div>
          {{ deviceMac }}
        </div>
        <div style="height: 1px;background: #e8f0ff;"/>
        <el-form ref="form" :model="form" label-width="90px">
          <div style="padding: 20px 30px;max-width: 990px;">
            <el-form-item label="助手昵称：">
              <div class="input-46">
                <el-input v-model="form.name"/>
              </div>
            </el-form-item>
            <el-form-item label="角色模版：">
              <div style="display: flex;gap: 10px;">
                <div class="template-item">
                  台湾女友
                </div>
                <div class="template-item">
                  土豆子
                </div>
                <div class="template-item">
                  英语老师
                </div>
                <div class="template-item">
                  好奇小男孩
                </div>
                <div class="template-item">
                  汪汪队队长
                </div>
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
                         style="height: 100%;width: 100%;"/>
                </div>
              </div>
            </el-form-item>
            <el-form-item label="角色介绍：">
              <div class="textarea-box">
                <el-input type="textarea" rows="6" resize="none" placeholder="请输入内容"
                          v-model="form.introduction" maxlength="2000" show-word-limit/>
              </div>
            </el-form-item>
            <el-form-item label="记忆体：">
              <div class="textarea-box">
                <el-input type="textarea" rows="6" resize="none" placeholder="请输入内容"
                          v-model="form.prompt" maxlength="1000"/>
                <div class="prompt-bottom">
                  <div style="display: flex;gap: 10px;align-items: center;">
                    <div style="color: #979db1;font-size: 14px;">当前记忆（每次对话后重新生成）</div>
                    <div class="clear-btn">
                      <i class="el-icon-delete-solid" style="font-size: 14px;"/>
                      清除
                    </div>
                  </div>
                  <div style="color: #979db1;font-size:14px;">{{ form.prompt.length }}/1000</div>
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
                实时”，其他模型通常会增加约1秒的延迟。改变模型后，建议清空记忆体，以免影响体验。
              </div>
            </el-form-item>
          </div>
        </el-form>
        <div style="display: flex;padding: 20px;gap: 10px;align-items: center;">
          <div class="save-btn" @click="saveConfig">
            保存配置
          </div>
          <div class="reset-btn" @click="resetConfig">
            重制
          </div>
          <div class="clear-text">
            <img src="@/assets/home/red-info.png" alt="" style="width: 24px;height: 24px;"/>
            保存配置后，需要重启设备，新的配置才会生效。
          </div>
        </div>
      </div>
      <div style="font-size: 12px;font-weight: 400;margin-top: auto;padding-top: 30px;color: #979db1;">
        ©2025 xiaozhi-esp32-server
      </div>
    </el-main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";

export default {
  name: 'RoleConfigPage',
  components: {HeaderBar},
  data() {
    return {
      deviceMac: 'CC:ba:97:11:a6:ac',
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
    saveConfig() {
      // 此处写保存配置逻辑
      this.$message.success('配置已保存')
    },
    resetConfig() {
      this.$confirm('确定要重置配置吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        // 重置表单
        this.form = {
          name: "",
          timbre: "",
          introduction: "",
          prompt: "",
          model: ""
        }
        this.$message.success('配置已重置')
      }).catch(() => {
      })
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
.audio-box {
  flex: 1;
  height: 46px;
  border-radius: 10px;
  border: 1px solid #e4e6ef;
}

.clear-btn {
  width: 60px;
  height: 24px;
  background: #fd8383;
  border-radius: 12px;
  line-height: 24px;
  font-size: 14px;
  color: #fff;
  cursor: pointer;
}

.clear-text {
  color: #979db1;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 20px;
}

.template-item {
  height: 46px;
  width: 100px;
  border-radius: 10px;
  background: #e6ebff;
  line-height: 46px;
  font-weight: 400;
  font-size: 14px;
  text-align: center;
  color: #5778ff;
}

.prompt-bottom {
  margin-bottom: 5px;
  display: flex;
  justify-content: space-between;
  padding: 0 20px;
  align-items: center;
}

.input-46 {
  border: 1px solid #e4e6ef;
  background: #f6f8fb;
  border-radius: 10px;
}

.save-btn,
.reset-btn {
  width: 140px;
  height: 46px;
  border-radius: 23px;
  line-height: 46px;
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
  border-radius: 10px;
  background: #f6f8fb;
}
</style>