<!-- src/views/prediction/training/index.vue -->
<template>
  <div class="training-page">
    <!-- 数据源切换 -->
    <div class="source-selector">
      <span class="selector-label">训练方式:</span>
      <el-radio-group v-model="trainMode" size="default" @change="handleModeChange">
        <el-radio-button value="random">随机模拟数据</el-radio-button>
        <el-radio-button value="uploaded">上传真实数据</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 模型来源切换 -->
    <div class="source-selector">
      <span class="selector-label">模型来源:</span>
      <el-radio-group v-model="modelSource" size="default" @change="handleSourceChange">
        <el-radio-button value="new">训练新模型</el-radio-button>
        <el-radio-button value="existing">从已有模型继续训练</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 已有模型选择 -->
    <div class="base-model-section" v-if="modelSource === 'existing'">
      <div class="base-model-row">
        <span class="config-label">选择基础模型:</span>
        <el-select v-model="selectedBaseModelId" placeholder="选择一个已保存的模型版本" style="width: 500px"
          :loading="loadingSavedModels" filterable>
          <el-option v-for="m in filteredSavedModels" :key="m.model_id"
            :label="`${m.display_name} | ${m.epochs}轮 | Val Loss: ${m.best_val_loss} | ${m.trained_at}`"
            :value="m.model_id" />
        </el-select>
        <el-button size="small" @click="loadSavedModels" :loading="loadingSavedModels" style="margin-left: 8px">
          刷新
        </el-button>
      </div>
      <div class="base-model-hint" v-if="!filteredSavedModels.length && !loadingSavedModels">
        暂无已保存的 {{ modelDisplayName }} 模型版本，请先训练一个模型或切换模型类型。
      </div>
    </div>

    <!-- 上传区域 -->
    <div class="upload-section" v-if="trainMode === 'uploaded'">
      <div class="upload-header">
        <h3>数据上传</h3>
        <div class="template-actions">
          <el-button type="primary" plain size="small" @click="handleDownloadTemplate('csv')">下载 CSV 模板</el-button>
          <el-button type="success" plain size="small" @click="handleDownloadTemplate('xlsx')">下载 Excel 模板</el-button>
        </div>
      </div>
      <div class="template-hint">
        模板包含 11 个特征列 + out_moist（目标）+ brandID（品牌标识）。相同 brandID 的数据为一组，基于特征变化预测 out_moist。
      </div>
      <el-upload drag multiple :auto-upload="false" :on-change="handleFileChange" :file-list="fileList"
        accept=".csv,.txt,.json,.xlsx,.xls" :on-remove="handleRemove">
        <div class="upload-area">
          <div class="upload-icon">+</div>
          <div class="upload-text">拖拽文件到这里，或点击选择</div>
          <div class="upload-hint">支持 CSV / TXT / JSON / Excel</div>
        </div>
      </el-upload>
      <div class="upload-actions" v-if="fileList.length > 0">
        <el-button type="primary" @click="handleUploadAll" :loading="uploading">上传全部 ({{ fileList.length }})</el-button>
      </div>

      <div class="uploaded-list" v-if="uploadedFiles.length > 0">
        <el-table :data="uploadedFiles" stripe size="small">
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="num_rows" label="行数" width="80" />
          <el-table-column prop="brand_count" label="品牌数" width="80" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button size="small" @click="previewData(row)">预览</el-button>
              <el-button size="small" type="danger" @click="handleDeleteFile(row.file_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="preview-table" v-if="previewRows.length > 0">
        <h4>数据预览（前 {{ previewRows.length }} 行）</h4>
        <el-table :data="previewDisplay" stripe max-height="200" style="width: 100%">
          <el-table-column v-for="col in previewCols" :key="col" :prop="col" :label="col" width="100" />
        </el-table>
      </div>

      <div class="upload-train-config" v-if="uploadedFiles.length > 0">
        <div class="config-row">
          <span class="config-label">选择数据</span>
          <el-select v-model="selectedFileIds" multiple placeholder="选择训练数据" style="width: 400px">
            <el-option v-for="f in uploadedFiles" :key="f.file_id"
              :label="`${f.filename} (${f.num_rows}行, ${f.brand_count}品牌)`" :value="f.file_id" />
          </el-select>
        </div>
      </div>
    </div>

    <!-- 顶部控制 -->
    <div class="train-controls">
      <div class="control-left">
        <h2>模型训练</h2>
        <el-select v-model="selectedModel" placeholder="选择模型" style="width: 180px">
          <el-option label="LSTM + Attention" value="lstm" />
          <el-option label="GRU" value="gru" />
          <el-option label="Transformer" value="transformer" />
        </el-select>
        <el-input-number v-model="epochs" :min="10" :max="200" :step="10" controls-position="right" />
        <span class="param-label">轮次</span>
        <el-input-number v-model="learningRate" :min="0.0001" :max="0.01" :step="0.0001" :precision="4"
          controls-position="right" />
        <span class="param-label">学习率</span>
      </div>
      <div class="control-right">
        <el-button v-if="!isTraining" type="primary" size="large" @click="handleStartTrain">开始训练</el-button>
        <el-button v-else type="danger" size="large" @click="handleStopTrain">停止训练</el-button>
      </div>
    </div>

    <!-- 进度 -->
    <div class="progress-section" v-if="trainState.total_epochs > 0 || isTraining">
      <div v-if="isTraining && trainState.epoch === 0" class="waiting-msg">正在启动训练...</div>
      <template v-if="trainState.epoch > 0">
        <div class="progress-info">
          <span>Epoch {{ trainState.epoch }} / {{ trainState.total_epochs }}</span>
          <span>{{ trainState.progress }}%</span>
        </div>
        <el-progress :percentage="trainState.progress" :stroke-width="10" :show-text="false"
          :status="trainState.done ? 'success' : ''" />
        <div class="progress-details">
          <span>Loss: <b>{{ trainState.loss.toFixed(6) }}</b></span>
          <span>Val Loss: <b>{{ trainState.val_loss.toFixed(6) }}</b></span>
          <span>最优: <b>{{ trainState.best_val_loss.toFixed(6) }}</b></span>
          <span>耗时: <b>{{ trainState.elapsed }}s</b></span>
        </div>
      </template>
    </div>

    <!-- 第一行：Loss + 学习率/验证集预测 -->
    <div class="charts-row">
      <div class="chart-card">
        <div ref="lossChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card" v-if="trainMode === 'random'">
        <div ref="lrChartRef" class="chart-container"></div>
      </div>
      <div class="chart-card" v-if="trainMode === 'uploaded'">
        <div ref="valPredChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- 趋势图区域 -->
    <div class="trend-section" v-if="trainMode === 'uploaded'">
      <div class="trend-header">
        <div class="trend-title-row">
          <h3>out_moist 实际值 vs 预测值趋势</h3>
          <span class="trend-brand-name">{{ brandTitle }}</span>
        </div>
        <div class="trend-info">
          <span class="trend-epoch" v-if="trainState.trend_epoch > 0">
            Epoch: {{ trainState.trend_epoch }} / {{ trainState.total_epochs }}
          </span>
          <span class="trend-range" v-if="trendRange.min !== null">
            范围: {{ trendRange.min.toFixed(4) }} ~ {{ trendRange.max.toFixed(4) }}
          </span>
        </div>
      </div>
      <div class="trend-chart-wrap">
        <div ref="trendChartRef" class="trend-chart-container"></div>
      </div>
    </div>

    <!-- [修改1] 品牌图表：上传模式下显示区域，brandList 为空时显示提示 -->
    <div class="brand-charts-section" v-if="trainMode === 'uploaded'">
      <h3>各品牌 out_moist 预测趋势</h3>
      <div class="brand-charts-grid">
        <template v-if="brandList.length > 0">
          <div v-for="brand in brandList" :key="brand" class="brand-chart-wrapper">
            <div class="brand-chart-title">品牌：{{ brand }}</div>
            <div
              :id="'brand-chart-' + brand"
              class="brand-chart-container"
            ></div>
          </div>
        </template>
        <div v-else class="brand-empty">暂无品牌预测数据，训练后将显示各品牌预测趋势。</div>
      </div>
    </div>

    <!-- 训练日志 -->
    <div class="log-section">
      <div class="log-header">
        <h3>训练日志</h3>
        <el-button size="small" @click="clearLogs">清空</el-button>
      </div>
      <div class="log-body" ref="logBodyRef">
        <div v-for="(log, i) in trainState.logs" :key="i" class="log-line">
          <span class="log-epoch">[{{ log.epoch }}/{{ trainState.total_epochs }}]</span>
          <span class="log-loss">Loss: {{ log.loss.toFixed(6) }}</span>
          <span class="log-val">Val: {{ log.val_loss.toFixed(6) }}</span>
          <span class="log-lr">LR: {{ log.lr }}</span>
          <span class="log-time">{{ log.time }}s</span>
        </div>
        <div v-if="trainState.logs.length === 0" class="log-empty">点击"开始训练"查看训练日志</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import {
  startTrain, stopTrain, getTrainStatus,
  uploadFile, getUploadedFiles, getUploadPreview, deleteUploadedFile,
  startTrainWithUpload, stopUploadTrain, downloadTemplate,
  getSavedModels
} from '../../../api/model'

