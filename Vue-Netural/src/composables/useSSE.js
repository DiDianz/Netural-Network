// src/composables/useSSE.js
import { ref } from 'vue'
import { usePredictionStore } from './usePredictionStore'

export function useSSE() {
  const { addDataPoint, addMultiDataPoint, clearData } = usePredictionStore()
  const connectionState = ref('closed')
  let eventSource = null

  function startStream(interval, modelKey, useUploaded) {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    clearData()
    connectionState.value = 'connecting'

    let url = `http://localhost:8000/predict/stream?interval=${interval || 1}`
    if (modelKey) url += `&model_key=${modelKey}`
    if (useUploaded) url += `&use_uploaded=true`

    const es = new EventSource(url)

    es.onopen = () => {
      connectionState.value = 'open'
    }

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        addDataPoint(data)
      } catch (e) {
        // 忽略解析错误
      }
    }

    es.onerror = () => {
      connectionState.value = 'closed'
      es.close()
      if (eventSource === es) {
        eventSource = null
      }
    }

    eventSource = es
  }

  /**
   * 多 PLC 多模型并行预测流
   * @param {number} interval - 预测间隔
   * @param {Array} devices - [{device_id, point_ids}]
   * @param {string[]} modelKeys - ['lstm', 'gru']
   */
  function startMultiStream(interval, devices, modelKeys) {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    clearData()
    connectionState.value = 'connecting'

    const devicesJson = encodeURIComponent(JSON.stringify(devices))
    const modelsStr = modelKeys.join(',')
    const url = `http://localhost:8000/predict/multi-stream?devices=${devicesJson}&model_keys=${modelsStr}&interval=${interval || 1}`

    const es = new EventSource(url)

    es.onopen = () => {
      connectionState.value = 'open'
    }

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        addMultiDataPoint(data)
      } catch (e) {
        // 忽略解析错误
      }
    }

    es.onerror = () => {
      connectionState.value = 'closed'
      es.close()
      if (eventSource === es) {
        eventSource = null
      }
    }

    eventSource = es
  }

  function stopStream() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    connectionState.value = 'closed'
  }

  return {
    connectionState,
    startStream,
    startMultiStream,
    stopStream
  }
}
