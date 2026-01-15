<template>
  <div class="space-y-6">
    <div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">{{ $t('backgroundConfig.title') }}</h3>
      <p class="text-gray-600">{{ $t('backgroundConfig.description') }}</p>
    </div>

    <div class="space-y-4">
      <h4 class="font-medium text-gray-900 flex items-center">
        <svg class="w-5 h-5 mr-2 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"/>
        </svg>
        {{ $t('backgroundConfig.lightMode') }}
      </h4>
      
      <div class="border border-gray-200 rounded-lg p-4 space-y-4">
        <div class="flex space-x-4">
          <button
            @click="setLightType('color')"
            :class="[
              'px-3 py-2 text-sm border rounded transition-colors',
              value.light.backgroundType === 'color'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-300 hover:border-gray-400'
            ]"
          >
            {{ $t('backgroundConfig.solidBackground') }}
          </button>
          <button
            @click="setLightType('image')"
            :class="[
              'px-3 py-2 text-sm border rounded transition-colors',
              value.light.backgroundType === 'image'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-300 hover:border-gray-400'
            ]"
          >
            {{ $t('backgroundConfig.imageBackground') }}
          </button>
        </div>

        <div v-if="value.light.backgroundType === 'color'" class="space-y-3">
          <div class="flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.backgroundColor') }}</label>
            <div class="flex items-center space-x-2">
              <input
                type="color"
                v-model="lightColor"
                class="w-10 h-10 border border-gray-300 rounded cursor-pointer"
              >
              <input
                type="text"
                v-model="lightColor"
                class="border border-gray-300 rounded px-3 py-2 text-sm font-mono w-24"
              >
            </div>
            <div 
              :style="{ backgroundColor: lightColor }"
              class="w-16 h-10 border border-gray-300 rounded shadow-inner"
            ></div>
          </div>
          <div class="flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.textColor') }}</label>
            <div class="flex items-center space-x-2">
              <input
                type="color"
                v-model="lightTextColor"
                class="w-10 h-10 border border-gray-300 rounded cursor-pointer"
              >
              <input
                type="text"
                v-model="lightTextColor"
                class="border border-gray-300 rounded px-3 py-2 text-sm font-mono w-24"
              >
            </div>
            <div 
              :style="{ backgroundColor: lightTextColor }"
              class="w-16 h-10 border border-gray-300 rounded shadow-inner"
            ></div>
          </div>
        </div>

        <div v-if="value.light.backgroundType === 'image'" class="space-y-3">
          <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.backgroundImage') }}</label>
          <div 
            @drop="(e) => handleFileDrop(e, 'light')"
            @dragover.prevent
            @dragenter.prevent
            :class="[
              'border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors',
              value.light.backgroundImage
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
            ]"
          >
            <input
              ref="lightImageInput"
              type="file"
              accept="image/*"
              @change="(e) => handleFileSelect(e, 'light')"
              class="hidden"
            >
            
            <div v-if="!value.light.backgroundImage" @click="$refs.lightImageInput.click()">
              <svg class="mx-auto h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              <p class="mt-1 text-sm text-gray-600">{{ $t('backgroundConfig.clickOrDragToUpload') }}</p>
            </div>
            
            <div v-else class="space-y-2">
              <img 
                :src="getImagePreview('light')"
                class="max-w-32 max-h-32 mx-auto rounded shadow"
              >
              <p class="text-sm text-green-700 font-medium">{{ value.light.backgroundImage.name }}</p>
              <button
                @click="removeImage('light')"
                class="text-red-600 hover:text-red-500 text-sm"
              >
                {{ $t('backgroundConfig.removeImage') }}
              </button>
            </div>
          </div>
          
          <div class="flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.textColor') }}</label>
            <div class="flex items-center space-x-2">
              <input
                type="color"
                v-model="lightTextColor"
                class="w-10 h-10 border border-gray-300 rounded cursor-pointer"
              >
              <input
                type="text"
                v-model="lightTextColor"
                class="border border-gray-300 rounded px-3 py-2 text-sm font-mono w-24"
              >
            </div>
            <div 
              :style="{ backgroundColor: lightTextColor }"
              class="w-16 h-10 border border-gray-300 rounded shadow-inner"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <h4 class="font-medium text-gray-900 flex items-center">
        <svg class="w-5 h-5 mr-2 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"/>
        </svg>
        {{ $t('backgroundConfig.darkMode') }}
      </h4>
      
      <div class="border border-gray-200 rounded-lg p-4 space-y-4">
        <div class="flex space-x-4">
          <button
            @click="setDarkType('color')"
            :class="[
              'px-3 py-2 text-sm border rounded transition-colors',
              value.dark.backgroundType === 'color'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-300 hover:border-gray-400'
            ]"
          >
            {{ $t('backgroundConfig.solidBackground') }}
          </button>
          <button
            @click="setDarkType('image')"
            :class="[
              'px-3 py-2 text-sm border rounded transition-colors',
              value.dark.backgroundType === 'image'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-300 hover:border-gray-400'
            ]"
          >
            {{ $t('backgroundConfig.imageBackground') }}
          </button>
        </div>

        <div v-if="value.dark.backgroundType === 'color'" class="space-y-3">
          <div class="flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.backgroundColor') }}</label>
            <div class="flex items-center space-x-2">
              <input
                type="color"
                v-model="darkColor"
                class="w-10 h-10 border border-gray-300 rounded cursor-pointer"
              >
              <input
                type="text"
                v-model="darkColor"
                class="border border-gray-300 rounded px-3 py-2 text-sm font-mono w-24"
              >
            </div>
            <div 
              :style="{ backgroundColor: darkColor }"
              class="w-16 h-10 border border-gray-300 rounded shadow-inner"
            ></div>
          </div>
          <div class="flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.textColor') }}</label>
            <div class="flex items-center space-x-2">
              <input
                type="color"
                v-model="darkTextColor"
                class="w-10 h-10 border border-gray-300 rounded cursor-pointer"
              >
              <input
                type="text"
                v-model="darkTextColor"
                class="border border-gray-300 rounded px-3 py-2 text-sm font-mono w-24"
              >
            </div>
            <div 
              :style="{ backgroundColor: darkTextColor }"
              class="w-16 h-10 border border-gray-300 rounded shadow-inner"
            ></div>
          </div>
        </div>

        <div v-if="value.dark.backgroundType === 'image'" class="space-y-3">
          <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.backgroundImage') }}</label>
          <div 
            @drop="(e) => handleFileDrop(e, 'dark')"
            @dragover.prevent
            @dragenter.prevent
            :class="[
              'border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors',
              value.dark.backgroundImage
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
            ]"
          >
            <input
              ref="darkImageInput"
              type="file"
              accept="image/*"
              @change="(e) => handleFileSelect(e, 'dark')"
              class="hidden"
            >
            
            <div v-if="!value.dark.backgroundImage" @click="$refs.darkImageInput.click()">
              <svg class="mx-auto h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              <p class="mt-1 text-sm text-gray-600">{{ $t('backgroundConfig.clickOrDragToUpload') }}</p>
            </div>
            
            <div v-else class="space-y-2">
              <img 
                :src="getImagePreview('dark')"
                class="max-w-32 max-h-32 mx-auto rounded shadow"
              >
              <p class="text-sm text-green-700 font-medium">{{ value.dark.backgroundImage.name }}</p>
              <button
                @click="removeImage('dark')"
                class="text-red-600 hover:text-red-500 text-sm"
              >
                {{ $t('backgroundConfig.removeImage') }}
              </button>
            </div>
          </div>
          
          <div class="flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.textColor') }}</label>
            <div class="flex items-center space-x-2">
              <input
                type="color"
                v-model="darkTextColor"
                class="w-10 h-10 border border-gray-300 rounded cursor-pointer"
              >
              <input
                type="text"
                v-model="darkTextColor"
                class="border border-gray-300 rounded px-3 py-2 text-sm font-mono w-24"
              >
            </div>
            <div 
              :style="{ backgroundColor: darkTextColor }"
              class="w-16 h-10 border border-gray-300 rounded shadow-inner"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览区域 -->
    <div class="space-y-4">
      <h4 class="font-medium text-gray-900">{{ $t('backgroundConfig.backgroundPreview') }}</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="space-y-2">
          <div class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.lightModePreview') }}</div>
          <div 
            :style="getLightPreviewStyle()"
            class="h-32 border border-gray-300 rounded-lg flex items-center justify-center text-sm relative overflow-hidden"
          >
            <div class="absolute inset-0 bg-white bg-opacity-10 flex items-center justify-center rounded-lg">
              <span :style="{ color: value.light.textColor }">
                {{ $t('backgroundConfig.chatArea') }}
              </span>
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <div class="text-sm font-medium text-gray-700">{{ $t('backgroundConfig.darkModePreview') }}</div>
          <div 
            :style="getDarkPreviewStyle()"
            class="h-32 border border-gray-300 rounded-lg flex items-center justify-center text-sm relative overflow-hidden"
          >
            <div class="absolute inset-0 bg-black bg-opacity-10 flex items-center justify-center rounded-lg">
              <span :style="{ color: value.dark.textColor }">
                {{ $t('backgroundConfig.chatArea') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h5 class="font-medium text-blue-900 mb-2">{{ $t('backgroundConfig.quickConfig') }}</h5>
      <div class="flex flex-wrap gap-2">
        <button
          @click="applyPresetColors('#ffffff', '#1f2937')"
          class="px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50"
        >
          {{ $t('backgroundConfig.defaultColors') }}
        </button>
        <button
          @click="applyPresetColors('#f5f5f4', '#374151')"
          class="px-3 py-1 text-sm bg-stone-100 border border-gray-300 rounded hover:bg-stone-200"
        >
          {{ $t('backgroundConfig.stoneTexture') }}
        </button>
        <button
          @click="applyPresetColors('#fef7cd', '#7c2d12')"
          class="px-3 py-1 text-sm bg-yellow-100 border border-gray-300 rounded hover:bg-yellow-200"
        >
          {{ $t('backgroundConfig.sunnyColors') }}
        </button>
        <button
          @click="applyPresetColors('#e0f2fe', '#1e40af')"
          class="px-3 py-1 text-sm bg-sky-100 border border-gray-300 rounded hover:bg-sky-200"
        >
          {{ $t('backgroundConfig.skyBlue') }}
        </button>
        <button
          @click="applyPresetColors('#fdf2f8', '#be185d')"
          class="px-3 py-1 text-sm bg-pink-100 border border-gray-300 rounded hover:bg-pink-200"
        >
          {{ $t('backgroundConfig.romanticPink') }}
        </button>
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

  computed: {
    lightColor: {
      get() {
        return this.value.light.backgroundColor
      },
      set(value) {
        this.updateLightColor(value)
      }
    },

    darkColor: {
      get() {
        return this.value.dark.backgroundColor
      },
      set(value) {
        this.updateDarkColor(value)
      }
    },

    lightTextColor: {
      get() {
        return this.value.light.textColor
      },
      set(value) {
        this.updateLightTextColor(value)
      }
    },

    darkTextColor: {
      get() {
        return this.value.dark.textColor
      },
      set(value) {
        this.updateDarkTextColor(value)
      }
    }
  },

  methods: {
    setLightType(backgroundType) {
      this.$emit('input', {
        ...this.value,
        light: {
          ...this.value.light,
          backgroundType,
          backgroundImage: backgroundType === 'image' ? this.value.light.backgroundImage : null
        }
      })
    },

    setDarkType(backgroundType) {
      this.$emit('input', {
        ...this.value,
        dark: {
          ...this.value.dark,
          backgroundType,
          backgroundImage: backgroundType === 'image' ? this.value.dark.backgroundImage : null
        }
      })
    },

    updateLightColor(backgroundColor) {
      this.$emit('input', {
        ...this.value,
        light: {
          ...this.value.light,
          backgroundColor
        }
      })
    },

    updateDarkColor(backgroundColor) {
      this.$emit('input', {
        ...this.value,
        dark: {
          ...this.value.dark,
          backgroundColor
        }
      })
    },

    updateLightTextColor(textColor) {
      this.$emit('input', {
        ...this.value,
        light: {
          ...this.value.light,
          textColor
        }
      })
    },

    updateDarkTextColor(textColor) {
      this.$emit('input', {
        ...this.value,
        dark: {
          ...this.value.dark,
          textColor
        }
      })
    },

    handleFileSelect(event, mode) {
      const file = event.target.files[0]
      if (file) {
        this.updateBackgroundImage(mode, file)
      }
    },

    handleFileDrop(event, mode) {
      event.preventDefault()
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.updateBackgroundImage(mode, files[0])
      }
    },

    async updateBackgroundImage(mode, file) {
      if (file && file.type.startsWith('image/')) {
        this.$emit('input', {
          ...this.value,
          [mode]: {
            ...this.value[mode],
            backgroundImage: file
          }
        })

        // 自动保存背景图片到存储
        await StorageHelper.saveBackgroundFile(mode, file)
      } else {
        alert(this.$t('backgroundConfig.selectValidImage'))
      }
    },

    async removeImage(mode) {
      this.$emit('input', {
        ...this.value,
        [mode]: {
          ...this.value[mode],
          backgroundImage: null
        }
      })
      
      // 清空文件输入
      if (mode === 'light' && this.$refs.lightImageInput) {
        this.$refs.lightImageInput.value = ''
      }
      if (mode === 'dark' && this.$refs.darkImageInput) {
        this.$refs.darkImageInput.value = ''
      }

      // 删除存储中的背景文件
      await StorageHelper.deleteBackgroundFile(mode)
    },

    getImagePreview(mode) {
      const backgroundImage = this.value[mode].backgroundImage
      return backgroundImage ? URL.createObjectURL(backgroundImage) : null
    },

    getLightPreviewStyle() {
      if (this.value.light.backgroundType === 'image' && this.value.light.backgroundImage) {
        return {
          backgroundImage: `url(${this.getImagePreview('light')})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }
      }
      return {
        backgroundColor: this.value.light.backgroundColor
      }
    },

    getDarkPreviewStyle() {
      if (this.value.dark.backgroundType === 'image' && this.value.dark.backgroundImage) {
        return {
          backgroundImage: `url(${this.getImagePreview('dark')})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }
      }
      return {
        backgroundColor: this.value.dark.backgroundColor
      }
    },

    applyPresetColors(lightColor, darkColor) {
      // 根据背景色智能选择文字色
      const lightTextColor = this.isLightColor(lightColor) ? '#000000' : '#ffffff'
      const darkTextColor = this.isLightColor(darkColor) ? '#000000' : '#ffffff'
      
      this.$emit('input', {
        ...this.value,
        light: {
          ...this.value.light,
          backgroundType: 'color',
          backgroundColor: lightColor,
          textColor: lightTextColor,
          backgroundImage: null
        },
        dark: {
          ...this.value.dark,
          backgroundType: 'color',
          backgroundColor: darkColor,
          textColor: darkTextColor,
          backgroundImage: null
        }
      })
    },

    // 判断颜色是否为浅色
    isLightColor(color) {
      const hex = color.replace('#', '')
      const r = parseInt(hex.substr(0, 2), 16)
      const g = parseInt(hex.substr(2, 2), 16)
      const b = parseInt(hex.substr(4, 2), 16)
      const brightness = (r * 299 + g * 587 + b * 114) / 1000
      return brightness > 128
    }
  }
}
</script>
