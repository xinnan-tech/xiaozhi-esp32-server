/**
 * AssetsBuilder 类
 * 用于处理小智 AI 自定义主题的 assets.bin 打包生成
 * 
 * 主要功能：
 * - 配置验证和处理
 * - 生成 index.json 内容
 * - 管理资源文件
 * - 与后端 API 交互生成 assets.bin
 * - 集成浏览器端字体转换功能
 */

import browserFontConverter from './font_conv/BrowserFontConverter.js'
import WakenetModelPacker from './WakenetModelPacker.js'
import SpiffsGenerator from './SpiffsGenerator.js'
import WasmGifScaler from './WasmGifScaler.js'
import configStorage from './ConfigStorage.js'

class AssetsBuilder {
  constructor() {
    this.config = null
    this.resources = new Map() // 存储资源文件
    this.tempFiles = [] // 临时文件列表
    this.fontConverterBrowser = browserFontConverter // 浏览器端字体转换器
    this.convertedFonts = new Map() // 缓存转换后的字体
    this.wakenetPacker = new WakenetModelPacker() // 唤醒词模型打包器
    this.spiffsGenerator = new SpiffsGenerator() // SPIFFS 生成器
    this.gifScaler = new WasmGifScaler({ 
      quality: 30, 
      debug: true,
      scalingMode: 'auto',  // 自动选择最佳缩放模式
      optimize: true,       // 启用 GIF 优化
      optimizationLevel: 2  // 优化级别 (1-3)
    }) // WASM GIF 缩放器
    this.configStorage = configStorage // 配置存储管理器
    this.autoSaveEnabled = true // 是否启用自动保存
  }

  /**
   * 设置配置对象
   * @param {Object} config - 完整的配置对象
   */
  setConfig(config, options = {}) {
    const strict = options?.strict ?? true
    if (strict && !this.validateConfig(config)) {
      throw new Error('Configuration object validation failed')
    }
    this.config = { ...config }
    return this
  }

  /**
   * 验证配置对象
   * @param {Object} config - 待验证的配置对象
   * @returns {boolean} 验证结果
   */
  validateConfig(config) {
    if (!config) return false
    
    // 验证芯片配置
    if (!config.chip?.model) {
      console.error('Missing chip model configuration')
      return false
    }

    // 验证显示配置
    const display = config.chip.display
    if (!display?.width || !display?.height) {
      console.error('Missing display resolution configuration')
      return false
    }

    // 验证字体配置
    const font = config.theme?.font
    if (font?.type === 'preset' && !font.preset) {
      console.error('Preset font configuration is incomplete')
      return false
    }
    if (font?.type === 'custom' && !font.custom?.file) {
      console.error('Custom font file not provided')
      return false
    }

    return true
  }

  /**
   * 添加资源文件
   * @param {string} key - 资源键名
   * @param {File|Blob} file - 文件对象
   * @param {string} filename - 文件名
   * @param {string} resourceType - 资源类型 (font, emoji, background)
   */
  addResource(key, file, filename, resourceType = 'other') {
    this.resources.set(key, {
      file,
      filename,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified || Date.now(),
      resourceType
    })

    // 自动保存文件到存储
    if (this.autoSaveEnabled && file instanceof File) {
      this.saveFileToStorage(key, file, resourceType).catch(error => {
        console.warn(`Auto-saving file ${filename} failed:`, error)
      })
    }

    return this
  }

  /**
   * 保存文件到存储
   * @param {string} key - 资源键名
   * @param {File} file - 文件对象
   * @param {string} resourceType - 资源类型
   * @returns {Promise<void>}
   */
  async saveFileToStorage(key, file, resourceType) {
    try {
      await this.configStorage.saveFile(key, file, resourceType)
      console.log(`File ${file.name} auto-saved to storage`)
    } catch (error) {
      console.error(`Failed to save file to storage: ${file.name}`, error)
      throw error
    }
  }

  /**
   * 从存储中恢复资源文件
   * @param {string} key - 资源键名
   * @returns {Promise<boolean>} 是否成功恢复
   */
  async restoreResourceFromStorage(key) {
    try {
      const file = await this.configStorage.loadFile(key)
      if (file) {
        this.resources.set(key, {
          file,
          filename: file.name,
          size: file.size,
          type: file.type,
          lastModified: file.lastModified,
          resourceType: file.storedType,
          fromStorage: true
        })
        console.log(`Resource ${key} restored from storage successfully: ${file.name}`)
        return true
      }
      return false
    } catch (error) {
      console.error(`Failed to restore resource from storage: ${key}`, error)
      return false
    }
  }