echarts.use([LineChart, CanvasRenderer, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const route = useRoute()

const selectedModel = ref('lstm')
const epochs = ref(50)
const learningRate = ref(0.001)
const isTraining = ref(false)
const trainMode = ref('random')

// 模型来源
const modelSource = ref('new')
const selectedBaseModelId = ref(null)
const savedModels = ref([])
const loadingSavedModels = ref(false)

const fileList = ref([])
const uploadedFiles = ref([])
const uploading = ref(false)
const previewRows = ref([])
const previewCols = ref([])
const previewDisplay = ref([])
const selectedFileIds = ref([])

const trainState = reactive({
  is_training: false, model_key: '', epoch: 0, total_epochs: 0,
  loss: 0, val_loss: 0, best_val_loss: 0, progress: 0, elapsed: 0,
  logs: [], loss_history: [], val_loss_history: [], done: false, message: '',
  predictions: [], actuals: [], brand_predictions: {},
  trend_predictions: [], trend_actuals: [], trend_epoch: 0
})

const trendRange = reactive({ min: null, max: null })

const lossChartRef = ref(null)
const lrChartRef = ref(null)
const valPredChartRef = ref(null)
const trendChartRef = ref(null)
const logBodyRef = ref(null)

let lossChart = null
let lrChart = null
let valPredChart = null
let trendChart = null
let pollTimer = null
let sseSource = null
let brandChartTimer = null

// [修改2] brandList 改为 computed，从 brand_predictions 的 keys 自动派生
// Vue 会自动管理 v-for 的 DOM 创建/销毁
const brandList = computed(function () {
  var bp = trainState.brand_predictions
  if (!bp || typeof bp !== 'object') return []
  return Object.keys(bp)
})

const brandTitle = computed(function () {
  if (!brandList.value.length) return '品牌: -'
  if (brandList.value.length === 1) return '品牌: ' + brandList.value[0]
  return '品牌: ' + brandList.value.join('、')
})

const modelDisplayName = computed(function () {
  var names = { lstm: 'LSTM + Attention', gru: 'GRU', transformer: 'Transformer' }
  return names[selectedModel.value] || selectedModel.value
})

const filteredSavedModels = computed(function () {
  return savedModels.value.filter(function (m) { return m.model_key === selectedModel.value })
})

// ===== 安全创建/获取 ECharts 实例 =====
function safeGetChart(dom, existing) {
  if (!dom) return null
  if (dom.offsetWidth < 10 || dom.offsetHeight < 10) return null

  if (existing) {
    try {
      var existingDom = existing.getDom()
      if (existingDom && document.contains(existingDom) && existingDom.offsetWidth >= 10 && existingDom.offsetHeight >= 10) {
        return existing
      }
    } catch (e) { }
    try { existing.dispose() } catch (e) { }
  }

  var inst = echarts.getInstanceByDom(dom)
  if (inst) {
    try { inst.dispose() } catch (e) { }
  }

  try {
    var chart = echarts.init(dom)
    chart.resize()
    return chart
  } catch (e) {
    console.error('ECharts init 失败:', e)
    return null
  }
}

onMounted(() => {
  if (route.query.model) selectedModel.value = route.query.model
  if (route.query.base_model_id) {
    modelSource.value = 'existing'
    selectedBaseModelId.value = route.query.base_model_id
  }
  setTimeout(function () {
    try { initVisibleCharts() } catch (e) { console.error('图表初始化失败:', e) }
  }, 300)
  window.addEventListener('resize', handleWindowResize)
  checkAndStartPolling()
  loadUploadedFiles()
  loadSavedModels()
})

onUnmounted(() => { cleanup() })

function handleWindowResize() {
  try {
    if (lossChart) lossChart.resize()
    if (lrChart) lrChart.resize()
    if (valPredChart) valPredChart.resize()
    if (trendChart) trendChart.resize()
    brandList.value.forEach(function (brand) {
      var el = document.getElementById('brand-chart-' + brand)
      if (el) {
        var inst = echarts.getInstanceByDom(el)
        if (inst) inst.resize()
      }
    })
  } catch (e) { }
}

function cleanup() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null }
  if (brandChartTimer) { clearInterval(brandChartTimer); brandChartTimer = null }
  window.removeEventListener('resize', handleWindowResize)
  if (lossChart) { try { lossChart.dispose() } catch (e) { } lossChart = null }
  if (lrChart) { try { lrChart.dispose() } catch (e) { } lrChart = null }
  if (valPredChart) { try { valPredChart.dispose() } catch (e) { } valPredChart = null }
  if (trendChart) { try { trendChart.dispose() } catch (e) { } trendChart = null }
  disposeAllBrandCharts()
}

