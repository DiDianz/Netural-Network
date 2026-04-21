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
  },
  // 多系列数据 { seriesKey: { times: [], predictions: [], upper: [], lower: [] } }
  multiSeries: {},
  multiTimes: []
})

// 配色方案
const SERIES_COLORS = [
  '#4a9eff', '#f97316', '#22c55e', '#a855f7',
  '#ec4899', '#14b8a6', '#eab308', '#6366f1',
  '#ef4444', '#06b6d4'
]

function getSeriesColor(index) {
  return SERIES_COLORS[index % SERIES_COLORS.length]
}

function getSeriesName(modelKey, deviceId) {
  const modelNames = { lstm: 'LSTM', gru: 'GRU', transformer: 'Transformer' }
  return `${modelNames[modelKey] || modelKey} (PLC-${deviceId})`
}

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

  function addMultiDataPoint(data) {
    // data 来自 multi-stream: { timestamp, tick, plc_data, predictions: [...] }
    const timeStr = new Date(data.timestamp * 1000).toLocaleTimeString()
    state.multiTimes.push(timeStr)
    if (state.multiTimes.length > state.maxHistory) {
      state.multiTimes.shift()
    }

    for (const pred of data.predictions) {
      if (pred.error) continue

      // 找出这个预测对应的 PLC device_id
      const deviceId = Object.keys(data.plc_data || {})[0] || '0'
      const seriesKey = `${pred.model_key}_${deviceId}`

      if (!state.multiSeries[seriesKey]) {
        const idx = Object.keys(state.multiSeries).length
        state.multiSeries[seriesKey] = {
          model_key: pred.model_key,
          model_name: pred.model_name,
          device_id: deviceId,
          name: getSeriesName(pred.model_key, deviceId),
          color: getSeriesColor(idx),
          times: [],
          predictions: [],
          upper: [],
          lower: [],
          uncertainty: []
        }
      }

      const series = state.multiSeries[seriesKey]
      series.predictions.push(pred.prediction)
      series.upper.push(pred.confidence_upper)
      series.lower.push(pred.confidence_lower)
      series.uncertainty.push(pred.uncertainty)
      series.times.push(timeStr)

      // 保持长度
      if (series.predictions.length > state.maxHistory) {
        series.predictions.shift()
        series.upper.shift()
        series.lower.shift()
        series.uncertainty.shift()
        series.times.shift()
      }

      // 更新全局统计
      state.stats.totalReceived++
      state.stats.maxPrediction = Math.max(state.stats.maxPrediction, pred.prediction)
      state.stats.minPrediction = Math.min(state.stats.minPrediction, pred.prediction)
      const recent = series.predictions.slice(-50)
      state.stats.avgPrediction = recent.reduce((s, v) => s + v, 0) / recent.length
    }
  }

  function clearData() {
    state.predictions.splice(0, state.predictions.length)
    state.actualValues.splice(0, state.actualValues.length)
    state.multiTimes.splice(0, state.multiTimes.length)
    // 清空多系列
    for (const key of Object.keys(state.multiSeries)) {
      delete state.multiSeries[key]
    }
    state.stats = {
      avgPrediction: 0,
      maxPrediction: -Infinity,
      minPrediction: Infinity,
      totalReceived: 0
    }
  }

  const chartData = computed(() => {
    const hasActual = state.actualValues.length > 0
    return {
      times: state.predictions.map(d => d.time),
      predictions: state.predictions.map(d => d.prediction),
      upper: state.predictions.map(d => d.confidence_upper),
      lower: state.predictions.map(d => d.confidence_lower),
      actuals: hasActual ? state.actualValues.map(d => d.actual) : [],
      hasActualData: hasActual,
      _len: state.predictions.length
    }
  })

  // 多系列图表数据
  const multiChartData = computed(() => {
    const seriesList = Object.values(state.multiSeries)
    return {
      times: [...state.multiTimes],
      series: seriesList.map(s => ({
        name: s.name,
        color: s.color,
        predictions: [...s.predictions],
        upper: [...s.upper],
        lower: [...s.lower],
        model_key: s.model_key,
        device_id: s.device_id
      })),
      _len: state.multiTimes.length
    }
  })

  const latestPrediction = computed(() =>
    state.predictions.length > 0 ? state.predictions[state.predictions.length - 1] : null
  )

  // 多系列最新预测
  const multiLatestPredictions = computed(() => {
    const result = {}
    for (const [key, series] of Object.entries(state.multiSeries)) {
      if (series.predictions.length > 0) {
        result[key] = {
          name: series.name,
          color: series.color,
          prediction: series.predictions[series.predictions.length - 1],
          upper: series.upper[series.upper.length - 1],
          lower: series.lower[series.lower.length - 1],
          uncertainty: series.uncertainty[series.uncertainty.length - 1]
        }
      }
    }
    return result
  })

  return {
    state, chartData, multiChartData, latestPrediction, multiLatestPredictions,
    addDataPoint, addMultiDataPoint, clearData
  }
}
