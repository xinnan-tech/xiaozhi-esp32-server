<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ $t('generateSummary.title') }}</h2>
      <p class="text-gray-600 mb-6">{{ $t('generateSummary.description') }}</p>
    </div>

    <!-- 设备预览区域 -->
    <div class="flex flex-col lg:flex-row gap-8">
      <!-- 设备模拟器 -->
      <div class="flex-1">
        <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('generateSummary.devicePreview') }}</h3>
        <div class="bg-gray-100 p-4 rounded-lg">
          <div class="max-w-full overflow-auto flex justify-center">
            <!-- 设备外框 -->
            <div class="bg-gray-800 p-6 rounded-2xl shadow-2xl inline-block">
              <div class="bg-gray-900 p-2 rounded-xl">
                <!-- 屏幕区域 -->
                <div 
                  :style="getScreenStyle()"
                  class="relative rounded-lg overflow-hidden border-2 border-gray-700 flex flex-col items-center justify-center"
                >
                <!-- 背景层 -->
                <div 
                  :style="getBackgroundStyle()"
                  class="absolute inset-0"
                ></div>
                
                <!-- 内容层 -->
                <div class="relative z-10 flex flex-col items-center justify-center p-4 text-center">
                  <!-- 表情显示 -->
                  <div class="mb-4">
                    <div v-if="currentEmoji && availableEmotions.length > 0" class="emoji-container">
                      <img 
                        v-if="currentEmojiImage"
                        :src="currentEmojiImage" 
                        :alt="currentEmoji"
                        :style="getEmojiStyle()"
                        class="emoji-image"
                      />
                      <div 
                        v-else
                        :style="getEmojiStyle()"
                        class="emoji-fallback bg-gray-200 rounded-full flex items-center justify-center text-2xl"
                      >
                        {{ getEmojiCharacter(currentEmoji) }}
                      </div>
                    </div>
                    <div v-else class="emoji-container">
                      <div 
                        :style="getEmojiStyle()"
                        class="emoji-placeholder flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-300 rounded bg-gray-50"
                      >
                        <div class="text-center">
                          <div class="text-sm">{{ config.theme.emoji.type === 'none' ? '📦' : '😕' }}</div>
                          <div class="text-xs">{{ config.theme.emoji.type === 'none' ? $t('emojiConfig.noEmojiPack') : $t('generateSummary.noEmotionConfigured') }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 文字显示 -->
                  <div 
                    v-if="!config.theme.font.hide_subtitle"
                    :style="getTextStyle()"
                    class="text-message max-w-full break-words relative"
                  >
                    <div v-if="!fontLoaded" class="absolute inset-0 flex items-center justify-center">
                      <div class="animate-pulse text-gray-400 text-xs">{{ $t('generateSummary.fontLoading') }}</div>
                    </div>
                    <div :class="{ 'opacity-0': !fontLoaded }">
                      {{ previewText }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 设备信息 -->
            <div class="mt-3 text-center text-xs text-gray-400">
              {{ config.chip.display.width }} × {{ config.chip.display.height }}
              {{ config.chip.model.toUpperCase() }}
            </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 控制面板 -->
      <div class="w-full lg:w-80">
        <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('generateSummary.previewSettings') }}</h3>
        <div class="space-y-6 bg-white border border-gray-200 rounded-lg p-4">
          
          <!-- 文字内容编辑 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('generateSummary.previewText') }}</label>
            <textarea
              v-model="previewText"
              class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows="3"
              placeholder="Hi, I'm your friend Xiaozhi!"
            ></textarea>
          </div>

          <!-- 表情切换 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('generateSummary.currentEmotion') }}</label>
            <div v-if="availableEmotions.length > 0" class="flex flex-wrap gap-2 max-h-32 overflow-y-auto justify-center">
              <button
                v-for="emotion in availableEmotions"
                :key="emotion.key"
                @click="changeEmotion(emotion.key)"
                :class="[
                  'p-2 border rounded transition-colors flex items-center justify-center',
                  currentEmoji === emotion.key 
                    ? 'border-primary-500 bg-primary-50' 
                    : 'border-gray-200 hover:border-gray-300'
                ]"
                :title="emotion.name"
                :style="{ width: getEmojiControlSize() + 'px', height: getEmojiControlSize() + 'px' }"
              >
                <div v-if="getEmotionImage(emotion.key)">
                  <img 
                    :src="getEmotionImage(emotion.key)"
                    :alt="emotion.name"
                    :style="{ width: getEmojiDisplaySize() + 'px', height: getEmojiDisplaySize() + 'px' }"
                    class="object-contain rounded"
                  />
                </div>
                <div v-else class="text-lg">{{ emotion.emoji }}</div>
              </button>
            </div>
            <div v-else class="text-center py-4 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed">
              <div class="text-2xl mb-2">{{ config.theme.emoji.type === 'none' ? '📦' : '😕' }}</div>
              <div class="text-sm">{{ config.theme.emoji.type === 'none' ? $t('emojiConfig.noEmojiPackDescription') : $t('generateSummary.configureEmojiFirst') }}</div>
            </div>
          </div>

          <!-- 主题模式切换 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('generateSummary.themeMode') }}</label>
            <div class="flex space-x-2">
              <button
                @click="themeMode = 'light'"
                :class="[
                  'flex-1 py-2 px-3 text-sm border rounded transition-colors',
                  themeMode === 'light'
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-300 hover:border-gray-400'
                ]"
              >
                🌞 {{ $t('generateSummary.lightMode') }}
              </button>
              <button
                @click="themeMode = 'dark'"
                :class="[
                  'flex-1 py-2 px-3 text-sm border rounded transition-colors',
                  themeMode === 'dark'
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-300 hover:border-gray-400'
                ]"
              >
                🌙 {{ $t('generateSummary.darkMode') }}
              </button>
            </div>
          </div>


          <!-- 配置摘要 -->
          <div class="border-t pt-4">
            <h4 class="font-medium text-gray-900 mb-2">{{ $t('generateSummary.configSummary') }}</h4>
            <div class="text-xs text-gray-600 space-y-1">
              <div v-if="config.theme.wakeword">{{ $t('generateSummary.wakeword') }} {{ getWakewordName() }}</div>
              <div class="flex items-center justify-center">
                <span>{{ $t('generateSummary.font') }} {{ getFontName() }}</span>
                <span v-if="!fontLoaded" class="ml-2 animate-pulse text-blue-500">{{ $t('generateSummary.loading') }}</span>
              </div>
              <div>{{ $t('generateSummary.emotion') }} {{ getEmojiName() }}</div>
              <div>{{ $t('generateSummary.skin') }} {{ getSkinName() }}</div>
              <div v-if="config.theme.font.hide_subtitle">{{ $t('generateSummary.hideSubtitle') }} {{ $t('common.yes') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="flex justify-between">
      <button 
        @click="$emit('prev')"
        class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
      >
        {{ $t('generateSummary.previous') }}
      </button>
      <button 
        @click="$emit('generate')"
        class="bg-green-500 hover:bg-green-600 text-white px-8 py-2 rounded-lg font-medium transition-colors flex items-center"
      >
        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
        </svg>
        {{ $t('generateSummary.generate') }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    config: {
      type: Object,
      required: true
    }
  },
  
  emits: ['prev', 'generate'],
  
  data() {
    return {
      // 预览状态
      previewText: this.$t('generateSummary.defaultPreviewText'),
      currentEmoji: 'happy',
      themeMode: 'light',
      fontLoaded: false,
      loadedFontFamily: ''
    }
  },
  
  computed: {
    // 表情数据
    emotionList() {
      return [
        { key: 'neutral', name: this.$t('generateSummary.emotions.neutral'), emoji: '😶' },
        { key: 'happy', name: this.$t('generateSummary.emotions.happy'), emoji: '🙂' },
        { key: 'laughing', name: this.$t('generateSummary.emotions.laughing'), emoji: '😆' },
        { key: 'funny', name: this.$t('generateSummary.emotions.funny'), emoji: '😂' },
        { key: 'sad', name: this.$t('generateSummary.emotions.sad'), emoji: '😔' },
        { key: 'angry', name: this.$t('generateSummary.emotions.angry'), emoji: '😠' },
        { key: 'crying', name: this.$t('generateSummary.emotions.crying'), emoji: '😭' },
        { key: 'loving', name: this.$t('generateSummary.emotions.loving'), emoji: '😍' },
        { key: 'surprised', name: this.$t('generateSummary.emotions.surprised'), emoji: '😯' },
        { key: 'thinking', name: this.$t('generateSummary.emotions.thinking'), emoji: '🤔' },
        { key: 'cool', name: this.$t('generateSummary.emotions.cool'), emoji: '😎' },
        { key: 'sleepy', name: this.$t('generateSummary.emotions.sleepy'), emoji: '😴' }
      ]
    },
    
    // 可用的表情列表
    availableEmotions() {
      if (this.config.theme.emoji.type === 'preset' && this.config.theme.emoji.preset) {
        return this.emotionList
      } else if (this.config.theme.emoji.type === 'custom') {
        // 只显示用户上传的表情
        const customImages = this.config.theme.emoji.custom.images
        return this.emotionList.filter(emotion => customImages[emotion.key])
      } else {
        // 未配置表情时返回空数组
        return []
      }
    },
    
    // 当前表情图片
    currentEmojiImage() {
      return this.getEmotionImage(this.currentEmoji)
    }
  },
  
  methods: {

    // 获取屏幕样式
    getScreenStyle() {
      const { width, height } = this.config.chip.display
      
      // 使用1:1像素比例，直接使用配置中的尺寸
      return {
        width: `${width}px`,
        height: `${height}px`
      }
    },
    
    // 获取背景样式
    getBackgroundStyle() {
      const bg = this.config.theme.skin[this.themeMode]
      
      if (bg.backgroundType === 'image' && bg.backgroundImage) {
        try {
          // 验证背景图片文件是否有效
          if (bg.backgroundImage && typeof bg.backgroundImage === 'object' && bg.backgroundImage.size) {
            return {
              backgroundImage: `url(${URL.createObjectURL(bg.backgroundImage)})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center'
            }
          }
        } catch (error) {
          console.warn('背景图片预览加载失败:', error)
        }
      }
      
      return {
        backgroundColor: bg.backgroundColor || '#ffffff'
      }
    },
    
    // 获取表情样式
    getEmojiStyle() {
      let size = 48 // 默认大小
      
      if (this.config.theme.emoji.type === 'preset') {
        size = this.config.theme.emoji.preset === 'twemoji64' ? 64 : 32
      } else if (this.config.theme.emoji.custom.size) {
        size = Math.min(this.config.theme.emoji.custom.size.width, this.config.theme.emoji.custom.size.height)
      }
      
      // 使用1:1像素比例，直接使用配置中的表情尺寸
      return {
        width: `${size}px`,
        height: `${size}px`
      }
    },
    
    // 获取文字样式
    getTextStyle() {
      let fontSize = 14
      
      // 根据字体配置调整字号
      if (this.config.theme.font.type === 'preset') {
        const fontConfig = this.config.theme.font.preset
        if (fontConfig.includes('_14_')) fontSize = 14
        else if (fontConfig.includes('_16_')) fontSize = 16
        else if (fontConfig.includes('_20_')) fontSize = 20
        else if (fontConfig.includes('_30_')) fontSize = 30
      } else if (this.config.theme.font.custom.size) {
        fontSize = this.config.theme.font.custom.size
      }
      
      // 使用1:1像素比例，直接使用配置中的字体大小
      const textColor = this.themeMode === 'dark' 
        ? this.config.theme.skin.dark.textColor 
        : this.config.theme.skin.light.textColor
      
      return {
        fontSize: `${fontSize}px`,
        color: textColor,
        fontFamily: this.getFontFamily(),
        textShadow: this.themeMode === 'dark' ? '1px 1px 2px rgba(0,0,0,0.5)' : '1px 1px 2px rgba(255,255,255,0.5)'
      }
    },
    
    // 动态加载字体
    async loadFont() {
      // 清理之前的字体
      const existingStyles = document.querySelectorAll('style[data-font-preview]')
      existingStyles.forEach(style => style.remove())
      
      this.fontLoaded = false
      this.loadedFontFamily = ''

      try {
        if (this.config.theme.font.type === 'preset') {
          // 加载预设字体
          const presetId = this.config.theme.font.preset
          let fontFamily, fontUrl
          
          // 根据预设字体 ID 判断是 puhui 还是 noto
          if (presetId && presetId.startsWith('font_noto_qwen_')) {
            fontFamily = 'NotoPreview'
            fontUrl = './static/fonts/noto_qwen.ttf'
          } else {
            // 默认为 puhui
            fontFamily = 'PuHuiPreview'
            fontUrl = './static/fonts/puhui_deepseek.ttf'
          }
          
          const style = document.createElement('style')
          style.setAttribute('data-font-preview', 'true')
          style.textContent = `
            @font-face {
              font-family: '${fontFamily}';
              src: url('${fontUrl}') format('truetype');
              font-display: swap;
            }
          `
          document.head.appendChild(style)
          
          // 等待字体加载完成
          if (document.fonts && document.fonts.load) {
            await document.fonts.load(`16px "${fontFamily}"`)
          }
          this.loadedFontFamily = fontFamily
          this.fontLoaded = true
          
        } else if (this.config.theme.font.custom.file) {
          // 加载自定义字体
          try {
            const fontFile = this.config.theme.font.custom.file
            
            // 验证文件对象是否有效
            if (!fontFile || typeof fontFile !== 'object' || !fontFile.size) {
              throw new Error('字体文件对象无效')
            }
            
            const fontFamily = 'CustomFontPreview'
            const fontUrl = URL.createObjectURL(fontFile)
            
            const style = document.createElement('style')
            style.setAttribute('data-font-preview', 'true')
            style.textContent = `
              @font-face {
                font-family: '${fontFamily}';
                src: url('${fontUrl}');
                font-display: swap;
              }
            `
            document.head.appendChild(style)
            
            // 等待字体加载完成
            if (document.fonts && document.fonts.load) {
              await document.fonts.load(`16px "${fontFamily}"`)
            }
            this.loadedFontFamily = fontFamily
            this.fontLoaded = true
          } catch (error) {
            console.warn('自定义字体预览加载失败:', error)
            // 使用系统默认字体作为fallback
            this.loadedFontFamily = 'Arial, sans-serif'
            this.fontLoaded = true
          }
        } else {
          // 使用系统字体
          this.loadedFontFamily = 'system-ui'
          this.fontLoaded = true
        }
      } catch (error) {
        console.warn('Font loading failed:', error)
        this.loadedFontFamily = 'system-ui'
        this.fontLoaded = true
      }
    },
    
    // 获取字体族
    getFontFamily() {
      if (this.fontLoaded && this.loadedFontFamily) {
        return `"${this.loadedFontFamily}", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif`
      }
      return '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
    },
    
    // 获取表情图片
    getEmotionImage(emotionKey) {
      if (this.config.theme.emoji.type === 'preset') {
        const size = this.config.theme.emoji.preset === 'twemoji64' ? '64' : '32'
        return `./static/twemoji${size}/${emotionKey}.png`
      } else if (this.config.theme.emoji.type === 'custom' && this.config.theme.emoji.custom.images[emotionKey]) {
        try {
          const emojiFile = this.config.theme.emoji.custom.images[emotionKey]
          // 验证表情文件是否有效
          if (emojiFile && typeof emojiFile === 'object' && emojiFile.size) {
            return URL.createObjectURL(emojiFile)
          }
        } catch (error) {
          console.warn(`表情图片预览加载失败 (${emotionKey}):`, error)
        }
      }
      return null
    },
    
    // 获取表情字符
    getEmojiCharacter(emotionKey) {
      const emotion = this.emotionList.find(e => e.key === emotionKey)
      return emotion ? emotion.emoji : '😶'
    },
    
    // 获取表情控制按钮尺寸
    getEmojiControlSize() {
      if (this.config.theme.emoji.type === 'preset') {
        const baseSize = this.config.theme.emoji.preset === 'twemoji64' ? 64 : 32
        return baseSize + 16 // 加上padding
      } else if (this.config.theme.emoji.custom.size) {
        const baseSize = Math.min(this.config.theme.emoji.custom.size.width, this.config.theme.emoji.custom.size.height)
        return Math.min(baseSize + 16, 64) // 限制最大尺寸
      }
      return 48 // 默认尺寸
    },
    
    // 获取表情图片显示尺寸
    getEmojiDisplaySize() {
      if (this.config.theme.emoji.type === 'preset') {
        return this.config.theme.emoji.preset === 'twemoji64' ? 64 : 32
      } else if (this.config.theme.emoji.custom.size) {
        return Math.min(this.config.theme.emoji.custom.size.width, this.config.theme.emoji.custom.size.height, 48) // 限制最大尺寸
      }
      return 32 // 默认尺寸
    },
    
    // 切换表情
    changeEmotion(emotionKey) {
      this.currentEmoji = emotionKey
    },
    
    // 配置摘要方法
    getWakewordName() {
      const wakeword = this.config.theme.wakeword
      if (!wakeword || wakeword.type === 'none') return this.$t('wakewordConfig.noWakeword')
      
      if (wakeword.type === 'preset') {
        const names = {
          'wn9s_hilexin': 'Hi,乐鑫', 'wn9s_hiesp': 'Hi,ESP', 'wn9s_nihaoxiaozhi': '你好小智',
          'wn9_nihaoxiaozhi_tts': '你好小智', 'wn9_alexa': 'Alexa', 'wn9_jarvis_tts': 'Jarvis'
        }
        return names[wakeword.preset] || wakeword.preset
      }
      
      if (wakeword.type === 'custom') {
        return wakeword.custom.name || this.$t('wakewordConfig.customWakeword')
      }
      
      return this.$t('wakewordConfig.noWakeword')
    },
    
    getFontName() {
      if (this.config.theme.font.type === 'preset') {
        // 使用国际化翻译获取预设字体名称
        return this.$t('fontConfig.presetFontNames.' + this.config.theme.font.preset) || this.config.theme.font.preset
      } else {
        const custom = this.config.theme.font.custom
        return this.$t('generateSummary.customFont', { size: custom.size })
      }
    },
    
    getEmojiName() {
      if (this.config.theme.emoji.type === 'preset' && this.config.theme.emoji.preset) {
        return this.config.theme.emoji.preset === 'twemoji64' ? 'Twemoji 64×64' : 'Twemoji 32×32'
      } else if (this.config.theme.emoji.type === 'custom') {
        const count = Object.keys(this.config.theme.emoji.custom.images).length
        return this.$t('generateSummary.customEmoji', { count })
      } else if (this.config.theme.emoji.type === 'none') {
        return this.$t('emojiConfig.noEmojiPack')
      } else {
        return this.$t('generateSummary.notConfigured')
      }
    },
    
    getSkinName() {
      const lightType = this.config.theme.skin.light.backgroundType === 'image' ? this.$t('generateSummary.image') : this.$t('generateSummary.color')
      const darkType = this.config.theme.skin.dark.backgroundType === 'image' ? this.$t('generateSummary.image') : this.$t('generateSummary.color')
      return this.$t('generateSummary.skinLight', { type: lightType }) + '/' + this.$t('generateSummary.skinDark', { type: darkType })
    }
  },
  
  watch: {
    // 监听字体配置变化
    'config.theme.font': {
      handler() {
        this.loadFont()
      },
      deep: true
    }
  },
  
  mounted() {
    // 确保有可用的表情
    if (this.availableEmotions.length > 0) {
      this.currentEmoji = this.availableEmotions[0].key
    } else {
      this.currentEmoji = ''
    }
    
    // 加载字体
    this.loadFont()
  },
  
  beforeDestroy() {
    // 组件卸载时清理字体
    const existingStyles = document.querySelectorAll('style[data-font-preview]')
    existingStyles.forEach(style => style.remove())
  }
}
</script>

<style scoped>
.emoji-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.emoji-image {
  border-radius: 8px;
  object-fit: contain;
}

.emoji-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
}

.text-message {
  line-height: 1;
  word-wrap: break-word;
}
</style>