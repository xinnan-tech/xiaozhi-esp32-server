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
import GifScaler from './GifScaler.js'
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
    this.gifScaler = new GifScaler({ 
      quality: 10, 
      debug: true,
      scalingMode: 'auto'  // 自动选择最佳缩放模式
    }) // GIF 缩放器
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
      throw new Error('配置对象验证失败')
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
      console.error('缺少芯片型号配置')
      return false
    }

    // 验证显示配置
    const display = config.chip.display
    if (!display?.width || !display?.height) {
      console.error('缺少显示分辨率配置')
      return false
    }

    // 验证字体配置
    const font = config.theme?.font
    if (font?.type === 'preset' && !font.preset) {
      console.error('预设字体配置不完整')
      return false
    }
    if (font?.type === 'custom' && !font.custom?.file) {
      console.error('自定义字体文件未提供')
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
        console.warn(`自动保存文件 ${filename} 失败:`, error)
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
      console.log(`文件 ${file.name} 已自动保存到存储`)
    } catch (error) {
      console.error(`保存文件到存储失败: ${file.name}`, error)
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
        console.log(`资源 ${key} 从存储恢复成功: ${file.name}`)
        return true
      }
      return false
    } catch (error) {
      console.error(`从存储恢复资源失败: ${key}`, error)
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

    // 恢复自定义字体文件
    if (config.theme?.font?.type === 'custom' && config.theme.font.custom?.file === null) {
      const fontKey = 'custom_font'
      if (await this.restoreResourceFromStorage(fontKey)) {
        const resource = this.resources.get(fontKey)
        if (resource) {
          config.theme.font.custom.file = resource.file
          restoredFiles.push(`自定义字体: ${resource.filename}`)
        }
      }
    }

    // 恢复自定义表情图片
    if (config.theme?.emoji?.type === 'custom' && config.theme.emoji.custom?.images) {
      for (const [emojiName, file] of Object.entries(config.theme.emoji.custom.images)) {
        if (file === null) {
          const emojiKey = `emoji_${emojiName}`
          if (await this.restoreResourceFromStorage(emojiKey)) {
            const resource = this.resources.get(emojiKey)
            if (resource) {
              config.theme.emoji.custom.images[emojiName] = resource.file
              restoredFiles.push(`表情 ${emojiName}: ${resource.filename}`)
            }
          }
        }
      }
    }

    // 恢复背景图片
    if (config.theme?.skin?.light?.backgroundType === 'image' && config.theme.skin.light.backgroundImage === null) {
      const bgKey = 'background_light'
      if (await this.restoreResourceFromStorage(bgKey)) {
        const resource = this.resources.get(bgKey)
        if (resource) {
          config.theme.skin.light.backgroundImage = resource.file
          restoredFiles.push(`浅色背景: ${resource.filename}`)
        }
      }
    }
    
    if (config.theme?.skin?.dark?.backgroundType === 'image' && config.theme.skin.dark.backgroundImage === null) {
      const bgKey = 'background_dark'
      if (await this.restoreResourceFromStorage(bgKey)) {
        const resource = this.resources.get(bgKey)
        if (resource) {
          config.theme.skin.dark.backgroundImage = resource.file
          restoredFiles.push(`深色背景: ${resource.filename}`)
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
          console.log(`转换后的字体数据已恢复: ${fontInfo.filename}`)
        }
      }
    } catch (error) {
      console.warn('恢复转换后的字体数据时出错:', error)
    }

    if (restoredFiles.length > 0) {
      console.log('已从存储恢复的文件:', restoredFiles)
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
    
    if (!wakeword) return null

    // 处理自定义唤醒词（使用 multinet 模型）
    if (wakeword === 'custom') {
      const customWakeword = this.config.theme.customWakeword
      if (!customWakeword || !customWakeword.chinese || !customWakeword.pinyin) {
        throw new Error('自定义唤醒词配置不完整，请填写中文和拼音')
      }
      return {
        name: 'mn5q8_cn',
        type: 'Multinet5Q8',
        filename: 'srmodels.bin',
        isCustom: true,
        customWakeword: customWakeword
      }
    }

    // 根据唤醒词模型名称确定类型（而不是根据芯片型号）
    // 因为实际文件目录中只有 WakeNet9s 和 WakeNet7 模型，没有 WakeNet9 模型
    let modelType = 'WakeNet9s' // 默认值
    
    if (wakeword.startsWith('wn9s_')) {
      modelType = 'WakeNet9s'
    } else if (wakeword.startsWith('wn7_')) {
      modelType = 'WakeNet7'
    } else if (wakeword.startsWith('wn9_')) {
      // 注意：实际文件目录中没有 wn9_ 开头的模型文件
      // 如果用户选择了 wn9_ 开头的模型，说明可能是旧配置或错误选择
      // 这种情况下应该报错，而不是尝试加载
      throw new Error(`模型 ${wakeword} 不存在。实际可用的模型只有: wn9s_alexa, wn9s_hiesp, wn9s_hijason, wn9s_hilexin, wn9s_nihaoxiaozhi, wn7_xiaoaitongxue`)
    }
    
    return {
      name: wakeword,
      type: modelType,
      filename: 'srmodels.bin',
      isCustom: false
    }
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
      // 自定义表情包
      const images = emoji.custom.images || {}
      const size = emoji.custom.size || { width: 64, height: 64 }
      
      Object.entries(images).forEach(([name, file]) => {
        if (file) {
          // 根据实际文件扩展名生成文件名
          const fileExtension = file.name ? file.name.split('.').pop().toLowerCase() : 'png'
          collection.push({
            name,
            file: `${name}.${fileExtension}`,
            source: file,
            size: { ...size }
          })
        }
      })
      
      // 确保至少有 neutral 表情
      if (!collection.find(item => item.name === 'neutral')) {
        console.warn('警告：未提供 neutral 表情，将使用默认图片')
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
    
    // 默认模式（由前端选择，light/dark）
    if (skin.defaultMode) {
      result.default_mode = skin.defaultMode
    }

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
      throw new Error('配置对象未设置')
    }

    const indexData = {
      version: 1,
      chip_model: this.config.chip.model,
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

    // 添加自定义唤醒词配置（multinet_model_info）
    // wakewordInfo 已在上面声明，直接使用
    if (wakewordInfo && wakewordInfo.isCustom && wakewordInfo.customWakeword) {
      indexData.multinet_model_info = {
        language: 'cn',
        duration: 3000,
        threshold: 20, // 默认阈值
        commands: [
          {
            command: wakewordInfo.customWakeword.pinyin,
            text: wakewordInfo.customWakeword.chinese,
            action: 'wake'
          }
        ]
      }
      // 添加 CONFIG 字段
      indexData.CONFIG_CUSTOM_WAKE_WORD = wakewordInfo.customWakeword.pinyin
      indexData.CONFIG_CUSTOM_WAKE_WORD_DISPLAY = wakewordInfo.customWakeword.chinese
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
        isCustom: wakewordInfo.isCustom || false,
        customWakeword: wakewordInfo.customWakeword || null
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

    // 添加表情文件
    const emojiCollection = this.getEmojiCollectionInfo()
    emojiCollection.forEach(emoji => {
      resources.files.push({
        type: 'emoji',
        name: emoji.name,
        filename: emoji.file,
        source: emoji.source,
        size: emoji.size
      })
    })

    // 添加背景图片
    const skin = this.config?.theme?.skin
    if (skin?.light?.backgroundType === 'image') {
      // 优先使用保存的 File 对象，否则使用 URL
      const source = skin.light.backgroundImageFile || skin.light.backgroundImage
      if (source) {
      resources.files.push({
        type: 'background',
        filename: 'background_light.raw',
          source: source,
        mode: 'light'
      })
    }
    }
    if (skin?.dark?.backgroundType === 'image') {
      // 优先使用保存的 File 对象，否则使用 URL
      const source = skin.dark.backgroundImageFile || skin.dark.backgroundImage
      if (source) {
      resources.files.push({
        type: 'background', 
        filename: 'background_dark.raw',
          source: source,
        mode: 'dark'
      })
      }
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
      if (progressCallback) progressCallback(20, '转换自定义字体...')
      
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
            if (progressCallback) progressCallback(20 + progress * 0.2, `字体转换: ${message}`)
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
            console.log(`转换后的字体已保存到存储: ${fontInfo.filename}`)
          } catch (error) {
            console.warn(`保存转换后的字体失败: ${fontInfo.filename}`, error)
          }
        }
      } catch (error) {
        console.error('字体转换失败:', error)
        throw new Error(`字体转换失败: ${error.message}`)
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
      throw new Error('配置对象未设置')
    }

    try {
      if (progressCallback) progressCallback(0, '开始生成...')
      
      // 预处理自定义字体
      await this.preprocessCustomFonts(progressCallback)
      
      await new Promise(resolve => setTimeout(resolve, 100))
      if (progressCallback) progressCallback(40, '准备资源文件...')
      
      const resources = this.preparePackageResources()
      
      // 清理生成器状态
      this.wakenetPacker.clear()
      this.spiffsGenerator.clear()
      
      // 处理各类资源文件
      await this.processResourceFiles(resources, progressCallback)
      
      await new Promise(resolve => setTimeout(resolve, 100))
      if (progressCallback) progressCallback(90, '生成最终文件...')
      
      // 生成最终的 assets.bin
      const assetsBinData = await this.spiffsGenerator.generate((progress, message) => {
        if (progressCallback) {
          progressCallback(90 + progress * 0.1, message)
        }
      })
      
      if (progressCallback) progressCallback(100, '生成完成')
      
      return new Blob([assetsBinData], { type: 'application/octet-stream' })
      
    } catch (error) {
      console.error('生成 assets.bin 失败:', error)
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
      console.error('获取字体详细信息失败:', error)
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
      console.error('估算字体大小失败:', error)
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
      errors.push('缺少字体文件')
    } else {
      // 使用浏览器端转换器验证
      const isValid = this.fontConverterBrowser.validateFont(fontConfig.file)
        
      if (!isValid) {
        errors.push('字体文件格式不支持')
      }
    }
    
    if (fontConfig.size < 8 || fontConfig.size > 80) {
      errors.push('字体大小必须在 8-80 之间')
    }
    
    if (![1, 2, 4, 8].includes(fontConfig.bpp)) {
      errors.push('BPP 必须是 1, 2, 4 或 8')
    }
    
    if (!fontConfig.charset && !fontConfig.symbols && !fontConfig.range) {
      warnings.push('未指定字符集、符号或范围，将使用默认字符集')
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
        progressCallback(progressPercent, `处理文件: ${resource.filename}`)
      }
      
      try {
        await this.processResourceFile(resource)
        processedCount++
      } catch (error) {
        console.error(`处理资源文件失败: ${resource.filename}`, error)
        throw new Error(`处理资源文件失败: ${resource.filename} - ${error.message}`)
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
        console.warn(`未知的资源类型: ${resource.type}`)
    }
  }

  /**
   * 处理唤醒词模型
   * @param {Object} resource - 资源配置
   */
  async processWakewordModel(resource) {
    const success = await this.wakenetPacker.loadModelFromShare(resource.name)
    if (!success) {
      throw new Error(`加载唤醒词模型失败: ${resource.name}`)
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
        throw new Error(`找不到转换后的字体: ${resource.filename}`)
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
        const targetSize = resource.size || { width: 32, height: 32 }
        
        // 如果实际尺寸超出目标尺寸范围，需要缩放
        if (actualDimensions.width > targetSize.width || 
            actualDimensions.height > targetSize.height) {
          needsScaling = true
          console.log(`表情 ${resource.name} 需要缩放: ${actualDimensions.width}x${actualDimensions.height} -> ${targetSize.width}x${targetSize.height}`)
        }
      } catch (error) {
        console.warn(`无法获取表情图片尺寸: ${resource.name}`, error)
      }
      
      // 如果不需要缩放，直接读取文件
      if (!needsScaling) {
        imageData = await this.fileToArrayBuffer(file)
      }
    }
    
    // 如果需要缩放，根据文件类型选择缩放方法
    if (needsScaling) {
      try {
        const targetSize = resource.size || { width: 32, height: 32 }
        
        if (isGif) {
          // 使用 GifScaler 处理 GIF 文件
          console.log(`使用 GifScaler 处理 GIF 表情: ${resource.name}`)
          const scaledGifBlob = await this.gifScaler.scaleGif(resource.source, {
            maxWidth: targetSize.width,
            maxHeight: targetSize.height,
            keepAspectRatio: true
          })
          imageData = await this.fileToArrayBuffer(scaledGifBlob)
        } else {
          // 使用常规方法处理其他格式的图片
          imageData = await this.scaleImageToFit(resource.source, targetSize, imageFormat)
        }
      } catch (error) {
        console.error(`表情图片缩放失败: ${resource.name}`, error)
        // 缩放失败时使用原图
        imageData = await this.fileToArrayBuffer(resource.source)
      }
    }
    
    this.spiffsGenerator.addFile(resource.filename, imageData, {
      width: resource.size?.width || 0,
      height: resource.size?.height || 0
    })
  }

  /**
   * 处理背景文件  
   * @param {Object} resource - 资源配置
   */
  async processBackgroundFile(resource) {
    let imageData
    
    // 如果 source 是 URL 字符串，需要先通过 fetch 获取
    if (typeof resource.source === 'string') {
      try {
        const response = await fetch(resource.source)
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        const blob = await response.blob()
        
        // 验证 blob 类型
        if (!(blob instanceof Blob)) {
          throw new Error(`fetch 返回的不是 Blob 对象，类型: ${typeof blob}`)
        }
        
        imageData = await this.fileToArrayBuffer(blob)
      } catch (error) {
        console.error('加载背景图片失败:', error)
        throw new Error(`加载背景图片失败: ${resource.filename} - ${error.message}`)
      }
    } else if (resource.source instanceof File || resource.source instanceof Blob) {
      // 如果是 File 或 Blob 对象，直接转换
      imageData = await this.fileToArrayBuffer(resource.source)
    } else {
      throw new Error(`不支持的背景图片格式: ${resource.filename}，source 类型: ${typeof resource.source}`)
    }
    
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
      // 兼容 UI 中的字体 ID（puhui-14 / puhui-16 / puhui-20 / puhui-30）
      const presetMap = {
        'puhui-14': 'font_puhui_deepseek_14_1',
        'puhui-16': 'font_puhui_deepseek_16_4',
        'puhui-20': 'font_puhui_deepseek_20_4',
        'puhui-30': 'font_puhui_deepseek_30_4'
      }
      const mapped = presetMap[fontName] || fontName
      const response = await fetch(`./static/fonts/${mapped}.bin`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      return await response.arrayBuffer()
    } catch (error) {
      throw new Error(`加载预设字体失败: ${fontName} - ${error.message}`)
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
      throw new Error(`加载预设表情失败: ${presetName}/${emojiName} - ${error.message}`)
    }
  }

  /**
   * 将文件转换为ArrayBuffer
   * @param {File|Blob|ArrayBuffer} file - 文件对象或 ArrayBuffer
   * @returns {Promise<ArrayBuffer>} 文件数据
   */
  fileToArrayBuffer(file) {
    // 如果已经是 ArrayBuffer，直接返回
    if (file instanceof ArrayBuffer) {
      return Promise.resolve(file)
    }
    
    // 验证类型
    if (!(file instanceof File) && !(file instanceof Blob)) {
      const errorMsg = `fileToArrayBuffer 需要 File 或 Blob 对象，但收到: ${typeof file}, 构造函数: ${file?.constructor?.name || 'unknown'}`
      console.error('fileToArrayBuffer 类型错误:', {
        file,
        type: typeof file,
        constructor: file?.constructor?.name,
        isFile: file instanceof File,
        isBlob: file instanceof Blob,
        isArrayBuffer: file instanceof ArrayBuffer
      })
      return Promise.reject(new Error(errorMsg))
    }
    
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = (e) => {
        console.error('FileReader 错误:', e)
        reject(new Error('读取文件失败'))
      }
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
            reader.onerror = () => reject(new Error('转换图片数据失败'))
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
        reject(new Error('无法加载图片'))
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
        reject(new Error('无法获取图片尺寸'))
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
        reject(new Error('无法加载图片'))
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
    this.gifScaler.dispose() // 清理 GifScaler 资源
  }

  /**
   * 清理所有存储数据（重新开始功能）
   * @returns {Promise<void>}
   */
  async clearAllStoredData() {
    try {
      await this.configStorage.clearAll()
      this.cleanup()
      console.log('所有存储数据已清理')
    } catch (error) {
      console.error('清理存储数据失败:', error)
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
      console.error('获取存储状态失败:', error)
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
    console.log(`自动保存已${enabled ? '启用' : '禁用'}`)
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
          description = `唤醒词模型: ${file.name} (${file.modelType})`
          break
        case 'font':
          if (file.config) {
            description = `自定义字体: 大小${file.config.size}px, BPP${file.config.bpp}`
          } else {
            description = `预设字体: ${file.source}`
          }
          break
        case 'emoji':
          description = `表情: ${file.name} (${file.size.width}x${file.size.height})`
          break
        case 'background':
          description = `${file.mode === 'light' ? '浅色' : '深色'}模式背景`
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
