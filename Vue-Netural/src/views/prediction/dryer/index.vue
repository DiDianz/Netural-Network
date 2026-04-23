<template>
  <div class="dryer-container">
    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="status-item">
        <span class="label">数据状态:</span>
        <el-tag :type="hasData ? 'success' : 'info'" size="small">
          {{ hasData ? `${dataRows} 行已加载` : '未上传' }}
        </el-tag>
      </div>
      <div class="status-item">
        <span class="label">模型状态:</span>
        <el-tag :type="activeVersion ? 'success' : 'info'" size="small">
          {{ activeVersion || '未训练' }}
        </el-tag>
      </div>
      <div class="status-item" v-if="modelR2 !== null">
        <span class="label">R²:</span>
        <el-tag :type="modelR2 > 0.9 ? 'success' : modelR2 > 0.7 ? 'warning' : 'danger'" size="small">
          {{ modelR2 }}
        </el-tag>
      </div>
    </div>

    <!-- 主标签页 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: 数据分析 -->
      <el-tab-pane label="数据分析" name="analysis">
        <div class="tab-header">
          <el-upload
            :show-file-list="false"
            :before-upload="handleUpload"
            accept=".xlsx,.xls,.csv"
          >
            <el-button type="primary" :loading="uploading">
              <el-icon><Upload /></el-icon> 上传训练数据
            </el-button>
          </el-upload>
          <el-button @click="refreshAnalysis" :disabled="!hasData" :loading="analyzing">
            <el-icon><Refresh /></el-icon> 刷新分析
          </el-button>
        </div>

        <div v-if="analysisData" class="analysis-content">
          <!-- 统计卡片 -->
          <el-row :gutter="16" class="stat-cards">
            <el-col :span="6" v-for="(stat, name) in analysisData.stats" :key="name">
              <el-card shadow="hover" class="stat-card">
                <div class="stat-name">{{ featureNameMap[name] || name }}</div>
                <div class="stat-values">
                  <span>均值: {{ stat.mean }}</span>
                  <span>范围: [{{ stat.min }}, {{ stat.max }}]</span>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 相关性 & 目标趋势 -->
          <el-row :gutter="16" style="margin-top: 16px;">
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>特征与出口水分相关性</template>
                <div ref="corrChartRef" style="height: 350px;"></div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>出口水分时间趋势</template>
                <div ref="trendChartRef" style="height: 350px;"></div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 分布 & 特征重要性 -->
          <el-row :gutter="16" style="margin-top: 16px;">
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>出口水分分布</template>
                <div ref="distChartRef" style="height: 350px;"></div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>特征方差贡献</template>
                <div ref="importanceChartRef" style="height: 350px;"></div>
              </el-card>
            </el-col>
          </el-row>
        </div>
        <el-empty v-else description="请先上传训练数据 (Excel/CSV)" />
      </el-tab-pane>

      <!-- Tab 2: 模型训练 -->
      <el-tab-pane label="模型训练" name="train">
        <el-row :gutter="16">
          <!-- 左: 训练配置 -->
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>训练配置</template>
              <el-form :model="trainForm" label-position="top" size="small">
                <el-form-item label="训练轮次">
                  <el-slider v-model="trainForm.epochs" :min="10" :max="500" :step="10" show-input />
                </el-form-item>
                <el-form-item label="批大小">
                  <el-select v-model="trainForm.batch_size" style="width: 100%;">
                    <el-option v-for="s in [8,16,32,64,128]" :key="s" :label="s" :value="s" />
                  </el-select>
                </el-form-item>
                <el-form-item label="学习率">
                  <el-input-number v-model="trainForm.learning_rate" :min="0.0001" :max="0.1" :step="0.0001" :precision="4" style="width: 100%;" />
                </el-form-item>
                <el-form-item label="滑动窗口">
                  <el-slider v-model="trainForm.window_size" :min="3" :max="50" show-input />
                </el-form-item>
                <el-form-item label="隐藏层维度">
                  <el-select v-model="trainForm.hidden_dim" style="width: 100%;">
                    <el-option v-for="d in [32,64,128,256,512]" :key="d" :label="d" :value="d" />
                  </el-select>
                </el-form-item>
                <el-form-item label="LSTM层数">
                  <el-slider v-model="trainForm.num_layers" :min="1" :max="4" show-input />
                </el-form-item>
                <el-form-item label="Dropout">
                  <el-slider v-model="trainForm.dropout" :min="0" :max="0.5" :step="0.05" show-input />
                </el-form-item>
                <el-form-item label="目标水分范围">
                  <el-input v-model="targetRangeStr" placeholder="14.0,15.0" />
                </el-form-item>
              </el-form>
              <el-button
                type="primary"
                @click="startTraining"
                :loading="training"
                :disabled="!hasData"
                style="width: 100%; margin-top: 12px;"
              >
                {{ training ? '训练中...' : '开始训练' }}
              </el-button>
            </el-card>
          </el-col>

          <!-- 右: 训练进度 -->
          <el-col :span="16">
            <el-card shadow="hover">
              <template #header>
                训练进度
                <el-tag v-if="trainingDone" type="success" size="small" style="margin-left: 8px;">
                  完成
                </el-tag>
              </template>

              <!-- 进度条 -->
              <div v-if="training || trainProgress" class="train-progress">
                <el-progress
                  :percentage="trainProgressPercent"
                  :status="trainingDone ? 'success' : ''"
                  :stroke-width="20"
                  striped
                  :striped-flow="training"
                />
                <div class="progress-stats" v-if="trainProgress">
                  <span>Epoch: {{ trainProgress.epoch }}/{{ trainProgress.total_epochs }}</span>
                  <span>Train Loss: {{ trainProgress.train_loss }}</span>
                  <span>Test Loss: {{ trainProgress.test_loss }}</span>
                  <span>R²: {{ trainProgress.r2 }}</span>
                  <span>LR: {{ trainProgress.lr }}</span>
                </div>
              </div>

              <!-- 损失曲线 -->
              <div ref="lossChartRef" style="height: 300px; margin-top: 16px;"></div>

              <!-- 特征权重 -->
              <div v-if="trainProgress && trainProgress.feature_weights" style="margin-top: 16px;">
                <h4>当前特征权重</h4>
                <div ref="weightsChartRef" style="height: 250px;"></div>
              </div>

              <!-- 训练结果 -->
              <el-result
                v-if="trainingDone && trainResult"
                icon="success"
                :title="trainResult.msg"
                sub-title=""
              >
                <template #extra>
                  <el-descriptions :column="2" border size="small">
                    <el-descriptions-item label="最优测试损失">{{ trainResult.best_test_loss }}</el-descriptions-item>
                    <el-descriptions-item label="最终R²">{{ trainResult.final_r2 }}</el-descriptions-item>
                    <el-descriptions-item label="模型版本">{{ trainResult.version }}</el-descriptions-item>
                  </el-descriptions>
                </template>
              </el-result>
            </el-card>

            <!-- 版本管理 -->
            <el-card shadow="hover" style="margin-top: 16px;">
              <template #header>模型版本管理</template>
              <el-table :data="versions" size="small" stripe>
                <el-table-column prop="version" label="版本" min-width="200" />
                <el-table-column prop="created_at" label="创建时间" width="180" />
                <el-table-column label="R²" width="80">
                  <template #default="{ row }">
                    {{ row.metrics?.final_r2 ?? '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="Loss" width="100">
                  <template #default="{ row }">
                    {{ row.metrics?.best_test_loss ?? '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                      {{ row.is_active ? '激活' : '' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="160">
                  <template #default="{ row }">
                    <el-button size="small" type="primary" @click="doActivate(row.version)" :disabled="row.is_active">
                      激活
                    </el-button>
                    <el-button size="small" type="danger" @click="doDelete(row.version)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 3: 预测 -->
      <el-tab-pane label="模型预测" name="predict">
        <el-row :gutter="16">
          <el-col :span="10">
            <el-card shadow="hover">
              <template #header>输入参数</template>
              <el-form label-position="top" size="small">
                <el-form-item v-for="(name, idx) in featureNames" :key="name" :label="featureNameMap[name] || name">
                  <el-input-number v-model="predictInput[idx]" :precision="4" style="width: 100%;" />
                </el-form-item>
              </el-form>
              <el-button
                type="primary"
                @click="doPredict"
                :loading="predicting"
                :disabled="!activeVersion"
                style="width: 100%; margin-top: 12px;"
              >
                预测出口水分
              </el-button>
            </el-card>
          </el-col>
          <el-col :span="14">
            <el-card shadow="hover">
              <template #header>预测结果</template>
              <div v-if="predictResult">
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="预测出口水分">
                    <span :class="{ 'target-ok': predictResult.in_target }">
                      {{ predictResult.prediction }}
                    </span>
                    <el-tag v-if="predictResult.in_target" type="success" size="small" style="margin-left: 8px;">
                      达标 ✓
                    </el-tag>
                    <el-tag v-else type="warning" size="small" style="margin-left: 8px;">
                      未达标
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="不确定性">± {{ predictResult.uncertainty }}</el-descriptions-item>
                  <el-descriptions-item label="置信上界">{{ predictResult.confidence_upper }}</el-descriptions-item>
                  <el-descriptions-item label="置信下界">{{ predictResult.confidence_lower }}</el-descriptions-item>
                  <el-descriptions-item label="目标范围">14.0 ~ 15.0</el-descriptions-item>
                  <el-descriptions-item label="模型版本">{{ predictResult.version }}</el-descriptions-item>
                </el-descriptions>
              </div>
              <el-empty v-else description="配置参数后点击预测" />
            </el-card>

            <!-- 预测历史曲线 -->
            <el-card shadow="hover" style="margin-top: 16px;">
              <template #header>预测历史</template>
              <div ref="predictChartRef" style="height: 300px;"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 4: PLC 实时应用 -->
      <el-tab-pane label="PLC实时应用" name="plc">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>PLC配置</template>
              <el-form :model="plcForm" label-position="top" size="small">
                <el-form-item label="PLC设备">
                  <el-select v-model="plcForm.device_id" placeholder="选择设备" style="width: 100%;">
                    <el-option v-for="d in plcDevices" :key="d.id" :label="d.device_name" :value="d.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="点位ID (逗号分隔, 留空=全部)">
                  <el-input v-model="plcForm.point_ids" placeholder="1,2,3" />
                </el-form-item>
                <el-form-item label="采集间隔(秒)">
                  <el-input-number v-model="plcForm.interval" :min="0.1" :max="30" :step="0.5" style="width: 100%;" />
                </el-form-item>
                <el-form-item label="模型版本">
                  <el-select v-model="plcForm.model_version" placeholder="使用激活版本" style="width: 100%;" clearable>
                    <el-option v-for="v in versions" :key="v.version" :label="v.version" :value="v.version" />
                  </el-select>
                </el-form-item>
              </el-form>
              <el-button
                :type="plcRunning ? 'danger' : 'success'"
                @click="togglePLCStream"
                :disabled="!activeVersion"
                style="width: 100%;"
              >
                {{ plcRunning ? '停止采集' : '开始采集' }}
              </el-button>
            </el-card>

            <!-- 实时状态 -->
            <el-card shadow="hover" style="margin-top: 16px;" v-if="plcRunning">
              <template #header>实时状态</template>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="当前预测">
                  <span :class="{ 'target-ok': plcPrediction?.in_target }">
                    {{ plcPrediction?.prediction ?? '-' }}
                  </span>
                </el-descriptions-item>
                <el-descriptions-item label="不确定性">± {{ plcPrediction?.uncertainty ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="是否达标">
                  <el-tag :type="plcPrediction?.in_target ? 'success' : 'warning'" size="small">
                    {{ plcPrediction?.in_target ? '✓ 达标' : '未达标' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="Tick">{{ plcPrediction?.tick ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="模式">
                  <el-tag :type="plcPrediction?.simulated ? 'info' : 'success'" size="small">
                    {{ plcPrediction?.simulated ? '模拟' : '真实' }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>

          <el-col :span="16">
            <el-card shadow="hover">
              <template #header>实时预测趋势</template>
              <div ref="plcChartRef" style="height: 400px;"></div>
            </el-card>

            <el-card shadow="hover" style="margin-top: 16px;">
              <template #header>PLC点位数据</template>
              <el-table :data="plcPointsData" size="small" stripe max-height="300">
                <el-table-column prop="point_name" label="点位名称" />
                <el-table-column prop="value" label="当前值" width="120" />
                <el-table-column prop="success" label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                      {{ row.success ? '正常' : '异常' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  uploadDryerData, analyzeData, getWeights, updateWeights,
  listVersions, activateVersion, deleteVersion, evaluateModel, predict
} from '@/api/dryer'
import { getPlcDeviceList } from '@/api/plc'
import request from '@/api/request'

// ---- 常量 ----
const FEATURE_NAMES = [
  'proc_steam_vol', 'proc_air_temp', 'input_moist', 'input_moist_SP',
  'moist_remove', 'out_moist_SP', 'out_temp', 'mat_flow_PV',
  'total_mat_flow', 'env_temp', 'env_moist', 'brandID'
]
const featureNameMap = {
  proc_steam_vol: '加工蒸汽量', proc_air_temp: '加工热风温度',
  input_moist: '入口含水率', input_moist_SP: '入口含水率设定值',
  moist_remove: '湿基去除量', out_moist: '出口含水率',
  out_moist_SP: '出口含水率设定值', out_temp: '出口温度',
  mat_flow_PV: '物料流量', total_mat_flow: '累计物料流量',
  env_temp: '环境温度', env_moist: '环境湿度', brandID: '牌号ID'
}

// ---- 状态 ----
const activeTab = ref('analysis')
const hasData = ref(false)
const dataRows = ref(0)
const activeVersion = ref(null)
const modelR2 = ref(null)
const uploading = ref(false)
const analyzing = ref(false)
const analysisData = ref(null)

// 训练
const training = ref(false)
const trainingDone = ref(false)
const trainProgress = ref(null)
const trainResult = ref(null)
const trainLossHistory = reactive({ train: [], test: [] })
const trainForm = reactive({
  epochs: 100, batch_size: 32, learning_rate: 0.001,
  window_size: 10, hidden_dim: 128, num_layers: 2, dropout: 0.2
})
const targetRangeStr = ref('14.0,15.0')
const versions = ref([])

// 预测
const predicting = ref(false)
const predictInput = ref(Array(12).fill(0))
const predictResult = ref(null)
const predictHistory = reactive({ preds: [], actuals: [] })

// PLC
const plcRunning = ref(false)
const plcDevices = ref([])
const plcPrediction = ref(null)
const plcPointsData = ref([])
const plcHistory = reactive({ preds: [], ticks: [] })
const plcForm = reactive({ device_id: null, point_ids: '', interval: 1, model_version: '' })
let plcEventSource = null

// ---- Chart refs ----
const corrChartRef = ref(null)
const trendChartRef = ref(null)
const distChartRef = ref(null)
const importanceChartRef = ref(null)
const lossChartRef = ref(null)
const weightsChartRef = ref(null)
const predictChartRef = ref(null)
const plcChartRef = ref(null)

let charts = {}

// ---- 初始化 ----
onMounted(async () => {
  await loadVersions()
  await loadPLCDevices()
  // 尝试加载分析
  try { await refreshAnalysis() } catch {}
})

onUnmounted(() => {
  Object.values(charts).forEach(c => c?.dispose())
  if (plcEventSource) plcEventSource.close()
})

function getChart(refEl) {
  if (!refEl.value) return null
  const key = refEl.value
  if (!charts[key]) {
    charts[key] = echarts.init(key)
  }
  return charts[key]
}

// ---- 上传 ----
async function handleUpload(file) {
  uploading.value = true
  try {
    const res = await uploadDryerData(file)
    ElMessage.success(res.msg)
    hasData.value = true
    dataRows.value = res.data.rows
    await refreshAnalysis()
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
  return false
}

// ---- 分析 ----
async function refreshAnalysis() {
  analyzing.value = true
  try {
    const res = await analyzeData()
    analysisData.value = res.data
    hasData.value = true
    dataRows.value = res.data.total_rows
    await nextTick()
    renderAnalysisCharts()
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '分析失败'
    ElMessage.error('数据分析失败: ' + msg)
  } finally {
    analyzing.value = false
  }
}

function renderAnalysisCharts() {
  const d = analysisData.value
  if (!d) return

  // 1. 相关性柱状图
  const corrChart = getChart(corrChartRef)
  if (corrChart) {
    const corrEntries = Object.entries(d.correlations).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    corrChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: corrEntries.map(e => featureNameMap[e[0]] || e[0]), axisLabel: { rotate: 45 } },
      yAxis: { type: 'value', name: '相关系数' },
      series: [{
        type: 'bar', data: corrEntries.map(e => e[1]),
        itemStyle: { color: p => p.value >= 0 ? '#409EFF' : '#F56C6C' }
      }]
    })
  }

  // 2. 趋势折线图
  const trendChart = getChart(trendChartRef)
  if (trendChart) {
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: d.trend.map((_, i) => i) },
      yAxis: { type: 'value', name: '出口含水率', min: 0, max: 20 },
      series: [{
        type: 'line', data: d.trend, smooth: true, symbol: 'none',
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.3 },
        markLine: {
          data: [
            { yAxis: 14, name: '目标下界', lineStyle: { color: '#67C23A', type: 'dashed' } },
            { yAxis: 15, name: '目标上界', lineStyle: { color: '#67C23A', type: 'dashed' } }
          ]
        }
      }]
    })
  }

  // 3. 分布直方图
  const distChart = getChart(distChartRef)
  if (distChart) {
    const bins = d.distribution.bins.slice(0, -1).map((b, i) => `${b}-${d.distribution.bins[i + 1]}`)
    distChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: bins, axisLabel: { rotate: 45 } },
      yAxis: { type: 'value', name: '频次' },
      series: [{ type: 'bar', data: d.distribution.counts, itemStyle: { color: '#E6A23C' } }]
    })
  }

  // 4. 特征重要性
  const impChart = getChart(importanceChartRef)
  if (impChart) {
    const entries = Object.entries(d.importance).sort((a, b) => b[1] - a[1])
    impChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: entries.map(e => featureNameMap[e[0]] || e[0]), axisLabel: { rotate: 45 } },
      yAxis: { type: 'value', name: '方差贡献率' },
      series: [{ type: 'bar', data: entries.map(e => e[1]), itemStyle: { color: '#909399' } }]
    })
  }
}

