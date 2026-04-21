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
import { graphic } from 'echarts/core'

echarts.use([
  LineChart, CanvasRenderer,
  GridComponent, TooltipComponent, LegendComponent,
  DataZoomComponent, MarkLineComponent
])

const props = defineProps({
  chartData: { type: Object, required: true },
  // 新增：多系列数据
  multiChartData: { type: Object, default: null }
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

// 单系列模式（兼容原有逻辑）
watch(
  () => props.chartData.times.length,
  function (newLen) {
    // 如果有多个系列数据，跳过单系列更新
    if (props.multiChartData && props.multiChartData.series && props.multiChartData.series.length > 0) return

    const chart = chartInstance.value
    const data = props.chartData
    if (!chart) return

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

// 多系列模式
watch(
  () => props.multiChartData ? props.multiChartData._len : 0,
  function (newLen) {
    if (!props.multiChartData || !props.multiChartData.series || props.multiChartData.series.length === 0) return

    const chart = chartInstance.value
    const data = props.multiChartData
    if (!chart) return

    if (newLen === 0) {
      chart.setOption({ series: [], legend: { data: [] } }, { notMerge: true, lazyUpdate: true })
      return
    }

    const legendData = []
    const series = []

    for (const s of data.series) {
      // 预测值主线
      legendData.push(s.name)
      series.push({
        name: s.name,
        type: 'line',
        data: s.predictions,
        smooth: 0.3,
        lineStyle: { color: s.color, width: 2.5 },
        itemStyle: { color: s.color },
        showSymbol: false
      })

      // 置信区间上界
      series.push({
        name: s.name + ' 上界',
        type: 'line',
        data: s.upper,
        smooth: 0.3,
        lineStyle: { color: s.color, width: 0.8, type: 'dashed', opacity: 0.4 },
        itemStyle: { color: s.color, opacity: 0.3 },
        showSymbol: false
      })

      // 置信区间下界
      series.push({
        name: s.name + ' 下界',
        type: 'line',
        data: s.lower,
        smooth: 0.3,
        lineStyle: { color: s.color, width: 0.8, type: 'dashed', opacity: 0.4 },
        itemStyle: { color: s.color, opacity: 0.3 },
        showSymbol: false,
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: s.color + '15' },
            { offset: 1, color: s.color + '05' }
          ])
        }
      })
    }

    chart.setOption({
      xAxis: { data: data.times },
      legend: {
        data: legendData,
        top: 10,
        right: 20,
        textStyle: { color: '#888' }
      },
      series: series
    }, { notMerge: true, lazyUpdate: true })
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
