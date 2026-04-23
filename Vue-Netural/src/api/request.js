// src/api/request.js
import axios from 'axios'
import { getToken, removeToken } from '../utils/auth'

const request = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

// 不需要记录日志的路径
const SKIP_LOG_PATHS = [
  '/log/record', '/log/list', '/log/modules',
  '/predict/stream', '/predict/plc-stream', '/predict/multi-stream',
  '/model/train/stream', '/model/train/upload/stream',
  '/instance/stream', '/plc/read/stream', '/dryer/train', '/dryer/plc-stream',
  '/health',
]

// URL → 模块名映射
const MODULE_MAP = {
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
  '/system/': '系统设置',
}

function getModuleName(url) {
  for (const prefix in MODULE_MAP) {
    if (url.includes(prefix)) return MODULE_MAP[prefix]
  }
  return '其他'
}

function getActionName(method, url) {
  const map = { GET: '查询', POST: '新增', PUT: '修改', DELETE: '删除' }
  const base = map[method] || method
  const parts = url.replace(/\?.*$/, '').split('/').filter(Boolean)
  if (parts.length > 0) {
    const last = parts[parts.length - 1]
    if (last && last !== 'v1' && last !== 'api') return `${base}-${last}`
  }
  return base
}

// 获取用户名
function getUserName() {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      return user.nick_name || user.user_name || ''
    }
  } catch {}
  return ''
}

// 异步上报日志（不阻塞请求）
function reportLog(data) {
  try {
    const token = getToken()
    if (!token) return
    const params = new URLSearchParams()
    for (const key in data) {
      params.set(key, String(data[key] ?? ''))
    }
    fetch(`${request.defaults.baseURL}/log/record?${params.toString()}`, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token },
    }).catch(() => {})
  } catch {}
}

// 请求拦截器 — 自动携带 Token
request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    config._startTime = Date.now()
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const config = response.config
    const costMs = Date.now() - (config._startTime || Date.now())
    const path = config.url || ''

    // 跳过不需要记录的路径
    const shouldSkip = SKIP_LOG_PATHS.some(p => path.startsWith(p))
    const method = (config.method || 'get').toUpperCase()

    // 记录写操作（POST/PUT/DELETE）和慢请求（>3s）
    if (!shouldSkip && (['POST', 'PUT', 'DELETE'].includes(method) || costMs > 3000)) {
      reportLog({
        user_name: getUserName(),
        module: getModuleName(path),
        action: getActionName(method, path),
        method: method,
        url: path,
        params: '',
        status: 200,
        result: '成功',
        cost_ms: costMs,
      })
    }

    return response.data
  },
  (error) => {
    const config = error.config || {}
    const costMs = Date.now() - (config._startTime || Date.now())
    const path = config.url || ''
    const method = (config.method || 'get').toUpperCase()
    const status = error.response ? error.response.status : 0
    const detail = error.response && error.response.data
      ? (error.response.data.detail || JSON.stringify(error.response.data))
      : error.message

    // 所有错误都记录
    if (!SKIP_LOG_PATHS.some(p => path.startsWith(p))) {
      reportLog({
        user_name: getUserName(),
        module: getModuleName(path),
        action: getActionName(method, path),
        method: method,
        url: path,
        params: '',
        status: status,
        error_msg: String(detail || '').substring(0, 500),
        result: '失败',
        cost_ms: costMs,
      })
    }

    if (error.response && error.response.status === 401) {
      removeToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
