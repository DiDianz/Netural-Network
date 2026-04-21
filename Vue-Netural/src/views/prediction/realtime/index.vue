<!-- src/views/prediction/realtime/index.vue -->
<!-- 支持两种模式：
     1. 独立模式 (无 route.params.id) — 手动选 PLC + 模型，自由预测
     2. 实例模式 (有 route.params.id) — 从后端加载实例配置，绑定固定 PLC + 模型
-->
<template>
  <div class="prediction-page">
    <!-- 实例模式：显示实例信息 -->
    <div v-if="isInstanceMode" class="instance-info-bar">
      <div class="instance-info-left">
        <el-tag :type="modelTagType(instanceConfig.model_key)" size="default">
          {{ (instanceConfig.model_key || '').toUpperCase() }}
        </el-tag>
        <span class="instance-name">{{ instanceConfig.name }}</span>
        <span class="instance-device">→ {{ instanceConfig.device_name || `设备#${instanceConfig.device_id}` }}</span>
      </div>
      <div class="instance-info-right">
        <el-tag :type="connectionState === 'open' ? 'success' : 'info'" size="small" effect="dark">
          {{ connectionState === 'open' ? '预测中' : '未运行' }}
        </el-tag>
        <el-button size="small" text type="primary" @click="goToInstanceList">
          返回实例列表
        </el-button>
      </div>
    </div>

    <!-- 独立模式：模型选择 + PLC 选择 -->
    <template v-if="!isInstanceMode">
      <div class="model-selector">
        <span class="selector-label">选择模型:</span>
        <el-radio-group v-model="selectedModelKey" size="default">
          <el-radio-button value="lstm">LSTM</el-radio-button>
          <el-radio-button value="gru">GRU</el-radio-button>
          <el-radio-button value="transformer">Transformer</el-radio-button>
        </el-radio-group>

        <span class="selector-label" style="margin-left: 20px">已保存模型:</span>
        <el-select
          v-model="selectedSavedModelId"
          placeholder="选择已保存的模型版本（可选）"
          size="default"
          style="width: 360px"
          filterable
          clearable
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
              </div>
            </div>
          </el-option>
        </el-select>
        <el-button size="default" :icon="Refresh" circle style="margin-left: 8px" @click="loadSavedModels" :loading="loadingSavedModels" />
      </div>

      <div class="data-source-selector">
        <span class="selector-label">PLC 设备:</span>
        <el-select
          v-model="selectedDeviceId"
          placeholder="请选择 PLC 设备"
          size="default"
          style="width: 300px"
          filterable
          :loading="loadingPlcDevices"
          @change="handleDeviceSelect"
        >
          <el-option
            v-for="d in availableDevices"
            :key="d.id"
            :label="d.name"
            :value="d.id"
          >
            <div class="plc-device-option">
              <span>{{ d.name }}</span>
              <el-tag :type="d.status === 'connected' ? 'success' : 'warning'" size="small">
                {{ d.status === 'connected' ? '已连接' : '模拟中' }}
              </el-tag>
              <span class="plc-device-meta">{{ d.ip }}:{{ d.port }}</span>
            </div>
          </el-option>
        </el-select>
        <el-button size="default" :icon="Refresh" circle style="margin-left: 8px" @click="loadPlcDevices" :loading="loadingPlcDevices" />
      </div>
    </template>

    <!-- 点位选择（独立模式，选择设备后显示） -->
    <div v-if="!isInstanceMode && selectedDeviceId" class="point-selector">
      <span class="selector-label">数据点位:</span>
      <el-select
        v-model="selectedPointIds"
        multiple
        placeholder="不选则读取所有启用点位"
        size="default"
        style="width: 100%"
        collapse-tags
        collapse-tags-tooltip
        filterable
        :loading="loadingPoints"
      >
        <el-option
          v-for="p in devicePoints"
          :key="p.id"
          :label="`${p.point_name} (DB${p.db_number}.${p.start_address})`"
          :value="p.id"
        />
      </el-select>
    </div>

    <!-- 图表 -->
    <div class="chart-section">
      <PredictionChart :chart-data="chartData" />
    </div>

    <!-- PLC 实时数据面板 -->
    <div v-if="plcLiveValues.length > 0" class="plc-live-panel">
      <div class="panel-title">
        <el-icon><Monitor /></el-icon>
        PLC 实时数据
      </div>
      <div class="plc-values-grid">
        <div v-for="item in plcLiveValues" :key="item.point_id" class="plc-value-card">
          <div class="pv-name">{{ item.point_name }}</div>
          <div class="pv-value" :class="{ 'pv-error': !item.success }">
            {{ item.success ? item.value : 'ERR' }}
          </div>
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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Monitor } from '@element-plus/icons-vue'
import PredictionChart from '../../../components/PredictionChart.vue'
import RealtimePanel from '../../../components/RealtimePanel.vue'
import ControlPanel from '../../../components/ControlPanel.vue'
import { usePredictionStore } from '../../../composables/usePredictionStore'
import { getSavedModels, loadSavedModel, switchModel } from '../../../api/model'
import { getPlcDeviceList, getPlcPointList } from '../../../api/plc'
import { getInstanceDetail } from '../../../api/instance'