  /**
   * 恢复所有相关的资源文件
   * @param {Object} config - 配置对象
   * @returns {Promise<void>}
   */
  async restoreAllResourcesFromStorage(config) {
    if (!config) return

    const restoredFiles = []

    // 恢复自定义字体文件（无论当前字体类型是什么，都尝试恢复）
    if (config.theme?.font?.custom && config.theme.font.custom?.file === null) {
      const fontKey = 'custom_font'
      if (await this.restoreResourceFromStorage(fontKey)) {
        const resource = this.resources.get(fontKey)
        if (resource) {
          config.theme.font.custom.file = resource.file
          restoredFiles.push(`Custom font: ${resource.filename}`)
          console.log(`Custom font restored even when type is '${config.theme.font.type}'`)
        }
      }
    }

    // 恢复自定义表情图片（支持新的 hash 去重结构）
    if (config.theme?.emoji?.type === 'custom' && config.theme.emoji.custom) {
      const emojiCustom = config.theme.emoji.custom
      const emotionMap = emojiCustom.emotionMap || {}
      const fileMap = emojiCustom.fileMap || {}
      const images = emojiCustom.images || {}
      
      // 如果存在新结构（emotionMap 和 fileMap），使用新结构恢复
      if (Object.keys(emotionMap).length > 0 || Object.keys(fileMap).length > 0) {
        // 收集所有需要恢复的 hash
        const hashesToRestore = new Set()
        
        // 从 fileMap 中收集所有 hash
        for (const hash of Object.keys(fileMap)) {
          if (fileMap[hash] === null) {
            hashesToRestore.add(hash)
          }
        }
        
        // 恢复每个唯一的文件（按 hash）
        for (const hash of hashesToRestore) {
          let fileKey = `hash_${hash}`
          let restored = await this.restoreResourceFromStorage(fileKey)
          
          // 如果新格式恢复失败，尝试旧格式（兼容性处理）
          if (!restored) {
            const oldKey = `emoji_hash_${hash}`
            restored = await this.restoreResourceFromStorage(oldKey)
            if (restored) {
              fileKey = oldKey
            }
          }
          
          if (restored) {
            const resource = this.resources.get(fileKey)
            if (resource) {
              // 更新 fileMap
              fileMap[hash] = resource.file
              
              // 找到所有使用该 hash 的表情
              const emotionsUsingHash = Object.entries(emotionMap)
                .filter(([_, h]) => h === hash)
                .map(([emotion, _]) => emotion)
              
              // 更新所有使用该文件的表情的 images
              emotionsUsingHash.forEach(emotion => {
                images[emotion] = resource.file
              })
              
              restoredFiles.push(`Emoji file ${hash.substring(0, 8)}... (used for: ${emotionsUsingHash.join(', ')})`)
            }
          }
        }
        
        // 直接修改原始对象（保持响应式）
        // 逐个更新 fileMap
        Object.keys(fileMap).forEach(hash => {
          config.theme.emoji.custom.fileMap[hash] = fileMap[hash]
        })
        
        // 逐个更新 images
        Object.keys(images).forEach(emotion => {
          config.theme.emoji.custom.images[emotion] = images[emotion]
        })
      } else {
        // 兼容旧结构：逐个恢复表情文件
        for (const [emojiName, file] of Object.entries(images)) {
          if (file === null) {
            const emojiKey = `emoji_${emojiName}`
            if (await this.restoreResourceFromStorage(emojiKey)) {
              const resource = this.resources.get(emojiKey)
              if (resource) {
                images[emojiName] = resource.file
                restoredFiles.push(`Emoji ${emojiName}: ${resource.filename}`)
              }
            }
          }
        }
        config.theme.emoji.custom.images = images
      }
    }

    // 恢复背景图片
    if (config.theme?.skin?.light?.backgroundType === 'image' && config.theme.skin.light.backgroundImage === null) {
      const bgKey = 'background_light'
      if (await this.restoreResourceFromStorage(bgKey)) {
        const resource = this.resources.get(bgKey)
        if (resource) {
          config.theme.skin.light.backgroundImage = resource.file
          restoredFiles.push(`Light background: ${resource.filename}`)
        }
      }
    }
    
    if (config.theme?.skin?.dark?.backgroundType === 'image' && config.theme.skin.dark.backgroundImage === null) {
      const bgKey = 'background_dark'
      if (await this.restoreResourceFromStorage(bgKey)) {
        const resource = this.resources.get(bgKey)
        if (resource) {
          config.theme.skin.dark.backgroundImage = resource.file
          restoredFiles.push(`Dark background: ${resource.filename}`)
        }
      }
    }

    // 恢复转换后的字体数据
    try {
      const fontInfo = this.getFontInfo()
      if (fontInfo && fontInfo.type === 'custom') {
        const tempKey = `converted_font_${fontInfo.filename}`
        const tempData = await this.configStorage.loadTempData(tempKey)
        if (tempData) {
          this.convertedFonts.set(fontInfo.filename, tempData.data)
          console.log(`Converted font data restored: ${fontInfo.filename}`)
        }
      }
    } catch (error) {
      console.warn('Error restoring converted font data:', error)
    }

    if (restoredFiles.length > 0) {
      console.log('Files restored from storage:', restoredFiles)
    }
  }

  /**
   * 获取唤醒词模型信息
   * @returns {Object|null} 唤醒词模型信息
   */
  getWakewordModelInfo() {
    if (!this.config || !this.config.chip || !this.config.theme) {
      return null
    }
    
    const chipModel = this.config.chip.model
    const wakeword = this.config.theme.wakeword
    
    if (!wakeword || wakeword.type === 'none') return null

    if (wakeword.type === 'preset') {
      // 根据芯片型号确定唤醒词模型类型
      const isC3OrC6 = chipModel === 'esp32c3' || chipModel === 'esp32c6'
      const modelType = isC3OrC6 ? 'WakeNet9s' : 'WakeNet9'
      
      return {
        type: modelType,
        name: wakeword.preset,
        filename: 'srmodels.bin'
      }
    } else if (wakeword.type === 'custom') {
      return {
        type: 'MultiNet',
        name: wakeword.custom.model,
        filename: 'srmodels.bin',
        custom: wakeword.custom
      }
    }
    
    return null
  }

