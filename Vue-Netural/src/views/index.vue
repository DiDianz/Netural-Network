<!-- src/views/index.vue — 美化版仪表盘 -->
<template>
  <div class="dashboard">
    <!-- 顶部 Hero 区 -->
    <div class="hero">
      <div class="hero-bg">
        <div class="hero-orb orb-1"></div>
        <div class="hero-orb orb-2"></div>
        <div class="hero-orb orb-3"></div>
      </div>
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-greeting">{{ greeting }}</div>
          <h1 class="hero-name">{{ userStore.nickName || userStore.userName }}</h1>
          <p class="hero-subtitle">神经网络预测系统 · 实时预测 · 智能分析 · PLC 数据采集</p>
        </div>
        <div class="hero-right">
          <div class="hero-time">{{ currentTime }}</div>
          <div class="hero-date">{{ currentDate }}</div>
          <div class="hero-status">
            <span class="status-dot" :class="hasOnlinePlc ? 'dot-on' : 'dot-off'"></span>
            <span>{{ hasOnlinePlc ? `${plcStats.connected} 台 PLC 在线` : 'PLC 全部离线' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计卡片行 -->
    <div class="stats-row">
      <div class="stat-card" v-for="s in statCards" :key="s.label" @click="$router.push(s.path)">
        <div class="stat-glow" :style="{ background: s.glow }"></div>
        <div class="stat-icon" :style="{ background: s.iconBg, color: s.iconColor }">
          <el-icon :size="22"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-number">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
        <div class="stat-badge" v-if="s.badge">
          <el-tag :type="s.badgeType" size="small" effect="dark" round>{{ s.badge }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-grid">
      <!-- 模型状态 -->
      <div class="panel glass">
        <div class="panel-head">
          <div class="panel-title">
            <div class="panel-icon blue"><el-icon><DataAnalysis /></el-icon></div>
            <span>模型状态</span>
          </div>
          <el-button text type="primary" size="small" @click="$router.push('/prediction/models')">
            查看全部 <el-icon class="ml-4"><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="panel-content">
          <div v-for="m in models" :key="m.key" class="list-item">
            <div class="list-left">
              <div class="item-avatar blue">
                <el-icon :size="16"><Cpu /></el-icon>
              </div>
              <div>
                <div class="item-name">{{ m.display_name }}</div>
                <div class="item-sub">{{ m.key.toUpperCase() }} 模型</div>
              </div>
            </div>
            <div class="list-right">
              <el-tag v-if="m.is_current" type="success" size="small" effect="dark" round>当前使用</el-tag>
              <el-tag :type="m.loaded ? 'success' : 'info'" size="small" plain round>
                {{ m.loaded ? '已加载' : '未加载' }}
              </el-tag>
            </div>
          </div>
          <el-empty v-if="models.length === 0" description="暂无模型" :image-size="50" />
        </div>
      </div>

      <!-- PLC 设备 -->
      <div class="panel glass">
        <div class="panel-head">
          <div class="panel-title">
            <div class="panel-icon amber"><el-icon><Cpu /></el-icon></div>
            <span>PLC 设备</span>
          </div>
          <el-button text type="primary" size="small" @click="$router.push('/prediction/device')">
            管理设备 <el-icon class="ml-4"><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="panel-content">
          <div v-for="d in plcDevices" :key="d.id" class="list-item">
            <div class="list-left">
              <div class="item-avatar" :class="d.status === 'connected' ? 'green' : 'grey'">
                <el-icon :size="16"><Connection /></el-icon>
              </div>
              <div>
                <div class="item-name">{{ d.name }}</div>
                <div class="item-sub mono">{{ d.ip }}:{{ d.port }} · {{ d.point_count || 0 }} 点位</div>
              </div>
            </div>
            <div class="list-right">
              <span class="pulse-dot" :class="d.status === 'connected' ? 'on' : 'off'"></span>
              <el-tag :type="d.status === 'connected' ? 'success' : 'info'" size="small" plain round>
                {{ d.status === 'connected' ? '在线' : '离线' }}
              </el-tag>
            </div>
          </div>
          <el-empty v-if="plcDevices.length === 0" description="暂无设备" :image-size="50">
            <el-button type="primary" size="small" @click="$router.push('/prediction/device')">添加设备</el-button>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="quick-row">
      <div class="quick-card" v-for="q in quickLinks" :key="q.title" @click="$router.push(q.path)">
        <div class="quick-icon" :style="{ background: q.iconBg }">
          <el-icon :size="20" :style="{ color: q.iconColor }"><component :is="q.icon" /></el-icon>
        </div>
        <div class="quick-text">
          <span class="quick-title">{{ q.title }}</span>
          <span class="quick-desc">{{ q.desc }}</span>
        </div>
        <el-icon class="quick-arrow"><ArrowRight /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  DataAnalysis, Cpu, TrendCharts, Timer,
  Monitor, VideoPlay, Connection, Document,
  ArrowRight
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
  if (h < 6) return '🌙 夜深了'
  if (h < 9) return '🌅 早上好'
  if (h < 12) return '☀️ 上午好'
  if (h < 14) return '🌤 中午好'
  if (h < 18) return '🌇 下午好'
  if (h < 22) return '🌆 晚上好'
  return '🌙 夜深了'
})

const plcStats = computed(() => ({
  total: plcDevices.value.length,
  connected: plcDevices.value.filter(d => d.status === 'connected').length
}))

const hasOnlinePlc = computed(() => plcStats.value.connected > 0)

const statCards = computed(() => [
  {
    label: '神经网络模型', value: models.value.length,
    icon: DataAnalysis, path: '/prediction/models',
    iconBg: 'rgba(74,158,255,0.12)', iconColor: '#4a9eff',
    glow: 'radial-gradient(circle, rgba(74,158,255,0.08) 0%, transparent 70%)',
    badge: models.value.find(m => m.is_current)?.display_name || null,
    badgeType: 'success'
  },
  {
    label: 'PLC 设备', value: plcStats.value.total,
    icon: Cpu, path: '/prediction/device',
    iconBg: 'rgba(251,191,36,0.12)', iconColor: '#fbbf24',
    glow: 'radial-gradient(circle, rgba(251,191,36,0.08) 0%, transparent 70%)',
    badge: plcStats.value.connected > 0 ? `${plcStats.value.connected} 在线` : '全部离线',
    badgeType: plcStats.value.connected > 0 ? 'success' : 'info'
  },
  {
    label: '预测记录', value: predictCount.value,
    icon: TrendCharts, path: '/prediction/history',
    iconBg: 'rgba(74,222,128,0.12)', iconColor: '#4ade80',
    glow: 'radial-gradient(circle, rgba(74,222,128,0.08) 0%, transparent 70%)',
    badge: null, badgeType: 'info'
  },
  {
    label: '训练次数', value: trainStats.value.total,
    icon: Timer, path: '/prediction/training',
    iconBg: 'rgba(167,139,250,0.12)', iconColor: '#a78bfa',
    glow: 'radial-gradient(circle, rgba(167,139,250,0.08) 0%, transparent 70%)',
    badge: trainStats.value.isTraining ? '训练中...' : null,
    badgeType: 'warning'
  }
])

const quickLinks = [
  { title: '实时预测', desc: 'SSE 实时预测流', path: '/prediction/realtime', icon: Monitor, iconBg: 'rgba(74,158,255,0.1)', iconColor: '#4a9eff' },
  { title: '模型训练', desc: 'LSTM / Transformer', path: '/prediction/training', icon: VideoPlay, iconBg: 'rgba(167,139,250,0.1)', iconColor: '#a78bfa' },
  { title: 'PLC 管理', desc: '设备连接 · 点位配置', path: '/prediction/device', icon: Connection, iconBg: 'rgba(251,191,36,0.1)', iconColor: '#fbbf24' },
  { title: '历史记录', desc: '查看预测历史数据', path: '/prediction/history', icon: Document, iconBg: 'rgba(74,222,128,0.1)', iconColor: '#4ade80' },
]

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
}

