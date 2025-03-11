const { defineConfig } = require('@vue/cli-service');
const dotenv = require('dotenv');

dotenv.config();

module.exports = defineConfig({
    devServer: {
      // Bug 修复：将代理配置为环境变量中定义的 API 基础 URL
      proxy: process.env.VUE_APP_API_BASE_URL,
      client: {
        overlay: false,
      },
    }
})
