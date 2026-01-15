/**
 * StorageHelper 工具类
 * 为各个组件提供便捷的文件存储功能
 */

import configStorage from './ConfigStorage.js'

class StorageHelper {
  /**
   * 为字体文件提供自动保存功能
   * @param {File} file - 字体文件
   * @param {Object} config - 字体配置
   * @returns {Promise<void>}
   */
  static async saveFontFile(file, config = {}) {
    if (file) {
      const key = 'custom_font'
      try {
        await configStorage.saveFile(key, file, 'font', {
          size: config.size || 20,
          bpp: config.bpp || 4,
          charset: config.charset || 'deepseek'
        })
        console.log(`字体文件已保存: ${file.name}`)
      } catch (error) {
        console.warn(`保存字体文件失败: ${file.name}`, error)
      }
    }
  }

  /**
   * 为表情文件提供自动保存功能
   * @param {string} emojiName - 表情名称或文件hash（如果以hash_开头）
   * @param {File} file - 表情文件
   * @param {Object} config - 表情配置
   * @returns {Promise<void>}
   */
  static async saveEmojiFile(emojiName, file, config = {}) {
    if (file && emojiName) {
      // 如果 emojiName 已经以 hash_ 开头（新的去重结构），直接使用
      // 否则添加 emoji_ 前缀（旧的结构，向后兼容）
      const key = emojiName.startsWith('hash_') ? emojiName : `emoji_${emojiName}`
      
      try {
        const width = config?.size?.width ?? 64
        const height = config?.size?.height ?? 64

        // 传入可克隆的普通对象，避免 Vue Proxy
        await configStorage.saveFile(key, file, 'emoji', {
          name: emojiName,
          size: { width, height },
          format: config?.format,
          emotions: config?.emotions  // 新增：记录使用该文件的表情列表
        })
        console.log(`表情文件已保存: ${key} - ${file.name}`)
      } catch (error) {
        console.warn(`保存表情文件失败: ${emojiName}`, error)
      }
    }
  }

  /**
   * 为背景文件提供自动保存功能
   * @param {string} mode - 模式 ('light' 或 'dark')
   * @param {File} file - 背景文件
   * @param {Object} config - 背景配置
   * @returns {Promise<void>}
   */
  static async saveBackgroundFile(mode, file, config = {}) {
    if (file && mode) {
      const key = `background_${mode}`
      try {
        let safeConfig = {}
        try {
          safeConfig = config ? JSON.parse(JSON.stringify(config)) : {}
        } catch (e) {
          safeConfig = { ...config }
        }

        await configStorage.saveFile(key, file, 'background', {
          mode,
          ...safeConfig
        })
        console.log(`背景文件已保存: ${mode} - ${file.name}`)
      } catch (error) {
        console.warn(`保存背景文件失败: ${mode}`, error)
      }
    }
  }

  /**
   * 恢复字体文件
   * @returns {Promise<File|null>}
   */
  static async restoreFontFile() {
    try {
      return await configStorage.loadFile('custom_font')
    } catch (error) {
      console.warn('恢复字体文件失败:', error)
      return null
    }
  }

  /**
   * 恢复表情文件
   * @param {string} emojiName - 表情名称或文件hash（如果以hash_开头）
   * @returns {Promise<File|null>}
   */
  static async restoreEmojiFile(emojiName) {
    if (!emojiName) return null

    try {
      // 如果 emojiName 已经以 hash_ 开头（新的去重结构），直接使用
      // 否则添加 emoji_ 前缀（旧的结构，向后兼容）
      const key = emojiName.startsWith('hash_') ? emojiName : `emoji_${emojiName}`
      return await configStorage.loadFile(key)
    } catch (error) {
      console.warn(`恢复表情文件失败: ${emojiName}`, error)
      return null
    }
  }

  /**
   * 恢复背景文件
   * @param {string} mode - 模式 ('light' 或 'dark')
   * @returns {Promise<File|null>}
   */
  static async restoreBackgroundFile(mode) {
    if (!mode) return null

    try {
      const key = `background_${mode}`
      return await configStorage.loadFile(key)
    } catch (error) {
      console.warn(`恢复背景文件失败: ${mode}`, error)
      return null
    }
  }

  /**
   * 删除字体文件
   * @returns {Promise<void>}
   */
  static async deleteFontFile() {
    try {
      await configStorage.deleteFile('custom_font')
      console.log('字体文件已删除')
    } catch (error) {
      console.warn('删除字体文件失败:', error)
    }
  }

  /**
   * 删除表情文件
   * @param {string} emojiName - 表情名称或文件hash（如果以hash_开头）
   * @returns {Promise<void>}
   */
  static async deleteEmojiFile(emojiName) {
    if (!emojiName) return

    try {
      // 如果 emojiName 已经以 hash_ 开头（新的去重结构），直接使用
      // 否则添加 emoji_ 前缀（旧的结构，向后兼容）
      const key = emojiName.startsWith('hash_') ? emojiName : `emoji_${emojiName}`
      await configStorage.deleteFile(key)
      console.log(`表情文件已删除: ${key}`)
    } catch (error) {
      console.warn(`删除表情文件失败: ${emojiName}`, error)
    }
  }

  /**
   * 删除背景文件
   * @param {string} mode - 模式 ('light' 或 'dark')
   * @returns {Promise<void>}
   */
  static async deleteBackgroundFile(mode) {
    if (!mode) return

    try {
      const key = `background_${mode}`
      await configStorage.deleteFile(key)
      console.log(`背景文件已删除: ${mode}`)
    } catch (error) {
      console.warn(`删除背景文件失败: ${mode}`, error)
    }
  }

  /**
   * 获取文件存储信息
   * @returns {Promise<Object>}
   */
  static async getStorageInfo() {
    try {
      return await configStorage.getStorageInfo()
    } catch (error) {
      console.warn('获取存储信息失败:', error)
      return {
        configs: { count: 0 },
        files: { count: 0 },
        temp_data: { count: 0 },
        lastSaved: null
      }
    }
  }

  /**
   * 清理所有文件存储
   * @returns {Promise<void>}
   */
  static async clearAllFiles() {
    try {
      await configStorage.clearAll()
      console.log('所有存储文件已清理')
    } catch (error) {
      console.warn('清理存储文件失败:', error)
      throw error
    }
  }
}

export default StorageHelper