async function loadModels() {
  try { const res = await getModelList(); models.value = res.data || res || [] } catch (e) {}
}
async function loadPlcDevices() {
  try { const res = await getPlcDeviceList(); plcDevices.value = res.data || [] } catch (e) {}
}
async function loadPredictCount() {
  try { const res = await request.get('/predict/history', { params: { limit: 1 } }); predictCount.value = res.total || 0 } catch (e) {}
}
async function loadTrainStats() {
  try {
    const [h, s] = await Promise.all([getTrainHistory({ limit: 1 }), request.get('/model/train/status')])
    trainStats.value = { total: h.total || 0, isTraining: s.data?.is_training || false }
  } catch (e) {}
}

let timer
onMounted(() => {
  updateTime(); timer = setInterval(updateTime, 1000)
  loadModels(); loadPlcDevices(); loadPredictCount(); loadTrainStats()
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ====== Hero ====== */
.hero {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
}

.hero-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.hero-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  animation: float 8s ease-in-out infinite alternate;
}

.orb-1 {
  width: 300px; height: 300px;
  background: var(--accent-glow);
  top: -100px; left: -50px;
}

.orb-2 {
  width: 200px; height: 200px;
  background: rgba(167,139,250,0.15);
  bottom: -80px; right: 100px;
  animation-delay: -3s;
}

.orb-3 {
  width: 150px; height: 150px;
  background: rgba(74,222,128,0.1);
  top: -30px; right: -20px;
  animation-delay: -5s;
}

@keyframes float {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(30px, 20px) scale(1.15); }
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px 36px;
}

