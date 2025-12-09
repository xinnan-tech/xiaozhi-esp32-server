/**
 * BrowserFontConverter - 完整的浏览器端字体转换器
 * 基于 lv_font_conv 的核心逻辑，适配浏览器环境
 */

import opentype from 'opentype.js'
import collect_font_data from './CollectFontData.js'
import AppError from './AppError.js'
import write_cbin from './writers/CBinWriter.js'

class BrowserFontConverter {
  constructor() {
    this.initialized = false
    this.supportedFormats = ['ttf', 'woff', 'woff2', 'otf']
    this.charsetCache = new Map() // 缓存已加载的字符集
  }

  /**
   * 初始化转换器
   */
  async initialize() {
    if (this.initialized) return
    
    try {
      // 检查依赖是否可用
      if (typeof opentype === 'undefined') {
        throw new Error('opentype.js 未加载')
      }
      
      this.initialized = true
      console.log('BrowserFontConverter 初始化完成')
    } catch (error) {
      console.error('BrowserFontConverter 初始化失败:', error)
      throw error
    }
  }

  /**
   * 验证字体文件
   */
  validateFont(fontFile) {
    if (!fontFile) return false
    
    if (fontFile instanceof File) {
      const fileName = fontFile.name.toLowerCase()
      const fileType = fontFile.type.toLowerCase()
      
      const validExtension = this.supportedFormats.some(ext => 
        fileName.endsWith(`.${ext}`)
      )
      
      const validMimeType = [
        'font/ttf', 'font/truetype', 'application/x-font-ttf',
        'font/woff', 'font/woff2', 'application/font-woff',
        'font/otf', 'application/x-font-otf'
      ].some(type => fileType.includes(type))
      
      return validExtension || validMimeType
    }
    
    return fontFile instanceof ArrayBuffer && fontFile.byteLength > 0
  }

  /**
   * 获取字体信息
   */
  async getFontInfo(fontFile) {
    try {
      let buffer
      
      if (fontFile instanceof File) {
        buffer = await fontFile.arrayBuffer()
      } else if (fontFile instanceof ArrayBuffer) {
        buffer = fontFile
      } else {
        throw new Error('不支持的字体文件类型')
      }
      
      const font = opentype.parse(buffer)
      
      return {
        familyName: this.getLocalizedName(font.names.fontFamily) || 'Unknown',
        fullName: this.getLocalizedName(font.names.fullName) || 'Unknown',
        postScriptName: this.getLocalizedName(font.names.postScriptName) || 'Unknown',
        version: this.getLocalizedName(font.names.version) || 'Unknown',
        unitsPerEm: font.unitsPerEm,
        ascender: font.ascender,
        descender: font.descender,
        numGlyphs: font.numGlyphs,
        supported: true
      }
    } catch (error) {
      console.error('获取字体信息失败:', error)
      return {
        familyName: 'Unknown',
        supported: false,
        error: error.message
      }
    }
  }

  /**
   * 获取本地化名称
   */
  getLocalizedName(nameObj) {
    if (!nameObj) return null
    
    // 优先级：中文 > 英文 > 第一个可用的
    return nameObj['zh'] || nameObj['zh-CN'] || nameObj['en'] || 
           nameObj[Object.keys(nameObj)[0]]
  }

