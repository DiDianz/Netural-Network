// src/composables/usePredictionStore.js
import { reactive, computed } from 'vue'

const state = reactive({
  predictions: [],
  actualValues: [],
  maxHistory: 500,
  stats: {
    avgPrediction: 0,
    maxPrediction: -Infinity,
    minPrediction: Infinity,
    totalReceived: 0
  }
})

export function usePredictionStore() {
  function addDataPoint(data) {
    state.predictions.push({
      ...data,
      time: new Date(data.timestamp * 1000).toLocaleTimeString()
    })

    if (state.predictions.length > state.maxHistory) {
      state.predictions.shift()
    }

    if (data.has_actual && data.actual_value != null) {
      state.actualValues.push({
        time: new Date(data.timestamp * 1000).toLocaleTimeString(),
        actual: data.actual_value
      })
      if (state.actualValues.length > state.maxHistory) {
        state.actualValues.shift()
      }
    }

    const pred = data.prediction
    state.stats.totalReceived++
    state.stats.maxPrediction = Math.max(state.stats.maxPrediction, pred)
    state.stats.minPrediction = Math.min(state.stats.minPrediction, pred)

    const recent = state.predictions.slice(-50)
    state.stats.avgPrediction = recent.reduce((s, d) => s + d.prediction, 0) / recent.length
  }

  function clearData() {
    state.predictions.splice(0, state.predictions.length)
    state.actualValues.splice(0, state.actualValues.length)
    state.stats = {
      avgPrediction: 0,
      maxPrediction: -Infinity,
      minPrediction: Infinity,
      totalReceived: 0
    }
  }

  // ========== 关键修改：返回稳定引用 ==========
  const chartData = computed(() => {
    const hasActual = state.actualValues.length > 0
    return {
      times: state.predictions.map(d => d.time),
      predictions: state.predictions.map(d => d.prediction),
      upper: state.predictions.map(d => d.confidence_upper),
      lower: state.predictions.map(d => d.confidence_lower),
      actuals: hasActual ? state.actualValues.map(d => d.actual) : [],
      hasActualData: hasActual,
      // 加一个长度标记，让 watch 可以只监听这个
      _len: state.predictions.length
    }
  })

  const latestPrediction = computed(() =>
    state.predictions.length > 0 ? state.predictions[state.predictions.length - 1] : null
  )

  return { state, chartData, latestPrediction, addDataPoint, clearData }
}
