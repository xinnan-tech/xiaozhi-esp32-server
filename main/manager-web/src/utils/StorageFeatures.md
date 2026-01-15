# 配置持久化存储功能说明

## 功能概述

本项目新增了基于 IndexedDB 的配置和文件持久化存储功能，让用户在刷新页面后仍能保持之前的配置状态和上传的文件。

## 主要特性

### 1. 自动配置保存
- **实时保存**：用户修改配置时自动保存到 IndexedDB
- **智能检测**：页面加载时自动检测是否有已保存的配置
- **状态恢复**：恢复用户的进度位置和主题标签状态

### 2. 文件自动存储
- **字体文件**：自定义字体文件自动保存，包含转换后的字体数据
- **表情图片**：自定义表情图片自动保存到存储
- **背景图片**：浅色/深色模式背景图片自动保存

### 3. 重新开始功能
- **一键清理**：提供重新开始按钮，确认后清空所有存储数据
- **安全确认**：包含详细的确认对话框，防止误操作
- **完整重置**：清理配置、文件和临时数据

## 技术实现

### 核心组件

#### ConfigStorage.js
- IndexedDB 数据库管理
- 配置存储与恢复
- 文件二进制存储
- 临时数据管理

#### StorageHelper.js
- 为各组件提供便捷的存储 API
- 统一的文件保存和删除接口
- 分类管理不同类型的资源文件

#### AssetsBuilder.js 集成
- 与存储系统深度集成
- 自动保存转换后的字体数据
- 资源文件智能恢复

### 存储结构

```javascript
// 数据库：XiaozhiConfigDB
{
  configs: {      // 配置表
    key: 'current_config',
    config: { ... },           // 完整配置对象
    currentStep: 1,           // 当前步骤
    activeThemeTab: 'font',   // 活跃标签
    timestamp: 1234567890     // 保存时间
  },
  
  files: {        // 文件表
    id: 'custom_font',
    type: 'font',             // 文件类型
    name: 'MyFont.ttf',       // 文件名
    size: 1024,               // 文件大小
    mimeType: 'font/ttf',     // MIME类型
    data: ArrayBuffer,        // 文件二进制数据
    metadata: { ... },        // 元数据
    timestamp: 1234567890     // 保存时间
  },
  
  temp_data: {    // 临时数据表
    key: 'converted_font_xxx',
    type: 'converted_font',   // 数据类型
    data: ArrayBuffer,        // 转换后数据
    metadata: { ... },        // 元数据
    timestamp: 1234567890     // 保存时间
  }
}
```

## 用户体验

### 首次使用
1. 用户正常配置芯片、主题等
2. 每次修改自动保存到本地存储
3. 上传的文件同步保存

### 刷新页面后
1. 显示"检测到已保存的配置"提示
2. 自动恢复到上次的配置状态
3. 恢复上传的文件和转换数据
4. 提供"重新开始"选项

### 重新开始
1. 点击"重新开始"按钮
2. 显示详细的确认对话框
3. 列出将要清除的数据类型
4. 确认后完整重置到初始状态

## API 参考

### ConfigStorage 主要方法

```javascript
// 保存配置
await configStorage.saveConfig(config, currentStep, activeThemeTab)

// 加载配置
const data = await configStorage.loadConfig()

// 保存文件
await configStorage.saveFile(id, file, type, metadata)

// 加载文件
const file = await configStorage.loadFile(id)

// 清空所有数据
await configStorage.clearAll()
```

### StorageHelper 便捷方法

```javascript
// 保存字体文件
await StorageHelper.saveFontFile(file, config)

// 保存表情文件
await StorageHelper.saveEmojiFile(emojiName, file, config)

// 保存背景文件
await StorageHelper.saveBackgroundFile(mode, file, config)

// 删除文件
await StorageHelper.deleteFontFile()
await StorageHelper.deleteEmojiFile(emojiName)
await StorageHelper.deleteBackgroundFile(mode)
```

## 注意事项

### 浏览器兼容性
- 需要支持 IndexedDB 的现代浏览器
- 建议使用 Chrome 58+, Firefox 55+, Safari 10.1+

### 存储限制
- IndexedDB 存储空间受浏览器限制
- 大文件可能影响存储性能
- 建议定期清理不需要的数据

### 隐私考虑
- 数据仅存储在用户本地浏览器
- 不会上传到服务器
- 清除浏览器数据会丢失存储的配置

## 故障排除

### 存储失败
- 检查浏览器是否支持 IndexedDB
- 确认浏览器存储空间充足
- 检查是否启用了私密浏览模式

### 配置丢失
- 清除浏览器数据会导致配置丢失
- 浏览器升级可能影响存储兼容性
- 建议重要配置手动备份

### 性能问题
- 大量文件存储可能影响性能
- 定期使用"重新开始"功能清理数据
- 避免频繁的大文件上传操作