  /**
   * 转换字体为 CBIN 格式
   */
  async convertToCBIN(options) {
    if (!this.initialized) {
      await this.initialize()
    }

    const {
      fontFile,
      fontName,
      fontSize = 20,
      bpp = 4,
      charset = 'deepseek',
      symbols = '',
      range = '',
      compression = false,
      lcd = false,
      lcd_v = false,
      progressCallback = null
    } = options

    if (!this.validateFont(fontFile)) {
      throw new AppError('不支持的字体文件格式')
    }

    try {
      if (progressCallback) progressCallback(0, '开始处理字体...')

      // 准备字体数据
      let fontBuffer
      if (fontFile instanceof File) {
        fontBuffer = await fontFile.arrayBuffer()
      } else {
        fontBuffer = fontFile
      }

      if (progressCallback) progressCallback(10, '解析字体结构...')

      // 构建字符范围和符号（使用异步版本支持从文件加载字符集）
      const { ranges, charSymbols } = await this.parseCharacterInputAsync(charset, symbols, range)

      if (progressCallback) progressCallback(20, '准备转换参数...')

      // 构建转换参数
      const convertArgs = {
        font: [{
          source_path: fontName || 'custom_font',
          source_bin: fontBuffer,
          ranges: [{ 
            range: ranges, 
            symbols: charSymbols 
          }],
          autohint_off: false,
          autohint_strong: false
        }],
        size: fontSize,
        bpp: bpp,
        lcd: lcd,
        lcd_v: lcd_v,
        no_compress: !compression,
        no_kerning: false,
        use_color_info: false,
        format: 'cbin',
        output: fontName || 'font'
      }

      if (progressCallback) progressCallback(30, '收集字体数据...')

      // 收集字体数据
      const fontData = await collect_font_data(convertArgs)

      if (progressCallback) progressCallback(70, '生成 CBIN 格式...')

      // 生成 CBIN 数据
      const result = write_cbin(convertArgs, fontData)
      const outputName = convertArgs.output
      
      if (progressCallback) progressCallback(100, '转换完成!')

      return result[outputName]

    } catch (error) {
      console.error('字体转换失败:', error)
      throw new AppError(`字体转换失败: ${error.message}`)
    }
  }

  /**
   * 解析字符输入（字符集、符号、范围）- 异步版本
   */
  async parseCharacterInputAsync(charset, symbols, range) {
    let ranges = []
    let charSymbols = symbols || ''

    // 处理预设字符集
    if (charset && charset !== 'custom') {
      const presetChars = await this.getCharsetContentAsync(charset)
      charSymbols = presetChars + charSymbols
    }

    // 处理 Unicode 范围
    if (range) {
      ranges = this.parseUnicodeRange(range)
    }

    return { ranges, charSymbols }
  }

  /**
   * 解析字符输入（字符集、符号、范围）- 同步版本（向后兼容）
   */
  parseCharacterInput(charset, symbols, range) {
    let ranges = []
    let charSymbols = symbols || ''

    // 处理预设字符集
    if (charset && charset !== 'custom') {
      const presetChars = this.getCharsetContent(charset)
      charSymbols = presetChars + charSymbols
    }

    // 处理 Unicode 范围
    if (range) {
      ranges = this.parseUnicodeRange(range)
    }

    return { ranges, charSymbols }
  }


  /**
   * 异步加载字符集文件
   */
  async loadCharsetFromFile(charset) {
    const charsetFiles = {
      latin: './static/charsets/latin1.txt',
      deepseek: './static/charsets/deepseek.txt',
      gb2312: './static/charsets/gb2312.txt'
    }
    
    const filePath = charsetFiles[charset]
    if (!filePath) {
      return null
    }
    
    try {
      const response = await fetch(filePath)
      if (!response.ok) {
        throw new Error(`Failed to load charset file: ${response.status}`)
      }
      
      const text = await response.text()
      // 将每行的字符连接成一个字符串，保留所有字符（包括空白字符）
      const characters = text.split('\n').join('')
      
      // 缓存结果
      this.charsetCache.set(charset, characters)
      return characters
    } catch (error) {
      console.error(`Failed to load charset ${charset}:`, error)
      return null
    }
  }

  /**
   * 获取字符集内容（同步方法，用于已缓存的字符集）
   */
  getCharsetContent(charset) {
    const charsets = {}
    
    // 如果是需要从文件加载的字符集，先检查缓存
    if ((charset === 'latin' || charset === 'deepseek' || charset === 'gb2312') && this.charsetCache.has(charset)) {
      return this.charsetCache.get(charset)
    }
    
    // 如果请求 basic，重定向到 latin（向后兼容）
    if (charset === 'basic') {
      return this.getCharsetContent('latin')
    }
    
    // 默认返回空字符串，需要先调用异步方法加载
    return charsets[charset] || ''
  }

