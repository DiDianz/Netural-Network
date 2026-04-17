<!-- src/views/prediction/realtime/index.vue — 新增 PLC 数据源 -->
<template>
  <div class="prediction-page">
    <!-- 模型选择 -->
    <div class="model-selector">
      <span class="selector-label">模型类型:</span>
      <el-radio-group v-model="filterModelType" size="default" @change="handleTypeFilterChange">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="lstm">LSTM</el-radio-button>
        <el-radio-button value="gru">GRU</el-radio-button>
        <el-radio-button value="transformer">Transformer</el-radio-button>
      </el-radio-group>

      <span class="selector-label" style="margin-left: 20px">选择模型:</span>
      <el-select
        v-model="selectedSavedModelId"
        placeholder="请选择已保存的模型"
        size="default"
        style="width: 360px"
        filterable
        :loading="loadingSavedModels"
        @change="handleSavedModelChange"
      >
        <el-option
          v-for="m in filteredSavedModels"
          :key="m.model_id"
          :label="m.name || m.display_name"
          :value="m.model_id"
        >
          <div class="model-option">
            <span class="model-option-name">{{ m.name || m.display_name }}</span>
            <div class="model-option-meta">
              <el-tag :type="modelTagType(m.model_key)" size="small">{{ m.model_key.toUpperCase() }}</el-tag>
              <span class="model-option-loss">Loss: {{ m.best_val_loss }}</span>
              <span class="model-option-time">{{ formatTime(m.trained_at) }}</span>
            </div>
          </div>
        </el-option>
      </el-select>

      <el-button
        size="default"
        :icon="Refresh"
        circle
        style="margin-left: 8px"
        @click="loadSavedModels"
        :loading="loadingSavedModels"
      />
    </div>

    <!-- 数据源选择 -->
    <div class="data-source-selector">
      <span class="selector-label">数据源:</span>
      <el-radio-group v-model="dataSource" size="default" @change="handleDataSourceChange">
        <el-radio-button value="random">随机模拟数据</el-radio-button>
        <el-radio-button value="uploaded" :disabled="!hasUploadedFiles">上传数据</el-radio-button>
        <el-radio-button value="plc" :disabled="!hasPlcConnected">PLC 实时数据</el-radio-button>
      </el-radio-group>

      <el-tag v-if="dataSource === 'uploaded'" type="warning" size="small" style="margin-left: 12px">
        预测值 vs 实际值对比
      </el-tag>
      <el-tag v-if="!hasUploadedFiles && dataSource !== 'plc'" type="info" size="small" style="margin-left: 12px">
        请先在模型管理页上传数据
      </el-tag>

      <!-- PLC 数据源配置 -->
      <template v-if="dataSource === 'plc'">
        <el-select
          v-model="selectedPlcDevice"
          placeholder="选择 PLC 设备"
          size="default"
          style="margin-left: 12px; width: 200px"
          @change="handlePlcDeviceChange"
        >
          <el-option
            v-for="d in plcDevices"
            :key="d.id"
            :label="d.name"
            :value="d.id"
            :disabled="d.status !== 'connected'"
          >
            <span>{{ d.name }}</span>
            <el-tag
              :type="d.status === 'connected' ? 'success' : 'info'"
              size="small"
              style="margin-left: 8px"
            >
              {{ d.status === 'connected' ? '已连接' : '未连接' }}
            </el-tag>
          </el-option>
        </el-select>

        <el-select
          v-model="selectedPlcPoints"
          multiple
          placeholder="选择 DB 点位"
          size="default"
          style="margin-left: 8px; width: 320px"
          collapse-tags
          collapse-tags-tooltip
          :disabled="!selectedPlcDevice"
        >
          <el-option
            v-for="p in plcPoints"
            :key="p.id"
            :label="`${p.point_name} (DB${p.db_number}.${p.start_address})`"
            :value="p.id"
          />
        </el-select>

        <el-button
          type="primary"
          size="default"
          style="margin-left: 8px"
          @click="handleRefreshPlcPoints"
          :disabled="!selectedPlcDevice"
          :icon="Refresh"
          circle
        />
      </template>
    </div>

    <!-- 图表区域 -->
    <div class="chart-section">
      <PredictionChart :chart-data="chartData" />
    </div>

    <!-- PLC 实时数据面板 (数据源为 PLC 时显示) -->
    <div v-if="dataSource === 'plc'" class="plc-live-panel">
      <div class="panel-title">
        <el-icon><Monitor /></el-icon>
        PLC 实时数据
        <el-tag
          :type="plcStreamState === 'open' ? 'success' : 'info'"
          size="small"
          effect="dark"
          style="margin-left: 8px"
        >
          {{ plcStreamState === 'open' ? '接收中' : '未连接' }}
        </el-tag>
      </div>
      <div class="plc-values-grid">
        <div
          v-for="item in plcLiveValues"
          :key="item.point_id"
          class="plc-value-card"
        >
          <div class="pv-name">{{ item.point_name }}</div>
          <div class="pv-value" :class="{ 'pv-error': !item.success }">
            {{ item.success ? item.value : 'ERR' }}
          </div>
        </div>
        <div v-if="plcLiveValues.length === 0" class="pv-empty">
          暂无数据 — 请先选择设备和点位
        </div>
      </div>
    </div>

    <!-- 控制面板 -->
    <div class="side-panels">
      <RealtimePanel
        :state="store.state"
        :latest-prediction="latestPrediction"
        :connection-state="connectionState"
      />
      <ControlPanel
        :connection-state="connectionState"
        :interval="interval"
        @start="handleStart"
        @stop="handleStop"
        @clear="handleClear"
        @update:interval="interval = $event"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Monitor } from '@element-plus/icons-vue'
