<!-- src/views/prediction/realtime/index.vue -->
<template>
  <div class="prediction-page">
    <!-- 模型选择（多选） -->
    <div class="model-selector">
      <span class="selector-label">选择模型:</span>
      <el-checkbox-group v-model="selectedModelKeys" size="default" @change="handleModelChange">
        <el-checkbox value="lstm">
          <el-tag :type="modelTagType('lstm')" size="small">LSTM</el-tag>
          LSTM + Attention
        </el-checkbox>
        <el-checkbox value="gru">
          <el-tag :type="modelTagType('gru')" size="small">GRU</el-tag>
          GRU
        </el-checkbox>
        <el-checkbox value="transformer">
          <el-tag :type="modelTagType('transformer')" size="small">Transformer</el-tag>
          Transformer
        </el-checkbox>
      </el-checkbox-group>
    </div>

    <!-- PLC 设备选择（多选） -->
    <div class="data-source-selector">
      <span class="selector-label">PLC 设备:</span>
      <el-select
        v-model="selectedDeviceIds"
        multiple
        placeholder="请选择 PLC 设备（可多选）"
        size="default"
        style="width: 480px"
        collapse-tags
        collapse-tags-tooltip
        filterable
        :loading="loadingPlcDevices"
        @change="handleDeviceChange"
      >
        <el-option
          v-for="d in plcDevices"
          :key="d.id"
          :label="d.name"
          :value="d.id"
          :disabled="d.status !== 'connected'"
        >
          <div class="plc-device-option">
            <span>{{ d.name }}</span>
            <el-tag
              :type="d.status === 'connected' ? 'success' : 'info'"
              size="small"
            >
              {{ d.status === 'connected' ? '已连接' : '未连接' }}
            </el-tag>
            <span class="plc-device-meta">{{ d.ip }}:{{ d.port }}</span>
          </div>
        </el-option>
      </el-select>
      <el-button
        size="default"
        :icon="Refresh"
        circle
        style="margin-left: 8px"
        @click="loadPlcDevices"
        :loading="loadingPlcDevices"
      />

      <!-- 点位配置按钮 -->
      <el-button
        size="default"
        type="primary"
        plain
        style="margin-left: 12px"
        :disabled="selectedDeviceIds.length === 0"
        @click="openPointConfigDialog"
      >
        配置点位 ({{ totalSelectedPoints }} 个)
      </el-button>
    </div>

    <!-- 已选组合概览 -->
    <div v-if="selectedDeviceIds.length > 0 && selectedModelKeys.length > 0" class="combo-overview">
      <span class="combo-label">预测组合:</span>
      <div class="combo-tags">
        <el-tag
          v-for="combo in predictionCombos"
          :key="combo.key"
          :type="combo.modelTag"
          size="default"
          effect="plain"
          class="combo-tag"
        >
          {{ combo.modelName }} → {{ combo.deviceName }}
        </el-tag>
      </div>
      <span class="combo-count">共 {{ predictionCombos.length }} 个组合</span>
    </div>

    <!-- PLC 点位配置弹窗 -->
    <el-dialog
      v-model="pointDialogVisible"
      title="配置各设备的 DB 点位"
      width="640px"
      :close-on-click-modal="false"
    >
      <div class="point-config-list">
        <div v-for="did in selectedDeviceIds" :key="did" class="point-config-item">
          <div class="point-config-header">
            <span class="point-config-device">{{ getDeviceName(did) }}</span>
            <el-tag :type="getDeviceStatus(did) === 'connected' ? 'success' : 'info'" size="small">
              {{ getDeviceStatus(did) === 'connected' ? '已连接' : '未连接' }}
            </el-tag>
          </div>
          <el-select
            v-model="devicePointMap[did]"
            multiple
            placeholder="选择点位（不选则读取所有启用点位）"
            style="width: 100%; margin-top: 8px"
            collapse-tags
            collapse-tags-tooltip
            :loading="loadingPoints[did]"
          >
            <el-option
              v-for="p in devicePoints[did] || []"
              :key="p.id"
              :label="`${p.point_name} (DB${p.db_number}.${p.start_address})`"
              :value="p.id"
            />
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="pointDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="pointDialogVisible = false">确认</el-button>
      </template>
    </el-dialog>

    <!-- 图表区域 -->
    <div class="chart-section">
      <PredictionChart :chart-data="chartData" :multi-chart-data="multiChartData" />
    </div>

    <!-- 多模型实时数据面板 -->
    <div v-if="Object.keys(multiLatestPredictions).length > 0" class="multi-prediction-panel">
      <div class="panel-title">
        <el-icon><Monitor /></el-icon>
        多模型实时预测
      </div>
      <div class="prediction-cards-grid">
        <div
          v-for="(pred, key) in multiLatestPredictions"
          :key="key"
          class="prediction-card"
          :style="{ borderLeftColor: pred.color }"
        >
          <div class="pc-header">
            <span class="pc-name" :style="{ color: pred.color }">{{ pred.name }}</span>
          </div>
          <div class="pc-value">{{ pred.prediction?.toFixed(6) }}</div>
          <div class="pc-meta">
            <span>上界: {{ pred.upper?.toFixed(4) }}</span>
            <span>下界: {{ pred.lower?.toFixed(4) }}</span>
            <span>σ: {{ pred.uncertainty?.toFixed(4) }}</span>
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
import { ref, onMounted, onUnmounted, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Monitor } from '@element-plus/icons-vue'
import PredictionChart from '../../../components/PredictionChart.vue'
import RealtimePanel from '../../../components/RealtimePanel.vue'
import ControlPanel from '../../../components/ControlPanel.vue'
import { useSSE } from '../../../composables/useSSE'
import { usePredictionStore } from '../../../composables/usePredictionStore'
import { getPlcDeviceList, getPlcPointList } from '../../../api/plc'

