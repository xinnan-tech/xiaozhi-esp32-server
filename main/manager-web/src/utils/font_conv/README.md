# Font Converter - 浏览器端字体转换器

这是基于 lv_font_conv 核心逻辑的浏览器端字体转换器，支持将 TTF/WOFF 字体文件转换为 LVGL 兼容的 CBIN 格式。

## 📁 模块结构

```
font_conv/
├── AppError.js              # 错误处理类
├── Ranger.js                # 字符范围管理器
├── Utils.js                 # 工具函数集合
├── FreeType.js              # FreeType 接口（ES6版本）
├── CollectFontData.js       # 字体数据收集核心模块
├── BrowserFontConverter.js  # 主要的转换器接口
├── TestConverter.js         # 测试模块
├── freetype_build/          # WebAssembly FreeType 模块
└── writers/
    ├── CBinWriter.js        # CBIN 格式写入器
    └── CBinFont.js          # CBIN 字体类
```

## 🚀 使用方法

### 基本使用

```javascript
import browserFontConverter from './font_conv/BrowserFontConverter.js'

// 初始化转换器
await browserFontConverter.initialize()

// 转换字体
const result = await browserFontConverter.convertToCBIN({
  fontFile: fontFile,          // File 对象
  fontName: 'my_font',
  fontSize: 20,
  bpp: 4,
  charset: 'deepseek',
  progressCallback: (progress, message) => {
    console.log(`${progress}% - ${message}`)
  }
})

// result 是 ArrayBuffer，包含 CBIN 格式的字体数据
```

### 获取字体信息

```javascript
const fontInfo = await browserFontConverter.getFontInfo(fontFile)
console.log('字体信息:', fontInfo)
/*
{
  familyName: "Arial",
  fullName: "Arial Regular", 
  postScriptName: "ArialMT",
  version: "1.0",
  unitsPerEm: 2048,
  ascender: 1854,
  descender: -434,
  numGlyphs: 3200,
  supported: true
}
*/
```

### 大小估算

```javascript
const estimate = browserFontConverter.estimateSize({
  fontSize: 20,
  bpp: 4,
  charset: 'deepseek'
})

console.log('估算结果:', estimate)
/*
{
  characterCount: 7405,
  avgBytesPerChar: 65,
  estimatedSize: 481325,
  formattedSize: "470 KB"
}
*/
```

## ⚙️ 配置选项

### 转换参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fontFile` | File/ArrayBuffer | - | 字体文件 |
| `fontName` | string | 'font' | 输出字体名称 |
| `fontSize` | number | 20 | 字号 (8-80) |
| `bpp` | number | 4 | 位深度 (1,2,4,8) |
| `charset` | string | 'basic' | 预设字符集 |
| `symbols` | string | '' | 自定义字符 |
| `range` | string | '' | Unicode 范围 |
| `compression` | boolean | true | 启用压缩 |
| `lcd` | boolean | false | 水平亚像素渲染 |
| `lcd_v` | boolean | false | 垂直亚像素渲染 |

### 支持的字符集

- `basic`: 基础 ASCII 字符集（95个字符）
- `deepseek`: DeepSeek R1 常用汉字（7405个字符）
- `gb2312`: GB2312 汉字集（7445个字符）

### 支持的字体格式

- TTF (TrueType Font)
- WOFF (Web Open Font Format)
- WOFF2 (Web Open Font Format 2.0)
- OTF (OpenType Font)

## 🔧 技术实现

### 核心依赖

1. **opentype.js**: 用于解析字体文件结构
2. **WebAssembly FreeType**: 用于字体渲染和字形生成
3. **自定义 CBIN 写入器**: 生成 LVGL 兼容格式

### 转换流程

1. **字体解析**: 使用 opentype.js 解析字体文件
2. **字形渲染**: 通过 FreeType WebAssembly 渲染字形
3. **数据收集**: 收集字形数据、度量信息、字距调整
4. **格式转换**: 将数据转换为 CBIN 格式
5. **输出生成**: 生成最终的二进制文件

### 与原版的区别

| 特性 | 原版 lv_font_conv | 浏览器版本 |
|------|-------------------|------------|
| 运行环境 | Node.js | 浏览器 |
| 模块系统 | CommonJS | ES6 Modules |
| 文件系统 | fs 模块 | File API |
| 缓冲区 | Buffer | ArrayBuffer/Uint8Array |
| 命令行 | CLI 接口 | JavaScript API |

## 🧪 测试

```javascript
import { testFontConverter, testWithSampleFont } from './font_conv/TestConverter.js'

// 基础功能测试
await testFontConverter()

// 字体文件测试
const result = await testWithSampleFont(fontFile)
console.log('测试结果:', result)
```

## ⚠️ 注意事项

1. **WebAssembly 支持**: 需要浏览器支持 WebAssembly
2. **内存限制**: 大字体文件可能消耗较多内存
3. **处理时间**: 复杂字体和大字符集转换需要较长时间
4. **文件大小**: ft_render.wasm 文件较大 (~2MB)
5. **兼容性**: 需要现代浏览器支持

## 📊 性能指标

| 字符集大小 | 字号 | BPP | 预计转换时间 | 输出大小 |
|------------|------|-----|-------------|----------|
| 100 字符 | 16px | 4 | < 1秒 | ~10KB |
| 1000 字符 | 20px | 4 | 2-5秒 | ~100KB |
| 7000 字符 | 20px | 4 | 10-30秒 | ~500KB |

## 🐛 已知问题

1. **字体验证**: 部分损坏的字体文件可能导致崩溃
2. **内存管理**: 长时间使用可能导致内存泄漏
3. **错误处理**: WebAssembly 错误难以调试
4. **字符集**: 某些特殊字符可能无法正确渲染

## 🔮 未来改进

- [ ] 支持更多字体格式
- [ ] 优化内存使用
- [ ] 增加字体预览功能
- [ ] 支持字体子集化
- [ ] 添加更多压缩选项
- [ ] 支持彩色字体

---

*基于 lv_font_conv 项目改编，适配浏览器环境*
