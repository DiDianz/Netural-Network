// src/utils/logger.js — 前端全链路日志工具
/**
 * 功能：
 * 1. Axios 请求/响应拦截器 → 自动上报 API 调用日志
 * 2. 路由守卫 → 记录页面访问
 * 3. 全局错误捕获 → 记录 JS 异常
 * 4. logAction() → 手动记录用户操作（按钮点击等）
 */
import axios from 'axios'
import { getToken } from './auth'

// 日志上报队列（批量发送，减少请求）
const logQueue = []
let flushTimer = null
const FLUSH_INTERVAL = 3000 // 3秒刷一次
const MAX_QUEUE = 20

// 获取当前用户名
function getCurrentUser() {
  try {
    const token = getToken()
    if (!token) return ''
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.sub || payload.username || ''
  } catch {
    return ''
  }
}

// 发送日志到后端
function sendLog(logData) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  const token = getToken()

  // 用 navigator.sendBeacon 优先（不阻塞页面关闭）
  const url = `${baseURL}/log/record?log_type=${encodeURIComponent(logData.log_type || 'frontend')}` +
    `&user_name=${encodeURIComponent(logData.user_name || '')}` +
    `&module=${encodeURIComponent(logData.module || '')}` +
    `&action=${encodeURIComponent(logData.action || '')}` +
    `&method=${encodeURIComponent(logData.method || '')}` +
    `&url=${encodeURIComponent(logData.url || '')}` +
    `&params=${encodeURIComponent((logData.params || '').slice(0, 2000))}` +
    `&status=${logData.status || 200}` +
    `&error_msg=${encodeURIComponent((logData.error_msg || '').slice(0, 2000))}` +
    `&result=${encodeURIComponent(logData.result || '')}` +
    `&cost_ms=${logData.cost_ms || 0}`

  if (navigator.sendBeacon) {
    navigator.sendBeacon(url)
  } else {
    // fallback: 加入队列批量发送
    logQueue.push(logData)
    if (logQueue.length >= MAX_QUEUE) {
      flushQueue()
    } else if (!flushTimer) {
      flushTimer = setTimeout(flushQueue, FLUSH_INTERVAL)
    }
  }
}

// 批量发送队列中的日志
async function flushQueue() {
  if (flushTimer) {
    clearTimeout(flushTimer)
    flushTimer = null
  }
  if (logQueue.length === 0) return

  const batch = logQueue.splice(0, MAX_QUEUE)
  try {
    const baseURL = import.meta.env.VITE_API_BASE_URL || ''
    const token = getToken()
    await axios.post(`${baseURL}/log/batch-record`, batch, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      timeout: 5000,
    })
  } catch {
    // 发送失败就丢弃，不阻塞用户
  }
}

// ========== 1. Axios 拦截器（自动记录 API 调用） ==========
export function setupApiLogger(axiosInstance) {
  // 请求拦截：记录开始时间
  axiosInstance.interceptors.request.use(
    (config) => {
      config._logStartTime = Date.now()
      config._logUrl = config.url || ''
      return config
    },
    (error) => {
      // 请求构造失败
      sendLog({
        log_type: 'frontend',
        user_name: getCurrentUser(),
        module: 'API请求',
        action: '请求构造失败',
        method: error.config?.method?.toUpperCase() || '',
        url: error.config?.url || '',
        status: 0,
        error_msg: error.message,
        result: '失败',
      })
      return Promise.reject(error)
    }
  )

  // 响应拦截：记录结果
  axiosInstance.interceptors.response.use(
    (response) => {
      const costMs = Date.now() - (response.config._logStartTime || Date.now())
      // 只记录非健康检查的日志
      const url = response.config.url || ''
      if (!url.includes('/health')) {
        sendLog({
          log_type: 'frontend',
          user_name: getCurrentUser(),
          module: guessModule(url),
          action: `API-${response.config.method?.toUpperCase() || 'GET'}`,
          method: response.config.method?.toUpperCase() || 'GET',
          url: url,
          params: getParamsStr(response.config),
          status: response.status,
          result: '成功',
          cost_ms: costMs,
        })
      }
      return response
    },
    (error) => {
      const config = error.config || {}
      const costMs = Date.now() - (config._logStartTime || Date.now())
      const status = error.response?.status || 0
      const errorMsg = error.response?.data?.detail || error.message || '未知错误'

      sendLog({
        log_type: 'frontend',
        user_name: getCurrentUser(),
        module: guessModule(config.url || ''),
        action: `API-${config.method?.toUpperCase() || 'GET'}失败`,
        method: config.method?.toUpperCase() || 'GET',
        url: config.url || '',
        params: getParamsStr(config),
        status: status,
        error_msg: errorMsg,
        result: '失败',
        cost_ms: costMs,
      })
      return Promise.reject(error)
    }
  )
}

