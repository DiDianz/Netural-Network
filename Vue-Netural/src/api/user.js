// src/api/user.js
import request from './request'

export function getUserInfo() {
  return request.get('/system/user/info')
}
