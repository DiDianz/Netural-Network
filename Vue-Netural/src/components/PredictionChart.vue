<!-- src/components/PredictionChart.vue -->
<template>
  <div class="chart-wrapper">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, shallowRef } from 'vue'
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
  chartData: { type: Object, required: true }
})

const chartRef = ref(null)
const chartInstance = shallowRef(null)

function initChart() {
  if (!chartRef.value) return
  chartInstance.value = echarts.init(chartRef.value)
  chartInstance.value.setOption({
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
    legend: { data: ['预测值'], top: 10, right: 20, textStyle: { color: '#888' } },
    grid: { left: 60, right: 30, top: 60, bottom: 80 },
    xAxis: {
      type: 'category', data: [],
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
    series: [{
      name: '预测值', type: 'line', data: [],
      smooth: 0.3,
      lineStyle: { color: '#4a9eff', width: 2.5 },
      itemStyle: { color: '#4a9eff' },
      showSymbol: false
    }]
  })
}

// 用 times.length 的变化来触发更新（避免 deep watch 的性能问题）
watch(
  () => props.chartData.times.length,
  function (newLen) {
    const chart = chartInstance.value
    const data = props.chartData
    if (!chart) return

    // 数据被清空时，重置图表 series（切换模型的中间态）
    if (newLen === 0) {
      chart.setOption({ series: [] }, { notMerge: false, lazyUpdate: true })
      return
    }

    const series = [{
      name: '预测值', type: 'line', data: data.predictions,
      smooth: 0.3,
      lineStyle: { color: '#4a9eff', width: 2.5 },
      itemStyle: { color: '#4a9eff' },
      showSymbol: false
    }]

    if (data.hasActualData && data.actuals.length > 0) {
      series.push({
        name: '实际值', type: 'line', data: data.actuals,
        smooth: 0.3,
        lineStyle: { color: '#f97316', width: 2, type: 'dashed' },
        itemStyle: { color: '#f97316' },
        showSymbol: false
      })
    }

    chart.setOption({
      xAxis: { data: data.times },
      legend: { data: data.hasActualData ? ['预测值', '实际值'] : ['预测值'] },
      series: series
    }, { notMerge: false, lazyUpdate: true })
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
