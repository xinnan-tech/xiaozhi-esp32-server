const { defineConfig } = require('@vue/cli-service');
const dotenv = require('dotenv');

// 确保加载 .env 文件
dotenv.config();

module.exports = defineConfig({
    devServer: {
      // Bug 修复：将代理配置为环境变量中定义的 API 基础 URL
      port: 8001, // 指定端口为 8001
      proxy: {
        '/xiaozhi-esp32-api': {
          target: process.env.VUE_APP_API_BASE_URL || 'http://localhost:8002', // 后端 API 的基础 URL
          changeOrigin: true, // 允许跨域
          // pathRewrite: {
          //   '^/api': '', // 路径重写
          // },
        },
        },
        client: {
          overlay: false,
        },
      },
});
