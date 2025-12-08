<template>
  <div class="summary-wrapper">
    <div class="summary-header">
      <h2 class="summary-title">步骤 3: 效果预览</h2>
      <p class="summary-desc">预览您的自定义配置在实际设备上的效果。</p>
    </div>

    <div class="preview-layout">
      <!-- 设备预览 -->
      <div class="preview-device">
        <h3 class="block-title">设备预览 (1:1 像素比例)</h3>
        <div class="preview-shell">
          <div class="device-shell">
            <div class="device-frame">
              <div class="device-screen" :style="getScreenStyle()">
                <div class="device-bg" :style="getBackgroundStyle()"></div>
                <div class="device-content">
                  <div class="emoji-block" :class="{ overlay: isCustomEmoji }">
                    <div v-if="currentEmoji && displayedEmotions.length > 0 && currentEmojiImage" class="emoji-container">
                      <img
                        :src="currentEmojiImage"
                        :alt="currentEmoji"
                        :style="getEmojiStyle()"
                        class="emoji-image"
                      />
                    </div>
                    <div v-else class="emoji-container empty-placeholder"></div>
                  </div>

                  <div
                    :style="getTextStyle()"
                    class="text-message"
                    :class="{ overlay: isCustomEmoji }"
                  >
                    <div v-if="!fontLoaded" class="loading-font">字体加载中...</div>
                    <div :class="{ 'opacity-0': !fontLoaded }">
                      {{ previewText }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="device-info">
              {{ config.chip.display.width }} × {{ config.chip.display.height }} {{ config.chip.model ? config.chip.model.toUpperCase() : '' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 控制面板 -->
      <div class="control-panel">
        <h3 class="block-title">预览设置</h3>
        <div class="panel-card">
          <div class="panel-item">
            <label class="panel-label">预览文字</label>
            <textarea
              v-model="previewText"
              rows="3"
              class="panel-textarea"
              placeholder="Hi，我是你的好朋友小智！"
            ></textarea>
          </div>

          <div class="panel-item">
            <label class="panel-label">当前表情</label>
            <div v-if="displayedEmotions.length > 0" class="emoji-list">
              <button
                v-for="emotion in displayedEmotions"
                :key="emotion.key"
                @click="changeEmotion(emotion.key)"
                :class="['emoji-button', { active: currentEmoji === emotion.key }]"
                :style="{ width: getEmojiControlSize() + 'px', height: getEmojiControlSize() + 'px' }"
                :title="emotion.name"
              >
                <div v-if="getEmotionImage(emotion.key)">
                  <img
                    :src="getEmotionImage(emotion.key)"
                    :alt="emotion.name"
                    :style="{ width: getEmojiThumbSize() + 'px', height: getEmojiThumbSize() + 'px' }"
                    class="emoji-btn-img"
                  />
                </div>
                <div v-else class="emoji-btn-fallback">{{ emotion.emoji }}</div>
              </button>
            </div>
            <div v-else class="emoji-empty">
              <div class="text-2xl mb-2">😕</div>
              <div class="text-sm">请上传自定义表情</div>
            </div>
          </div>

          <div class="panel-item">
            <label class="panel-label">主题模式</label>
            <div class="mode-switch">
              <button
                @click="themeMode = 'light'"
                :class="['switch-btn', { active: themeMode === 'light' }]"
              >
                🌞 浅色
              </button>
              <button
                @click="themeMode = 'dark'"
                :class="['switch-btn', { active: themeMode === 'dark' }]"
              >
                🌙 深色
              </button>
            </div>
          </div>

          <div class="panel-item summary-box">
            <h4 class="panel-subtitle">配置摘要</h4>
            <div class="summary-lines">
              <div v-if="config.theme.wakeword">唤醒词: {{ getWakewordName() }}</div>
              <div class="flex items-center">
                <span>字体: {{ getFontName() }}</span>
                <span v-if="!fontLoaded" class="loading-dot">加载中...</span>
                <span v-else class="ok-dot">✓</span>
              </div>
              <div>表情: {{ getEmojiName() }}</div>
              <div>皮肤: {{ getSkinName() }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="action-buttons">
      <el-button @click="$emit('prev')">{{ $t('device.customThemePrev') }}</el-button>
      <el-button type="primary" @click="handleGenerate">{{ $t('device.customThemeGenerate') }}</el-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CustomThemeSummary',
  props: {
    config: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      previewText: 'Hi，我是你的好朋友小智！',
      currentEmoji: '',
      themeMode: 'light',
      fontLoaded: true, // 简化处理
      availableEmotions: [
        { key: 'neutral', name: '默认', emoji: '😶' },
        { key: 'happy', name: '开心', emoji: '🙂' },
        { key: 'laughing', name: '大笑', emoji: '😆' },
        { key: 'funny', name: '搞笑', emoji: '😂' },
        { key: 'sad', name: '伤心', emoji: '😔' },
        { key: 'angry', name: '生气', emoji: '😠' },
        { key: 'crying', name: '哭泣', emoji: '😭' },
        { key: 'loving', name: '喜爱', emoji: '😍' },
        { key: 'surprised', name: '惊讶', emoji: '😯' },
        { key: 'thinking', name: '思考', emoji: '🤔' },
        { key: 'cool', name: '酷炫', emoji: '😎' },
        { key: 'sleepy', name: '困倦', emoji: '😴' }
      ]
    };
  },
  computed: {
    currentEmojiImage() {
      return this.getEmotionImage(this.currentEmoji);
    },
    isCustomEmoji() {
      return this.config.theme.emoji && this.config.theme.emoji.type === 'custom';
    },
    displayedEmotions() {
      const emojiCfg = this.config.theme.emoji;
      if (emojiCfg.type === 'custom') {
        const imgs = emojiCfg.custom && emojiCfg.custom.images ? emojiCfg.custom.images : {};
        const keys = Object.keys(imgs);
        return this.availableEmotions.filter((e) => keys.includes(e.key));
      }
      return this.availableEmotions;
    }
  },
  watch: {
    displayedEmotions: {
      handler(list) {
        if (list.length > 0) {
          if (!list.find((e) => e.key === this.currentEmoji)) {
            this.currentEmoji = list[0].key;
          }
        } else {
          this.currentEmoji = '';
        }
      },
      immediate: true
    }
  },
  methods: {
    handleGenerate() {
      this.$emit('generate');
    },
    getScreenStyle() {
      const { width, height } = this.config.chip.display;
      return {
        width: `${width}px`,
        height: `${height}px`
      };
    },
    getBackgroundStyle() {
      const bg = this.config.theme.skin[this.themeMode] || {};
      if (bg.backgroundType === 'image' && bg.backgroundImage) {
        return {
          backgroundImage: `url(${bg.backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        };
      }
      return {
        backgroundColor: bg.backgroundColor || '#ffffff'
      };
    },
    getEmojiStyle() {
      let width = 48;
      let height = 48;
      const emojiCfg = this.config.theme.emoji;
      if (emojiCfg.type === 'preset') {
        const size = emojiCfg.preset === 'twemoji64' ? 64 : 32;
        width = size;
        height = size;
      } else if (emojiCfg.custom && emojiCfg.custom.size) {
        width = emojiCfg.custom.size.width || width;
        height = emojiCfg.custom.size.height || height;
      }
      const min = 16;
      width = Math.max(width, min);
      height = Math.max(height, min);
      const maxW = this.config?.chip?.display?.width || width;
      const maxH = this.config?.chip?.display?.height || height;
      width = Math.min(width, maxW);
      height = Math.min(height, maxH);
      return {
        width: `${width}px`,
        height: `${height}px`,
        maxWidth: `${maxW}px`,
        maxHeight: `${maxH}px`
      };
    },
    getEmojiDisplaySize() {
      const style = this.getEmojiStyle();
      return parseInt(style.width, 10);
    },
    getEmojiControlSize() {
      return this.getEmojiThumbSize() + 8;
    },
    getEmojiThumbSize() {
      const style = this.getEmojiStyle();
      const size = parseInt(style.width, 10);
      return Math.min(Math.max(size, 32), 64);
    },
    getEmotionImage(key) {
      const emojiCfg = this.config.theme.emoji;
      if (emojiCfg.type === 'preset' && emojiCfg.preset) {
        const base = `/static/${emojiCfg.preset}`;
        const file = key === 'neutral' ? 'neutral.png' : `${key}.png`;
        return `${base}/${file}`;
      }
      if (emojiCfg.type === 'custom' && emojiCfg.custom && emojiCfg.custom.images && emojiCfg.custom.images[key]) {
        const img = emojiCfg.custom.images[key];
        if (typeof img === 'string') return img;
        if (img instanceof File || img instanceof Blob) return URL.createObjectURL(img);
        return null;
      }
      return null;
    },
    getEmojiCharacter(key) {
      const found = this.availableEmotions.find((e) => e.key === key);
      return found ? found.emoji : '😶';
    },
    changeEmotion(key) {
      this.currentEmoji = key;
    },
    getTextStyle() {
      const font = this.getFontStyle();
      const textColor = this.themeMode === 'dark'
        ? this.config.theme.skin.dark.textColor
        : this.config.theme.skin.light.textColor;
      return {
        fontSize: font.fontSize,
        fontFamily: font.fontFamily,
        color: textColor,
        textShadow: this.themeMode === 'dark' ? '1px 1px 2px rgba(0,0,0,0.5)' : '1px 1px 2px rgba(255,255,255,0.5)'
      };
    },
    getWakewordName() {
      return this.config.theme.wakeword || this.$t('device.customThemeNotConfigured');
    },
    getFontName() {
      const fontCfg = this.config.theme.font;
      if (fontCfg.type === 'preset') {
        return fontCfg.preset || '-';
      }
      return fontCfg.custom && fontCfg.custom.name ? fontCfg.custom.name : '-';
    },
    getFontStyle() {
      const fontCfg = this.config.theme.font || {};
      let family = 'Alibaba PuHuiTi';
      let size = 16;
      if (fontCfg.type === 'preset' && fontCfg.preset) {
        const match = fontCfg.preset.match(/(\d+)/);
        size = match ? Number(match[1]) : 16;
      } else if (fontCfg.type === 'custom' && fontCfg.custom) {
        if (fontCfg.custom.name) family = fontCfg.custom.name;
        if (fontCfg.custom.size) size = fontCfg.custom.size;
      }
      return {
        fontFamily: `'${family}', sans-serif`,
        fontSize: `${size}px`
      };
    },
    getEmojiName() {
      const emojiCfg = this.config.theme.emoji;
      if (emojiCfg.type === 'preset') {
        return emojiCfg.preset || '-';
      }
      const count = emojiCfg.custom && emojiCfg.custom.images ? Object.keys(emojiCfg.custom.images).length : 0;
      return `${this.$t('device.customThemeEmojiCustom')} (${count})`;
    },
    getSkinName() {
      const light = this.config.theme.skin.light;
      const dark = this.config.theme.skin.dark;
      const lightLabel = `☀️ ${this.$t('device.customThemeLightMode')}`;
      const darkLabel = `🌙 ${this.$t('device.customThemeDarkMode')}`;
      return `${lightLabel} / ${darkLabel}`;
    }
  }
};
</script>

<style scoped>
.summary-wrapper {
  padding: 12px 8px;
  text-align: left;
}
.summary-header {
  margin-bottom: 12px;
}
.summary-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
}
.summary-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.preview-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
@media (min-width: 1024px) {
  .preview-layout {
    flex-direction: row;
    gap: 16px;
  }
}
.preview-device {
  flex: 1 1 0%;
}
.preview-shell {
  background: #eef1f5;
  border: 1px solid #d6d9de;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.control-panel {
  width: 100%;
  max-width: 320px;
}
.block-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
}
.device-shell {
  background: linear-gradient(135deg, #111827, #1f2937);
  border: 1px solid #111827;
  border-radius: 18px;
  padding: 12px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
  display: inline-block;
}
.device-frame {
  display: flex;
  justify-content: center;
  align-items: center;
}
.device-screen {
  position: relative;
  background: #0b0f1a;
  border: 4px solid #2c3340;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
}
.device-bg {
  position: absolute;
  inset: 0;
}
.device-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0;
  text-align: center;
  width: 100%;
  height: 100%;
}
.emoji-block {
  margin-bottom: 10px;
}
.emoji-block.overlay {
  position: absolute;
  inset: 0;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}
.emoji-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  position: relative;
}
.emoji-image {
  object-fit: cover;
  border-radius: 12px;
  max-width: 100%;
  max-height: 100%;
  display: block;
  margin: 0 auto;
  object-position: center center;
}
.emoji-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e5e7eb;
  border-radius: 50%;
  font-size: 20px;
  width: 100%;
}
.emoji-placeholder {
  border: 2px dashed #d1d5db;
  border-radius: 6px;
  background: #f9fafb;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.text-message {
  max-width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.text-message.overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}
.loading-font {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #9ca3af;
}
.device-info {
  margin-top: 6px;
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
}
.control-panel .panel-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  display: grid;
  gap: 12px;
}
.panel-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.panel-label {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.panel-textarea {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
  color: #111827;
  resize: vertical;
}
.emoji-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 140px;
  overflow-y: auto;
  justify-content: flex-start;
}
.emoji-button {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s, background-color 0.2s;
}
.emoji-button.active {
  border-color: #2563eb;
  background: #eff6ff;
}
.emoji-btn-img {
  object-fit: contain;
}
.emoji-btn-fallback {
  font-size: 16px;
}
.emoji-empty {
  text-align: center;
  padding: 12px;
  border: 2px dashed #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  color: #6b7280;
}
.mode-switch {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.switch-btn {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  background: #fff;
  color: #111827;
  transition: all 0.2s;
}
.switch-btn.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}
.summary-lines {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: #374151;
}
.loading-dot {
  margin-left: 6px;
  color: #2563eb;
  font-size: 12px;
}
.ok-dot {
  margin-left: 6px;
  color: #10b981;
  font-size: 12px;
}
.summary-lines .flex {
  display: flex;
  align-items: center;
}
.summary-lines .flex.items-center {
  display: flex;
}
.summary-lines .flex.items-center span + span {
  margin-left: 4px;
}
.panel-subtitle {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.summary-box {
  border-top: 1px solid #e5e7eb;
  padding-top: 8px;
}
.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
</style>