// ---- 训练 ----
async function startTraining() {
  if (!hasData.value) return ElMessage.warning('请先上传数据')

  training.value = true
  trainingDone.value = false
  trainProgress.value = null
  trainResult.value = null
  trainLossHistory.train = []
  trainLossHistory.test = []

  const tr = targetRangeStr.value.split(',').map(Number)
  const params = { ...trainForm, target_range: tr.join(',') }
  const qs = new URLSearchParams(params).toString()

  const es = new EventSource(`http://localhost:8000/dryer/train?${qs}`)
  es.onmessage = (ev) => {
    const data = JSON.parse(ev.data)
    if (data.type === 'error') {
      ElMessage.error(data.msg || '训练失败')
      training.value = false
      es.close()
      return
    }
    if (data.type === 'progress') {
      trainProgress.value = data
      trainLossHistory.train.push(data.train_loss)
      trainLossHistory.test.push(data.test_loss)
      renderLossChart()
      renderWeightsChart(data.feature_weights)
    } else if (data.type === 'done') {
      trainResult.value = data
      trainingDone.value = true
      training.value = false
      activeVersion.value = data.version
      modelR2.value = data.final_r2
      es.close()
      loadVersions()
      ElMessage.success(data.msg)
    }
  }
  es.onerror = (err) => {
    training.value = false
    es.close()
    ElMessage.error('训练连接中断')
  }
}

