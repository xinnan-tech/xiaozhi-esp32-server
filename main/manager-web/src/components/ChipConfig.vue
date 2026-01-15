<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 mb-4">{{ $t('chipConfig.title') }}</h2>
      <p class="text-gray-600 mb-6">
        <span v-if="isLoadingConfig">{{ $t('chipConfig.loadingFromDevice') }}</span>
        <span v-else-if="deviceConfigLoaded">{{ $t('chipConfig.loadedFromDevice') }}</span>
        <span v-else>{{ $t('chipConfig.manualConfig') }}</span>
      </p>
    </div>

    <!-- 加载中状态 -->
    <div v-if="isLoadingConfig" class="space-y-4">
      <div class="bg-blue-50 border-2 border-blue-200 rounded-lg p-6">
        <div class="flex items-center justify-center space-x-3">
          <!-- 加载动画 -->
          <svg class="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <div>
            <h3 class="text-lg font-medium text-blue-900">{{ $t('chipConfig.loadingTitle') }}</h3>
            <p class="text-sm text-blue-700 mt-1">{{ $t('chipConfig.loadingDesc') }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 设备在线：显示自动读取的配置 -->
    <div v-else-if="isDeviceOnline && deviceConfigLoaded" class="space-y-4">
      <div class="bg-green-50 border-2 border-green-200 rounded-lg p-4">
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center">
            <div class="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center mr-2">
              <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </div>
            <h3 class="text-lg font-medium text-green-900">{{ $t('chipConfig.autoLoadedTitle') }}</h3>
          </div>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div class="bg-white rounded-lg p-3">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('chipConfig.chipModel') }}</label>
            <div class="text-base font-semibold text-gray-900">{{ currentChipModel }}</div>
          </div>
          
          <div class="bg-white rounded-lg p-3">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('chipConfig.screenWidth') }}</label>
            <div class="text-base font-semibold text-gray-900">{{ currentDisplay.width }} px</div>
          </div>
          
          <div class="bg-white rounded-lg p-3">
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ $t('chipConfig.screenHeight') }}</label>
            <div class="text-base font-semibold text-gray-900">{{ currentDisplay.height }} px</div>
          </div>
        </div>

        <div class="mt-3 text-sm text-green-700">
          ✓ {{ $t('chipConfig.colorFormat') }} {{ currentDisplay.color }}
        </div>
      </div>

      <!-- 可选：手动修改配置 -->
      <div class="border border-gray-200 rounded-lg p-4">
        <button 
          @click="toggleManualEdit"
          class="flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
          {{ showManualEdit ? $t('chipConfig.collapseManual') : $t('chipConfig.manualEdit') }}
        </button>
        
        <!-- 使用可复用的配置表单 -->
        <div v-if="showManualEdit" class="mt-4">
          <ConfigForm :config="customConfig" /></div>
      </div>
    </div>

    <!-- 设备离线或加载失败：显示手动配置 -->
    <div v-else class="space-y-4">
      <!-- 提示信息 -->
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex items-start">
          <svg class="w-5 h-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
          </svg>
          <div>
            <h4 class="font-medium text-yellow-900">{{ $t('chipConfig.manualConfigDesc') }}</h4>
            <p class="text-sm text-yellow-700 mt-1">
              {{ loadingError || $t('chipConfig.manualConfigHint') }}
            </p>
          </div>
        </div>
      </div>

      <!-- 手动配置表单 -->
      <div class="border-2 border-gray-300 rounded-lg p-4">
        <h3 class="text-lg font-medium text-gray-900 mb-4">{{ $t('chipConfig.manualConfigTitle') }}</h3>
        <ConfigForm :config="customConfig" :show-required="true" />
      </div>
    </div>

    <!-- 下一步按钮 -->
    <div class="flex justify-end">
      <el-button type="primary" @click="handleNext" :disabled="!hasValidConfig">{{ $t('chipConfig.next') }}</el-button>
    </div>
  </div>
</template>

