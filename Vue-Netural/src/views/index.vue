<!-- src/views/index.vue — 系统首页仪表盘 -->
<template>
  <div class="dashboard">
    <!-- 欢迎卡片 -->
    <div class="welcome-card">
      <div class="welcome-left">
        <h2>{{ greeting }}，{{ userStore.nickName || userStore.userName }} 👋</h2>
        <p>神经网络预测系统 — 实时预测 · 智能分析 · PLC 数据采集</p>
      </div>
      <div class="welcome-right">
        <div class="time-display">{{ currentTime }}</div>
        <div class="date-display">{{ currentDate }}</div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" @click="$router.push('/prediction/models')">
        <div class="stat-icon" style="background: rgba(74,158,255,0.12); color: #4a9eff;">
          <el-icon :size="22"><DataAnalysis /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ modelStats.total }}</div>
          <div class="stat-label">模型总数</div>
        </div>
        <div class="stat-extra">
          <el-tag type="success" size="small" v-if="modelStats.current">{{ modelStats.current }}</el-tag>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/prediction/device')">
        <div class="stat-icon" style="background: rgba(251,191,36,0.12); color: #fbbf24;">
          <el-icon :size="22"><Cpu /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ plcStats.total }}</div>
          <div class="stat-label">PLC 设备</div>
        </div>
        <div class="stat-extra">
          <el-tag type="success" size="small" v-if="plcStats.connected > 0">{{ plcStats.connected }} 已连接</el-tag>
          <el-tag type="info" size="small" v-else>全部离线</el-tag>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/prediction/history')">
        <div class="stat-icon" style="background: rgba(74,222,128,0.12); color: #4ade80;">
          <el-icon :size="22"><TrendCharts /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ predictCount }}</div>
          <div class="stat-label">预测记录</div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/prediction/training')">
        <div class="stat-icon" style="background: rgba(167,139,250,0.12); color: #a78bfa;">
          <el-icon :size="22"><Timer /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ trainStats.total }}</div>
          <div class="stat-label">训练次数</div>
        </div>
        <div class="stat-extra">
          <el-tag :type="trainStats.isTraining ? 'warning' : 'info'" size="small" effect="dark">
            {{ trainStats.isTraining ? '训练中...' : '空闲' }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 中间区域 -->
    <div class="main-grid">
      <!-- 左侧：模型状态 -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title"><el-icon><DataAnalysis /></el-icon> 模型状态</span>
          <el-button text type="primary" size="small" @click="$router.push('/prediction/models')">管理 →</el-button>
        </div>
        <div class="panel-body">
          <div v-for="m in models" :key="m.key" class="model-item">
            <div class="model-left">
              <span class="model-name">{{ m.display_name }}</span>
              <el-tag v-if="m.is_current" type="success" size="small" effect="dark">当前</el-tag>
            </div>
            <div class="model-right">
              <el-tag :type="m.loaded ? 'success' : 'info'" size="small" plain>
                {{ m.loaded ? '已加载' : '未加载' }}
              </el-tag>
            </div>
          </div>
          <el-empty v-if="models.length === 0" description="暂无模型" :image-size="60" />
        </div>
      </div>

      <!-- 右侧：PLC 设备状态 -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title"><el-icon><Cpu /></el-icon> PLC 设备</span>
          <el-button text type="primary" size="small" @click="$router.push('/prediction/device')">管理 →</el-button>
        </div>
        <div class="panel-body">
          <div v-for="d in plcDevices" :key="d.id" class="plc-item">
            <div class="plc-left">
              <span class="plc-dot" :class="d.status === 'connected' ? 'dot-online' : 'dot-offline'"></span>
              <span class="plc-name">{{ d.name }}</span>
            </div>
            <div class="plc-right">
              <span class="plc-ip mono">{{ d.ip }}:{{ d.port }}</span>
              <el-tag size="small" :type="d.status === 'connected' ? 'success' : 'info'" plain>
                {{ d.status === 'connected' ? '在线' : '离线' }}
              </el-tag>
            </div>
          </div>
          <el-empty v-if="plcDevices.length === 0" description="暂无设备" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- 底部：快捷操作 -->
    <div class="quick-actions">
      <div class="action-card" @click="$router.push('/prediction/realtime')">
        <div class="action-icon" style="background: rgba(74,158,255,0.12); color: #4a9eff;">
          <el-icon :size="22"><Monitor /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">实时预测</span>
          <span class="action-desc">启动 SSE 实时预测流</span>
        </div>
      </div>
      <div class="action-card" @click="$router.push('/prediction/training')">
        <div class="action-icon" style="background: rgba(167,139,250,0.12); color: #a78bfa;">
          <el-icon :size="22"><VideoPlay /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">模型训练</span>
          <span class="action-desc">训练 LSTM / Transformer</span>
        </div>
      </div>
      <div class="action-card" @click="$router.push('/prediction/device')">
        <div class="action-icon" style="background: rgba(251,191,36,0.12); color: #fbbf24;">
          <el-icon :size="22"><Connection /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">PLC 管理</span>
          <span class="action-desc">设备连接 · 点位配置</span>
        </div>
      </div>
      <div class="action-card" @click="$router.push('/prediction/history')">
        <div class="action-icon" style="background: rgba(74,222,128,0.12); color: #4ade80;">
          <el-icon :size="22"><Document /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">历史记录</span>
          <span class="action-desc">查看预测历史数据</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  DataAnalysis, Cpu, TrendCharts, Timer,
  Monitor, VideoPlay, Connection, Document
} from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import { getModelList, getTrainHistory } from '../api/model'
import { getPlcDeviceList } from '../api/plc'
import request from '../api/request'