function renderLossChart() {
  const chart = getChart(lossChartRef)
  if (!chart) return
  const epochs = trainLossHistory.train.map((_, i) => i + 1)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Train Loss', 'Test Loss'] },
    xAxis: { type: 'category', data: epochs, name: 'Epoch' },
    yAxis: { type: 'value', name: 'Loss' },
    series: [
      { name: 'Train Loss', type: 'line', data: trainLossHistory.train, smooth: true, lineStyle: { color: '#409EFF' } },
      { name: 'Test Loss', type: 'line', data: trainLossHistory.test, smooth: true, lineStyle: { color: '#F56C6C' } }
    ]
  })
}

function renderWeightsChart(weights) {
  const chart = getChart(weightsChartRef)
  if (!chart || !weights) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: FEATURE_NAMES.map(n => featureNameMap[n] || n), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', name: '权重', min: 0, max: 1 },
    series: [{
      type: 'bar', data: weights.map(w => +w.toFixed(4)),
      itemStyle: { color: '#67C23A' }
    }]
  })
}

// ---- 版本管理 ----
async function loadVersions() {
  try {
    const res = await listVersions()
    versions.value = res.data || []
    const active = versions.value.find(v => v.is_active)
    if (active) {
      activeVersion.value = active.version
      modelR2.value = active.metrics?.final_r2 ?? null
    }
  } catch {}
}

