import request from './request'

// 菜单列表（Sidebar 用）
export function getMenuList() {
  return request.get('/system/menu/list')
}

// 菜单树（菜单管理页用）
export function getMenuTree() {
  return request.get('/system/menu/tree')
}

// 菜单树选择器（角色分配权限用）
export function getMenuTreeSelect() {
  return request.get('/system/menu/treeselect')
}

// 获取菜单详情
export function getMenuDetail(menuId) {
  return request.get(`/system/menu/get/${menuId}`)
}

// 新增菜单
export function addMenu(data) {
  return request.post('/system/menu/add', data)
}

// 修改菜单
export function updateMenu(data) {
  return request.put('/system/menu/update', data)
}

// 删除菜单
export function deleteMenu(menuId) {
  return request.delete(`/system/menu/delete/${menuId}`)
}
