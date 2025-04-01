module.exports = {
    presets: [
      ['@vue/cli-plugin-babel/preset', {
        useBuiltIns: 'usage',
        corejs: 3
      }]
    ],
    plugins: [
        '@babel/plugin-syntax-dynamic-import',  // 确保支持动态导入 (Lazy Loading)
        '@babel/plugin-transform-runtime' 
      ]
  }
  