async function doActivate(version) {
  await activateVersion(version)
  ElMessage.success('已激活')
  await loadVersions()
}

async function doDelete(version) {
  await ElMessageBox.confirm('确定删除该版本?', '警告', { type: 'warning' })
  await deleteVersion(version)
  ElMessage.success('已删除')
  await loadVersions()
}

// ---- 预测 ----
async function doPredict() {
  if (!activeVersion.value) return ElMessage.warning('请先训练模型')
  predicting.value = true
  try {
    const windowData = [predictInput.value]
    const res = await predict(windowData, activeVersion.value)
    predictResult.value = res.data
    predictHistory.preds.push(res.data.prediction)
    renderPredictChart()
  } catch (e) {
    ElMessage.error('预测失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    predicting.value = false
  }
}

function renderPredictChart() {
  const chart = getChart(predictChartRef)
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: predictHistory.preds.map((_, i) => i + 1) },
    yAxis: { type: 'value', name: '出口含水率', min: 0, max: 20 },
    series: [{
      type: 'line', data: predictHistory.preds, smooth: true,
      markLine: {
        data: [
          { yAxis: 14, name: '目标下界', lineStyle: { color: '#67C23A', type: 'dashed' } },
          { yAxis: 15, name: '目标上界', lineStyle: { color: '#67C23A', type: 'dashed' } }
        ]
      }
    }]
  })
}

