/**
 * SpiffsGenerator 类
 * 模仿 spiffs_assets_gen.py 的功能，用于在浏览器端生成 assets.bin 文件
 * 
 * 文件格式：
 * {
 *     total_files: int (4字节)          // 文件总数
 *     checksum: int (4字节)            // 校验和
 *     combined_data_length: int (4字节) // 数据总长度
 *     mmap_table: [                    // 文件映射表
 *         {
 *             name: char[32]           // 文件名 (32字节)
 *             size: int (4字节)        // 文件大小
 *             offset: int (4字节)      // 文件偏移量 
 *             width: short (2字节)     // 图片宽度
 *             height: short (2字节)    // 图片高度
 *         }
 *         ...
 *     ]
 *     file_data: [                     // 文件数据
 *         0x5A 0x5A + file1_data      // 每个文件前面加0x5A5A标识
 *         0x5A 0x5A + file2_data
 *         ...
 *     ]
 * }
 */

class SpiffsGenerator {
  constructor() {
    this.files = []
    this.textEncoder = new TextEncoder()
  }

  /**
   * 添加文件
   * @param {string} filename - 文件名
   * @param {ArrayBuffer} data - 文件数据
   * @param {Object} options - 可选参数 {width?, height?}
   */
  addFile(filename, data, options = {}) {
    if (filename.length > 32) {
      console.warn(`文件名 "${filename}" 超过32字节，将被截断`)
    }

    this.files.push({
      filename,
      data,
      size: data.byteLength,
      width: options.width || 0,
      height: options.height || 0
    })
  }

  /**
   * 从图片文件获取尺寸信息
   * @param {ArrayBuffer} imageData - 图片数据
   * @returns {Promise<Object>} {width, height}
   */
  async getImageDimensions(imageData) {
    return new Promise((resolve) => {
      try {
        const blob = new Blob([imageData])
        const url = URL.createObjectURL(blob)
        const img = new Image()
        
        img.onload = () => {
          URL.revokeObjectURL(url)
          resolve({ width: img.width, height: img.height })
        }
        
        img.onerror = () => {
          URL.revokeObjectURL(url)
          resolve({ width: 0, height: 0 })
        }
        
        img.src = url
      } catch (error) {
        resolve({ width: 0, height: 0 })
      }
    })
  }

  /**
   * 检查是否为特殊图片格式 (.sjpg, .spng, .sqoi)
   * @param {string} filename - 文件名
   * @param {ArrayBuffer} data - 文件数据
   * @returns {Object} {width, height}
   */
  parseSpecialImageFormat(filename, data) {
    const ext = filename.toLowerCase().split('.').pop()
    
    if (['.sjpg', '.spng', '.sqoi'].includes('.' + ext)) {
      try {
        // 特殊格式的头部结构：偏移14字节后是宽度和高度（各2字节，小端序）
        const view = new DataView(data)
        const width = view.getUint16(14, true)  // 小端序
        const height = view.getUint16(16, true) // 小端序
        return { width, height }
      } catch (error) {
        console.warn(`解析特殊图片格式失败: ${filename}`, error)
      }
    }
    
    return { width: 0, height: 0 }
  }

  /**
   * 将32位整数转换为小端序字节数组
   * @param {number} value - 整数值
   * @returns {Uint8Array} 4字节的小端序数组
   */
  packUint32(value) {
    const bytes = new Uint8Array(4)
    bytes[0] = value & 0xFF
    bytes[1] = (value >> 8) & 0xFF
    bytes[2] = (value >> 16) & 0xFF
    bytes[3] = (value >> 24) & 0xFF
    return bytes
  }

  /**
   * 将16位整数转换为小端序字节数组
   * @param {number} value - 整数值
   * @returns {Uint8Array} 2字节的小端序数组
   */
  packUint16(value) {
    const bytes = new Uint8Array(2)
    bytes[0] = value & 0xFF
    bytes[1] = (value >> 8) & 0xFF
    return bytes
  }