function disposeAllBrandCharts() {
  brandList.value.forEach(function (brand) {
    var el = document.getElementById('brand-chart-' + brand)
    if (el) {
      var inst = echarts.getInstanceByDom(el)
      if (inst) { try { inst.dispose() } catch (e) { } }
    }
  })
}

function initVisibleCharts() {
  lossChart = safeGetChart(lossChartRef.value, lossChart)
  if (lossChart) setupLossChart()

  if (trainMode.value === 'random') {
    lrChart = safeGetChart(lrChartRef.value, lrChart)
    if (lrChart) setupLRChart()
  }

  if (trainMode.value === 'uploaded') {
    valPredChart = safeGetChart(valPredChartRef.value, valPredChart)
    if (valPredChart) setupValPredChart()

    trendChart = safeGetChart(trendChartRef.value, trendChart)
    if (trendChart) setupTrendChart()
  }
}

// ===== 图表配置 =====
function setupLossChart() {
  if (!lossChart) return
  lossChart.setOption({
    title: { text: 'Loss 曲线', left: 16, top: 10, textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' } },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333', textStyle: { color: '#e0e0e0' } },
    legend: { data: ['Train Loss', 'Val Loss'], top: 10, right: 16, textStyle: { color: '#888', fontSize: 12 } },
    grid: { left: 60, right: 20, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } } },
    series: [
      { name: 'Train Loss', type: 'line', data: [], smooth: true, lineStyle: { color: '#4a9eff', width: 2 }, itemStyle: { color: '#4a9eff' }, showSymbol: false },
      { name: 'Val Loss', type: 'line', data: [], smooth: true, lineStyle: { color: '#f87171', width: 2 }, itemStyle: { color: '#f87171' }, showSymbol: false }
    ]
  }, true)
}

function setupLRChart() {
  if (!lrChart) return
  lrChart.setOption({
    title: { text: '学习率变化', left: 16, top: 10, textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' } },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333', textStyle: { color: '#e0e0e0' } },
    grid: { left: 80, right: 20, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#666', formatter: function (v) { return v.toExponential(1) } }, splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } } },
    series: [{ name: 'Learning Rate', type: 'line', data: [], smooth: true, lineStyle: { color: '#a78bfa', width: 2 }, itemStyle: { color: '#a78bfa' }, showSymbol: false }]
  }, true)
}

function setupValPredChart() {
  if (!valPredChart) return
  valPredChart.setOption({
    title: { text: '验证集预测 vs 实际', left: 16, top: 10, textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' } },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333', textStyle: { color: '#e0e0e0' } },
    legend: { data: ['预测值', '实际值'], top: 10, right: 16, textStyle: { color: '#888', fontSize: 12 } },
    grid: { left: 60, right: 20, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } } },
    series: [
      { name: '预测值', type: 'line', data: [], smooth: 0.3, lineStyle: { color: '#4a9eff', width: 2 }, itemStyle: { color: '#4a9eff' }, showSymbol: false },
      { name: '实际值', type: 'line', data: [], smooth: 0.3, lineStyle: { color: '#f97316', width: 1.5, type: 'dashed' }, itemStyle: { color: '#f97316' }, showSymbol: false }
    ]
  }, true)
}

