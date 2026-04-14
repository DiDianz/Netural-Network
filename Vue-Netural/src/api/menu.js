// src/api/menu.js
import request from './request'

export function getMenuList() {
  return request.get('/system/menu/list')
}
