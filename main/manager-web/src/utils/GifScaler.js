/**
 * GifScaler 类
 * 用于对 GIF 表情进行缩放处理
 * 
 * 主要功能：
 * - 解析 GIF 文件的每一帧
 * - 对每一帧进行缩放处理
 * - 重新生成缩放后的 GIF 文件
 * - 支持保持原始动画时序
 * 
 * 依赖建议：
 * 为了支持完整的多帧 GIF 处理，建议安装以下依赖：
 * ```bash
 * npm install gif.js gifuct-js
 * ```
 * 
 * 使用示例：
 * ```javascript
 * const scaler = new GifScaler({ 
 *   quality: 10, 
 *   debug: true,
 *   scalingMode: 'auto',  // 'auto', 'smooth', 'sharp', 'pixelated'
 *   workers: 2,  // 使用 2 个 worker 线程进行并行处理
 *   workerScript: '/share/gif.worker.js'  // Worker 脚本路径
 * })
 * const scaledGif = await scaler.scaleGif(gifFile, {
 *   maxWidth: 64,
 *   maxHeight: 64,
 *   keepAspectRatio: true
 * })
 * ```
 */
// 可选依赖：如果未安装则使用降级方案
// 注意：这些依赖需要手动安装: npm install gifuct-js gif.js
let parseGIF, decompressFrames, GIF
try {
  // 尝试动态导入（如果使用 ES6 modules）
  if (typeof require !== 'undefined') {
    try {
      const gifuct = require('gifuct-js')
      parseGIF = gifuct.parseGIF || gifuct.default?.parseGIF
      decompressFrames = gifuct.decompressFrames || gifuct.default?.decompressFrames
    } catch (e) {
      console.warn('gifuct-js 未安装，GIF 处理功能将受限')
    }
    try {
      GIF = require('gif.js')
      if (GIF && GIF.default) GIF = GIF.default
    } catch (e) {
      console.warn('gif.js 未安装，GIF 处理功能将受限')
    }
  }
} catch (e) {
  console.warn('GIF 依赖加载失败，GIF 处理功能将受限:', e)
}


class GifScaler {
  constructor(options = {}) {
    this.options = {
      quality: options.quality || 10,  // GIF 质量 (1-20, 越小质量越高)
      repeat: options.repeat !== undefined ? options.repeat : -1,  // 重复次数 (-1 为无限循环)
      debug: options.debug || false,  // 调试模式
      scalingMode: options.scalingMode || 'auto',  // 缩放模式: 'auto', 'smooth', 'sharp', 'pixelated'
      workers: options.workers || 2,  // Worker 线程数量 (1-4, 更多线程可以提高大型 GIF 的处理速度)
      // 在 Vue2 + webpack 环境中没有 import.meta.env，使用浏览器 origin 作为默认前缀，避免 undefined
      workerScript: options.workerScript || `${(typeof window !== 'undefined' ? window.location.origin : '')}/workers/gif.worker.js`,  // Worker 脚本路径
      ...options
    }
    
    this.canvas = null
    this.ctx = null
    this.frames = []
    this.delays = []
    this.originalWidth = 0
    this.originalHeight = 0
    this.targetWidth = 0
    this.targetHeight = 0
    this.gifRepeat = 0  // 默认无限循环
  }

  /**
   * 初始化 Canvas 和上下文
   * @param {number} width - Canvas 宽度
   * @param {number} height - Canvas 高度
   * @private
   */
  initCanvas(width, height) {
    this.canvas = document.createElement('canvas')
    this.canvas.width = width
    this.canvas.height = height
    this.ctx = this.canvas.getContext('2d')
    
    if (this.options.debug) {
      console.log(`Canvas initialized: ${width}x${height}`)
    }
  }

