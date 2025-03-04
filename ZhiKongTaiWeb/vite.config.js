import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    server: {
        open: true, // 自动启动浏览器
        host: "0.0.0.0", // localhost
        port: 8002, // 端口号
        https: false,
        hmr: {overlay: false},
        proxy: {
            "^/(api)": {
                target: "http://127.0.0.1:8002",
                changeOrigin: true
            }
        }
    },
    base: '/'
})
