// src/api/plc.js
import request from './request'

// ========== PLC 设备管理 ==========
export function getPlcDeviceList() {
  return request.get('/plc/device/list')
}

export function getPlcDeviceDetail(deviceId) {
  return request.get('/plc/device/detail', { params: { device_id: deviceId } })
}

export function addPlcDevice(data) {
  return request.post('/plc/device/add', null, { params: data })
}

export function updatePlcDevice(data) {
  return request.put('/plc/device/update', null, { params: data })
}

export function deletePlcDevice(deviceId) {
  return request.delete('/plc/device/delete', { params: { device_id: deviceId } })
}

// ========== PLC 连接管理 ==========
export function connectPlc(deviceId) {
  return request.post('/plc/device/connect', null, { params: { device_id: deviceId } })
}

export function disconnectPlc(deviceId) {
  return request.post('/plc/device/disconnect', null, { params: { device_id: deviceId } })
}

export function connectAllPlc() {
  return request.post('/plc/device/connect-all')
}

export function disconnectAllPlc() {
  return request.post('/plc/device/disconnect-all')
}

// ========== PLC DB 点位管理 ==========
export function getPlcPointList(params) {
  return request.get('/plc/point/list', { params })
}

export function addPlcPoint(data) {
  return request.post('/plc/point/add', null, { params: data })
}

export function updatePlcPoint(data) {
  return request.put('/plc/point/update', null, { params: data })
}

export function deletePlcPoint(pointId) {
  return request.delete('/plc/point/delete', { params: { point_id: pointId } })
}

// ========== PLC 数据读取 ==========
export function readPlcSingle(params) {
  return request.get('/plc/read/single', { params })
}

export function readPlcBatch(deviceId, pointIds) {
  return request.get('/plc/read/batch', {
    params: { device_id: deviceId, point_ids: pointIds }
  })
}