  /**
   * 解析 GIF 文件并提取所有帧
   * @param {File|Blob} gifFile - GIF 文件
   * @returns {Promise<Array>} 返回帧数据数组
   */
  async parseGifFrames(gifFile) {
    try {
      // 只使用 gifuct-js 进行 GIF 解析
      return await this.parseGifWithGifuct(gifFile)
    } catch (error) {
      throw new Error(`GIF 解析失败: ${error.message}`)
    }
  }


  /**
   * 使用 gifuct-js 进行高级 GIF 解析
   * @param {File|Blob} gifFile - GIF 文件
   * @returns {Promise<Array>} 返回帧数据数组
   */
  async parseGifWithGifuct(gifFile) {
    const arrayBuffer = await this.fileToArrayBuffer(gifFile)
    const gif = parseGIF(arrayBuffer)
    const frames = decompressFrames(gif, true)
    
    this.originalWidth = gif.lsd.width
    this.originalHeight = gif.lsd.height
    this.frames = []
    this.delays = []
    
    // 读取原始GIF的循环信息
    // 如果用户没有手动设置repeat，则使用原始GIF的循环设置
    if (this.options.repeat === -1) {  // 使用默认值
      // gif.lsd.globalColorTableFlag, gif.applicationExtensions 等信息中可能包含循环信息
      // 检查是否有 NETSCAPE2.0 应用扩展，它定义了循环次数
      let originalRepeat = 0  // 0 表示无限循环
      
      if (gif.applicationExtensions) {
        const netscapeExt = gif.applicationExtensions.find(ext => 
          ext.identifier === 'NETSCAPE' && ext.authenticationCode === '2.0'
        )
        if (netscapeExt && netscapeExt.data && netscapeExt.data.length >= 3) {
          // NETSCAPE2.0 格式：[0x01, 低字节, 高字节]
          originalRepeat = netscapeExt.data[1] + (netscapeExt.data[2] << 8)
        }
      }
      
      this.gifRepeat = originalRepeat
      
      if (this.options.debug) {
        console.log(`原始GIF循环设置: ${originalRepeat === 0 ? '无限循环' : originalRepeat + '次'}`)
      }
    } else {
      this.gifRepeat = this.options.repeat
    }
    
    // 创建主画布来处理每一帧
    const canvas = document.createElement('canvas')
    canvas.width = this.originalWidth
    canvas.height = this.originalHeight
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    
    // 保存前一帧的图像数据（用于disposal type 3）
    let previousFrameData = null
    
    for (let i = 0; i < frames.length; i++) {
      const frame = frames[i]
      
      // 根据 disposal 方法处理画布
      if (i === 0) {
        // 第一帧：清除整个画布为透明
        ctx.clearRect(0, 0, canvas.width, canvas.height)
      } else if (frame.disposalType === 2) {
        // 清除到背景色（透明）
        ctx.clearRect(0, 0, canvas.width, canvas.height)
      } else if (frame.disposalType === 3 && previousFrameData) {
        // 恢复到前一帧状态
        ctx.putImageData(previousFrameData, 0, 0)
      }
      // disposalType 0 和 1：不清除，保持当前内容
      
      // 保存当前状态（用于disposalType 3）
      if (frame.disposalType === 3) {
        previousFrameData = ctx.getImageData(0, 0, this.originalWidth, this.originalHeight)
      }
      
      // 创建帧画布并绘制当前帧
      const frameCanvas = document.createElement('canvas')
      frameCanvas.width = frame.dims.width
      frameCanvas.height = frame.dims.height
      const frameCtx = frameCanvas.getContext('2d', { willReadFrequently: true })
      
      // 确保帧画布背景透明
      frameCtx.clearRect(0, 0, frame.dims.width, frame.dims.height)
      
      // 绘制帧像素数据
      const imageData = new ImageData(frame.patch, frame.dims.width, frame.dims.height)
      frameCtx.putImageData(imageData, 0, 0)
      
      // 将帧绘制到主画布上
      ctx.drawImage(frameCanvas, frame.dims.left || 0, frame.dims.top || 0)
      
      // 获取完整帧的图像数据
      const fullFrameImageData = ctx.getImageData(0, 0, this.originalWidth, this.originalHeight)
      this.frames.push(fullFrameImageData)
      this.delays.push(frame.delay || 100)
    }
    
    if (this.options.debug) {
      console.log(`GIF parsed (gifuct-js): ${this.originalWidth}x${this.originalHeight}, frames: ${this.frames.length}`)
    }
    
    return this.frames
  }

