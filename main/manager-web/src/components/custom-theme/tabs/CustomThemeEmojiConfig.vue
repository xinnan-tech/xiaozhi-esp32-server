<template>
  <div class="emoji-config-wrapper">
    <div class="config-header">
      <h3 class="config-title">{{ $t('device.customThemeEmojiTab') }}</h3>
      <p class="config-desc">选择预设表情包或自定义表情图片。每个表情包包含21种不同情绪的表情。</p>
    </div>

    <div class="type-switch">
      <el-button-group>
        <el-button :type="modelValue.type === 'preset' ? 'primary' : 'default'" @click="setEmojiType('preset')">
          {{ $t('device.customThemePresetEmoji') }}
        </el-button>
        <el-button :type="modelValue.type === 'custom' ? 'primary' : 'default'" @click="setEmojiType('custom')">
          {{ $t('device.customThemeCustomEmoji') }}
        </el-button>
      </el-button-group>
    </div>

    <div v-if="modelValue.type === 'preset'" class="preset-grid">
      <div
        v-for="pack in presetEmojis"
        :key="pack.id"
        class="preset-card"
        :class="{ active: modelValue.preset === pack.id }"
        @click="selectPresetEmoji(pack.id)"
      >
        <div class="preset-header">
          <div>
            <h4 class="preset-name">{{ pack.name }}</h4>
            <p class="preset-desc">{{ pack.description }}</p>
            <div class="preset-meta">{{ $t('device.customThemeEmojiSize') }}: {{ pack.size }}px</div>
          </div>
          <div v-if="modelValue.preset === pack.id" class="preset-check"><i class="el-icon-check"></i></div>
        </div>
        <div class="emoji-preview">
          <div
            v-for="emotion in pack.preview"
            :key="emotion"
            class="emoji-box"
            :style="emojiBoxStyle(pack.size)"
          >
            <img
              :src="getPresetEmojiUrl(pack.id, emotion)"
              :alt="emotion"
              :style="{ width: pack.size + 'px', height: pack.size + 'px' }"
            />
          </div>
        </div>
      </div>
    </div>

    <div v-if="modelValue.type === 'custom'" class="custom-upload">
      <div class="size-row">
        <div class="size-item">
          <label>图片宽度 (px)</label>
          <el-input-number
            v-model="customSize.width"
            :min="16"
            :max="displaySize && displaySize.width ? displaySize.width : 5000"
            @change="updateSize"
            style="width: 100%;"
          />
        </div>
        <div class="size-item">
          <label>图片高度 (px)</label>
          <el-input-number
            v-model="customSize.height"
            :min="16"
            :max="displaySize && displaySize.height ? displaySize.height : 5000"
            @change="updateSize"
            style="width: 100%;"
          />
        </div>
      </div>
      <div class="upload-tip">{{ $t('device.customThemeEmojiUploadTip') }}</div>
      <div class="emoji-grid">
        <div v-for="emotion in emotionList" :key="emotion.key" class="emoji-card">
          <div class="emoji-card-header">
            <span class="emoji-icon">{{ emotion.emoji }}</span>
            <div class="emoji-meta">
              <div class="emoji-name">{{ emotion.name }}</div>
              <div v-if="emotion.key === 'neutral'" class="emoji-required">必需</div>
            </div>
          </div>
          <div
            class="upload-box"
            :class="{
              filled: !!modelValue.custom.images[emotion.key],
              required: emotion.key === 'neutral' && !modelValue.custom.images[emotion.key]
            }"
            @drop.prevent="(e) => handleFileDrop(e, emotion.key)"
            @dragover.prevent
            @dragenter.prevent
            @click="() => triggerInput(emotion.key)"
          >
            <input
              class="hidden-input"
              type="file"
              accept=".png,.gif"
              :ref="emotion.key + 'Input'"
              @change="(e) => handleFileSelect(e, emotion.key)"
            />
            <template v-if="modelValue.custom.images[emotion.key]">
              <img
                :src="getImagePreview(emotion.key)"
                :alt="emotion.name"
                class="emoji-fill"
              />
              <button class="remove-btn" @click.stop="removeImage(emotion.key)">×</button>
            </template>
            <template v-else>
              <div class="upload-text">{{ $t('device.customThemeEmojiClickUpload') }}</div>
            </template>
          </div>
        </div>
      </div>
      <div class="upload-note">
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CustomThemeEmojiConfig',
  props: {
    value: {
      type: Object,
      required: true
    },
    displaySize: {
      type: Object,
      default: () => ({ width: 32, height: 32 })
    }
  },
  data() {
    return {
      presetEmojis: [
        { id: 'twemoji32', name: 'Twemoji 32px', size: 32, description: 'Twitter emoji 32px', preview: ['neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying'] },
        { id: 'twemoji64', name: 'Twemoji 64px', size: 64, description: 'Twitter emoji 64px', preview: ['neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying'] }
      ],
      fileList: [],
      emotionList: [
        { key: 'neutral', name: '默认', emoji: '😶' },
        { key: 'happy', name: '开心', emoji: '🙂' },
        { key: 'laughing', name: '大笑', emoji: '😆' },
        { key: 'funny', name: '搞笑', emoji: '😂' },
        { key: 'sad', name: '伤心', emoji: '😔' },
        { key: 'angry', name: '生气', emoji: '😠' },
        { key: 'crying', name: '哭泣', emoji: '😭' },
        { key: 'loving', name: '喜爱', emoji: '😍' },
        { key: 'embarrassed', name: '尴尬', emoji: '😳' },
        { key: 'surprised', name: '惊讶', emoji: '😯' },
        { key: 'shocked', name: '震惊', emoji: '😱' },
        { key: 'thinking', name: '思考', emoji: '🤔' },
        { key: 'winking', name: '眨眼', emoji: '😉' },
        { key: 'cool', name: '酷炫', emoji: '😎' },
        { key: 'relaxed', name: '放松', emoji: '😌' },
        { key: 'delicious', name: '美味', emoji: '🤤' },
        { key: 'kissy', name: '飞吻', emoji: '😘' },
        { key: 'confident', name: '自信', emoji: '😏' },
        { key: 'sleepy', name: '困倦', emoji: '😴' },
        { key: 'silly', name: '调皮', emoji: '😜' },
        { key: 'confused', name: '困惑', emoji: '🙄' }
      ],
      customSize: { width: 64, height: 64 }
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
    // no-op placeholder
  },
  watch: {
    displaySize: {
      handler() {
        this.syncDisplaySize();
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    getMaxSize() {
      const maxW = this.displaySize?.width || 5000;
      const maxH = this.displaySize?.height || 5000;
      return {
        maxWidth: Math.floor(maxW * 0.7),
        maxHeight: Math.floor(maxH * 0.7)
      };
    },
    setEmojiType(type) {
      console.log('[CustomThemeEmojiConfig] setEmojiType:', type);
      if (type === this.modelValue.type) return;

      if (type === 'preset') {
        const presetId = this.modelValue.preset || 'twemoji32';
        const preset = this.presetEmojis.find((p) => p.id === presetId) || this.presetEmojis[0];
        const size = preset ? { width: preset.size, height: preset.size } : { width: 32, height: 32 };
        this.customSize = { ...size };
        this.modelValue = {
          ...this.modelValue,
          type: 'preset',
          preset: preset ? preset.id : 'twemoji32',
          custom: { images: {}, size: { ...size } }
        };
      } else {
        const baseSize = this.modelValue.custom?.size || this.customSize || { width: 64, height: 64 };
        const { maxWidth, maxHeight } = this.getMaxSize();
        const clamped = {
          width: Math.min(baseSize.width || 32, maxWidth),
          height: Math.min(baseSize.height || 32, maxHeight)
        };
        this.customSize = { ...clamped };
        this.modelValue = {
          ...this.modelValue,
          type: 'custom',
          preset: '',
          custom: { images: { ...(this.modelValue.custom?.images || {}) }, size: { ...clamped } }
        };
      }
    },
    selectPresetEmoji(id) {
      const preset = this.presetEmojis.find(p => p.id === id);
      if (preset) this.customSize = { width: preset.size, height: preset.size };
      this.modelValue = { ...this.modelValue, type: 'preset', preset: id, custom: { images: {}, size: { ...this.customSize } } };
    },
    getPresetEmojiUrl(id, emotion) {
      return `/static/${id}/${emotion}.png`;
    },
    triggerInput(key) {
      const input = this.$refs[key + 'Input'];
      if (Array.isArray(input) && input[0]) {
        input[0].click();
      } else if (input) {
        input.click();
      }
    },
    handleFileSelect(e, key) {
      const file = e.target.files && e.target.files[0];
      if (file) this.updateEmotionImage(key, file);
    },
    handleFileDrop(e, key) {
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) this.updateEmotionImage(key, file);
    },
    updateEmotionImage(key, file) {
      if (!/\.(png|gif)$/i.test(file.name)) {
        this.$message.warning(this.$t('device.customThemeEmojiInvalidFile'));
        return;
      }
      const images = { ...(this.modelValue.custom.images || {}) };
      images[key] = file;
      this.modelValue = {
        ...this.modelValue,
        type: 'custom',
        preset: '',
        custom: { ...this.modelValue.custom, images, size: this.customSize }
      };
    },
    removeImage(key) {
      const images = { ...(this.modelValue.custom.images || {}) };
      delete images[key];
      this.modelValue = {
        ...this.modelValue,
        custom: { ...this.modelValue.custom, images, size: this.customSize }
      };
    },
    getImagePreview(key) {
      const img = this.modelValue.custom.images && this.modelValue.custom.images[key];
      if (!img) return '';
      if (typeof img === 'string') return img;
      if (img instanceof File || img instanceof Blob) return URL.createObjectURL(img);
      return '';
    },
    emojiBoxStyle(size) {
      const s = typeof size === 'number' ? size : 32;
      const pad = 6;
      return {
        width: s + pad * 2 + 'px',
        height: s + pad * 2 + 'px'
      };
    },
    syncDisplaySize() {
      const base = this.modelValue.custom?.size || this.customSize || { width: 64, height: 64 };
      const w = base.width || 64;
      const h = base.height || 64;
      const { maxWidth, maxHeight } = this.getMaxSize();
      this.customSize = { width: Math.min(w, maxWidth), height: Math.min(h, maxHeight) };
      if (this.modelValue.type === 'custom') {
        const images = { ...(this.modelValue.custom?.images || {}) };
        this.modelValue = {
          ...this.modelValue,
          custom: { ...this.modelValue.custom, images, size: { width: Math.min(w, maxWidth), height: Math.min(h, maxHeight) } }
        };
      }
    },
    updateSize() {
      const { maxWidth, maxHeight } = this.getMaxSize();
      const width = Math.min(Math.max(this.customSize.width || 32, 16), maxWidth);
      const height = Math.min(Math.max(this.customSize.height || 32, 16), maxHeight);
      this.customSize = { width, height };
      const images = { ...(this.modelValue.custom.images || {}) };
      this.modelValue = {
        ...this.modelValue,
        type: 'custom',
        preset: '',
        custom: { ...this.modelValue.custom, images, size: { ...this.customSize } }
      };
    }
  }
};
</script>

<style scoped>
.emoji-config-wrapper {
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
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}
.preset-desc {
  margin: 2px 0;
  font-size: 13px;
  color: #4b5563;
}
.preset-meta {
  font-size: 12px;
  color: #6b7280;
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
.emoji-preview {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.emoji-box {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 6px;
  overflow: hidden;
}
.emoji-box img {
  object-fit: contain;
}
.custom-upload {
  margin-top: 12px;
}
.size-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 8px;
}
.size-item label {
  display: block;
  font-size: 13px;
  margin-bottom: 4px;
  color: #4b5563;
}
.upload-tip {
  margin: 0 0 10px;
  font-size: 13px;
  color: #4b5563;
}
.emoji-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.emoji-card {
  padding: 0;
  border: none;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.emoji-card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-bottom: 0;
}
.emoji-icon {
  font-size: 18px;
}
.emoji-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.emoji-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.emoji-required {
  font-size: 11px;
  color: #ef4444;
}
.upload-box {
  border: 2px dashed #9ca3af;
  border-radius: 8px;
  padding: 0;
  width: 140px;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: pointer;
  background: #f9fafb;
  overflow: hidden;
  margin: 0 auto;
}
.upload-box.filled {
  border-color: #10b981;
  background: #ecfdf3;
}
.upload-box.required {
  border-color: #fca5a5;
  background: #fef2f2;
}
.emoji-fill {
  width: 90%;
  height: 90%;
  object-fit: cover;
  display: block;
  margin: auto;
}
.upload-text {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
}
.emoji-center {
  display: block;
  margin: 0 auto;
}
.hidden-input {
  display: none;
}
.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  border: none;
  background: #ef4444;
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
  cursor: pointer;
}
.upload-note {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}
</style>