// ---- PLC ----
async function loadPLCDevices() {
  try {
    const res = await getPlcDeviceList()
    plcDevices.value = res.data?.list || res.data || []
  } catch {}
}

function togglePLCStream() {
  if (plcRunning.value) {
    if (plcEventSource) plcEventSource.close()
    plcRunning.value = false
    return
  }

  if (!plcForm.device_id) return ElMessage.warning('请选择PLC设备')

  plcRunning.value = true
  plcHistory.preds = []
  plcHistory.ticks = []

  const params = new URLSearchParams({
    device_id: plcForm.device_id,
    interval: plcForm.interval
  })
  if (plcForm.point_ids) params.append('point_ids', plcForm.point_ids)
  if (plcForm.model_version) params.append('model_version', plcForm.model_version)

  plcEventSource = new EventSource(`http://localhost:8000/dryer/plc-stream?${params}`)

  plcEventSource.onmessage = (ev) => {
    const data = JSON.parse(ev.data)
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    plcPrediction.value = data
    plcPointsData.value = data.plc_points || []
    plcHistory.preds.push(data.prediction)
    plcHistory.ticks.push(data.tick)
    if (plcHistory.preds.length > 200) {
      plcHistory.preds.shift()
      plcHistory.ticks.shift()
    }
    renderPLCChart()
  }

  plcEventSource.onerror = () => {
    plcRunning.value = false
    plcEventSource.close()
  }
}

function renderPLCChart() {
  const chart = getChart(plcChartRef)
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: plcHistory.ticks },
    yAxis: { type: 'value', name: '出口含水率', min: 0, max: 20 },
    series: [{
      type: 'line', data: plcHistory.preds, smooth: true, symbol: 'none',
      areaStyle: { opacity: 0.2 },
      markLine: {
        data: [
          { yAxis: 14, name: '目标下界', lineStyle: { color: '#67C23A', type: 'dashed' } },
          { yAxis: 15, name: '目标上界', lineStyle: { color: '#67C23A', type: 'dashed' } }
        ]
      }
    }]
  })
}
</script>

<style scoped>
.dryer-container {
  padding: 16px;
}
.status-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
}
.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-item .label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.tab-header {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-cards .stat-card {
  margin-bottom: 8px;
}
.stat-name {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}
.stat-values {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.train-progress {
  margin-bottom: 12px;
}
.progress-stats {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.target-ok {
  color: #67C23A;
  font-weight: 700;
  font-size: 18px;
}
</style>