function getTrendTooltipFormatter(params) {
  if (!params || !params.length) return ''
  var idx = params[0] ? params[0].dataIndex : 0
  var html = '<div style="margin-bottom:4px;color:#aaa">样本 #' + (idx + 1) + '</div>'
  params.forEach(function (p) {
    var val = Array.isArray(p.value) ? p.value[1] : p.value
    html += '<div style="display:flex;justify-content:space-between;gap:20px">'
    html += '<span>' + p.marker + ' ' + p.seriesName + '</span>'
    html += '<span style="font-weight:600">' + (val != null && !isNaN(val) ? Number(val).toFixed(6) : '-') + '</span>'
    html += '</div>'
  })
  return html
}

function setupTrendChart() {
  if (!trendChart) return
  trendChart.setOption({
    title: {
      text: 'out_moist 实际值 vs 预测值趋势',
      left: 16, top: 10,
      textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' }
    },
    tooltip: {
      trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333',
      textStyle: { color: '#e0e0e0' }, formatter: getTrendTooltipFormatter
    },
    legend: {
      data: ['实际值 (out_moist)', '预测值'],
      top: 10, right: 16, textStyle: { color: '#888', fontSize: 12 }
    },
    grid: { left: 70, right: 30, top: 50, bottom: 55 },
    xAxis: {
      type: 'value', axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#666', fontSize: 10, formatter: function (v) { return Math.round(v) } },
      name: '样本索引', nameTextStyle: { color: '#666', fontSize: 11 }, minInterval: 1
    },
    yAxis: {
      type: 'value', axisLine: { show: false }, axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } },
      name: 'out_moist', nameTextStyle: { color: '#666', fontSize: 11 }
    },
    dataZoom: [
      { type: 'slider', xAxisIndex: 0, start: 0, end: 100, height: 18, bottom: 6, borderColor: '#333', backgroundColor: 'rgba(20,20,30,0.5)', fillerColor: 'rgba(74,158,255,0.15)', handleStyle: { color: '#4a9eff' }, textStyle: { color: '#888', fontSize: 10 } },
      { type: 'inside', xAxisIndex: 0, start: 0, end: 100 }
    ],
    series: [
      { name: '实际值 (out_moist)', type: 'line', data: [], smooth: 0.3, lineStyle: { color: '#f97316', width: 2 }, itemStyle: { color: '#f97316' }, showSymbol: false, z: 2 },
      {
        name: '预测值', type: 'line', data: [], smooth: 0.3,
        lineStyle: { color: '#4a9eff', width: 2 }, itemStyle: { color: '#4a9eff' }, showSymbol: false, z: 1,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(74,158,255,0.15)' },
            { offset: 1, color: 'rgba(74,158,255,0)' }
          ])
        }
      }
    ]
  }, true)
}

// ===== 更新函数 =====
function updateCharts() {
  try {
    var logs = trainState.logs
    if (!logs || !logs.length) return
    lossChart = safeGetChart(lossChartRef.value, lossChart)
    if (lossChart && !lossChart.getOption()) setupLossChart()
    if (trainMode.value === 'random' && lrChartRef.value) {
      lrChart = safeGetChart(lrChartRef.value, lrChart)
      if (lrChart && !lrChart.getOption()) setupLRChart()
    }
    var epArr = logs.map(function (l) { return 'E' + l.epoch })
    if (lossChart) lossChart.setOption({ xAxis: { data: epArr }, series: [{ data: logs.map(function (l) { return l.loss }) }, { data: logs.map(function (l) { return l.val_loss }) }] })
    if (lrChart) lrChart.setOption({ xAxis: { data: epArr }, series: [{ data: logs.map(function (l) { return l.lr }) }] })
  } catch (e) { console.error('更新 Loss/LR 失败:', e) }
}

function updateValPredChart() {
  try {
    if (!valPredChartRef.value) return
    if (valPredChartRef.value.offsetWidth < 10 || valPredChartRef.value.offsetHeight < 10) {
      setTimeout(function () { updateValPredChart() }, 300)
      return
    }
    valPredChart = safeGetChart(valPredChartRef.value, valPredChart)
    if (!valPredChart) { setTimeout(function () { updateValPredChart() }, 300); return }
    var preds = trainState.predictions
    var actuals = trainState.actuals
    if (!preds || !preds.length || !actuals || !actuals.length) return
    var indices = preds.map(function (_, i) { return String(i + 1) })
    valPredChart.setOption({ xAxis: { data: indices }, series: [{ data: preds }, { data: actuals }] })
  } catch (e) { console.error('更新验证集图表失败:', e) }
}

