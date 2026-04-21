import request from './request'

export function getPredictHistory(modelKey, limit = 200) {
  return request.get('/predict/history', { params: { model_key: modelKey, limit } })
}

export function getActualValues(fileIds, limit = 500) {
  return request.get('/predict/actual-values', { params: { file_ids: fileIds, limit } })
}
