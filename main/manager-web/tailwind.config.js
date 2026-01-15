/** @type {import('tailwindcss').Config} */

module.exports = {
  // 配置需要扫描的文件路径（Tailwind 会检测这些文件中使用的工具类，用于生产环境 Tree-shaking）
  content: [
    "./src/**/*.html", // HTML 文件
    "./src/**/*.vue", // Vue 组件
    "./src/**/*.jsx", // React 组件
    "./src/**/*.tsx", // TypeScript + React 组件
    "./src/**/*.js", // JavaScript 文件（若有动态类名）
    "./src/**/*.ts" // TypeScript 文件
  ],
  // 主题配置（可扩展颜色、字体、间距等）
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8'
        },
        orange: {
          50: '#fff7ed',
          200: '#fed7aa',
          800: '#9a3412'
        }
      }
    },
  },
  // 插件（可添加官方或第三方插件）
  plugins: [
    // 示例：添加表单插件
    // require('@tailwindcss/forms'),
  ],
  // 暗色模式配置（可选）
  darkMode: "class" // 或 'media'（根据系统暗色模式自动切换）
};