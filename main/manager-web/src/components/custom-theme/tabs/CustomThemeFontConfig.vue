<template>
  <div class="font-config-wrapper">
    <div class="config-header">
      <h3 class="config-title">{{ $t('device.customThemeFontTab') }}</h3>
      <p class="config-desc">{{ $t('device.customThemeFontDesc') }}</p>
    </div>

    <div class="type-switch">
      <el-button-group>
        <el-button :type="modelValue.type === 'preset' ? 'primary' : 'default'" @click="setFontType('preset')">
          {{ $t('device.customThemePresetFont') }}
        </el-button>
        <el-button :type="modelValue.type === 'custom' ? 'primary' : 'default'" @click="setFontType('custom')">
          {{ $t('device.customThemeCustomFont') }}
        </el-button>
      </el-button-group>
    </div>

    <div v-if="modelValue.type === 'preset'" class="preset-grid">
      <div
        v-for="font in presetFonts"
        :key="font.id"
        class="preset-card"
        :class="{ active: modelValue.preset === font.id }"
        @click="selectPresetFont(font.id)"
      >
        <div class="preset-header">
          <div>
            <h4 class="preset-name">{{ font.name }}</h4>
            <div class="preset-details">
              <div>{{ $t('device.customThemeFontSize') }}: {{ font.size }}px</div>
              <div>{{ $t('device.customThemeFontBpp') }}: {{ font.bpp }}bpp</div>
              <div>{{ $t('device.customThemeFontCharset') }}: {{ font.charset }}</div>
              <div>{{ $t('device.customThemeFontFileSize') }}: {{ font.fileSize }}</div>
            </div>
          </div>
          <div v-if="modelValue.preset === font.id" class="preset-check"><i class="el-icon-check"></i></div>
        </div>
      </div>
    </div>

    <div v-if="modelValue.type === 'custom'" class="custom-upload">
      <div class="upload-area" @click="triggerFile">
        <input ref="fileInput" type="file" accept=".ttf,.woff,.woff2" class="hidden-input" @change="handleFile">
        <div v-if="!modelValue.custom.file" class="upload-placeholder">
          <i class="el-icon-upload"></i>
          <p>{{ $t('device.customThemeFontUploadText') }}</p>
          <p class="hint">{{ $t('device.customThemeFontUploadTip') }}</p>
        </div>
        <div v-else class="upload-success">
          <i class="el-icon-success"></i>
          <div class="file-name">{{ modelValue.custom.name }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CustomThemeFontConfig',
  props: {
    value: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      presetFonts: [
        { id: 'puhui-14', name: '阿里巴巴普惠体 14px', size: 14, bpp: 1, charset: 'DeepSeek', fileSize: '266 KB' },
        { id: 'puhui-16', name: '阿里巴巴普惠体 16px', size: 16, bpp: 4, charset: 'DeepSeek', fileSize: '844 KB' },
        { id: 'puhui-20', name: '阿里巴巴普惠体 20px', size: 20, bpp: 4, charset: 'DeepSeek', fileSize: '1.2 MB' },
        { id: 'puhui-30', name: '阿里巴巴普惠体 30px', size: 30, bpp: 4, charset: 'DeepSeek', fileSize: '2.5 MB' }
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
    }
  },
  methods: {
    setFontType(type) {
      this.modelValue = {
        ...this.modelValue,
        type,
        preset: type === 'preset' ? this.modelValue.preset : '',
        custom: type === 'custom' ? this.modelValue.custom : { file: null, name: '' }
      };
    },
    selectPresetFont(id) {
      this.modelValue = { ...this.modelValue, type: 'preset', preset: id, custom: { file: null, name: '' } };
    },
    triggerFile() {
      this.$refs.fileInput && this.$refs.fileInput.click();
    },
    handleFile(e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      if (!/\.(ttf|woff|woff2)$/i.test(file.name)) {
        this.$message.warning(this.$t('device.customThemeFontInvalidFile'));
        return;
      }
      this.modelValue = { ...this.modelValue, type: 'custom', preset: '', custom: { file, name: file.name } };
    }
  }
};
</script>

<style scoped>
.font-config-wrapper {
  padding: 8px 4px;
  text-align: left;
}
.config-header {
  margin-bottom: 12px;
}
.config-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
}
.config-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.type-switch {
  margin: 10px 0 14px;
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
  transition: all 0.2s;
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
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}
.preset-details {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}
.preset-check {
  width: 20px;
  height: 20px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.custom-upload {
  margin-top: 10px;
}
.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
}
.hidden-input {
  display: none;
}
.upload-placeholder {
  color: #6b7280;
}
.upload-placeholder .hint {
  font-size: 12px;
  color: #9ca3af;
}
.upload-success {
  color: #10b981;
  font-size: 14px;
}
.file-name {
  margin-top: 6px;
}
</style>

