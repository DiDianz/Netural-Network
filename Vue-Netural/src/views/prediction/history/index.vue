<!-- src/views/prediction/history/index.vue -->
<template>
  <div class="history-page">
    <div class="page-header">
      <h2>历史记录</h2>
      <p>查看训练日志、预测历史和训练趋势</p>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- 训练日志 -->
      <el-tab-pane label="训练日志" name="trainLog">
        <div class="search-bar">
          <el-input v-model="logKeyword" placeholder="搜索模型名/状态/备注" clearable style="width: 300px" @clear="loadTrainLogs"
            @keyup.enter="loadTrainLogs" />
          <el-button type="primary" @click="loadTrainLogs">搜索</el-button>
          <el-select v-model="logModelKey" placeholder="模型筛选" clearable style="width: 150px" @change="loadTrainLogs">
            <el-option label="LSTM" value="lstm" />
            <el-option label="GRU" value="gru" />
            <el-option label="Transformer" value="transformer" />
          </el-select>
        </div>
        <el-table :data="trainLogs" stripe v-loading="logLoading">
          <el-table-column prop="model_name" label="模型" width="120" />
          <el-table-column prop="total_epochs" label="总轮次" width="80" />
          <el-table-column prop="best_val_loss" label="最优Val Loss" width="130">
            <template #default="{ row }">
              {{ row.best_val_loss != null ? row.best_val_loss.toFixed(6) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="duration_seconds" label="耗时(秒)" width="100">
            <template #default="{ row }">
              {{ row.duration_seconds ? row.duration_seconds.toFixed(1) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="180" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="viewTrend(row)">查看趋势</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination v-if="logTotal > 0" :current-page="logPage" :page-size="logPageSize" :total="logTotal"
          layout="prev, pager, next" @current-change="handleLogPageChange"
          style="margin-top: 16px; justify-content: center;" />
      </el-tab-pane>

      <!-- 预测历史 -->
      <el-tab-pane label="预测历史" name="predictHistory">
        <div class="search-bar">
          <el-input v-model="predKeyword" placeholder="搜索模型名" clearable style="width: 300px" @clear="loadPredictHistory"
            @keyup.enter="loadPredictHistory" />
          <el-button type="primary" @click="loadPredictHistory">搜索</el-button>
          <el-select v-model="predModelKey" placeholder="模型筛选" clearable style="width: 150px"
            @change="loadPredictHistory">
            <el-option label="LSTM" value="lstm" />
            <el-option label="GRU" value="gru" />
            <el-option label="Transformer" value="transformer" />
          </el-select>
        </div>
        <el-table :data="predictHistory" stripe v-loading="predLoading">
          <el-table-column prop="model_name" label="模型" width="120" />
          <el-table-column prop="prediction" label="预测值" width="120">
            <template #default="{ row }">
              {{ row.prediction.toFixed(6) }}
            </template>
          </el-table-column>
          <el-table-column prop="confidence_upper" label="置信上界" width="120">
            <template #default="{ row }">
              {{ row.confidence_upper.toFixed(6) }}
            </template>
          </el-table-column>
          <el-table-column prop="confidence_lower" label="置信下界" width="120">
            <template #default="{ row }">
              {{ row.confidence_lower.toFixed(6) }}
            </template>
          </el-table-column>
          <el-table-column prop="uncertainty" label="不确定性" width="120">
            <template #default="{ row }">
              {{ row.uncertainty.toFixed(6) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="180" />
        </el-table>
        <el-pagination v-if="predTotal > 0" :current-page="predPage" :page-size="predPageSize" :total="predTotal"
          layout="prev, pager, next" @current-change="handlePredPageChange"
          style="margin-top: 16px; justify-content: center;" />
      </el-tab-pane>

      <!-- 训练趋势 -->
      <el-tab-pane label="训练趋势" name="trainTrend">
        <div class="search-bar">
          <el-input v-model="trendKeyword" placeholder="搜索train_id/模型名" clearable style="width: 300px"
            @clear="loadTrendList" @keyup.enter="loadTrendList" />
          <el-button type="primary" @click="loadTrendList">搜索</el-button>
        </div>

        <!-- 批次列表 -->
        <el-table :data="trendList" stripe v-loading="trendLoading" @row-click="handleTrendClick" highlight-current-row>
          <el-table-column prop="train_id" label="训练ID" width="100" />
          <el-table-column prop="model_name" label="模型" width="120" />
          <el-table-column prop="epoch_count" label="已训练轮次" width="100" />
          <el-table-column prop="total_epochs" label="总轮次" width="80" />
          <el-table-column prop="best_val_loss" label="最优Val Loss" width="130">
            <template #default="{ row }">
              {{ row.best_val_loss != null ? row.best_val_loss.toFixed(6) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="total_seconds" label="耗时(秒)" width="100" />
          <el-table-column prop="created_at" label="时间" width="180" />
        </el-table>

        <!-- 趋势图 -->
        <div class="trend-charts" v-if="trendData.length > 0">
          <div class="chart-card">
            <div ref="trendLossChartRef" class="chart-container"></div>
          </div>
          <div class="chart-card" v-if="trendData[0] && trendData[0].predictions.length > 0">
            <div ref="trendPredChartRef" class="chart-container"></div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { getTrainHistory, getPredictionHistory, getTrainTrend, getTrainTrendList } from '../../../api/model'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, CanvasRenderer, GridComponent, TooltipComponent, LegendComponent])

const activeTab = ref('trainLog')

// ========== 训练日志 ==========
const trainLogs = ref([])
const logLoading = ref(false)
const logKeyword = ref('')
const logModelKey = ref('')
const logPage = ref(1)
const logPageSize = ref(20)
const logTotal = ref(0)

async function loadTrainLogs() {
  logLoading.value = true
  try {
    const res = await getTrainHistory({
      keyword: logKeyword.value || undefined,
      model_key: logModelKey.value || undefined,
      limit: logPageSize.value,
      offset: (logPage.value - 1) * logPageSize.value
    })
    trainLogs.value = res.data || []
    logTotal.value = res.total || 0
  } catch (e) { console.error(e) }
  finally { logLoading.value = false }
}

function handleLogPageChange(page) {
  logPage.value = page
  loadTrainLogs()
}

// ========== 预测历史 ==========
const predictHistory = ref([])
const predLoading = ref(false)
const predKeyword = ref('')
const predModelKey = ref('')
const predPage = ref(1)
const predPageSize = ref(20)
const predTotal = ref(0)

async function loadPredictHistory() {
  predLoading.value = true
  try {
    const res = await getPredictionHistory({
      keyword: predKeyword.value || undefined,
      model_key: predModelKey.value || undefined,
      limit: predPageSize.value,
      offset: (predPage.value - 1) * predPageSize.value
    })
    predictHistory.value = res.data || []
    predTotal.value = res.total || 0
  } catch (e) { console.error(e) }
  finally { predLoading.value = false }
}

function handlePredPageChange(page) {
  predPage.value = page
  loadPredictHistory()
}

// ========== 训练趋势 ==========
const trendList = ref([])
const trendData = ref([])
const trendLoading = ref(false)
const trendKeyword = ref('')
const trendLossChartRef = ref(null)
const trendPredChartRef = ref(null)
let trendLossChart = null
let trendPredChart = null

async function loadTrendList() {
  trendLoading.value = true
  try {
    const res = await getTrainTrendList({ keyword: trendKeyword.value || undefined, limit: 20 })
    trendList.value = res.data || []
  } catch (e) { console.error(e) }
  finally { trendLoading.value = false }
}

async function handleTrendClick(row) {
  try {
    const res = await getTrainTrend({ train_id: row.train_id })
    trendData.value = res.data || []
    nextTick(() => renderTrendCharts())
  } catch (e) { console.error(e) }
}

function viewTrend(row) {
  activeTab.value = 'trainTrend'
  // 用 model_key 搜索趋势
  trendKeyword.value = row.model_key
  loadTrendList()
}

function renderTrendCharts() {
  const data = trendData.value
  if (!data.length) return

  const epochs = data.map(d => 'E' + d.epoch)
  const trainLosses = data.map(d => d.train_loss)
  const valLosses = data.map(d => d.val_loss)

  // Loss 曲线
  if (trendLossChartRef.value) {
    if (trendLossChart) trendLossChart.dispose()
    trendLossChart = echarts.init(trendLossChartRef.value)
    trendLossChart.setOption({
      title: { text: `Loss 曲线 (${data[0].model_name})`, left: 16, top: 10, textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' } },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333', textStyle: { color: '#e0e0e0' } },
      legend: { data: ['Train Loss', 'Val Loss'], top: 10, right: 16, textStyle: { color: '#888' } },
      grid: { left: 60, right: 20, top: 50, bottom: 40 },
      xAxis: { type: 'category', data: epochs, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#666' } },
      yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } } },
      series: [
        { name: 'Train Loss', type: 'line', data: trainLosses, smooth: true, lineStyle: { color: '#4a9eff', width: 2 }, itemStyle: { color: '#4a9eff' }, showSymbol: false },
        { name: 'Val Loss', type: 'line', data: valLosses, smooth: true, lineStyle: { color: '#f87171', width: 2 }, itemStyle: { color: '#f87171' }, showSymbol: false }
      ]
    })
  }

  // 预测值 vs 实际值（取最后一个 epoch 的数据）
  const lastEpoch = data[data.length - 1]
  if (trendPredChartRef.value && lastEpoch.predictions && lastEpoch.predictions.length > 0) {
    if (trendPredChart) trendPredChart.dispose()
    trendPredChart = echarts.init(trendPredChartRef.value)
    const indices = lastEpoch.predictions.map((_, i) => String(i + 1))
    trendPredChart.setOption({
      title: { text: `预测值 vs 实际值 (Epoch ${lastEpoch.epoch})`, left: 16, top: 10, textStyle: { fontSize: 14, fontWeight: 600, color: '#e0e0e0' } },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,15,20,0.95)', borderColor: '#333', textStyle: { color: '#e0e0e0' } },
      legend: { data: ['预测值', '实际值 (out_moist)'], top: 10, right: 16, textStyle: { color: '#888' } },
      grid: { left: 60, right: 20, top: 50, bottom: 40 },
      xAxis: { type: 'category', data: indices, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#666' } },
      yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#1a1a2e', type: 'dashed' } } },
      series: [
        { name: '预测值', type: 'line', data: lastEpoch.predictions, smooth: 0.3, lineStyle: { color: '#4a9eff', width: 2 }, itemStyle: { color: '#4a9eff' }, showSymbol: false },
        { name: '实际值 (out_moist)', type: 'line', data: lastEpoch.actuals, smooth: 0.3, lineStyle: { color: '#f97316', width: 2, type: 'dashed' }, itemStyle: { color: '#f97316' }, showSymbol: false }
      ]
    })
  }
}

function handleTabChange(tab) {
  if (tab === 'trainLog') loadTrainLogs()
  if (tab === 'predictHistory') loadPredictHistory()
  if (tab === 'trainTrend') loadTrendList()
}

onMounted(() => { loadTrainLogs() })

onUnmounted(() => {
  if (trendLossChart) trendLossChart.dispose()
  if (trendPredChart) trendPredChart.dispose()
})
</script>

<style scoped>
.history-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.page-header p {
  font-size: 13px;
  color: var(--text-muted);
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.trend-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 24px;
}

.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  padding: 12px;
}

.chart-container {
  width: 100%;
  height: 360px;
}
</style>
