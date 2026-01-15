<template>
  <div class="space-y-6">
    <div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">{{ $t('fontConfig.title') }}</h3>
      <p class="text-gray-600">{{ $t('fontConfig.description') }}</p>
    </div>

    <!-- 字体类型选择 -->
    <div class="space-y-4">
      <div class="flex justify-center space-x-4">
        <el-button
          @click="setFontType('none')"
          :type="value.type === 'none' ? 'primary' : 'default'"
        >
          {{ $t('fontConfig.noFonts') }}
        </el-button>
        <el-button
          @click="setFontType('preset')"
          :type="value.type === 'preset' ? 'primary' : 'default'"
        >
          {{ $t('fontConfig.presetFonts') }}
        </el-button>
        <el-button
          @click="setFontType('custom')"
          :type="value.type === 'custom' ? 'primary' : 'default'"
        >
          {{ $t('fontConfig.customFonts') }}
        </el-button>
      </div>
    </div>

    <div v-if="value.type === 'none'" class="space-y-4">
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
        <p class="mt-2 text-gray-600">{{ $t('fontConfig.noFontsDescription') }}</p>
      </div>
    </div>

    <div v-if="value.type === 'preset'" class="space-y-4">
      <h4 class="font-medium text-gray-900">{{ $t('fontConfig.presetFonts') }}</h4>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div
          v-for="font in presetFonts"
          :key="font.id"
          @click="selectPresetFont(font.id)"
          :class="[
            'border-2 rounded-lg p-4 cursor-pointer transition-all',
            value.preset === font.id
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <h5 class="font-medium text-gray-900 mb-1">{{ font.name }}</h5>
              <div class="text-sm text-gray-600 space-y-1">
                <div>{{ $t('fontConfig.fontSize') }} {{ font.size }}px</div>
                <div>{{ $t('fontConfig.bitDepth') }} {{ font.bpp }}bpp</div>
                <div>{{ $t('fontConfig.charset') }} {{ font.charset }}</div>
                <div>{{ $t('fontConfig.fileSize') }} {{ font.fileSize }}</div>
              </div>
            </div>
            <div 
              v-if="value.preset === font.id"
              class="flex-shrink-0 ml-3"
            >
              <div class="w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="value.type === 'custom'" class="space-y-6">
      <h4 class="font-medium text-gray-900">{{ $t('fontConfig.customFonts') }}</h4>
      
      <!-- 文件上传 -->
      <div class="space-y-2">
        <label class="block text-sm font-medium text-gray-700">{{ $t('fontConfig.fontFile') }}</label>
        <div 
          @drop="handleFileDrop"
          @dragover.prevent
          @dragenter.prevent
          class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".ttf,.woff,.woff2"
            @change="handleFileSelect"
            class="hidden"
          >
          <div v-if="!value.custom.file">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            <div class="mt-2">
              <button 
                @click="openFileDialog"
                class="text-primary-600 hover:text-primary-500 font-medium"
              >
                {{ $t('fontConfig.clickSelectFontFile') }}
              </button>
              <p class="text-gray-500">{{ $t('fontConfig.orDragFileHere') }}</p>
            </div>
            <p class="text-xs text-gray-400 mt-1">{{ $t('fontConfig.supportedFormats') }}</p>
          </div>
          <div v-else class="text-green-600">
            <svg class="mx-auto h-8 w-8" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <p class="mt-1 font-medium">{{ value.custom.file?.name }}</p>
            <button 
              @click="clearFile"
              class="text-red-600 hover:text-red-500 text-sm mt-1"
            >
              {{ $t('fontConfig.removeFile') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 字体配置选项 -->
      <div v-if="value.custom.file" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('fontConfig.fontSizePx') }}</label>
          <input
            type="number"
            v-model.number="localCustom.size"
            min="8"
            max="80"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
          <p class="text-xs text-gray-500 mt-1">{{ $t('fontConfig.range') }} 8-80px</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('fontConfig.bitDepthBpp') }}</label>
          <select 
            v-model="localCustom.bpp"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option :value="1">{{ $t('fontConfig.monochrome') }}</option>
            <option :value="2">{{ $t('fontConfig.fourColors') }}</option>
            <option :value="4">{{ $t('fontConfig.sixteenColors') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">{{ $t('fontConfig.characterSet') }}</label>
          <select 
            v-model="localCustom.charset"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="qwen">{{ $t('fontConfig.qwen18409') }}</option>
            <option value="deepseek">{{ $t('fontConfig.deepseekR1') }}</option>
            <option value="gb2312">{{ $t('fontConfig.gb2312') }}</option>
            <option value="latin">{{ $t('fontConfig.latin1') }}</option>
            <option value="full">{{ $t('fontConfig.fullCharset') }}</option>
          </select>
        </div>
      </div>

    </div>

    <!-- 隐藏字幕选项 -->
    <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div class="flex-1">
        <h4 class="font-medium text-gray-900">{{ $t('fontConfig.hideSubtitle') }}</h4>
        <p class="text-sm text-gray-500 mt-1">{{ $t('fontConfig.hideSubtitleDescription') }}</p>
      </div>
      <div class="ml-4">
        <label class="relative inline-flex items-center cursor-pointer">
          <el-switch v-model="value.hide_subtitle"></el-switch>
        </label>
      </div>
    </div>

  </div>
</template>

<script>
import Vue from 'vue'
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
      presetFontsBase: [
        {
          id: 'font_puhui_deepseek_14_1',
          size: 14,
          bpp: 1,
          fileSize: '~180KB'
        },
        {
          id: 'font_puhui_deepseek_16_4',
          size: 16,
          bpp: 4,
          fileSize: '~720KB'
        },
        {
          id: 'font_puhui_deepseek_20_4',
          size: 20,
          bpp: 4,
          fileSize: '~1.1MB'
        },
        {
          id: 'font_puhui_deepseek_30_4',
          size: 30,
          bpp: 4,
          fileSize: '~2.5MB'
        },
        {
          id: 'font_noto_qwen_14_1',
          size: 14,
          bpp: 1,
          fileSize: '~626KB'
        },
        {
          id: 'font_noto_qwen_16_4',
          size: 16,
          bpp: 4,
          fileSize: '~2.0MB'
        },
        {
          id: 'font_noto_qwen_20_4',
          size: 20,
          bpp: 4,
          fileSize: '~2.9MB'
        },
        {
          id: 'font_noto_qwen_30_4',
          size: 30,
          bpp: 4,
          fileSize: '~5.8MB'
        }
      ],
      localCustom: {
        size: 20,
        bpp: 4,
        charset: 'qwen'
      },
      isUpdatingFromProps: false
    }
  },
  computed: {
    presetFonts() {
      return this.presetFontsBase.map(font => {
        // 根据字体ID判断字符集
        let charsetText
        if (font.id.startsWith('font_puhui_deepseek_')) {
          charsetText = this.$t('fontConfig.charsetDeepseek')
        } else if (font.id.startsWith('font_noto_qwen_')) {
          charsetText = this.$t('fontConfig.charsetQwen')
        }
        
        return {
          ...font,
          name: this.$t('fontConfig.presetFontNames.' + font.id),
          charset: charsetText
        }
      })
    }
  },
  watch: {
    'localCustom': {
      handler(newVal) {
        if (this.isUpdatingFromProps) return
        
        if (this.value.type === 'custom' && this.value.custom.file) {
          this.$emit('input', {
            ...this.value,
            custom: {
              ...this.value.custom,
              ...newVal
            }
          })
        }
      },
      deep: true
    },
    'value.custom': {
      handler(newVal) {
        if (newVal.size && newVal.bpp && newVal.charset) {
          this.isUpdatingFromProps = true
          this.localCustom = {
            size: newVal.size,
            bpp: newVal.bpp,
            charset: newVal.charset
          }
          // 在下一个 tick 重置标志
          this.$nextTick(() => {
            this.isUpdatingFromProps = false
          })
        }
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    openFileDialog() {
      this.$refs.fileInput.click()
    },
    setFontType(type) {
      this.$emit('input', {
        ...this.value,
        type,
        preset: type === 'preset' ? (this.value.preset || 'font_puhui_deepseek_20_4') : '',
        custom: {
          ...this.value.custom,
          file: this.value.custom.file || null
        }
      })
    },
    selectPresetFont(id) {
      this.$emit('input', {
        ...this.value,
        preset: id,
        custom: {
          ...this.value.custom,
          file: this.value.custom.file || null
        }
      })
    },
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.updateCustomFile(file)
      }
    },
    handleFileDrop(event) {
      event.preventDefault()
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.updateCustomFile(files[0])
      }
    },
    async updateCustomFile(file) {
      if (file && (file.type.includes('font') || file.name.toLowerCase().match(/\.(ttf|woff|woff2)$/))) {
        this.$emit('input', {
          ...this.value,
          custom: {
            ...this.value.custom,
            file,
            ...this.localCustom
          }
        })

        // 自动保存文件到存储
        await StorageHelper.saveFontFile(file, this.localCustom)
      } else {
        alert(this.$t('fontConfig.selectValidFontFile'))
      }
    },
    async clearFile() {
      this.$emit('input', {
        ...this.value,
        custom: {
          ...this.value.custom,
          file: null
        }
      })
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = ''
      }

      // 删除存储中的文件
      await StorageHelper.deleteFontFile()
    },
  }
}
</script>