  /**
   * 将字符串打包为固定长度的二进制数据
   * @param {string} string - 输入字符串
   * @param {number} maxLen - 最大长度
   * @returns {Uint8Array} 打包后的二进制数据
   */
  packString(string, maxLen) {
    const bytes = new Uint8Array(maxLen)
    const encoded = this.textEncoder.encode(string)
    
    // 复制字符串数据，确保不超过最大长度
    const copyLen = Math.min(encoded.length, maxLen)
    bytes.set(encoded.slice(0, copyLen), 0)
    
    // 剩余字节为0填充
    return bytes
  }

  /**
   * 计算校验和
   * @param {Uint8Array} data - 数据
   * @returns {number} 16位校验和
   */
  computeChecksum(data) {
    let checksum = 0
    for (let i = 0; i < data.length; i++) {
      checksum += data[i]
    }
    return checksum & 0xFFFF
  }

  /**
   * 对文件进行排序
   * @param {Array} files - 文件列表
   * @returns {Array} 排序后的文件列表
   */
  sortFiles(files) {
    return files.slice().sort((a, b) => {
      const extA = a.filename.split('.').pop() || ''
      const extB = b.filename.split('.').pop() || ''
      
      if (extA !== extB) {
        return extA.localeCompare(extB)
      }
      
      const nameA = a.filename.replace(/\.[^/.]+$/, '')
      const nameB = b.filename.replace(/\.[^/.]+$/, '')
      return nameA.localeCompare(nameB)
    })
  }

  /**
   * 生成 assets.bin 文件
   * @param {Function} progressCallback - 进度回调函数
   * @returns {Promise<ArrayBuffer>} 生成的 assets.bin 数据
   */
  async generate(progressCallback = null) {
    if (this.files.length === 0) {
      throw new Error('没有文件可打包')
    }

    if (progressCallback) progressCallback(0, '开始打包文件...')

    // 排序文件
    const sortedFiles = this.sortFiles(this.files)
    const totalFiles = sortedFiles.length

    // 处理文件信息并获取图片尺寸
    const fileInfoList = []
    let mergedDataSize = 0

    for (let i = 0; i < sortedFiles.length; i++) {
      const file = sortedFiles[i]
      let width = file.width
      let height = file.height

      if (progressCallback) {
        progressCallback(10 + (i / totalFiles) * 30, `处理文件: ${file.filename}`)
      }

      // 如果没有提供尺寸信息，尝试自动获取
      if (width === 0 && height === 0) {
        // 先检查特殊图片格式
        const specialDimensions = this.parseSpecialImageFormat(file.filename, file.data)
        if (specialDimensions.width > 0 || specialDimensions.height > 0) {
          width = specialDimensions.width
          height = specialDimensions.height
        } else {
          // 尝试作为普通图片解析
          const ext = file.filename.toLowerCase().split('.').pop()
          if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) {
            const dimensions = await this.getImageDimensions(file.data)
            width = dimensions.width
            height = dimensions.height
          }
        }
      }

      // offset 是文件在 mergedData 中的位置，包括前缀
      // 与 Python 参考代码一致：offset = len(merged_data) (在添加前缀之前)
      const fileOffset = mergedDataSize
      
      fileInfoList.push({
        filename: file.filename,
        data: file.data,
        size: file.size,
        offset: fileOffset,  // 文件在 mergedData 中的位置（包括前缀）
        width,
        height
      })

      // 更新 mergedDataSize：包括前缀(2字节) + 文件数据
      mergedDataSize += 2 + file.size
    }

    if (progressCallback) progressCallback(40, '构建文件映射表...')

    // 构建映射表
    const mmapTableSize = totalFiles * (32 + 4 + 4 + 2 + 2) // name + size + offset + width + height
    const mmapTable = new Uint8Array(mmapTableSize)
    let mmapOffset = 0

