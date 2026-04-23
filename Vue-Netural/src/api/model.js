// src/api/model.js
import request from './request'

// ========== 模型管理 ==========
export function getModelList() { return request.get('/model/list') }
export function switchModel(modelKey) { return request.post('/model/switch', { model_key: modelKey }) }
export function getModelStatus() { return request.get('/model/status') }

// ========== 训练 ==========
export function startTrain(data) { return request.post('/model/train/start', data) }
export function stopTrain() { return request.post('/model/train/stop') }
export function getTrainStatus() { return request.get('/model/train/status') }

// ========== 上传数据训练（支持自定义特征列） ==========
export function startTrainWithUpload(params) {
  // params 包含: model_key, file_ids, epochs, lr, batch_size, schema_id, feature_weights, ...
  return request.post('/model/train/upload', null, { params })
}
export function stopUploadTrain(modelKey) {
  return request.post('/model/train/upload/stop', null, { params: { model_key: modelKey } })
}

// ========== 模型版本管理 ==========
export function getSavedModels(modelKey) {
  const params = modelKey ? { model_key: modelKey } : {}
  return request.get('/model/saved/list', { params })
}
export function deleteSavedModel(modelId) { return request.delete(`/model/saved/${modelId}`) }
export function loadSavedModel(modelId) { return request.post(`/model/saved/${modelId}/load`) }
export function renameSavedModel(modelId, name) {
  return request.put(`/model/saved/${modelId}/rename`, { name })
}

// ========== 文件上传（支持自定义特征列） ==========
export function uploadFile(file, schemaId) {
  const fd = new FormData()
  fd.append('file', file)
  const params = schemaId ? { schema_id: schemaId } : {}
  return request.post('/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params
  })
}
export function getUploadedFiles() { return request.get('/upload/list') }
export function getUploadPreview(fileId) { return request.get(`/upload/preview/${fileId}`) }
export function deleteUploadedFile(fileId) { return request.delete(`/upload/${fileId}`) }

// ========== 下载模板（支持自定义特征列） ==========
export function downloadTemplate(format, schemaId) {
  const params = new URLSearchParams()
  params.set('format', format || 'csv')
  if (schemaId) params.set('schema_id', schemaId)

  const url = `http://localhost:8000/upload/template?${params.toString()}`
  const token = localStorage.getItem('token')
  return fetch(url, {
    headers: { 'Authorization': 'Bearer ' + (token || '') }
  }).then(res => res.blob()).then(blob => {
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = format === 'xlsx' ? 'upload_template.xlsx' : 'upload_template.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  })
}

// ========== 预测历史（支持关键字搜索） ==========
export function getPredictionHistory(params) {
  return request.get('/predict/history', { params })
}

export function getActualValues(fileIds, limit) {
  return request.get('/predict/actual-values', { params: { file_ids: fileIds, limit: limit || 500 } })
}

// ========== 训练历史（支持关键字搜索） ==========
export function getTrainHistory(params) {
  return request.get('/model/train/history', { params })
}

// ========== 训练趋势 ==========
export function getTrainTrend(params) {
  return request.get('/model/train/trend', { params })
}

export function getTrainTrendList(params) {
  return request.get('/model/train/trend/list', { params })
}
