// src/api/request.js — 集成日志拦截器
import axios from 'axios'
import { getToken, removeToken } from '../utils/auth'
import { setupApiLogger } from '../utils/logger'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

// ★ 注册日志拦截器
setupApiLogger(service)

// Token 拦截器
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截：401 自动跳登录
service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      removeToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service