  /**
   * 缩放单个图像帧
   * @param {ImageData} imageData - 源图像数据
   * @param {number} targetWidth - 目标宽度
   * @param {number} targetHeight - 目标高度
   * @returns {ImageData} 缩放后的图像数据
   */
  scaleFrame(imageData, targetWidth, targetHeight) {
    const sourceCanvas = document.createElement('canvas')
    const sourceCtx = sourceCanvas.getContext('2d')
    sourceCanvas.width = imageData.width
    sourceCanvas.height = imageData.height
    
    // 确保源画布背景透明
    sourceCtx.clearRect(0, 0, imageData.width, imageData.height)
    sourceCtx.putImageData(imageData, 0, 0)
    
    const targetCanvas = document.createElement('canvas')
    const targetCtx = targetCanvas.getContext('2d', { willReadFrequently: true })
    targetCanvas.width = targetWidth
    targetCanvas.height = targetHeight
    
    // 确保目标画布背景透明
    targetCtx.clearRect(0, 0, targetWidth, targetHeight)
    
    // 根据缩放模式选择不同的缩放策略
    const scaleRatio = Math.min(targetWidth / imageData.width, targetHeight / imageData.height)
    const scalingMode = this.getOptimalScalingMode(scaleRatio)
    
    // 对于大幅缩放，使用特殊的多步缩放算法来减少边缘模糊
    if (scaleRatio < 0.5 && scalingMode === 'pixelated') {
      this.scaleWithEdgePreservation(sourceCtx, targetCtx, imageData.width, imageData.height, targetWidth, targetHeight)
    } else {
      this.applyScalingMode(targetCtx, scalingMode)
      targetCtx.drawImage(
        sourceCanvas, 
        0, 0, imageData.width, imageData.height,
        0, 0, targetWidth, targetHeight
      )
    }
    
    return targetCtx.getImageData(0, 0, targetWidth, targetHeight)
  }

  /**
   * 根据缩放比例获取最优的缩放模式
   * @param {number} scaleRatio - 缩放比例
   * @returns {string} 缩放模式
   */
  getOptimalScalingMode(scaleRatio) {
    if (this.options.scalingMode !== 'auto') {
      return this.options.scalingMode
    }
    
    // 自动选择缩放模式
    if (scaleRatio >= 0.5) {
      // 缩放比例较大时，使用平滑缩放保持质量
      return 'smooth'
    } else if (scaleRatio >= 0.25) {
      // 中等缩放比例，使用锐化缩放保持边缘清晰
      return 'sharp'
    } else {
      // 大幅缩小时，使用像素化缩放避免模糊
      return 'pixelated'
    }
  }

  /**
   * 应用指定的缩放模式
   * @param {CanvasRenderingContext2D} ctx - Canvas上下文
   * @param {string} mode - 缩放模式
   */
  applyScalingMode(ctx, mode) {
    switch (mode) {
      case 'smooth':
        // 平滑缩放 - 适合小幅缩放
        ctx.imageSmoothingEnabled = true
        ctx.imageSmoothingQuality = 'high'
        break
        
      case 'sharp':
        // 锐化缩放 - 适合中等缩放，保持边缘清晰
        ctx.imageSmoothingEnabled = true
        ctx.imageSmoothingQuality = 'high'
        break
        
      case 'pixelated':
        // 像素化缩放 - 适合大幅缩放，避免模糊
        ctx.imageSmoothingEnabled = false
        break
        
      default:
        // 默认平滑缩放
        ctx.imageSmoothingEnabled = true
        ctx.imageSmoothingQuality = 'high'
    }
  }

