<!-- src/views/prediction/realtime/index.vue -->
<template>
  <div class="prediction-page">
    <div class="model-selector">
      <span class="selector-label">当前模型:</span>
      <el-radio-group v-model="selectedModel" size="default" @change="handleModelChange">
        <el-radio-button v-for="m in modelList" :key="m.key" :value="m.key">
          {{ m.display_name }}
          <el-tag v-if="m.is_current" type="success" size="small" style="margin-left: 4px">当前</el-tag>
        </el-radio-button>
      </el-radio-group>
    </div>

    <div class="data-source-selector">
      <span class="selector-label">数据源:</span>
      <el-radio-group v-model="dataSource" size="default" @change="handleDataSourceChange">
        <el-radio-button value="random">随机模拟数据</el-radio-button>
        <el-radio-button value="uploaded" :disabled="!hasUploadedFiles">上传数据</el-radio-button>
      </el-radio-group>
      <el-tag v-if="dataSource === 'uploaded'" type="warning" size="small" style="margin-left: 12px">
        预测值 vs 实际值对比
      </el-tag>
      <el-tag v-if="!hasUploadedFiles" type="info" size="small" style="margin-left: 12px">
        请先在模型管理页上传数据
      </el-tag>
    </div>

    <div class="chart-section">
      <PredictionChart :chart-data="chartData" />
    </div>

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
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import PredictionChart from '../../../components/PredictionChart.vue'
import RealtimePanel from '../../../components/RealtimePanel.vue'
import ControlPanel from '../../../components/ControlPanel.vue'
import { useSSE } from '../../../composables/useSSE'
import { usePredictionStore } from '../../../composables/usePredictionStore'
import { getModelList, switchModel, getUploadedFiles } from '../../../api/model'

const store = usePredictionStore()
const { chartData, latestPrediction } = store
const { connectionState, startStream, stopStream } = useSSE()
const interval = ref(1.0)

const modelList = ref([])
const selectedModel = ref('lstm')
const dataSource = ref('random')
const hasUploadedFiles = ref(false)

onMounted(async () => {
  await loadModels()
  checkUploadedFiles()
})

onUnmounted(() => {
  stopStream()
})

async function loadModels() {
  try {
    const res = await getModelList()
    modelList.value = res.data || res
    const current = modelList.value.find(m => m.is_current)
    if (current) selectedModel.value = current.key
  } catch (e) {
    console.error('获取模型列表失败:', e)
  }
}

async function checkUploadedFiles() {
  try {
    const res = await getUploadedFiles()
    hasUploadedFiles.value = (res.data || []).length > 0
  } catch (e) { /* ignore */ }
}

async function handleModelChange(key) {
  try {
    await switchModel(key)
    ElMessage.success('已切换到 ' + key.toUpperCase() + ' 模型')
    // 重新加载模型列表，更新"当前"标签
    await loadModels()
    if (connectionState.value === 'open') {
      stopStream()
      setTimeout(() => {
        startStream(interval.value, key, dataSource.value === 'uploaded')
      }, 500)
    }
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

function handleDataSourceChange() {
  if (connectionState.value === 'open') {
    stopStream()
    setTimeout(() => handleStart(), 500)
  }
}

function handleStart() {
  startStream(interval.value, selectedModel.value, dataSource.value === 'uploaded')
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
  border: 1px solid #1e1e2e;
  border-radius: 12px;
}

.selector-label {
  font-size: 14px;
  color: #888;
  white-space: nowrap;
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
