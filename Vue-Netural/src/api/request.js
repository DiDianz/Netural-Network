// src/api/request.js
import axios from 'axios'
import { getToken, removeToken } from '../utils/auth'

const request = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

// 请求拦截器 — 自动携带 Token
request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && error.response.status === 401) {
      removeToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default request