  /**
   * 边缘保持缩放算法 - 减少线条变粗的问题
   * @param {CanvasRenderingContext2D} sourceCtx - 源Canvas上下文
   * @param {CanvasRenderingContext2D} targetCtx - 目标Canvas上下文
   * @param {number} sourceWidth - 源宽度
   * @param {number} sourceHeight - 源高度
   * @param {number} targetWidth - 目标宽度
   * @param {number} targetHeight - 目标高度
   */
  scaleWithEdgePreservation(sourceCtx, targetCtx, sourceWidth, sourceHeight, targetWidth, targetHeight) {
    const scaleRatio = Math.min(targetWidth / sourceWidth, targetHeight / sourceHeight)
    
    // 如果缩放比例很小，使用多步缩放来保持边缘清晰
    if (scaleRatio < 0.5) {
      // 创建中间画布，分步缩放
      const intermediateCanvas = document.createElement('canvas')
      const intermediateCtx = intermediateCanvas.getContext('2d')
      
      // 第一步：缩放到中间尺寸（至少50%）
      const intermediateWidth = Math.max(sourceWidth * 0.5, targetWidth)
      const intermediateHeight = Math.max(sourceHeight * 0.5, targetHeight)
      
      intermediateCanvas.width = intermediateWidth
      intermediateCanvas.height = intermediateHeight
      
      // 使用像素化缩放进行第一步
      intermediateCtx.imageSmoothingEnabled = false
      intermediateCtx.drawImage(
        sourceCtx.canvas,
        0, 0, sourceWidth, sourceHeight,
        0, 0, intermediateWidth, intermediateHeight
      )
      
      // 第二步：从中间尺寸缩放到目标尺寸
      if (intermediateWidth !== targetWidth || intermediateHeight !== targetHeight) {
        // 如果还需要进一步缩放，使用平滑缩放
        targetCtx.imageSmoothingEnabled = true
        targetCtx.imageSmoothingQuality = 'high'
        targetCtx.drawImage(
          intermediateCanvas,
          0, 0, intermediateWidth, intermediateHeight,
          0, 0, targetWidth, targetHeight
        )
      } else {
        // 直接复制
        targetCtx.drawImage(intermediateCanvas, 0, 0)
      }
    } else {
      // 缩放比例较大，直接使用像素化缩放
      targetCtx.imageSmoothingEnabled = false
      targetCtx.drawImage(
        sourceCtx.canvas,
        0, 0, sourceWidth, sourceHeight,
        0, 0, targetWidth, targetHeight
      )
    }
  }

  /**
   * 计算保持宽高比的目标尺寸
   * @param {number} originalWidth - 原始宽度
   * @param {number} originalHeight - 原始高度  
   * @param {number} maxWidth - 最大宽度
   * @param {number} maxHeight - 最大高度
   * @returns {Object} 包含 width 和 height 的对象
   */
  calculateTargetSize(originalWidth, originalHeight, maxWidth, maxHeight) {
    const ratio = Math.min(maxWidth / originalWidth, maxHeight / originalHeight)
    
    return {
      width: Math.round(originalWidth * ratio),
      height: Math.round(originalHeight * ratio)
    }
  }

