<template>
  <div class="min-h-screen voice-box">
  <HeaderBar />
    <!-- Header -->
      <!-- <header class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
            <h1 class="text-2xl font-bold text-gray-900">{{ $t('header.title') }}</h1>
            <div class="flex items-center space-x-4">
              <DeviceStatus />
            </div>
          </div>
        </div>
      </header> -->

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
      <div>
    <!-- 配置状态提示（右下角浮动通知） -->
    <div
      v-if="hasStoredConfig"
      class="fixed bottom-4 right-4 z-50 bg-blue-50 border border-blue-200 rounded-lg p-4 shadow-lg transition-opacity duration-300 min-w-[300px]"
      @mouseenter="resetAutoHideTimer"
    >
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center">
          <svg class="w-5 h-5 text-blue-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
          </svg>
          <span class="text-blue-800 font-medium">{{ $t('configNotice.title') }}</span>
        </div>
        <button 
          @click="closeConfigNotice"
          class="text-gray-500 hover:text-gray-700"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      <p class="text-blue-600 text-sm mb-3">
        {{ $t('configNotice.message') }}
      </p>
      <div class="flex justify-end space-x-2">
        <button 
          @click="confirmReset"
          class="px-3 py-1 text-sm text-red-600 hover:text-red-800 font-medium"
        >
          {{ $t('configNotice.restart') }}
        </button>
      </div>
    </div>

    <!-- Step Indicator -->
    <div class="flex items-center justify-center mb-8">
      <div v-for="(step, index) in steps" :key="index" class="flex items-center">
        <div class="flex flex-col items-center">
          <div :class="getStepClass(index)">
            {{ index + 1 }}
          </div>
          <span class="text-sm mt-2 text-gray-600">{{ step.titleKey }}</span>
        </div>
        <div v-if="index < steps.length - 1" class="w-16 h-0.5 bg-white mx-4"></div>
      </div>
    </div>

    <!-- Step Content -->
    <div class="bg-white rounded-lg p-6">
      <ChipConfig 
        v-if="currentStep === 0"
        v-model="config.chip"
        @next="nextStep"
      />
      
      <ThemeDesign 
        v-if="currentStep === 1"
        v-model="config.theme"
        :chipModel="config.chip.model"
        :activeTab="activeThemeTab"
        @next="nextStep"
        @prev="prevStep"
        @tabChange="handleThemeTabChange"
      />
      
      <GenerateSummary 
        v-if="currentStep === 2"
        :config="config"
        @generate="handleGenerate"
        @prev="prevStep"
      />
    </div>

      <!-- Generate Modal -->
      <GenerateModal
        v-if="showGenerateModal"
        :config="config"
        @close="showGenerateModal = false"
        @generate="handleModalGenerate"
        @startFlash="handleStartFlash"
        @cancelFlash="handleCancelFlash"
      />

      <!-- Reset Confirmation Modal -->
      <!-- 移除重置确认对话框 -->
    </div>
    </main>
  </div>
</template>
<script>
import HeaderBar from "@/components/HeaderBar.vue";
import ChipConfig from '@/components/ChipConfig.vue'
import DeviceStatus from '@/components/DeviceStatus.vue'

import ThemeDesign from '@/components/ThemeDesign.vue'
import GenerateSummary from '@/components/GenerateSummary.vue'
import GenerateModal from '@/components/GenerateModal.vue'
import configStorage from '@/utils/ConfigStorage.js'
import AssetsBuilder from '@/utils/AssetsBuilder.js'
import WebSocketTransfer from '@/utils/WebSocketTransfer.js'

