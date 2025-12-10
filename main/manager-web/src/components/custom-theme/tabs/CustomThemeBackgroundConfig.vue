<template>
  <div class="bg-config-wrapper">
    <div class="config-header">
      <h3 class="config-title">{{ $t('device.customThemeBackgroundTab') }}</h3>
      <p class="config-desc">{{ $t('device.customThemeBackgroundDesc') }}</p>
    </div>

    <div class="mode-row">
      <!-- Light mode -->
      <div class="mode-section">
        <h4 class="mode-title">{{ $t('device.customThemeLightMode') }}</h4>
        <div class="mode-card">
          <div class="mode-buttons">
            <el-button :type="modelValue.light.backgroundType === 'color' ? 'primary' : 'default'" size="mini" @click="setLightType('color')">
              {{ $t('device.customThemeColorBackground') }}
            </el-button>
            <el-button :type="modelValue.light.backgroundType === 'image' ? 'primary' : 'default'" size="mini" @click="setLightType('image')">
              {{ $t('device.customThemeImageBackground') }}
            </el-button>
          </div>

          <div class="color-row">
            <div class="color-stack">
              <div class="color-item">
                <label>{{ $t('device.customThemeBackgroundColor') }}</label>
                <div class="picker-wrap" :class="{ disabled: modelValue.light.backgroundType === 'image' }">
                  <el-color-picker
                    v-model="lightColor"
                    @change="handlePickerChange('light', 'bg')"
                    :disabled="modelValue.light.backgroundType === 'image'"
                  />
                  <el-input
                    class="hex-input"
                    size="mini"
                    v-model="lightColorInput"
                  @input="(val) => handleHexInput('light', 'bg', val)"
                    placeholder="#ffffff"
                    :disabled="modelValue.light.backgroundType === 'image'"
                  />
                  <span class="swatch" :style="{ backgroundColor: lightColor }"></span>
                </div>
              </div>

              <div class="color-item">
                <label>{{ $t('device.customThemeTextColor') }}</label>
                <div class="picker-wrap">
                  <el-color-picker v-model="lightTextColor" @change="handlePickerChange('light', 'text')" />
                  <el-input
                    class="hex-input"
                    size="mini"
                    v-model="lightTextColorInput"
                  @input="(val) => handleHexInput('light', 'text', val)"
                    placeholder="#000000"
                  />
                  <span class="swatch" :style="{ backgroundColor: lightTextColor }"></span>
                </div>
              </div>
            </div>

            <div v-if="modelValue.light.backgroundType === 'image'" class="upload-center">
              <div class="upload-side">
                <div v-if="!modelValue.light.backgroundImage" class="upload-wrapper">
                  <el-upload
                    class="dashed-upload"
                    action=""
                    :auto-upload="false"
                    :on-change="(f)=>handleBgUpload(f, 'light')"
                    accept=".png,.jpg,.jpeg"
                    :show-file-list="false"
                    drag
                  >
                    <i class="el-icon-upload"></i>
                    <div class="el-upload__text">{{ $t('device.customThemeBackgroundImageUpload') }}</div>
                  </el-upload>
                </div>
                <div v-else class="preview-wrapper">
                  <img 
                    :src="modelValue.light.backgroundImage" 
                    alt="背景预览"
                    class="preview-image"
                  />
                  <div class="preview-overlay">
                    <el-button 
                      size="mini" 
                      type="text" 
                      icon="el-icon-refresh"
                      @click="triggerReupload('light')"
                      class="preview-btn"
                    >
                      {{ $t('device.customThemeBackgroundImageUpload') }}
                    </el-button>
                    <el-button 
                      size="mini" 
                      type="text" 
                      icon="el-icon-delete"
                      @click="clearBg('light')"
                      class="preview-btn"
                    >
                      {{ $t('device.customThemeRemoveImage') }}
                    </el-button>
                  </div>
                  <input
                    ref="lightFileInput"
                    type="file"
                    accept=".png,.jpg,.jpeg"
                    style="display: none"
                    @change="(e) => handleFileInputChange(e, 'light')"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Dark mode -->
      <div class="mode-section">
        <h4 class="mode-title">{{ $t('device.customThemeDarkMode') }}</h4>
        <div class="mode-card">
          <div class="mode-buttons">
            <el-button :type="modelValue.dark.backgroundType === 'color' ? 'primary' : 'default'" size="mini" @click="setDarkType('color')">
              {{ $t('device.customThemeColorBackground') }}
            </el-button>
            <el-button :type="modelValue.dark.backgroundType === 'image' ? 'primary' : 'default'" size="mini" @click="setDarkType('image')">
              {{ $t('device.customThemeImageBackground') }}
            </el-button>
          </div>

          <div class="color-row">
            <div class="color-stack">
              <div class="color-item">
                <label>{{ $t('device.customThemeBackgroundColor') }}</label>
                <div class="picker-wrap" :class="{ disabled: modelValue.dark.backgroundType === 'image' }">
                  <el-color-picker
                    v-model="darkColor"
                    @change="handlePickerChange('dark', 'bg')"
                    :disabled="modelValue.dark.backgroundType === 'image'"
                  />
                  <el-input
                    class="hex-input"
                    size="mini"
                    v-model="darkColorInput"
                    @input="(val) => handleHexInput('dark', 'bg', val)"
                    placeholder="#121212"
                    :disabled="modelValue.dark.backgroundType === 'image'"
                  />
                  <span class="swatch" :style="{ backgroundColor: darkColor }"></span>
                </div>
              </div>

              <div class="color-item">
                <label>{{ $t('device.customThemeTextColor') }}</label>
                <div class="picker-wrap">
                  <el-color-picker v-model="darkTextColor" @change="handlePickerChange('dark', 'text')" />
                  <el-input
                    class="hex-input"
                    size="mini"
                    v-model="darkTextColorInput"
                    @input="(val) => handleHexInput('dark', 'text', val)"
                    placeholder="#ffffff"
                  />
                  <span class="swatch" :style="{ backgroundColor: darkTextColor }"></span>
                </div>
              </div>
            </div>

            <div v-if="modelValue.dark.backgroundType === 'image'" class="upload-center">
              <div class="upload-side">
                <div v-if="!modelValue.dark.backgroundImage" class="upload-wrapper">
                  <el-upload
                    class="dashed-upload"
                    action=""
                    :auto-upload="false"
                    :on-change="(f)=>handleBgUpload(f, 'dark')"
                    accept=".png,.jpg,.jpeg"
                    :show-file-list="false"
                    drag
                  >
                    <i class="el-icon-upload"></i>
                    <div class="el-upload__text">{{ $t('device.customThemeBackgroundImageUpload') }}</div>
                  </el-upload>
                </div>
                <div v-else class="preview-wrapper">
                  <img 
                    :src="modelValue.dark.backgroundImage" 
                    alt="背景预览"
                    class="preview-image"
                  />
                  <div class="preview-overlay">
                    <el-button 
                      size="mini" 
                      type="text" 
                      icon="el-icon-refresh"
                      @click="triggerReupload('dark')"
                      class="preview-btn"
                    >
                      {{ $t('device.customThemeBackgroundImageUpload') }}
                    </el-button>
                    <el-button 
                      size="mini" 
                      type="text" 
                      icon="el-icon-delete"
                      @click="clearBg('dark')"
                      class="preview-btn"
                    >
                      {{ $t('device.customThemeRemoveImage') }}
                    </el-button>
                  </div>
                  <input
                    ref="darkFileInput"
                    type="file"
                    accept=".png,.jpg,.jpeg"
                    style="display: none"
                    @change="(e) => handleFileInputChange(e, 'dark')"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览区域 -->
    <div class="preview-section">
      <h4 class="preview-title">{{ $t('device.customThemeBackgroundPreview') }}</h4>
      <div class="preview-grid">
        <div class="preview-card">
          <div class="preview-label">
            <span class="mode-icon">☀️</span>
            <span>{{ $t('device.customThemeLightMode').replace('背景', '') }}</span>
          </div>
          <div class="preview-box" :style="lightPreviewStyle">
            <span class="preview-text" :style="{ color: modelValue.light.textColor }">聊天内容区域</span>
          </div>
        </div>
        <div class="preview-card">
          <div class="preview-label">
            <span class="mode-icon">🌙</span>
            <span>{{ $t('device.customThemeDarkMode').replace('背景', '') }}</span>
          </div>
          <div class="preview-box" :style="darkPreviewStyle">
            <span class="preview-text" :style="{ color: modelValue.dark.textColor }">聊天内容区域</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷配置 -->
    <div class="quick-section">
      <h5 class="quick-title">{{ $t('device.customThemeQuickConfig') }}</h5>
      <div class="quick-list">
        <el-button
          size="mini"
          @click="applyPreset('#ffffff', '#1f2937', '#111827', '#e5e7eb')"
          :style="{ backgroundColor: '#ffffff', color: '#1f2937', borderColor: '#e5e7eb' }"
        >默认配色</el-button>
        <el-button
          size="mini"
          @click="applyPreset('#f5f5f4', '#374151', '#0f172a', '#e5e7eb')"
          :style="{ backgroundColor: '#f5f5f4', color: '#374151', borderColor: '#e5e7eb' }"
        >石墨质感</el-button>
        <el-button
          size="mini"
          @click="applyPreset('#fef7cd', '#7c2d12', '#78350f', '#f3f4f6')"
          :style="{ backgroundColor: '#fef7cd', color: '#7c2d12', borderColor: '#e5e7eb' }"
        >暖阳配色</el-button>
        <el-button
          size="mini"
          @click="applyPreset('#e0f2fe', '#1e40af', '#0f172a', '#e2e8f0')"
          :style="{ backgroundColor: '#e0f2fe', color: '#1e40af', borderColor: '#e5e7eb' }"
        >天空蓝调</el-button>
        <el-button
          size="mini"
          @click="applyPreset('#fdf2f8', '#be185d', '#3b082f', '#fdf2f8')"
          :style="{ backgroundColor: '#fdf2f8', color: '#be185d', borderColor: '#e5e7eb' }"
        >浪漫粉色</el-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CustomThemeBackgroundConfig',
  props: {
    value: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      lightColor: this.value.light.backgroundColor || '#ffffff',
      lightTextColor: this.value.light.textColor || '#000000',
      darkColor: this.value.dark.backgroundColor || '#121212',
      darkTextColor: this.value.dark.textColor || '#ffffff',
      lightColorInput: this.value.light.backgroundColor || '#ffffff',
      lightTextColorInput: this.value.light.textColor || '#000000',
      darkColorInput: this.value.dark.backgroundColor || '#121212',
      darkTextColorInput: this.value.dark.textColor || '#ffffff'
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
    lightPreviewStyle() {
      if (this.modelValue.light.backgroundType === 'image' && this.modelValue.light.backgroundImage) {
        return {
          backgroundImage: `url(${this.modelValue.light.backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        };
      }
      return {
        backgroundColor: this.modelValue.light.backgroundColor
      };
    },
    darkPreviewStyle() {
      if (this.modelValue.dark.backgroundType === 'image' && this.modelValue.dark.backgroundImage) {
        return {
          backgroundImage: `url(${this.modelValue.dark.backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        };
      }
      return {
        backgroundColor: this.modelValue.dark.backgroundColor
      };
    }
  },
  methods: {
    setLightType(type) {
      this.modelValue = { ...this.modelValue, light: { ...this.modelValue.light, backgroundType: type } };
    },
    setDarkType(type) {
      this.modelValue = { ...this.modelValue, dark: { ...this.modelValue.dark, backgroundType: type } };
    },
    emitLightColor() {
      this.modelValue = {
        ...this.modelValue,
        light: { ...this.modelValue.light, backgroundColor: this.lightColor, textColor: this.lightTextColor }
      };
    },
    emitDarkColor() {
      this.modelValue = {
        ...this.modelValue,
        dark: { ...this.modelValue.dark, backgroundColor: this.darkColor, textColor: this.darkTextColor }
      };
    },
    handlePickerChange(mode, type) {
      if (mode === 'light' && type === 'bg') {
        this.lightColorInput = this.lightColor;
        this.emitLightColor();
      } else if (mode === 'light' && type === 'text') {
        this.lightTextColorInput = this.lightTextColor;
        this.emitLightColor();
      } else if (mode === 'dark' && type === 'bg') {
        this.darkColorInput = this.darkColor;
        this.emitDarkColor();
      } else if (mode === 'dark' && type === 'text') {
        this.darkTextColorInput = this.darkTextColor;
        this.emitDarkColor();
      }
    },
    handleHexInput(mode, type, val) {
      const raw = (val || '').trim();
      if (!/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(raw)) {
        // 无效色值，忽略，不弹窗
        return;
      }
      const norm = raw.toLowerCase();
      if (mode === 'light' && type === 'bg') {
        this.lightColor = norm;
        this.lightColorInput = norm;
        this.emitLightColor();
      } else if (mode === 'light' && type === 'text') {
        this.lightTextColor = norm;
        this.lightTextColorInput = norm;
        this.emitLightColor();
      } else if (mode === 'dark' && type === 'bg') {
        this.darkColor = norm;
        this.darkColorInput = norm;
        this.emitDarkColor();
      } else if (mode === 'dark' && type === 'text') {
        this.darkTextColor = norm;
        this.darkTextColorInput = norm;
        this.emitDarkColor();
      }
    },
    handleBgUpload(file, mode) {
      const f = file.raw;
      if (!f || !/\.(png|jpg|jpeg)$/i.test(f.name)) {
        this.$message.warning(this.$t('device.customThemeInvalidImageFile'));
        return false;
      }
      const url = URL.createObjectURL(f);
      // 同时保存 File 对象和 URL，以便后续处理
      if (mode === 'light') {
        this.modelValue = { 
          ...this.modelValue, 
          light: { 
            ...this.modelValue.light, 
            backgroundImage: url, 
            backgroundImageFile: f, // 保存原始 File 对象
            backgroundType: 'image' 
          } 
        };
      } else {
        this.modelValue = { 
          ...this.modelValue, 
          dark: { 
            ...this.modelValue.dark, 
            backgroundImage: url, 
            backgroundImageFile: f, // 保存原始 File 对象
            backgroundType: 'image' 
          } 
        };
      }
      return false;
    },
    clearBg(mode) {
      if (mode === 'light') {
        // 释放 blob URL
        if (this.modelValue.light.backgroundImage && this.modelValue.light.backgroundImage.startsWith('blob:')) {
          URL.revokeObjectURL(this.modelValue.light.backgroundImage)
        }
        this.modelValue = { 
          ...this.modelValue, 
          light: { 
            ...this.modelValue.light, 
            backgroundImage: '', 
            backgroundImageFile: null, // 清除 File 对象
            backgroundType: 'color' 
          } 
        };
      } else {
        // 释放 blob URL
        if (this.modelValue.dark.backgroundImage && this.modelValue.dark.backgroundImage.startsWith('blob:')) {
          URL.revokeObjectURL(this.modelValue.dark.backgroundImage)
        }
        this.modelValue = { 
          ...this.modelValue, 
          dark: { 
            ...this.modelValue.dark, 
            backgroundImage: '', 
            backgroundImageFile: null, // 清除 File 对象
            backgroundType: 'color' 
          } 
        };
      }
    },
    triggerReupload(mode) {
      // 触发文件选择
      const inputRef = mode === 'light' ? this.$refs.lightFileInput : this.$refs.darkFileInput
      if (inputRef) {
        inputRef.click()
      }
    },
    handleFileInputChange(event, mode) {
      const file = event.target.files?.[0]
      if (file && /\.(png|jpg|jpeg)$/i.test(file.name)) {
        // 释放旧的 blob URL
        if (mode === 'light' && this.modelValue.light.backgroundImage && this.modelValue.light.backgroundImage.startsWith('blob:')) {
          URL.revokeObjectURL(this.modelValue.light.backgroundImage)
        } else if (mode === 'dark' && this.modelValue.dark.backgroundImage && this.modelValue.dark.backgroundImage.startsWith('blob:')) {
          URL.revokeObjectURL(this.modelValue.dark.backgroundImage)
        }
        
        // 创建新的 blob URL 并保存 File 对象
        const url = URL.createObjectURL(file)
        if (mode === 'light') {
          this.modelValue = {
            ...this.modelValue,
            light: {
              ...this.modelValue.light,
              backgroundImage: url,
              backgroundImageFile: file,
              backgroundType: 'image'
            }
          }
        } else {
          this.modelValue = {
            ...this.modelValue,
            dark: {
              ...this.modelValue.dark,
              backgroundImage: url,
              backgroundImageFile: file,
              backgroundType: 'image'
            }
          }
        }
      }
      // 清空 input，以便可以再次选择同一文件
      event.target.value = ''
    },
    fileName(url) {
      if (!url) return '';
      const parts = url.split('/');
      return parts[parts.length - 1];
    },
    applyPreset(lightBg, lightText, darkBg, darkText) {
      this.lightColor = lightBg;
      this.lightTextColor = lightText;
      this.darkColor = darkBg;
      this.darkTextColor = darkText;
      this.lightColorInput = lightBg;
      this.lightTextColorInput = lightText;
      this.darkColorInput = darkBg;
      this.darkTextColorInput = darkText;
      this.modelValue = {
        ...this.modelValue,
        light: { ...this.modelValue.light, backgroundType: 'color', backgroundColor: lightBg, textColor: lightText, backgroundImage: '' },
        dark: { ...this.modelValue.dark, backgroundType: 'color', backgroundColor: darkBg, textColor: darkText, backgroundImage: '' }
      };
    }
  }
};
</script>

<style scoped>
.bg-config-wrapper {
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
.mode-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.mode-section {
  height: 100%;
}
.mode-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}
.mode-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
.mode-buttons {
  margin-bottom: 10px;
}
.color-row,
.upload-row {
  display: flex;
  align-items: stretch;
  gap: 12px;
  flex-wrap: nowrap;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
.color-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  flex: 0 0 auto;
  max-width: 100%;
}
.upload-center {
  display: flex;
  flex: 0 0 auto;
  justify-content: center;
  align-items: center;
  width: 360px;
  min-width: 360px;
  max-width: 360px;
  overflow: visible;
  box-sizing: border-box;
  padding: 0;
}
.color-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.picker-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.picker-wrap.disabled {
  opacity: 0.5;
  pointer-events: none;
}
.hex-input {
  width: 110px;
}
.hex-text {
  font-size: 12px;
  color: #303133;
}
.swatch {
  width: 64px;
  height: 32px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}
.dashed-upload {
  display: flex;
  width: 100%;
  box-sizing: border-box;
  border: none;
  padding: 0;
  justify-content: center;
}
.dashed-upload .el-upload-dragger {
  border: 2px dashed #909399;
  border-radius: 4px;
  padding: 2px 0;
  width: 360px;
  min-width: 360px;
  max-width: 360px;
  height: 180px;
  min-height: 180px;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  flex-shrink: 0;
}
.upload-row .file-name,
.inline-upload .file-name,
.upload-side .file-name {
  font-size: 12px;
  color: #6b7280;
}
.upload-side {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 360px;
  min-width: 360px;
  max-width: 360px;
  flex-shrink: 0;
  flex-grow: 0;
  align-items: center;
  box-sizing: border-box;
  overflow: visible;
}
.upload-wrapper {
  width: 100%;
}
.preview-wrapper {
  position: relative;
  width: 360px !important;
  min-width: 360px !important;
  max-width: 360px !important;
  height: 180px !important;
  min-height: 180px !important;
  border: 2px dashed #909399;
  border-radius: 4px;
  overflow: hidden;
  box-sizing: border-box;
  flex-shrink: 0;
}
.preview-image {
  width: 360px !important;
  height: 180px !important;
  min-width: 360px !important;
  min-height: 180px !important;
  object-fit: cover;
  display: block;
}
.preview-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s;
}
.preview-wrapper:hover .preview-overlay {
  opacity: 1;
}
.preview-btn {
  color: #fff !important;
  padding: 4px 8px;
  font-size: 12px;
}
.dashed-upload .el-upload__text {
  font-size: 12px;
  line-height: 16px;
}
.dashed-upload .el-icon-upload {
  font-size: 20px;
}
.preview-section {
  margin-top: 44px;
  padding-top: 16px;
  border-top: none;
  clear: both;
}
.preview-title {
  margin: 0 0 18px;
  font-size: 14px;
  font-weight: 600;
}
.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.preview-card {
  padding: 0;
}
.preview-label {
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.mode-icon {
  font-size: 14px;
}
.preview-box {
  height: 100px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.preview-text {
  font-size: 13px;
}
.quick-section {
  margin-top: 12px;
  border: 1px solid #dce7ff;
  background: #f5f8ff;
  border-radius: 8px;
  padding: 10px;
}
.quick-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #2c4fa3;
}
.quick-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>