  /**
   * 主要的缩放函数
   * @param {File|Blob} gifFile - 输入的 GIF 文件
   * @param {Object} scaleOptions - 缩放选项
   * @param {number} scaleOptions.maxWidth - 最大宽度
   * @param {number} scaleOptions.maxHeight - 最大高度
   * @param {boolean} scaleOptions.keepAspectRatio - 是否保持宽高比
   * @returns {Promise<Blob>} 返回缩放后的 GIF Blob
   */
  async scaleGif(gifFile, scaleOptions) {
    try {
      const { maxWidth, maxHeight, keepAspectRatio = true } = scaleOptions
      
      if (!maxWidth || !maxHeight) {
        throw new Error('必须指定最大宽度和高度')
      }
      
      // 解析原始 GIF
      await this.parseGifFrames(gifFile)
      
      // 计算目标尺寸
      let targetSize
      if (keepAspectRatio) {
        targetSize = this.calculateTargetSize(
          this.originalWidth, 
          this.originalHeight, 
          maxWidth, 
          maxHeight
        )
      } else {
        targetSize = { width: maxWidth, height: maxHeight }
      }
      
      this.targetWidth = targetSize.width
      this.targetHeight = targetSize.height
      
      // 检查是否需要缩放
      if (this.targetWidth === this.originalWidth && this.targetHeight === this.originalHeight) {
        if (this.options.debug) {
          console.log('无需缩放，返回原始文件')
        }
        return gifFile
      }
      
      // 缩放所有帧
      const scaledFrames = this.frames.map(frame => 
        this.scaleFrame(frame, this.targetWidth, this.targetHeight)
      )
      
      // 生成新的 GIF
      const scaledGifBlob = await this.generateGif(scaledFrames, this.delays)
      
      if (this.options.debug) {
        console.log(`GIF 缩放完成: ${this.originalWidth}x${this.originalHeight} -> ${this.targetWidth}x${this.targetHeight}`)
      }
      
      return scaledGifBlob
      
    } catch (error) {
      throw new Error(`GIF 缩放失败: ${error.message}`)
    }
  }

  /**
   * 生成新的 GIF 文件
   * @param {Array<ImageData>} frames - 图像帧数组
   * @param {Array<number>} delays - 延迟数组
   * @returns {Promise<Blob>} 生成的 GIF Blob
   */
  async generateGif(frames, delays) {
    try {
      // 统一使用 gif.js 生成 GIF，无论单帧还是多帧
      return await this.generateGifWithGifJs(frames, delays)
      
    } catch (error) {
      throw new Error(`GIF 生成失败: ${error.message}`)
    }
  }

  /**
   * 使用 gif.js 生成动态 GIF
   * @param {Array<ImageData>} frames - 图像帧数组
   * @param {Array<number>} delays - 延迟数组
   * @returns {Promise<Blob>} 生成的 GIF Blob
   */
  async generateGifWithGifJs(frames, delays) {
    return new Promise((resolve, reject) => {
      if (!GIF) {
        throw new Error('gif.js 未安装，无法生成 GIF 文件。请运行: npm install gif.js')
      }
      const gif = new GIF({
        workers: this.options.workers,
        quality: this.options.quality,
        width: this.targetWidth,
        height: this.targetHeight,
        transparent: 'rgba(255, 0, 255, 0)',
        repeat: this.gifRepeat !== undefined ? this.gifRepeat : 0,  // 0表示无限循环
        workerScript: this.options.workerScript  // 指定 worker 脚本路径
        // gif.js 会自动处理透明像素，不需要手动设置 transparent 选项
      })
      
      // 添加所有帧
      frames.forEach((frameData, index) => {
        const canvas = document.createElement('canvas')
        canvas.width = this.targetWidth
        canvas.height = this.targetHeight
        const ctx = canvas.getContext('2d', { willReadFrequently: true })
        
        // 确保画布背景透明
        ctx.clearRect(0, 0, this.targetWidth, this.targetHeight)
        ctx.putImageData(frameData, 0, 0)
        
        gif.addFrame(canvas, { delay: delays[index] || 100 })
      })
      
      gif.on('finished', (blob) => {
        if (this.options.debug) {
          console.log(`GIF generated: ${frames.length} frames, ${blob.size} bytes, repeat: ${this.gifRepeat === 0 ? '无限循环' : this.gifRepeat + '次'}`)
        }
        resolve(blob)
      })
      
      gif.on('abort', () => {
        reject(new Error('GIF 生成被中止'))
      })
      
      gif.render()
    })
  }

