// src/api/log.js
import request from './request'

// 查询操作日志
export function getLogList(params) {
  return request.get('/log/list', { params })
}

// 获取所有模块名（用于筛选）
export function getLogModules() {
  return request.get('/log/modules')
}

// 清理旧日志
export function clearLogs(days) {
  return request.delete('/log/clear', { params: { days } })
}

// 前端主动上报操作日志
export function recordLog(data) {
  return request.post('/log/record', null, { params: data })
}