  /**
   * 获取字体信息
   * @returns {Object|null} 字体信息
   */
  getFontInfo() {
    if (!this.config || !this.config.theme || !this.config.theme.font) {
      return null
    }
    
    const font = this.config.theme.font
    
    if (font.type === 'preset') {
      return {
        type: 'preset',
        filename: `${font.preset}.bin`,
        source: font.preset
      }
    }
    
    if (font.type === 'custom' && font.custom.file) {
      const custom = font.custom
      const filename = `font_custom_${custom.size}_${custom.bpp}.bin`
      
      return {
        type: 'custom',
        filename,
        source: font.custom.file,
        config: {
          size: custom.size,
          bpp: custom.bpp,
          charset: custom.charset
        }
      }
    }
    
    return null
  }

  /**
   * 获取表情集合信息
   * @returns {Array} 表情集合信息数组
   */
  getEmojiCollectionInfo() {
    if (!this.config || !this.config.theme || !this.config.theme.emoji) {
      return []
    }
    
    const emoji = this.config.theme.emoji
    const collection = []
    
    if (emoji.type === 'preset') {
      // 预设表情包
      const presetEmojis = [
        'neutral', 'happy', 'laughing', 'funny', 'sad', 'angry', 'crying',
        'loving', 'embarrassed', 'surprised', 'shocked', 'thinking', 'winking',
        'cool', 'relaxed', 'delicious', 'kissy', 'confident', 'sleepy', 'silly', 'confused'
      ]
      
      const size = emoji.preset === 'twemoji32' ? '32' : '64'
      presetEmojis.forEach(name => {
        collection.push({
          name,
          file: `${name}.png`,
          source: `preset:${emoji.preset}`,
          size: { width: parseInt(size), height: parseInt(size) }
        })
      })
    } else if (emoji.type === 'custom') {
      // 自定义表情包（支持文件去重）
      const images = emoji.custom.images || {}
      const emotionMap = emoji.custom.emotionMap || {}
      const fileMap = emoji.custom.fileMap || {}
      const size = emoji.custom.size || { width: 64, height: 64 }
      
      // 必须使用新的 hash 映射结构
      if (Object.keys(emotionMap).length === 0 || Object.keys(fileMap).length === 0) {
        console.error('❌ Error: Detected old version of emoji data structure')
        console.error('Please clear browser cache or reset configuration, then re-upload emoji images')
        throw new Error('Incompatible emoji data structure: Missing fileMap or emotionMap. Please reconfigure emojis.')
      }
      
      // 创建 hash 到文件名的映射（用于去重）
      const hashToFilename = new Map()
      
      Object.entries(emotionMap).forEach(([emotionName, fileHash]) => {
        const file = fileMap[fileHash]
        if (file) {
          // 为每个唯一的文件 hash 生成一个共享的文件名
          if (!hashToFilename.has(fileHash)) {
            const fileExtension = file.name ? file.name.split('.').pop().toLowerCase() : 'png'
            // 使用 hash 前8位作为文件名，确保唯一性
            const sharedFilename = `emoji_${fileHash.substring(0, 8)}.${fileExtension}`
            hashToFilename.set(fileHash, sharedFilename)
          }
          
          const sharedFilename = hashToFilename.get(fileHash)
          
          collection.push({
            name: emotionName,
            file: sharedFilename,  // 多个表情可能指向同一个文件
            source: file,
            fileHash,  // 保留 hash 信息用于去重处理
            size: { ...size }
          })
        }
      })
      
      console.log(`Emoji deduplication: ${Object.keys(emotionMap).length} emojis using ${hashToFilename.size} different image files`)
      
      // 确保至少有 neutral 表情
      if (!collection.find(item => item.name === 'neutral')) {
        console.warn('Warning: neutral emoji not provided, default image will be used')
      }
    }
    
    return collection
  }

  /**
   * 获取皮肤配置信息
   * @returns {Object} 皮肤配置信息
   */
  getSkinInfo() {
    if (!this.config || !this.config.theme || !this.config.theme.skin) {
      return {}
    }
    
    const skin = this.config.theme.skin
    const result = {}
    
    // 处理浅色模式
    if (skin.light) {
      result.light = {
        text_color: skin.light.textColor || '#000000',
        background_color: skin.light.backgroundColor || '#ffffff'
      }
      
      if (skin.light.backgroundType === 'image' && skin.light.backgroundImage) {
        result.light.background_image = 'background_light.raw'
      }
    }
    
    // 处理深色模式  
    if (skin.dark) {
      result.dark = {
        text_color: skin.dark.textColor || '#ffffff',
        background_color: skin.dark.backgroundColor || '#121212'
      }
      
      if (skin.dark.backgroundType === 'image' && skin.dark.backgroundImage) {
        result.dark.background_image = 'background_dark.raw'
      }
    }
    
    return result
  }

  /**
   * 生成 index.json 内容
   * @returns {Object} index.json 对象
   */
  generateIndexJson() {
    if (!this.config) {
      throw new Error('Configuration object not set')
    }

    const indexData = {
      version: 1,
      chip_model: this.config.chip.model,
      hide_subtitle: this.config.theme.font.hide_subtitle || false,
      display_config: {
        width: this.config.chip.display.width,
        height: this.config.chip.display.height,
        monochrome: false,
        color: this.config.chip.display.color || 'RGB565'
      }
    }

    // 添加唤醒词模型
    const wakewordInfo = this.getWakewordModelInfo()
    if (wakewordInfo) {
      indexData.srmodels = wakewordInfo.filename
      
      // 如果是自定义唤醒词，添加 multinet_model 配置
      if (wakewordInfo.type === 'MultiNet' && wakewordInfo.custom) {
        const custom = wakewordInfo.custom
        indexData.multinet_model = {
          language: custom.model.includes('_en') ? 'en' : 'cn',
          duration: custom.duration || 3000,
          threshold: custom.threshold / 100.0,
          commands: [
            {
              command: custom.command,
              text: custom.name,
              action: "wake"
            }
          ]
        }
      }
    }

    // 添加字体信息
    const fontInfo = this.getFontInfo()
    if (fontInfo) {
      indexData.text_font = fontInfo.filename
    }

    // 添加皮肤配置
    const skinInfo = this.getSkinInfo()
    if (Object.keys(skinInfo).length > 0) {
      indexData.skin = skinInfo
    }

    // 添加表情集合
    const emojiCollection = this.getEmojiCollectionInfo()
    if (emojiCollection.length > 0) {
      indexData.emoji_collection = emojiCollection.map(emoji => ({
        name: emoji.name,
        file: emoji.file
      }))
    }

    return indexData
  }