  /**
   * 异步获取字符集内容
   */
  async getCharsetContentAsync(charset) {
    // 如果请求 basic，重定向到 latin（向后兼容）
    if (charset === 'basic') {
      charset = 'latin'
    }
    
    // 如果字符集已缓存，直接返回
    if (this.charsetCache.has(charset)) {
      return this.charsetCache.get(charset)
    }
    
    // 对于需要从文件加载的字符集
    if (charset === 'latin' || charset === 'deepseek' || charset === 'gb2312') {
      const loadedCharset = await this.loadCharsetFromFile(charset)
      if (loadedCharset) {
        return loadedCharset
      }
    }
    
    // 回退到同步方法
    return this.getCharsetContent(charset)
  }

  /**
   * 解析 Unicode 范围字符串
   */
  parseUnicodeRange(rangeStr) {
    const ranges = []
    const parts = rangeStr.split(',')
    
    for (const part of parts) {
      const trimmed = part.trim()
      if (!trimmed) continue
      
      if (trimmed.includes('-')) {
        const [start, end] = trimmed.split('-')
        const startCode = this.parseHexOrDec(start)
        const endCode = this.parseHexOrDec(end)
        
        if (startCode !== null && endCode !== null) {
          ranges.push(startCode, endCode, startCode)
        }
      } else {
        const code = this.parseHexOrDec(trimmed)
        if (code !== null) {
          ranges.push(code, code, code)
        }
      }
    }
    
    return ranges
  }

  /**
   * 解析十六进制或十进制数字
   */
  parseHexOrDec(str) {
    const trimmed = str.trim()
    
    if (trimmed.startsWith('0x') || trimmed.startsWith('0X')) {
      const parsed = parseInt(trimmed, 16)
      return isNaN(parsed) ? null : parsed
    }
    
    const parsed = parseInt(trimmed, 10)
    return isNaN(parsed) ? null : parsed
  }

  /**
   * 估算输出大小 - 异步版本
   */
  async estimateSizeAsync(options) {
    const { fontSize = 20, bpp = 4, charset = 'latin', symbols = '', range = '' } = options
    
    // 计算字符数量
    let charCount = symbols.length
    
    if (charset && charset !== 'custom') {
      const charsetContent = await this.getCharsetContentAsync(charset)
      charCount += charsetContent.length
    }
    
    if (range) {
      const ranges = this.parseUnicodeRange(range)
      for (let i = 0; i < ranges.length; i += 3) {
        charCount += ranges[i + 1] - ranges[i] + 1
      }
    }
    
    // 去重字符数（粗略估算）
    charCount = Math.min(charCount, charCount * 0.8)
    
    // 估算每个字符的字节数
    const avgBytesPerChar = Math.ceil((fontSize * fontSize * bpp) / 8) + 40
    
    const estimatedSize = charCount * avgBytesPerChar + 2048 // 加上头部和索引
    
    return {
      characterCount: Math.floor(charCount),
      avgBytesPerChar,
      estimatedSize,
      formattedSize: this.formatBytes(estimatedSize)
    }
  }

  /**
   * 估算输出大小 - 同步版本（向后兼容）
   */
  estimateSize(options) {
    const { fontSize = 20, bpp = 4, charset = 'latin', symbols = '', range = '' } = options
    
    // 计算字符数量
    let charCount = symbols.length
    
    if (charset && charset !== 'custom') {
      const charsetContent = this.getCharsetContent(charset)
      charCount += charsetContent.length
    }
    
    if (range) {
      const ranges = this.parseUnicodeRange(range)
      for (let i = 0; i < ranges.length; i += 3) {
        charCount += ranges[i + 1] - ranges[i] + 1
      }
    }
    
    // 去重字符数（粗略估算）
    charCount = Math.min(charCount, charCount * 0.8)
    
    // 估算每个字符的字节数
    const avgBytesPerChar = Math.ceil((fontSize * fontSize * bpp) / 8) + 40
    
    const estimatedSize = charCount * avgBytesPerChar + 2048 // 加上头部和索引
    
    return {
      characterCount: Math.floor(charCount),
      avgBytesPerChar,
      estimatedSize,
      formattedSize: this.formatBytes(estimatedSize)
    }
  }

  /**
   * 格式化字节大小
   */
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes'
    
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  /**
   * 清理资源
   */
  cleanup() {
    // 清理可能的资源引用
    this.initialized = false
  }
}

// 创建单例实例
const browserFontConverter = new BrowserFontConverter()

export default browserFontConverter
export { BrowserFontConverter }