function updateTrendChart() {
  try {
    var preds = trainState.trend_predictions
    var actuals = trainState.trend_actuals
    if (!actuals || !actuals.length) return
    if (!trendChartRef.value || trendChartRef.value.offsetWidth < 10 || trendChartRef.value.offsetHeight < 10) {
      setTimeout(function () { updateTrendChart() }, 300)
      return
    }
    trendChart = safeGetChart(trendChartRef.value, trendChart)
    if (!trendChart) { setTimeout(function () { updateTrendChart() }, 300); return }

    var actualData = []
    var predData = []
    for (var i = 0; i < actuals.length; i++) actualData.push([i + 1, actuals[i]])
    if (preds && preds.length > 0) {
      for (var j = 0; j < preds.length; j++) predData.push([j + 1, preds[j]])
    }

    var allY = actuals.slice()
    if (preds && preds.length > 0) allY = allY.concat(preds)
    var yMin = Math.min.apply(null, allY)
    var yMax = Math.max.apply(null, allY)
    var yRange = yMax - yMin
    var yPad = yRange * 0.1
    if (yPad < 0.001) yPad = Math.abs(yMax) * 0.1 + 0.01

    trendRange.min = yMin
    trendRange.max = yMax

    var xMax = Math.max(actuals.length, preds ? preds.length : 0)
    var displayEnd = Math.min(xMax, 150)
    var zoomEnd = (displayEnd / xMax) * 100

    trendChart.setOption({
      title: {
        text: 'out_moist 实际值 vs 预测值趋势 (Epoch ' + (trainState.trend_epoch || '-') + '/' + trainState.total_epochs + ')',
        left: 16, top: 10,
        textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' }
      },
      tooltip: {
        trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333',
        textStyle: { color: '#e0e0e0' }, formatter: getTrendTooltipFormatter
      },
      legend: {
        data: ['实际值 (out_moist)', '预测值'],
        top: 10, right: 16, textStyle: { color: '#888', fontSize: 12 }
      },
      grid: { left: 70, right: 30, top: 50, bottom: 55 },
      xAxis: {
        type: 'value', min: 1, max: xMax,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: '#666', fontSize: 10, formatter: function (v) { return Math.round(v) } },
        name: '样本索引', nameTextStyle: { color: '#666', fontSize: 11 }, minInterval: 1
      },
      yAxis: {
        type: 'value', min: yMin - yPad, max: yMax + yPad,
        axisLine: { show: false }, axisLabel: { color: '#666' },
        splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } },
        name: 'out_moist', nameTextStyle: { color: '#666', fontSize: 11 }
      },
      dataZoom: [
        { type: 'slider', xAxisIndex: 0, start: 0, end: zoomEnd, height: 18, bottom: 6, borderColor: '#333', backgroundColor: 'rgba(20,20,30,0.5)', fillerColor: 'rgba(74,158,255,0.15)', handleStyle: { color: '#4a9eff' }, textStyle: { color: '#888', fontSize: 10 } },
        { type: 'inside', xAxisIndex: 0, start: 0, end: zoomEnd }
      ],
      series: [
        { name: '实际值 (out_moist)', type: 'line', data: actualData, smooth: 0.3, lineStyle: { color: '#f97316', width: 2 }, itemStyle: { color: '#f97316' }, showSymbol: false, z: 2 },
        {
          name: '预测值', type: 'line', data: predData.length > 0 ? predData : [], smooth: 0.3,
          lineStyle: { color: '#4a9eff', width: 2 }, itemStyle: { color: '#4a9eff' }, showSymbol: false, z: 1,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(74,158,255,0.15)' },
              { offset: 1, color: 'rgba(74,158,255,0)' }
            ])
          }
        }
      ]
    }, true)
  } catch (e) { console.error('更新趋势图表失败:', e) }
}

// [修改3] 品牌图表：轮询等待 DOM 就绪
function updateBrandCharts() {
  try {
    var bp = trainState.brand_predictions
    if (!bp || typeof bp !== 'object') return
    var keys = Object.keys(bp)
    if (!keys.length) return

    // 启动轮询等待 DOM 就绪
    if (brandChartTimer) clearInterval(brandChartTimer)
    var maxAttempts = 40
    var attempt = 0
    brandChartTimer = setInterval(function () {
      attempt++
      var allReady = true
      var anyReady = false
      brandList.value.forEach(function (brand) {
        var el = document.getElementById('brand-chart-' + brand)
        if (el && el.offsetWidth >= 10 && el.offsetHeight >= 10) {
          anyReady = true
        } else {
          allReady = false
        }
      })

      if (allReady && anyReady) {
        clearInterval(brandChartTimer)
        brandChartTimer = null
        initAllBrandCharts()
      } else if (attempt >= maxAttempts) {
        clearInterval(brandChartTimer)
        brandChartTimer = null
        console.warn('品牌图表 DOM 初始化超时，尝试初始化已就绪的')
        initAllBrandCharts()
      }
    }, 200)
  } catch (e) { console.error('更新品牌图表失败:', e) }
}

function initAllBrandCharts() {
  var colors = ['#4a9eff', '#f97316', '#4ade80', '#a78bfa', '#f87171', '#facc15', '#14b8a6', '#ec4899']
  var bp = trainState.brand_predictions
  if (!bp) return

  brandList.value.forEach(function (brand, idx) {
    var data = bp[brand]
    if (!data || !data.predictions || !data.predictions.length) return

    var el = document.getElementById('brand-chart-' + brand)
    if (!el) {
      console.warn('品牌图表 DOM 未找到:', 'brand-chart-' + brand)
      return
    }
    if (el.offsetWidth < 10 || el.offsetHeight < 10) {
      console.warn('品牌图表 DOM 尺寸不足:', brand, el.offsetWidth, 'x', el.offsetHeight)
      return
    }

    createOrUpdateBrandChart(el, brand, data, colors[idx % colors.length])
  })
}

function createOrUpdateBrandChart(el, brand, data, color) {
  try {
    var existing = echarts.getInstanceByDom(el)
    if (!existing) {
      existing = echarts.init(el)
    }

    var indices = data.predictions.map(function (_, i) { return String(i + 1) })

    existing.setOption({
      title: { text: '品牌 ' + brand + ' — out_moist 预测', left: 16, top: 10, textStyle: { fontSize: 13, fontWeight: 600, color: '#e0e0e0' } },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15,15,20,0.95)',
        borderColor: '#333',
        textStyle: { color: '#e0e0e0' },
        formatter: function (params) {
          if (!params || !params.length) return ''
          var html = '<div style="margin-bottom:4px;color:#aaa">样本 #' + (params[0].dataIndex + 1) + '</div>'
          params.forEach(function (p) {
            var val = Array.isArray(p.value) ? p.value[1] : p.value
            html += '<div>' + p.marker + ' ' + p.seriesName + ': <b>' + (val != null && !isNaN(val) ? Number(val).toFixed(6) : '-') + '</b></div>'
          })
          return html
        }
      },
      legend: { data: ['预测值', '实际值'], top: 10, right: 16, textStyle: { color: '#888', fontSize: 11 } },
      grid: { left: 55, right: 20, top: 45, bottom: 35 },
      xAxis: { type: 'category', data: indices, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#666', fontSize: 10 } },
      yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } } },
      series: [
        { name: '预测值', type: 'line', data: data.predictions, smooth: 0.3, lineStyle: { color: color, width: 2 }, itemStyle: { color: color }, showSymbol: false },
        { name: '实际值', type: 'line', data: data.actuals, smooth: 0.3, lineStyle: { color: '#f97316', width: 1.5, type: 'dashed' }, itemStyle: { color: '#f97316' }, showSymbol: false }
      ]
    }, true)

    existing.resize()
  } catch (e) { console.error('品牌图表创建失败:', brand, e) }
}