const route = useRoute()
const router = useRouter()
const store = usePredictionStore()
const { chartData, latestPrediction } = store
const interval = ref(1.0)
const connectionState = ref('closed')
let eventSource = null

// ========== 实例模式 ==========
const isInstanceMode = computed(() => !!route.params.id)
const instanceConfig = ref({})
const plcLiveValues = ref([])

// ========== 独立模式 ==========
const selectedModelKey = ref('lstm')
const selectedDeviceId = ref(null)
const selectedSavedModelId = ref(null)
const savedModels = ref([])
const loadingSavedModels = ref(false)
const plcDevices = ref([])
const loadingPlcDevices = ref(false)
const devicePoints = ref([])
const selectedPointIds = ref([])
const loadingPoints = ref(false)

const filteredSavedModels = computed(() => {
  return savedModels.value.filter(m => m.model_key === selectedModelKey.value)
})

const availableDevices = computed(() => {
  return plcDevices.value.filter(d => d.status === 'connected' || d.status === 'simulated')
})

function modelTagType(key) {
  return { lstm: '', gru: 'success', transformer: 'warning' }[key] || 'info'
}

onMounted(async () => {
  if (isInstanceMode.value) {
    await loadInstanceConfig()
  } else {
    await loadSavedModels()
    await loadPlcDevices()
  }
})

onUnmounted(() => {
  stopStream()
})

// ========== 实例模式：加载配置 ==========
async function loadInstanceConfig() {
  try {
    const res = await getInstanceDetail(route.params.id)
    instanceConfig.value = res.data || {}
    interval.value = instanceConfig.value.interval || 1.0
  } catch (e) {
    ElMessage.error('加载实例配置失败')
    router.push('/prediction/instances')
  }
}

function goToInstanceList() {
  router.push('/prediction/instances')
}

// ========== 独立模式：加载模型/设备 ==========
async function loadSavedModels() {
  loadingSavedModels.value = true
  try {
    const res = await getSavedModels()
    savedModels.value = res.data || []
    if (!selectedSavedModelId.value && savedModels.value.length > 0) {
      const first = filteredSavedModels.value[0] || savedModels.value[0]
      selectedSavedModelId.value = first.model_id
      selectedModelKey.value = first.model_key
    }
  } catch (e) {
    console.error('获取已保存模型列表失败:', e)
  } finally {
    loadingSavedModels.value = false
  }
}

async function handleSavedModelChange(modelId) {
  if (!modelId) return
  const model = savedModels.value.find(m => m.model_id === modelId)
  if (!model) return
  try {
    await loadSavedModel(modelId)
    await switchModel(model.model_key)
    selectedModelKey.value = model.model_key
    ElMessage.success(`已加载: ${model.name || model.display_name}`)
    if (connectionState.value === 'open') {
      stopStream()
      setTimeout(() => handleStart(), 500)
    }
  } catch (e) {
    ElMessage.error('加载模型失败: ' + ((e.response && e.response.data && e.response.data.detail) || e.message))
  }
}

async function loadPlcDevices() {
  loadingPlcDevices.value = true
  try {
    const res = await getPlcDeviceList()
    plcDevices.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingPlcDevices.value = false }
}