  /**
   * 准备打包资源
   * @returns {Object} 打包资源清单
   */
  preparePackageResources() {
    const resources = {
      files: [],
      indexJson: this.generateIndexJson(),
      config: { ...this.config }
    }

    // 添加唤醒词模型
    const wakewordInfo = this.getWakewordModelInfo()
    if (wakewordInfo && wakewordInfo.name) {
      resources.files.push({
        type: 'wakeword',
        name: wakewordInfo.name,
        filename: wakewordInfo.filename,
        modelType: wakewordInfo.type,
        isCustom: wakewordInfo.type === 'MultiNet'
      })
    }

    // 添加字体文件
    const fontInfo = this.getFontInfo()
    if (fontInfo) {
      resources.files.push({
        type: 'font',
        filename: fontInfo.filename,
        source: fontInfo.source,
        config: fontInfo.config || null
      })
    }

    // 添加表情文件（去重处理）
    const emojiCollection = this.getEmojiCollectionInfo()
    const addedFileHashes = new Set()  // 跟踪已添加的文件 hash
    
    emojiCollection.forEach(emoji => {
      // 如果有 fileHash（自定义表情且使用新结构），检查是否已添加
      if (emoji.fileHash) {
        if (addedFileHashes.has(emoji.fileHash)) {
          // 文件已添加，跳过（但保留在 index.json 的 emoji_collection 中）
          console.log(`Skipping duplicate file: ${emoji.name} -> ${emoji.file} (hash: ${emoji.fileHash.substring(0, 8)})`)
          return
        }
        addedFileHashes.add(emoji.fileHash)
      }
      
      // 添加唯一的文件
      resources.files.push({
        type: 'emoji',
        name: emoji.name,
        filename: emoji.file,
        source: emoji.source,
        size: emoji.size,
        fileHash: emoji.fileHash  // 传递 hash 信息
      })
    })

    // 添加背景图片
    const skin = this.config?.theme?.skin
    if (skin?.light?.backgroundType === 'image' && skin.light.backgroundImage) {
      resources.files.push({
        type: 'background',
        filename: 'background_light.raw',
        source: skin.light.backgroundImage,
        mode: 'light'
      })
    }
    if (skin?.dark?.backgroundType === 'image' && skin.dark.backgroundImage) {
      resources.files.push({
        type: 'background', 
        filename: 'background_dark.raw',
        source: skin.dark.backgroundImage,
        mode: 'dark'
      })
    }

    return resources
  }

  /**
   * 预处理自定义字体
   * @param {Function} progressCallback - 进度回调函数  
   * @returns {Promise<void>}
   */
  async preprocessCustomFonts(progressCallback = null) {
    const fontInfo = this.getFontInfo()
    
    if (fontInfo && fontInfo.type === 'custom' && !this.convertedFonts.has(fontInfo.filename)) {
      if (progressCallback) progressCallback(20, 'Converting custom font...')
      
      try {
        const convertOptions = {
          fontFile: fontInfo.source,
          fontName: fontInfo.filename.replace(/\.bin$/, ''),
          fontSize: fontInfo.config.size,
          bpp: fontInfo.config.bpp,
          charset: fontInfo.config.charset,
          symbols: fontInfo.config.symbols || '',
          range: fontInfo.config.range || '',
          compression: false,
          progressCallback: (progress, message) => {
            if (progressCallback) progressCallback(20 + progress * 0.2, `Font conversion: ${message}`)
          }
        }
        
        let convertedFont
        
        // 使用浏览器端字体转换器
        await this.fontConverterBrowser.initialize()
        convertedFont = await this.fontConverterBrowser.convertToCBIN(convertOptions)
        this.convertedFonts.set(fontInfo.filename, convertedFont)

        // 保存转换后的字体到临时存储
        if (this.autoSaveEnabled) {
          const tempKey = `converted_font_${fontInfo.filename}`
          try {
            await this.configStorage.saveTempData(tempKey, convertedFont, 'converted_font', {
              filename: fontInfo.filename,
              size: fontInfo.config.size,
              bpp: fontInfo.config.bpp,
              charset: fontInfo.config.charset
            })
            console.log(`Converted font saved to storage: ${fontInfo.filename}`)
          } catch (error) {
            console.warn(`Failed to save converted font: ${fontInfo.filename}`, error)
          }
        }
      } catch (error) {
        console.error('Font conversion failed:', error)
        throw new Error(`Font conversion failed: ${error.message}`)
      }
    }
  }

