// src/api/log.js — 日志 API（增强版，新增 stats 接口）
import request from './request'

export function getLogList(params) {
  return request.get('/log/list', { params })
}

export function getLogModules() {
  return request.get('/log/modules')
}

export function getLogStats(days = 7) {
  return request.get('/log/stats', { params: { days } })
}

export function clearLogs(days, logType) {
  const params = { days }
  if (logType) params.log_type = logType
  return request.delete('/log/clear', { params })
}

export function recordLog(data) {
  return request.post('/log/record', null, { params: data })
}