const store = usePredictionStore()
const { chartData, multiChartData, latestPrediction, multiLatestPredictions } = store
const { connectionState, startMultiStream, stopStream } = useSSE()
const interval = ref(1.0)

// 模型多选
const selectedModelKeys = ref(['lstm'])

// PLC 设备多选
const selectedDeviceIds = ref([])
const plcDevices = ref([])
const loadingPlcDevices = ref(false)

// 每个设备的点位数据
const devicePoints = reactive({})  // { deviceId: [point, ...] }
const devicePointMap = reactive({})  // { deviceId: [pointId, ...] }
const loadingPoints = reactive({})

// 点位配置弹窗
const pointDialogVisible = ref(false)

// 预测组合
const predictionCombos = computed(() => {
  const combos = []
  for (const mk of selectedModelKeys.value) {
    for (const did of selectedDeviceIds.value) {
      combos.push({
        key: `${mk}_${did}`,
        modelKey: mk,
        modelName: { lstm: 'LSTM', gru: 'GRU', transformer: 'Transformer' }[mk] || mk,
        modelTag: modelTagType(mk),
        deviceId: did,
        deviceName: getDeviceName(did)
      })
    }
  }
  return combos
})

// 已选点位总数
const totalSelectedPoints = computed(() => {
  let count = 0
  for (const did of selectedDeviceIds.value) {
    const pts = devicePointMap[did]
    if (pts && pts.length > 0) count += pts.length
    else {
      // 没有点位配置 = 读取所有
      const allPts = devicePoints[did]
      count += allPts ? allPts.length : 0
    }
  }
  return count
})

function getDeviceName(did) {
  const d = plcDevices.value.find(d => d.id === did)
  return d ? d.name : `设备${did}`
}

function getDeviceStatus(did) {
  const d = plcDevices.value.find(d => d.id === did)
  return d ? d.status : 'disconnected'
}

function modelTagType(key) {
  return { lstm: '', gru: 'success', transformer: 'warning' }[key] || 'info'
}

onMounted(async () => {
  await loadPlcDevices()
})

onUnmounted(() => {
  stopStream()
})

async function loadPlcDevices() {
  loadingPlcDevices.value = true
  try {
    const res = await getPlcDeviceList()
    plcDevices.value = res.data || []
  } catch (e) { /* ignore */ }
  finally { loadingPlcDevices.value = false }
}

async function handleDeviceChange() {
  // 为新选的设备加载点位
  for (const did of selectedDeviceIds.value) {
    if (!devicePoints[did]) {
      loadingPoints[did] = true
      try {
        const res = await getPlcPointList({ device_id: did, is_active: 1 })
        devicePoints[did] = res.data || []
        if (!devicePointMap[did]) {
          devicePointMap[did] = []
        }
      } catch (e) {
        devicePoints[did] = []
      } finally {
        loadingPoints[did] = false
      }
    }
  }
  // 清理取消选择的设备
  for (const did of Object.keys(devicePointMap)) {
    if (!selectedDeviceIds.value.includes(Number(did))) {
      delete devicePointMap[did]
    }
  }
}

function handleModelChange() {
  // 如果正在运行，重启流
  if (connectionState.value === 'open' && selectedModelKeys.value.length > 0) {
    stopStream()
    setTimeout(() => {
      handleStart()
    }, 500)
  }
}

function openPointConfigDialog() {
  handleDeviceChange()
  pointDialogVisible.value = true
}

function handleStart() {
  if (selectedModelKeys.value.length === 0) {
    ElMessage.warning('请至少选择一个模型')
    return
  }
  if (selectedDeviceIds.value.length === 0) {
    ElMessage.warning('请至少选择一个 PLC 设备')
    return
  }

  // 检查所有设备是否已连接
  const disconnected = selectedDeviceIds.value.filter(did => getDeviceStatus(did) !== 'connected')
  if (disconnected.length > 0) {
    const names = disconnected.map(did => getDeviceName(did)).join(', ')
    ElMessage.warning(`以下设备未连接: ${names}`)
    return
  }

  // 构建设备参数
  const devices = selectedDeviceIds.value.map(did => {
    const pointIds = devicePointMap[did]
    return {
      device_id: did,
      point_ids: pointIds && pointIds.length > 0 ? pointIds.join(',') : ''
    }
  })

  startMultiStream(interval.value, devices, selectedModelKeys.value)
  ElMessage.success(`已启动 ${predictionCombos.value.length} 个预测组合`)
}

function handleStop() {
  stopStream()
}

function handleClear() {
  store.clearData()
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

/* 组合概览 */
.combo-overview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  flex-wrap: wrap;
}

.combo-label {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
}

.combo-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.combo-tag {
  font-size: 12px;
}

.combo-count {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}

/* PLC 设备选项 */
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

/* 点位配置弹窗 */
.point-config-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.point-config-item {
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
}

.point-config-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.point-config-device {
  font-size: 14px;
  font-weight: 600;
}

/* 多模型预测面板 */
.multi-prediction-panel {
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

.prediction-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.prediction-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-left: 4px solid var(--primary);
  border-radius: 8px;
  padding: 14px 16px;
}

.pc-header {
  margin-bottom: 8px;
}

.pc-name {
  font-size: 14px;
  font-weight: 600;
}

.pc-value {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.pc-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.chart-section {
  width: 100%;
}

.side-panels {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
}
</style>
