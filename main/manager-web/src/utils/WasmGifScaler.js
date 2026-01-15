/**
 * WasmGifScaler 类
 * 使用 gifsicle-wasm-browser 进行 GIF 图片缩放处理
 * 
 * 主要功能：
 * - GIF 图片缩放
 * - 保持宽高比
 * - GIF 优化压缩
 * - 多种缩放模式
 */

import gifsicle from 'gifsicle-wasm-browser'

class WasmGifScaler {
  constructor(options = {}) {
    this.quality = options.quality || 10 // 1-200, lossy 压缩质量
    this.debug = options.debug || false
    this.scalingMode = options.scalingMode || 'auto' // 'auto', 'fit', 'fill'
    this.optimize = options.optimize !== false // 默认启用优化
    this.optimizationLevel = options.optimizationLevel || 2 // 1-3, 优化级别
  }

  /**
   * 缩放 GIF 图片
   * @param {File|Blob|ArrayBuffer} gifFile - GIF 文件
   * @param {Object} options - 缩放选项
   * @param {number} options.maxWidth - 最大宽度
   * @param {number} options.maxHeight - 最大高度
   * @param {boolean} options.keepAspectRatio - 是否保持宽高比，默认 true
   * @param {boolean} options.optimize - 是否优化，默认 true
   * @param {number} options.lossy - lossy 压缩质量 (1-200)，默认使用实例配置
   * @param {number} options.loopCount - 循环次数，0 表示无限循环（默认），-1 表示保持原样
   * @returns {Promise<Blob>} 缩放后的 GIF Blob
   */
  async scaleGif(gifFile, options = {}) {
    const {
      maxWidth,
      maxHeight,
      keepAspectRatio = true,
      optimize = this.optimize,
      lossy = this.quality,
      loopCount = 0  // 默认无限循环
    } = options

    if (!maxWidth && !maxHeight) {
      throw new Error('必须指定 maxWidth 或 maxHeight')
    }

    try {
      // 构建 resize 命令
      let resizeCmd
      if (keepAspectRatio) {
        // 保持宽高比的缩放，使用 --resize-fit
        const width = maxWidth || '_'
        const height = maxHeight || '_'
        resizeCmd = `--resize-fit ${width}x${height}`
      } else {
        // 强制缩放到指定尺寸，使用 --resize
        const width = maxWidth || '_'
        const height = maxHeight || '_'
        resizeCmd = `--resize ${width}x${height}!`
      }

      // 构建完整的 gifsicle 命令
      const commandParts = []
      
      // 添加 unoptimize 确保正确处理
      commandParts.push('-U')
      
      // 添加 resize 命令
      commandParts.push(resizeCmd)
      
      // 添加循环次数设置（loopCount >= 0 时生效，-1 表示不设置）
      if (loopCount >= 0) {
        commandParts.push(`--loopcount=${loopCount}`)
      }
      
      // 添加 lossy 压缩
      if (lossy && lossy > 0) {
        commandParts.push(`--lossy=${lossy}`)
      }
      
      // 添加优化
      if (optimize) {
        commandParts.push(`-O${this.optimizationLevel}`)
      }
      
      // 输入输出
      commandParts.push('1.gif')
      commandParts.push('-o /out/output.gif')
      
      const command = commandParts.join(' ')
      
      if (this.debug) {
        console.log('GIF 缩放命令:', command)
        console.log('输入文件大小:', gifFile.size || '未知')
      }

      // 调用 gifsicle
      const result = await gifsicle.run({
        input: [{
          file: gifFile,
          name: '1.gif'
        }],
        command: [command]
      })

      if (!result || result.length === 0) {
        throw new Error('gifsicle 处理失败，未返回结果')
      }

      const outputFile = result[0]
      
      if (this.debug) {
        console.log('GIF 缩放完成')
        console.log('输出文件大小:', outputFile.size)
        if (gifFile.size) {
          const ratio = ((1 - outputFile.size / gifFile.size) * 100).toFixed(2)
          console.log(`压缩率: ${ratio}%`)
        }
      }

      // 转换为 Blob
      return new Blob([outputFile], { type: 'image/gif' })
      
    } catch (error) {
      console.error('GIF 缩放失败:', error)
      throw new Error(`GIF 缩放失败: ${error.message}`)
    }
  }

  /**
   * 批量缩放 GIF 图片
   * @param {Array} files - GIF 文件数组 [{file, options}]
   * @returns {Promise<Array>} 缩放后的 GIF Blob 数组
   */
  async scaleGifBatch(files) {
    const results = []
    
    for (let i = 0; i < files.length; i++) {
      const { file, options } = files[i]
      try {
        const result = await this.scaleGif(file, options)
        results.push(result)
      } catch (error) {
        console.error(`批量缩放第 ${i + 1} 个文件失败:`, error)
        results.push(null)
      }
    }
    
    return results
  }