// ===== Watch（防抖） =====
var chartUpdateTimer = null
watch(function () { return trainState.logs.length }, function () {
  if (chartUpdateTimer) clearTimeout(chartUpdateTimer)
  chartUpdateTimer = setTimeout(function () {
    nextTick(function () {
      updateCharts()
      if (logBodyRef.value) logBodyRef.value.scrollTop = logBodyRef.value.scrollHeight
    })
  }, 100)
})

var trendUpdateTimer = null
watch(function () { return trainState.trend_epoch }, function () {
  if (trendUpdateTimer) clearTimeout(trendUpdateTimer)
  trendUpdateTimer = setTimeout(function () { nextTick(updateTrendChart) }, 200)
})

var valPredTimer = null
watch(function () { return trainState.predictions.length }, function () {
  if (valPredTimer) clearTimeout(valPredTimer)
  valPredTimer = setTimeout(function () { nextTick(updateValPredChart) }, 200)
})

// [修改4] brand_predictions watcher：只触发 updateBrandCharts，不再手动管理 brandList
var brandUpdateTimer = null
watch(function () { return trainState.brand_predictions }, function () {
  if (brandUpdateTimer) clearTimeout(brandUpdateTimer)
  brandUpdateTimer = setTimeout(function () { nextTick(updateBrandCharts) }, 250)
}, { deep: true })

// 模型类型变化时重新加载已保存模型列表
watch(function () { return selectedModel.value }, function () {
  if (modelSource.value === 'existing') {
    loadSavedModels()
    selectedBaseModelId.value = null
  }
})

// ===== 轮询 =====
async function checkAndStartPolling() {
  try {
    var res = await getTrainStatus()
    var data = res.data || res
    if (data && data.is_training) {
      mergeTrainState(data)
      isTraining.value = true
      startPolling()
    }
  } catch (e) { }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async function () {
    try {
      var res = await getTrainStatus()
      var data = res.data || res
      if (data) {
        mergeTrainState(data)
        isTraining.value = !!data.is_training
        if (data.done || !data.is_training) {
          isTraining.value = false
          stopPolling()
          if (data.message) ElMessage.success(data.message)
          if (data.error) ElMessage.error(data.error)
        }
      }
    } catch (e) { }
  }, 500)
}

function startUploadPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async function () {
    try {
      var res = await getTrainStatus()
      var data = res.data || res
      if (data) mergeTrainState(data)
    } catch (e) { }
  }, 500)
}

function mergeTrainState(d) {
  if (!d) return
  if (d.epoch != null) trainState.epoch = d.epoch
  if (d.total_epochs != null) trainState.total_epochs = d.total_epochs
  if (d.loss != null) trainState.loss = d.loss
  if (d.val_loss != null) trainState.val_loss = d.val_loss
  if (d.best_val_loss != null) trainState.best_val_loss = d.best_val_loss
  if (d.progress != null) trainState.progress = d.progress
  if (d.elapsed != null) trainState.elapsed = d.elapsed
  if (d.done != null) trainState.done = d.done
  if (d.message != null) trainState.message = d.message
  if (d.logs && Array.isArray(d.logs)) trainState.logs = d.logs
  if (d.loss_history && Array.isArray(d.loss_history)) trainState.loss_history = d.loss_history
  if (d.val_loss_history && Array.isArray(d.val_loss_history)) trainState.val_loss_history = d.val_loss_history
  if (d.predictions && Array.isArray(d.predictions)) trainState.predictions = d.predictions
  if (d.actuals && Array.isArray(d.actuals)) trainState.actuals = d.actuals
  if (d.brand_predictions && typeof d.brand_predictions === 'object') trainState.brand_predictions = d.brand_predictions
  if (d.trend_predictions && Array.isArray(d.trend_predictions)) trainState.trend_predictions = d.trend_predictions
  if (d.trend_actuals && Array.isArray(d.trend_actuals)) trainState.trend_actuals = d.trend_actuals
  if (d.trend_epoch != null) trainState.trend_epoch = d.trend_epoch

  if (d.done || d.error) {
    isTraining.value = false
    stopPolling()
    if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null }
    if (d.message) ElMessage.success(d.message)
    if (d.error) ElMessage.error(d.error)
  }
}

