// src/api/user.js
import request from './request'

// 获取当前用户信息
export function getUserInfo() {
  return request.get('/system/user/info')
}

// 用户列表（分页）
export function getUserList(params) {
  return request.get('/system/user/list', { params })
}

// 获取用户详情
export function getUserDetail(userId) {
  return request.get(`/system/user/get/${userId}`)
}

// 新增用户
export function addUser(data) {
  return request.post('/system/user/add', data)
}

// 修改用户
export function updateUser(data) {
  return request.put('/system/user/update', data)
}

// 删除用户
export function deleteUser(userId) {
  return request.delete(`/system/user/delete/${userId}`)
}

// 重置密码
export function resetUserPwd(data) {
  return request.put('/system/user/resetPwd', data)
}