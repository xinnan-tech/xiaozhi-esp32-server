<template>
  <div class="chip-config-wrapper">
    <div class="config-header">
      <h2 class="config-title">{{ $t('device.customThemeStep1') }}</h2>
      <p class="config-desc">{{ $t('device.customThemeChipConfigDesc') }}</p>
    </div>

    <div class="section">
      <h3 class="section-title">{{ $t('device.customThemePresetConfig') }}</h3>
      <div class="preset-grid">
        <div
          v-for="preset in presetConfigs"
          :key="preset.id"
          class="preset-card"
          :class="{ active: modelValue.preset === preset.id }"
          @click="selectPreset(preset)"
        >
          <div class="preset-header">
            <div class="preset-info">
              <h4 class="preset-name">{{ preset.name }}</h4>
              <div class="preset-details">
                <div>{{ $t('device.customThemeChip') }}: {{ preset.chip }}</div>
                <div>{{ $t('device.customThemeResolution') }}: {{ preset.display.width }}×{{ preset.display.height }}</div>
                <div>{{ $t('device.customThemeColor') }}: {{ preset.display.color }}</div>
              </div>
            </div>
            <div v-if="modelValue.preset === preset.id" class="preset-check">
              <i class="el-icon-check"></i>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <h3 class="section-title">{{ $t('device.customThemeCustomConfig') }}</h3>
      <div class="custom-card" :class="{ active: isCustom }" @click="enableCustomConfig">
        <div class="custom-header">
          <h4 class="custom-name">{{ $t('device.customThemeCustomHardware') }}</h4>
          <div v-if="isCustom" class="custom-check">
            <i class="el-icon-check"></i>
          </div>
        </div>
        <div v-if="isCustom" class="custom-form" @click.stop>
          <div class="custom-form-grid">
            <div class="form-item">
              <label class="form-label">{{ $t('device.customThemeChipModel') }}</label>
              <el-select v-model="customConfig.model" :placeholder="$t('device.customThemeSelectChip')" @change="handleCustomConfigChange">
                <el-option label="ESP32-S3" value="esp32s3" />
                <el-option label="ESP32-C3" value="esp32c3" />
                <el-option label="ESP32-P4" value="esp32p4" />
                <el-option label="ESP32-C6" value="esp32c6" />
              </el-select>
            </div>
            <div class="form-item">
              <label class="form-label">{{ $t('device.customThemeScreenWidth') }}</label>
              <el-input-number
                v-model="customConfig.display.width"
                :min="128"
                :max="800"
                placeholder="320"
                @change="handleCustomConfigChange"
              />
            </div>
            <div class="form-item">
              <label class="form-label">{{ $t('device.customThemeScreenHeight') }}</label>
              <el-input-number
                v-model="customConfig.display.height"
                :min="128"
                :max="600"
                placeholder="240"
                @change="handleCustomConfigChange"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="hasValidConfig" class="preview-card">
      <h4 class="preview-title">{{ $t('device.customThemeCurrentConfig') }}</h4>
      <div class="preview-content">
        <div>{{ $t('device.customThemeChipModel') }}: {{ currentChipModel }}</div>
        <div>{{ $t('device.customThemeResolution') }}: {{ currentDisplay.width }}×{{ currentDisplay.height }}</div>
        <div>{{ $t('device.customThemeColor') }}: {{ currentDisplay.color }}</div>
      </div>
    </div>

    <div class="action-buttons">
      <el-button type="primary" :disabled="!hasValidConfig" @click="handleNext">
        {{ $t('device.customThemeNext') }}
      </el-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CustomThemeChipConfig',
  props: {
    value: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      isCustom: false,
      customConfig: {
        model: '',
        display: { width: 320, height: 240, color: 'RGB565' }
      },
      presetConfigs: [
        { id: 'lichuang-dev', name: '立创·实战派 ESP32-S3', chip: 'ESP32-S3', display: { width: 320, height: 240, color: 'RGB565' } },
        { id: 'xingzhi-cube-1.54tft-wifi', name: '无名科技·星智 1.54 TFT', chip: 'ESP32-S3', display: { width: 240, height: 240, color: 'RGB565' } },
        { id: 'atoms3r-echo-base', name: 'AtomS3R Echo Base', chip: 'ESP32-S3', display: { width: 128, height: 128, color: 'RGB565' } },
        { id: 'surfer-c3-1.14tft', name: 'Surfer C3 1.14 TFT', chip: 'ESP32-C3', display: { width: 240, height: 135, color: 'RGB565' } }
      ]
    };
  },
  computed: {
    modelValue: {
      get() {
        return this.value;
      },
      set(val) {
        this.$emit('input', val);
      }
    },
    hasValidConfig() {
      if (this.modelValue.preset) return true;
      return this.customConfig.model && this.customConfig.display.width && this.customConfig.display.height;
    },
    currentChipModel() {
      if (this.modelValue.preset) {
        const preset = this.presetConfigs.find(p => p.id === this.modelValue.preset);
        return preset ? preset.chip : '';
      }
      return this.customConfig.model || '';
    },
    currentDisplay() {
      if (this.modelValue.preset) {
        const preset = this.presetConfigs.find(p => p.id === this.modelValue.preset);
        return preset ? preset.display : {};
      }
      return this.customConfig.display;
    }
  },
  watch: {
    'modelValue.preset'(val) {
      if (val) this.isCustom = false;
    },
    'modelValue.model'(val) {
      if (val && !this.modelValue.preset) this.isCustom = true;
    }
  },
  mounted() {
    if (this.modelValue.preset) {
      this.isCustom = false;
    } else if (this.modelValue.model) {
      this.isCustom = true;
      this.customConfig.model = this.modelValue.model;
      if (this.modelValue.display) this.customConfig.display = { ...this.modelValue.display };
    }
  },
  methods: {
    selectPreset(preset) {
      this.isCustom = false;
      this.modelValue = { model: preset.chip.toLowerCase().replace('esp32-', 'esp32'), display: { ...preset.display }, preset: preset.id };
    },
    enableCustomConfig() {
      if (!this.isCustom) {
        this.isCustom = true;
        this.modelValue = { model: this.customConfig.model, display: { ...this.customConfig.display }, preset: '' };
      }
    },
    handleCustomConfigChange() {
      if (this.isCustom) {
        this.modelValue = { model: this.customConfig.model, display: { ...this.customConfig.display }, preset: '' };
      }
    },
    handleNext() {
      if (this.hasValidConfig) this.$emit('next');
      else this.$message.warning(this.$t('device.customThemeInvalidConfig'));
    }
  }
};
</script>

<style scoped>
.chip-config-wrapper {
  padding: 10px 6px;
  text-align: left;
}
.config-header {
  margin-bottom: 16px;
}
.config-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 6px;
}
.config-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.section {
  margin-bottom: 20px;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.preset-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}
.preset-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}
.preset-header {
  display: flex;
  justify-content: space-between;
}
.preset-name {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 6px;
}
.preset-details {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}
.preset-check {
  width: 22px;
  height: 22px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
}
.custom-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  text-align: left;
  transition: all 0.2s ease;
}
.custom-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}
.custom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.custom-name {
  font-size: 14px;
  font-weight: 600;
}
.custom-check {
  width: 22px;
  height: 22px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
}
.custom-form {
  margin-top: 10px;
}
.custom-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.custom-form-grid :deep(.el-select),
.custom-form-grid :deep(.el-input-number) {
  width: 100%;
}
.form-item {
  display: flex;
  flex-direction: column;
}
.form-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.preview-card {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 10px;
}
.preview-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
}
.preview-content {
  font-size: 13px;
  color: #1e3a8a;
  line-height: 1.6;
}
.action-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>