  /**
   * 优化 GIF（不改变尺寸）
   * @param {File|Blob|ArrayBuffer} gifFile - GIF 文件
   * @param {Object} options - 优化选项
   * @param {number} options.lossy - lossy 压缩质量 (1-200)
   * @param {number} options.level - 优化级别 (1-3)
   * @param {number} options.loopCount - 循环次数，0 表示无限循环（默认），-1 表示保持原样
   * @returns {Promise<Blob>} 优化后的 GIF Blob
   */
  async optimizeGif(gifFile, options = {}) {
    const {
      lossy = this.quality,
      level = this.optimizationLevel,
      loopCount = 0  // 默认无限循环
    } = options

    try {
      const commandParts = ['-U']
      
      // 添加循环次数设置
      if (loopCount >= 0) {
        commandParts.push(`--loopcount=${loopCount}`)
      }
      
      if (lossy && lossy > 0) {
        commandParts.push(`--lossy=${lossy}`)
      }
      
      commandParts.push(`-O${level}`)
      commandParts.push('1.gif')
      commandParts.push('-o /out/output.gif')
      
      const command = commandParts.join(' ')
      
      if (this.debug) {
        console.log('GIF 优化命令:', command)
      }

      const result = await gifsicle.run({
        input: [{
          file: gifFile,
          name: '1.gif'
        }],
        command: [command]
      })

      if (!result || result.length === 0) {
        throw new Error('gifsicle 优化失败')
      }

      return new Blob([result[0]], { type: 'image/gif' })
      
    } catch (error) {
      console.error('GIF 优化失败:', error)
      throw new Error(`GIF 优化失败: ${error.message}`)
    }
  }

  /**
   * 获取 GIF 信息
   * @param {File|Blob|ArrayBuffer} gifFile - GIF 文件
   * @returns {Promise<Object>} GIF 信息
   */
  async getGifInfo(gifFile) {
    try {
      const result = await gifsicle.run({
        input: [{
          file: gifFile,
          name: '1.gif'
        }],
        command: ['--info 1.gif -o /out/info.txt']
      })

      if (!result || result.length === 0) {
        throw new Error('无法获取 GIF 信息')
      }

      const infoFile = result[0]
      const infoText = await infoFile.text()
      
      // 解析信息文本
      const info = this.parseGifInfo(infoText)
      
      return info
      
    } catch (error) {
      console.error('获取 GIF 信息失败:', error)
      // 返回基本信息
      return {
        size: gifFile.size || 0,
        type: 'image/gif'
      }
    }
  }

  /**
   * 解析 GIF 信息文本
   * @param {string} infoText - gifsicle --info 输出的文本
   * @returns {Object} 解析后的信息对象
   */
  parseGifInfo(infoText) {
    const info = {
      frames: 0,
      width: 0,
      height: 0,
      colors: 0,
      loopCount: 0
    }

    try {
      // 解析帧数
      const framesMatch = infoText.match(/(\d+) images?/)
      if (framesMatch) {
        info.frames = parseInt(framesMatch[1])
      }

      // 解析尺寸
      const sizeMatch = infoText.match(/logical screen (\d+)x(\d+)/)
      if (sizeMatch) {
        info.width = parseInt(sizeMatch[1])
        info.height = parseInt(sizeMatch[2])
      }

      // 解析颜色数
      const colorsMatch = infoText.match(/(\d+) colors/)
      if (colorsMatch) {
        info.colors = parseInt(colorsMatch[1])
      }

      // 解析循环次数
      if (infoText.includes('loop forever')) {
        info.loopCount = 0
      } else {
        const loopMatch = infoText.match(/loop count (\d+)/)
        if (loopMatch) {
          info.loopCount = parseInt(loopMatch[1])
        }
      }
    } catch (error) {
      console.warn('解析 GIF 信息时出错:', error)
    }

    return info
  }

  /**
   * 裁剪 GIF
   * @param {File|Blob|ArrayBuffer} gifFile - GIF 文件
   * @param {Object} cropRect - 裁剪区域 {x, y, width, height}
   * @returns {Promise<Blob>} 裁剪后的 GIF Blob
   */
  async cropGif(gifFile, cropRect) {
    const { x, y, width, height } = cropRect

    try {
      const command = [
        '-U',
        `--crop ${x},${y}+${width}x${height}`,
        '1.gif',
        '-o /out/output.gif'
      ].join(' ')

      if (this.debug) {
        console.log('GIF 裁剪命令:', command)
      }

      const result = await gifsicle.run({
        input: [{
          file: gifFile,
          name: '1.gif'
        }],
        command: [command]
      })

      if (!result || result.length === 0) {
        throw new Error('gifsicle 裁剪失败')
      }

      return new Blob([result[0]], { type: 'image/gif' })
      
    } catch (error) {
      console.error('GIF 裁剪失败:', error)
      throw new Error(`GIF 裁剪失败: ${error.message}`)
    }
  }

  /**
   * 清理资源
   */
  dispose() {
    // gifsicle-wasm-browser 不需要特殊的清理
    if (this.debug) {
      console.log('WasmGifScaler disposed')
    }
  }

  /**
   * 设置调试模式
   * @param {boolean} enabled - 是否启用调试
   */
  setDebug(enabled) {
    this.debug = enabled
  }

  /**
   * 设置压缩质量
   * @param {number} quality - 压缩质量 (1-200)
   */
  setQuality(quality) {
    if (quality < 1 || quality > 200) {
      throw new Error('质量参数必须在 1-200 之间')
    }
    this.quality = quality
  }

  /**
   * 设置优化级别
   * @param {number} level - 优化级别 (1-3)
   */
  setOptimizationLevel(level) {
    if (level < 1 || level > 3) {
      throw new Error('优化级别必须在 1-3 之间')
    }
    this.optimizationLevel = level
  }
}

export default WasmGifScaler

