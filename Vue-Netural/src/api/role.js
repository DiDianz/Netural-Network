// src/api/role.js
import request from './request'

// 角色列表
export function getRoleList(params) {
  return request.get('/system/role/list', { params })
}

// 角色选项（下拉框）
export function getRoleOptions() {
  return request.get('/system/role/options')
}