  /**
   * 生成 assets.bin
   * @param {Function} progressCallback - 进度回调函数
   * @returns {Promise<Blob>} 生成的 assets.bin 文件
   */
  async generateAssetsBin(progressCallback = null) {
    if (!this.config) {
      throw new Error('Configuration object not set')
    }

    try {
      if (progressCallback) progressCallback(0, 'Starting generation...')
      
      // 预处理自定义字体
      await this.preprocessCustomFonts(progressCallback)
      
      await new Promise(resolve => setTimeout(resolve, 100))
      if (progressCallback) progressCallback(40, 'Preparing resource files...')
      
      const resources = this.preparePackageResources()
      
      // 清理生成器状态
      this.wakenetPacker.clear()
      this.spiffsGenerator.clear()
      
      // 处理各类资源文件
      await this.processResourceFiles(resources, progressCallback)
      
      await new Promise(resolve => setTimeout(resolve, 100))
      if (progressCallback) progressCallback(90, 'Generating final file...')

      // Print file list
      this.spiffsGenerator.printFileList()
      
      // 生成最终的 assets.bin
      const assetsBinData = await this.spiffsGenerator.generate((progress, message) => {
        if (progressCallback) {
          progressCallback(90 + progress * 0.1, message)
        }
      })
      
      if (progressCallback) progressCallback(100, 'Generation completed')
      
      return new Blob([assetsBinData], { type: 'application/octet-stream' })
      
    } catch (error) {
      console.error('Failed to generate assets.bin:', error)
      throw error
    }
  }

