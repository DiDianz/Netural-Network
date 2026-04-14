<!-- src/views/index.vue -->
<template>
  <div class="dashboard">
    <div class="welcome-card">
      <div>
        <h2>欢迎回来，{{ userStore.nickName || userStore.userName }}</h2>
        <p>神经网络预测系统 — 实时预测 · 智能分析</p>
      </div>
      <div class="welcome-time">
        <div class="time-display">{{ currentTime }}</div>
        <div class="date-display">{{ currentDate }}</div>
      </div>
    </div>

    <div class="quick-actions">
      <div class="action-card" @click="$router.push('/prediction/realtime')">
        <div class="action-icon" style="background: rgba(74, 158, 255, 0.1); color: #4a9eff;">
          <el-icon :size="24"><TrendCharts /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">实时预测</span>
          <span class="action-desc">启动神经网络实时预测</span>
        </div>
      </div>
      <div class="action-card">
        <div class="action-icon" style="background: rgba(74, 222, 128, 0.1); color: #4ade80;">
          <el-icon :size="24"><DataLine /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">历史记录</span>
          <span class="action-desc">查看历史预测数据</span>
        </div>
      </div>
      <div class="action-card">
        <div class="action-icon" style="background: rgba(167, 139, 250, 0.1); color: #a78bfa;">
          <el-icon :size="24"><Setting /></el-icon>
        </div>
        <div class="action-info">
          <span class="action-title">模型管理</span>
          <span class="action-desc">管理神经网络模型</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { TrendCharts, DataLine, Setting } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const currentTime = ref('')
const currentDate = ref('')

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  currentDate.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  })
}

let timer
onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<!-- src/views/index.vue（只改 style 部分） -->
<style scoped>
.dashboard {
  max-width: 1200px;
}

.welcome-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28px 32px;
  background: linear-gradient(135deg, var(--accent-bg), var(--info-bg));
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  margin-bottom: 20px;
}

.welcome-card h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.welcome-card p {
  font-size: 13px;
  color: var(--text-muted);
}

.welcome-time { text-align: right; }

.time-display {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent);
}

.date-display {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
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
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  display: block;
  margin-bottom: 4px;
}

.action-desc {
  font-size: 12px;
  color: var(--text-muted);
}
</style>

