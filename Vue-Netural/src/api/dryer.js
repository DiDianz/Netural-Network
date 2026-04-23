// src/api/dryer.js
import request from './request'

// 上传训练数据
export function uploadDryerData(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/dryer/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 数据分析
export function analyzeData() {
  return request({ url: '/dryer/analyze', method: 'get' })
}

// 训练模型 (SSE, 由组件直接调用)
export function getTrainUrl(params) {
  const qs = new URLSearchParams(params).toString()
  return `/dryer/train?${qs}`
}

// 预测
export function predict(data, modelVersion) {
  return request({
    url: '/dryer/predict',
    method: 'post',
    data: { data, model_version: modelVersion || undefined }
  })
}

// 获取特征权重
export function getWeights() {
  return request({ url: '/dryer/weights', method: 'get' })
}

// 更新特征权重
export function updateWeights(weights) {
  return request({ url: '/dryer/weights', method: 'post', data: { weights } })
}

// 模型版本列表
export function listVersions() {
  return request({ url: '/dryer/versions', method: 'get' })
}

// 激活版本
export function activateVersion(version) {
  return request({ url: `/dryer/versions/${version}/activate`, method: 'post' })
}

// 删除版本
export function deleteVersion(version) {
  return request({ url: `/dryer/versions/${version}`, method: 'delete' })
}

// 评估模型
export function evaluateModel(version) {
  return request({ url: '/dryer/evaluate', method: 'get', params: { model_version: version || '' } })
}

// PLC 预测 SSE URL
export function getPLCStreamUrl(deviceId, pointIds, interval, modelVersion) {
  const params = new URLSearchParams({ device_id: deviceId, interval: interval || 1 })
  if (pointIds) params.append('point_ids', pointIds)
  if (modelVersion) params.append('model_version', modelVersion)
  return `/dryer/plc-stream?${params.toString()}`
}