  /**
   * 下载 assets.bin 文件
   * @param {Blob} blob - assets.bin 文件数据
   * @param {string} filename - 下载文件名
   */
  downloadAssetsBin(blob, filename = 'assets.bin') {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  /**
   * 获取字体信息（包含转换功能）
   * @param {File} fontFile - 字体文件（可选，如果提供则获取该文件的信息）
   * @returns {Promise<Object>} 字体信息
   */
  async getFontInfoWithDetails(fontFile = null) {
    try {
      const file = fontFile || this.config?.theme?.font?.custom?.file
      if (!file) return null
      
      let info
      
      // 使用浏览器端字体转换器
      await this.fontConverterBrowser.initialize()
      info = await this.fontConverterBrowser.getFontInfo(file)
      
      return {
        ...info,
        file: file,
        isCustom: true
      }
    } catch (error) {
      console.error('Failed to get font details:', error)
      return null
    }
  }

  /**
   * 估算字体大小
   * @param {Object} fontConfig - 字体配置
   * @returns {Promise<Object>} 大小估算结果
   */
  async estimateFontSize(fontConfig = null) {
    try {
      const config = fontConfig || this.config?.theme?.font?.custom
      if (!config) return null
      
      const estimateOptions = {
        fontSize: config.size,
        bpp: config.bpp,
        charset: config.charset,
        symbols: config.symbols || '',
        range: config.range || ''
      }
      
      let sizeInfo
      
      // 使用浏览器端字体转换器
      sizeInfo = this.fontConverterBrowser.estimateSize(estimateOptions)
      
      return sizeInfo
    } catch (error) {
      console.error('Failed to estimate font size:', error)
      return null
    }
  }

  /**
   * 验证自定义字体配置
   * @param {Object} fontConfig - 字体配置
   * @returns {Object} 验证结果
   */
  validateCustomFont(fontConfig) {
    const errors = []
    const warnings = []
    
    if (!fontConfig.file) {
      errors.push('Missing font file')
    } else {
      // 使用浏览器端转换器验证
      const isValid = this.fontConverterBrowser.validateFont(fontConfig.file)
        
      if (!isValid) {
        errors.push('Font file format not supported')
      }
    }
    
    if (fontConfig.size < 8 || fontConfig.size > 80) {
      errors.push('Font size must be between 8-80')
    }
    
    if (![1, 2, 4, 8].includes(fontConfig.bpp)) {
      errors.push('BPP must be 1, 2, 4 or 8')
    }
    
    if (!fontConfig.charset && !fontConfig.symbols && !fontConfig.range) {
      warnings.push('No charset, symbols or range specified, default charset will be used')
    }
    
    return {
      valid: errors.length === 0,
      errors,
      warnings
    }
  }


  /**
   * 获取字体转换器状态
   * @returns {Object} 转换器状态信息
   */
  getConverterStatus() {
    return {
      initialized: this.fontConverterBrowser.initialized,
      supportedFormats: this.fontConverterBrowser.supportedFormats
    }
  }

  /**
   * 处理资源文件
   * @param {Object} resources - 资源配置
   * @param {Function} progressCallback - 进度回调
   */
  async processResourceFiles(resources, progressCallback = null) {
    let processedCount = 0
    const totalFiles = resources.files.length
    
    // 添加 index.json 文件
    const indexJsonData = new TextEncoder().encode(JSON.stringify(resources.indexJson, null, 2))
    // print json string
    console.log('index.json', resources.indexJson);
    this.spiffsGenerator.addFile('index.json', indexJsonData.buffer)
    
    for (const resource of resources.files) {
      const progressPercent = 40 + (processedCount / totalFiles) * 40
      if (progressCallback) {
        progressCallback(progressPercent, `Processing file: ${resource.filename}`)
      }
      
      try {
        await this.processResourceFile(resource)
        processedCount++
      } catch (error) {
        console.error(`Failed to process resource file: ${resource.filename}`, error)
        throw new Error(`Failed to process resource file: ${resource.filename} - ${error.message}`)
      }
    }
  }

  /**
   * 处理单个资源文件
   * @param {Object} resource - 资源配置
   */
  async processResourceFile(resource) {
    switch (resource.type) {
      case 'wakeword':
        await this.processWakewordModel(resource)
        break
      case 'font':
        await this.processFontFile(resource)
        break
      case 'emoji':
        await this.processEmojiFile(resource)
        break
      case 'background':
        await this.processBackgroundFile(resource)
        break
      default:
        console.warn(`Unknown resource type: ${resource.type}`)
    }
  }

  /**
   * 处理唤醒词模型
   * @param {Object} resource - 资源配置
   */
  async processWakewordModel(resource) {
    const success = await this.wakenetPacker.loadModelFromShare(resource.name)
    if (!success) {
      throw new Error(`Failed to load wakeword model: ${resource.name}`)
    }
    
    const srmodelsData = this.wakenetPacker.packModels()
    this.spiffsGenerator.addFile(resource.filename, srmodelsData)
  }

  /**
   * 处理字体文件
   * @param {Object} resource - 资源配置
   */
  async processFontFile(resource) {
    if (resource.config) {
      // 自定义字体，使用转换后的数据
      const convertedFont = this.convertedFonts.get(resource.filename)
      if (convertedFont) {
        this.spiffsGenerator.addFile(resource.filename, convertedFont)
      } else {
        throw new Error(`Converted font not found: ${resource.filename}`)
      }
    } else {
      // 预设字体，从share/fonts目录加载
      const fontData = await this.loadPresetFont(resource.source)
      this.spiffsGenerator.addFile(resource.filename, fontData)
    }
  }

  /**
   * 处理表情文件
   * @param {Object} resource - 资源配置
   */
  async processEmojiFile(resource) {
    // 注意：文件去重已在 preparePackageResources() 阶段完成
    // 这里处理的每个文件都是唯一的
    
    let imageData
    let needsScaling = false
    let imageFormat = 'png' // 默认格式
    let isGif = false
    
    if (typeof resource.source === 'string' && resource.source.startsWith('preset:')) {
      // 预设表情包
      const presetName = resource.source.replace('preset:', '')
      imageData = await this.loadPresetEmoji(presetName, resource.name)
    } else {
      // 自定义表情
      const file = resource.source
      
      // 检测是否为 GIF 格式
      isGif = this.isGifFile(file)
      
      // 获取文件格式
      const fileExtension = file.name.split('.').pop().toLowerCase()
      imageFormat = fileExtension
      
      // 检查图片实际尺寸
      try {
        const actualDimensions = await this.getImageDimensions(file)
        const targetSize = resource.size || { width: 64, height: 64 }
        
        // 如果实际尺寸超出目标尺寸范围，需要缩放
        if (actualDimensions.width > targetSize.width || 
            actualDimensions.height > targetSize.height) {
          needsScaling = true
          console.log(`Emoji ${resource.name} needs scaling: ${actualDimensions.width}x${actualDimensions.height} -> ${targetSize.width}x${targetSize.height}`)
        }
      } catch (error) {
        console.warn(`Failed to get emoji image dimensions: ${resource.name}`, error)
      }
      
      // 如果不需要缩放，直接读取文件
      if (!needsScaling) {
        imageData = await this.fileToArrayBuffer(file)
      }
    }
    
    // 如果需要缩放，根据文件类型选择缩放方法
    if (needsScaling) {
      try {
        const targetSize = resource.size || { width: 64, height: 64 }
        
        if (isGif) {
          // 使用 WasmGifScaler 处理 GIF 文件
          console.log(`Using WasmGifScaler to process GIF emoji: ${resource.name}`)
          const scaledGifBlob = await this.gifScaler.scaleGif(resource.source, {
            maxWidth: targetSize.width,
            maxHeight: targetSize.height,
            keepAspectRatio: true,
            lossy: 30  // 使用 lossy 压缩减小文件大小
          })
          imageData = await this.fileToArrayBuffer(scaledGifBlob)
        } else {
          // 使用常规方法处理其他格式的图片
          imageData = await this.scaleImageToFit(resource.source, targetSize, imageFormat)
        }
      } catch (error) {
        console.error(`Failed to scale emoji image: ${resource.name}`, error)
        // 缩放失败时使用原图
        imageData = await this.fileToArrayBuffer(resource.source)
      }
    }
    
    // 添加文件到 SPIFFS
    this.spiffsGenerator.addFile(resource.filename, imageData, {
      width: resource.size?.width || 0,
      height: resource.size?.height || 0
    })
    
    // 记录处理日志
    if (resource.fileHash) {
      console.log(`Emoji file added: ${resource.filename} (hash: ${resource.fileHash.substring(0, 8)})`)
    }
  }

  /**
   * 处理背景文件  
   * @param {Object} resource - 资源配置
   */
  async processBackgroundFile(resource) {
    const imageData = await this.fileToArrayBuffer(resource.source)
    
    // 将图片转换为RGB565格式的原始数据
    const rawData = await this.convertImageToRgb565(imageData)
    this.spiffsGenerator.addFile(resource.filename, rawData)
  }

  /**
   * 加载预设字体
   * @param {string} fontName - 字体名称
   * @returns {Promise<ArrayBuffer>} 字体数据
   */
  async loadPresetFont(fontName) {
    try {
      const response = await fetch(`./static/fonts/${fontName}.bin`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return await response.arrayBuffer()
    } catch (error) {
      throw new Error(`Failed to load preset font: ${fontName} - ${error.message}`)
    }
  }

  /**
   * 加载预设表情
   * @param {string} presetName - 预设名称 (twemoji32/twemoji64)
   * @param {string} emojiName - 表情名称
   * @returns {Promise<ArrayBuffer>} 表情数据
   */
  async loadPresetEmoji(presetName, emojiName) {
    try {
      const response = await fetch(`./static/${presetName}/${emojiName}.png`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return await response.arrayBuffer()
    } catch (error) {
      throw new Error(`Failed to load preset emoji: ${presetName}/${emojiName} - ${error.message}`)
    }
  }

  /**
   * 将文件转换为ArrayBuffer
   * @param {File|Blob} file - 文件对象
   * @returns {Promise<ArrayBuffer>} 文件数据
   */
  fileToArrayBuffer(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = () => reject(new Error('Failed to read file'))
      reader.readAsArrayBuffer(file)
    })
  }

  /**
   * 缩放图片以适应指定尺寸（等比例缩放，contain效果）
   * @param {ArrayBuffer|File} imageData - 图片数据
   * @param {Object} targetSize - 目标尺寸 {width, height}
   * @param {string} format - 图片格式（用于透明背景处理）
   * @returns {Promise<ArrayBuffer>} 缩放后的图片数据
   */
  async scaleImageToFit(imageData, targetSize, format = 'png') {
    return new Promise((resolve, reject) => {
      const blob = imageData instanceof File ? imageData : new Blob([imageData])
      const url = URL.createObjectURL(blob)
      const img = new Image()
      
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          
          // 设置目标画布尺寸
          canvas.width = targetSize.width
          canvas.height = targetSize.height
          
          // 计算等比例缩放尺寸（contain效果）
          const imgAspectRatio = img.width / img.height
          const targetAspectRatio = targetSize.width / targetSize.height
          
          let drawWidth, drawHeight, offsetX, offsetY
          
          if (imgAspectRatio > targetAspectRatio) {
            // 图片较宽，按宽度缩放
            drawWidth = targetSize.width
            drawHeight = targetSize.width / imgAspectRatio
            offsetX = 0
            offsetY = (targetSize.height - drawHeight) / 2
          } else {
            // 图片较高，按高度缩放
            drawHeight = targetSize.height
            drawWidth = targetSize.height * imgAspectRatio
            offsetX = (targetSize.width - drawWidth) / 2
            offsetY = 0
          }
          
          // 对PNG格式保持透明背景
          if (format === 'png') {
            // 清除画布，保持透明
            ctx.clearRect(0, 0, canvas.width, canvas.height)
          } else {
            // 其他格式使用白色背景
            ctx.fillStyle = '#FFFFFF'
            ctx.fillRect(0, 0, canvas.width, canvas.height)
          }
          
          // 绘制缩放后的图片
          ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight)
          
          // 转换为ArrayBuffer
          canvas.toBlob((blob) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result)
            reader.onerror = () => reject(new Error('Failed to convert image data'))
            reader.readAsArrayBuffer(blob)
          }, `image/${format}`)
          
          URL.revokeObjectURL(url)
        } catch (error) {
          URL.revokeObjectURL(url)
          reject(error)
        }
      }
      
      img.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('Unable to load image'))
      }
      
      img.src = url
    })
  }

  /**
   * 检测文件是否为 GIF 格式
   * @param {File} file - 文件对象
   * @returns {boolean} 是否为 GIF 格式
   */
  isGifFile(file) {
    // 检查 MIME 类型
    if (file.type === 'image/gif') {
      return true
    }
    
    // 检查文件扩展名
    const extension = file.name.split('.').pop().toLowerCase()
    return extension === 'gif'
  }

  /**
   * 获取图片尺寸信息
   * @param {ArrayBuffer|File} imageData - 图片数据
   * @returns {Promise<Object>} 图片尺寸信息 {width, height}
   */
  async getImageDimensions(imageData) {
    return new Promise((resolve, reject) => {
      const blob = imageData instanceof File ? imageData : new Blob([imageData])
      const url = URL.createObjectURL(blob)
      const img = new Image()
      
      img.onload = () => {
        URL.revokeObjectURL(url)
        resolve({
          width: img.width,
          height: img.height
        })
      }
      
      img.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('Unable to get image dimensions'))
      }
      
      img.src = url
    })
  }

  /**
   * 将图片转换为RGB565格式的原始数据
   * @param {ArrayBuffer} imageData - 图片数据
   * @returns {Promise<ArrayBuffer>} RGB565原始数据
   */
  async convertImageToRgb565(imageData) {
    return new Promise((resolve, reject) => {
      const blob = new Blob([imageData])
      const url = URL.createObjectURL(blob)
      const img = new Image()
      
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d', { willReadFrequently: true })
          
          canvas.width = this.config?.chip?.display?.width || 320
          canvas.height = this.config?.chip?.display?.height || 240
          
          // 使用 cover 模式绘制图片，保持比例并居中显示
          const imgAspectRatio = img.width / img.height
          const canvasAspectRatio = canvas.width / canvas.height
          
          let drawWidth, drawHeight, offsetX, offsetY
          
          if (imgAspectRatio > canvasAspectRatio) {
            // 图片较宽，按高度缩放 (cover效果)
            drawHeight = canvas.height
            drawWidth = canvas.height * imgAspectRatio
            offsetX = (canvas.width - drawWidth) / 2
            offsetY = 0
          } else {
            // 图片较高，按宽度缩放 (cover效果)
            drawWidth = canvas.width
            drawHeight = canvas.width / imgAspectRatio
            offsetX = 0
            offsetY = (canvas.height - drawHeight) / 2
          }
          
          // 绘制图片到画布，使用cover模式保持比例并居中
          ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight)
          
          // 获取像素数据
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
          const pixels = imageData.data
          
          // 转换为RGB565格式
          const rgb565Data = new ArrayBuffer(canvas.width * canvas.height * 2)
          const rgb565View = new Uint16Array(rgb565Data)
          
          for (let i = 0; i < pixels.length; i += 4) {
            const r = pixels[i] >> 3      // 5位红色
            const g = pixels[i + 1] >> 2  // 6位绿色 
            const b = pixels[i + 2] >> 3  // 5位蓝色
            
            rgb565View[i / 4] = (r << 11) | (g << 5) | b
          }
          
          // LVGL 常量定义
          const LV_IMAGE_HEADER_MAGIC = 0x19  // LVGL图片header魔数
          const LV_COLOR_FORMAT_RGB565 = 0x12 // RGB565颜色格式
          
          // 计算stride（每行字节数）
          const stride = canvas.width * 2  // RGB565每像素2字节
          
          // 创建符合lv_image_dsc_t结构的header
          const headerSize = 28  // lv_image_dsc_t结构大小: header(12) + data_size(4) + data(4) + reserved(4) + reserved_2(4) = 28字节
          const totalSize = headerSize + rgb565Data.byteLength
          const finalData = new ArrayBuffer(totalSize)
          const finalView = new Uint8Array(finalData)
          const headerView = new DataView(finalData)
          
          let offset = 0
          
          // lv_image_header_t结构 (16字节)
          // magic: 8位, cf: 8位, flags: 16位 (共4字节)
          const headerWord1 = (0 << 24) | (0 << 16) | (LV_COLOR_FORMAT_RGB565 << 8) | LV_IMAGE_HEADER_MAGIC
          headerView.setUint32(offset, headerWord1, true)
          offset += 4
          
          // w: 16位, h: 16位 (共4字节)
          const sizeWord = (canvas.height << 16) | canvas.width

          headerView.setUint32(offset, sizeWord, true)  
          offset += 4
          
          // stride: 16位, reserved_2: 16位 (共4字节)
          const strideWord = (0 << 16) | stride
          headerView.setUint32(offset, strideWord, true)
          offset += 4
          
          // lv_image_dsc_t其余字段
          // data_size: 32位 (4字节)
          headerView.setUint32(offset, rgb565Data.byteLength, true)
          offset += 4
          
          // data指针占位 (4字节，在实际使用中会指向数据部分)
          headerView.setUint32(offset, headerSize, true)  // 相对偏移
          offset += 4
          
          // reserved (4字节)
          headerView.setUint32(offset, 0, true)
          offset += 4
          
          // reserved_2 (4字节)  
          headerView.setUint32(offset, 0, true)
          offset += 4
          
          // 复制RGB565数据到header后面
          finalView.set(new Uint8Array(rgb565Data), headerSize)
          
          URL.revokeObjectURL(url)
          resolve(finalData)
        } catch (error) {
          URL.revokeObjectURL(url)
          reject(error)
        }
      }
      
      img.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('Unable to load image'))
      }
      
      img.src = url
    })
  }

  /**
   * 清理临时资源
   */
  cleanup() {
    this.resources.clear()
    this.tempFiles = []
    this.convertedFonts.clear()
    this.wakenetPacker.clear()
    this.spiffsGenerator.clear()
    this.gifScaler.dispose() // 清理 WasmGifScaler 资源
  }

  /**
   * 清理所有存储数据（重新开始功能）
   * @returns {Promise<void>}
   */
  async clearAllStoredData() {
    try {
      await this.configStorage.clearAll()
      this.cleanup()
      console.log('All stored data cleared')
    } catch (error) {
      console.error('Failed to clear stored data:', error)
      throw error
    }
  }

  /**
   * 获取存储状态信息
   * @returns {Promise<Object>} 存储状态信息
   */
  async getStorageStatus() {
    try {
      const storageInfo = await this.configStorage.getStorageInfo()
      const hasConfig = await this.configStorage.hasStoredConfig()
      
      return {
        hasStoredData: hasConfig,
        storageInfo,
        autoSaveEnabled: this.autoSaveEnabled
      }
    } catch (error) {
      console.error('Failed to get storage status:', error)
      return {
        hasStoredData: false,
        storageInfo: null,
        autoSaveEnabled: this.autoSaveEnabled
      }
    }
  }

  /**
   * 启用/禁用自动保存
   * @param {boolean} enabled - 是否启用
   */
  setAutoSave(enabled) {
    this.autoSaveEnabled = enabled
    console.log(`Auto-save ${enabled ? 'enabled' : 'disabled'}`)
  }

  /**
   * 获取资源清单用于显示
   * @returns {Array} 资源清单
   */
  getResourceSummary() {
    const summary = []
    const resources = this.preparePackageResources()
    
    // 统计各类资源
    const counts = {
      wakeword: 0,
      font: 0, 
      emoji: 0,
      background: 0
    }
    
    resources.files.forEach(file => {
      counts[file.type] = (counts[file.type] || 0) + 1
      
      let description = ''
      switch (file.type) {
        case 'wakeword':
          description = `Wakeword model: ${file.name} (${file.modelType})`
          break
        case 'font':
          if (file.config) {
            description = `Custom font: size ${file.config.size}px, BPP ${file.config.bpp}`
          } else {
            description = `Preset font: ${file.source}`
          }
          break
        case 'emoji':
          description = `Emoji: ${file.name} (${file.size.width}x${file.size.height})`
          break
        case 'background':
          description = `${file.mode === 'light' ? 'Light' : 'Dark'} mode background`
          break
      }
      
      summary.push({
        type: file.type,
        filename: file.filename,
        description
      })
    })
    
    return {
      files: summary,
      counts,
      totalFiles: summary.length,
      indexJson: resources.indexJson
    }
  }
}

export default AssetsBuilder