// ===== 训练控制 =====
async function handleStartTrain() {
  trainState.logs = []
  trainState.loss_history = []
  trainState.val_loss_history = []
  trainState.predictions = []
  trainState.actuals = []
  trainState.brand_predictions = {}
  trainState.trend_predictions = []
  trainState.trend_actuals = []
  trainState.trend_epoch = 0
  trainState.epoch = 0
  trainState.done = false
  trainState.message = ''
  trendRange.min = null
  trendRange.max = null

  // [修改5] 清理品牌图表定时器和实例
  if (brandChartTimer) { clearInterval(brandChartTimer); brandChartTimer = null }
  disposeAllBrandCharts()

  stopPolling()
  if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null }

  if (lossChart) { try { lossChart.dispose() } catch (e) { } lossChart = null }
  if (lrChart) { try { lrChart.dispose() } catch (e) { } lrChart = null }
  if (valPredChart) { try { valPredChart.dispose() } catch (e) { } valPredChart = null }
  if (trendChart) { try { trendChart.dispose() } catch (e) { } trendChart = null }

  nextTick(function () {
    setTimeout(function () {
      try { initVisibleCharts() } catch (e) { console.error('重新初始化图表失败:', e) }
    }, 300)
  })

  if (trainMode.value === 'uploaded') {
    if (!selectedFileIds.value.length) { ElMessage.warning('请选择训练数据'); return }
    if (modelSource.value === 'existing' && !selectedBaseModelId.value) { ElMessage.warning('请选择一个基础模型'); return }
    await handleStartUploadTrain()
  } else {
    if (modelSource.value === 'existing' && !selectedBaseModelId.value) { ElMessage.warning('请选择一个基础模型'); return }
    await handleStartRandomTrain()
  }
}

async function handleStartRandomTrain() {
  try {
    var params = { model_key: selectedModel.value, epochs: epochs.value, lr: learningRate.value, batch_size: 32 }
    if (modelSource.value === 'existing' && selectedBaseModelId.value) {
      params.base_model_id = selectedBaseModelId.value
    }
    await startTrain(params)
    ElMessage.success('训练已启动')
    isTraining.value = true
    trainState.total_epochs = epochs.value
    startPolling()
    startSSEStream()
  } catch (e) { ElMessage.error((e.response && e.response.data && e.response.data.detail) || '启动失败') }
}

async function handleStartUploadTrain() {
  try {
    var params = {
      model_key: selectedModel.value,
      file_ids: selectedFileIds.value.join(','),
      epochs: epochs.value, lr: learningRate.value, batch_size: 32
    }
    if (modelSource.value === 'existing' && selectedBaseModelId.value) {
      params.base_model_id = selectedBaseModelId.value
    }
    await startTrainWithUpload(params)
    ElMessage.success('训练已启动')
    isTraining.value = true
    trainState.total_epochs = epochs.value
    startUploadPolling()
    startUploadSSE()
  } catch (e) {
    isTraining.value = false
    ElMessage.error((e.response && e.response.data && e.response.data.detail) || '启动训练失败')
  }
}

function getApiBase() {
  var host = window.location.hostname || 'localhost'
  return 'http://' + host + ':8000'
}

function startSSEStream() {
  if (sseSource) { try { sseSource.close() } catch (e) { } }
  try {
    var base = getApiBase()
    var url = base + '/model/train/stream?model_key=' + selectedModel.value + '&epochs=' + epochs.value + '&lr=' + learningRate.value
    sseSource = new EventSource(url)
    sseSource.onmessage = function (event) {
      try {
        var data = JSON.parse(event.data)
        mergeTrainState(data)
        isTraining.value = !!data.is_training
        if (data.done) {
          try { sseSource.close() } catch (e) { }
          sseSource = null
          isTraining.value = false
          stopPolling()
          if (data.error) ElMessage.error(data.message)
          else if (data.message) ElMessage.success(data.message)
        }
      } catch (e) { console.warn('SSE 解析失败:', e) }
    }
    sseSource.onerror = function () { if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null } }
  } catch (e) { console.error('SSE 连接失败:', e) }
}

function startUploadSSE() {
  if (sseSource) { try { sseSource.close() } catch (e) { } }
  try {
    var base = getApiBase()
    sseSource = new EventSource(base + '/model/train/upload/stream')
    sseSource.onmessage = function (event) { try { mergeTrainState(JSON.parse(event.data)) } catch (e) { } }
    sseSource.onerror = function () { if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null } }
  } catch (e) { console.error('上传 SSE 连接失败:', e) }
}

function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

async function handleStopTrain() {
  try {
    if (trainMode.value === 'uploaded') await stopUploadTrain(selectedModel.value)
    else await stopTrain()
    stopPolling()
    if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null }
    isTraining.value = false
    ElMessage.info('训练已停止')
  } catch (e) { ElMessage.error('停止失败') }
}

function handleModeChange() {
  stopPolling()
  if (sseSource) { try { sseSource.close() } catch (e) { } sseSource = null }
  if (brandChartTimer) { clearInterval(brandChartTimer); brandChartTimer = null }
  isTraining.value = false
  trainState.logs = []
  trainState.predictions = []
  trainState.actuals = []
  trainState.brand_predictions = {}
  trainState.trend_predictions = []
  trainState.trend_actuals = []
  trainState.trend_epoch = 0
  trainState.epoch = 0
  trainState.done = false
  trendRange.min = null
  trendRange.max = null

  disposeAllBrandCharts()

  if (lossChart) { try { lossChart.dispose() } catch (e) { } lossChart = null }
  if (lrChart) { try { lrChart.dispose() } catch (e) { } lrChart = null }
  if (valPredChart) { try { valPredChart.dispose() } catch (e) { } valPredChart = null }
  if (trendChart) { try { trendChart.dispose() } catch (e) { } trendChart = null }

  nextTick(function () {
    setTimeout(function () {
      try { initVisibleCharts() } catch (e) { console.error(e) }
    }, 300)
  })
}

function clearLogs() { trainState.logs = [] }

// ===== 模型版本管理 =====
async function loadSavedModels() {
  loadingSavedModels.value = true
  try {
    var res = await getSavedModels()
    savedModels.value = res.data || []
  } catch (e) { console.error('加载已保存模型失败:', e) }
  finally { loadingSavedModels.value = false }
}

