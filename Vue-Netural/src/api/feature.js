// src/api/feature.js
import request from './request'

// ========== 特征方案 ==========

/** 获取所有特征方案列表 */
export function listSchemas() {
  return request.get('/feature/schema/list')
}

/** 获取方案详情 */
export function getSchema(schemaId) {
  return request.get(`/feature/schema/${schemaId}`)
}

/** 创建特征方案 */
export function createSchema(data) {
  return request.post('/feature/schema', data)
}

/** 更新特征方案 */
export function updateSchema(schemaId, data) {
  return request.put(`/feature/schema/${schemaId}`, data)
}

/** 删除特征方案 */
export function deleteSchema(schemaId) {
  return request.delete(`/feature/schema/${schemaId}`)
}

/** 复制方案 */
export function copySchema(schemaId, newName) {
  return request.post(`/feature/schema/${schemaId}/copy`, { new_name: newName })
}

/** 更新特征权重 */
export function updateWeights(schemaId, weights) {
  return request.put(`/feature/schema/${schemaId}/weights`, { weights })
}

/** 获取特征权重 */
export function getWeights(schemaId) {
  return request.get(`/feature/schema/${schemaId}/weights`)
}
