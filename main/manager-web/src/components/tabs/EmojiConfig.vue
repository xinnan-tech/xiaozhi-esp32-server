<template>
  <div class="space-y-6">
    <div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">{{ $t('emojiConfig.title') }}</h3>
      <p class="text-gray-600">{{ $t('emojiConfig.description') }}</p>
    </div>

    <!-- 表情类型选择 -->
    <div class="space-y-4">
      <div class="flex flex-wrap gap-3">
        <button
          @click="setEmojiType('none')"
          :class="[
            'px-4 py-2 border rounded-lg transition-colors',
            value.type === 'none'
              ? 'border-primary-500 bg-primary-50 text-primary-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ $t('emojiConfig.noEmojiPack') }}
        </button>
        <button
          @click="setEmojiType('preset')"
          :class="[
            'px-4 py-2 border rounded-lg transition-colors',
            value.type === 'preset'
              ? 'border-primary-500 bg-primary-50 text-primary-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ $t('emojiConfig.presetEmojiPack') }}
        </button>
        <button
          @click="setEmojiType('custom')"
          :class="[
            'px-4 py-2 border rounded-lg transition-colors',
            value.type === 'custom'
              ? 'border-primary-500 bg-primary-50 text-primary-700'
              : 'border-gray-300 hover:border-gray-400'
          ]"
        >
          {{ $t('emojiConfig.customEmojiPack') }}
        </button>
      </div>
      <p v-if="value.type === 'none'" class="text-sm text-gray-500">
        {{ $t('emojiConfig.noEmojiPackDescription') }}
      </p>
    </div>

    <div v-if="value.type === 'preset'" class="space-y-4">
      <h4 class="font-medium text-gray-900">{{ $t('emojiConfig.selectPresetEmojiPack') }}</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          v-for="pack in presetEmojis"
          :key="pack.id"
          @click="selectPresetEmoji(pack.id)"
          :class="[
            'border-2 rounded-lg p-4 cursor-pointer transition-all',
            value.preset === pack.id
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="flex items-start justify-between mb-3">
            <div>
              <h5 class="font-medium text-gray-900">{{ pack.name }}</h5>
              <p class="text-sm text-gray-600">{{ pack.description }}</p>
              <div class="text-xs text-gray-500 mt-1">
                {{ $t('emojiConfig.size') }}: {{ pack.size }}px × {{ pack.size }}px
              </div>
            </div>
            <div 
              v-if="value.preset === pack.id"
              class="flex-shrink-0 ml-3"
            >
              <div class="w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
          </div>
          
          <!-- 表情预览网格 -->
          <div class="grid grid-cols-7 gap-1 justify-items-center">
            <div
              v-for="emotion in pack.preview"
              :key="emotion"
              :style="{ width: pack.size + 'px', height: pack.size + 'px' }"
              class="bg-gray-100 rounded flex items-center justify-center"
            >
              <img 
                :src="getPresetEmojiUrl(pack.id, emotion)"
                :alt="emotion"
                :style="{ width: pack.size + 'px', height: pack.size + 'px' }"
                class="object-contain rounded"
                @error="handleImageError"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="value.type === 'custom'" class="space-y-6">
      <h4 class="font-medium text-gray-900">{{ $t('emojiConfig.customEmojiPackConfig') }}</h4>
      
      <!-- 基本配置 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- 图片尺寸 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('emojiConfig.maxImageWidth') }}</label>
          <input
            type="number"
            v-model.number="localCustom.size.width"
            min="16"
            max="200"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('emojiConfig.maxImageHeight') }}</label>
          <input
            type="number"
            v-model.number="localCustom.size.height"
            min="16"
            max="200"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
        </div>
      </div>

      <!-- 表情图片上传 -->
      <div class="space-y-4">
        <h5 class="font-medium text-gray-900">{{ $t('emojiConfig.uploadEmojiImages') }}</h5>
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <div
            v-for="emotion in emotionList"
            :key="emotion.key"
            class="space-y-2"
          >
            <div class="text-center">
              <div class="text-lg mb-1">{{ emotion.emoji }}</div>
              <div class="text-xs text-gray-600 flex items-center justify-center gap-1">
                <span>{{ emotion.name }}</span>
                <span v-if="emotion.key === 'neutral'" class="text-red-500">{{ $t('emojiConfig.required') }}</span>
              </div>
            </div>
            
            <div 
              @drop="(e) => handleFileDrop(e, emotion.key)"
              @dragover.prevent
              @dragenter.prevent
              :class="[
                'border-2 border-dashed rounded-lg p-2 text-center cursor-pointer transition-colors aspect-square flex flex-col items-center justify-center',
                value.custom.images[emotion.key]
                  ? 'border-green-300 bg-green-50'
                  : emotion.key === 'neutral'
                    ? 'border-red-300 bg-red-50'
                    : 'border-gray-300 hover:border-gray-400'
              ]"
            >
              <input
                :ref="emotion.key + 'Input'"
                type="file"
                accept=".png,.gif"
                @change="(e) => handleFileSelect(e, emotion.key)"
                class="hidden"
              >
              
              <div v-if="!value.custom.images[emotion.key]" @click="$refs[emotion.key + 'Input'][0]?.click()">
                <svg class="w-6 h-6 text-gray-400 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                </svg>
                <div class="text-xs text-gray-500">{{ $t('emojiConfig.clickToUploadOrDrag') }}</div>
              </div>
              
              <div v-else class="w-full h-full relative">
                <img 
                  v-if="getImagePreview(emotion.key)"
                  :src="getImagePreview(emotion.key)" 
                  :alt="emotion.name"
                  class="w-full h-full object-cover rounded"
                  @error="handleImageError"
                >
                <button
                  @click="removeImage(emotion.key)"
                  class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600"
                >
                  ×
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <div class="text-xs text-gray-500 mt-2">
          {{ $t('emojiConfig.neutralRequiredNotice') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import StorageHelper from '@/utils/StorageHelper.js'

export default {
  props: {
    value: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      localCustom: {
        size: { width: 32, height: 32 }
      },
      presetEmojis: [
        {
          id: 'twemoji32',
          name: this.$t('emojiConfig.twitterEmojiName', { size: 32 }),
          description: this.$t('emojiConfig.twitterEmojiDescription', { size: 32 }),
          size: 32,
          preview: ['neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying']
        },
        {
          id: 'twemoji64',
          name: this.$t('emojiConfig.twitterEmojiName', { size: 64 }),
          description: this.$t('emojiConfig.twitterEmojiDescription', { size: 64 }),
          size: 64,
          preview: ['neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying']
        }
      ]
    }
  },

  computed: {
    // 使用计算属性来获取翻译后的表情名称
    emotionList() {
      return [
        { key: 'neutral', name: this.$t('emojiConfig.emotions.neutral'), emoji: '😶' },
        { key: 'happy', name: this.$t('emojiConfig.emotions.happy'), emoji: '🙂' },
        { key: 'laughing', name: this.$t('emojiConfig.emotions.laughing'), emoji: '😆' },
        { key: 'funny', name: this.$t('emojiConfig.emotions.funny'), emoji: '😂' },
        { key: 'sad', name: this.$t('emojiConfig.emotions.sad'), emoji: '😔' },
        { key: 'angry', name: this.$t('emojiConfig.emotions.angry'), emoji: '😠' },
        { key: 'crying', name: this.$t('emojiConfig.emotions.crying'), emoji: '😭' },
        { key: 'loving', name: this.$t('emojiConfig.emotions.loving'), emoji: '😍' },
        { key: 'embarrassed', name: this.$t('emojiConfig.emotions.embarrassed'), emoji: '😳' },
        { key: 'surprised', name: this.$t('emojiConfig.emotions.surprised'), emoji: '😯' },
        { key: 'shocked', name: this.$t('emojiConfig.emotions.shocked'), emoji: '😱' },
        { key: 'thinking', name: this.$t('emojiConfig.emotions.thinking'), emoji: '🤔' },
        { key: 'winking', name: this.$t('emojiConfig.emotions.winking'), emoji: '😉' },
        { key: 'cool', name: this.$t('emojiConfig.emotions.cool'), emoji: '😎' },
        { key: 'relaxed', name: this.$t('emojiConfig.emotions.relaxed'), emoji: '😌' },
        { key: 'delicious', name: this.$t('emojiConfig.emotions.delicious'), emoji: '🤤' },
        { key: 'kissy', name: this.$t('emojiConfig.emotions.kissy'), emoji: '😘' },
        { key: 'confident', name: this.$t('emojiConfig.emotions.confident'), emoji: '😏' },
        { key: 'sleepy', name: this.$t('emojiConfig.emotions.sleepy'), emoji: '😴' },
        { key: 'silly', name: this.$t('emojiConfig.emotions.silly'), emoji: '😜' },
        { key: 'confused', name: this.$t('emojiConfig.emotions.confused'), emoji: '🙄' }
      ]
    }
  },

  methods: {
    /**
     * 计算文件的 SHA-256 hash
     * @param {File} file - 文件对象
     * @returns {Promise<string>} 文件的 hash 值
     */
    async calculateFileHash(file) {
      const buffer = await file.arrayBuffer()
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
      const hashArray = Array.from(new Uint8Array(hashBuffer))
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
      return hashHex
    },

    setEmojiType(type) {
      // 避免重复设置相同类型
      if (this.value.type === type) return
      
      const newValue = { ...this.value, type }
      
      if (type === 'none') {
        // 选择无表情包
        newValue.preset = ''
        newValue.custom = {
          ...this.value.custom,
          images: this.value.custom.images || {}
        }
      } else if (type === 'preset') {
        // 切换到预设表情时，保留自定义表情数据
        newValue.preset = this.value.preset || 'twemoji32'
        newValue.custom = {
          ...this.value.custom,
          images: this.value.custom.images || {}
        }
      } else if (type === 'custom') {
        newValue.preset = ''
        newValue.custom = {
          ...this.value.custom,
          images: this.value.custom.images || {}
        }
      }
      
      this.$emit('input', newValue)
    },

    selectPresetEmoji(id) {
      // 避免重复选择相同预设
      if (this.value.preset === id) return
      
      // 选择不同的{{ $t('emojiConfig.presetEmojiPack') }}时，保留自定义表情数据
      this.$emit('input', {
        ...this.value,
        preset: id,
        custom: {
          ...this.value.custom,
          images: this.value.custom.images || {}
        }
      })
    },

    handleFileSelect(event, emotionKey) {
      const file = event.target.files[0]
      if (file) {
        this.updateEmojiImage(emotionKey, file)
      }
    },

    handleFileDrop(event, emotionKey) {
      event.preventDefault()
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.updateEmojiImage(emotionKey, files[0])
      }
    },

    async updateEmojiImage(emotionKey, file) {
      const validFormats = ['png', 'gif']
      const fileExtension = file.name.split('.').pop().toLowerCase()
      
      if (!validFormats.includes(fileExtension)) {
        alert(this.$t('emojiConfig.selectValidFormat'))
        return
      }

      // 计算文件 hash
      const fileHash = await this.calculateFileHash(file)
      
      // 获取或初始化 fileMap 和 emotionMap
      const currentCustom = this.value.custom || {}
      const fileMap = { ...(currentCustom.fileMap || {}) }
      const emotionMap = { ...(currentCustom.emotionMap || {}) }
      const images = { ...(currentCustom.images || {}) }
      
      // 检查是否已经存在相同的文件
      let existingEmotions = []
      for (const [emotion, hash] of Object.entries(emotionMap)) {
        if (hash === fileHash && emotion !== emotionKey) {
          existingEmotions.push(emotion)
        }
      }
      
      // 如果检测到相同文件，提示用户
      if (existingEmotions.length > 0) {
        console.log(this.$t('emojiConfig.sharedFileMessage', { emotionKey, existingEmotions: existingEmotions.join(', ') }))
      }
      
      // 更新映射关系
      fileMap[fileHash] = file
      emotionMap[emotionKey] = fileHash
      images[emotionKey] = file  // 保持向后兼容
      
      this.$emit('input', {
        ...this.value,
        custom: {
          ...currentCustom,
          size: this.localCustom.size,
          images,
          fileMap,      // 新增：hash -> File
          emotionMap    // 新增：emotion -> hash
        }
      })

      // 自动保存表情文件到存储（按 hash 保存，避免重复）
      await StorageHelper.saveEmojiFile(`hash_${fileHash}`, file, {
        size: this.localCustom.size,
        format: fileExtension,
        emotions: [...existingEmotions, emotionKey]  // 记录使用该文件的所有表情
      })
    },

    async removeImage(emotionKey) {
      const currentCustom = this.value.custom || {}
      const newImages = { ...currentCustom.images }
      const newEmotionMap = { ...(currentCustom.emotionMap || {}) }
      const newFileMap = { ...(currentCustom.fileMap || {}) }
      
      // 获取要删除的表情对应的 hash
      const fileHash = newEmotionMap[emotionKey]
      
      // 删除表情到 hash 的映射
      delete newImages[emotionKey]
      delete newEmotionMap[emotionKey]
      
      // 检查是否还有其他表情使用同一个文件
      const otherEmotionsUsingFile = Object.values(newEmotionMap).filter(h => h === fileHash)
      
      // 如果没有其他表情使用这个文件，则删除文件本身
      if (otherEmotionsUsingFile.length === 0 && fileHash) {
        delete newFileMap[fileHash]
        // 删除存储中的文件
        await StorageHelper.deleteEmojiFile(`hash_${fileHash}`)
        console.log(this.$t('emojiConfig.fileDeleted', { fileHash }))
      } else {
        console.log(this.$t('emojiConfig.fileRetained', { fileHash }))
      }
      
      this.$emit('input', {
        ...this.value,
        custom: {
          ...currentCustom,
          images: newImages,
          emotionMap: newEmotionMap,
          fileMap: newFileMap
        }
      })
    },

    getPresetEmojiUrl(packId, emotion) {
      const size = packId === 'twemoji64' ? '64' : '32'
      return `./static/twemoji${size}/${emotion}.png`
    },

    getImagePreview(emotionKey) {
      if (this.value.type === 'preset') {
        return this.getPresetEmojiUrl(this.value.preset, emotionKey)
      } else {
        const file = this.value.custom.images[emotionKey]
        // 仅当为 File 或 Blob 时创建预览，避免恢复后占位对象导致报错
        if (file instanceof File || file instanceof Blob) {
          return URL.createObjectURL(file)
        }
        return null
      }
    },

    handleImageError(event) {
      console.warn(this.$t('emojiConfig.imageLoadFailed'), event.target.src)
      // 可以设置一个默认的fallback图片
      event.target.style.display = 'none'
    },

  },
  watch: {
    // 移除可能导致无限递归的 watch
    // 使用 computed 来同步 localCustom，避免双向绑定冲突
    'localCustom.size': {
      handler(newSize) {
        if (this.value.type === 'custom') {
          const currentCustom = this.value.custom
          // 只在尺寸实际值改变时触发更新
          if (JSON.stringify(currentCustom.size) !== JSON.stringify(newSize)) {
            this.$emit('input', {
              ...this.value,
              custom: {
                ...currentCustom,
                size: newSize
              }
            })
          }
        }
      },
      deep: true
    }
  },
  mounted() {
    // 初始化 localCustom
    if (this.value.custom.size) {
      this.localCustom = {
        size: { ...this.value.custom.size }
      }
    }
  }
}

</script>
