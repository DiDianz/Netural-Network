// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 后端实际的 API 路由路径（不含前端页面路由）
const BACKEND_API_PREFIXES = [
  '/auth', '/predict', '/model', '/upload', '/plc',
  '/instance', '/dryer', '/feature', '/log', '/ws', '/health',
  // system 子路由 — 只代理真正的 API 端点
  '/system/user/', '/system/role/', '/system/menu/', '/system/config/',
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
    proxy: {
      // 使用函数式代理，精确区分 API 请求和前端路由
      '^/(auth|predict|model|upload|plc|instance|dryer|feature|log|ws|health)(/|$)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '^/system/(user|role|menu|config)/': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  }
})