export default {
  name: "VoiceBoxCustom",
  components: {
    HeaderBar,
    ChipConfig,
    DeviceStatus,
    ThemeDesign,
    GenerateSummary,
    GenerateModal
  },
  data() {
    return {
      currentStep: 0,
      showGenerateModal: false,
      activeThemeTab: "wakeword",
      hasStoredConfig: false,
      isAutoSaveEnabled: false,
      isAutoSaveEnabled: false,
      isLoading: false,
      assetsBuilder: new AssetsBuilder(),
      autoHideTimer: null,
      webSocketTransfer: null,
      steps: [
        { titleKey: this.$t('steps.chip'), key: 'chip' },
        { titleKey: this.$t('steps.theme'), key: 'theme' },
        { titleKey: this.$t('steps.generate'), key: 'generate' }
      ],
      config: {
        chip: {
          model: '',
          display: {
            width: 320,
            height: 240,
            color: 'RGB565'
          }
        },
        theme: {
          wakeword: {
            type: 'none',
            preset: '',
            custom: {
              name: '',
              command: '',
              threshold: 20,
              duration: 3000,
              model: 'mn6_cn'
            }
          },
          font: {
            type: 'none',
            preset: '',
            hide_subtitle: false,
            custom: {
              file: null,
              size: 20,
              bpp: 4,
              charset: 'deepseek'
            }
          },
          emoji: {
            type: 'none',
            preset: '',
            custom: {
              size: { width: 160, height: 120 },
              images: {}
            }
          },
          skin: {
            light: {
              backgroundType: 'color',
              backgroundColor: '#ffffff',
              textColor: '#000000',
              backgroundImage: null
            },
            dark: {
              backgroundType: 'color', 
              backgroundColor: '#121212',
              textColor: '#ffffff',
              backgroundImage: null
            }
          }
        }
      }
    }
  },
  methods: {
    getStepClass(index) {
      if (index < this.currentStep) return 'step-indicator completed'
      if (index === this.currentStep) return 'step-indicator active'
      return 'step-indicator inactive'
    },
    async nextStep() {
      if (this.currentStep < this.steps.length - 1) {
        this.currentStep += 1;
        
        // 启用自动保存（如果还没启用的话）
        if (!this.isAutoSaveEnabled) {
          this.isAutoSaveEnabled = true
          await this.saveConfigToStorage()
        }
      }
    },
    prevStep() {
      if (this.currentStep > 0) {
        this.currentStep -= 1;
      }
    },
    handleGenerate() {
      this.showGenerateModal = true
    },
    handleModalGenerate(selectedItems) {
      console.log("🚀 ~ selectedItems:", selectedItems)
    },
    // 获取URL参数中的token
    getToken() {
      const urlParams = new URLSearchParams(window.location.search)
      return urlParams.get('token')
    },
    // 调用MCP工具（使用共享的方法）
    async callMcpTool(toolName, params = {}) {
      return await this.$store.state.deviceStatus.callMcpTool(toolName, params)
    },
    // 处理开始在线烧录
    async handleStartFlash(flashData) {
      const { blob, onProgress, onComplete, onError } = flashData

      try {
        const token = getToken()
        if (!token) {
          throw new Error(t('flashProgress.authTokenMissing'))
        }

        // 步骤1: 检查设备状态
        onProgress(5, t('flashProgress.checkingDeviceStatus'))
        try {
          const deviceStatus = await this.callMcpTool('self.get_device_status')
          if (!deviceStatus) {
            throw new Error(t('flashProgress.deviceOfflineOrUnresponsive', { error: t('flashProgress.unableToGetDeviceStatus') }))
          }
        } catch (error) {
          console.error('检查设备状态失败:', error)
          onError(t('flashProgress.deviceOfflineOrUnresponsive', { error: error.message }))
          return
        }

        // 步骤2: 初始化WebSocket传输并获取下载URL
        onProgress(15, t('flashProgress.initializingTransferService'))
        this.webSocketTransfer = new WebSocketTransfer(token)

        // 创建一个Promise来等待下载URL准备好
        let downloadUrlReady = null
        const downloadUrlPromise = new Promise((resolve, reject) => {
          downloadUrlReady = resolve
        })

        // 创建一个Promise来等待transfer_started事件
        let transferStartedResolver = null
        const transferStartedPromise = new Promise((resolve, reject) => {
          transferStartedResolver = resolve
        })

        // 初始化WebSocket会话（只建立连接和获取URL）
        this.webSocketTransfer.onTransferStarted = () => {
          // 当收到transfer_started事件时，resolve等待的Promise
          if (transferStartedResolver) {
            transferStartedResolver()
            transferStartedResolver = null
          }
        }

        await this.webSocketTransfer.initializeSession(
          blob,
          (progress, step) => {
            // 初始化进度：15-30
            onProgress(15 + progress * 0.75, step)
          },
          (error) => {
            console.error('WebSocket初始化失败:', error)
            onError(t('flashProgress.initializeTransferFailed', { error: error.message }))
          },
          (downloadUrl) => {
            downloadUrlReady(downloadUrl)
          }
        )

        // 等待下载URL准备好
        const downloadUrl = await downloadUrlPromise

        // 步骤3: 设置设备的下载URL
        onProgress(30, t('flashProgress.settingDeviceDownloadUrl'))
        try {
          await this.callMcpTool('self.assets.set_download_url', {
            url: downloadUrl
          })
        } catch (error) {
          console.error('设置下载URL失败:', error)
          onError(t('flashProgress.setDownloadUrlFailed', { error: error.message }))
          return
        }

        // 步骤4: 重启设备
        onProgress(40, t('flashProgress.rebootingDevice'))
        // reboot指令没有返回值，不需要等待，直接调用
        this.callMcpTool('self.reboot').catch(error => {
          console.warn('reboot指令调用警告（设备可能已重启）:', error)
          // 即使reboot失败，也继续流程，因为设备可能已经重启
        })

        // 步骤5: 等待设备重启并建立HTTP连接（通过transfer_started事件）
        onProgress(50, t('flashProgress.waitingForDeviceReboot'))

        // 等待transfer_started事件，设置60秒超时
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error(t('flashProgress.deviceRebootTimeout'))), 60000)
        })

        await Promise.race([transferStartedPromise, timeoutPromise])

        // 步骤6: 开始实际的文件传输
        onProgress(60, t('flashProgress.startingFileTransfer'))

        // 设备已准备好，直接开始传输（transfer_started已收到，sendFileData会立即执行）
        await this.webSocketTransfer.startTransfer(
          (progress, step) => {
            // 文件传输进度：60-100
            const adjustedProgress = 60 + (progress * 0.4)
            onProgress(Math.round(adjustedProgress), step)
          },
          (error) => {
            onError(t('flashProgress.onlineFlashFailed', { error: error.message }))
          },
          () => {
            onComplete()
          }
        )

        // 清理回调引用
        this.webSocketTransfer.onTransferStarted = null

      } catch (error) {
        console.error('在线烧录失败:', error)
        onError(t('flashProgress.onlineFlashFailed', { error: error.message }))
      }
    },
    // 处理取消烧录
    handleCancelFlash() {
      if (this.webSocketTransfer) {
        this.webSocketTransfer.cancel()
        this.webSocketTransfer.destroy()
        this.webSocketTransfer = null
      }
    },
    handleThemeTabChange(tabId) {
      this.activeThemeTab = tabId
    },
    // 从存储加载配置
    async loadConfigFromStorage() {
      try {
        this.isLoading = true
        const storedData = await configStorage.loadConfig()
        
        if (storedData) {
          // 恢复配置（但不恢复 step 和 tab，总是从第一步开始）
          this.config = storedData.config
          // 始终从第一步开始
          this.currentStep = 0
          this.activeThemeTab = 'wakeword'
          this.hasStoredConfig = true // 显示"检测到已保存的配置"提示
          this.isAutoSaveEnabled = true // 启用自动保存
          
          // 检查并清除旧的表情数据结构（不兼容旧版本）
          await this.cleanupLegacyEmojiData()
          
          // 清除之前的定时器
          if (this.autoHideTimer) {
            clearTimeout(this.autoHideTimer)
          }
          
          // 设置5秒后自动隐藏提示
          this.autoHideTimer = setTimeout(() => {
            this.hasStoredConfig = false
          }, 5000)
          
          // 设置 AssetsBuilder 的配置（非严格模式，允许先恢复文件再校验）
          this.assetsBuilder.setConfig(this.config, { strict: false })
          await this.assetsBuilder.restoreAllResourcesFromStorage(this.config)
          
          // 触发一次浅拷贝以刷新引用，避免渲染时对占位值执行 createObjectURL
          try {
            const emojiCustom = this.config?.theme?.emoji?.custom || {}
            const images = emojiCustom.images || {}
            const fileMap = emojiCustom.fileMap || {}
            const emotionMap = emojiCustom.emotionMap || {}
            
            this.config = {
              ...this.config,
              theme: {
                ...this.config.theme,
                emoji: {
                  ...this.config.theme.emoji,
                  custom: {
                    ...emojiCustom,
                    images: { ...images },
                    fileMap: { ...fileMap },
                    emotionMap: { ...emotionMap }
                  }
                }
              }
            }
          } catch (e) {
            console.error('刷新表情配置引用失败:', e)
          }
          
        } else {
          this.hasStoredConfig = false
          this.isAutoSaveEnabled = false
        }
      } catch (error) {
        console.error('加载配置失败:', error)
        this.hasStoredConfig = false
        this.isAutoSaveEnabled = false
      } finally {
        this.isLoading = false
      }
    },
    // 清理旧版本表情数据（强制使用新的 hash 结构）
    async cleanupLegacyEmojiData() {
      try {
        const emojiCustom = this.config?.theme?.emoji?.custom
        if (!emojiCustom) return
        
        // 检查是否使用旧结构（有 images 但没有 fileMap 和 emotionMap）
        const hasImages = Object.keys(emojiCustom.images || {}).length > 0
        const hasFileMap = emojiCustom.fileMap && Object.keys(emojiCustom.fileMap).length > 0
        const hasEmotionMap = emojiCustom.emotionMap && Object.keys(emojiCustom.emotionMap).length > 0
        const hasOldStructure = hasImages && (!hasFileMap || !hasEmotionMap)
        
        if (hasOldStructure) {
          console.warn('⚠️ 检测到旧版本的表情数据结构（不兼容）')
          console.log('正在清理旧数据...')
          
          // 清除存储中的旧表情文件
          try {
            const oldEmotions = Object.keys(emojiCustom.images || {})
            for (const emotion of oldEmotions) {
              await configStorage.deleteFile(`emoji_${emotion}`)
            }
            console.log(`已删除 ${oldEmotions.length} 个旧表情文件`)
          } catch (error) {
            console.warn('清理旧表情文件时出错:', error)
          }
          
          // 重置为新的空结构
          this.config.theme.emoji.custom = {
            size: emojiCustom.size || { width: 64, height: 64 },
            images: {},
            fileMap: {},
            emotionMap: {}
          }
          
          // 如果当前在使用自定义表情，重置为未选择状态
          if (this.config.theme.emoji.type === 'custom') {
            this.config.theme.emoji.type = ''
            console.log('已重置表情类型，请重新选择')
          }
          
          // 立即保存清理后的配置
          await this.saveConfigToStorage()
          
          console.log('✅ 旧表情数据已完全清除')
          
          // 友好的用户提示
          setTimeout(() => {
            alert('检测到旧版本的表情数据结构已被清除。\n\n新版本使用文件去重技术，可以节省存储空间。\n\n请重新上传自定义表情图片。')
          }, 500)
        }
      } catch (error) {
        console.error('清理旧表情数据时出错:', error)
      }
    },
    // 保存配置到存储
    async saveConfigToStorage() {
      try {
        await configStorage.saveConfig(this.config)
      } catch (error) {
        console.error('保存配置失败:', error)
      }
    },
    // 确认重新开始
    async confirmReset() {
      try {
        this.isResetting = true
        
        // 清理 AssetsBuilder 的存储数据
        await this.assetsBuilder.clearAllStoredData()
        
        // 保存当前的芯片配置
        const currentChipConfig = {
          model: this.config.chip.model,
          display: { ...this.config.chip.display }
        }
        
        // 重置配置到默认值，但保留芯片配置
        this.config = {
          chip: currentChipConfig,
          theme: {
            wakeword: {
              type: 'none',
              preset: '',
              custom: {
                name: '',
                command: '',
                threshold: 20,
                model: 'mn6_cn'
              }
            },
            font: {
              type: 'none',
              preset: '',
              hide_subtitle: false,
              custom: {
                file: null,
                size: 20,
                bpp: 4,
                charset: 'deepseek'
              }
            },
            emoji: {
              type: 'none',
              preset: '',
              custom: {
                size: { width: 64, height: 64 },
                images: {}
              }
            },
            skin: {
              light: {
                backgroundType: 'color',
                backgroundColor: '#ffffff',
                textColor: '#000000',
                backgroundImage: null
              },
              dark: {
                backgroundType: 'color', 
                backgroundColor: '#121212',
                textColor: '#ffffff',
                backgroundImage: null
              }
            }
          }
        }
        
        // 重置步骤和状态
        this.currentStep = 0
        this.activeThemeTab = 'wakeword'
        this.hasStoredConfig = false
        this.isAutoSaveEnabled = false
        
      } catch (error) {
        console.error('重置配置失败:', error)
        alert(t('errors.resetFailed'))
      } finally {
        this.isResetting = false
      }
    },
    // 修改关闭按钮逻辑
    closeConfigNotice() {
      this.hasStoredConfig = false
      if (this.autoHideTimer) {
        clearTimeout(this.autoHideTimer)
      }
    },
    // 重置自动隐藏定时器（鼠标悬停时调用）
    resetAutoHideTimer() {
      // 清除之前的定时器
      if (this.autoHideTimer) {
        clearTimeout(this.autoHideTimer)
      }

      // 设置新的5秒定时器
      this.autoHideTimer = setTimeout(() => {
        this.hasStoredConfig = false
      }, 5000)
    }
  },
  watch: {
    config: {
      async handler() {
        if (!this.isLoading && this.isAutoSaveEnabled) {
          await this.saveConfigToStorage()
        }
      },
      deep: true,
    }
  },
  async mounted() {
    await configStorage.initialize()
    await this.loadConfigFromStorage()
  },
  async destroyed() {
    if (this.autoHideTimer) {
      clearTimeout(this.autoHideTimer)
    }
  },
}
</script>

<style scoped>
.voice-box {
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd) center;
}
</style>