function handleSourceChange() {
  if (modelSource.value === 'existing') {
    selectedBaseModelId.value = null
    loadSavedModels()
  }
}

// ===== 上传 =====
function handleFileChange(file, fl) { fileList.value = fl }
function handleRemove(file, fl) { fileList.value = fl }

async function loadUploadedFiles() {
  try { var res = await getUploadedFiles(); uploadedFiles.value = res.data || [] } catch (e) { console.error(e) }
}

async function handleUploadAll() {
  uploading.value = true
  var ok = 0
  for (var i = 0; i < fileList.value.length; i++) {
    var f = fileList.value[i]
    try { await uploadFile(f.raw); ok++ }
    catch (e) { ElMessage.error(f.name + ' 失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message)) }
  }
  if (ok > 0) ElMessage.success(ok + ' 个文件上传成功')
  fileList.value = []
  uploading.value = false
  await loadUploadedFiles()
}

async function previewData(row) {
  try {
    var res = await getUploadPreview(row.file_id)
    previewRows.value = res.data || []
    if (previewRows.value.length > 0) {
      previewCols.value = previewRows.value[0].map(function (_, i) { return '列' + (i + 1) })
      previewDisplay.value = previewRows.value.map(function (r) {
        var obj = {}
        r.forEach(function (v, i) { obj['列' + (i + 1)] = v })
        return obj
      })
    }
  } catch (e) { ElMessage.error('预览失败') }
}

async function handleDeleteFile(fileId) {
  try {
    await ElMessageBox.confirm('确定删除？', '提示', { type: 'warning' })
    await deleteUploadedFile(fileId)
    ElMessage.success('删除成功')
    previewRows.value = []
    await loadUploadedFiles()
  } catch (e) { }
}

async function handleDownloadTemplate(fmt) {
  try { await downloadTemplate(fmt); ElMessage.success('模板下载成功') } catch (e) { ElMessage.error('下载失败') }
}
</script>

<style scoped>
.training-page {
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.selector-label {
  font-size: 14px;
  color: var(--text-muted);
  white-space: nowrap;
}

.base-model-section {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  padding: 16px 20px;
}

.base-model-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.base-model-hint {
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.config-label {
  font-size: 14px;
  color: var(--text-muted);
  flex-shrink: nowrap;
}

.upload-section {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  padding: 24px;
}

.upload-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.upload-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.template-actions {
  display: flex;
  gap: 8px;
}

.template-hint {
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.upload-area {
  padding: 20px;
  text-align: center;
}

.upload-icon {
  font-size: 36px;
  color: var(--text-muted);
}

.upload-text {
  font-size: 14px;
  color: var(--text-primary);
  margin-top: 8px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.upload-actions {
  margin-top: 12px;
}

.uploaded-list {
  margin-top: 16px;
}

.preview-table {
  margin-top: 16px;
}

.preview-table h4 {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.upload-train-config {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-secondary);
}

.config-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-label {
  font-size: 14px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.train-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.control-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-left h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-right: 8px;
  white-space: nowrap;
}

.param-label {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
}

.progress-section {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.waiting-msg {
  font-size: 14px;
  color: var(--text-muted);
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1 }
  50% { opacity: 0.4 }
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.progress-details {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-muted);
}

.progress-details b {
  color: var(--text-primary);
  font-family: 'DM Mono', monospace;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  padding: 12px;
}

.chart-container {
  width: 100%;
  height: 320px;
}

.trend-section {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  padding: 24px;
  border-left: 3px solid var(--accent);
}

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.trend-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.trend-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.trend-brand-name {
  font-size: 13px;
  color: var(--accent);
  background: var(--accent-bg-light);
  padding: 6px 12px;
  border-radius: 999px;
  white-space: nowrap;
}

.trend-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.trend-epoch {
  font-size: 13px;
  color: var(--accent);
  font-family: 'DM Mono', monospace;
  background: var(--accent-bg-light);
  padding: 4px 12px;
  border-radius: 6px;
}

.trend-range {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'DM Mono', monospace;
  background: var(--bg-secondary);
  padding: 3px 10px;
  border-radius: 6px;
}

.trend-chart-wrap {
  background: var(--bg-primary);
  border-radius: 12px;
  padding: 8px;
}

.trend-chart-container {
  width: 100%;
  height: 380px;
}

/* ===== 品牌图表 ===== */
.brand-charts-section {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  padding: 24px;
}

.brand-charts-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.brand-charts-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.brand-chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.brand-chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  padding-left: 8px;
}

.brand-chart-container {
  width: 100%;
  height: 320px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  overflow: hidden;
}

.brand-empty {
  width: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 14px;
  background: var(--bg-primary);
  border: 1px dashed var(--border-secondary);
  border-radius: 12px;
  padding: 24px;
}

.log-section {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  overflow: hidden;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-secondary);
}

.log-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.log-body {
  height: 240px;
  overflow-y: auto;
  padding: 8px 20px;
  font-family: 'DM Mono', 'Consolas', monospace;
  font-size: 12px;
  background: var(--bg-primary);
}

.log-body::-webkit-scrollbar {
  width: 6px;
}

.log-body::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 3px;
}

.log-line {
  display: flex;
  gap: 16px;
  padding: 3px 0;
  border-bottom: 1px solid var(--bg-card);
  line-height: 1.8;
}

.log-epoch {
  color: var(--accent);
  min-width: 80px;
}

.log-loss {
  color: var(--text-primary);
  min-width: 140px;
}

.log-val {
  color: var(--danger);
  min-width: 140px;
}

.log-lr {
  color: var(--info);
  min-width: 100px;
}

.log-time {
  color: var(--text-muted);
}

.log-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-disabled);
  font-family: inherit;
}
</style>