import PredictionChart from '../../../components/PredictionChart.vue'
import RealtimePanel from '../../../components/RealtimePanel.vue'
import ControlPanel from '../../../components/ControlPanel.vue'
import { useSSE } from '../../../composables/useSSE'
import { usePredictionStore } from '../../../composables/usePredictionStore'
import { getSavedModels, loadSavedModel, switchModel, getUploadedFiles } from '../../../api/model'
import { getPlcDeviceList, getPlcPointList, readPlcBatch } from '../../../api/plc'

const store = usePredictionStore()
const { chartData, latestPrediction } = store
const { connectionState, startStream, stopStream } = useSSE()
const interval = ref(1.0)

// 已保存模型相关状态
const savedModels = ref([])
const filterModelType = ref('')
const selectedSavedModelId = ref(null)
const loadingSavedModels = ref(false)
const currentModelKey = ref('lstm')

const dataSource = ref('random')
const hasUploadedFiles = ref(false)

// 按类型筛选后的已保存模型列表
const filteredSavedModels = computed(() => {
  if (!filterModelType.value) return savedModels.value
  return savedModels.value.filter(m => m.model_key === filterModelType.value)
})

// PLC 相关状态
const plcDevices = ref([])
const plcPoints = ref([])
const selectedPlcDevice = ref(null)
const selectedPlcPoints = ref([])
const plcLiveValues = ref([])
const plcStreamState = ref('closed')
let plcStreamEventSource = null

const hasPlcConnected = computed(() =>
  plcDevices.value.some(d => d.status === 'connected')
)

onMounted(async () => {
  await loadSavedModels()
  checkUploadedFiles()
  await loadPlcDevices()
})

onUnmounted(() => {
  stopStream()
  stopPlcStream()
})

async function loadSavedModels() {
  loadingSavedModels.value = true
  try {
    const res = await getSavedModels()
    savedModels.value = res.data || []
    // 如果当前没有选中模型且有数据，默认选第一个
    if (!selectedSavedModelId.value && savedModels.value.length > 0) {
      const first = filteredSavedModels.value[0] || savedModels.value[0]
      selectedSavedModelId.value = first.model_id
      currentModelKey.value = first.model_key
    }
  } catch (e) {
    console.error('获取已保存模型列表失败:', e)
  } finally {
    loadingSavedModels.value = false
  }
}

function handleTypeFilterChange() {
  // 切换类型筛选后，如果当前选中的模型不在筛选结果中，自动选第一个
  const match = filteredSavedModels.value.find(m => m.model_id === selectedSavedModelId.value)
  if (!match && filteredSavedModels.value.length > 0) {
    selectedSavedModelId.value = filteredSavedModels.value[0].model_id
    currentModelKey.value = filteredSavedModels.value[0].model_key
  }
}

async function handleSavedModelChange(modelId) {
  const model = savedModels.value.find(m => m.model_id === modelId)
  if (!model) return
  try {
    // 先加载模型，再切换
    await loadSavedModel(modelId)
    await switchModel(model.model_key)
    currentModelKey.value = model.model_key
    ElMessage.success(`已加载模型: ${model.name || model.display_name} (${model.model_key.toUpperCase()})`)
    // 如果正在运行预测流，重启
    if (connectionState.value === 'open') {
      stopStream()
      setTimeout(() => {
        startStream(interval.value, model.model_key, dataSource.value === 'uploaded')
      }, 500)
    }
  } catch (e) {
    ElMessage.error('加载模型失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message))
  }
}

function modelTagType(key) {
  return { lstm: '', gru: 'success', transformer: 'warning' }[key] || 'info'
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 16)
}

