// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 后端 API 路径前缀列表
const API_PREFIXES = [
  '/auth', '/system', '/predict', '/model', '/upload',
  '/plc', '/instance', '/dryer', '/feature', '/log',
  '/ws', '/health', '/menu', '/role', '/user',
]

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    host: true,
    open: false,
    // 拉取代码后自动全量刷新，避免 HMR 状态不一致
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      // 所有后端 API 路由统一代理到 8000
      ...Object.fromEntries(API_PREFIXES.map(prefix => [prefix, {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }])),
    }
  }
})
