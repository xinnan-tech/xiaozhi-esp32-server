/**
 * ConfigStorage 类
 * 用于管理配置和文件的 IndexedDB 存储
 * 
 * 主要功能：
 * - 存储和恢复用户配置
 * - 存储和恢复用户上传的文件
 * - 提供清空配置的功能
 */

class ConfigStorage {
  constructor() {
    this.dbName = 'XiaozhiConfigDB'
    this.version = 1
    this.db = null
    this.initialized = false
  }

  /**
   * 初始化 IndexedDB
   * @returns {Promise<void>}
   */
  async initialize() {
    if (this.initialized && this.db) {
      return
    }

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version)

      request.onerror = () => {
        console.error('IndexedDB 初始化失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        this.initialized = true
        console.log('IndexedDB 初始化成功')
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = event.target.result

        // 创建配置存储表
        if (!db.objectStoreNames.contains('configs')) {
          const configStore = db.createObjectStore('configs', { keyPath: 'key' })
          configStore.createIndex('timestamp', 'timestamp', { unique: false })
        }

        // 创建文件存储表
        if (!db.objectStoreNames.contains('files')) {
          const fileStore = db.createObjectStore('files', { keyPath: 'id' })
          fileStore.createIndex('type', 'type', { unique: false })
          fileStore.createIndex('timestamp', 'timestamp', { unique: false })
        }

        // 创建临时存储表（用于转换后的字体等）
        if (!db.objectStoreNames.contains('temp_data')) {
          const tempStore = db.createObjectStore('temp_data', { keyPath: 'key' })
          tempStore.createIndex('type', 'type', { unique: false })
          tempStore.createIndex('timestamp', 'timestamp', { unique: false })
        }

        console.log('IndexedDB 表结构创建完成')
      }
    })
  }

  /**
   * 保存配置到 IndexedDB
   * @param {Object} config - 完整的配置对象
   * @param {number} currentStep - 当前步骤
   * @param {string} activeThemeTab - 活动的主题标签
   * @returns {Promise<void>}
   */
  async saveConfig(config, currentStep = 0, activeThemeTab = 'wakeword') {
    if (!this.initialized) {
      await this.initialize()
    }

    const sanitizedConfig = this.sanitizeConfigForStorage(config)

    const configData = {
      key: 'current_config',
      config: sanitizedConfig, // 深拷贝并剔除不可序列化字段
      currentStep,
      activeThemeTab,
      timestamp: Date.now()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['configs'], 'readwrite')
      const store = transaction.objectStore('configs')
      const request = store.put(configData)

      request.onerror = () => {
        console.error('保存配置失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        console.log('配置已保存到 IndexedDB')
        resolve()
      }
    })
  }

  /**
   * 生成可安全存储的配置对象
   * - File/Blob 等不可序列化字段统一置为 null
   * - 保留 images 的键，以便后续按键名从存储恢复
   */
  sanitizeConfigForStorage(config) {
    const cloned = JSON.parse(JSON.stringify(config || {}))

    try {
      // 字体文件
      if (cloned?.theme?.font?.type === 'custom') {
        if (!cloned.theme.font.custom) cloned.theme.font.custom = {}
        cloned.theme.font.custom.file = null
      }

      // 表情图片
      if (cloned?.theme?.emoji?.type === 'custom') {
        const images = cloned.theme.emoji?.custom?.images || {}
        const sanitizedImages = {}
        Object.keys(images).forEach((k) => {
          // 无论反序列化为何形态，都统一置为 null，表示待恢复
          sanitizedImages[k] = null
        })
        if (!cloned.theme.emoji.custom) cloned.theme.emoji.custom = {}
        cloned.theme.emoji.custom.images = sanitizedImages
      }

      // 背景图片
      if (cloned?.theme?.skin?.light) {
        cloned.theme.skin.light.backgroundImage = null
      }
      if (cloned?.theme?.skin?.dark) {
        cloned.theme.skin.dark.backgroundImage = null
      }
    } catch (e) {
      // 忽略清理异常，返回已克隆对象
    }

    return cloned
  }

  /**
   * 从 IndexedDB 恢复配置
   * @returns {Promise<Object|null>} 配置数据或null
   */
  async loadConfig() {
    if (!this.initialized) {
      await this.initialize()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['configs'], 'readonly')
      const store = transaction.objectStore('configs')
      const request = store.get('current_config')

      request.onerror = () => {
        console.error('加载配置失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        const result = request.result
        if (result) {
          console.log('从 IndexedDB 恢复配置成功')
          resolve({
            config: result.config,
            currentStep: result.currentStep || 0,
            activeThemeTab: result.activeThemeTab || 'wakeword',
            timestamp: result.timestamp
          })
        } else {
          resolve(null)
        }
      }
    })
  }

  /**
   * 保存文件到 IndexedDB
   * @param {string} id - 文件ID
   * @param {File} file - 文件对象
   * @param {string} type - 文件类型 (font, emoji, background)
   * @param {Object} metadata - 额外的元数据
   * @returns {Promise<void>}
   */
  async saveFile(id, file, type, metadata = {}) {
    if (!this.initialized) {
      await this.initialize()
    }

    // 将文件转换为 ArrayBuffer 以便存储
    const arrayBuffer = await this.fileToArrayBuffer(file)

    // 确保 metadata 可被结构化克隆（去除 Proxy/Ref/循环等）
    let safeMetadata = {}
    try {
      safeMetadata = metadata ? JSON.parse(JSON.stringify(metadata)) : {}
    } catch (e) {
      // 回退为浅拷贝的纯对象
      safeMetadata = { ...metadata }
    }

    const fileData = {
      id,
      type,
      name: file.name,
      size: file.size,
      mimeType: file.type,
      lastModified: file.lastModified,
      data: arrayBuffer,
      metadata: safeMetadata,
      timestamp: Date.now()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['files'], 'readwrite')
      const store = transaction.objectStore('files')
      const request = store.put(fileData)

      request.onerror = () => {
        console.error('保存文件失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        console.log(`文件 ${file.name} 已保存到 IndexedDB`)
        resolve()
      }
    })
  }

  /**
   * 从 IndexedDB 加载文件
   * @param {string} id - 文件ID
   * @returns {Promise<File|null>} 文件对象或null
   */
  async loadFile(id) {
    if (!this.initialized) {
      await this.initialize()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['files'], 'readonly')
      const store = transaction.objectStore('files')
      const request = store.get(id)

      request.onerror = () => {
        console.error('加载文件失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        const result = request.result
        if (result) {
          // 将 ArrayBuffer 转换回 File 对象
          const blob = new Blob([result.data], { type: result.mimeType })
          const file = new File([blob], result.name, {
            type: result.mimeType,
            lastModified: result.lastModified
          })

          // 添加额外的元数据
          file.storedId = result.id
          file.storedType = result.type
          file.storedMetadata = result.metadata
          file.storedTimestamp = result.timestamp

          console.log(`文件 ${result.name} 从 IndexedDB 恢复成功`)
          resolve(file)
        } else {
          resolve(null)
        }
      }
    })
  }

  /**
   * 获取指定类型的所有文件
   * @param {string} type - 文件类型
   * @returns {Promise<Array>} 文件列表
   */
  async getFilesByType(type) {
    if (!this.initialized) {
      await this.initialize()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['files'], 'readonly')
      const store = transaction.objectStore('files')
      const index = store.index('type')
      const request = index.getAll(type)

      request.onerror = () => {
        console.error('获取文件列表失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        const results = request.result || []
        const files = results.map(result => {
          const blob = new Blob([result.data], { type: result.mimeType })
          const file = new File([blob], result.name, {
            type: result.mimeType,
            lastModified: result.lastModified
          })

          file.storedId = result.id
          file.storedType = result.type
          file.storedMetadata = result.metadata
          file.storedTimestamp = result.timestamp

          return file
        })

        resolve(files)
      }
    })
  }

  /**
   * 保存临时数据（如转换后的字体等）
   * @param {string} key - 数据键
   * @param {ArrayBuffer} data - 数据
   * @param {string} type - 数据类型
   * @param {Object} metadata - 元数据
   * @returns {Promise<void>}
   */
  async saveTempData(key, data, type, metadata = {}) {
    if (!this.initialized) {
      await this.initialize()
    }

    const tempData = {
      key,
      type,
      data,
      metadata,
      timestamp: Date.now()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['temp_data'], 'readwrite')
      const store = transaction.objectStore('temp_data')
      const request = store.put(tempData)

      request.onerror = () => {
        console.error('保存临时数据失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        console.log(`临时数据 ${key} 已保存`)
        resolve()
      }
    })
  }

  /**
   * 加载临时数据
   * @param {string} key - 数据键
   * @returns {Promise<Object|null>} 临时数据或null
   */
  async loadTempData(key) {
    if (!this.initialized) {
      await this.initialize()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['temp_data'], 'readonly')
      const store = transaction.objectStore('temp_data')
      const request = store.get(key)

      request.onerror = () => {
        console.error('加载临时数据失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        const result = request.result
        resolve(result || null)
      }
    })
  }

  /**
   * 清空所有存储的数据
   * @returns {Promise<void>}
   */
  async clearAll() {
    if (!this.initialized) {
      await this.initialize()
    }

    const storeNames = ['configs', 'files', 'temp_data']
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(storeNames, 'readwrite')
      let completedStores = 0
      let hasError = false

      const checkComplete = () => {
        completedStores++
        if (completedStores === storeNames.length) {
          if (hasError) {
            reject(new Error('清空部分数据时出现错误'))
          } else {
            console.log('所有存储数据已清空')
            resolve()
          }
        }
      }

      storeNames.forEach(storeName => {
        const store = transaction.objectStore(storeName)
        const request = store.clear()

        request.onerror = () => {
          console.error(`清空 ${storeName} 失败:`, request.error)
          hasError = true
          checkComplete()
        }

        request.onsuccess = () => {
          console.log(`${storeName} 已清空`)
          checkComplete()
        }
      })
    })
  }

  /**
   * 删除指定文件
   * @param {string} id - 文件ID
   * @returns {Promise<void>}
   */
  async deleteFile(id) {
    if (!this.initialized) {
      await this.initialize()
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['files'], 'readwrite')
      const store = transaction.objectStore('files')
      const request = store.delete(id)

      request.onerror = () => {
        console.error('删除文件失败:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        console.log(`文件 ${id} 已删除`)
        resolve()
      }
    })
  }

  /**
   * 获取存储使用情况
   * @returns {Promise<Object>} 存储统计信息
   */
  async getStorageInfo() {
    if (!this.initialized) {
      await this.initialize()
    }

    const storeNames = ['configs', 'files', 'temp_data']
    const info = {}

    for (const storeName of storeNames) {
      const count = await new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const request = store.count()

        request.onerror = () => reject(request.error)
        request.onsuccess = () => resolve(request.result)
      })

      info[storeName] = { count }
    }

    // 获取上次保存配置的时间
    const configData = await this.loadConfig()
    info.lastSaved = configData ? new Date(configData.timestamp) : null

    return info
  }

  /**
   * 检查是否有存储的配置
   * @returns {Promise<boolean>}
   */
  async hasStoredConfig() {
    try {
      const config = await this.loadConfig()
      return config !== null
    } catch (error) {
      console.error('检查存储配置时出错:', error)
      return false
    }
  }

  /**
   * 将文件转换为 ArrayBuffer
   * @param {File} file - 文件对象
   * @returns {Promise<ArrayBuffer>}
   */
  fileToArrayBuffer(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = () => reject(new Error('读取文件失败'))
      reader.readAsArrayBuffer(file)
    })
  }

  /**
   * 关闭数据库连接
   */
  close() {
    if (this.db) {
      this.db.close()
      this.db = null
      this.initialized = false
      console.log('IndexedDB 连接已关闭')
    }
  }
}

// 创建单例实例
const configStorage = new ConfigStorage()

export default configStorage