async function checkUploadedFiles() {
  try {
    const res = await getUploadedFiles()
    hasUploadedFiles.value = (res.data || []).length > 0
  } catch (e) { /* ignore */ }
}

// ========== PLC 相关 ==========
async function loadPlcDevices() {
  try {
    const res = await getPlcDeviceList()
    plcDevices.value = res.data || []
  } catch (e) { /* ignore */ }
}

async function handlePlcDeviceChange(deviceId) {
  selectedPlcPoints.value = []
  plcLiveValues.value = []
  if (!deviceId) {
    plcPoints.value = []
    return
  }
  try {
    const res = await getPlcPointList({ device_id: deviceId, is_active: 1 })
    plcPoints.value = res.data || []
  } catch (e) {
    console.error('加载点位失败:', e)
  }
}

async function handleRefreshPlcPoints() {
  if (selectedPlcDevice.value) {
    await handlePlcDeviceChange(selectedPlcDevice.value)
    ElMessage.success('已刷新点位列表')
  }
}

function startPlcStream() {
  stopPlcStream()
  if (!selectedPlcDevice.value || selectedPlcPoints.value.length === 0) return

  const token = localStorage.getItem('token') || ''
  const pointIds = selectedPlcPoints.value.join(',')
  const url = `http://localhost:8000/plc/read/stream?device_id=${selectedPlcDevice.value}&interval=${interval.value}&point_ids=${pointIds}`

  plcStreamEventSource = new EventSource(url)
  plcStreamState.value = 'open'

  plcStreamEventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.error) {
        ElMessage.error(`PLC 读取错误: ${data.error}`)
        stopPlcStream()
        return
      }
      if (data.points) {
        plcLiveValues.value = data.points
      }
    } catch (e) { /* ignore parse errors */ }
  }

  plcStreamEventSource.onerror = () => {
    plcStreamState.value = 'closed'
    stopPlcStream()
  }
}

function stopPlcStream() {
  if (plcStreamEventSource) {
    plcStreamEventSource.close()
    plcStreamEventSource = null
  }
  plcStreamState.value = 'closed'
}

// ========== 事件处理 ==========
function handleDataSourceChange() {
  stopStream()
  stopPlcStream()

  if (dataSource.value === 'plc') {
    // PLC 模式：自动加载设备列表
    loadPlcDevices()
  } else {
    setTimeout(() => handleStart(), 300)
  }
}

function handleStart() {
  if (dataSource.value === 'plc') {
    if (!selectedPlcDevice.value) {
      ElMessage.warning('请先选择 PLC 设备')
      return
    }
    if (selectedPlcPoints.value.length === 0) {
      ElMessage.warning('请至少选择一个 DB 点位')
      return
    }
    startPlcStream()
    // 同时启动预测流
    startStream(interval.value, currentModelKey.value, false)
  } else {
    startStream(interval.value, currentModelKey.value, dataSource.value === 'uploaded')
  }
}

function handleStop() {
  stopStream()
  stopPlcStream()
}

function handleClear() {
  store.clearData()
  plcLiveValues.value = []
}
</script>

<style scoped>
.prediction-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-selector,
.data-source-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
  flex-wrap: wrap;
}

.selector-label {
  font-size: 14px;
  color: #888;
  white-space: nowrap;
}

/* 已保存模型下拉选项 */
.model-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-option-name {
  font-size: 13px;
  font-weight: 500;
}

.model-option-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #999;
}

.model-option-loss {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: #f56c6c;
}

.model-option-time {
  color: #666;
}

.chart-section {
  width: 100%;
}

/* PLC 实时数据面板 */
.plc-live-panel {
  background: var(--bg-card);
  border: 1px solid #1e1e2e;
  border-radius: 12px;
  padding: 16px 20px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 14px;
  color: #ccc;
}

.plc-values-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.plc-value-card {
  background: #111118;
  border: 1px solid #1e1e2e;
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
}

.pv-name {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.pv-value {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #67c23a;
}

.pv-value.pv-error {
  color: #f56c6c;
  font-size: 14px;
}

.pv-empty {
  grid-column: 1 / -1;
  text-align: center;
  color: #666;
  padding: 20px;
}

.side-panels {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
}
</style>