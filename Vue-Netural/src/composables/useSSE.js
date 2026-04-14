// src/composables/useSSE.js
import { ref } from 'vue'
import { usePredictionStore } from './usePredictionStore'

export function useSSE() {
  const { addDataPoint, clearData } = usePredictionStore()
  const connectionState = ref('closed')
  let eventSource = null

  function startStream(interval, modelKey, useUploaded) {
    // 先关旧连接
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
      // 只清理当前引用
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
    stopStream
  }
}
