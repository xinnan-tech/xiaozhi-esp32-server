<template>
  <el-drawer
    :visible.sync="drawerVisible"
    :before-close="handleClose"
    direction="rtl"
    size="400px"
    :modal="true"
    :show-close="false"
    custom-class="tts-advanced-drawer"
  >
    <div class="drawer-header" slot="title">
      <span class="drawer-title">{{ $t('roleConfig.advancedSettings') }}</span>
      <button class="drawer-close-btn" @click="handleClose">×</button>
    </div>

    <div class="drawer-content">
      <el-form label-position="top">
        <!-- 音量 -->
        <el-form-item :label="$t('roleConfig.ttsVolume')">
          <div class="slider-container">
            <el-slider
              v-model="localSettings.volume"
              :min="-100"
              :max="100"
              :step="1"
              :format-tooltip="formatTooltip"
              class="tts-slider"
            />
            <span class="slider-hint">{{ $t('roleConfig.volumeHint') }}</span>
          </div>
        </el-form-item>

        <!-- 语速 -->
        <el-form-item :label="$t('roleConfig.ttsRate')">
          <div class="slider-container">
            <el-slider
              v-model="localSettings.speed"
              :min="-100"
              :max="100"
              :step="1"
              :format-tooltip="formatTooltip"
              class="tts-slider"
            />
            <span class="slider-hint">{{ $t('roleConfig.speedHint') }}</span>
          </div>
        </el-form-item>

        <!-- 音调 -->
        <el-form-item :label="$t('roleConfig.ttsPitch')">
          <div class="slider-container">
            <el-slider
              v-model="localSettings.pitch"
              :min="-100"
              :max="100"
              :step="1"
              :format-tooltip="formatTooltip"
              class="tts-slider"
            />
            <span class="slider-hint">{{ $t('roleConfig.pitchHint') }}</span>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <div class="drawer-footer">
      <el-button @click="handleCancel">{{ $t('button.cancel') }}</el-button>
      <el-button type="primary" @click="handleSave">{{ $t('button.save') }}</el-button>
    </div>
  </el-drawer>
</template>

<script>
export default {
  name: 'TtsAdvancedSettings',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    settings: {
      type: Object,
      default: () => ({
        volume: 0,
        speed: 0,
        pitch: 0
      })
    }
  },
  data() {
    return {
      localSettings: {
        volume: 0,
        speed: 0,
        pitch: 0
      }
    };
  },
  computed: {
    drawerVisible: {
      get() {
        return this.visible;
      },
      set(val) {
        this.$emit('update:visible', val);
      }
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        // 当抽屉打开时，复制当前设置到本地
        this.localSettings = { ...this.settings };
      }
    }
  },
  methods: {
    handleClose() {
      this.$emit('update:visible', false);
    },
    handleCancel() {
      // 取消时不保存，直接关闭
      this.handleClose();
    },
    handleSave() {
      // 保存设置并关闭
      this.$emit('save', { ...this.localSettings });
      this.handleClose();
    },
    formatTooltip(val) {
      return `${val}%`;
    }
  }
};
</script>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e8f0ff;
}

.drawer-title {
  font-size: 18px;
  font-weight: 600;
  color: #3d4566;
}

.drawer-close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 28px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  outline: none;
  transition: all 0.3s;
}

.drawer-close-btn:hover {
  color: #409eff;
  border-color: #409eff;
}

.drawer-content {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.slider-container {
  width: 100%;
}

.slider-hint {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  line-height: 1.5;
}

.tts-slider {
  width: 100%;
}

.tts-slider ::v-deep .el-slider__input {
  width: 80px;
}

.tts-slider ::v-deep .el-input__inner {
  text-align: center;
  padding: 0 8px;
}

.drawer-footer {
  padding: 16px 24px;
  border-top: 1px solid #e8f0ff;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.drawer-footer .el-button {
  min-width: 80px;
}

::v-deep .el-form-item__label {
  font-size: 14px !important;
  color: #3d4566 !important;
  font-weight: 500;
  padding-bottom: 8px;
}

::v-deep .el-form-item {
  margin-bottom: 24px;
}
</style>

<style>
.tts-advanced-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 0;
}

.tts-advanced-drawer .el-drawer__body {
  display: flex;
  flex-direction: column;
  padding: 0;
}
</style>
