// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 后端 API 路由前缀
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
    proxy: {
      // 匹配所有可能的 API 前缀
      ...Object.fromEntries(API_PREFIXES.map(prefix => [prefix, {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // bypass: 如果是浏览器页面导航（Accept 包含 text/html），不代理，让 Vite SPA fallback 处理
        bypass(req) {
          const accept = req.headers.accept || ''
          // 浏览器页面请求会带 text/html，API 请求不会
          if (accept.includes('text/html') && !accept.includes('application/json')) {
            return req.url  // 返回原始 URL = 不代理，走 Vite SPA fallback
          }
        },
      }])),
    }
  }
})