  /**
   * 获取 GIF 信息
   * @param {File|Blob} gifFile - GIF 文件
   * @returns {Promise<Object>} GIF 信息对象
   */
  async getGifInfo(gifFile) {
    try {
      // 使用 parseGifWithGifuct 解析获取信息
      await this.parseGifWithGifuct(gifFile)
      
      return {
        width: this.originalWidth,
        height: this.originalHeight,
        frameCount: this.frames.length,
        totalDuration: this.delays.reduce((sum, delay) => sum + delay, 0),
        repeat: this.gifRepeat,
        fileSize: gifFile.size
      }
    } catch (error) {
      throw new Error(`获取 GIF 信息失败: ${error.message}`)
    }
  }

  /**
   * 检查是否需要缩放
   * @param {File|Blob} gifFile - GIF 文件
   * @param {number} maxWidth - 最大宽度
   * @param {number} maxHeight - 最大高度
   * @returns {Promise<boolean>} 是否需要缩放
   */
  async needsScaling(gifFile, maxWidth, maxHeight) {
    const info = await this.getGifInfo(gifFile)
    return info.width > maxWidth || info.height > maxHeight
  }

  /**
   * 将文件转换为 ArrayBuffer
   * @param {File|Blob} file - 文件对象
   * @returns {Promise<ArrayBuffer>} ArrayBuffer
   */
  async fileToArrayBuffer(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = () => reject(new Error('文件读取失败'))
      reader.readAsArrayBuffer(file)
    })
  }

  /**
   * 批量缩放多个 GIF 文件
   * @param {Array<File>} gifFiles - GIF 文件数组
   * @param {Object} scaleOptions - 缩放选项
   * @returns {Promise<Array<Blob>>} 缩放后的 GIF 数组
   */
  async scaleBatchGifs(gifFiles, scaleOptions) {
    const results = []
    
    for (let i = 0; i < gifFiles.length; i++) {
      try {
        if (this.options.debug) {
          console.log(`处理第 ${i + 1}/${gifFiles.length} 个文件`)
        }
        
        const scaledGif = await this.scaleGif(gifFiles[i], scaleOptions)
        results.push({
          index: i,
          success: true,
          result: scaledGif,
          originalFile: gifFiles[i]
        })
      } catch (error) {
        results.push({
          index: i,
          success: false,
          error: error.message,
          originalFile: gifFiles[i]
        })
      }
    }
    
    return results
  }

  /**
   * 获取建议的缩放尺寸
   * @param {number} originalWidth - 原始宽度
   * @param {number} originalHeight - 原始高度
   * @param {Array<Object>} targetSizes - 目标尺寸数组，如 [{name: '32x32', width: 32, height: 32}]
   * @returns {Object} 建议的缩放配置
   */
  getSuggestedScaling(originalWidth, originalHeight, targetSizes = []) {
    const suggestions = []
    
    // 默认目标尺寸
    const defaultSizes = [
      { name: 'emoji_32', width: 32, height: 32 },
      { name: 'emoji_64', width: 64, height: 64 },
      { name: 'small', width: 48, height: 48 },
      { name: 'medium', width: 96, height: 96 }
    ]
    
    const sizes = targetSizes.length > 0 ? targetSizes : defaultSizes
    
    sizes.forEach(size => {
      const targetSize = this.calculateTargetSize(
        originalWidth, 
        originalHeight, 
        size.width, 
        size.height
      )
      
      suggestions.push({
        name: size.name,
        target: size,
        actual: targetSize,
        needsScaling: targetSize.width !== originalWidth || targetSize.height !== originalHeight,
        scaleRatio: targetSize.width / originalWidth
      })
    })
    
    return {
      original: { width: originalWidth, height: originalHeight },
      suggestions
    }
  }

  /**
   * 清理资源
   */
  dispose() {
    if (this.canvas) {
      this.canvas = null
      this.ctx = null
    }
    this.frames = []
    this.delays = []
    
    // 清理可能的 Object URLs
    if (this.tempObjectUrls) {
      this.tempObjectUrls.forEach(url => URL.revokeObjectURL(url))
      this.tempObjectUrls = []
    }
  }
}

export default GifScaler
