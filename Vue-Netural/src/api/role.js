import request from './request'

// 角色列表（分页）
export function getRoleList(params) {
  return request.get('/system/role/list', { params })
}

// 角色选项（下拉框）
export function getRoleOptions() {
  return request.get('/system/role/options')
}

// 获取角色详情
export function getRoleDetail(roleId) {
  return request.get(`/system/role/get/${roleId}`)
}

// 新增角色
export function addRole(data) {
  return request.post('/system/role/add', data)
}

// 修改角色
export function updateRole(data) {
  return request.put('/system/role/update', data)
}

// 删除角色
export function deleteRole(roleId) {
  return request.delete(`/system/role/delete/${roleId}`)
}