    for (const fileInfo of fileInfoList) {
      // 文件名 (32字节)
      mmapTable.set(this.packString(fileInfo.filename, 32), mmapOffset)
      mmapOffset += 32

      // 文件大小 (4字节)
      mmapTable.set(this.packUint32(fileInfo.size), mmapOffset)
      mmapOffset += 4

      // 文件偏移 (4字节)
      mmapTable.set(this.packUint32(fileInfo.offset), mmapOffset)
      mmapOffset += 4

      // 图片宽度 (2字节)
      mmapTable.set(this.packUint16(fileInfo.width), mmapOffset)
      mmapOffset += 2

      // 图片高度 (2字节)  
      mmapTable.set(this.packUint16(fileInfo.height), mmapOffset)
      mmapOffset += 2
    }

    if (progressCallback) progressCallback(60, '合并文件数据...')

    // 合并文件数据
    const mergedData = new Uint8Array(mergedDataSize)
    let mergedOffset = 0

    for (let i = 0; i < fileInfoList.length; i++) {
      const fileInfo = fileInfoList[i]
      
      if (progressCallback) {
        progressCallback(60 + (i / totalFiles) * 20, `合并文件: ${fileInfo.filename}`)
      }

      // 添加0x5A5A前缀
      mergedData[mergedOffset] = 0x5A
      mergedData[mergedOffset + 1] = 0x5A
      mergedOffset += 2

      // 添加文件数据
      mergedData.set(new Uint8Array(fileInfo.data), mergedOffset)
      mergedOffset += fileInfo.size
    }

    if (progressCallback) progressCallback(80, '计算校验和...')

    // 计算组合数据的校验和
    // 注意：combinedData = mmapTable + mergedData，顺序必须与Python参考代码一致
    // 设备端从偏移12开始读取，读取stored_len长度的数据，这应该等于combinedData
    const combinedData = new Uint8Array(mmapTableSize + mergedDataSize)
    combinedData.set(mmapTable, 0)
    combinedData.set(mergedData, mmapTableSize)
    
    // 验证数据一致性
    if (mmapTable.length !== mmapTableSize) {
      console.error('[SpiffsGenerator] mmapTable长度不匹配:', mmapTable.length, '!=', mmapTableSize)
    }
    if (mergedData.length !== mergedDataSize) {
      console.error('[SpiffsGenerator] mergedData长度不匹配:', mergedData.length, '!=', mergedDataSize)
    }
    if (combinedData.length !== mmapTableSize + mergedDataSize) {
      console.error('[SpiffsGenerator] combinedData长度不匹配:', combinedData.length, '!=', mmapTableSize + mergedDataSize)
    }
    
    // 计算校验和（对combinedData的所有字节求和，取低16位）
    // 与设备端 CalculateChecksum 逻辑一致：对数据求和，取低16位
    // 注意：必须在写入文件之前计算校验码，确保使用的数据与最终写入的数据一致
    const combinedDataLength = combinedData.length
    const checksum = this.computeChecksum(combinedData)
    
    // 调试日志：详细输出校验码计算过程
    console.log('[SpiffsGenerator] 校验码计算:', {
      totalFiles,
      mmapTableSize,
      mergedDataSize,
      combinedDataLength,
      checksum: `0x${checksum.toString(16).toUpperCase().padStart(4, '0')}`,
      checksumDecimal: checksum,
      mmapTableLength: mmapTable.length,
      mergedDataLength: mergedData.length,
      combinedDataLengthActual: combinedData.length
    })
    
    // 验证：计算前几个字节的校验码（用于调试）
    if (combinedData.length > 0) {
      const firstBytes = Array.from(combinedData.slice(0, Math.min(20, combinedData.length)))
      const firstBytesSum = firstBytes.reduce((sum, b) => sum + b, 0)
      console.log('[SpiffsGenerator] 前20字节:', firstBytes.map(b => `0x${b.toString(16).toUpperCase().padStart(2, '0')}`).join(' '))
      console.log('[SpiffsGenerator] 前20字节和:', firstBytesSum)
    }

