import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  define: {
    __UNI_PLATFORM__: JSON.stringify('h5'),
    __VITE_APP_PROXY__: JSON.stringify(false),
  },
  resolve: {
    alias: {
      '@/': `${path.resolve(__dirname, 'src')}/`,
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
  },
})