function handleDeviceSelect() {
  // 重置点位选择
  selectedPointIds.value = []
  devicePoints.value = []
  // 加载该设备的点位
  loadDevicePoints(selectedDeviceId.value)
  // 设备变更后，如果正在运行，重启
  if (connectionState.value === 'open') {
    stopStream()
    setTimeout(() => handleStart(), 500)
  }
}

async function loadDevicePoints(deviceId) {
  if (!deviceId) return
  loadingPoints.value = true
  try {
    const res = await getPlcPointList({ device_id: deviceId, is_active: 1 })
    devicePoints.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingPoints.value = false }
}

// ========== 预测流控制 ==========
function stopStream() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  connectionState.value = 'closed'
}

async function handleStart() {
  if (isInstanceMode.value) {
    startInstanceStream()
    return
  }

  // 独立模式
  if (!selectedDeviceId.value) {
    ElMessage.warning('请先选择 PLC 设备')
    return
  }

  const device = plcDevices.value.find(d => d.id === selectedDeviceId.value)
  if (!device || (device.status !== 'connected' && device.status !== 'simulated')) {
    ElMessage.warning('PLC 设备未连接或未启动模拟')
    return
  }

  // 加载并切换模型
  if (selectedSavedModelId.value) {
    try {
      await loadSavedModel(selectedSavedModelId.value)
      const model = savedModels.value.find(m => m.model_id === selectedSavedModelId.value)
      if (model) {
        await switchModel(model.model_key)
        selectedModelKey.value = model.model_key
      }
    } catch (e) {
      ElMessage.error('加载模型失败')
      return
    }
  }

  // 使用实例模式的 stream（临时创建）
  startStandaloneStream()
}

function startInstanceStream() {
  stopStream()
  store.clearData()
  plcLiveValues.value = []
  connectionState.value = 'connecting'

  const instanceId = route.params.id
  const url = `http://localhost:8000/instance/stream?instance_id=${instanceId}`
  const es = new EventSource(url)

  es.onopen = () => { connectionState.value = 'open' }

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.error) {
        ElMessage.error(`预测错误: ${data.error}`)
        return
      }
      store.addDataPoint(data)
      if (data.plc_points) {
        plcLiveValues.value = data.plc_points
      }
    } catch (e) { /* ignore */ }
  }

  es.onerror = () => {
    connectionState.value = 'closed'
    es.close()
  }

  eventSource = es
}

function startStandaloneStream() {
  stopStream()
  store.clearData()
  plcLiveValues.value = []
  connectionState.value = 'connecting'

  const pointIds = selectedPointIds.value.length > 0
    ? selectedPointIds.value.join(',')
    : ''

  const savedModelParam = selectedSavedModelId.value || ''
  const query = new URLSearchParams()
  query.set('device_id', selectedDeviceId.value)
  query.set('model_key', selectedModelKey.value)
  if (pointIds) query.set('point_ids', pointIds)
  query.set('interval', interval.value)
  if (savedModelParam) query.set('use_saved_model', savedModelParam)

  const url = `http://localhost:8000/predict/plc-stream?${query.toString()}`
  const es = new EventSource(url)

  es.onopen = () => { connectionState.value = 'open' }

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.error) {
        ElMessage.error(`预测错误: ${data.error}`)
        return
      }
      store.addDataPoint(data)
      if (data.plc_points) {
        plcLiveValues.value = data.plc_points
      }
    } catch (e) { /* ignore */ }
  }

  es.onerror = () => {
    connectionState.value = 'closed'
    es.close()
  }

  eventSource = es
}

function handleStop() {
  stopStream()
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

/* 实例信息条 */
.instance-info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.instance-info-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.instance-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.instance-device {
  font-size: 13px;
  color: var(--text-muted);
}

.instance-info-right {
  display: flex;
  align-items: center;
  gap: 12px;
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

.point-selector {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.point-selector .selector-label {
  margin-top: 10px;
  white-space: nowrap;
}

.selector-label {
  font-size: 14px;
  color: var(--text-muted);
  white-space: nowrap;
}

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

.plc-device-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plc-device-meta {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
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

.side-panels {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
}
</style>