<script>
import { h } from 'vue'
// 定义可复用的配置表单组件（使用渲染函数）
const ConfigForm = {
  name: 'ConfigForm',
  props: {
    config: {
      type: Object,
      required: true
    },
    showRequired: {
      type: Boolean,
      default: false
    }
  },
  render() {
    return h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-4' }, [
      // 芯片型号选择
      h('div', [
        h('label', { class: 'block text-sm font-medium text-gray-700 mb-2' }, [
          this.$t('chipConfig.chipRequired') + ' ',
          this.showRequired ? h('span', { class: 'text-red-500' }, '*') : ''
        ]),
        h('select', {
          class: 'w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
          value: this.config.model,
          on: {
            change: (e) => { this.config.model = e.target.value }
          }
        }, this.$parent.CHIP_OPTIONS.map(option =>
          h('option', { attrs: { value: option.value }, key: option.value }, option.label)
        ))
      ]),

      // 屏幕宽度
      h('div', [
        h('label', { class: 'block text-sm font-medium text-gray-700 mb-2' }, [
          this.$t('chipConfig.widthRequired') + ' ',
          this.showRequired ? h('span', { class: 'text-red-500' }, '*') : ''
        ]),
        h('input', {
          class: 'w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
          attrs: {
            type: 'number',
            min: 128,
            max: 800,
            placeholder: '320',
          },
          domProps: {
            value: this.config.display.width,
          },
          on: {
            input: (e) => { this.config.display.width = Number(e.target.value) }
          }
        })
      ]),

      // 屏幕高度
      h('div', [
        h('label', { class: 'block text-sm font-medium text-gray-700 mb-2' }, [
          this.$t('chipConfig.heightRequired') + ' ',
          this.showRequired ? h('span', { class: 'text-red-500' }, '*') : ''
        ]),
        h('input', {
          class: 'w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
          attrs: {
            type: 'number',
            min: 128,
            max: 600,
            placeholder: '240',
          },
          domProps: {
            value: this.config.display.height,
          },
          on: {
            input: (e) => { this.config.display.height = Number(e.target.value) }
          }
        })
      ])
    ])
  }
}