const userStore = useUserStore()

const currentTime = ref('')
const currentDate = ref('')
const models = ref([])
const plcDevices = ref([])
const predictCount = ref(0)
const trainStats = ref({ total: 0, isTraining: false })

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  if (h < 22) return '晚上好'
  return '夜深了'
})

const modelStats = computed(() => ({
  total: models.value.length,
  current: models.value.find(m => m.is_current)?.display_name || ''
}))

const plcStats = computed(() => ({
  total: plcDevices.value.length,
  connected: plcDevices.value.filter(d => d.status === 'connected').length
}))

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  currentDate.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  })
}

async function loadModels() {
  try {
    const res = await getModelList()
    models.value = res.data || res || []
  } catch (e) { /* ignore */ }
}

async function loadPlcDevices() {
  try {
    const res = await getPlcDeviceList()
    plcDevices.value = res.data || []
  } catch (e) { /* ignore */ }
}

async function loadPredictCount() {
  try {
    const res = await request.get('/predict/history', { params: { limit: 1 } })
    predictCount.value = res.total || 0
  } catch (e) { /* ignore */ }
}

async function loadTrainStats() {
  try {
    const [historyRes, statusRes] = await Promise.all([
      getTrainHistory({ limit: 1 }),
      request.get('/model/train/status')
    ])
    trainStats.value = {
      total: historyRes.total || 0,
      isTraining: statusRes.data?.is_training || false
    }
  } catch (e) { /* ignore */ }
}

let timer
onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  loadModels()
  loadPlcDevices()
  loadPredictCount()
  loadTrainStats()
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 欢迎卡片 */
.welcome-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28px 32px;
  background: linear-gradient(135deg, var(--accent-bg), var(--info-bg));
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
}

.welcome-left h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.welcome-left p {
  font-size: 13px;
  color: var(--text-muted);
}

.welcome-right { text-align: right; }

.time-display {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}

.date-display {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.stat-extra {
  flex-shrink: 0;
}

/* 面板 */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.panel {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-secondary);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-body {
  padding: 8px 12px;
  max-height: 260px;
  overflow-y: auto;
}

/* 模型列表 */
.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}

.model-item:hover {
  background: var(--accent-bg-light);
}

.model-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

/* PLC 列表 */
.plc-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}

.plc-item:hover {
  background: var(--accent-bg-light);
}

.plc-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plc-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-online {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103,194,58,0.5);
}

.dot-offline {
  background: #666;
}

.plc-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.plc-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plc-ip {
  font-size: 12px;
  color: var(--text-muted);
}

.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* 快捷操作 */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: block;
  margin-bottom: 3px;
}

.action-desc {
  font-size: 12px;
  color: var(--text-muted);
}

/* 响应式 */
@media (max-width: 900px) {
  .stats-grid,
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  .main-grid {
    grid-template-columns: 1fr;
  }
}
</style>
