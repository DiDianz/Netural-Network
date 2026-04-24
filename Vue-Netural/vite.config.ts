// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 只代理这些具体的后端 API 路径（精确匹配，避免拦截前端路由）
const PROXY_ROUTES = [
  '/auth/login', '/auth/logout',
  '/system/user', '/system/role', '/system/menu', '/system/config',
  '/predict', '/model', '/upload', '/plc', '/instance', '/dryer',
  '/feature', '/log', '/ws', '/health',
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
    proxy: Object.fromEntries(
      PROXY_ROUTES.map(route => [route, {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }])
    )
  }
})