export default {
  name: 'ChipConfig',
  components: {
    ConfigForm
  },
  props: {
    value: {
      type: Object,
      default: () => ({
        model: '',
        display: {
          width: 320,
          height: 240,
          color: 'RGB565'
        },
      })
    }
  },
  data() {
    return {
      // 设备状态
      deviceInfo: this.$store.state.deviceStatus.deviceInfo,
      isDeviceOnline: this.$store.state.deviceStatus.isDeviceOnline,
      hasToken: this.$store.state.deviceStatus.hasToken,
      
      // 本地状态
      isLoadingConfig: this.$store.state.deviceStatus.hasToken?.value, // 如果有 token，初始状态应该是加载中
      deviceConfigLoaded: false,
      loadingError: '',
      showManualEdit: false,
      
      customConfig: {
        model: '',
        display: {
          width: 320,
          height: 240,
          color: 'RGB565'
        }
      },
      
      // 芯片型号映射（将设备返回的型号映射到选项值）
      chipModelMapping: {
        'ESP32-S3': 'esp32s3',
        'ESP32S3': 'esp32s3',
        'ESP32-C3': 'esp32c3',
        'ESP32C3': 'esp32c3',
        'ESP32-C5': 'esp32c5',
        'ESP32C5': 'esp32c5',
        'ESP32-P4': 'esp32p4',
        'ESP32P4': 'esp32p4',
        'ESP32-C6': 'esp32c6',
        'ESP32C6': 'esp32c6',
        'ESP32': 'esp32'
      }
    }
  },
  computed: {
    // 芯片型号选项常量
    CHIP_OPTIONS() {
      return [
        { value: '', label: this.$t('chipConfig.selectChip') },
        { value: 'esp32s3', label: 'ESP32-S3' },
        { value: 'esp32c3', label: 'ESP32-C3' },
        { value: 'esp32c5', label: 'ESP32-C5' },
        { value: 'esp32c6', label: 'ESP32-C6' },
        { value: 'esp32p4', label: 'ESP32-P4' },
        { value: 'esp32', label: 'ESP32' },
        { value: 'others', label: this.$t('common.other') }
      ]
    },
    
    hasValidConfig() {
      return this.customConfig.model && 
             this.customConfig.display.width && 
             this.customConfig.display.height
    },
    
    currentChipModel() {
      if (!this.customConfig.model) return ''
      return this.customConfig.model.toUpperCase().replace(/ESP32/i, 'ESP32-')
    },
    
    currentDisplay() {
      return this.customConfig.display
    }
  },
  watch: {
    // 监听自定义配置变化
    customConfig: {
      handler(newVal) {
        this.$emit('input', {
          model: newVal.model,
          display: { ...newVal.display }
        })
      },
      deep: true
    },
    
    // 监听设备在线状态变化
    'isDeviceOnline': {
      handler(online) {
        if (online && !this.deviceConfigLoaded) {
          // 设备上线后立即尝试加载配置
          this.isLoadingConfig = true
          this.loadingError = '' // 清除之前的超时错误
          // 使用 setTimeout 确保状态更新后再加载
          setTimeout(() => {
            this.loadConfigFromDevice()
          }, 100)
        }
      }
    },
    
    // 监听设备信息变化
    'deviceInfo': {
      handler() {
        if (this.isDeviceOnline && !this.deviceConfigLoaded) {
          this.loadConfigFromDevice()
        }
      },
      deep: true
    }
  },
  mounted() {
    // 如果没有 token，直接使用手动配置模式
    if (!this.hasToken) {
      this.isLoadingConfig = false
      this.loadingError = this.$t('chipConfig.manualConfigRequired')
      console.log('⚠ 未检测到设备连接，使用手动配置模式')
      return
    }

    // 检查是否已经有有效的设备信息（可能是从其他页面返回）
    const hasValidDeviceInfo = this.isDeviceOnline && 
                             this.deviceInfo.chip && 
                             this.deviceInfo.chip.model !== '未知' &&
                             this.deviceInfo.screen && 
                             this.deviceInfo.screen.resolution !== '未知'
    
    if (hasValidDeviceInfo) {
      // 已有设备信息，立即加载（无延迟）
      console.log('✓ 检测到已缓存的设备信息，立即加载')
      this.loadConfigFromDevice()
    } else if (this.isDeviceOnline) {
      // 设备在线但信息未加载完成，短暂延迟后尝试
      console.log('⏳ 设备在线，等待设备信息加载...')
      this.isLoadingConfig = true
      setTimeout(() => {
        this.loadConfigFromDevice()
      }, 500)
      
      // 设置10秒超时
      setTimeout(() => {
        if (this.isLoadingConfig && !this.deviceConfigLoaded) {
          // 额外检查：确保设备仍然在线，且确实没有加载成功
          if (this.isDeviceOnline) {
            this.isLoadingConfig = false
            if (!this.deviceInfo.chip || this.deviceInfo.chip.model === '未知') {
              this.loadingError = this.$t('chipConfig.chipModelError')
            } else if (!this.deviceInfo.screen || this.deviceInfo.screen.resolution === '未知') {
              this.loadingError = this.$t('chipConfig.resolutionError')
            } else {
              this.loadingError = this.$t('chipConfig.timeoutError')
            }
            console.warn('⚠ 设备配置加载超时:', this.loadingError)
          }
        }
      }, 10000) // 延长到10秒
    } else {
      // 设备暂时离线，保持加载状态，等待设备上线
      console.log('⏳ 等待设备连接...')
      this.isLoadingConfig = true
      
      // 设置10秒超时，如果还未连接则显示手动配置
      setTimeout(() => {
        if (this.isLoadingConfig && !this.deviceConfigLoaded && !this.isDeviceOnline) {
          // 额外检查：只有在设备确实还未上线时才显示超时错误
          this.isLoadingConfig = false
          this.loadingError = this.$t('chipConfig.manualConfigHint')
          console.warn('⚠ 等待设备连接超时')
        }
      }, 10000) // 延长到10秒，给设备更多连接时间
    }
  },
  methods: {
    // 从设备信息加载配置
    loadConfigFromDevice() {
      try {
        // 检查设备是否在线
        if (!this.isDeviceOnline) {
          // 设备离线时，如果还在加载状态，不立即失败（可能正在连接）
          if (!this.isLoadingConfig) {
            this.loadingError = this.$t('chipConfig.deviceOffline')
            this.deviceConfigLoaded = false
          }
          return false
        }

        // 获取芯片型号
        const chipModel = this.deviceInfo.chip?.model
        if (!chipModel || chipModel === '未知') {
          // 如果还在加载期间（5秒超时前），不立即失败，等待数据更新
          // 只在明确失败或超时后才设置错误
          return false
        }

        // 映射芯片型号
        let mappedChip = this.chipModelMapping[chipModel.toUpperCase()] ||
                         this.chipModelMapping[chipModel] ||
                         chipModel.toLowerCase().replace(/-/g, '')

        // 如果映射结果不在已知选项中，设置为 others
        const validChipModels = ['esp32s3', 'esp32c3', 'esp32c5', 'esp32p4', 'esp32c6', 'esp32', 'others']
        if (!validChipModels.includes(mappedChip)) {
          mappedChip = 'others'
        }

        // 获取屏幕分辨率
        const resolution = this.deviceInfo.screen?.resolution
        if (!resolution || resolution === '未知') {
          // 同样，在加载期间不立即失败
          return false
        }

        // 解析分辨率
        const [width, height] = resolution.split('x').map(Number)
        if (!width || !height || isNaN(width) || isNaN(height)) {
          this.loadingError = this.$t('chipConfig.resolutionFormatError')
          this.deviceConfigLoaded = false
          this.isLoadingConfig = false
          return false
        }

        // 设置配置
        this.customConfig = {
          model: mappedChip,
          display: {
            width,
            height,
            color: 'RGB565'
          }
        }

        // 更新父组件
        this.$emit('input', {
          model: mappedChip,
          display: {
            width,
            height,
            color: 'RGB565'
          },
        })

        this.deviceConfigLoaded = true
        this.loadingError = ''
        this.isLoadingConfig = false
        console.log('✓ 设备配置加载成功:', { chip: mappedChip, width, height })
        return true

      } catch (error) {
        console.error('加载设备配置失败:', error)
        this.loadingError = this.$t('chipConfig.loadingError')
        this.deviceConfigLoaded = false
        this.isLoadingConfig = false
        return false
      }
    },
    
    // 切换手动编辑
    toggleManualEdit() {
      this.showManualEdit = !this.showManualEdit
    },
    
    // 下一步
    handleNext() {
      if (this.hasValidConfig) {
        this.$emit('next')
      }
    }
  }
}
</script>
