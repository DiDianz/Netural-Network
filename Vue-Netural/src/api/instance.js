// src/api/instance.js
import request from './request'

// 预测实例 CRUD
export function getInstanceList() {
  return request.get('/instance/list')
}

export function getInstanceDetail(instanceId) {
  return request.get('/instance/detail', { params: { instance_id: instanceId } })
}

export function addInstance(data) {
  return request.post('/instance/add', null, { params: data })
}

export function updateInstance(data) {
  return request.put('/instance/update', null, { params: data })
}

export function deleteInstance(instanceId) {
  return request.delete('/instance/delete', { params: { instance_id: instanceId } })
}
