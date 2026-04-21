<!-- src/views/prediction/realtime/index.vue -->
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
        <el-radio-button value="plc">PLC 实时数据</el-radio-button>
      </el-radio-group>

      <el-tag v-if="dataSource === 'plc' && selectedPlcDevice" type="success" size="small" style="margin-left: 12px">
        {{ selectedPlcDeviceName }} — {{ selectedPlcPoints.length }} 个点位
      </el-tag>
    </div>

    <!-- PLC 设备选择弹窗 -->
    <el-dialog
      v-model="plcDialogVisible"
      title="选择 PLC 设备与点位"
      width="560px"
      :close-on-click-modal="false"
    >
      <div class="plc-dialog-content">
        <div class="plc-dialog-row">
          <span class="plc-dialog-label">PLC 设备:</span>
          <el-select
            v-model="dialogPlcDevice"
            placeholder="请选择 PLC 设备"
            style="flex: 1"
            @change="handleDialogDeviceChange"
            :loading="loadingPlcDevices"
          >
            <el-option
              v-for="d in plcDevices"
              :key="d.id"
              :label="d.name"
              :value="d.id"
            >
              <div class="plc-device-option">
                <span>{{ d.name }}</span>
                <el-tag
                  :type="d.status === 'connected' ? 'success' : 'info'"
                  size="small"
                >
                  {{ d.status === 'connected' ? '已连接' : '未连接' }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
          <el-button
            :icon="Refresh"
            circle
            size="default"
            @click="loadPlcDevices"
            :loading="loadingPlcDevices"
            style="margin-left: 8px"
          />
        </div>

        <div class="plc-dialog-row" style="margin-top: 16px">
          <span class="plc-dialog-label">DB 点位:</span>
          <el-select
            v-model="dialogPlcPoints"
            multiple
            placeholder="请先选择设备"
            style="flex: 1"
            collapse-tags
            collapse-tags-tooltip
            :disabled="!dialogPlcDevice"
            :loading="loadingPlcPoints"
          >
            <el-option
              v-for="p in plcPoints"
              :key="p.id"
              :label="`${p.point_name} (DB${p.db_number}.${p.start_address})`"
              :value="p.id"
            />
          </el-select>
        </div>

        <div v-if="dialogPlcDevice && plcPoints.length === 0 && !loadingPlcPoints" class="plc-dialog-empty">
          该设备下暂无可用点位
        </div>
      </div>

      <template #footer>
        <el-button @click="handlePlcDialogCancel">取消</el-button>
        <el-button
          type="primary"
          @click="handlePlcDialogConfirm"
          :disabled="!dialogPlcDevice || dialogPlcPoints.length === 0"
        >
          确认选择
        </el-button>
      </template>
    </el-dialog>

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

      <!-- 数据源信息 -->
      <div class="plc-source-info">
        <div class="plc-info-item">
          <span class="plc-info-label">设备</span>
          <span class="plc-info-value">{{ selectedPlcDeviceName || '未选择' }}</span>
        </div>
        <div class="plc-info-item">
          <span class="plc-info-label">设备IP</span>
          <span class="plc-info-value mono">{{ selectedPlcDeviceInfo?.ip || '-' }}:{{ selectedPlcDeviceInfo?.port || '-' }}</span>
        </div>
        <div class="plc-info-item">
          <span class="plc-info-label">模型</span>
          <span class="plc-info-value">
            <el-tag :type="modelTagType(currentModelKey)" size="small">{{ currentModelKey.toUpperCase() }}</el-tag>
          </span>
        </div>
        <div class="plc-info-item">
          <span class="plc-info-label">点位</span>
          <span class="plc-info-value">
            <el-tag type="info" size="small" v-for="pid in selectedPlcPoints" :key="pid">
              {{ getPointLabel(pid) }}
            </el-tag>
            <span v-if="selectedPlcPoints.length === 0" style="color: var(--text-muted)">未选择</span>
          </span>
        </div>
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
        <div v-if="!selectedPlcDevice" class="pv-empty">
          暂无数据 — 请先选择设备和点位
        </div>
        <div v-else-if="plcStreamState === 'open'" class="pv-empty">
          已连接设备，等待数据接收中...
        </div>
        <div v-else class="pv-empty">
          设备已配置 — 等待设备连接
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
import { getSavedModels, loadSavedModel, switchModel } from '../../../api/model'
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

// PLC 弹窗状态
const plcDialogVisible = ref(false)
const dialogPlcDevice = ref(null)
const dialogPlcPoints = ref([])
const loadingPlcDevices = ref(false)
const loadingPlcPoints = ref(false)

// 当前选中设备名称（用于数据源标签显示）
const selectedPlcDeviceName = computed(() => {
  const d = plcDevices.value.find(d => d.id === selectedPlcDevice.value)
  return d ? d.name : ''
})

// 当前选中设备完整信息
const selectedPlcDeviceInfo = computed(() => {
  return plcDevices.value.find(d => d.id === selectedPlcDevice.value) || null
})

// 点位ID转名称标签
function getPointLabel(pointId) {
  const p = plcPoints.value.find(p => p.id === pointId)
  if (!p) return `#${pointId}`
  return `${p.point_name} (DB${p.db_number}.${p.start_address})`
}

const hasPlcConnected = computed(() =>
  plcDevices.value.some(d => d.status === 'connected')
)

onMounted(async () => {
  await loadSavedModels()
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
        startStream(interval.value, model.model_key)
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

// ========== PLC 相关 ==========
async function loadPlcDevices() {
  loadingPlcDevices.value = true
  try {
    const res = await getPlcDeviceList()
    plcDevices.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingPlcDevices.value = false }
}

async function handleDialogDeviceChange(deviceId) {
  dialogPlcPoints.value = []
  plcPoints.value = []
  if (!deviceId) return
  loadingPlcPoints.value = true
  try {
    const res = await getPlcPointList({ device_id: deviceId, is_active: 1 })
    plcPoints.value = res.data || []
  } catch (e) {
    console.error('加载点位失败:', e)
  } finally { loadingPlcPoints.value = false }
}

// 弹窗确认
function handlePlcDialogConfirm() {
  selectedPlcDevice.value = dialogPlcDevice.value
  selectedPlcPoints.value = [...dialogPlcPoints.value]
  plcDialogVisible.value = false
  ElMessage.success('PLC 设备已配置，点击开始按钮启动预测')
}

// 弹窗取消 — 如果之前没选过设备，回退到随机模拟
function handlePlcDialogCancel() {
  plcDialogVisible.value = false
  if (!selectedPlcDevice.value) {
    dataSource.value = 'random'
  }
  // 恢复弹窗状态为已确认的值
  dialogPlcDevice.value = selectedPlcDevice.value
  dialogPlcPoints.value = [...selectedPlcPoints.value]
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
    // 打开 PLC 设备选择弹窗
    loadPlcDevices()
    dialogPlcDevice.value = selectedPlcDevice.value
    dialogPlcPoints.value = [...selectedPlcPoints.value]
    // 如果弹窗中选了设备，加载点位
    if (dialogPlcDevice.value) {
      handleDialogDeviceChange(dialogPlcDevice.value)
    }
    plcDialogVisible.value = true
  }
}

async function handleStart() {
  if (!selectedSavedModelId.value) {
    ElMessage.warning('请先选择一个已保存的模型')
    return
  }
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
  }

  // 确保加载并切换到选中的模型
  try {
    await loadSavedModel(selectedSavedModelId.value)
    const model = savedModels.value.find(m => m.model_id === selectedSavedModelId.value)
    if (model) {
      await switchModel(model.model_key)
      currentModelKey.value = model.model_key
    }
  } catch (e) {
    ElMessage.error('加载模型失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message))
    return
  }

  // 使用当前选中的模型类型进行推理
  startStream(interval.value, currentModelKey.value)
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
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  flex-wrap: wrap;
}

.selector-label {
  font-size: 14px;
  color: var(--text-muted);
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
  color: var(--text-secondary);
}

.model-option-loss {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--danger);
}

.model-option-time {
  color: var(--text-muted);
}

/* PLC 弹窗 */
.plc-dialog-content {
  padding: 8px 0;
}

.plc-dialog-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plc-dialog-label {
  font-size: 14px;
  color: var(--text-muted);
  white-space: nowrap;
  width: 70px;
  text-align: right;
}

.plc-dialog-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 20px 0;
}

.plc-device-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-section {
  width: 100%;
}

/* PLC 实时数据面板 */
.plc-live-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
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
  color: var(--text-primary);
}

.plc-values-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.plc-value-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
  padding: 12px 14px;
  text-align: center;
}

.pv-name {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.pv-value {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 20px;
  font-weight: 700;
  color: var(--success);
}

.pv-value.pv-error {
  color: var(--danger);
  font-size: 14px;
}

.pv-empty {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--text-muted);
  padding: 20px;
}

/* PLC 数据源信息 */
.plc-source-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
}

.plc-info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plc-info-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.plc-info-value {
  font-size: 13px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.plc-info-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.side-panels {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
}
</style>