// ========== 2. 路由守卫（记录页面访问） ==========
export function setupRouterLogger(router) {
  router.afterEach((to, from) => {
    // 跳过登录页和 404
    if (to.path === '/login' || to.path === '/404') return

    sendLog({
      log_type: 'frontend',
      user_name: getCurrentUser(),
      module: '页面访问',
      action: `访问-${to.meta?.title || to.path}`,
      method: 'NAVIGATE',
      url: to.fullPath,
      params: JSON.stringify({ from: from.path }),
      status: 200,
      result: '成功',
    })
  })
}

// ========== 3. 全局错误捕获 ==========
export function setupErrorLogger(app) {
  // Vue 组件错误
  app.config.errorHandler = (err, instance, info) => {
    sendLog({
      log_type: 'error',
      user_name: getCurrentUser(),
      module: 'Vue组件',
      action: '组件错误',
      status: 500,
      error_msg: `${err.message}\ninfo: ${info}\ncomponent: ${instance?.$options?.name || 'unknown'}`,
      result: '错误',
    })
  }

  // 全局 JS 错误
  window.addEventListener('error', (event) => {
    sendLog({
      log_type: 'error',
      user_name: getCurrentUser(),
      module: 'JavaScript',
      action: 'JS运行时错误',
      status: 500,
      error_msg: `${event.message}\nat ${event.filename}:${event.lineno}:${event.colno}`,
      result: '错误',
    })
  })

  // Promise 未捕获异常
  window.addEventListener('unhandledrejection', (event) => {
    sendLog({
      log_type: 'error',
      user_name: getCurrentUser(),
      module: 'Promise',
      action: '未捕获Promise异常',
      status: 500,
      error_msg: String(event.reason || 'unknown'),
      result: '错误',
    })
  })
}

// ========== 4. 手动操作记录 ==========
/**
 * 在任何用户交互处调用：
 *   logAction('用户管理', '点击新增按钮')
 *   logAction('预测', '启动实时预测', { model_key: 'lstm' })
 */
export function logAction(module, action, params = null) {
  sendLog({
    log_type: 'frontend',
    user_name: getCurrentUser(),
    module: module,
    action: action,
    method: 'CLICK',
    url: window.location.pathname,
    params: params ? JSON.stringify(params) : '',
    status: 200,
    result: '成功',
  })
}

// ========== 工具函数 ==========
function guessModule(url) {
  const map = {
    '/auth/': '认证',
    '/user/': '用户管理',
    '/role/': '角色管理',
    '/menu/': '菜单管理',
    '/predict/': '预测',
    '/model/': '模型管理',
    '/upload/': '文件上传',
    '/plc/': 'PLC管理',
    '/instance/': '预测实例',
    '/dryer/': '烘丝机预测',
    '/feature/': '特征方案',
    '/log/': '操作日志',
    '/system/config': '系统设置',
  }
  for (const [prefix, name] of Object.entries(map)) {
    if (url.includes(prefix)) return name
  }
  return '其他'
}

function getParamsStr(config) {
  try {
    if (config.params) return JSON.stringify(config.params).slice(0, 2000)
    if (config.data) {
      if (typeof config.data === 'string') return config.data.slice(0, 2000)
      return JSON.stringify(config.data).slice(0, 2000)
    }
  } catch {}
  return ''
}