.hero-greeting {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 4px;
  letter-spacing: 0.5px;
}

.hero-name {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.hero-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.3px;
}

.hero-right { text-align: right; }

.hero-time {
  font-size: 36px;
  font-weight: 700;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  line-height: 1;
  letter-spacing: -1px;
}

.hero-date {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

.hero-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-input);
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-secondary);
}

.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
}

.dot-on {
  background: var(--success);
  box-shadow: 0 0 8px rgba(74,222,128,0.5);
}

.dot-off { background: #555; }

/* ====== 统计卡 ====== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s;
  overflow: hidden;
}

.stat-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.2);
}

.stat-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.stat-card:hover .stat-glow { opacity: 1; }

.stat-icon {
  width: 46px; height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info { flex: 1; min-width: 0; }

.stat-number {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
}

.stat-badge { flex-shrink: 0; }

/* ====== 面板 ====== */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.panel {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  overflow: hidden;
}

.glass {
  backdrop-filter: blur(10px);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-secondary);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-icon.blue { background: rgba(74,158,255,0.12); color: #4a9eff; }
.panel-icon.amber { background: rgba(251,191,36,0.12); color: #fbbf24; }

.panel-content {
  padding: 6px 12px;
  max-height: 280px;
  overflow-y: auto;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  transition: background 0.15s;
}

.list-item:hover {
  background: var(--accent-bg-light);
}

.list-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.item-avatar {
  width: 36px; height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.item-avatar.blue { background: rgba(74,158,255,0.12); color: #4a9eff; }
.item-avatar.green { background: rgba(74,222,128,0.12); color: #4ade80; }
.item-avatar.amber { background: rgba(251,191,36,0.12); color: #fbbf24; }
.item-avatar.grey { background: rgba(100,100,100,0.12); color: #888; }

.item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.item-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px !important;
}

.list-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.pulse-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pulse-dot.on {
  background: var(--success);
  box-shadow: 0 0 6px rgba(74,222,128,0.5);
  animation: pulse 2s ease-in-out infinite;
}

.pulse-dot.off { background: #555; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.ml-4 { margin-left: 4px; }

/* ====== 快捷入口 ====== */
.quick-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s;
}

.quick-card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}

.quick-icon {
  width: 42px; height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.quick-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quick-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.quick-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.quick-arrow {
  color: var(--text-muted);
  transition: transform 0.2s, color 0.2s;
}

.quick-card:hover .quick-arrow {
  transform: translateX(3px);
  color: var(--accent);
}

/* ====== 响应式 ====== */
@media (max-width: 1000px) {
  .stats-row, .quick-row { grid-template-columns: repeat(2, 1fr); }
  .content-grid { grid-template-columns: 1fr; }
  .hero-content { flex-direction: column; gap: 16px; text-align: center; }
  .hero-right { text-align: center; }
}
</style>
