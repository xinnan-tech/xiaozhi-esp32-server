<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
      <!-- 模态框头部 -->
      <div class="flex items-center justify-between p-6 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">{{ $t('generateModal.title') }}</h3>
        <button
          v-if="!isFlashing"
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-500"
        >
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
        <!-- 烧录中提示 -->
        <div v-else class="text-sm text-red-50 font-medium">
          {{ $t('generateModal.flashingInProgress') }}
        </div>
      </div>

      <!-- 模态框内容 -->
      <div class="p-6 overflow-y-auto" style="max-height: calc(90vh - 140px)">
        <div v-if="!isGenerating && !isCompleted" class="space-y-6">
          <!-- 配置确认 -->
          <div>
            <h4 class="font-medium text-gray-900 mb-3">{{ $t('generateModal.confirmConfig') }}</h4>
            <div class="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">{{ $t('generateModal.chipModel') }}</span>
                <span class="font-medium">{{ config.chip.model.toUpperCase() }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">{{ $t('generateModal.resolution') }}</span>
                <span class="font-medium">{{ config.chip.display.width }}×{{ config.chip.display.height }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">{{ $t('generateModal.wakeword') }}</span>
                <span class="font-medium">{{ getWakewordName() }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">{{ $t('generateModal.font') }}</span>
                <span class="font-medium">{{ getFontName() }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">{{ $t('generateModal.emoji') }}</span>
                <span class="font-medium">{{ getEmojiName() }}</span>
              </div>
            </div>
          </div>

          <!-- 文件列表 -->
          <div>
            <h4 class="font-medium text-gray-900 mb-3">{{ $t('generateModal.fileList') }}</h4>
            <div class="space-y-2 max-h-64 overflow-y-auto">
              <div
                v-for="item in fileList"
                :key="item.id"
                class="flex items-center justify-between px-3 py-2 border border-gray-200 rounded bg-gray-50"
              >
                <div class="flex items-center">
                  <component :is="item.icon" class="w-4 h-4 mr-2" :class="item.iconColor" />
                  <span class="text-sm font-medium text-gray-900">{{ item.name }}</span>
                </div>
                <div class="text-sm text-gray-700">
                  {{ item.size }}
                  <span v-if="item.estimated" class="text-xs text-gray-500 ml-1">{{ $t('generateModal.estimated') }}</span>
                  <span v-if="item.isCustomEmoji" class="text-xs text-gray-500 ml-1">{{ $t('generateModal.compressed') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 生成进度 -->
        <div v-if="isGenerating" class="space-y-6 text-center">
          <div class="flex items-center justify-center">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-primary-500"></div>
          </div>
          
          <div class="space-y-4">
            <p class="text-gray-600 mt-2">{{ $t('generateModal.generating') }}</p>
            <div class="bg-gray-200 rounded-full h-2 overflow-hidden">
              <div 
                class="bg-primary-500 h-2 rounded-full transition-all duration-500 ease-out"
                :style="{ width: progress + '%' }"
              ></div>
            </div>
            <div class="text-sm text-gray-600">
              <div>{{ currentStep }}</div>
              <div class="mt-1">{{ $t('generateModal.progress', { progress: progress }) }}</div>
            </div>
          </div>

          <!-- 进度步骤 -->
          <div class="space-y-2 text-left">
            <div
              v-for="step in progressSteps"
              :key="step.id"
              class="flex items-center text-sm"
            >
              <div class="flex-shrink-0 mr-3">
                <div v-if="step.status === 'completed'" class="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                  <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                  </svg>
                </div>
                <div v-else-if="step.status === 'processing'" class="w-5 h-5 bg-primary-500 rounded-full animate-pulse"></div>
                <div v-else class="w-5 h-5 bg-gray-300 rounded-full"></div>
              </div>
              <span :class="[
                step.status === 'completed' ? 'text-green-700' : 
                step.status === 'processing' ? 'text-primary-700' : 
                'text-gray-500'
              ]">{{ step.name }}</span>
            </div>
          </div>
        </div>

        <!-- 完成状态 -->
        <div v-if="isCompleted && !isFlashing" class="text-center space-y-6">
          <div class="mx-auto flex items-center justify-center">
            <svg class="w-20 h-20 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
          </div>
          
          <div>
            <p class="text-gray-600 mt-2">{{ $t('generateModal.completed') }}</p>
          </div>

          <div class="bg-green-50 border border-green-200 rounded-lg p-4">
            <div class="text-sm text-green-800 space-y-1">
              <div>{{ $t('generateModal.filename') }}</div>
              <div>{{ $t('generateModal.fileSize', { size: generatedFileSize }) }}</div>
              <div>{{ $t('generateModal.generationTime', { time: generationTime }) }}</div>
            </div>
          </div>

          <div class="space-y-3">
            <el-button
              @click="downloadFile"
              type="primary"
              class="w-full"
            >
              <span class="w-full flex items-center justify-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
                {{ $t('generateModal.downloadAssets') }}
              </span>
            </el-button>
            <!-- 注释在线烧录设备功能 -->
            <!-- <el-button
              @click="startOnlineFlash"
              :disabled="!deviceOnline"
              class="w-full"
              style="margin-left: 0;"
            >
              <span class="w-full flex items-center justify-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
                {{ $t('generateModal.flashToDevice') }}
              </span>
            </el-button> -->
          </div>
        </div>

        <!-- 在线烧录进度 -->
        <!-- 烧录进行中 -->
        <div v-if="isFlashing && !flashError" class="space-y-6 text-center">
          <div class="flex items-center justify-center">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500"></div>
          </div>

          <div class="space-y-4">
            <p class="text-gray-600">{{ $t('generateModal.flashing') }}</p>
            <div class="bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                class="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
                :style="{ width: flashProgress + '%' }"
              ></div>
            </div>
            <div class="text-sm text-gray-600">
              <div>{{ flashCurrentStep }}</div>
              <div class="mt-1">{{ $t('generateModal.progress', { progress: flashProgress }) }}</div>
            </div>
          </div>

          <!-- 取消按钮 -->
          <button
            @click="cancelFlash"
            class="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-md transition-colors"
          >
            {{ $t('generateModal.flashingCancel') }}
          </button>
        </div>

        <!-- 烧录失败错误提示 -->
        <div v-if="flashError" class="text-center mt-4">
          <p class="text-sm text-red-600">{{ flashError }}</p>
        </div>
      </div>

      <!-- 模态框底部 -->
      <div class="flex justify-end space-x-3 p-6 border-t border-gray-200">
        <button
          v-if="!isGenerating && !isCompleted"
          @click="$emit('close')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
        >
          {{ $t('common.cancel') }}
        </button>
        <button
          v-if="!isGenerating && !isCompleted"
          @click="startGeneration"
          :disabled="!hasSelectedFiles"
          class="px-6 py-2 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 rounded-md transition-colors"
        >
          {{ $t('common.start') }} {{ $t('common.generate') }}
        </button>
        <button
          v-if="isCompleted && !isFlashing"
          @click="$emit('close')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
        >
          {{ $t('common.close') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import AssetsBuilder from '@/utils/AssetsBuilder.js'

// 定义图标组件作为简单的对象，在模板中直接使用 SVG
// 文件图标
const FileIcon = {
  render(h) {
    return h('svg', {
      class: 'w-4 h-4',
      attrs: {
        fill: 'currentColor',
        viewBox: '0 0 20 20'
      }
    }, [
      h('path', {
        attrs: {
          d: 'M4 3a2 2 0 00-2 2v1a1 1 0 001 1h14a1 1 0 001-1V5a2 2 0 00-2-2H4zM3 8a1 1 0 011-1h12a1 1 0 011 1v5a2 2 0 01-2 2H5a2 2 0 01-2-2V8z'
        }
      })
    ]);
  }
};
// 麦克风图标
const MicIcon = {
  render(h) {
    return h('svg', {
      class: 'w-4 h-4',
      attrs: {
        fill: 'currentColor',
        viewBox: '0 0 20 20'
      }
    }, [
      h('path', {
        attrs: {
          'fill-rule': 'evenodd',
          d: 'M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z',
          'clip-rule': 'evenodd'
        }
      })
    ]);
  }
};
// 字体图标
const FontIcon = {
  render(h) {
    return h('svg', {
      class: 'w-4 h-4',
      attrs: {
        fill: 'none',
        stroke: 'currentColor',
        viewBox: '0 0 24 24'
      }
    }, [
      h('path', {
        attrs: {
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'stroke-width': '2',
          d: 'M8 4l8 16m-6-6h4'
        }
      })
    ]);
  }
};
// 图片图标
const ImageIcon = {
  render(h) {
    return h('svg', {
      class: 'w-4 h-4',
      attrs: {
        fill: 'currentColor',
        viewBox: '0 0 20 20'
      }
    }, [
      h('path', {
        attrs: {
          'fill-rule': 'evenodd',
          d: 'M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z',
          'clip-rule': 'evenodd'
        }
      })
    ]);
  }
};

export default {
  components: {
    FileIcon,
    MicIcon,
    FontIcon,
    ImageIcon
  },
  
  props: {
    config: {
      type: Object,
      required: true
    }
  },
  
  data() {
    return {
      isGenerating: false,
      isCompleted: false,
      progress: 0,
      currentStep: '',
      generatedFileSize: '',
      generationTime: '',
      generatedBlob: null,
      generationStartTime: null,
      deviceOnline: false,
      isFlashing: false,
      flashProgress: 0,
      flashCurrentStep: '',
      flashError: '',
      fileList: [],
      deviceInfo: {
        value: {
          assetsPartition: null
        }
      }
    }
  },
  
  computed: {
    // 使用计算属性来获取翻译后的进度步骤名称
    progressSteps() {
      return [
        { id: 1, name: this.$t('progressSteps.init'), status: 'pending' },
        { id: 2, name: this.$t('progressSteps.font'), status: 'pending' },
        { id: 3, name: this.$t('progressSteps.wakeword'), status: 'pending' },
        { id: 4, name: this.$t('progressSteps.emoji'), status: 'pending' },
        { id: 5, name: this.$t('progressSteps.background'), status: 'pending' },
        { id: 6, name: this.$t('progressSteps.index'), status: 'pending' },
        { id: 7, name: this.$t('progressSteps.spiffs'), status: 'pending' },
        { id: 8, name: this.$t('progressSteps.package'), status: 'pending' }
      ]
    },
    
    hasSelectedFiles() {
      return this.fileList.length > 0
    }
  },
  
  methods: {
    getWakewordName() {
      const wakeword = this.config.theme.wakeword
      if (!wakeword || wakeword.type === 'none') return this.$t('wakewordConfig.noWakeword')
      
      if (wakeword.type === 'preset') {
        const names = {
          'wn9s_hilexin': 'Hi,乐鑫',
          'wn9s_hiesp': 'Hi,ESP',
          'wn9s_nihaoxiaozhi': '你好小智',
          'wn9_nihaoxiaozhi_tts': '你好小智',
          'wn9_alexa': 'Alexa'
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
        return this.config.theme.font.preset.replace('font_', '').replace('_', ' ')
      }
      return this.$t('generateModal.customFont')
    },
    
    getEmojiName() {
      if (this.config.theme.emoji.type === 'preset' && this.config.theme.emoji.preset) {
        return this.config.theme.emoji.preset === 'twemoji32' ? 'Twemoji 32×32' : 'Twemoji 64×64'
      } else if (this.config.theme.emoji.type === 'custom') {
        return this.$t('generateModal.customEmoji')
      } else if (this.config.theme.emoji.type === 'none') {
        return this.$t('emojiConfig.noEmojiPack')
      }
      return this.$t('generateModal.notConfigured')
    },
    
    initializeFileList() {
      this.fileList = []

      // 添加索引文件
      this.fileList.push({
        id: 'index',
        name: 'index.json',
        description: '配置索引文件',
        icon: 'FileIcon', // 使用组件名称字符串而不是组件对象
        iconColor: 'text-blue-500',
        size: '1KB'
      })

      // 添加唤醒词模型（如果有配置）
      const wakeword = this.config.theme.wakeword
      if (wakeword && wakeword.type !== 'none') {
        this.fileList.push({
          id: 'srmodels',
          name: 'srmodels.bin',
          description: wakeword.type === 'custom' ? '自定义命令词模型' : '预设唤醒词模型',
          icon: 'MicIcon',
          iconColor: 'text-green-500',
          size: wakeword.type === 'custom' ? '~1.2MB' : '~300KB'
        })
      }

      // 添加字体文件
      if (this.config.theme.font.type === 'preset') {
        const fontSizes = {
          'font_puhui_deepseek_14_1': '180KB',
          'font_puhui_deepseek_16_4': '720KB',
          'font_puhui_deepseek_20_4': '1.1MB',
          'font_puhui_deepseek_30_4': '2.5MB'
        }
        
        this.fileList.push({
          id: 'font',
          name: `${this.config.theme.font.preset}.bin`,
          description: '预设字体文件',
          icon: 'FontIcon',
          iconColor: 'text-yellow-500',
          size: fontSizes[this.config.theme.font.preset] || '500KB'
        })
      } else if (this.config.theme.font.custom.file) {
        const custom = this.config.theme.font.custom
        const estimatedSize = Math.max(100, custom.size * custom.size * custom.bpp * 0.7)
        
        this.fileList.push({
          id: 'font',
          name: `font_custom_${custom.size}_${custom.bpp}.bin`,
          description: '自定义字体文件',
          icon: 'FontIcon',
          iconColor: 'text-yellow-500',
          size: estimatedSize > 1024 ? `${(estimatedSize/1024).toFixed(1)}MB` : `${Math.round(estimatedSize)}KB`,
          estimated: true
        })
      }

      // 添加表情文件
      if (this.config.theme.emoji.type === 'preset' && this.config.theme.emoji.preset) {
        const emotionList = ['neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying', 'loving', 'embarrassed', 'surprised', 'shocked', 'thinking', 'winking', 'cool', 'relaxed', 'delicious', 'kissy', 'confident', 'sleepy', 'silly', 'confused']
        const size = this.config.theme.emoji.preset === 'twemoji64' ? '3KB' : '1KB'
        
        emotionList.forEach(emotion => {
          this.fileList.push({
            id: `emoji_${emotion}`,
            name: `${emotion}.png`,
            description: `${emotion}表情图片`,
            icon: 'ImageIcon',
            iconColor: 'text-pink-500',
            size: size
          })
        })
      } else if (this.config.theme.emoji.type === 'custom') {
        const custom = this.config.theme.emoji.custom
        const emotionMap = custom.emotionMap || {}
        const fileMap = custom.fileMap || {}
        const images = custom.images || {}
        
        // 必须使用新的 hash 映射结构
        if (Object.keys(emotionMap).length === 0 || Object.keys(fileMap).length === 0) {
          console.error(this.$t('errors.incompatibleEmojiData'))
          return
        }
        
        // 统计唯一文件
        const uniqueFiles = new Map()
        const emotionsPerFile = new Map()
        
        Object.entries(emotionMap).forEach(([emotion, fileHash]) => {
          const file = fileMap[fileHash]
          if (file) {
            if (!uniqueFiles.has(fileHash)) {
              const fileSizeKB = Math.round(file.size / 1024)
              uniqueFiles.set(fileHash, {
                file,
                size: fileSizeKB > 1024 ? `${(fileSizeKB/1024).toFixed(1)}MB` : `${fileSizeKB}KB`,
                emotions: []
              })
            }
            uniqueFiles.get(fileHash).emotions.push(emotion)
            emotionsPerFile.set(emotion, fileHash)
          }
        })
        
        // 添加去重后的文件到列表
        uniqueFiles.forEach((fileInfo, fileHash) => {
          const emotionNames = fileInfo.emotions.join(', ')
          const isShared = fileInfo.emotions.length > 1
          
          this.fileList.push({
            id: `emoji_${fileHash.substring(0, 8)}`,
            name: `emoji_${fileHash.substring(0, 8)}.${fileInfo.file.name.split('.').pop()}`,
            description: isShared 
              ? `共享表情图片 (${emotionNames})` 
              : `${emotionNames}表情图片`,
            icon: 'ImageIcon',
            iconColor: isShared ? 'text-purple-500' : 'text-pink-500',
            size: fileInfo.size,
            isCustomEmoji: true
          })
        })
        
        // 添加去重统计信息
        if (uniqueFiles.size < Object.keys(emotionMap).length) {
          console.log(`表情去重：${Object.keys(emotionMap).length} 个表情使用了 ${uniqueFiles.size} 个文件`)
        }
      }

      // 添加背景文件
      if (this.config.theme.skin.light.backgroundType === 'image' && this.config.theme.skin.light.backgroundImage) {
        const { width, height } = this.config.chip.display
        const estimatedSize = Math.round(width * height * 2 / 1024) // RGB565
        
        this.fileList.push({
          id: 'bg_light',
          name: 'background_light.raw',
          description: '浅色模式背景图片',
          icon: 'ImageIcon',
          iconColor: 'text-indigo-500',
          size: estimatedSize > 1024 ? `${(estimatedSize/1024).toFixed(1)}MB` : `${estimatedSize}KB`,
          estimated: true
        })
      }

      if (this.config.theme.skin.dark.backgroundType === 'image' && this.config.theme.skin.dark.backgroundImage) {
        const { width, height } = this.config.chip.display
        const estimatedSize = Math.round(width * height * 2 / 1024) // RGB565
        
        this.fileList.push({
          id: 'bg_dark',
          name: 'background_dark.raw',
          description: '深色模式背景图片',
          icon: 'ImageIcon',
          iconColor: 'text-indigo-500',
          size: estimatedSize > 1024 ? `${(estimatedSize/1024).toFixed(1)}MB` : `${estimatedSize}KB`,
          estimated: true
        })
      }
    },
    
    getTotalSize() {
      let totalKB = 0
      
      this.fileList.forEach(file => {
        const sizeStr = file.size.replace('~', '').replace('预估', '')
        if (sizeStr.includes('MB')) {
          totalKB += parseFloat(sizeStr.replace('MB', '')) * 1024
        } else {
          totalKB += parseFloat(sizeStr.replace('KB', ''))
        }
      })
      
      return totalKB > 1024 ? `${(totalKB / 1024).toFixed(1)}MB` : `${Math.round(totalKB)}KB`
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
    },
    
    formatDuration(milliseconds) {
      if (milliseconds < 1000) {
        return `${milliseconds}ms`
      } else if (milliseconds < 60000) {
        return `${(milliseconds / 1000).toFixed(1)}s`
      } else {
        const minutes = Math.floor(milliseconds / 60000)
        const seconds = Math.floor((milliseconds % 60000) / 1000)
        return `${minutes}m ${seconds}s`
      }
    },
    
    async startGeneration() {
      this.isGenerating = true
      this.progress = 0
      this.generationStartTime = Date.now()
      
      try {
        // 创建AssetsBuilder实例
        const builder = new AssetsBuilder()
        builder.setConfig(this.config)
        
        // 生成assets.bin
        const blob = await builder.generateAssetsBin((progressPercent, message) => {
          this.progress = parseInt(progressPercent)
          this.currentStep = message
          
          // 更新进度步骤状态
          const stepIndex = Math.floor(progressPercent / (100 / this.progressSteps.length))
          this.progressSteps.forEach((step, index) => {
            if (index < stepIndex) {
              step.status = 'completed'
            } else if (index === stepIndex) {
              step.status = 'processing'
            } else {
              step.status = 'pending'
            }
          })
        })
        
        // 完成生成
        this.isGenerating = false
        this.isCompleted = true
        
        // 更新生成结果
        this.generatedFileSize = this.formatFileSize(blob.size)
        const endTime = Date.now()
        const duration = endTime - this.generationStartTime
        this.generationTime = this.formatDuration(duration)
        
        // 存储生成的文件用于下载
        this.generatedBlob = blob
        
        // 标记所有步骤为完成
        this.progressSteps.forEach(step => {
          step.status = 'completed'
        })
        
        // 通知父组件
        this.$emit('generate', this.fileList.map(f => ({ id: f.id, name: f.name })))
        
      } catch (error) {
        console.error('生成 assets.bin 失败:', error)
        
        // 重置状态
        this.isGenerating = false
        this.isCompleted = false
        
        // 显示错误
        alert(this.$t('errors.generationFailed', { error: error.message }))
      }
    },
    
    downloadFile() {
      if (this.generatedBlob) {
        const url = URL.createObjectURL(this.generatedBlob)
        const element = document.createElement('a')
        element.href = url
        element.download = 'assets.bin'
        element.style.display = 'none'
        document.body.appendChild(element)
        element.click()
        document.body.removeChild(element)
        URL.revokeObjectURL(url)
      } else {
        console.error(this.$t('errors.noFileToDownload'))
      }
    },
    
    // 检查设备在线状态
    async checkDeviceOnline() {
      try {
        // 获取URL参数中的token
        const urlParams = new URLSearchParams(window.location.search)
        const token = urlParams.get('token')

        if (!token) {
          this.deviceOnline = false
          return
        }

        const response = await fetch('/api/messaging/device/tools/list', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        })

        this.deviceOnline = response.ok
      } catch (error) {
        console.error(this.$t('flashProgress.unableToGetDeviceStatus'), error)
        this.deviceOnline = false
      }
    },
    
    // 开始在线烧录
    async startOnlineFlash() {
      if (!this.generatedBlob) {
        alert(this.$t('errors.noFileToDownload'))
        return
      }

      if (!this.deviceOnline) {
        alert(this.$t('errors.deviceOffline'))
        return
      }

      // 检查文件大小是否超过assets分区大小
      if (this.deviceInfo.value.assetsPartition && this.deviceInfo.value.assetsPartition.size) {
        const assetsPartitionSize = this.deviceInfo.value.assetsPartition.size
        const fileSize = this.generatedBlob.size
        
        if (fileSize > assetsPartitionSize) {
          const fileSizeMB = (fileSize / 1024 / 1024).toFixed(2)
          const partitionSizeMB = (assetsPartitionSize / 1024 / 1024).toFixed(2)
          alert(this.$t('errors.fileTooLarge', { fileSize: fileSizeMB, partitionSize: partitionSizeMB }))
          return
        }
      }

      this.isFlashing = true
      this.flashProgress = 0
      this.flashCurrentStep = this.$t('flashProgress.startingFileTransfer')
      this.flashError = ''

      try {
        // 通知父组件开始在线烧录
        this.$emit('startFlash', {
          blob: this.generatedBlob,
          onProgress: (progress, step) => {
            this.flashProgress = progress
            this.flashCurrentStep = step
          },
          onComplete: () => {
            this.isFlashing = false
            this.flashProgress = 100
            this.flashCurrentStep = this.$t('flashProgress.flashCompleted')
          },
          onError: (error) => {
            this.isFlashing = false
            this.flashError = error
            console.error(this.$t('flashProgress.onlineFlashFailed', { error }))
          }
        })
      } catch (error) {
        this.isFlashing = false
        this.flashError = this.$t('flashProgress.onlineFlashFailed', { error: error.message })
        console.error(this.$t('flashProgress.onlineFlashFailed', { error }))
      }
    },
    
    // 取消烧录
    cancelFlash() {
      if (confirm(this.$t('errors.flashCancelConfirm'))) {
        this.isFlashing = false
        this.flashProgress = 0
        this.flashCurrentStep = ''
        this.flashError = ''
        this.$emit('cancelFlash')
      }
    }
  },
  
  mounted() {
    this.initializeFileList()
    this.checkDeviceOnline()
  }
}
</script>
