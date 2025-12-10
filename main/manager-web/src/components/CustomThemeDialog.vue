<template>
  <el-dialog
    :visible.sync="dialogVisible"
    width="80%"
    custom-class="custom-theme-dialog"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="dialog-header">
      <h3 class="dialog-title">{{ $t('device.customThemeDialogTitle') }}</h3>
      <p class="dialog-desc">{{ device ? device.macAddress : '' }}</p>
    </div>

    <div class="step-indicator">
      <div class="step-line"></div>
      <div
        v-for="step in steps"
        :key="step.id"
        class="step-dot"
        :class="{ active: currentStep === step.id, done: currentStep > step.id }"
      >
        <div class="dot-number">{{ step.id }}</div>
        <div class="dot-title">{{ step.title }}</div>
      </div>
    </div>

    <div class="step-content">
      <CustomThemeChipConfig
        v-if="currentStep === 1"
        v-model="config.chip"
        @next="nextStep"
      />
      <CustomThemeDesign
        v-else-if="currentStep === 2"
        v-model="config.theme"
        :chip-model="config.chip.model"
        :chip-display="config.chip.display"
        @next="nextStep"
        @prev="prevStep"
      />
      <CustomThemeSummary
        v-else
        :config="config"
        @prev="prevStep"
        @generate="handleGenerate"
      />
    </div>
  </el-dialog>
</template>

<script>
import CustomThemeChipConfig from './custom-theme/CustomThemeChipConfig.vue';
import CustomThemeDesign from './custom-theme/CustomThemeDesign.vue';
import CustomThemeSummary from './custom-theme/CustomThemeSummary.vue';

export default {
  name: 'CustomThemeDialog',
  components: {
    CustomThemeChipConfig,
    CustomThemeDesign,
    CustomThemeSummary
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    device: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      currentStep: 1,
      config: {
        chip: {
          model: '',
          display: { width: 320, height: 240, color: 'RGB565' },
          preset: ''
        },
        theme: {
          wakeword: '',
          font: {
            type: 'preset',
            preset: '',
            custom: { file: null, name: '' }
          },
          emoji: {
            type: 'preset',
            preset: '',
            custom: { images: {} }
          },
          skin: {
            defaultMode: 'light',
            light: { backgroundType: 'color', backgroundColor: '#ffffff', textColor: '#000000', backgroundImage: '' },
            dark: { backgroundType: 'color', backgroundColor: '#121212', textColor: '#ffffff', backgroundImage: '' }
          }
        }
      }
    };
  },
  computed: {
    dialogVisible: {
      get() {
        return this.visible;
      },
      set(val) {
        this.$emit('update:visible', val);
      }
    },
    steps() {
      return [
        { id: 1, title: this.$t('device.customThemeStep1'), desc: this.$t('device.customThemeChipConfigDesc') },
        { id: 2, title: this.$t('device.customThemeStep2'), desc: this.$t('device.customThemeDesignDesc') },
        { id: 3, title: this.$t('device.customThemeStep3'), desc: this.$t('device.customThemeSummaryDesc') }
      ];
    }
  },
  methods: {
    nextStep() {
      if (this.currentStep < 3) this.currentStep += 1;
    },
    prevStep() {
      if (this.currentStep > 1) this.currentStep -= 1;
    },
    handleGenerate() {
      // 通过事件通知父组件打开生成模态框
      this.$emit('generate', this.config);
    },
    handleClose() {
      this.dialogVisible = false;
      this.currentStep = 1;
    }
  }
};
</script>

<style scoped>
.custom-theme-dialog ::v-deep .el-dialog__header {
  padding: 4px 16px 0;
  text-align: center;
}
.custom-theme-dialog ::v-deep .el-dialog__body {
  padding: 4px 16px 14px;
}
.dialog-header {
  margin: 0 0 8px;
  text-align: center;
}
.dialog-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
}
.dialog-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.step-indicator {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 6px 12px;
  padding: 6px 0 2px;
}
.step-line {
  position: absolute;
  top: 20px;
  left: 0;
  right: 0;
  height: 4px;
  background: #e5e7eb;
  border-radius: 4px;
  z-index: 1;
}
.step-dot {
  position: relative;
  z-index: 2;
  text-align: center;
  flex: 1;
}
.step-dot:not(:last-child) {
  margin-right: 8px;
}
.dot-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  margin: 0 auto 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e5e7eb;
  color: #374151;
  font-weight: 600;
  transition: all 0.2s ease;
}
.dot-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}
.step-dot.active .dot-number {
  background: #409eff;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.15);
}
.step-dot.done .dot-number {
  background: #67c23a;
  color: #fff;
}
.step-dot.done .dot-title {
  color: #1f2937;
}
.step-content {
  min-height: 420px;
}
</style>
