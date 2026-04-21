<!-- src/components/PredictionChart.vue -->
<template>
  <div class="chart-wrapper">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, shallowRef, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  DataZoomComponent, MarkLineComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  LineChart, CanvasRenderer,
  GridComponent, TooltipComponent, LegendComponent,
  DataZoomComponent, MarkLineComponent
])

const props = defineProps({
  chartData: { type: Object, required: true },
  multiChartData: { type: Object, default: null },
  // 传入的点位列表：[{ point_name, description, history: [] }]
  inputPoints: { type: Array, default: () => [] }
})

const chartRef = ref(null)
const chartInstance = shallowRef(null)

// 点位配色
const POINT_COLORS = [
  '#4a9eff', '#f97316', '#22c55e', '#a855f7',
  '#ec4899', '#14b8a6', '#eab308', '#6366f1',
  '#ef4444', '#06b6d4'
]

// 构建 series + legend（不包含 dataZoom，用于增量更新）
function buildSeriesAndLegend(data, inputPts) {
  const legendData = ['预测值']
  const series = [{
    name: '预测值', type: 'line', data: data.predictions,
    smooth: 0.3,
    lineStyle: { color: '#4a9eff', width: 2.5 },
    itemStyle: { color: '#4a9eff' },
    showSymbol: false,
    z: 10
  }]

  inputPts.forEach((p, i) => {
    const color = POINT_COLORS[i % POINT_COLORS.length]
    const label = p.description || p.point_name
    if (p.history && p.history.length > 0) {
      legendData.push(label)
      series.push({
        name: label, type: 'line', data: p.history,
        smooth: 0.3,
        lineStyle: { color, width: 1.5 },
        itemStyle: { color },
        showSymbol: false,
        yAxisIndex: 0
      })
    }
  })

  if (data.hasActualData && data.actuals.length > 0) {
    legendData.push('实际值')
    series.push({
      name: '实际值', type: 'line', data: data.actuals,
      smooth: 0.3,
      lineStyle: { color: '#f97316', width: 2, type: 'dashed' },
      itemStyle: { color: '#f97316' },
      showSymbol: false
    })
  }

  return { legendData, series }
}

// 完整 option（含 dataZoom，仅用于初始化）
function buildFullOption(data, inputPts) {
  const { legendData, series } = buildSeriesAndLegend(data, inputPts)
  return {
    title: {
      text: '神经网络实时预测',
      left: 20, top: 10,
      textStyle: { fontSize: 16, fontWeight: 600, color: '#e0e0e0' }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 15, 20, 0.95)',
      borderColor: '#333',
      textStyle: { color: '#e0e0e0' }
    },
    legend: { data: legendData, top: 10, right: 20, textStyle: { color: '#888' } },
    grid: { left: 60, right: 30, top: 60, bottom: 80 },
    xAxis: {
      type: 'category', data: data.times,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#666' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } }
    },
    dataZoom: [
      { type: 'inside', start: 80, end: 100 },
      { type: 'slider', start: 80, end: 100, height: 20, bottom: 10 }
    ],
    series
  }
}

// 安全调用 setOption
// 用 notMerge: false 保留用户 dataZoom 拖动位置，不每次重置缩放范围
function safeSetOption(chart, option) {
  if (!chart) return
  try {
    chart.setOption(option, { notMerge: false, lazyUpdate: true })
  } catch (e) {
    console.warn('[PredictionChart] setOption warning:', e.message)
  }
}

function initChart() {
  if (!chartRef.value) return
  chartInstance.value = echarts.init(chartRef.value)
  // 初始渲染用 notMerge: true 确保干净状态
  chartInstance.value.setOption(
    buildFullOption({ times: [], predictions: [], actuals: [], hasActualData: false }, []),
    { notMerge: true, lazyUpdate: true }
  )
}

// 主更新：预测线 + 点位趋势线
// 只更新 xAxis/legend/series，不传 dataZoom，保留用户缩放位置
watch(
  () => [props.chartData._len, props.inputPoints.map(p => (p.history || []).length).join(',')],
  function () {
    const chart = chartInstance.value
    if (!chart) return
    if (props.multiChartData && props.multiChartData.series && props.multiChartData.series.length > 0) return

    nextTick(() => {
      if (!chartInstance.value) return
      const data = props.chartData
      const { legendData, series } = buildSeriesAndLegend(data, props.inputPoints)
      safeSetOption(chart, {
        xAxis: { data: data.times },
        legend: { data: legendData },
        series
      })
    })
  },
  { deep: true }
)

// 多系列模式 —— 同理不传 dataZoom
watch(
  () => props.multiChartData ? props.multiChartData._len : 0,
  function (newLen) {
    if (!props.multiChartData || !props.multiChartData.series || props.multiChartData.series.length === 0) return
    const chart = chartInstance.value
    if (!chart) return

    nextTick(() => {
      if (!chartInstance.value) return
      if (newLen === 0) {
        safeSetOption(chart, { series: [], legend: { data: [] } })
        return
      }
      const data = props.multiChartData
      const legendData = []
      const series = []
      for (const s of data.series) {
        legendData.push(s.name)
        series.push({
          name: s.name, type: 'line', data: s.predictions,
          smooth: 0.3,
          lineStyle: { color: s.color, width: 2.5 },
          itemStyle: { color: s.color },
          showSymbol: false
        })
        series.push({
          name: s.name + ' 上界', type: 'line', data: s.upper,
          smooth: 0.3,
          lineStyle: { color: s.color, width: 0.8, type: 'dashed', opacity: 0.4 },
          itemStyle: { color: s.color, opacity: 0.3 },
          showSymbol: false
        })
        series.push({
          name: s.name + ' 下界', type: 'line', data: s.lower,
          smooth: 0.3,
          lineStyle: { color: s.color, width: 0.8, type: 'dashed', opacity: 0.4 },
          itemStyle: { color: s.color, opacity: 0.3 },
          showSymbol: false,
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: s.color + '15' },
                { offset: 1, color: s.color + '05' }
              ]
            }
          }
        })
      }
      safeSetOption(chart, {
        xAxis: { data: data.times },
        legend: { data: legendData },
        series
      })
    })
  }
)

function handleResize() {
  if (chartInstance.value) chartInstance.value.resize()
}

onMounted(function () {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(function () {
  window.removeEventListener('resize', handleResize)
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
})
</script>

<style scoped>
.chart-wrapper {
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
  padding: 16px;
}
.chart-container {
  width: 100%;
  height: 420px;
}
</style>
