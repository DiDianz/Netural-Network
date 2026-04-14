<!-- src/components/RealtimePanel.vue -->
<template>
  <div class="panel">
    <div class="panel-header">
      <h3>实时预测</h3>
      <div class="status-dot" :class="connectionState"></div>
    </div>
    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-label">当前预测值</span>
        <span class="metric-value accent">{{ (latestPrediction && latestPrediction.prediction && latestPrediction.prediction.toFixed(4)) || '--' }}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">滑动均值</span>
        <span class="metric-value">{{ state.stats.avgPrediction.toFixed(4) }}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">最大值</span>
        <span class="metric-value high">{{ state.stats.maxPrediction === -Infinity ? '--' : state.stats.maxPrediction.toFixed(4) }}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">最小值</span>
        <span class="metric-value low">{{ state.stats.minPrediction === Infinity ? '--' : state.stats.minPrediction.toFixed(4) }}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">已接收</span>
        <span class="metric-value">{{ state.stats.totalReceived }}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">不确定性</span>
        <span class="metric-value">{{ (latestPrediction && latestPrediction.uncertainty && latestPrediction.uncertainty.toFixed(4)) || '--' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  state: Object,
  latestPrediction: Object,
  connectionState: String
})
</script>

<style scoped>
.panel { background: var(--bg-card); border: 1px solid #1e1e2e; border-radius: 12px; padding: 20px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.panel-header h3 { font-size: 15px; font-weight: 600; color: #e0e0e0; margin: 0; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; background: #555; }
.status-dot.open { background: #4ade80; box-shadow: 0 0 8px rgba(74, 222, 128, 0.5); }
.status-dot.connecting, .status-dot.reconnecting { background: #facc15; animation: pulse 1s infinite; }
.status-dot.closed { background: #ef4444; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.metric-card { background: var(--bg-card); border: 1px solid #252530; border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 6px; }
.metric-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-value { font-size: 20px; font-weight: 700; color: #e0e0e0; }
.metric-value.accent { color: #4a9eff; }
.metric-value.high { color: #f87171; }
.metric-value.low { color: #4ade80; }
</style>