    if (progressCallback) progressCallback(90, '构建最终文件...')

    // 构建最终输出
    // 文件格式：header (12字节) + combinedData
    // header格式：[4字节文件数][4字节校验码][4字节数据长度]
    // 注意：必须确保 combinedData 在写入前不被修改
    const headerSize = 4 + 4 + 4 // total_files + checksum + combined_data_length
    const totalSize = headerSize + combinedDataLength
    const finalData = new Uint8Array(totalSize)
    
    let offset = 0

    // 写入文件总数（4字节，小端序）
    finalData.set(this.packUint32(totalFiles), offset)
    offset += 4

    // 写入校验和（4字节，小端序）
    // 注意：校验码是16位值，但作为32位写入（高16位为0）
    const checksumBytes = this.packUint32(checksum)
    finalData.set(checksumBytes, offset)
    
    // 调试日志：验证校验码写入
    console.log('[SpiffsGenerator] 校验码写入:', {
      checksum: `0x${checksum.toString(16).toUpperCase().padStart(4, '0')}`,
      packedBytes: Array.from(checksumBytes).map(b => `0x${b.toString(16).toUpperCase().padStart(2, '0')}`),
      offset,
      // 验证写入的校验码字节
      writtenChecksum: (checksumBytes[0] | (checksumBytes[1] << 8)) & 0xFFFF
    })
    
    offset += 4

    // 写入组合数据长度（4字节，小端序）
    finalData.set(this.packUint32(combinedDataLength), offset)
    offset += 4

    // 写入组合数据（mmapTable + mergedData）
    // 注意：这里必须使用之前计算校验码时使用的同一个 combinedData
    finalData.set(combinedData, offset)
    
    // 验证：重新计算写入后的 combinedData 的校验码，确保一致
    const writtenCombinedData = finalData.slice(offset, offset + combinedDataLength)
    const verifyChecksum = this.computeChecksum(writtenCombinedData)
    if (verifyChecksum !== checksum) {
      console.error('[SpiffsGenerator] 警告：写入后的校验码验证失败！', {
        originalChecksum: `0x${checksum.toString(16).toUpperCase().padStart(4, '0')}`,
        verifyChecksum: `0x${verifyChecksum.toString(16).toUpperCase().padStart(4, '0')}`
      })
    } else {
      console.log('[SpiffsGenerator] 校验码验证通过:', {
        checksum: `0x${checksum.toString(16).toUpperCase().padStart(4, '0')}`
      })
    }
    
    // 调试日志：验证最终文件结构
    console.log('[SpiffsGenerator] 最终文件结构:', {
      totalSize,
      headerSize,
      combinedDataLength,
      fileCount: totalFiles,
      checksum: `0x${checksum.toString(16).toUpperCase().padStart(4, '0')}`,
      headerBytes: Array.from(finalData.slice(0, 12)).map(b => `0x${b.toString(16).toUpperCase().padStart(2, '0')}`)
    })

    if (progressCallback) progressCallback(100, '打包完成')

    return finalData.buffer
  }

  /**
   * 获取文件统计信息
   * @returns {Object} 统计信息
   */
  getStats() {
    let totalSize = 0
    const fileTypes = new Map()

    for (const file of this.files) {
      totalSize += file.size
      
      const ext = file.filename.split('.').pop()?.toLowerCase() || 'unknown'
      fileTypes.set(ext, (fileTypes.get(ext) || 0) + 1)
    }

    return {
      fileCount: this.files.length,
      totalSize,
      fileTypes: Object.fromEntries(fileTypes),
      averageFileSize: this.files.length > 0 ? Math.round(totalSize / this.files.length) : 0
    }
  }

  /**
   * 清理文件列表
   */
  clear() {
    this.files = []
  }
}

export default SpiffsGenerator
